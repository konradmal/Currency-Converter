import sys
from PyQt6.QtWidgets import QApplication
from currency_converter import CurrencyConverter
import getApi

def main():
    app = QApplication(sys.argv)
    api_key = getApi.getApi()
    ex = CurrencyConverter(api_key)
    ex.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()