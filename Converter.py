import sys
import requests
import getApi
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox

API_KEY = getApi.getApi()

def pobierz_kursy():
    url = f"https://api.exchangerate-api.com/v4/latest/USD?apiKey={API_KEY}"
    response = requests.get(url)
    return response.json()['rates']

def konwertuj(kwota, kurs_zrodlowy, kurs_docelowy):
    return kwota * (kurs_docelowy / kurs_zrodlowy)

class CurrencyConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.kursy = {}
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Konwerter Walut')

        layout = QVBoxLayout()

        self.amountEdit = QLineEdit(self)
        self.amountEdit.setPlaceholderText('Wprowadź kwotę')
        layout.addWidget(self.amountEdit)

        self.sourceCurrencyComboBox = QComboBox(self)
        self.targetCurrencyComboBox = QComboBox(self)
        waluty = ['PLN', 'EUR', 'USD', 'CHF', 'GBP']
        self.sourceCurrencyComboBox.addItems(waluty)
        self.targetCurrencyComboBox.addItems(waluty)
        layout.addWidget(self.sourceCurrencyComboBox)
        layout.addWidget(self.targetCurrencyComboBox)

        self.convertButton = QPushButton('Konwertuj', self)
        self.convertButton.clicked.connect(self.on_convert)
        layout.addWidget(self.convertButton)

        self.resultLabel = QLabel('')
        layout.addWidget(self.resultLabel)

        self.setLayout(layout)
        self.setGeometry(300, 300, 350, 200)

    def on_convert(self):
        try:
            kwota = float(self.amountEdit.text())
            if not self.kursy:
                self.kursy = pobierz_kursy()
            waluta_zrodlowa = self.sourceCurrencyComboBox.currentText()
            waluta_docelowa = self.targetCurrencyComboBox.currentText()
            kurs_zrodlowy = self.kursy.get(waluta_zrodlowa, 1)
            kurs_docelowy = self.kursy.get(waluta_docelowa, 1)
            wynik = konwertuj(kwota, kurs_zrodlowy, kurs_docelowy)
            self.resultLabel.setText(f"{kwota:.2f} {waluta_zrodlowa} to {wynik:.2f} {waluta_docelowa}")
        except ValueError:
            self.resultLabel.setText("Proszę wprowadzić poprawną kwotę.")

def main():
    app = QApplication(sys.argv)
    ex = CurrencyConverter()
    ex.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()