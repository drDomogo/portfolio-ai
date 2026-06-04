from pathlib import Path

import matplotlib.pyplot as plt
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

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)


# =====================================================
# POMOCNICZE
# =====================================================

def get_value(df, possible_names, column):
    """
    Pobiera wartość z DataFrame po jednej z możliwych nazw wiersza.
    """

    if df is None or df.empty:
        return None

    if isinstance(possible_names, str):
        possible_names = [possible_names]

    for name in possible_names:
        try:
            if name in df.index:
                return df.loc[name, column]
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

    hist["SMA50"] = hist["Close"].rolling(50).mean()
    hist["SMA200"] = hist["Close"].rolling(200).mean()

    hist.to_csv(output_dir / "price_history.csv")

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(14, 8),
        height_ratios=[3, 1],
        sharex=True
    )

    ax1.plot(hist.index, hist["Close"], label="Close")
    ax1.plot(hist.index, hist["SMA50"], label="SMA50")
    ax1.plot(hist.index, hist["SMA200"], label="SMA200")

    ax1.set_title("Price + SMA50 + SMA200")
    ax1.legend()
    ax1.grid(True)

    ax2.bar(hist.index, hist["Volume"])

    ax2.set_title("Volume")
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig(output_dir / "technical_chart.png")
    plt.close()


# =====================================================
# CURRENT SNAPSHOT
# =====================================================

def create_current_snapshot(ticker_obj, output_dir):

    try:
        info = ticker_obj.info
    except Exception:
        info = {}

    snapshot = {
        "shortName": info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "currency": info.get("currency"),

        "currentPrice": info.get("currentPrice"),
        "marketCap": info.get("marketCap"),

        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),

        "trailingEps": info.get("trailingEps"),
        "forwardEps": info.get("forwardEps"),

        "pegRatio": info.get("pegRatio"),
        "priceToBook": info.get("priceToBook"),

        "returnOnEquity": info.get("returnOnEquity"),
        "debtToEquity": info.get("debtToEquity"),

        "beta": info.get("beta"),

        "dividendYield": info.get("dividendYield"),
        "dividendRate": info.get("dividendRate"),
        "fiveYearAvgDividendYield":
            info.get("fiveYearAvgDividendYield"),

        "sharesOutstanding":
            info.get("sharesOutstanding"),
    }

    pd.DataFrame([snapshot]).to_csv(
        output_dir / "current_snapshot.csv",
        index=False
    )


# =====================================================
# FUNDAMENTY KWARTALNE
# =====================================================

def create_quarterly_fundamentals(ticker_obj, output_dir):

    try:
        info = ticker_obj.info
    except Exception:
        info = {}

    currency = info.get("currency")

    quarterly_income = ticker_obj.quarterly_income_stmt
    quarterly_balance = ticker_obj.quarterly_balance_sheet
    quarterly_cashflow = ticker_obj.quarterly_cashflow

    if quarterly_income.empty:
        print("Brak danych kwartalnych")
        return

    dividends = ticker_obj.dividends

    # -------------------------------------------------
    # naprawa stref czasowych
    # -------------------------------------------------

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

        revenue = get_value(
            quarterly_income,
            [
                "Total Revenue",
                "Revenue"
            ],
            q
        )

        net_income = get_value(
            quarterly_income,
            [
                "Net Income",
                "NetIncome"
            ],
            q
        )

        operating_income = get_value(
            quarterly_income,
            [
                "Operating Income",
                "OperatingIncome"
            ],
            q
        )

        debt = get_value(
            quarterly_balance,
            [
                "Total Debt"
            ],
            q
        )

        cash = get_value(
            quarterly_balance,
            [
                "Cash And Cash Equivalents",
                "Cash Cash Equivalents And Short Term Investments",
                "Cash"
            ],
            q
        )

        free_cash_flow = get_value(
            quarterly_cashflow,
            [
                "Free Cash Flow"
            ],
            q
        )

        dividend_paid = 0

        if not dividends.empty:
            dividend_paid = dividends[
                (dividends.index >= quarter_start)
                & (dividends.index <= quarter_end)
            ].sum()

        rows.append({
            "Quarter": quarter_end.date(),

            "Currency": currency,

            "Revenue": revenue,
            "NetIncome": net_income,
            "OperatingIncome": operating_income,

            "Debt": debt,
            "Cash": cash,

            "FreeCashFlow": free_cash_flow,

            "DividendPaid": dividend_paid,
        })

    df = pd.DataFrame(rows)

    df.sort_values(
        by="Quarter",
        inplace=True
    )

    df.to_csv(
        output_dir / "quarterly_fundamentals.csv",
        index=False
    )
# =====================================================
# FUNDAMENTY ROCZNE
# =====================================================

def create_annual_fundamentals(ticker_obj, output_dir):

    try:
        info = ticker_obj.info
    except Exception:
        info = {}

    currency = info.get("currency")

    income = ticker_obj.income_stmt
    balance = ticker_obj.balance_sheet
    cashflow = ticker_obj.cashflow

    dividends = ticker_obj.dividends

    if not dividends.empty:
        dividends = dividends.copy()

        try:
            dividends.index = dividends.index.tz_localize(None)
        except Exception:
            pass

    if income.empty:
        print("Brak danych rocznych")
        return

    rows = []

    years = income.columns

    for year in years:

        year_end = pd.Timestamp(year).tz_localize(None)

        year_start = pd.Timestamp(
            year_end.year,
            1,
            1
        )

        revenue = get_value(
            income,
            ["Total Revenue", "Revenue"],
            year
        )

        net_income = get_value(
            income,
            ["Net Income"],
            year
        )

        operating_income = get_value(
            income,
            ["Operating Income"],
            year
        )

        debt = get_value(
            balance,
            ["Total Debt"],
            year
        )

        cash = get_value(
            balance,
            [
                "Cash And Cash Equivalents",
                "Cash Cash Equivalents And Short Term Investments",
                "Cash"
            ],
            year
        )

        free_cash_flow = get_value(
            cashflow,
            ["Free Cash Flow"],
            year
        )

        dividend_paid = 0

        if not dividends.empty:
            dividend_paid = dividends[
                (dividends.index >= year_start)
                & (dividends.index <= year_end)
            ].sum()

        rows.append({
            "Year": year_end.year,

            "Currency": currency,

            "Revenue": revenue,
            "NetIncome": net_income,
            "OperatingIncome": operating_income,

            "Debt": debt,
            "Cash": cash,

            "FreeCashFlow": free_cash_flow,

            "DividendPaid": dividend_paid,
        })

    df = pd.DataFrame(rows)

    df.sort_values(
        by="Year",
        inplace=True
    )

    df.to_csv(
        output_dir / "annual_fundamentals.csv",
        index=False
    )

# =====================================================
# PRZETWARZANIE SPÓŁKI
# =====================================================

def process_ticker(symbol):

    print(f"Przetwarzam {symbol}")

    ticker = yf.Ticker(symbol)

    company_dir = OUTPUT_DIR / symbol

    company_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    try:
        create_technical_chart(
            ticker,
            company_dir
        )
    except Exception as e:
        print(
            f"Błąd technical_chart {symbol}: {e}"
        )

    try:
        create_current_snapshot(
            ticker,
            company_dir
        )
    except Exception as e:
        print(
            f"Błąd current_snapshot {symbol}: {e}"
        )

    try:
        create_quarterly_fundamentals(
            ticker,
            company_dir
        )
    except Exception as e:
        print(
            f"Błąd quarterly_fundamentals {symbol}: {e}"
        )

    try:
        create_annual_fundamentals(
            ticker,
            company_dir
        )
    except Exception as e:
        print(
            f"Błąd annual_fundamentals {symbol}: {e}"
        )


# =====================================================
# MAIN
# =====================================================

def main():

    for symbol in TICKERS:
        process_ticker(symbol)

    print("Gotowe")


if __name__ == "__main__":
    main()