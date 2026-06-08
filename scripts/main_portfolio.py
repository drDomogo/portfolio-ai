import time
import random
from pathlib import Path
import pandas as pd
import yfinance as yf

# Importujemy potrzebne funkcje i zmienne z Twojego poprzedniego modułu
from stock_research_automate import (
    OUTPUT_DIR,
    process_ticker,  # Przetwarza pełny pakiet (JSON + 2 Wykresy)
    create_technical_chart  # Generuje TYLKO analizę techniczną (CSV + Wykres)
)

# =====================================================
# KONFIGURACJA PORTFELA
# =====================================================

# Wyznaczamy główny folder projektu 'portfolio-ai' relatywnie do tego skryptu
BASE_DIR = Path(__file__).resolve().parent.parent

# Ścieżka względna do pliku Excel
EXCEL_PATH = BASE_DIR / "portfolios" / "portfel.xlsx"

SHEET_NAME = "assets"  # Nazwa zakładki
TICKER_COLUMN = "ticker"  # Nazwa kolumny z tickerami w Excelu

# Listy klasyfikacji aktywów
TECH_ONLY_TICKERS = ["GC=F", "BTC-USD", "SOL-USD"]
IGNORE_TICKERS = ["none", "RNDR-USD", "USDPLN=X", "EURPLN=X", "IB01.L"]


def load_tickers_from_excel(excel_path, sheet_name, column_name):
    """
    Wczytuje tickery z określonej kolumny i zakładki pliku Excel.
    """
    if not excel_path.exists():
        print(f"Błąd: Plik Excel '{excel_path}' nie istnieje!")
        return []

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)

        if column_name not in df.columns:
            # Próba dopasowania wielkości liter, gdyby w Excelu było "Ticker" zamiast "ticker"
            available_cols = {col.lower(): col for col in df.columns}
            if column_name.lower() in available_cols:
                column_name = available_cols[column_name.lower()]
            else:
                print(f"Błąd: Nie znaleziono kolumny '{column_name}' w zakładce '{sheet_name}'.")
                print(f"Dostępne kolumny: {list(df.columns)}")
                return []

        # Pobranie unikalnych, niepustych wartości, oczyszczonych ze spacji
        #tickers = df[column_name].dropna().astype(str).str.strip().unique().tolist()
        tickers = df[column_name].dropna().astype(str).str.strip().str.upper().unique().tolist()
        return tickers

    except Exception as e:
        print(f"Wystąpił błąd podczas czytania pliku Excel: {e}")
        return []


def process_portfolio():
    """
    Główna funkcja sterująca procesem analizy portfela.
    """
    print("Rozpoczynam wczytywanie portfela...")
    tickers = load_tickers_from_excel(EXCEL_PATH, SHEET_NAME, TICKER_COLUMN)

    if not tickers:
        print("Koniec programu: Brak tickerów do przetworzenia.")
        return

    print(f"Znaleziono {len(tickers)} tickerów w portfelu. Rozpoczynam selekcję...")
    print("-" * 50)

    for symbol in tickers:
        # Standaryzacja tekstu (w ignorowanych mamy małe 'none', ujednolicamy poronanie)
        symbol_lower = symbol.lower()

        # 1. Sprawdzenie listy ignorowanej
        if symbol_lower in [t.lower() for t in IGNORE_TICKERS]:
            print(f"Ignoruję: {symbol} (Lista IGNORE)")
            continue

        # Tworzenie dedykowanego folderu dla aktywa (zgodnie z poprzednią architekturą)
        company_dir = OUTPUT_DIR / symbol
        company_dir.mkdir(parents=True, exist_ok=True)
        ticker_obj = yf.Ticker(symbol)

        # 2. Sprawdzenie aktywów TYLKO do analizy technicznej (Kryptowaluty, Złoto)
        if symbol in TECH_ONLY_TICKERS:
            print(f"Przetwarzam (Tylko Techniczna): {symbol}")
            try:
                create_technical_chart(ticker_obj, company_dir)
            except Exception as e:
                print(f"Błąd podczas generowania analizy technicznej dla {symbol}: {e}")

        # 3. Standardowe spółki giełdowe (Pełna analiza)
        else:
            # Wywołujemy gotową, kompletną funkcję z Twojego głównego skryptu
            process_ticker(symbol)

        # Losowe opóźnienie BHP anty-ban (3 do 6 sekund)
        delay = random.uniform(3.0, 6.0)
        print(f"Oczekiwanie {delay:.2f} s przed kolejnym aktywem...")
        print("-" * 30)
        time.sleep(delay)

    print("Przetwarzanie całego portfela zakończone sukcesem!")


if __name__ == "__main__":
    process_portfolio()