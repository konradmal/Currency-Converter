# Import required modules
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox
from PyQt6.QtCore import QCoreApplication
from exchange_rates_api import ExchangeRatesApi

# Main class for the currency converter application
class CurrencyConverter(QWidget):
    # Initialize the application with an API key
    def __init__(self, api_key):
        super().__init__()
        self.api = ExchangeRatesApi(api_key)
        self.exchange_rates = self.api.fetch_exchange_rates()
        self.initialize_ui()
        self.last_converted_value = None
        self.last_update_date = ""

    # Set up the initial user interface
    def initialize_ui(self):
        self.setWindowTitle('Currency Converter')
        self.setStyleSheet("font-family: Arial; background-color: #F5F5F5;")
        self.setup_layout()
        self.center_window()
    
    # Centers the window on the screen based on the screen's available geometry.
    def center_window(self):
        screen = QCoreApplication.instance().primaryScreen()
        rect = screen.availableGeometry()
        center_point = rect.center()
        self.setGeometry(center_point.x() - self.width() // 2, center_point.y() - self.height() // 2, self.width(), self.height())

    # Define the layout of the user interface
    def setup_layout(self):
        layout = QVBoxLayout()
        self.setup_input_widgets(layout)
        self.setup_result_label(layout)
        self.setLayout(layout)
        self.setGeometry(0, 0, 420, 230)
        self.setup_swap_button(layout)

    # Set up input widgets for the user interface
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

    # Set up the result label for the user interface
    def setup_result_label(self, layout):
        self.resultLabel = QLabel('')
        self.resultLabel.setStyleSheet("color: #333333; font-size: 18px;")
        layout.addWidget(self.resultLabel)

    # Create a line edit widget
    def create_line_edit(self, placeholder, style):
        line_edit = QLineEdit(self)
        line_edit.setPlaceholderText(placeholder)
        line_edit.setStyleSheet(style)
        return line_edit

    # Create a combo box widget
    def create_combo_box(self, items, style):
        combo_box = QComboBox(self)
        combo_box.addItems(items)
        combo_box.setStyleSheet(style)
        return combo_box

    # Create a button widget
    def create_button(self, text, style):
        button = QPushButton(text, self)
        button.setStyleSheet(style)
        button.clicked.connect(self.on_convert)
        return button
    
    # Set up the swap button
    def setup_swap_button(self, layout):
        self.swapButton = self.create_button('Swap', "background-color: #2196F3; color: white; font-size: 14px;")
        self.swapButton.clicked.connect(self.on_swap)
        layout.addWidget(self.swapButton)
        
    # Swap the values of source and target currency selectors
    def on_swap(self):
        source_index = self.sourceCurrencySelector.currentIndex()
        target_index = self.targetCurrencySelector.currentIndex()
        self.sourceCurrencySelector.setCurrentIndex(target_index)
        self.targetCurrencySelector.setCurrentIndex(source_index)
        if self.last_converted_value is not None:
            self.amountInput.setText(str(self.last_converted_value))
        self.on_convert()

    # Handle the conversion process when the convert button is clicked
    def on_convert(self):
        input_text = self.amountInput.text().strip()
        if not input_text:
            self.resultLabel.setText("Please enter an amount to convert.")
            return
        try:
            self.exchange_rates, self.last_update_date = self.api.fetch_exchange_rates()  # Zaktualizuj, aby otrzymać datę
            amount = float(input_text)
            source_currency = self.sourceCurrencySelector.currentText()
            target_currency = self.targetCurrencySelector.currentText()
            result = self.convert_currency(amount, source_currency, target_currency)
            exchange_rate = self.exchange_rates.get(target_currency) / self.exchange_rates.get(source_currency)
            self.resultLabel.setText(f"{amount:.2f} <b>{source_currency}</b> = {result:.2f} <b>{target_currency}</b><br>Rate 1 <b>{source_currency}</b> = 1 {exchange_rate:.4f} <b>{target_currency}</b><br>According to the exchange rate from {self.last_update_date}")
        except ValueError:
            self.resultLabel.setText("Please enter a valid amount.")

    # Perform the currency conversion calculation
    def convert_currency(self, amount, source_currency, target_currency):
        source_rate = self.exchange_rates.get(source_currency, 1)
        target_rate = self.exchange_rates.get(target_currency, 1)
        return amount * (target_rate / source_rate)