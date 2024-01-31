import sys
import requests
import getApi
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox

API_KEY = getApi.getApi()

def fetch_exchange_rates():
    url = f"https://api.exchangerate-api.com/v4/latest/USD?apiKey={API_KEY}"
    response = requests.get(url)
    return response.json()['rates']

def convert_currency(amount, source_rate, target_rate):
    return amount * (target_rate / source_rate)

class CurrencyConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.exchange_rates = {}
        self.initialize_ui()
    
    def initialize_ui(self):
        self.setWindowTitle('Currency Converter')

        layout = QVBoxLayout()

        self.amountInput = QLineEdit(self)
        self.amountInput.setPlaceholderText('Enter amount')
        layout.addWidget(self.amountInput)

        self.sourceCurrencySelector = QComboBox(self)
        self.targetCurrencySelector = QComboBox(self)
        currencies = ['PLN', 'EUR', 'USD', 'CHF', 'GBP']
        self.sourceCurrencySelector.addItems(currencies)
        self.targetCurrencySelector.addItems(currencies)
        layout.addWidget(self.sourceCurrencySelector)
        layout.addWidget(self.targetCurrencySelector)

        self.convertButton = QPushButton('Convert', self)
        self.convertButton.clicked.connect(self.on_convert)
        layout.addWidget(self.convertButton)

        self.resultLabel = QLabel('')
        layout.addWidget(self.resultLabel)

        self.setLayout(layout)
        self.setGeometry(300, 300, 350, 200)

    def on_convert(self):
        try:
            amount = float(self.amountInput.text())
            if not self.exchange_rates:
                self.exchange_rates = fetch_exchange_rates()
            source_currency = self.sourceCurrencySelector.currentText()
            target_currency = self.targetCurrencySelector.currentText()
            source_rate = self.exchange_rates.get(source_currency, 1)
            target_rate = self.exchange_rates.get(target_currency, 1)
            result = convert_currency(amount, source_rate, target_rate)
            self.resultLabel.setText(f"{amount:.2f} {source_currency} to {result:.2f} {target_currency}")
        except ValueError:
            self.resultLabel.setText("Please enter a valid amount.")

def main():
    app = QApplication(sys.argv)
    ex = CurrencyConverter()
    ex.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()