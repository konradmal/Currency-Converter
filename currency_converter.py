from typing import Dict, Optional, List

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QFrame,
)
from PyQt6.QtCore import Qt

from exchange_rates_api import ExchangeRatesApi
import re

# Matplotlib is optional; we try to import it for charts.
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except Exception:  # ImportError or backend issues
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = None
    Figure = None


# A dictionary mapping ISO currency codes to their respective symbols
# for display purposes.
currency_symbols: Dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "PLN": "zł",
    "GBP": "£",
    "CHF": "CHF",
}


class RatesChartWindow(QWidget):
    """Window responsible only for displaying the historical rate chart.

    It is created when the user clicks "Show chart" in the main converter
    window. The user can close this window with the "Back" button or the
    standard window close button.
    """

    def __init__(
        self,
        history: List[dict],
        source_currency: str,
        target_currency: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(f"Rate history: {source_currency} → {target_currency}")
        # Make the window larger so the chart is easier to read.
        self.resize(900, 550)

        # Main vertical layout: message / chart / buttons.
        layout = QVBoxLayout(self)

        # Fallback when Matplotlib is not installed or backend is unavailable.
        if not MATPLOTLIB_AVAILABLE or Figure is None or FigureCanvas is None:
            info = QLabel("Matplotlib is not available. Install it to see charts.")
            info.setWordWrap(True)
            layout.addWidget(info)
            return

        # Create the figure and canvas with a larger logical size.
        figure = Figure(figsize=(8.0, 4.5))
        self.canvas = FigureCanvas(figure)
        layout.addWidget(self.canvas)

        ax = figure.add_subplot(111)

        dates: List[str] = []
        values: List[float] = []

        # Build the time series: for each snapshot we compute
        #   target_per_source = rate[target] / rate[source]
        # which is "how many units of target currency you get for 1 source".
        for idx, snap in enumerate(history):
            date = str(snap.get("date", idx + 1))
            rates = snap.get("rates", {})
            if (
                not isinstance(rates, dict)
                or source_currency not in rates
                or target_currency not in rates
            ):
                continue
            try:
                value = float(rates[target_currency]) / float(rates[source_currency])
            except Exception:
                # Ignore broken entries instead of crashing the whole chart.
                continue
            dates.append(date)
            values.append(value)

        if not dates or not values:
            # When there is no usable data for this pair we show a clear message
            # instead of an empty or misleading chart.
            ax.text(0.5, 0.5, "No data for the selected currency pair.", ha="center", va="center")
        else:
            ax.plot(dates, values, marker="o")
            ax.set_xlabel("Date")
            ax.set_ylabel(f"{target_currency} per {source_currency}")
            ax.set_title(f"History: {source_currency} → {target_currency}")
            ax.grid(True)

        figure.tight_layout()
        self.canvas.draw()

        # Simple horizontal bar with a "Back" button below the chart.
        # It only closes this window; the main converter stays open.
        buttons_layout = QHBoxLayout()
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.close)
        buttons_layout.addStretch()
        buttons_layout.addWidget(back_button)
        layout.addLayout(buttons_layout)


class CurrencyConverter(QWidget):
    """GUI application for converting between currencies.

    This version focuses on a user-friendly layout and visual design,
    and adds an optional chart showing historical rate changes based
    on the locally stored history.
    """

    def __init__(self, api_key: str) -> None:
        super().__init__()

        self.api = ExchangeRatesApi(api_key)
        self.exchange_rates: Dict[str, float] = {}
        self.last_update_date: str = ""
        self.last_converted_value: Optional[float] = None
        # Reference to the last opened chart window. It is reused each time
        # the user requests a chart for some pair.
        self.chart_window: Optional[RatesChartWindow] = None

        self._init_ui()
        self._load_initial_rates()

    # ------------------------------------------------------------------
    # UI SETUP
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        """Build and configure the main converter window UI."""
        self.setWindowTitle("Currency Converter")
        self.resize(600, 440)
        self.setMinimumWidth(480)

        # Global style (simple dark theme)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #0f172a;
                color: #e5e7eb;
                font-family: Segoe UI, Arial;
                font-size: 14px;
            }
            QLineEdit, QComboBox {
                background-color: #020617;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 6px 8px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #38bdf8;
            }
            QPushButton {
                border-radius: 6px;
                padding: 6px 14px;
                background-color: #0ea5e9;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
            QPushButton#secondaryButton {
                background-color: #1e293b;
                color: #e5e7eb;
                font-weight: 500;
            }
            QPushButton#secondaryButton:hover {
                background-color: #111827;
            }
            QFrame#card {
                background-color: #020617;
                border: 1px solid #1f2937;
                border-radius: 10px;
            }
            """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header with title and short description.
        header_layout = QVBoxLayout()
        title_label = QLabel("Currency Converter")
        title_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        subtitle_label = QLabel("Fast and simple conversion between popular currencies.")
        subtitle_label.setStyleSheet("color: #9ca3af;")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addSpacing(4)
        main_layout.addLayout(header_layout)

        # Input "card" with amount and currency selectors.
        input_card = QFrame()
        input_card.setObjectName("card")
        input_layout = QGridLayout(input_card)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setVerticalSpacing(8)

        amount_label = QLabel("Amount")
        self.amountInput = QLineEdit()
        self.amountInput.setPlaceholderText("e.g. 100.50")
        # Pressing Enter in the amount field triggers a conversion.
        self.amountInput.returnPressed.connect(self.on_convert)

        from_label = QLabel("From")
        self.sourceCurrencySelector = QComboBox()

        to_label = QLabel("To")
        self.targetCurrencySelector = QComboBox()

        input_layout.addWidget(amount_label, 0, 0)
        input_layout.addWidget(self.amountInput, 0, 1, 1, 3)

        input_layout.addWidget(from_label, 1, 0)
        input_layout.addWidget(self.sourceCurrencySelector, 1, 1)

        input_layout.addWidget(to_label, 1, 2)
        input_layout.addWidget(self.targetCurrencySelector, 1, 3)

        # Buttons row inside the card: main actions + chart + refresh.
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        self.convertButton = self._create_button("Convert", self.on_convert)
        self.swapButton = self._create_button("Swap", self.on_swap, "secondaryButton")
        self.clearButton = self._create_button("Clear", self.on_clear, "secondaryButton")
        self.refreshButton = self._create_button("Refresh rates", self.on_refresh_rates, "secondaryButton")
        self.chartButton = self._create_button("Show chart", self.on_show_chart, "secondaryButton")

        buttons_layout.addWidget(self.convertButton)
        buttons_layout.addWidget(self.swapButton)
        buttons_layout.addWidget(self.clearButton)
        buttons_layout.addWidget(self.chartButton)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.refreshButton)

        input_layout.addLayout(buttons_layout, 2, 0, 1, 4)

        main_layout.addWidget(input_card)

        # Result "card": main conversion line + extra details.
        result_card = QFrame()
        result_card.setObjectName("card")
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(12, 12, 12, 12)
        result_layout.setSpacing(6)

        result_caption = QLabel("Result")
        result_caption.setStyleSheet("font-size: 13px; color: #9ca3af;")

        self.resultMainLabel = QLabel("No conversion yet.")
        self.resultMainLabel.setStyleSheet("font-size: 20px; font-weight: 600;")
        self.resultDetailsLabel = QLabel("")
        self.resultDetailsLabel.setStyleSheet("color: #9ca3af;")
        self.resultDetailsLabel.setWordWrap(True)

        result_layout.addWidget(result_caption)
        result_layout.addWidget(self.resultMainLabel)
        result_layout.addWidget(self.resultDetailsLabel)

        main_layout.addWidget(result_card)

        # Status and last update (footer).
        footer_layout = QHBoxLayout()
        self.lastUpdateLabel = QLabel("")
        self.lastUpdateLabel.setStyleSheet("color: #9ca3af; font-size: 12px;")

        self.statusLabel = QLabel("")
        self.statusLabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        footer_layout.addWidget(self.lastUpdateLabel)
        footer_layout.addStretch()
        footer_layout.addWidget(self.statusLabel)
        main_layout.addLayout(footer_layout)

        self._set_status("", error=False)
        self._populate_currency_selectors()

    def _set_status(self, text: str, error: bool = False) -> None:
        """Show a short status message in the footer."""
        if error:
            self.statusLabel.setStyleSheet("color: #fca5a5; font-size: 12px;")
        else:
            self.statusLabel.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.statusLabel.setText(text)

    def _create_button(self, text: str, callback, object_name: Optional[str] = None) -> QPushButton:
        """Create a QPushButton with an optional object name and connect it."""
        button = QPushButton(text, self)
        if object_name:
            button.setObjectName(object_name)
        button.clicked.connect(callback)
        return button

    def _populate_currency_selectors(self) -> None:
        """Fill the currency combo boxes with available currency codes."""
        self.sourceCurrencySelector.clear()
        self.targetCurrencySelector.clear()

        for code, symbol in currency_symbols.items():
            label = f"{code} ({symbol})"
            self.sourceCurrencySelector.addItem(label)
            self.targetCurrencySelector.addItem(label)

        # Set some reasonable defaults if available.
        usd_label = "USD ($)"
        eur_label = "EUR (€)"

        usd_index = self.sourceCurrencySelector.findText(usd_label)
        eur_index = self.targetCurrencySelector.findText(eur_label)

        if usd_index >= 0:
            self.sourceCurrencySelector.setCurrentIndex(usd_index)
        if eur_index >= 0:
            self.targetCurrencySelector.setCurrentIndex(eur_index)

    # ------------------------------------------------------------------
    # DATA LOADING
    # ------------------------------------------------------------------
    def _load_initial_rates(self) -> None:
        """Attempt to load exchange rates at application start."""
        try:
            self.exchange_rates, self.last_update_date = self.api.fetch_exchange_rates()
            if self.last_update_date:
                self.lastUpdateLabel.setText(f"Rates date: {self.last_update_date}")
            else:
                self.lastUpdateLabel.setText("Rates loaded.")
            self._set_status("Exchange rates loaded.", error=False)
        except Exception as exc:
            self.exchange_rates = {}
            self.last_update_date = ""
            self.lastUpdateLabel.setText("Rates could not be loaded.")
            self._set_status(f"Cannot load exchange rates: {exc}", error=True)

    def on_refresh_rates(self) -> None:
        """Reload exchange rates and optionally re-run the last conversion."""
        self._load_initial_rates()
        if self.amountInput.text().strip():
            # If there is an amount present, try to convert again with fresh rates.
            self.on_convert()

    # ------------------------------------------------------------------
    # MAIN ACTIONS
    # ------------------------------------------------------------------
    def on_convert(self) -> None:
        """Handle the Convert button click."""
        raw_text = self.amountInput.text().strip()
        if not raw_text:
            self._set_status("Please enter an amount.", error=True)
            return

        normalized_text = raw_text.replace(",", ".")
        try:
            amount = float(normalized_text)
        except ValueError:
            self._set_status("Please enter a valid number.", error=True)
            return

        source_label = self.sourceCurrencySelector.currentText()
        target_label = self.targetCurrencySelector.currentText()
        source_currency = self.extract_currency_code(source_label)
        target_currency = self.extract_currency_code(target_label)

        if not self.exchange_rates:
            # Try once more to fetch rates if they are not available yet.
            try:
                self.exchange_rates, self.last_update_date = self.api.fetch_exchange_rates()
                if self.last_update_date:
                    self.lastUpdateLabel.setText(f"Rates date: {self.last_update_date}")
            except Exception as exc:
                self._set_status(f"Cannot convert – cannot load exchange rates: {exc}", error=True)
                return

        try:
            result = self.convert_currency(amount, source_currency, target_currency)
        except KeyError:
            self._set_status("Cannot convert – missing exchange rate for selected currency.", error=True)
            self.resultMainLabel.setText("Conversion failed.")
            self.resultDetailsLabel.setText("Selected currency is not available in the current rates.")
            return
        except ZeroDivisionError:
            self._set_status("Cannot convert – invalid source exchange rate (zero).", error=True)
            self.resultMainLabel.setText("Conversion failed.")
            self.resultDetailsLabel.setText("The exchange rate for the source currency is equal to 0.")
            return

        self.last_converted_value = result

        source_rate = self.exchange_rates[source_currency]
        target_rate = self.exchange_rates[target_currency]
        exchange_rate = target_rate / source_rate

        source_symbol = currency_symbols.get(source_currency, "")
        target_symbol = currency_symbols.get(target_currency, "")

        main_line = f"{amount:.2f} {source_currency} {source_symbol} = {result:.2f} {target_currency} {target_symbol}"
        details_lines = [
            f"1 {source_currency} = {exchange_rate:.4f} {target_currency}",
        ]
        if self.last_update_date:
            details_lines.append(f"According to exchange rates from {self.last_update_date}")

        self.resultMainLabel.setText(main_line)
        self.resultDetailsLabel.setText("\n".join(details_lines))
        self._set_status("Conversion successful.", error=False)

    def on_swap(self) -> None:
        """Swap the selected source and target currencies.

        If a previous conversion result exists, use it as the new input
        amount and immediately run another conversion.
        """
        source_index = self.sourceCurrencySelector.currentIndex()
        target_index = self.targetCurrencySelector.currentIndex()

        self.sourceCurrencySelector.setCurrentIndex(target_index)
        self.targetCurrencySelector.setCurrentIndex(source_index)

        if self.last_converted_value is not None:
            # Use the previous result as the new amount.
            self.amountInput.setText(f"{self.last_converted_value:.2f}")

        if self.amountInput.text().strip():
            self.on_convert()

    def on_clear(self) -> None:
        """Clear the input and result fields."""
        self.amountInput.clear()
        self.last_converted_value = None
        self.resultMainLabel.setText("No conversion yet.")
        self.resultDetailsLabel.setText("")
        self._set_status("Cleared.", error=False)

    def on_show_chart(self) -> None:
        """Open or update a window with a chart of historical rate changes.

        The data comes from the locally stored history JSON file which
        you can build with the separate `build_history.py` script.
        """
        if not MATPLOTLIB_AVAILABLE:
            self._set_status("Matplotlib is not installed – charts are unavailable.", error=True)
            return

        # Load or create the history list from the API helper. The heavy work
        # of downloading and saving history is done outside the GUI.
        history = self.api.get_history()
        if len(history) < 2:
            self._set_status("Not enough history yet to draw a chart.", error=False)
            return

        source_label = self.sourceCurrencySelector.currentText()
        target_label = self.targetCurrencySelector.currentText()
        source_currency = self.extract_currency_code(source_label)
        target_currency = self.extract_currency_code(target_label)

        # Always create a fresh chart window so that each request uses the
        # current pair and history, and the user has a dedicated "Back" button.
        self.chart_window = RatesChartWindow(history, source_currency, target_currency, self)
        self.chart_window.show()
        self.chart_window.raise_()
        self.chart_window.activateWindow()

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    @staticmethod
    def extract_currency_code(label: str) -> str:
        """Extract a three-letter currency code from a combo-box label."""
        match = re.match(r"^([A-Z]{3})", label)
        if match:
            return match.group(1)
        return label.strip().upper()

    def convert_currency(self, amount: float, source_currency: str, target_currency: str) -> float:
        """Convert `amount` from `source_currency` to `target_currency`.

        Raises KeyError if any of the currencies is missing in the
        `exchange_rates` dictionary.
        """
        if source_currency not in self.exchange_rates or target_currency not in self.exchange_rates:
            raise KeyError("Missing exchange rate for one of the currencies.")

        source_rate = self.exchange_rates[source_currency]
        target_rate = self.exchange_rates[target_currency]

        if source_rate == 0:
            raise ZeroDivisionError("Source currency rate is zero.")

        return amount * (target_rate / source_rate)