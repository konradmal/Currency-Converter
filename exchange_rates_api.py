import json
from json import JSONDecodeError
from typing import Dict, Tuple

import requests
from requests import RequestException


class ExchangeRatesApi:
    """Simple wrapper around the ExchangeRate-API with file-based caching.

    The main method `fetch_exchange_rates` always returns a tuple:
    (rates_dict, date_string).
    It first tries to use the online API, and if that fails it falls back
    to the cached JSON file. If neither works, it raises RuntimeError.
    """

    def __init__(self, api_key: str, base_currency: str = "USD", cache_file: str = "exchange_rates_cache.json", timeout: int = 5) -> None:
        self.api_key = api_key
        self.base_currency = base_currency
        self.cache_file = cache_file
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
            return rates, date

        except (RequestException, ValueError, KeyError, TypeError) as api_exc:
            # API failed – try cache
            try:
                data = self._read_cache()
                rates, date = self._extract_rates_and_date(data)
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
