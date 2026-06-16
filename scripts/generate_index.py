import json
from pathlib import Path

from main_portfolio import BASE_DIR

# BASE_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = BASE_DIR / "analysis"
OUTPUT_INDEX = BASE_DIR / "analysis_index.json"


def build_portfolio_index():
    portfolio_index = []

    if not ANALYSIS_DIR.exists():
        print("Błąd: Folder 'analysis' nie istnieje!")
        return

    print(f"Rozpoczynam skanowanie katalogu: {ANALYSIS_DIR}\n" + "-" * 50)

    # Bezpieczne pobranie wszystkich elementów wewnątrz 'analysis'
    try:
        group_dirs = list(ANALYSIS_DIR.iterdir())
    except Exception as e:
        print(f"Błąd krytyczny podczas odczytu folderu analysis: {e}")
        return

    for group_dir in group_dirs:
        # Ignorujemy pliki ukryte i systemowe (np. .DS_Store, desktop.ini)
        if group_dir.name.startswith('.'):
            continue

        if group_dir.is_dir():
            group_name = group_dir.name
            print(f"Sprawdzam grupę: {group_name}")

            # Bezpieczne pobranie zawartości folderu grupy
            try:
                company_dirs = list(group_dir.iterdir())
            except Exception as e:
                print(f"  [BŁĄD] Nie można otworzyć katalogu grupy {group_name}: {e}")
                continue

            has_companies = False
            for company_dir in company_dirs:
                if company_dir.is_dir() and not company_dir.name.startswith('.'):
                    ticker = company_dir.name
                    json_file = company_dir / "ai-comment.json"

                    if json_file.exists():
                        try:
                            with open(json_file, "r", encoding="utf-8") as f:
                                data = json.load(f)

                            portfolio_index.append({
                                "group": group_name,
                                "ticker": ticker,
                                "short_name": data.get("short_name", ticker),
                                "verdict": data.get("final_verdict", "TRZYMAJ"),
                                "price": data.get("current_price", "--"),
                                "currency": data.get("currency", ""),
                                "filePath": f"analysis/{group_name}/{ticker}/ai-comment.json",
                                "folderPath": f"analysis/{group_name}/{ticker}"
                            })
                            print(f"  -> Zindeksowano: {ticker}")
                            has_companies = True
                        except Exception as e:
                            print(f"  [BŁĄD] Błąd indeksowania {ticker} w [{group_name}]: {e}")
                    else:
                        # Informacja o braku pliku - ułatwia debugowanie
                        print(f"  [INFO] Pominięto {ticker} (brak pliku ai-comment.json)")

            if not has_companies:
                print(f"  [UWAGA] Grupa '{group_name}' nie zawierała żadnych poprawnych analiz.")
        else:
            print(f"Pominięto plik (to nie jest katalog): {group_dir.name}")

    # Zapisujemy plik indeksu
    print("-" * 50)
    try:
        with open(OUTPUT_INDEX, "w", encoding="utf-8") as out_f:
            json.dump(portfolio_index, out_f, ensure_ascii=False, indent=4)
        print(f"Sukces! Utworzono zaktualizowany plik indeksu ({len(portfolio_index)} spółek): {OUTPUT_INDEX}")
    except Exception as e:
        print(f"Błąd podczas zapisu pliku indeksu: {e}")


if __name__ == "__main__":
    build_portfolio_index()