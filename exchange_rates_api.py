import json
from json import JSONDecodeError
from typing import Dict, Tuple, List

import requests
from requests import RequestException


class ExchangeRatesApi:
    """Simple wrapper around the ExchangeRate-API with file-based caching.

    The main method `fetch_exchange_rates` always returns a tuple:
    (rates_dict, date_string).
    It first tries to use the online API, and if that fails it falls back
    to the cached JSON file. If neither works, it raises RuntimeError.

    Additionally, every successful fetch is appended to a simple local
    history file, allowing the GUI to display charts of rate changes
    over time.
    """

    def __init__(
        self,
        api_key: str,
        base_currency: str = "USD",
        cache_file: str = "exchange_rates_cache.json",
        history_file: str = "exchange_rates_history.json",
        timeout: int = 5,
    ) -> None:
        self.api_key = api_key
        self.base_currency = base_currency
        self.cache_file = cache_file
        self.history_file = history_file
        self.timeout = timeout

    def _build_url(self) -> str:
        """Build the URL for the given base currency.

        The exact format of the URL depends on the API provider. This keeps
        the rest of the code in one place so it's easy to adjust.
        """
        return f"https://api.exchangerate-api.com/v4/latest/{self.base_currency}?apiKey={self.api_key}"

    def fetch_exchange_rates(self) -> Tuple[Dict[str, float], str]:
        """Fetch exchange rates from the API or cache.

        Returns
        -------
        Tuple[Dict[str, float], str]
            A dictionary of currency rates and a string representation
            of the date when those rates were valid.

        Raises
        ------
        RuntimeError
            If neither the API nor the cache can be used to obtain rates.
        """
        try:
            url = self._build_url()
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            try:
                data = response.json()
            except JSONDecodeError as exc:
                raise ValueError("Invalid JSON in exchange rates response") from exc

            rates, date = self._extract_rates_and_date(data)
            self._save_cache(data)
            self._append_history_snapshot(date, rates)
            return rates, date

        except (RequestException, ValueError, KeyError, TypeError) as api_exc:
            # API failed – try cache
            try:
                data = self._read_cache()
                rates, date = self._extract_rates_and_date(data)
                # Do not append to history here: it's already old data
                return rates, date
            except (OSError, JSONDecodeError, ValueError, KeyError, TypeError) as cache_exc:
                raise RuntimeError(
                    f"Cannot load exchange rates from API nor cache "
                    f"(api error: {api_exc}, cache error: {cache_exc})"
                ) from cache_exc

    @staticmethod
    def _extract_rates_and_date(data: dict) -> Tuple[Dict[str, float], str]:
        """Extract the rates dictionary and a human-readable date string."""
        if "rates" not in data:
            raise ValueError("Missing 'rates' in exchange rates response.")

        rates = data["rates"]
        if not isinstance(rates, dict):
            raise ValueError("'rates' field is not a dictionary.")

        # Prefer the 'date' field; if missing, fall back to 'time_last_updated'
        date = data.get("date")
        if date is None:
            # Some APIs return a Unix timestamp here; convert it to string anyway
            date = str(data.get("time_last_updated", "unknown date"))

        return rates, date

    def _save_cache(self, data: dict) -> None:
        """Save raw API JSON to the cache file.

        Any error while writing the cache is ignored deliberately, because
        it should not break the main functionality.
        """
        try:
            with open(self.cache_file, "w", encoding="utf-8") as file:
                json.dump(data, file)
        except OSError:
            # Cache write errors are non-fatal
            pass

    def _read_cache(self) -> dict:
        """Read and return the cached JSON data.

        Raises
        ------
        OSError
            If the cache file is missing or cannot be opened.
        JSONDecodeError
            If the cache file does not contain valid JSON.
        """
        with open(self.cache_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data

    # ------------------------------------------------------------------
    # SIMPLE LOCAL HISTORY
    # ------------------------------------------------------------------
    def _append_history_snapshot(self, date: str, rates: Dict[str, float]) -> None:
        """Append a single snapshot (date + rates) to the history file.

        If the last entry already has the same date, it is replaced.
        Any error while writing history is ignored to avoid breaking
        the main flow.
        """
        try:
            history = self._read_history()
        except Exception:
            history = []

        entry = {"date": date, "rates": rates}

        if history and history[-1].get("date") == date:
            history[-1] = entry
        else:
            history.append(entry)

        try:
            with open(self.history_file, "w", encoding="utf-8") as file:
                json.dump(history, file)
        except OSError:
            # History write errors are non-fatal
            pass

    def _read_history(self) -> List[dict]:
        """Read full history from the history file."""
        with open(self.history_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError("History file must contain a list of entries.")
        return data

    def get_history(self) -> List[dict]:
        """Public helper: safely return entire history list.

        Returns an empty list if there is no valid history file yet.
        """
        try:
            return self._read_history()
        except (OSError, JSONDecodeError, ValueError, TypeError):
            return []


    def get_or_create_history(self, days: int = 365) -> List[dict]:
        """Return existing history or fetch it from the API if missing.

        By default it tries to load a local history file; if it does not
        exist or is empty, it downloads approximately `days` days of data,
        saves them to the history file and returns them.
        """
        history = self.get_history()
        if history:
            return history

        history = self._fetch_history_series(days=days)
        try:
            with open(self.history_file, "w", encoding="utf-8") as file:
                json.dump(history, file)
        except OSError:
            # Not fatal
            pass
        return history

    def _fetch_history_series(self, days: int) -> List[dict]:
        """Fetch historical daily rates for the last `days` days.

        This implementation uses one request per day. Depending on your
        API provider, you may want to replace this with a dedicated
        time-series endpoint to stay within rate limits.
        """
        from datetime import date, timedelta

        history: List[dict] = []

        today = date.today()
        start = today - timedelta(days=days - 1)

        for i in range(days):
            current = start + timedelta(days=i)
            day_str = current.isoformat()
            url = f"https://api.exchangerate-api.com/v4/{day_str}/{self.base_currency}?apiKey={self.api_key}"

            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                rates, date_str = self._extract_rates_and_date(data)
                history.append({"date": date_str, "rates": rates})
            except (RequestException, JSONDecodeError, ValueError, KeyError, TypeError):
                # Skip days we could not download
                continue

        return history
