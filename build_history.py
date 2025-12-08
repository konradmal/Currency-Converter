"""
Helper script for building a local history of exchange rates for charts.

Data source
-----------
The script uses official average FX rates from the NBP public API
(tables A, endpoint `api.nbp.pl`), which does not require any API key.

Output format
-------------
The history is stored in a JSON file with the following structure:

    [
        {
            "date": "YYYY-MM-DD",
            "rates": {
                "USD": 1.0,
                "PLN": <PLN per 1 USD>,
                "EUR": <EUR per 1 USD>,
                ...
            }
        },
        ...
    ]

The "rates" dictionary is compatible with the rest of the project:

- USD is the base currency (rates["USD"] == 1.0).
- rates["PLN"] is how many PLN you get for 1 USD.
- For any other currency X, rates[X] is how many units of X you get for 1 USD.

Implementation details
----------------------
NBP enforces a maximum range of 93 days for a single request. To work
around this, the script splits the requested period into several smaller
chunks (for example 90-day ranges) and downloads each chunk separately.
All the partial results are then merged and written to a single file.
"""

import json
from datetime import date, timedelta
from typing import Dict, List, Tuple

import requests


NBP_URL_TEMPLATE = "https://api.nbp.pl/api/exchangerates/tables/a/{start}/{end}/?format=json"


def _iter_ranges(start: date, end: date, max_span_days: int = 90) -> List[Tuple[date, date]]:
    """
    Split the closed interval [start, end] into subranges with length
    at most `max_span_days` days.

    The resulting ranges are non-overlapping and cover the entire
    [start, end] interval.
    """
    ranges: List[Tuple[date, date]] = []
    current = start
    step = timedelta(days=max_span_days - 1)

    while current <= end:
        chunk_end = current + step
        if chunk_end > end:
            chunk_end = end
        ranges.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)

    return ranges


def build_history(
    days: int = 365,
    history_file: str = "exchange_rates_history.json",
) -> None:
    """
    Build a local history of FX rates based on NBP tables A.

    The function:
    - approximates the last `days` business days by querying a wider
      date range (about 2 * days days back),
    - splits that range into smaller chunks to respect the NBP limit
      of 93 days per request,
    - converts all rates from "PLN per currency" to "currency per USD",
    - stores the last `days` available dates as a list of snapshots
      in `history_file`.

    Parameters
    ----------
    days : int
        Target length of the history (number of business days).
    history_file : str
        Output JSON file path for the generated history.
    """
    if days <= 0:
        raise ValueError("days must be a positive integer")

    today = date.today()
    # NBP does not publish tables for weekends and holidays.
    # To obtain approximately `days` business days we go back
    # roughly twice as far and then trim the result.
    raw_start = today - timedelta(days=days * 2)
    raw_end = today

    print(f"Building history from NBP tables A between {raw_start} and {raw_end} (in chunks)...")

    # Map from date string ("YYYY-MM-DD") to a dictionary of rates.
    history_by_date: Dict[str, Dict[str, float]] = {}

    # Download and process each date range chunk separately.
    for chunk_start, chunk_end in _iter_ranges(raw_start, raw_end, max_span_days=90):
        url = NBP_URL_TEMPLATE.format(start=chunk_start.isoformat(), end=chunk_end.isoformat())
        print(f"  -> Requesting {chunk_start} to {chunk_end}")
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
        except Exception as exc:
            # Network or HTTP problems for this particular chunk are logged
            # but do not stop the whole process.
            print(f"[ERROR] Request for {chunk_start}..{chunk_end} failed: {exc}")
            continue

        tables = response.json()
        if not isinstance(tables, list):
            print(f"[WARN] Unexpected response (not a list) for {chunk_start}..{chunk_end}, skipping.")
            continue

        for table in tables:
            date_str = table.get("effectiveDate")
            rates_list = table.get("rates")

            if not date_str or not isinstance(rates_list, list):
                print(f"[WARN] Skipping malformed table: {table!r}")
                continue

            # Build a mapping "PLN per 1 unit of a given currency".
            pln_per_currency: Dict[str, float] = {}
            for item in rates_list:
                code = item.get("code")
                mid = item.get("mid")
                if not code or not isinstance(mid, (int, float)):
                    continue
                pln_per_currency[code] = float(mid)

            if "USD" not in pln_per_currency:
                print(f"[WARN] No USD rate for {date_str}, skipping.")
                continue

            pln_per_usd = pln_per_currency["USD"]  # PLN per 1 USD

            # Convert NBP data to the internal format where USD is the base.
            rates: Dict[str, float] = {}

            # 1 USD in USD (base currency).
            rates["USD"] = 1.0

            # 1 USD expressed in PLN.
            rates["PLN"] = pln_per_usd

            # For each other currency X (NBP gives PLN per 1 X):
            #   1 USD = pln_per_usd PLN
            #   1 X   = pln_per_currency[X] PLN
            # so X per USD = pln_per_usd / pln_per_currency[X].
            for code, pln_per_code in pln_per_currency.items():
                if code == "USD":
                    continue
                rate_x_per_usd = pln_per_usd / pln_per_code
                rates[code] = rate_x_per_usd

            # If the same date is encountered in several chunks the last
            # processed entry for that date will overwrite previous ones.
            history_by_date[date_str] = rates
            print(f"[OK] {date_str} - {len(rates)} rates (NBP-based, base USD)")

    if not history_by_date:
        print("No history collected from NBP – nothing to write.")
        return

    # Sort all available dates, then keep only the last `days` entries.
    all_dates_sorted = sorted(history_by_date.keys())
    if len(all_dates_sorted) > days:
        selected_dates = all_dates_sorted[-days:]
    else:
        selected_dates = all_dates_sorted

    history = [
        {"date": d, "rates": history_by_date[d]}
        for d in selected_dates
    ]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f)

    print(f"Written {len(history)} snapshots to {history_file}")


if __name__ == "__main__":
    # Typical usage from the command line:
    #     python build_history.py
    #
    # If needed, you can adjust the number of days here.
    build_history(days=365)