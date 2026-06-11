import os
import time
import random
from pathlib import Path
from datetime import datetime
from google import genai
from google.genai import types
from google.genai import errors
from schemas import PortfolioAnalysisReport

# Reużywamy konfiguracji i funkcji ładowania tickerów z istniejącego modułu
from main_portfolio import (
    BASE_DIR,
    SHEET_NAME,
    TICKER_COLUMN,
    TECH_ONLY_TICKERS,
    IGNORE_TICKERS,
    load_tickers_from_excel
)

# =====================================================
# KONFIGURACJA ŚCIEŻEK I AI
# =====================================================
# Nowy plik wejściowy z listą tickerów do analizy AI
INPUT_EXCEL_PATH = BASE_DIR / "portfolios" / "to_ai_analysis.xlsx"
ANALYSIS_DIR = BASE_DIR / "analysis"
PROMPTS_DIR = BASE_DIR / "prompts"

MODEL_NAME = "gemini-2.5-flash" # "gemini-2.5-pro"

# Mechanizm ograniczenia tokenów (None = brak ograniczenia / domyślne modelu)
MAX_OUTPUT_TOKENS = None  # Możesz tu wpisać np. 2048, aby aktywować limit


def read_text_file(path: Path) -> str:
    """Pomocnicza funkcja do bezpiecznego wczytywania plików tekstowych/markdown."""
    if not path.exists():
        raise FileNotFoundError(f"Brak wymaganego pliku promptu: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run_ai_analysis():
    """Główna funkcja uruchomieniowa potoku analizy AI."""
    print(f"Rozpoczynam proces analizy AI za pomocą modelu {MODEL_NAME}...")

    # Inicjalizacja klienta Gemini (pobiera klucz ze zmiennej środowiskowej GEMINI_API_KEY)
    gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    # Wczytanie tickerów z dedykowanego pliku Excel
    tickers = load_tickers_from_excel(INPUT_EXCEL_PATH, SHEET_NAME, TICKER_COLUMN)

    if not tickers:
        print("Koniec programu: Brak tickerów do przetworzenia.")
        return

    print(f"Znaleziono {len(tickers)} tickerów w {INPUT_EXCEL_PATH.name}. Rozpoczynam przetwarzanie...")
    print("-" * 60)

    # Dzisiejsza data do formatowania nazwy pliku wynikowego
    today_str = datetime.now().strftime("%Y-%m-%d")

    for symbol in tickers:
        symbol_upper = symbol.strip().upper()
        symbol_lower = symbol.strip().lower()

        # 1. Filtrowanie: Ignorowane tickery
        if symbol_lower in [t.lower() for t in IGNORE_TICKERS]:
            print(f"Ignoruję: {symbol_upper} (Lista IGNORE)")
            continue

        # Definiujemy folder dedykowany dla danej spółki
        company_dir = ANALYSIS_DIR / symbol_upper
        if not company_dir.exists():
            print(f"Pominięto {symbol_upper}: Folder danych wejściowych '{company_dir}' nie istnieje!")
            continue

        # Definiowanie ścieżek do potencjalnych plików załączników
        price_history_path = company_dir / "price_history.csv"
        company_data_path = company_dir / "company_data.json"

        # 2. Selekcja ścieżki promptów oraz załączników w zależności od typu aktywa
        if symbol_upper in [t.upper() for t in TECH_ONLY_TICKERS]:
            print(f"Klasyfikacja: {symbol_upper} -> Analiza TECHNICZNA")
            prompt_subfolder = "technical-analysis"
            required_files = [price_history_path]
        else:
            print(f"Klasyfikacja: {symbol_upper} -> Pełna analiza FUNDAMENTALNA + TECHNICZNA")
            prompt_subfolder = "full-analysis"
            required_files = [company_data_path, price_history_path]

        # Budowanie ścieżek do plików promptów
        system_prompt_path = PROMPTS_DIR / prompt_subfolder / "system.md"
        user_prompt_path = PROMPTS_DIR / prompt_subfolder / "user.md"

        try:
            # Wczytywanie instrukcji systemowych i promptu użytkownika
            system_prompt = read_text_file(system_prompt_path)
            user_prompt = read_text_file(user_prompt_path)

            # Budowanie paczki zawartości (contents) dla Gemini API
            contents = []
            for file_path in required_files:
                if not file_path.exists():
                    raise FileNotFoundError(f"Brak wymaganego pliku danych: {file_path}")

                # było:  file_content = read_text_file(file_path)
                # zamienione na (redukcja wierszy):
                if file_path.suffix == '.csv':
                    # Wczytaj za pomocą pandas i weź np. co trzeci wiersz, żeby zmniejszyć payload o 66%
                    # bez utraty trendu rynkowego
                    import pandas as pd
                    df_temp = pd.read_csv(file_path)
                    # Bierzemy co 3 wiersz, zachowując nagłówki
                    df_reduced = df_temp.iloc[::3]
                    file_content = df_reduced.to_csv(index=False)
                else:
                    file_content = read_text_file(file_path)

                filename = file_path.name
                contents.append(f"--- ZAŁĄCZNIK: {filename} ---\n{file_content}\n\n")
                print(f" -> Dołączono plik: {filename}")

            # Na końcu dodajemy właściwe zapytanie użytkownika
            contents.append(user_prompt)

            # Konfiguracja parametrów generowania z wymuszeniem struktury JSON
            config_params = {
                "system_instruction": system_prompt,
                "temperature": 0.2,
                "response_mime_type": "application/json",
                "response_schema": PortfolioAnalysisReport,  # Podajemy naszą klasę Pydantic
            }
            if MAX_OUTPUT_TOKENS is not None:
                config_params["max_output_tokens"] = MAX_OUTPUT_TOKENS
            if MAX_OUTPUT_TOKENS is not None:
                config_params["max_output_tokens"] = MAX_OUTPUT_TOKENS

            # Wywołanie API Gemini z wbudowanym mechanizmem ponawiania prób (znanym z prompt_composer)
            max_retries = 3
            ai_response_text = None

            for attempt in range(max_retries):
                try:
                    print(f" -> Wysyłanie zapytania do Gemini... Próba {attempt + 1}/{max_retries}")
                    response = gemini_client.models.generate_content(
                        model=MODEL_NAME,
                        contents=contents,
                        config=types.GenerateContentConfig(**config_params),
                    )
                    ai_response_text = response.text
                    break  # Sukces, przerywamy pętlę retry

                except (errors.ClientError, errors.ServerError) as e:
                    if hasattr(e, 'code') and e.code in [429, 503]:
                        if attempt < max_retries - 1:
                            print(f" -> Kod {e.code} (Limit/Przeciążenie). Oczekiwanie 10s...")
                            time.sleep(10)
                            continue
                    raise e

            if not ai_response_text:
                raise Exception("Nie udało się uzyskać odpowiedzi z modelu Gemini.")

            # 3. Zapis raportu w formacie JSON w folderze spółki
            output_filename = f"ai-comment.json"
            output_file_path = company_dir / output_filename

            # Wczytujemy tekst odpowiedzi i zapisujemy jako sformatowany JSON (z wcięciami)
            import json
            json_data = json.loads(ai_response_text)

            with open(output_file_path, "w", encoding="utf-8") as out_f:
                json.dump(json_data, out_f, ensure_ascii=False, indent=4)

            print(f" SUCCESS: Raport JSON zapisany w: {output_file_path.relative_to(BASE_DIR)}")

        except Exception as ex:
            print(f" ERROR podczas przetwarzania {symbol_upper}: {ex}")

        # Losowe opóźnienie BHP anty-ban (od 3 do 6 sekund), spójne z resztą projektu
        delay = random.uniform(3.0, 6.0)
        print(f"Oczekiwanie {delay:.2f} s przed kolejnym aktywem...")
        print("-" * 60)
        time.sleep(delay)

    print("Proces analizy portfela przez AI został zakończony!")


if __name__ == "__main__":
    run_ai_analysis()