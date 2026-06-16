import os
import time
import random
from pathlib import Path
from datetime import datetime
import wx
import pandas as pd

from google import genai
from google.genai import types
from google.genai import errors
from schemas import PortfolioAnalysisReport

# Importujemy tylko to co naprawdę potrzebne
from main_portfolio import (
    BASE_DIR,
    TECH_ONLY_TICKERS,
    IGNORE_TICKERS,
    load_tickers_from_excel   # zostawiamy, ale ulepszymy poniżej
)

# =====================================================
# KONFIGURACJA
# =====================================================

ANALYSIS_DIR = BASE_DIR / "analysis"
PROMPTS_DIR = BASE_DIR / "prompts"

MODEL_NAME = "gemini-2.5-flash"
MAX_OUTPUT_TOKENS = None


def select_portfolio_file():
    """Okno wyboru pliku Excel"""
    app = wx.App(False)
    dialog = wx.FileDialog(
        None,
        message="Wybierz plik Excel z tickerami do analizy AI",
        defaultDir=str(BASE_DIR / "portfolios"),
        defaultFile="to_ai_analysis.xlsx",
        wildcard="Pliki Excel (*.xlsx;*.xls)|*.xlsx;*.xls|Wszystkie pliki (*.*)|*.*",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    )

    if dialog.ShowModal() == wx.ID_OK:
        path = Path(dialog.GetPath())
        dialog.Destroy()
        return path
    else:
        dialog.Destroy()
        return None


def load_tickers_from_excel_flexible(excel_path, sheet_name=None, column_name=None):
    """Ulepszona wersja — bardziej odporna na brak SHEET_NAME / TICKER_COLUMN"""
    if not excel_path.exists():
        print(f"Błąd: Plik {excel_path} nie istnieje!")
        return []

    try:
        # Jeśli nie podano sheet_name → bierzemy pierwszy arkusz
        if sheet_name is None:
            xl = pd.ExcelFile(excel_path)
            sheet_name = xl.sheet_names[0]
            print(f"Nie podano nazwy arkusza → używam pierwszego: '{sheet_name}'")

        df = pd.read_excel(excel_path, sheet_name=sheet_name)

        # Jeśli nie podano column_name → szukamy kolumny z tickerami
        if column_name is None or column_name not in df.columns:
            possible_names = ["ticker", "Ticker", "symbol", "Symbol", "tickers", "Tickers"]
            for col in possible_names:
                if col in df.columns:
                    column_name = col
                    print(f"Znaleziono kolumnę z tickerami: '{column_name}'")
                    break
            else:
                # Jeśli nadal nie znaleziono — bierzemy pierwszą kolumnę
                column_name = df.columns[0]
                print(f"Nie znaleziono typowej kolumny → używam pierwszej: '{column_name}'")

        tickers = df[column_name].dropna().astype(str).str.strip().str.upper().unique().tolist()
        return tickers

    except Exception as e:
        print(f"Błąd odczytu Excela: {e}")
        return []


def run_ai_analysis():
    print("Otwieram okno wyboru pliku do analizy AI...")

    excel_path = select_portfolio_file()
    if not excel_path:
        print("Anulowano wybór pliku.")
        return

    portfolio_name = excel_path.stem
    print(f"Wybrano: {excel_path.name} → portfolio: {portfolio_name}")

    # Wczytujemy tickery (SHEET_NAME i TICKER_COLUMN są teraz opcjonalne)
    tickers = load_tickers_from_excel_flexible(excel_path)  # bez podawania sheet i column

    if not tickers:
        print("Brak tickerów do przetworzenia.")
        return

    print(f"Znaleziono {len(tickers)} tickerów. Rozpoczynam analizę AI...")
    print("-" * 70)

    today_str = datetime.now().strftime("%Y-%m-%d")

    for symbol in tickers:
        symbol_upper = symbol.strip().upper()
        symbol_lower = symbol.strip().lower()

        if symbol_lower in [t.lower() for t in IGNORE_TICKERS]:
            print(f"Ignoruję: {symbol_upper}")
            continue

        # --- TUTAJ NASTĄPIŁA ZMIANA ---
        # Ścieżka uwzględnia teraz podfolder o nazwie portfolio (np. analysis/NASDAQ_top10/NVDA)
        company_dir = ANALYSIS_DIR / portfolio_name / symbol_upper

        if not company_dir.exists():
            # Ulepszony print, żeby w logach było widać pełną ścieżkę, której brakuje
            print(f"Pominięto {symbol_upper}: Folder '{company_dir.relative_to(BASE_DIR)}' nie istnieje!")
            continue
        # ------------------------------

        price_history_path = company_dir / "price_history.csv"
        company_data_path = company_dir / "company_data.json"

        if symbol_upper in [t.upper() for t in TECH_ONLY_TICKERS]:
            print(f"→ {symbol_upper} [TECHNICZNA]")
            prompt_subfolder = "technical-analysis"
            required_files = [price_history_path]
        else:
            print(f"→ {symbol_upper} [FULL]")
            prompt_subfolder = "full-analysis"
            required_files = [company_data_path, price_history_path]

        system_prompt_path = PROMPTS_DIR / prompt_subfolder / "system.md"
        user_prompt_path = PROMPTS_DIR / prompt_subfolder / "user.md"

        try:
            system_prompt = read_text_file(system_prompt_path)
            user_prompt = read_text_file(user_prompt_path)

            contents = []
            for file_path in required_files:
                if not file_path.exists():
                    print(f"  Ostrzeżenie: Brak pliku {file_path.name}")
                    continue

                if file_path.suffix == '.csv':
                    df_temp = pd.read_csv(file_path)
                    df_reduced = df_temp.iloc[::3]
                    file_content = df_reduced.to_csv(index=False)
                else:
                    file_content = read_text_file(file_path)

                contents.append(f"--- ZAŁĄCZNIK: {file_path.name} ---\n{file_content}\n\n")

            contents.append(user_prompt)

            # === Gemini API ===
            gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

            config_params = {
                "system_instruction": system_prompt,
                "temperature": 0.2,
                "response_mime_type": "application/json",
                "response_schema": PortfolioAnalysisReport,
            }
            if MAX_OUTPUT_TOKENS:
                config_params["max_output_tokens"] = MAX_OUTPUT_TOKENS

            response = gemini_client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=types.GenerateContentConfig(**config_params),
            )

            json_data = response.text  # zakładam, że to już string JSON

            output_file_path = company_dir / f"ai-comment.json"

            import json
            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(json.loads(json_data), f, ensure_ascii=False, indent=4)

            print(f"✓ Sukces: {output_file_path.name}")

        except Exception as ex:
            print(f"✗ BŁĄD przy {symbol_upper}: {ex}")

        delay = random.uniform(3.0, 6.0)
        print(f"Oczekiwanie {delay:.2f}s...")
        time.sleep(delay)

    print("\nAnaliza AI zakończona!")

def read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Brak pliku: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    run_ai_analysis()