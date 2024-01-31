import requests

class ExchangeRatesApi:
    def __init__(self, api_key):
        self.api_key = api_key

    def fetch_exchange_rates(self):
        url = f"https://api.exchangerate-api.com/v4/latest/USD?apiKey={self.api_key}"
        response = requests.get(url)
        return response.json()['rates']