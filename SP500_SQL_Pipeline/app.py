"""S&P 500 Market Monitoring Engine — Executive Financial Dashboard

Design System:
- Primary Dark: #001524 (Deep Obsidian Navy)
- Primary Teal: #15616D (Marine Teal)
- Tab Accent: #78290F (Rich Mahogany Rust)
- Canvas: #F0F0F3 (Soft Neumorphic Background)
- Font: Modern Sans-Serif ('Inter', -apple-system, sans-serif)
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pyodbc
import streamlit as st

ROOT = Path(__file__).resolve().parent

# --- Page Configuration ---
st.set_page_config(
    page_title="S&P 500 Market Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Executive Design System (CSS) ---
st.markdown("""
<style>
    /* Modern Sans-Serif Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* Hide Default Streamlit Chrome & Sidebar */
    #MainMenu, header, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Global Typography Stack */
    *, html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
    }

    /* Base Body Surface */
    .stApp {
        background-color: #F0F0F3 !important;
        color: #001524 !important;
    }

    .block-container {
        max-width: 1440px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 4rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
    }

    /* 1. Executive Hero Block */
    .hero-container {
        background: #001524;
        color: #FFFFFF;
        border-radius: 24px;
        padding: 34px 44px;
        margin-bottom: 24px;
        box-shadow: 12px 12px 28px rgba(0, 21, 36, 0.22), -6px -6px 20px rgba(255, 255, 255, 0.7);
        position: relative;
        overflow: hidden;
    }

    .hero-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 8px;
        height: 100%;
        background: #15616D;
    }

    .hero-meta {
        font-size: 0.80rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #15616D;
        text-transform: uppercase;
        margin-bottom: 6px;
    }

    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.1;
        color: #FFFFFF;
        margin: 0;
    }

    .hero-subtitle {
        font-size: 0.98rem;
        font-weight: 400;
        color: #CBD5E1;
        margin-top: 8px;
        letter-spacing: -0.01em;
        line-height: 1.5;
    }

    /* 2. Alternating Cards (#001524 & #15616D) */
    .card-dark {
        background: #001524 !important;
        color: #FFFFFF !important;
        border-radius: 22px;
        box-shadow: 8px 8px 18px rgba(0, 21, 36, 0.28), -6px -6px 14px rgba(255, 255, 255, 0.85);
        padding: 22px 24px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        transition: all 0.2s ease-in-out;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .card-dark:hover {
        transform: translateY(-2px);
        box-shadow: 11px 11px 24px rgba(0, 21, 36, 0.40), -8px -8px 18px rgba(255, 255, 255, 0.95);
    }

    .card-dark .w-tag {
        font-size: 0.76rem;
        font-weight: 700;
        color: #15616D;
        letter-spacing: 0.03em;
        margin-bottom: 6px;
    }

    .card-dark .w-val {
        font-size: 2.1rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.03em;
        line-height: 1.1;
        font-variant-numeric: tabular-nums;
    }

    .card-dark .w-sub {
        font-size: 0.80rem;
        color: #CBD5E1;
        margin-top: 10px;
        line-height: 1.5;
    }

    .card-teal {
        background: #15616D !important;
        color: #FFFFFF !important;
        border-radius: 22px;
        box-shadow: 8px 8px 18px rgba(21, 97, 109, 0.30), -6px -6px 14px rgba(255, 255, 255, 0.85);
        padding: 22px 24px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        transition: all 0.2s ease-in-out;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .card-teal:hover {
        transform: translateY(-2px);
        box-shadow: 11px 11px 24px rgba(21, 97, 109, 0.42), -8px -8px 18px rgba(255, 255, 255, 0.95);
    }

    .card-teal .w-tag {
        font-size: 0.76rem;
        font-weight: 700;
        color: #E0F2FE;
        opacity: 0.92;
        letter-spacing: 0.03em;
        margin-bottom: 6px;
    }

    .card-teal .w-val {
        font-size: 2.1rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.03em;
        line-height: 1.1;
        font-variant-numeric: tabular-nums;
    }

    .card-teal .w-sub {
        font-size: 0.80rem;
        color: #E2E8F0;
        font-weight: 500;
        margin-top: 10px;
        line-height: 1.5;
    }

    /* Neumorphic Canvas Cards */
    .neu-card {
        background: #F0F0F3;
        border-radius: 24px;
        box-shadow: 10px 10px 22px #d1d1d4, -10px -10px 22px #ffffff;
        padding: 32px;
        margin-bottom: 28px;
        border: 1px solid rgba(255, 255, 255, 0.8);
    }

    /* Executive Summary Card */
    .exec-summary-card {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 22px 28px;
        margin-top: 22px;
        margin-bottom: 24px;
        box-shadow: 8px 8px 20px #d4d4d8, -8px -8px 20px #ffffff;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #78290F;
    }

    .exec-summary-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 10px;
    }

    .exec-summary-badge {
        background: #78290F;
        color: #FFFFFF;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 9999px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    .exec-summary-date {
        font-size: 0.84rem;
        font-weight: 600;
        color: #64748B;
    }

    .exec-summary-body {
        font-size: 0.98rem;
        line-height: 1.65;
        color: #1E293B;
        font-weight: 450;
    }

    /* In-Tab Executive Takeaway Box */
    .takeaway-container {
        background: rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 18px 20px;
        margin-top: 22px;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .takeaway-label {
        font-size: 0.74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #E2E8F0;
        margin-bottom: 6px;
    }

    .takeaway-content {
        font-size: 0.88rem;
        line-height: 1.6;
        color: #FFFFFF;
        font-weight: 400;
    }

    /* Badges */
    .badge-on-dark {
        background: #15616D;
        color: #FFFFFF;
        font-size: 0.82rem;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 9999px;
        letter-spacing: 0.03em;
        display: inline-block;
    }

    .badge-on-teal {
        background: #001524;
        color: #FFFFFF;
        font-size: 0.82rem;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 9999px;
        letter-spacing: 0.03em;
        display: inline-block;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* 3. Executive Tab Navigation Buttons (#78290F Palette) */
    [data-testid="stTabs"],
    .stTabs {
        margin-top: 10px !important;
        margin-bottom: 24px !important;
    }

    [data-testid="stTabs"] [role="tablist"],
    div[data-baseweb="tab-list"],
    .stTabs [role="tablist"],
    div[data-testid="stTabs"] > div:first-child {
        gap: 12px !important;
        background: transparent !important;
        border-bottom: none !important;
        padding: 6px 4px 18px 4px !important;
        display: flex !important;
        flex-wrap: wrap !important;
        align-items: center !important;
    }

    [data-testid="stTabs"] [role="tablist"]::after,
    [data-testid="stTabs"] div::after,
    .stTabs [role="tablist"]::after,
    .react-aria-SelectionIndicator,
    div[data-baseweb="tab-highlight"],
    div[data-baseweb="tab-border"] {
        display: none !important;
        height: 0px !important;
        width: 0px !important;
        background: transparent !important;
        border: none !important;
        opacity: 0 !important;
        visibility: hidden !important;
    }

    [data-testid="stTab"],
    [data-testid="stTabs"] [role="tab"],
    button[data-baseweb="tab"],
    .stTabs [role="tab"] {
        background-color: #F0F0F3 !important;
        border-radius: 14px !important;
        box-shadow: 6px 6px 14px #d1d1d4, -6px -6px 14px #ffffff !important;
        padding: 12px 24px !important;
        margin: 4px 4px !important;
        border: 1px solid rgba(255, 255, 255, 0.9) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.9) !important;
        cursor: pointer !important;
        transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
        height: auto !important;
        min-height: 44px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        outline: none !important;
        text-decoration: none !important;
    }

    [data-testid="stTab"] p,
    [data-testid="stTab"] span,
    [data-testid="stTab"] div,
    [data-testid="stTabs"] [role="tab"] p,
    [data-testid="stTabs"] [role="tab"] span,
    button[data-baseweb="tab"] p {
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
        text-transform: none !important;
        color: #001524 !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.2 !important;
        transition: color 0.2s ease !important;
    }

    [data-testid="stTab"]:hover,
    [data-testid="stTabs"] [role="tab"]:hover,
    button[data-baseweb="tab"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 8px 8px 18px #c5c5c9, -8px -8px 18px #ffffff !important;
        border: 1px solid rgba(120, 41, 15, 0.35) !important;
    }

    [data-testid="stTab"]:hover p,
    [data-testid="stTab"]:hover span,
    [data-testid="stTabs"] [role="tab"]:hover p,
    button[data-baseweb="tab"]:hover p {
        color: #78290F !important;
    }

    [data-testid="stTab"][aria-selected="true"],
    [data-testid="stTab"][data-selected],
    [data-testid="stTabs"] [role="tab"][aria-selected="true"],
    [data-testid="stTabs"] [role="tab"][data-selected],
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #78290F !important;
        border-radius: 14px !important;
        box-shadow: 6px 6px 16px rgba(120, 41, 15, 0.42), -4px -4px 12px rgba(255, 255, 255, 0.85), inset 2px 2px 4px rgba(255, 255, 255, 0.18), inset -2px -2px 4px rgba(0, 0, 0, 0.35) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    [data-testid="stTab"][aria-selected="true"] p,
    [data-testid="stTab"][aria-selected="true"] span,
    [data-testid="stTab"][aria-selected="true"] div,
    [data-testid="stTab"][data-selected] p,
    [data-testid="stTab"][data-selected] span,
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] p,
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] span,
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35) !important;
    }

    [data-testid="stTab"]:focus,
    [data-testid="stTab"]:focus-visible,
    [data-testid="stTabs"] [role="tab"]:focus {
        outline: none !important;
    }

    /* Section Typography */
    .section-title {
        font-size: 1.7rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #001524;
        margin-top: 4px;
        margin-bottom: 8px;
    }

    .meta-crumb {
        font-size: 0.78rem;
        font-weight: 700;
        color: #78290F;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    /* Date Selector Container */
    div[data-baseweb="select"] {
        background: #F0F0F3 !important;
        border-radius: 12px !important;
        box-shadow: inset 4px 4px 8px #d1d1d4, inset -4px -4px 8px #ffffff !important;
        border: none !important;
    }
    div[data-baseweb="select"] > div {
        background: transparent !important;
        border: none !important;
        color: #001524 !important;
        font-weight: 600 !important;
    }

    /* Dataframe Neumorphism */
    [data-testid="stDataFrame"] {
        background: #F0F0F3 !important;
        border-radius: 20px !important;
        box-shadow: inset 5px 5px 12px #d1d1d4, inset -5px -5px 12px #ffffff !important;
        padding: 18px !important;
    }

    .live-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #15616D;
        box-shadow: 0 0 10px #15616D;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)


# --- Database Connector ---
@st.cache_resource
def get_db_connection():
    with open(ROOT / 'config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    driver = config['odbc_driver']
    cs = (f'DRIVER={{{driver}}};SERVER={{{config["sql_server"]}}};'
          f'DATABASE={{{config["sql_database"]}}};Trusted_Connection=yes;Encrypt=yes;'
          f'TrustServerCertificate={"yes" if config["trust_server_certificate"] else "no"};')
    return pyodbc.connect(cs, timeout=15)


def load_market_metrics():
    conn = get_db_connection()
    query = """
        SELECT 
            TradingDate, CalculatedUtc, RuleVersion,
            IndexClose, IndexSMA200, IndexSMA200_20d_ago, Regime, RegimeReason,
            BreadthAboveCount, BreadthEligibleCount, BreadthRosterCount, BreadthExcludedCount,
            BreadthCoveragePct, BreadthHealthPct, HealthBand, BreadthReason,
            SPY_Close, SPY_30d_Return, RSP_Close, RSP_30d_Return, LeadershipGap_PctPoints, ConcentrationProxyReason,
            VIX_Close, VIX_Date, RealizedVol_20d_Annualized,
            Current_PE, Current_PE_Date, Historical_PE_60m_Mean, PE_vs_Historical_Mean_Pct, StressReason,
            QualityStatus, QualityNotes
        FROM dbo.DailyMarketMetrics
        ORDER BY TradingDate ASC
    """
    df = pd.read_sql(query, conn)
    df['TradingDate'] = pd.to_datetime(df['TradingDate'])
    return df


def load_stock_features(target_date):
    conn = get_db_connection()
    query = """
        SELECT 
            f.Symbol, c.CompanyName, c.Sector,
            f.CloseSplitAdjusted, f.SMA200, f.AboveSMA200, f.IsEligibleBreadth
        FROM dbo.StockDailyFeatures f
        LEFT JOIN dbo.v_LatestConstituents c ON f.Symbol = c.Symbol
        WHERE f.PriceDate = ?
        ORDER BY f.Symbol ASC
    """
    return pd.read_sql(query, conn, params=[target_date.strftime('%Y-%m-%d')])


# --- Chart Theming Helper ---
def get_chart_layout(title: str = "") -> dict:
    return dict(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(family="Inter, -apple-system, sans-serif", size=15, color="#001524")
        ),
        paper_bgcolor="#F0F0F3",
        plot_bgcolor="#F0F0F3",
        font=dict(family="Inter, -apple-system, sans-serif", size=11, color="#001524"),
        xaxis=dict(
            showgrid=True,
            gridcolor="#E2E4E8",
            gridwidth=1,
            zeroline=False,
            linecolor="#CBD5E1",
            tickfont=dict(family="Inter, -apple-system, sans-serif", size=11, color="#64748B")
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#E2E4E8",
            gridwidth=1,
            zeroline=False,
            linecolor="#CBD5E1",
            tickfont=dict(family="Inter, -apple-system, sans-serif", size=11, color="#64748B")
        ),
        margin=dict(l=40, r=40, t=50, b=40),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family="Inter, -apple-system, sans-serif", size=11, color="#001524")
        )
    )


# --- State-Aware Market Evaluation Helpers ---
def _is_valid(val) -> bool:
    return val is not None and not pd.isna(val)


def evaluate_regime_state(row: pd.Series) -> dict:
    """Evaluate market trend regime and produce state-aware status and narrative."""
    raw_regime = str(row.get('Regime') or 'Unavailable').strip()
    close = row.get('IndexClose')
    sma200 = row.get('IndexSMA200')
    sma_20d = row.get('IndexSMA200_20d_ago')

    close_str = f"{close:,.2f}" if _is_valid(close) else "N/A"
    sma_str = f"{sma200:,.2f}" if _is_valid(sma200) else "N/A"
    sma20_str = f"{sma_20d:,.2f}" if _is_valid(sma_20d) else "N/A"

    if _is_valid(sma200) and _is_valid(sma_20d):
        if sma200 > sma_20d:
            slope_label = "Upward (Positive Momentum)"
            slope_short = "Rising 200-Day Trend"
        elif sma200 < sma_20d:
            slope_label = "Downward (Negative Momentum)"
            slope_short = "Falling 200-Day Trend"
        else:
            slope_label = "Flat (Unchanged)"
            slope_short = "Flat 200-Day Trend"
    else:
        slope_label = "Insufficient History"
        slope_short = "Warmup Period"

    if raw_regime == 'Bull' and _is_valid(close) and _is_valid(sma200):
        spread = close - sma200
        status_label = "BULL"
        summary_sentence = (
            f"The S&P 500 maintains an established Bull regime, closing at {close_str} "
            f"above its upward-trending 200-day moving average ({sma_str})."
        )
        takeaway = (
            f"The index is trading {spread:+,.2f} points above its rising 200-day moving average, "
            "confirming a constructive primary uptrend with institutional buyers supporting higher price levels."
        )
    elif raw_regime == 'Bear' and _is_valid(close) and _is_valid(sma200):
        spread = close - sma200
        status_label = "BEAR"
        summary_sentence = (
            f"The S&P 500 remains in a Bear regime, closing at {close_str} "
            f"below its declining 200-day moving average ({sma_str})."
        )
        takeaway = (
            f"The index is trading {spread:+,.2f} points below its downward-sloping 200-day moving average, "
            "signaling a defensive environment where rebounds face sustained overhead resistance."
        )
    elif raw_regime == 'Neutral' and _is_valid(close) and _is_valid(sma200):
        status_label = "NEUTRAL"
        if close >= sma200:
            summary_sentence = (
                f"The S&P 500 is in a Neutral transition phase at {close_str}; price has reclaimed the "
                f"200-day moving average ({sma_str}), though the longer-term slope has not yet turned positive."
            )
            takeaway = (
                "Price holds above the 200-day average, but the trailing trend slope remains flat or negative. "
                "Continued strength is needed to confirm a full shift into a Bull regime."
            )
        else:
            summary_sentence = (
                f"The S&P 500 is in a Neutral consolidation phase at {close_str}, sitting below its "
                f"200-day moving average ({sma_str}) while the long-term slope stays resilient."
            )
            takeaway = (
                "Short-term price action has slipped under the 200-day moving average while the underlying trend slope "
                "remains non-negative, pointing to a pullback or consolidation rather than a confirmed Bear trend."
            )
    else:
        status_label = "PENDING"
        summary_sentence = (
            f"The S&P 500 closed at {close_str}; trend regime classification is pending the full "
            "220-session historical baseline required to establish the 200-day average and slope."
        )
        takeaway = (
            "Fewer than 220 historical trading sessions are available prior to this date, so the 200-day moving average "
            "and 20-day slope classification remain intentionally unrated until sufficient history accumulates."
        )

    return {
        'status_label': status_label,
        'close_str': close_str,
        'sma_str': sma_str,
        'sma20_str': sma20_str,
        'slope_label': slope_label,
        'slope_short': slope_short,
        'summary_sentence': summary_sentence,
        'takeaway': takeaway,
    }


def evaluate_health_state(row: pd.Series, regime_label: str) -> dict:
    """Evaluate constituent breadth participation and return dynamic state and narrative."""
    raw_band = row.get('HealthBand')
    band = str(raw_band).strip() if _is_valid(raw_band) and str(raw_band).strip() else 'Pending'
    pct = row.get('BreadthHealthPct')
    above = row.get('BreadthAboveCount')
    eligible = row.get('BreadthEligibleCount')
    excluded = row.get('BreadthExcludedCount')
    roster = row.get('BreadthRosterCount')
    coverage = row.get('BreadthCoveragePct')

    pct_str = f"{pct:.1f}%" if _is_valid(pct) else "N/A"
    counts_str = f"{int(above)}/{int(eligible)} stocks" if _is_valid(above) and _is_valid(eligible) else "Warmup Period"
    above_str = f"{int(above)}" if _is_valid(above) else "N/A"
    eligible_str = f"{int(eligible)}" if _is_valid(eligible) else "N/A"
    excluded_str = f"{int(excluded)}" if _is_valid(excluded) else "N/A"
    roster_str = f"{int(roster)}" if _is_valid(roster) else "N/A"
    coverage_str = f"{coverage:.1f}%" if _is_valid(coverage) else "N/A"

    band_upper = band.upper()
    if band == 'Strong':
        summary_clause = f"Market health is strong with {pct_str} of eligible S&P 500 stocks above their 200-day averages"
        if regime_label == 'BULL':
            takeaway = (
                f"{pct_str} of eligible constituents ({above_str} of {eligible_str}) trade above their 200-day moving averages, "
                "confirming broad, durable participation behind the Bull trend rather than narrow leadership."
            )
        else:
            takeaway = (
                f"Despite the {regime_label.title()} index backdrop, {pct_str} of constituents ({above_str} of {eligible_str}) "
                "remain above their 200-day averages, demonstrating strong underlying constituent resilience."
            )
    elif band == 'Mixed':
        summary_clause = f"Market participation is mixed with {pct_str} of constituent stocks holding above their 200-day averages"
        takeaway = (
            f"{pct_str} of eligible stocks ({above_str} of {eligible_str}) sit above their 200-day averages, placing breadth "
            "in the mixed 40%–60% zone and signaling selective sector rotation rather than uniform buying pressure."
        )
    elif band == 'Weak':
        summary_clause = f"Market health is weak, with only {pct_str} of constituent stocks trading above their 200-day averages"
        if regime_label == 'BULL':
            takeaway = (
                f"Only {pct_str} of constituents ({above_str} of {eligible_str}) hold above their 200-day averages even though "
                "the headline index trends upward—a negative breadth divergence warning that gains rely on a narrow cohort."
            )
        else:
            takeaway = (
                f"Just {pct_str} of constituents ({above_str} of {eligible_str}) remain above their 200-day averages, "
                "confirming widespread weakness and broad participation in the market downturn."
            )
    elif band == 'Suppressed':
        summary_clause = f"Breadth classification is suppressed due to limited constituent coverage ({coverage_str})"
        takeaway = (
            f"Data coverage is {coverage_str}, below the 95% quality safeguard threshold required to assign a reliable "
            "market health band on this date."
        )
    else:
        band_upper = "PENDING"
        summary_clause = "Constituent breadth metrics are pending the 200-session minimum history threshold"
        takeaway = (
            "Individual S&P 500 stocks require at least 200 completed trading sessions to calculate a 200-day moving average, "
            "so constituent participation rates are not yet populated for this early date."
        )

    return {
        'status_label': band_upper,
        'pct_str': pct_str,
        'counts_str': counts_str,
        'above_str': above_str,
        'eligible_str': eligible_str,
        'excluded_str': excluded_str,
        'roster_str': roster_str,
        'coverage_str': coverage_str,
        'summary_clause': summary_clause,
        'takeaway': takeaway,
    }


def evaluate_concentration_state(row: pd.Series) -> dict:
    """Evaluate 30-session SPY vs RSP leadership gap and return dynamic status and narrative."""
    gap = row.get('LeadershipGap_PctPoints')
    spy_ret = row.get('SPY_30d_Return')
    rsp_ret = row.get('RSP_30d_Return')

    spy_str = f"{spy_ret * 100:+.2f}%" if _is_valid(spy_ret) else "N/A"
    rsp_str = f"{rsp_ret * 100:+.2f}%" if _is_valid(rsp_ret) else "N/A"

    if not _is_valid(gap):
        return {
            'status_label': 'PENDING',
            'gap_val_str': 'N/A',
            'gap_unit': '',
            'value_color': '#CBD5E1',
            'spy_str': spy_str,
            'rsp_str': rsp_str,
            'summary_clause': 'while 30-session cap-weight versus equal-weight concentration data is still accumulating.',
            'takeaway': (
                'Fewer than 31 synchronized closing sessions exist prior to this date to compute the 30-day return comparison '
                'between cap-weighted SPY and equal-weighted RSP.'
            ),
        }

    gap_val_str = f"{gap:+.2f}"
    value_color = '#38BDF8' if gap >= 0 else '#818CF8'

    if gap > 1.5:
        status_label = 'MEGA-CAP LED'
        summary_clause = (
            f"while recent 30-day performance is concentrated among mega-cap leaders "
            f"(cap-weighted SPY outpacing equal-weighted RSP by {gap:+.2f} percentage points)."
        )
        takeaway = (
            f"Cap-weighted SPY ({spy_str}) has outperformed equal-weighted RSP ({rsp_str}) by {gap:+.2f} percentage points "
            "over the past 30 sessions, indicating that index returns are heavily driven by the largest mega-cap constituents."
        )
    elif gap < -1.5:
        status_label = 'BROAD MARKET LED'
        summary_clause = (
            f"supported by broad-market leadership as equal-weighted RSP outpaces cap-weighted SPY "
            f"by {abs(gap):.2f} percentage points."
        )
        takeaway = (
            f"Equal-weighted RSP ({rsp_str}) has outperformed cap-weighted SPY ({spy_str}) by {abs(gap):.2f} percentage points "
            "over the past 30 sessions, showing healthy rotation toward the average constituent company across sectors."
        )
    else:
        status_label = 'BALANCED'
        summary_clause = (
            f"with balanced leadership between cap-weighted SPY ({spy_str}) and equal-weighted RSP ({rsp_str}) "
            "across the past 30 trading sessions."
        )
        takeaway = (
            f"The 30-session return spread between cap-weighted SPY ({spy_str}) and equal-weighted RSP ({rsp_str}) is just "
            f"{gap:+.2f} percentage points, reflecting balanced performance without excessive mega-cap concentration."
        )

    return {
        'status_label': status_label,
        'gap_val_str': gap_val_str,
        'gap_unit': ' pp',
        'value_color': value_color,
        'spy_str': spy_str,
        'rsp_str': rsp_str,
        'summary_clause': summary_clause,
        'takeaway': takeaway,
    }


def evaluate_stress_valuation_state(row: pd.Series) -> dict:
    """Evaluate implied volatility, realized volatility, and trailing valuation states."""
    vix = row.get('VIX_Close')
    rvol = row.get('RealizedVol_20d_Annualized')
    pe = row.get('Current_PE')
    pe_mean = row.get('Historical_PE_60m_Mean')
    pe_diff = row.get('PE_vs_Historical_Mean_Pct')

    vix_str = f"{vix:.2f}" if _is_valid(vix) else "N/A"
    rvol_str = f"{rvol:.2f}%" if _is_valid(rvol) else "N/A"
    spread_str = f"{vix - rvol:+.2f} pp" if (_is_valid(vix) and _is_valid(rvol)) else "N/A"
    pe_str = f"{pe:.2f}x" if _is_valid(pe) else "N/A"
    pe_mean_str = f"{pe_mean:.2f}x" if _is_valid(pe_mean) else "N/A"
    pe_diff_str = f"{pe_diff:+.1f}%" if _is_valid(pe_diff) else "N/A"

    if not _is_valid(vix):
        vol_status = "UNAVAILABLE"
        vol_phrase = "volatility data unavailable"
        vol_takeaway = "Expected volatility readings are unavailable for this date."
    elif vix < 15.0:
        vol_status = "LOW VOLATILITY"
        vol_phrase = f"calm, low-volatility conditions (VIX at {vix_str})"
        vol_takeaway = (
            f"The VIX sits at a subdued {vix_str}, signaling low expected near-term turbulence and complacent option pricing."
        )
    elif vix < 20.0:
        vol_status = "NORMAL"
        vol_phrase = f"normal, orderly volatility expectations (VIX at {vix_str})"
        vol_takeaway = (
            f"The VIX reads {vix_str} against 20-day realized volatility of {rvol_str}, pointing to stable, orderly "
            "institutional risk pricing within normal historical boundaries."
        )
    elif vix < 30.0:
        vol_status = "ELEVATED"
        vol_phrase = f"elevated market caution (VIX at {vix_str})"
        vol_takeaway = (
            f"The VIX has risen into the caution zone at {vix_str} (vs. {rvol_str} 20-day realized volatility), "
            "indicating heightened hedging demand and wider expected daily swings."
        )
    else:
        vol_status = "HIGH STRESS"
        vol_phrase = f"acute market stress (VIX at {vix_str})"
        vol_takeaway = (
            f"The VIX is flashing high stress at {vix_str} (vs. {rvol_str} realized volatility), reflecting defensive "
            "de-risking and substantial demand for downside protection."
        )

    if _is_valid(vix) and _is_valid(rvol):
        if (vix - rvol) >= 3.0:
            vol_takeaway += " Implied volatility trades at a notable premium over realized swings, showing forward caution."
        elif (vix - rvol) <= -3.0:
            vol_takeaway += " Realized swings currently exceed forward VIX pricing, suggesting recent volatility may be stabilizing."

    if not _is_valid(pe) or not _is_valid(pe_diff):
        val_status = "UNAVAILABLE"
        val_phrase = "valuation baseline unavailable"
        val_takeaway = "Historical P/E comparison data is unavailable for this observation."
    elif pe_diff > 5.0:
        val_status = "PREMIUM"
        val_phrase = f"the trailing P/E ratio of {pe:.1f}x trades {pe_diff:.1f}% above its 5-year average"
        val_takeaway = (
            f"At {pe_str}, market valuation trades at a {pe_diff_str} premium over its 5-year average of {pe_mean_str}, "
            "leaving less margin for earnings disappointment."
        )
    elif pe_diff < -5.0:
        val_status = "DISCOUNTED"
        val_phrase = f"the trailing P/E ratio of {pe:.1f}x trades {abs(pe_diff):.1f}% below its 5-year average"
        val_takeaway = (
            f"At {pe_str}, market valuation trades at a {abs(pe_diff):.1f}% discount to its 5-year average of {pe_mean_str}, "
            "offering relatively favorable long-term valuation support."
        )
    else:
        val_status = "NEAR AVERAGE"
        val_phrase = f"the trailing P/E ratio of {pe:.1f}x sits roughly in line ({pe_diff_str}) with its 5-year average"
        val_takeaway = (
            f"At {pe_str}, market valuation sits close to its 5-year historical average of {pe_mean_str} ({pe_diff_str}), "
            "reflecting balanced multiple pricing relative to recent history."
        )

    return {
        'vol_status': vol_status,
        'val_status': val_status,
        'vix_str': vix_str,
        'rvol_str': rvol_str,
        'spread_str': spread_str,
        'pe_str': pe_str,
        'pe_mean_str': pe_mean_str,
        'pe_diff_str': pe_diff_str,
        'summary_sentence': f"Risk conditions reflect {vol_phrase}, while {val_phrase}.",
        'takeaway': f"{vol_takeaway} {val_takeaway}",
    }


def build_executive_summary(reg_state: dict, health_state: dict, conc_state: dict, stress_state: dict) -> str:
    """Assemble a cohesive, state-aware executive briefing from evaluated pillar states."""
    return (
        f"{reg_state['summary_sentence']} "
        f"{health_state['summary_clause']}, {conc_state['summary_clause']} "
        f"{stress_state['summary_sentence']}"
    )


# --- Load Data ---
metrics_df = load_market_metrics()

if metrics_df.empty:
    st.error("No market metrics found in SQL Server database. Run features.py first.")
    st.stop()

available_dates = sorted(metrics_df['TradingDate'].dt.date.unique(), reverse=True)

# ==============================================================================
# SECTION 1: EXECUTIVE HERO HEADER
# ==============================================================================
col_h_left, col_h_right = st.columns([3, 1])

with col_h_left:
    st.markdown("""
    <div class="hero-container">
        <div class="hero-meta">S&P 500 Market Intelligence</div>
        <h1 class="hero-title">Market Surveillance Dashboard</h1>
        <div class="hero-subtitle">Executive oversight across market regime, constituent breadth, cap-weight concentration, and valuation risk at US market close.</div>
    </div>
    """, unsafe_allow_html=True)

with col_h_right:
    st.markdown("""
    <div class="neu-card" style="padding: 24px; text-align: left; height: 100%;">
        <div class="w-tag" style="color:#001524; font-weight:700; font-size:0.75rem; letter-spacing:0.04em;">As-Of Trading Date</div>
    """, unsafe_allow_html=True)
    selected_date = st.selectbox(
        label="Select Date",
        options=available_dates,
        index=0,
        label_visibility="collapsed"
    )
    st.markdown("""
        <div style="font-size:0.78rem; margin-top: 12px; line-height: 1.4;">
            <span class="live-dot"></span><span style="font-weight:700; color:#001524;">Verified Data Feed</span><br>
            <span style="color:#64748B;">Official Daily Close</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

selected_row = metrics_df[metrics_df['TradingDate'].dt.date == selected_date].iloc[0]

# Compute state-aware evaluations for the selected trading date
reg_state = evaluate_regime_state(selected_row)
health_state = evaluate_health_state(selected_row, reg_state['status_label'])
conc_state = evaluate_concentration_state(selected_row)
stress_state = evaluate_stress_valuation_state(selected_row)

# ==============================================================================
# SECTION 2: ALTERNATING KPI CARDS (#001524 & #15616D)
# ==============================================================================
w_col1, w_col2, w_col3, w_col4, w_col5 = st.columns(5)

# Card 1: Market Regime -> CARD DARK (#001524)
with w_col1:
    st.markdown(f"""
    <div class="card-dark">
        <div>
            <div class="w-tag">Market Regime</div>
            <div class="w-val" style="margin-top: 4px;">
                <span class="badge-on-dark">{reg_state['status_label']}</span>
            </div>
        </div>
        <div class="w-sub">
            Close: <b style="color:#FFFFFF;">{reg_state['close_str']}</b><br>
            200-Day SMA: <b style="color:#FFFFFF;">{reg_state['sma_str']}</b><br>
            Trend: <b style="color:#38BDF8;">{reg_state['slope_short']}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Card 2: Market Participation -> CARD TEAL (#15616D)
with w_col2:
    st.markdown(f"""
    <div class="card-teal">
        <div>
            <div class="w-tag">Market Participation</div>
            <div class="w-val">
                {health_state['pct_str']}
            </div>
        </div>
        <div class="w-sub">
            Breadth Status: <span class="badge-on-teal">{health_state['status_label']}</span><br>
            Above 200 SMA: <b>{health_state['counts_str']}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Card 3: Leadership Gap -> CARD DARK (#001524)
with w_col3:
    st.markdown(f"""
    <div class="card-dark">
        <div>
            <div class="w-tag">Leadership Gap</div>
            <div class="w-val" style="color: {conc_state['value_color']};">
                {conc_state['gap_val_str']}<span style="font-size:1.1rem; font-weight:700;">{conc_state['gap_unit']}</span>
            </div>
        </div>
        <div class="w-sub">
            Status: <span class="badge-on-dark">{conc_state['status_label']}</span><br>
            SPY: <b style="color:#FFFFFF;">{conc_state['spy_str']}</b> &bull; RSP: <b style="color:#FFFFFF;">{conc_state['rsp_str']}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Card 4: Expected Volatility (VIX) -> CARD TEAL (#15616D)
with w_col4:
    st.markdown(f"""
    <div class="card-teal">
        <div>
            <div class="w-tag">Expected Volatility (VIX)</div>
            <div class="w-val">
                {stress_state['vix_str']}
            </div>
        </div>
        <div class="w-sub">
            Risk State: <span class="badge-on-teal">{stress_state['vol_status']}</span><br>
            Recorded: <b>{selected_row['VIX_Date']}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Card 5: Valuation -> CARD DARK (#001524)
with w_col5:
    st.markdown(f"""
    <div class="card-dark">
        <div>
            <div class="w-tag">Trailing Valuation</div>
            <div class="w-val" style="color:#FFFFFF;">
                {stress_state['pe_str']}
            </div>
        </div>
        <div class="w-sub">
            Status: <span class="badge-on-dark">{stress_state['val_status']}</span><br>
            vs. 5Y Avg: <b style="color:#38BDF8;">{stress_state['pe_diff_str']}</b> ({stress_state['pe_mean_str']})
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# SECTION 3: EXECUTIVE SUMMARY BRIEFING
# ==============================================================================
exec_summary_text = build_executive_summary(reg_state, health_state, conc_state, stress_state)
st.markdown(f"""
<div class="exec-summary-card">
    <div class="exec-summary-header">
        <span class="exec-summary-badge">Executive Briefing</span>
        <span class="exec-summary-date">Market Close Overview &bull; {selected_date.strftime('%B %d, %Y')}</span>
    </div>
    <div class="exec-summary-body">
        {exec_summary_text}
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# SECTION 4: EXECUTIVE NAVIGATION TABS
# ==============================================================================
t_regime, t_health, t_concentration, t_stress, t_explorer, t_method = st.tabs([
    "Market Regime",
    "Market Health",
    "Concentration",
    "Stress & Valuation",
    "Data Explorer",
    "Methodology"
])

# ------------------------------------------------------------------------------
# TAB 1: MARKET REGIME
# ------------------------------------------------------------------------------
with t_regime:
    st.markdown("""
    <div class="meta-crumb">Trend Classification</div>
    <div class="section-title">Market Regime</div>
    """, unsafe_allow_html=True)

    r_left, r_right = st.columns([1, 2])

    with r_left:
        st.markdown(f"""
        <div class="card-dark" style="padding: 28px;">
            <div>
                <div class="w-tag">Current Verdict</div>
                <div style="margin-top: 8px; margin-bottom: 20px;">
                    <span class="badge-on-dark" style="font-size: 1.15rem; padding: 6px 20px;">{reg_state['status_label']}</span>
                </div>
                <div class="w-tag">Primary Trend Indicators</div>
                <div style="font-size: 0.88rem; line-height: 1.8; margin-top: 8px;">
                    • S&P 500 Close: <b style="color:#FFFFFF;">{reg_state['close_str']}</b><br>
                    • 200-Day Moving Average: <b style="color:#FFFFFF;">{reg_state['sma_str']}</b><br>
                    • 200-Day SMA (20 Days Ago): <b style="color:#FFFFFF;">{reg_state['sma20_str']}</b><br>
                    • 20-Day Trend Slope: <b style="color:#38BDF8;">{reg_state['slope_label']}</b>
                </div>
            </div>
            <div class="takeaway-container">
                <div class="takeaway-label">Executive Takeaway</div>
                <div class="takeaway-content">{reg_state['takeaway']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with r_right:
        st.markdown("<div class='neu-card'>", unsafe_allow_html=True)
        fig_regime = go.Figure()
        fig_regime.add_trace(go.Scatter(
            x=metrics_df['TradingDate'], y=metrics_df['IndexClose'],
            mode='lines', name='S&P 500 Close',
            line=dict(color='#001524', width=2.4)
        ))
        fig_regime.add_trace(go.Scatter(
            x=metrics_df['TradingDate'], y=metrics_df['IndexSMA200'],
            mode='lines', name='200-Day SMA',
            line=dict(color='#15616D', width=2.2, dash='dash')
        ))
        fig_regime.add_vline(
            x=pd.to_datetime(selected_date),
            line_width=1.5, line_dash="dot", line_color="#001524",
            annotation_text="Selected Date", annotation_position="top left",
            annotation_font=dict(family="Inter, sans-serif", size=10, color="#15616D")
        )
        fig_regime.update_layout(get_chart_layout("S&P 500 Closing Level vs. 200-Day Moving Average"))
        st.plotly_chart(fig_regime, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 2: MARKET HEALTH & BREADTH
# ------------------------------------------------------------------------------
with t_health:
    st.markdown("""
    <div class="meta-crumb">Constituent Participation</div>
    <div class="section-title">Market Health & Breadth</div>
    """, unsafe_allow_html=True)

    h_left, h_right = st.columns([1, 2])

    with h_left:
        st.markdown(f"""
        <div class="card-teal" style="padding: 28px;">
            <div>
                <div class="w-tag">Breadth Status</div>
                <div style="margin-top: 8px; margin-bottom: 20px;">
                    <span class="badge-on-teal" style="font-size: 1.15rem; padding: 6px 20px;">{health_state['status_label']}</span>
                </div>
                <div class="w-tag">Constituent Participation Summary</div>
                <div style="font-size: 0.88rem; line-height: 1.8; margin-top: 8px;">
                    • Stocks Above 200-Day SMA: <b>{health_state['above_str']}</b><br>
                    • Eligible Constituents: <b>{health_state['eligible_str']}</b><br>
                    • Excluded (Insufficient History): <b>{health_state['excluded_str']}</b><br>
                    • Active S&P 500 Roster: <b>{health_state['roster_str']}</b><br>
                    • Roster Data Coverage: <b>{health_state['coverage_str']}</b>
                </div>
            </div>
            <div class="takeaway-container">
                <div class="takeaway-label">Executive Takeaway</div>
                <div class="takeaway-content">{health_state['takeaway']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with h_right:
        st.markdown("<div class='neu-card'>", unsafe_allow_html=True)
        fig_breadth = go.Figure()
        fig_breadth.add_trace(go.Scatter(
            x=metrics_df['TradingDate'], y=metrics_df['BreadthHealthPct'],
            mode='lines', name='% Above 200-Day SMA',
            line=dict(color='#15616D', width=2.4)
        ))
        fig_breadth.add_hline(y=60, line_dash="dot", line_color="#10B981", annotation_text="Strong (> 60%)", annotation_font=dict(family="Inter, sans-serif", size=10, color="#10B981"))
        fig_breadth.add_hline(y=40, line_dash="dot", line_color="#EF4444", annotation_text="Weak (< 40%)", annotation_font=dict(family="Inter, sans-serif", size=10, color="#EF4444"))
        fig_breadth.add_vline(x=pd.to_datetime(selected_date), line_width=1.5, line_dash="dot", line_color="#001524")
        layout_b = get_chart_layout("Constituent Breadth: Percentage of S&P 500 Members Above 200-Day SMA")
        layout_b['yaxis']['range'] = [0, 100]
        fig_breadth.update_layout(layout_b)
        st.plotly_chart(fig_breadth, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 3: RETURN CONCENTRATION
# ------------------------------------------------------------------------------
with t_concentration:
    st.markdown("""
    <div class="meta-crumb">Performance Divergence</div>
    <div class="section-title">Return Concentration</div>
    """, unsafe_allow_html=True)

    c_left, c_right = st.columns([1, 2])

    with c_left:
        st.markdown(f"""
        <div class="card-dark" style="padding: 28px;">
            <div>
                <div class="w-tag">30-Day Leadership Gap</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: {conc_state['value_color']}; margin-top: 6px; margin-bottom: 10px;">
                    {conc_state['gap_val_str']} <span style="font-size:1.1rem; font-weight:600;">{conc_state['gap_unit']}</span>
                </div>
                <div style="margin-bottom: 18px;">
                    <span class="badge-on-dark">{conc_state['status_label']}</span>
                </div>
                <div class="w-tag">Index Return Comparison (Past 30 Trading Days)</div>
                <div style="font-size: 0.88rem; line-height: 1.8; margin-top: 8px;">
                    • SPY (Cap-Weighted): <b style="color:#FFFFFF;">{conc_state['spy_str']}</b><br>
                    • RSP (Equal-Weighted): <b style="color:#FFFFFF;">{conc_state['rsp_str']}</b><br>
                    • Measurement Window: <b style="color:#15616D;">30 Trading Days</b>
                </div>
            </div>
            <div class="takeaway-container">
                <div class="takeaway-label">Executive Takeaway</div>
                <div class="takeaway-content">{conc_state['takeaway']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c_right:
        st.markdown("<div class='neu-card'>", unsafe_allow_html=True)
        fig_gap = go.Figure()
        fig_gap.add_trace(go.Bar(
            x=metrics_df['TradingDate'],
            y=metrics_df['LeadershipGap_PctPoints'],
            marker_color=['#15616D' if (_is_valid(g) and g >= 0) else '#001524' for g in metrics_df['LeadershipGap_PctPoints']],
            name='Leadership Gap (pp)'
        ))
        fig_gap.add_hline(y=0, line_color="#001524", line_width=1.2)
        fig_gap.add_vline(x=pd.to_datetime(selected_date), line_width=1.5, line_dash="dot", line_color="#15616D")
        layout_c = get_chart_layout("30-Day Leadership Gap: SPY Return minus RSP Return (Percentage Points)")
        layout_c['yaxis']['title'] = "Percentage Points (pp)"
        fig_gap.update_layout(layout_c)
        st.plotly_chart(fig_gap, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 4: MARKET STRESS & VALUATION
# ------------------------------------------------------------------------------
with t_stress:
    st.markdown("""
    <div class="meta-crumb">Risk & Valuation</div>
    <div class="section-title">Market Stress & Valuation</div>
    """, unsafe_allow_html=True)

    s_left, s_right = st.columns([1, 2])

    with s_left:
        st.markdown(f"""
        <div class="card-teal" style="padding: 28px;">
            <div>
                <div class="w-tag">Risk & Valuation Status</div>
                <div style="margin-top: 8px; margin-bottom: 18px; display: flex; gap: 8px; flex-wrap: wrap;">
                    <span class="badge-on-teal">{stress_state['vol_status']}</span>
                    <span class="badge-on-teal">{stress_state['val_status']}</span>
                </div>
                <div class="w-tag">Volatility & Valuation Overview</div>
                <div style="font-size: 0.88rem; line-height: 1.8; margin-top: 10px;">
                    • Cboe VIX (Implied Volatility): <b>{stress_state['vix_str']}</b><br>
                    • 20-Day Realized Volatility: <b>{stress_state['rvol_str']}</b><br>
                    • Volatility Spread (VIX vs. Realized): <b>{stress_state['spread_str']}</b><br>
                    • Trailing P/E Ratio: <b>{stress_state['pe_str']}</b><br>
                    • 5-Year Historical Average: <b>{stress_state['pe_mean_str']}</b><br>
                    • Valuation vs. 5-Year Average: <b>{stress_state['pe_diff_str']}</b>
                </div>
            </div>
            <div class="takeaway-container">
                <div class="takeaway-label">Executive Takeaway</div>
                <div class="takeaway-content">{stress_state['takeaway']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with s_right:
        st.markdown("<div class='neu-card'>", unsafe_allow_html=True)
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(
            x=metrics_df['TradingDate'], y=metrics_df['VIX_Close'],
            mode='lines', name='VIX (Expected 30-Day Vol)',
            line=dict(color='#001524', width=2.4)
        ))
        fig_vol.add_trace(go.Scatter(
            x=metrics_df['TradingDate'], y=metrics_df['RealizedVol_20d_Annualized'],
            mode='lines', name='20-Day Realized Vol (Observed)',
            line=dict(color='#15616D', width=2.2)
        ))
        fig_vol.add_hline(y=20, line_dash="dot", line_color="#F59E0B", annotation_text="Caution (20)", annotation_font=dict(family="Inter, sans-serif", size=10, color="#F59E0B"))
        fig_vol.add_hline(y=30, line_dash="dot", line_color="#EF4444", annotation_text="Elevated Stress (30)", annotation_font=dict(family="Inter, sans-serif", size=10, color="#EF4444"))
        fig_vol.add_vline(x=pd.to_datetime(selected_date), line_width=1.5, line_dash="dot", line_color="#001524")
        fig_vol.update_layout(get_chart_layout("Expected Volatility (VIX) vs. Observed 20-Day Realized Volatility"))
        st.plotly_chart(fig_vol, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 5: DATA EXPLORER (Completely Unaltered per User Request)
# ------------------------------------------------------------------------------
with t_explorer:
    st.markdown("""
    <div class="meta-crumb">Audit & Data Inspection</div>
    <div class="section-title">Data Explorer</div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='neu-card'>", unsafe_allow_html=True)
    view_mode = st.radio(
        "Choose Inspection Scope:",
        ["Market-Wide Daily Metrics", "Constituent Stock Features on Selected Date"],
        horizontal=True
    )

    if view_mode == "Market-Wide Daily Metrics":
        st.dataframe(metrics_df, use_container_width=True)
        csv_m = metrics_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Market Metrics (CSV)",
            data=csv_m,
            file_name=f"sp500_daily_metrics_{selected_date}.csv",
            mime="text/csv"
        )
    else:
        stock_df = load_stock_features(selected_date)
        if stock_df.empty:
            st.info(f"No constituent features loaded for {selected_date}.")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                sector_filter = st.multiselect("Filter by GICS Sector:", sorted(stock_df['Sector'].dropna().unique()))
            with col_f2:
                status_filter = st.selectbox("Filter by 200 SMA Status:", ["All Securities", "Above 200 SMA", "Below 200 SMA"])

            filtered_stocks = stock_df.copy()
            if sector_filter:
                filtered_stocks = filtered_stocks[filtered_stocks['Sector'].isin(sector_filter)]
            if status_filter == "Above 200 SMA":
                filtered_stocks = filtered_stocks[filtered_stocks['AboveSMA200'] == 1]
            elif status_filter == "Below 200 SMA":
                filtered_stocks = filtered_stocks[filtered_stocks['AboveSMA200'] == 0]

            st.dataframe(filtered_stocks, use_container_width=True)
            csv_s = filtered_stocks.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Constituent Stock Features (CSV)",
                data=csv_s,
                file_name=f"sp500_constituents_{selected_date}.csv",
                mime="text/csv"
            )
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 6: METHODOLOGY & DATA ARCHITECTURE
# ------------------------------------------------------------------------------
with t_method:
    st.markdown("""
    <div class="meta-crumb">Architecture & Pipeline</div>
    <div class="section-title">Methodology & Data Flow</div>
    """, unsafe_allow_html=True)

    # 1. Existing Architecture Flow Chart (Retained)
    st.markdown("""
    <div class="neu-card">
        <div class="meta-crumb" style="margin-bottom: 6px;">Pipeline Architecture</div>
        <div class="section-title" style="font-size: 1.3rem; margin-bottom: 14px;">Data Processing Flow</div>
        <div style="font-size: 0.85rem; line-height: 1.7; color: #001524; background: #FFFFFF; border-radius: 16px; padding: 22px 26px; border: 1px solid #E2E8F0; box-shadow: inset 2px 2px 6px #e2e4e8;">
            <strong>Public Sources</strong> ──&gt; FRED (SP500), Cboe (VIX), Multpl (P/E), Wikipedia (Roster), Yahoo (Prices)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼ (DNS-resilient automated ingestion &amp; audit report)<br>
            <strong>Raw Storage</strong> ──────&gt; Timestamped raw payload captures &amp; run audit reports<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼ (Transactional SQL Server backfill)<br>
            <strong>SQL Server</strong> ───────&gt; SeriesObservation, DailyPrice, ConstituentSnapshot, FetchAudit<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼ (Feature Engineering)<br>
            <strong>Derived SQL</strong> ──────&gt; DailyMarketMetrics &amp; StockDailyFeatures<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼<br>
            <strong>Executive Dashboard</strong> ─&gt; Market Surveillance Application
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. New Clean Plain-English Stakeholder Explanation
    st.markdown("""
    <div class="neu-card">
        <div class="meta-crumb" style="margin-bottom: 6px;">Executive Briefing</div>
        <div class="section-title" style="font-size: 1.3rem; margin-bottom: 14px;">How Data Flows Through the Enterprise Architecture</div>
        <div style="font-size: 0.95rem; line-height: 1.7; color: #334155;">
            <p style="margin-bottom: 14px;">
                The S&P 500 Market Monitoring Engine operates as an automated, multi-tiered data intelligence system designed to deliver transparent, institutional-grade market surveillance after each trading session.
            </p>
            <p style="margin-bottom: 14px;">
                <strong>1. Data Ingestion from Public Authorities:</strong> Immediately following the US market close, automated collectors connect to primary financial institutions, including the Federal Reserve Bank of St. Louis for daily index closes, the Chicago Board Options Exchange for the VIX volatility index, historical valuation databases for trailing price-to-earnings ratios, and market feeds for individual constituent equity prices.
            </p>
            <p style="margin-bottom: 14px;">
                <strong>2. Raw Storage & Audit Archival:</strong> Every raw download is stored in an immutable raw data repository tagged with unique run identifiers, timestamps, and cryptographic integrity hashes. This guarantees audit compliance, allowing decision-makers to verify any dashboard metric back to its original source.
            </p>
            <p style="margin-bottom: 14px;">
                <strong>3. SQL Server Warehousing & Feature Engineering:</strong> Ingested data is staged into a dedicated Microsoft SQL Server database. Dedicated calculation engines compute 200-day moving averages across all 500 constituent stocks, evaluate participation breadth, measure equal-weight versus market-cap return divergence, and track historical valuation deviations.
            </p>
            <p style="margin-bottom: 0;">
                <strong>4. Executive Dashboard Delivery:</strong> The final calculated features are delivered directly to this interactive dashboard. Leadership and portfolio teams receive clean, timely market insights on trend regime, breadth health, return concentration, and systemic risk without manual data overhead.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. Reference Data Dictionary
    st.markdown("""
    <div class="neu-card">
        <div class="meta-crumb" style="margin-bottom: 6px;">Reference & Definitions</div>
        <div class="section-title" style="font-size: 1.3rem; margin-bottom: 14px;">Core Metrics & Business Definitions</div>
        <div style="margin-top: 12px; overflow-x: auto;">
            <table style="width: 100%; border-collapse: separate; border-spacing: 0 8px; font-size: 0.88rem;">
                <thead>
                    <tr style="font-size: 0.76rem; color: #001524; text-transform: uppercase; font-weight: 700;">
                        <th style="padding: 10px 16px; text-align: left;">Metric</th>
                        <th style="padding: 10px 16px; text-align: left;">Unit</th>
                        <th style="padding: 10px 16px; text-align: left;">Primary Source</th>
                        <th style="padding: 10px 16px; text-align: left;">Business Definition & Rule</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="background: #001524; color: #FFFFFF; border-radius: 8px;">
                        <td style="padding: 12px 16px; font-weight: 700; color: #15616D;">Index Close</td>
                        <td style="padding: 12px 16px;">USD points</td>
                        <td style="padding: 12px 16px;">FRED (SP500)</td>
                        <td style="padding: 12px 16px;">Official daily closing price of the S&P 500 index.</td>
                    </tr>
                    <tr style="background: #15616D; color: #FFFFFF; border-radius: 8px;">
                        <td style="padding: 12px 16px; font-weight: 700;">200-Day Moving Average</td>
                        <td style="padding: 12px 16px;">USD points</td>
                        <td style="padding: 12px 16px;">Calculated</td>
                        <td style="padding: 12px 16px;">Arithmetic mean of the closing price over the last 200 trading sessions.</td>
                    </tr>
                    <tr style="background: #001524; color: #FFFFFF; border-radius: 8px;">
                        <td style="padding: 12px 16px; font-weight: 700; color: #15616D;">Market Regime</td>
                        <td style="padding: 12px 16px;">Classification</td>
                        <td style="padding: 12px 16px;">Calculated</td>
                        <td style="padding: 12px 16px;">Bull if price > 200 SMA and slope is positive; Bear if price < 200 SMA and slope is negative; otherwise Neutral.</td>
                    </tr>
                    <tr style="background: #15616D; color: #FFFFFF; border-radius: 8px;">
                        <td style="padding: 12px 16px; font-weight: 700;">Participation Rate</td>
                        <td style="padding: 12px 16px;">Percentage (%)</td>
                        <td style="padding: 12px 16px;">Calculated</td>
                        <td style="padding: 12px 16px;">Percentage of constituent stocks trading above their own 200-day moving average.</td>
                    </tr>
                    <tr style="background: #001524; color: #FFFFFF; border-radius: 8px;">
                        <td style="padding: 12px 16px; font-weight: 700; color: #15616D;">Health Category</td>
                        <td style="padding: 12px 16px;">Classification</td>
                        <td style="padding: 12px 16px;">Calculated</td>
                        <td style="padding: 12px 16px;">Categorized as Weak (under 40%), Mixed (40% to 60%), or Strong (over 60%).</td>
                    </tr>
                    <tr style="background: #15616D; color: #FFFFFF; border-radius: 8px;">
                        <td style="padding: 12px 16px; font-weight: 700;">Leadership Gap</td>
                        <td style="padding: 12px 16px;">Percentage Points</td>
                        <td style="padding: 12px 16px;">Calculated</td>
                        <td style="padding: 12px 16px;">Difference between 30-day returns of cap-weighted SPY and equal-weighted RSP.</td>
                    </tr>
                    <tr style="background: #001524; color: #FFFFFF; border-radius: 8px;">
                        <td style="padding: 12px 16px; font-weight: 700; color: #15616D;">Cboe VIX</td>
                        <td style="padding: 12px 16px;">Annualized %</td>
                        <td style="padding: 12px 16px;">Cboe / FRED</td>
                        <td style="padding: 12px 16px;">Annualized 30-day forward implied volatility priced into SPX options.</td>
                    </tr>
                    <tr style="background: #15616D; color: #FFFFFF; border-radius: 8px;">
                        <td style="padding: 12px 16px; font-weight: 700;">Realized Volatility</td>
                        <td style="padding: 12px 16px;">Annualized %</td>
                        <td style="padding: 12px 16px;">Calculated</td>
                        <td style="padding: 12px 16px;">Annualized sample standard deviation of daily log returns over the past 20 trading sessions.</td>
                    </tr>
                    <tr style="background: #001524; color: #FFFFFF; border-radius: 8px;">
                        <td style="padding: 12px 16px; font-weight: 700; color: #15616D;">Trailing P/E Ratio</td>
                        <td style="padding: 12px 16px;">Ratio (x)</td>
                        <td style="padding: 12px 16px;">Multpl</td>
                        <td style="padding: 12px 16px;">Latest reported monthly trailing twelve months price-to-earnings multiple.</td>
                    </tr>
                    <tr style="background: #15616D; color: #FFFFFF; border-radius: 8px;">
                        <td style="padding: 12px 16px; font-weight: 700;">Valuation vs. 5-Year Mean</td>
                        <td style="padding: 12px 16px;">Percentage (%)</td>
                        <td style="padding: 12px 16px;">Calculated</td>
                        <td style="padding: 12px 16px;">Percentage deviation of current trailing P/E relative to its trailing 60-month historical mean.</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    """, unsafe_allow_html=True)
