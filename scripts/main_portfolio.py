import time
import random
from pathlib import Path
import pandas as pd
import yfinance as yf
import wx
import matplotlib
matplotlib.use('Agg')        # <<< NAJWAŻNIEJSZA LINIA
import matplotlib.pyplot as plt

# Import z Twojego modułu
from stock_research_automate import (
    OUTPUT_DIR,
    process_ticker,
    create_technical_chart
)

# =====================================================
# KONFIGURACJA PORTFELA
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Listy klasyfikacji aktywów
TECH_ONLY_TICKERS = ["EIMI.L", "IWDA.L", "UDVD.L", "GC=F", "BTC-USD", "SOL-USD"]
IGNORE_TICKERS = ["none", "RNDR-USD", "USDPLN=X", "EURPLN=X", "IB01.L"]


def select_portfolio_file():
    """Wyświetla okno dialogowe do wyboru pliku Excel."""
    app = wx.App(False)  # Tworzymy instancję aplikacji wx (bez głównego okna)
    dialog = wx.FileDialog(
        None,
        message="Wybierz plik z portfelem",
        defaultDir=str(BASE_DIR / "portfolios"),
        defaultFile="portfel.xlsx",
        wildcard="Pliki Excel (*.xlsx;*.xls)|*.xlsx;*.xls|Wszystkie pliki (*.*)|*.*",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    )

    if dialog.ShowModal() == wx.ID_OK:
        path = Path(dialog.GetPath())
        dialog.Destroy()
        return path
    else:
        dialog.Destroy()
        print("Anulowano wybór pliku.")
        return None


def load_tickers_from_excel(excel_path, sheet_name="assets", column_name="ticker"):
    """Wczytuje tickery z wybranego pliku Excel."""
    if not excel_path.exists():
        print(f"Błąd: Plik '{excel_path}' nie istnieje!")
        return []

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)

        if column_name not in df.columns:
            available_cols = {col.lower(): col for col in df.columns}
            if column_name.lower() in available_cols:
                column_name = available_cols[column_name.lower()]
            else:
                print(f"Błąd: Nie znaleziono kolumny '{column_name}'.")
                print(f"Dostępne kolumny: {list(df.columns)}")
                return []

        tickers = df[column_name].dropna().astype(str).str.strip().str.upper().unique().tolist()
        return tickers

    except Exception as e:
        print(f"Wystąpił błąd podczas czytania pliku Excel: {e}")
        return []


def process_portfolio():
    """Główna funkcja sterująca procesem analizy portfela."""
    print("Otwieram okno wyboru pliku portfela...")

    excel_path = select_portfolio_file()
    if not excel_path:
        print("Nie wybrano pliku – kończę program.")
        return

    # Tworzymy dedykowany folder wyjściowy na podstawie nazwy pliku (bez rozszerzenia)
    portfolio_name = excel_path.stem  # np. "portfel_maj2026"
    output_base = OUTPUT_DIR / portfolio_name
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"Wybrano plik: {excel_path.name}")
    print(f"Wyniki będą zapisywane do: {output_base}")
    print(f"Znaleziono {len(load_tickers_from_excel(excel_path))} tickerów (przed filtracją).")
    print("-" * 60)

    tickers = load_tickers_from_excel(excel_path)

    if not tickers:
        print("Brak tickerów do przetworzenia.")
        return

    for symbol in tickers:
        symbol_lower = symbol.lower()

        if symbol_lower in [t.lower() for t in IGNORE_TICKERS]:
            print(f"Ignoruję: {symbol} (Lista IGNORE)")
            continue

        # Folder dla konkretnego aktywa wewnątrz folderu portfela
        company_dir = output_base / symbol
        company_dir.mkdir(parents=True, exist_ok=True)

        ticker_obj = yf.Ticker(symbol)

        if symbol in TECH_ONLY_TICKERS:
            print(f"Przetwarzam (Tylko Techniczna): {symbol}")
            try:
                create_technical_chart(ticker_obj, company_dir)
            except Exception as e:
                print(f"Błąd technicznej analizy dla {symbol}: {e}")
        else:
            print(f"Przetwarzam (Pełna analiza): {symbol}")
            try:
                process_ticker(symbol, output_dir=output_base)  # <-- najważniejsze
            except Exception as e:
                print(f"❌ BŁĄD przy {symbol}: {e}")

        # Anty-ban delay
        delay = random.uniform(3.0, 6.0)
        print(f"Oczekiwanie {delay:.2f} s...")
        time.sleep(delay)

    print("\nPrzetwarzanie całego portfela zakończone sukcesem!")
    print(f"Wszystkie wyniki zapisano w: {output_base}")


if __name__ == "__main__":
    process_portfolio()