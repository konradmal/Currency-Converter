import sys

from PyQt6.QtWidgets import QApplication

from currency_converter import CurrencyConverter
import get_api


def main() -> None:
    """Entry point for the currency converter GUI application."""
    app = QApplication(sys.argv)
    api_key = get_api.get_api()
    window = CurrencyConverter(api_key)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
