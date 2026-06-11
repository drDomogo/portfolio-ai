import json
from pathlib import Path

from main_portfolio import (BASE_DIR)
#BASE_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = BASE_DIR / "analysis"
OUTPUT_INDEX = BASE_DIR / "analysis_index.json"


def build_portfolio_index():
    portfolio_index = []

    # Przechodzimy przez wszystkie foldery wewnątrz 'analysis'
    if not ANALYSIS_DIR.exists():
        print("Błąd: Folder 'analysis' nie istnieje!")
        return

    for company_dir in ANALYSIS_DIR.iterdir():
        if company_dir.is_dir():
            ticker = company_dir.name
            # Definiujemy bezpośrednią ścieżkę do stałego pliku JSON
            json_file = company_dir / "ai-comment.json"

            if json_file.exists():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    portfolio_index.append({
                        "ticker": ticker,
                        "short_name": data.get("short_name", ticker),
                        "verdict": data.get("final_verdict", "TRZYMAJ"),
                        "price": data.get("current_price", "--"),
                        "currency": data.get("currency", ""),
                        "filePath": f"analysis/{ticker}/ai-comment.json",
                        "folderPath": f"analysis/{ticker}"
                    })
                    print(f"Zindeksowano: {ticker}")
                except Exception as e:
                    print(f"Błąd indeksowania {ticker}: {e}")

    # Zapisujemy plik indeksu w katalogu głównym witryny
    with open(OUTPUT_INDEX, "w", encoding="utf-8") as out_f:
        json.dump(portfolio_index, out_f, ensure_ascii=False, indent=4)
    print(f"\nSukces! Utworzono plik indeksu: {OUTPUT_INDEX}")


if __name__ == "__main__":
    build_portfolio_index()