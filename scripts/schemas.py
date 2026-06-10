from pydantic import BaseModel, Field
from typing import List, Optional


# Definicja podstruktury dla Karty Wyników (Scorecard)
class ScorecardItem(BaseModel):
    criterion: str = Field(description="Nazwa kryterium, np. 'Przychody i Marże', 'Trend Techniczny'")
    score: int = Field(description="Ocena w skali 1-10")
    reason: str = Field(description="Kluczowy powód oceny, maksymalnie 5 słów")


# Główna struktura raportu JSON, którą musi zwrócić Gemini
class PortfolioAnalysisReport(BaseModel):
    ticker: str
    analysis_date: str = Field(description="Data analizy w formacie YYYY-MM-DD")
    current_price: float
    currency: str

    # Sekcja 1: Fundamenty
    revenue_and_eps_trend: str = Field(
        description="Max 2 zdania: trend średnioterminowy, dynamika CAGR/r-r, ocena stabilności trendu")
    fcf_and_operations: str = Field(
        description="Max 2 zdania: zdolność do generowania gotówki, relacja FCF do zysku netto")
    balance_sheet_debt: str = Field(description="Max 1 zdanie: ocena dźwigni finansowej i poziomu bezpieczeństwa")
    dividend_policy: str = Field(description="Max 1 zdanie: czy dywidenda jest bezpieczna i pokryta zyskami/FCF")

    # Sekcja 2 & 3: Oczekiwania i Wycena
    market_expectations: str = Field(
        description="Max 2 zdania: Jaki % prognoz EPS spółka pobija? Czy regularnie dowozi wyniki?")
    valuation_status: str = Field(
        description="Status wyceny: Tania, Uczciwa lub Droga względem historycznego tempa wzrostu")
    key_valuation_metrics: str = Field(
        description="Max 2 zdania syntetyzujące wskaźniki P/E, P/B, ROE oraz poziom zadłużenia")

    # Sekcja 4: Poziomy cenowe
    price_strong_opportunity: float = Field(description="Cena stanowiąca mocną okazję (bardzo atrakcyjna)")
    price_attractive: float = Field(description="Cena atrakcyjna")
    price_fair_value: float = Field(description="Cena uczciwa (Fair Value)")
    price_overvalued: float = Field(description="Cena przewartościowana")
    price_valuation_justification: str = Field(
        description="Krótkie uzasadnienie matematyczne/wskaźnikowe dla wyznaczonych poziomów")

    # Sekcja 5: Analiza Techniczna
    trend_short_term: str = Field(description="Trend krótkoterminowy, np. Spadkowy, Wzrostowy, Konsolidacja")
    trend_long_term: str = Field(description="Trend długoterminowy")
    position_vs_sma50: str = Field(description="Pozycja ceny względem średniej SMA50: 'nad' lub 'pod'")
    position_vs_sma200: str = Field(description="Pozycja ceny względem średniej SMA200: 'nad' lub 'pod'")
    support_level: float = Field(description="Istotny poziom wsparcia cenowego")
    resistance_level: float = Field(description="Istotny poziom oporu cenowego")
    momentum_summary: str = Field(
        description="1 zdanie: czy obecny moment na bazie wykresu/historii cen sprzyja akumulacji")

    # Sekcja 6: Scorecard i Werdykt
    scorecard: List[ScorecardItem]
    final_verdict: str = Field(description="Jedno słowo: AKUMULUJ, TRZYMAJ, REDUKUJ lub SPRZEDAJ")
    main_risk: str = Field(description="Zdefiniuj 1 najważniejsze ryzyko dla spółki w maksymalnie 10 słowach")