"""Calculates S&P 500 Market Monitoring Engine features from stored SQL Server data.

Pillars:
1. Market Regime (Bull / Bear / Neutral via 200-session SMA and 20-session slope)
2. Market Health / Breadth (% of constituents above their own 200-session SMA)
3. 30-Session Concentration Proxy (SPY vs RSP return leadership gap)
4. Stress & Valuation (VIX, 20-day annualized realized vol, and P/E vs 60-month mean)

Separates ingestion, derived features, and UI. Repeatable and transactional.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT / 'logs' / 'features.log', encoding='utf-8')
    ]
)
log = logging.getLogger(__name__)

RULE_VERSION = 'v1.0'


def load_config():
    with open(ROOT / 'config.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_connection(config):
    import pyodbc
    driver = config['odbc_driver']
    cs = (f'DRIVER={{{driver}}};SERVER={{{config["sql_server"]}}};'
          f'DATABASE={{{config["sql_database"]}}};Trusted_Connection=yes;Encrypt=yes;'
          f'TrustServerCertificate={"yes" if config["trust_server_certificate"] else "no"};')
    return pyodbc.connect(cs, timeout=15, autocommit=False)


def calculate_regime(index_prices: List[Tuple[date, float]]) -> Dict[date, dict]:
    """Calculates SMA200 and Bull/Bear/Neutral regime for index closes."""
    # index_prices is sorted by date ascending: [(d, close), ...]
    results = {}
    closes = [p[1] for p in index_prices]
    dates = [p[0] for p in index_prices]
    n = len(closes)

    sma200_series = [None] * n
    for i in range(199, n):
        sma200_series[i] = sum(closes[i - 199 : i + 1]) / 200.0

    for i in range(n):
        d = dates[i]
        c = closes[i]
        sma = sma200_series[i]
        if sma is None or i < 219:
            results[d] = {
                'close': c,
                'sma200': sma,
                'sma200_20d_ago': None,
                'regime': 'Unavailable',
                'reason': 'Insufficient history (< 220 sessions required for 200-day average and 20-day slope)'
            }
            continue

        sma_20d_ago = sma200_series[i - 20]
        if sma_20d_ago is None:
            results[d] = {
                'close': c,
                'sma200': sma,
                'sma200_20d_ago': None,
                'regime': 'Unavailable',
                'reason': 'Insufficient history for 20-session slope comparison'
            }
            continue

        if c > sma and sma > sma_20d_ago:
            regime = 'Bull'
            reason = f'Close ({c:.2f}) > SMA200 ({sma:.2f}) AND SMA200 slope is upward ({sma:.2f} > {sma_20d_ago:.2f} 20d ago)'
        elif c < sma and sma < sma_20d_ago:
            regime = 'Bear'
            reason = f'Close ({c:.2f}) < SMA200 ({sma:.2f}) AND SMA200 slope is downward ({sma:.2f} < {sma_20d_ago:.2f} 20d ago)'
        else:
            regime = 'Neutral'
            if c >= sma and sma <= sma_20d_ago:
                reason = f'Mixed: Close ({c:.2f}) >= SMA200 ({sma:.2f}), but 200-day slope is not positive ({sma:.2f} <= {sma_20d_ago:.2f})'
            elif c <= sma and sma >= sma_20d_ago:
                reason = f'Mixed: Close ({c:.2f}) <= SMA200 ({sma:.2f}), but 200-day slope is not negative ({sma:.2f} >= {sma_20d_ago:.2f})'
            else:
                reason = 'Mixed or flat evidence'

        results[d] = {
            'close': c,
            'sma200': sma,
            'sma200_20d_ago': sma_20d_ago,
            'regime': regime,
            'reason': reason
        }
    return results


def calculate_realized_vol(index_prices: List[Tuple[date, float]]) -> Dict[date, Optional[float]]:
    """Calculates 20-session annualized realized volatility = std(20 daily returns, ddof=1) * sqrt(252)."""
    results = {}
    dates = [p[0] for p in index_prices]
    closes = [p[1] for p in index_prices]
    n = len(closes)

    # Calculate daily returns r(t) = P(t)/P(t-1) - 1
    returns = [None] * n
    for i in range(1, n):
        if closes[i - 1] > 0:
            returns[i] = (closes[i] / closes[i - 1]) - 1.0

    for i in range(n):
        d = dates[i]
        # Needs 20 valid returns (which requires 21 price closes)
        if i < 20 or any(r is None for r in returns[i - 19 : i + 1]):
            results[d] = None
            continue
        window_r = returns[i - 19 : i + 1]
        mean_r = sum(window_r) / 20.0
        var_r = sum((r - mean_r) ** 2 for r in window_r) / 19.0  # sample std ddof=1
        daily_std = math.sqrt(var_r)
        annualized_vol_pct = daily_std * math.sqrt(252.0) * 100.0
        results[d] = round(annualized_vol_pct, 4)
    return results


def calculate_concentration_proxy(spy_prices: List[Tuple[date, float]], rsp_prices: List[Tuple[date, float]]) -> Dict[date, dict]:
    """Calculates 30-session returns for SPY and RSP and leadership gap."""
    spy_dict = dict(spy_prices)
    rsp_dict = dict(rsp_prices)

    # Find common session dates sorted
    common_dates = sorted(set(spy_dict.keys()) & set(rsp_dict.keys()))
    results = {}

    for i, d in enumerate(common_dates):
        if i < 30:
            results[d] = {
                'spy_close': spy_dict[d],
                'spy_30d_return': None,
                'rsp_close': rsp_dict[d],
                'rsp_30d_return': None,
                'leadership_gap': None,
                'reason': 'Insufficient history (< 30 common trading sessions)'
            }
            continue

        d_30 = common_dates[i - 30]
        spy_now = spy_dict[d]
        spy_prev = spy_dict[d_30]
        rsp_now = rsp_dict[d]
        rsp_prev = rsp_dict[d_30]

        r30_spy = (spy_now / spy_prev) - 1.0
        r30_rsp = (rsp_now / rsp_prev) - 1.0
        gap_pct_pts = (r30_spy - r30_rsp) * 100.0

        if gap_pct_pts > 0:
            reason = f'Cap-weighted SPY (+{r30_spy*100:.2f}%) outperformed Equal-weighted RSP (+{r30_rsp*100:.2f}%) by {gap_pct_pts:.2f} pp. Mega-caps leading.'
        elif gap_pct_pts < 0:
            reason = f'Equal-weighted RSP ({r30_rsp*100:+.2f}%) outperformed Cap-weighted SPY ({r30_spy*100:+.2f}%) by {abs(gap_pct_pts):.2f} pp. Broad participation leading.'
        else:
            reason = 'Equal performance between Cap-weighted and Equal-weighted exposure.'

        results[d] = {
            'spy_close': spy_now,
            'spy_30d_return': round(r30_spy, 6),
            'rsp_close': rsp_now,
            'rsp_30d_return': round(r30_rsp, 6),
            'leadership_gap': round(gap_pct_pts, 4),
            'reason': reason
        }
    return results


def calculate_pe_metrics(pe_monthly: List[Tuple[date, float]]) -> Dict[date, dict]:
    """Computes trailing P/E metrics and 60-month historical mean comparison."""
    # pe_monthly is sorted by date ascending: [(d, val), ...]
    results = {}
    dates = [p[0] for p in pe_monthly]
    vals = [p[1] for p in pe_monthly]
    n = len(vals)

    for i in range(n):
        d = dates[i]
        curr_val = vals[i]
        # Preceding 60 valid monthly observations, excluding the current observation
        if i < 60:
            results[d] = {
                'current_pe': curr_val,
                'historical_mean': None,
                'pct_vs_mean': None,
                'reason': f'Insufficient history ({i} of 60 monthly observations available)'
            }
        else:
            window = vals[i - 60 : i]
            mean_60 = sum(window) / 60.0
            pct_vs_mean = ((curr_val / mean_60) - 1.0) * 100.0
            results[d] = {
                'current_pe': curr_val,
                'historical_mean': round(mean_60, 4),
                'pct_vs_mean': round(pct_vs_mean, 4),
                'reason': f'Current P/E ({curr_val:.2f}) vs 60-month mean ({mean_60:.2f}): {pct_vs_mean:+.2f}%'
            }
    return results


def run_features_pipeline():
    log.info('Starting feature engineering calculation...')
    config = load_config()
    conn = get_connection(config)
    cursor = conn.cursor()

    try:
        # 1. Fetch S&P 500 Index Closes
        cursor.execute("SELECT ObservationDate, CAST(Value as float) FROM dbo.SeriesObservation WHERE SeriesCode = 'SP500' ORDER BY ObservationDate")
        sp500_data = [(r[0], float(r[1])) for r in cursor.fetchall()]
        if not sp500_data:
            raise RuntimeError('No S&P 500 data found in SeriesObservation. Run backfill first.')

        regime_results = calculate_regime(sp500_data)
        vol_results = calculate_realized_vol(sp500_data)

        # 2. Fetch VIX Data
        cursor.execute("SELECT ObservationDate, CAST(Value as float) FROM dbo.SeriesObservation WHERE SeriesCode = 'VIX' ORDER BY ObservationDate")
        vix_dict = {r[0]: float(r[1]) for r in cursor.fetchall()}

        # 3. Fetch Monthly P/E Data
        cursor.execute("SELECT ObservationDate, CAST(Value as float) FROM dbo.SeriesObservation WHERE SeriesCode = 'PE_MONTHLY' ORDER BY ObservationDate")
        pe_data = [(r[0], float(r[1])) for r in cursor.fetchall()]
        pe_results = calculate_pe_metrics(pe_data)

        # Precompute latest available monthly P/E for any daily date
        pe_sorted_dates = sorted(pe_results.keys())

        def get_latest_pe_for_date(target_date: date):
            applicable = [d for d in pe_sorted_dates if d <= target_date]
            if not applicable:
                return None, None
            latest_pe_date = applicable[-1]
            return latest_pe_date, pe_results[latest_pe_date]

        # 4. Fetch SPY and RSP ETF Prices for Concentration Proxy
        cursor.execute("SELECT PriceDate, CAST(CloseTotalReturnAdjusted as float) FROM dbo.DailyPrice WHERE Symbol = 'SPY' AND CloseTotalReturnAdjusted IS NOT NULL ORDER BY PriceDate")
        spy_prices = [(r[0], float(r[1])) for r in cursor.fetchall()]

        cursor.execute("SELECT PriceDate, CAST(CloseTotalReturnAdjusted as float) FROM dbo.DailyPrice WHERE Symbol = 'RSP' AND CloseTotalReturnAdjusted IS NOT NULL ORDER BY PriceDate")
        rsp_prices = [(r[0], float(r[1])) for r in cursor.fetchall()]

        concentration_results = calculate_concentration_proxy(spy_prices, rsp_prices)

        # 5. Fetch Constituent Roster & Compute Stock-Level Breadth Features
        cursor.execute("SELECT DISTINCT Symbol FROM dbo.v_LatestConstituents")
        roster_symbols = set(r[0] for r in cursor.fetchall())
        roster_count = len(roster_symbols)
        log.info(f'Observed constituent roster contains {roster_count} securities.')

        # Fetch all stock prices in one efficient query (excluding benchmark ETFs SPY/RSP)
        cursor.execute("""
            SELECT Symbol, PriceDate, CAST(CloseSplitAdjusted as float)
            FROM dbo.DailyPrice
            WHERE Symbol NOT IN ('SPY', 'RSP') AND CloseSplitAdjusted IS NOT NULL
            ORDER BY Symbol, PriceDate
        """)
        stock_price_rows = cursor.fetchall()

        # Group by symbol
        stock_prices_by_symbol: Dict[str, List[Tuple[date, float]]] = {}
        for sym, dt, close in stock_price_rows:
            stock_prices_by_symbol.setdefault(sym, []).append((dt, close))

        # Calculate 200-session SMA for each stock
        # stock_features: (Symbol, PriceDate, CloseSplitAdjusted, SMA200, AboveSMA200, IsEligibleBreadth)
        stock_features_to_save = []
        stock_status_by_date: Dict[date, List[Tuple[str, bool]]] = {}

        for sym, p_list in stock_prices_by_symbol.items():
            is_in_roster = sym in roster_symbols
            closes = [p[1] for p in p_list]
            dates = [p[0] for p in p_list]
            n_prices = len(closes)

            for i in range(n_prices):
                d = dates[i]
                c = closes[i]
                if i >= 199:
                    sma200 = sum(closes[i - 199 : i + 1]) / 200.0
                    above = c > sma200
                    is_eligible = is_in_roster
                    stock_features_to_save.append((sym, d, c, sma200, 1 if above else 0, 1 if is_eligible else 0))
                    if is_in_roster:
                        stock_status_by_date.setdefault(d, []).append((sym, above))
                else:
                    stock_features_to_save.append((sym, d, c, None, None, 0))

        log.info(f'Calculated {len(stock_features_to_save)} stock-level feature rows.')

        # 6. Save StockDailyFeatures in batches
        cursor.execute("DELETE FROM dbo.StockDailyFeatures")
        cursor.fast_executemany = True
        insert_stock_sql = """
            INSERT INTO dbo.StockDailyFeatures (Symbol, PriceDate, CloseSplitAdjusted, SMA200, AboveSMA200, IsEligibleBreadth)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        batch_size = 5000
        for i in range(0, len(stock_features_to_save), batch_size):
            cursor.executemany(insert_stock_sql, stock_features_to_save[i : i + batch_size])
        conn.commit()
        log.info('StockDailyFeatures committed successfully.')

        # 7. Assemble and Save DailyMarketMetrics
        all_trading_dates = sorted(regime_results.keys())
        market_metrics_to_save = []
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

        for d in all_trading_dates:
            reg = regime_results.get(d, {})
            c_proxy = concentration_results.get(d, {})
            vix_close = vix_dict.get(d)
            realized_vol = vol_results.get(d)

            pe_obs_date, pe_info = get_latest_pe_for_date(d)
            curr_pe = pe_info['current_pe'] if pe_info else None
            hist_pe_mean = pe_info['historical_mean'] if pe_info else None
            pe_vs_mean_pct = pe_info['pct_vs_mean'] if pe_info else None

            # Breadth calculations
            stocks_today = stock_status_by_date.get(d, [])
            eligible_count = len(stocks_today)
            above_count = sum(1 for _, is_above in stocks_today if is_above)
            excluded_count = max(0, roster_count - eligible_count)
            coverage_pct = (eligible_count / roster_count * 100.0) if roster_count > 0 else 0.0

            if eligible_count > 0:
                health_pct = (above_count / eligible_count) * 100.0
                if coverage_pct < 95.0:
                    health_band = 'Suppressed'
                    breadth_reason = f'Warning: Data coverage is only {coverage_pct:.1f}% (< 95% threshold). Band suppressed. {above_count}/{eligible_count} stocks ({health_pct:.1f}%) above 200 SMA.'
                else:
                    if health_pct < 40.0:
                        health_band = 'Weak'
                    elif health_pct <= 60.0:
                        health_band = 'Mixed'
                    else:
                        health_band = 'Strong'
                    breadth_reason = f'{above_count} of {eligible_count} eligible stocks ({health_pct:.1f}%) are above their 200-session average. Band: {health_band}.'
            else:
                health_pct = None
                health_band = None
                breadth_reason = 'No constituent price history available for this date.'

            # Stress Summary Reason
            stress_parts = []
            if vix_close is not None:
                stress_parts.append(f'VIX: {vix_close:.2f}')
            if realized_vol is not None:
                stress_parts.append(f'20d Realized Vol: {realized_vol:.2f}%')
            if curr_pe is not None and hist_pe_mean is not None:
                stress_parts.append(f'P/E: {curr_pe:.2f} ({pe_vs_mean_pct:+.1f}% vs 60m mean {hist_pe_mean:.2f})')
            stress_reason = ' | '.join(stress_parts) if stress_parts else 'Stress data unavailable'

            # Overall Quality Status
            if reg.get('regime') == 'Unavailable' or coverage_pct < 90.0:
                quality_status = 'INCOMPLETE'
                quality_notes = 'Warming up or missing historical constituent price data.'
            elif coverage_pct < 95.0:
                quality_status = 'WARNING'
                quality_notes = f'Breadth coverage {coverage_pct:.1f}% below 95% benchmark.'
            else:
                quality_status = 'OK'
                quality_notes = 'All required observations and thresholds verified.'

            market_metrics_to_save.append((
                d,
                reg.get('close'),
                reg.get('sma200'),
                reg.get('sma200_20d_ago'),
                reg.get('regime', 'Unavailable'),
                above_count,
                eligible_count,
                roster_count,
                excluded_count,
                round(coverage_pct, 4) if coverage_pct is not None else None,
                round(health_pct, 4) if health_pct is not None else None,
                health_band,
                c_proxy.get('spy_30d_return'),
                c_proxy.get('rsp_30d_return'),
                c_proxy.get('leadership_gap'),
                vix_close,
                d if vix_close is not None else None,
                realized_vol,
                curr_pe,
                hist_pe_mean,
                pe_vs_mean_pct
            ))

        cursor.execute("DELETE FROM dbo.DailyMarketMetrics")
        insert_metric_sql = """
            INSERT INTO dbo.DailyMarketMetrics (
                TradingDate,
                IndexClose, IndexSMA200, IndexSMA200_20d_ago, Regime,
                BreadthAboveCount, BreadthEligibleCount, BreadthRosterCount, BreadthExcludedCount,
                BreadthCoveragePct, BreadthHealthPct, HealthBand,
                SPY_30d_Return, RSP_30d_Return, LeadershipGap_PctPoints,
                VIX_Close, VIX_Date, RealizedVol_20d_Annualized,
                Current_PE, Historical_PE_60m_Mean, PE_vs_Historical_Mean_Pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(insert_metric_sql, market_metrics_to_save)
        conn.commit()
        log.info(f'Saved {len(market_metrics_to_save)} rows to DailyMarketMetrics.')
        print(f'Successfully calculated features for {len(market_metrics_to_save)} trading dates.')

    except Exception as exc:
        conn.rollback()
        log.exception(f'Features pipeline failed: {exc}')
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    run_features_pipeline()
