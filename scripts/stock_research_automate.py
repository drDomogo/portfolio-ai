import json
from pathlib import Path
import random
import time
import matplotlib
matplotlib.use('Agg')          # <<< WAŻNE - zapobiega crashowi z wxPython
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

# =====================================================
# KONFIGURACJA
# =====================================================

TICKERS = [
    "KRU.WA",
    "LPP.WA",
    "XTB.WA",
    "WWD",
]

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "analysis"          # domyślny folder (dla wstecznej kompatybilności)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================
# POMOCNICZE
# =====================================================

def get_value(df, possible_names, column):
    if df is None or df.empty:
        return None

    if isinstance(possible_names, str):
        possible_names = [possible_names]

    for name in possible_names:
        try:
            if name in df.index:
                val = df.loc[name, column]
                if pd.isna(val):
                    return None
                return val.item() if hasattr(val, "item") else val
        except Exception:
            pass
    return None


# =====================================================
# ANALIZA TECHNICZNA
# =====================================================

def create_technical_chart(ticker_obj, output_dir):
    hist = ticker_obj.history(period="1y")
    if hist.empty:
        print("Brak danych historycznych")
        return

    currency = ticker_obj.info.get("currency", "N/A")
    ticker_name = ticker_obj.ticker

    hist["SMA50"] = hist["Close"].rolling(50).mean()
    hist["SMA200"] = hist["Close"].rolling(200).mean()

    hist.to_csv(output_dir / "price_history.csv")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), height_ratios=[3, 1], sharex=True)
    fig.suptitle(f"Analiza Techniczna: {ticker_name} ({currency})", fontsize=16, fontweight="bold")

    ax1.plot(hist.index, hist["Close"], label="Close")
    ax1.plot(hist.index, hist["SMA50"], label="SMA50")
    ax1.plot(hist.index, hist["SMA200"], label="SMA200")
    ax1.set_title("Price + SMA50 + SMA200")
    ax1.legend()
    ax1.grid(True)

    ax2.bar(hist.index, hist["Volume"])
    ax2.set_title("Volume")
    ax2.grid(True)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_dir / "technical_chart.png")
    plt.close()


# =====================================================
# CURRENT SNAPSHOT (ZWRACA SŁOWNIK)
# =====================================================

def get_current_snapshot(ticker_obj):
    try:
        info = ticker_obj.info
    except Exception:
        info = {}

    # Konwersja typów numpy do natywnych pythonowych dla kompatybilności z JSON
    def clean_val(v):
        if pd.isna(v):
            return None
        return v.item() if hasattr(v, "item") else v

    return {
        "shortName": clean_val(info.get("shortName")),
        "sector": clean_val(info.get("sector")),
        "industry": clean_val(info.get("industry")),
        "country": clean_val(info.get("country")),
        "currency": clean_val(info.get("currency")),
        "currentPrice": clean_val(info.get("currentPrice")),
        "marketCap": clean_val(info.get("marketCap")),
        "trailingPE": clean_val(info.get("trailingPE")),
        "forwardPE": clean_val(info.get("forwardPE")),
        "trailingEps": clean_val(info.get("trailingEps")),
        "forwardEps": clean_val(info.get("forwardEps")),
        "pegRatio": clean_val(info.get("pegRatio")),
        "priceToBook": clean_val(info.get("priceToBook")),
        "returnOnEquity": clean_val(info.get("returnOnEquity")),
        "debtToEquity": clean_val(info.get("debtToEquity")),
        "beta": clean_val(info.get("beta")),
        "dividendYield": clean_val(info.get("dividendYield")),
        "dividendRate": clean_val(info.get("dividendRate")),
        "fiveYearAvgDividendYield": clean_val(
            info.get("fiveYearAvgDividendYield")
        ),
        "sharesOutstanding": clean_val(info.get("sharesOutstanding")),
    }


# =====================================================
# FUNDAMENTY KWARTALNE (ZWRACA LISTĘ SŁOWNIKÓW)
# =====================================================

def get_quarterly_fundamentals(ticker_obj):
    try:
        info = ticker_obj.info
    except Exception:
        info = {}

    currency = info.get("currency")
    quarterly_income = ticker_obj.quarterly_income_stmt
    quarterly_balance = ticker_obj.quarterly_balance_sheet
    quarterly_cashflow = ticker_obj.quarterly_cashflow

    if quarterly_income.empty:
        return []

    dividends = ticker_obj.dividends

    if not dividends.empty:
        dividends = dividends.copy()
        try:
            dividends.index = dividends.index.tz_localize(None)
        except Exception:
            pass

    rows = []
    quarters = quarterly_income.columns

    for q in quarters:
        quarter_end = pd.Timestamp(q).tz_localize(None)
        quarter_start = quarter_end - pd.offsets.QuarterEnd()

        revenue = get_value(quarterly_income, ["Total Revenue", "Revenue"], q)
        net_income = get_value(quarterly_income, ["Net Income", "NetIncome"], q)
        operating_income = get_value(
            quarterly_income, ["Operating Income", "OperatingIncome"], q
        )
        debt = get_value(quarterly_balance, ["Total Debt"], q)
        cash = get_value(
            quarterly_balance,
            [
                "Cash And Cash Equivalents",
                "Cash Cash Equivalents And Short Term Investments",
                "Cash",
            ],
            q
        )
        free_cash_flow = get_value(quarterly_cashflow, ["Free Cash Flow"], q)

        dividend_paid = 0
        if not dividends.empty:
            div_series = dividends[
                (dividends.index >= quarter_start)
                & (dividends.index <= quarter_end)
            ]
            dividend_paid = (
                div_series.sum().item()
                if hasattr(div_series.sum(), "item")
                else div_series.sum()
            )

        rows.append({
            "Quarter": str(quarter_end.date()),  # jako string do JSON
            "Currency": currency,
            "Revenue": revenue,
            "NetIncome": net_income,
            "OperatingIncome": operating_income,
            "Debt": debt,
            "Cash": cash,
            "FreeCashFlow": free_cash_flow,
            "DividendPaid": dividend_paid if dividend_paid != 0 else None,
        })

    rows.sort(key=lambda x: x["Quarter"])
    return rows


# =====================================================
# FUNDAMENTY ROCZNE (ZWRACA LISTĘ SŁOWNIKÓW)
# =====================================================

def get_annual_fundamentals(ticker_obj):
    try:
        info = ticker_obj.info
    except Exception:
        info = {}

    currency = info.get("currency")
    income = ticker_obj.income_stmt
    balance = ticker_obj.balance_sheet
    cashflow = ticker_obj.cashflow

    if income.empty:
        return []

    dividends = ticker_obj.dividends

    if not dividends.empty:
        dividends = dividends.copy()
        try:
            dividends.index = dividends.index.tz_localize(None)
        except Exception:
            pass

    rows = []
    years = income.columns

    for year in years:
        year_end = pd.Timestamp(year).tz_localize(None)
        year_start = pd.Timestamp(year_end.year, 1, 1)

        revenue = get_value(income, ["Total Revenue", "Revenue"], year)
        net_income = get_value(income, ["Net Income"], year)
        operating_income = get_value(income, ["Operating Income"], year)
        debt = get_value(balance, ["Total Debt"], year)
        cash = get_value(
            balance,
            [
                "Cash And Cash Equivalents",
                "Cash Cash Equivalents And Short Term Investments",
                "Cash",
            ],
            year
        )
        free_cash_flow = get_value(cashflow, ["Free Cash Flow"], year)

        dividend_paid = 0
        if not dividends.empty:
            div_series = dividends[
                (dividends.index >= year_start) & (dividends.index <= year_end)
            ]
            dividend_paid = (
                div_series.sum().item()
                if hasattr(div_series.sum(), "item")
                else div_series.sum()
            )

        rows.append({
            "Year": int(year_end.year),
            "Currency": currency,
            "Revenue": revenue,
            "NetIncome": net_income,
            "OperatingIncome": operating_income,
            "Debt": debt,
            "Cash": cash,
            "FreeCashFlow": free_cash_flow,
            "DividendPaid": dividend_paid if dividend_paid != 0 else None,
        })

    rows.sort(key=lambda x: x["Year"])
    return rows


# =====================================================
# EARNINGS SURPRISES (ZWRACA LISTĘ SŁOWNIKÓW)
# =====================================================

def get_earnings_surprises(ticker_obj):
    try:
        earnings_dates = ticker_obj.earnings_dates
    except Exception:
        return []

    if earnings_dates is None or earnings_dates.empty:
        return []

    df = earnings_dates.copy().reset_index()

    rename_map = {}
    for col in df.columns:
        lower = str(col).lower()
        if "eps estimate" in lower:
            rename_map[col] = "EPSEstimate"
        elif "reported eps" in lower:
            rename_map[col] = "EPSActual"
        elif "surprise" in lower:
            rename_map[col] = "SurprisePercent"
        elif "earnings date" in lower:
            rename_map[col] = "EarningsDate"

    df.rename(columns=rename_map, inplace=True)

    columns_to_keep = []
    for col in ["EarningsDate", "EPSEstimate", "EPSActual", "SurprisePercent"]:
        if col in df.columns:
            columns_to_keep.append(col)

    df = df[columns_to_keep]

    if "EarningsDate" in df.columns:
        df.sort_values(by="EarningsDate", inplace=True)
        df["EarningsDate"] = df["EarningsDate"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Zamiana ewentualnych NaN na None (w JSON da to null)
    df = df.replace({np.nan: None})

    return df.to_dict(orient="records")


# =====================================================
# WYKRESY FUNDAMENTÓW SPÓŁKI
# =====================================================

def create_fundamental_chart(ticker_obj, output_dir):
    try:
        info = ticker_obj.info
        currency = info.get("currency", "N/A")
    except Exception:
        currency = "N/A"

    ticker_name = ticker_obj.ticker
    income = ticker_obj.income_stmt
    balance = ticker_obj.balance_sheet
    cashflow = ticker_obj.cashflow

    if income.empty:
        print(
            f"Brak danych rocznych do wygenerowania wykresu fundamentów dla {ticker_name}"
        )
        return

    years = income.columns[::-1]
    years_labels = [str(pd.Timestamp(y).year) for y in years]

    revenues = [
        get_value(income, ["Total Revenue", "Revenue"], y) for y in years
    ]
    net_incomes = [get_value(income, ["Net Income"], y) for y in years]
    debts = [get_value(balance, ["Total Debt"], y) for y in years]
    cashes = [
        get_value(
            balance,
            [
                "Cash And Cash Equivalents",
                "Cash Cash Equivalents And Short Term Investments",
                "Cash",
            ],
            y
        )
        for y in years
    ]
    fcfs = [get_value(cashflow, ["Free Cash Flow"], y) for y in years]

    def to_mln(lst):
        return [val / 1_000_000 if val is not None else 0 for val in lst]

    revenues_m = to_mln(revenues)
    net_incomes_m = to_mln(net_incomes)
    debts_m = to_mln(debts)
    cashes_m = to_mln(cashes)
    fcfs_m = to_mln(fcfs)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 11), sharex=True)

    fig.suptitle(
        f"Analiza Fundamentalna Roczna: {ticker_name} (Waluta: {currency})",
        fontsize=16,
        fontweight="bold",
    )

    x = np.arange(len(years_labels))
    width = 0.35

    ax1.bar(
        x - width / 2,
        revenues_m,
        width,
        label="Przychody (Revenue)",
        color="#1f77b4",
    )
    ax1.bar(
        x + width / 2,
        net_incomes_m,
        width,
        label="Zysk Netto (Net Income)",
        color="#2ca02c",
    )
    ax1.set_title("Wyniki Finansowe")
    ax1.set_ylabel(f"w mln {currency}")
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2.bar(
        x - width / 2, cashes_m, width, label="Gotówka (Cash)", color="#bcbd22"
    )
    ax2.bar(x + width / 2, debts_m, width, label="Dług (Total Debt)", color="#d62728")
    ax2.set_title("Pozycja Gotówkowa i Zadłużenie")
    ax2.set_ylabel(f"w mln {currency}")
    ax2.legend()
    ax2.grid(True, linestyle="--", alpha=0.5)

    ax3.plot(years_labels, fcfs_m, marker="o", color="#9467bd", linewidth=2, label="FCF")
    ax3.axhline(0, color="black", linewidth=0.8, linestyle="-")
    ax3.set_title("Wolne Przepływy Pieniężne (Free Cash Flow)")
    ax3.set_ylabel(f"w mln {currency}")
    ax3.legend()
    ax3.grid(True, linestyle="--", alpha=0.5)

    plt.xticks(x, years_labels)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_dir / "fundamental_chart.png")
    plt.close()


def create_dividend_chart(ticker_obj, output_dir):
    """
    Generuje wykres słupkowy rocznych dywidend wypłacanych przez spółkę.
    """
    try:
        info = ticker_obj.info
        currency = info.get("currency", "N/A")
    except Exception:
        currency = "N/A"

    ticker_name = ticker_obj.ticker
    dividends = ticker_obj.dividends

    if dividends.empty:
        print(f"Spółka {ticker_name} nie wypłacała dywidend (brak danych).")
        return

    # Kopia i ujednolicenie indeksu (usunięcie stref czasowych)
    div_df = dividends.to_frame().copy()
    div_df.index = div_df.index.tz_localize(None)

    # Agregacja dywidend według roku (suma wypłat w danym roku)
    div_annual = div_df.groupby(div_df.index.year).sum()

    plt.figure(figsize=(10, 5))

    # Rysowanie słupków
    plt.bar(div_annual.index, div_annual["Dividends"], color="#2ca02c", edgecolor="black", alpha=0.8, width=0.6)

    plt.title(f"Roczna Historia Dywidend: {ticker_name}", fontsize=14, fontweight="bold")
    plt.xlabel("Rok")
    plt.ylabel(f"Suma dywidend w roku ({currency})")
    plt.grid(True, linestyle="--", alpha=0.5, axis="y")

    # Wymuszenie wyświetlania lat jako liczb całkowitych na osi X
    plt.xticks(div_annual.index, rotation=45)

    plt.tight_layout()
    plt.savefig(output_dir / "dividend_history_chart.png")
    plt.close()


def create_earnings_surprise_chart(ticker_obj, output_dir):
    """
    Generuje wykres porównujący EPS szacowany (Estimate) z raportowanym (Actual) oraz procentowe zaskoczenie.
    """
    try:
        earnings_dates = ticker_obj.earnings_dates
    except Exception:
        return

    if earnings_dates is None or earnings_dates.empty:
        print(f"Brak danych earnings_dates do wykresu dla {ticker_obj.ticker}")
        return

    df = earnings_dates.copy().reset_index()

    # Ujednolicenie kolumn (analogicznie do Twojej funkcji JSON)
    rename_map = {}
    for col in df.columns:
        lower = str(col).lower()
        if "eps estimate" in lower:
            rename_map[col] = "EPSEstimate"
        elif "reported eps" in lower:
            rename_map[col] = "EPSActual"
        elif "surprise" in lower:
            rename_map[col] = "SurprisePercent"
        elif "earnings date" in lower:
            rename_map[col] = "EarningsDate"

    df.rename(columns=rename_map, inplace=True)

    # Filtrujemy tylko wiersze, które mają komplet danych (prognozę i wykonanie)
    df = df.dropna(subset=["EPSEstimate", "EPSActual"]).copy()

    if df.empty:
        print(f"Brak kompletnych danych EPS (Estimate/Actual) dla {ticker_obj.ticker}")
        return

    # Sortowanie chronologiczne (najstarsze na początku)
    df.sort_values(by="EarningsDate", inplace=True)

    # Przygotowanie etykiet dat na oś X (Format: RRRR-MM-DD)
    df["DateLabel"] = df["EarningsDate"].dt.strftime("%Y-%m-%d")

    # Tworzenie wykresu z dwiema osiami Y (lewa dla EPS, prawa dla Surprise %)
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()

    ticker_name = ticker_obj.ticker

    # 1. Lewa oś: Linie dla Prognozy i Wykonania
    ax1.plot(df["DateLabel"], df["EPSEstimate"], marker="o", linestyle="--", color="#1f77b4", linewidth=2,
             label="Szacowany EPS (Estimate)")
    ax1.plot(df["DateLabel"], df["EPSActual"], marker="s", linestyle="-", color="#ff7f0e", linewidth=2,
             label="Raportowany EPS (Actual)")
    ax1.set_ylabel("Zysk na akcję (EPS)", color="black")
    ax1.tick_params(axis="y", labelcolor="black")

    # 2. Prawa oś: Słupki reprezentujące Surprise % (zielone gdy dodatnie, czerwone gdy ujemne)
    colors = ["#2ca02c" if x >= 0 else "#d62728" for x in df["SurprisePercent"]]
    bars = ax2.bar(df["DateLabel"], df["SurprisePercent"], alpha=0.3, color=colors, width=0.4,
                   label="Zaskoczenie (Surprise %)")
    ax2.set_ylabel("Zaskoczenie (%)", color="gray")
    ax2.tick_params(axis="y", labelcolor="gray")
    ax2.axhline(0, color="gray", linewidth=0.8, linestyle="-")

    # Tytuły i legendy
    fig.suptitle(f"Rozbieżność Zysków (Earnings Surprise): {ticker_name}", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Data raportu finansowego")
    # NAPRAWA WARNINGA: Najpierw definiujemy pozycje punktów na osi X
    ax1.set_xticks(range(len(df)))
    # Dopiero teraz przypisujemy im teksty (daty)
    ax1.set_xticklabels(df["DateLabel"], rotation=45, ha="right")

    # Połączenie legend z obu osi w jedną
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    ax1.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_dir / "earnings_surprise_chart.png")
    plt.close()

# =====================================================
# PRZETWARZANIE SPÓŁKI
# =====================================================

def process_ticker(symbol, output_dir=None):
    """
    Przetwarza spółkę i zapisuje wyniki do podanego folderu.
    Jeśli output_dir=None → używa globalnego OUTPUT_DIR (stare zachowanie).
    """
    print(f"Przetwarzam {symbol}")

    ticker = yf.Ticker(symbol)

    # Określenie folderu docelowego
    if output_dir is None:
        company_dir = OUTPUT_DIR / symbol
    else:
        company_dir = Path(output_dir) / symbol

    company_dir.mkdir(parents=True, exist_ok=True)

    # Główny słownik danych
    combined_data = {
        "ticker": symbol,
        "generated_at": str(pd.Timestamp.now())
    }

    # 1. Wykres techniczny + historia cen
    try:
        create_technical_chart(ticker, company_dir)
    except Exception as e:
        print(f"Błąd technical_chart {symbol}: {e}")

    # 2. Dane do JSONa
    try:
        combined_data["current_snapshot"] = get_current_snapshot(ticker)
    except Exception as e:
        print(f"Błąd snapshot {symbol}: {e}")
        combined_data["current_snapshot"] = {}

    try:
        combined_data["quarterly_fundamentals"] = get_quarterly_fundamentals(ticker)
    except Exception as e:
        print(f"Błąd quarterly {symbol}: {e}")
        combined_data["quarterly_fundamentals"] = []

    try:
        combined_data["annual_fundamentals"] = get_annual_fundamentals(ticker)
    except Exception as e:
        print(f"Błąd annual {symbol}: {e}")
        combined_data["annual_fundamentals"] = []

    try:
        combined_data["earnings_surprises"] = get_earnings_surprises(ticker)
    except Exception as e:
        print(f"Błąd earnings_surprises {symbol}: {e}")
        combined_data["earnings_surprises"] = []

    # 3. Zapis JSON
    json_path = company_dir / "company_data.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=4)
        print(f"✓ Zapisano JSON: {json_path}")
    except Exception as e:
        print(f"Błąd zapisu JSON {symbol}: {e}")

    # 4. Pozostałe wykresy
    try:
        create_fundamental_chart(ticker, company_dir)
    except Exception as e:
        print(f"Błąd fundamental_chart {symbol}: {e}")

    try:
        create_dividend_chart(ticker, company_dir)
    except Exception as e:
        print(f"Błąd dividend_chart {symbol}: {e}")

    try:
        create_earnings_surprise_chart(ticker, company_dir)
    except Exception as e:
        print(f"Błąd earnings_surprise_chart {symbol}: {e}")

# =====================================================
# MAIN
# =====================================================

def main():
    for symbol in TICKERS:
        process_ticker(symbol)

        # Losowe opóźnienie od 3 do 6 sekund między spółkami
        delay = random.uniform(3.0, 6.0)
        print(f"Oczekiwanie {delay:.2f} s przed kolejną spółką...")
        time.sleep(delay)

    print("Gotowe")


if __name__ == "__main__":
    main()