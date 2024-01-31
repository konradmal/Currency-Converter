import sys
import requests
import getApi
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox


class CurrencyConverter(QWidget):
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.exchange_rates = self.fetch_exchange_rates()
        self.initialize_ui()
    
    def fetch_exchange_rates(self):
        url = f"https://api.exchangerate-api.com/v4/latest/USD?apiKey={self.api_key}"
        response = requests.get(url)
        return response.json()['rates']

    def convert_currency(self, amount, source_currency, target_currency):
        source_rate = self.exchange_rates.get(source_currency, 1)
        target_rate = self.exchange_rates.get(target_currency, 1)
        return amount * (target_rate / source_rate)

    def initialize_ui(self):
        self.setWindowTitle('Currency Converter')
        self.setStyleSheet("font-family: Arial; background-color: #F5F5F5;")
        self.setup_layout()

    def setup_layout(self):
        layout = QVBoxLayout()
        self.setup_input_widgets(layout)
        self.setup_result_label(layout)
        self.setLayout(layout)
        self.setGeometry(300, 300, 350, 200)

    def setup_input_widgets(self, layout):
        self.amountInput = self.create_line_edit('Enter amount', "font-size: 16px;")
        layout.addWidget(self.amountInput)

        currencies = ['PLN', 'EUR', 'USD', 'CHF', 'GBP']
        self.sourceCurrencySelector = self.create_combo_box(currencies, "font-size: 14px; background-color: #E8E8E8;")
        self.targetCurrencySelector = self.create_combo_box(currencies, "font-size: 14px; background-color: #E8E8E8;")
        layout.addWidget(self.sourceCurrencySelector)
        layout.addWidget(self.targetCurrencySelector)

        self.convertButton = self.create_button('Convert', "background-color: #4CAF50; color: white; font-size: 16px;")
        layout.addWidget(self.convertButton)

    def setup_result_label(self, layout):
        self.resultLabel = QLabel('')
        self.resultLabel.setStyleSheet("color: #333333; font-size: 18px;")
        layout.addWidget(self.resultLabel)

    def create_line_edit(self, placeholder, style):
        line_edit = QLineEdit(self)
        line_edit.setPlaceholderText(placeholder)
        line_edit.setStyleSheet(style)
        return line_edit

    def create_combo_box(self, items, style):
        combo_box = QComboBox(self)
        combo_box.addItems(items)
        combo_box.setStyleSheet(style)
        return combo_box

    def create_button(self, text, style):
        button = QPushButton(text, self)
        button.setStyleSheet(style)
        button.clicked.connect(self.on_convert)
        return button

    def on_convert(self):
        try:
            amount = float(self.amountInput.text())
            source_currency = self.sourceCurrencySelector.currentText()
            target_currency = self.targetCurrencySelector.currentText()
            result = self.convert_currency(amount, source_currency, target_currency)
            self.resultLabel.setText(f"{amount:.2f} {source_currency} to {result:.2f} {target_currency}")
        except ValueError:
            self.resultLabel.setText("Please enter a valid amount.")


def main():
    app = QApplication(sys.argv)
    api_key = getApi.getApi()
    ex = CurrencyConverter(api_key)
    ex.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()