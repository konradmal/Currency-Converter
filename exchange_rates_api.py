import requests
import json

# Class handling communication with the Exchange Rates API
class ExchangeRatesApi:
    def __init__(self, api_key):
        self.api_key = api_key
        self.cache_file = 'exchange_rates_cache.json'

    # Function to fetch and return exchange rates from the API
    def fetch_exchange_rates(self):
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/USD?apiKey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            with open(self.cache_file, 'w') as file:
                json.dump(data, file)
            return data['rates'], data['date']
        except Exception as e:
            try:
                with open(self.cache_file, 'r') as file:
                    data = json.load(file)
                return data['rates'], data['date']
            except Exception as e:
                print("Error fetching exchange rates: ", e)
                return {}