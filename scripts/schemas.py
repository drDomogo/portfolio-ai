from typing import List, Optional
from pydantic import BaseModel, Field


class ScorecardItem(BaseModel):
    criterion: str = Field(description="Nazwa kryterium oceny (np. Bilans, Marże, Trend)")
    score: int = Field(description="Ocena w skali 1-10")
    reason: str = Field(description="Zwięzłe uzasadnienie przyznanej oceny")


class PortfolioAnalysisReport(BaseModel):
    ticker: str = Field(description="Symbol giełdowy spółki, np. KRU.WA, Apple itp.")
    short_name: str = Field(
        description="Pełna lub skrócona czytelna nazwa firmy/instrumentu, np. Kruk, Microsoft, Bitcoin")
    analysis_date: str = Field(description="Data przeprowadzenia analizy w formacie YYYY-MM-DD")
    current_price: float = Field(description="Aktualny kurs zamknięcia instrumentu")
    currency: str = Field(description="Waluta notowania, np. PLN, USD, EUR")

    # Pola fundamentalne dopuszczające None (dla TECH_ONLY)
    revenue_and_eps_trend: Optional[str] = Field(None,
                                                 description="Analiza trendu przychodów i zysków netto. Wstaw null, jeśli brak danych fundamentalnych.")
    fcf_and_operations: Optional[str] = Field(None,
                                              description="Analiza wolnych przepływów pieniężnych i operacji. Wstaw null, jeśli brak danych fundamentalnych.")
    balance_sheet_debt: Optional[str] = Field(None,
                                              description="Analiza bilansu i poziomu zadłużenia. Wstaw null, jeśli brak danych fundamentalnych.")
    dividend_policy: Optional[str] = Field(None,
                                           description="Analiza historii i polityki dywidendowej. Wstaw null, jeśli brak danych danych fundamentalnych.")

    market_expectations: Optional[str] = Field(None,
                                               description="Realizacja oczekiwań rynkowych i zaskoczenia wynikami. Wstaw null, jeśli brak danych.")
    valuation_status: str = Field(description="Ocena wyceny: Tania, Fair Value, Droga, Bardzo Droga")
    key_valuation_metrics: str = Field(description="Kluczowe wskaźniki użyte do oceny, np. P/E, P/B, EV/EBITDA")

    # Poziomy cenowe
    price_strong_opportunity: float = Field(
        description="Poziom ceny oznaczający silną okazję inwestycyjną (Mocna Okazja)")
    price_attractive: float = Field(description="Cena atrakcyjna do zakupu (Cena Atrakcyjna)")
    price_fair_value: float = Field(description="Wycena godziwa (Fair Value)")
    price_overvalued: float = Field(description="Poziom wyraźnego przewartościowania (Drogo)")
    price_valuation_justification: str = Field(
        description="Matematyczne i rynkowe uzasadnienie wyznaczonych poziomów cenowych")

    # Analiza techniczna
    trend_short_term: str = Field(description="Krótkoterminowy trend: Spadkowy, Wzrostowy, Boczny")
    trend_long_term: str = Field(description="Długoterminowy trend: Spadkowy, Wzrostowy, Boczny")
    position_vs_sma50: str = Field(description="Pozycja ceny względem SMA50: nad, pod, na poziomie")
    position_vs_sma200: str = Field(description="Pozycja ceny względem SMA200: nad, pod, na poziomie")
    support_level: float = Field(description="Najbliższy istotny poziom wsparcia technicznego")
    resistance_level: float = Field(description="Najbliższy istotny poziom oporu technycznego")
    momentum_summary: str = Field(description="Podsumowanie momentum i zachowania wskaźników technicznych")

    # Podsumowanie końcowe
    scorecard: List[ScorecardItem] = Field(description="Lista obiektów ocen cząstkowych dla kluczowych kryteriów")
    final_verdict: str = Field(description="Ostateczny werdykt: AKUMULUJ, TRZYMAJ, REDUKUJ, SPRZEDAJ")
    main_risk: str = Field(description="Główne zidentyfikowane ryzyko dla tej inwestycji")