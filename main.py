# Import required modules
import sys
from PyQt6.QtWidgets import QApplication
from currency_converter import CurrencyConverter
import get_api

# Define the main function to set up and run the application
def main():
    app = QApplication(sys.argv)
    api_key = get_api.get_api()
    ex = CurrencyConverter(api_key)
    ex.show()
    sys.exit(app.exec())

# Check if the script is run directly (not imported as a module)
# and if so, call the main function
if __name__ == '__main__':
    main()
