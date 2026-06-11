# Portfolio AI

Repozytorium promptów do analizowania spółek.

## Struktura

prompts/     - prompty
portfolios/  - listy spółek
outputs/     - wygenerowane raporty


Uruchom: 
1. main_portfolio.py - pobiera aktualne dane z yfinance (na podstawie portfolio.xlsx) , rysuje wykresy, generuje pliki company_data.json i price_history.csv
2. ai_portfolio_analyser.py - wysyła zapytania do Gemini (na podstawie to_ai_analysis.xlsx), tworzy pliki ai-comment.json
3. generate_index.py - tworzy analysis_index.json
4. żeby zupdatować zawartość strony internetowej skopiuj analysis_index.json oraz cały folder analysis do repozytorium strony