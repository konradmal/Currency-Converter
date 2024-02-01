import requests

# Class handling communication with the Exchange Rates API
class ExchangeRatesApi:
    # Constructor initializing the class with an API key
    def __init__(self, api_key):
        self.api_key = api_key

    # Function to fetch and return exchange rates from the API
    def fetch_exchange_rates(self):
        url = f"https://api.exchangerate-api.com/v4/latest/USD?apiKey={self.api_key}"
        response = requests.get(url)
        return response.json()['rates']
