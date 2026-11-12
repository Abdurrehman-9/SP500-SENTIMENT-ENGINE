"""Free-source market monitoring ingestion. Python 3.11+; Windows SQL Server.

No indicators or ML are fitted here. Current membership is never backdated.
Commands: dbcheck, backfill, daily, verify, sample (sample never writes SQL).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import logging
import math
import re
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
NY = ZoneInfo('America/New_York')
FRED = 'https://fred.stlouisfed.org/graph/fredgraph.csv'
CBOE = 'https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv'
MULTPL = 'https://www.multpl.com/s-p-500-pe-ratio/table/by-month'
ROSTER = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
YAHOO = 'https://query1.finance.yahoo.com/v8/finance/chart/'


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def shift_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def positive(value):
    if value in (None, '', '.', '-'):
        return None
    try:
        n = float(str(value).replace(',', '').strip())
    except ValueError:
        return None
    return n if math.isfinite(n) and n > 0 else None


class TableParser(HTMLParser):
    """Read a named HTML table, preserving cell text without scripts or footnotes."""
    def __init__(self, table_id):
        super().__init__(convert_charrefs=True)
        self.table_id, self.depth = table_id, 0
        self.rows, self.row, self.cell = [], None, None
        self.suppress = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            if self.depth:
                self.depth += 1
            elif dict(attrs).get('id') == self.table_id:
                self.depth = 1
        if not self.depth:
            return
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th'):
            self.cell = []
        elif tag in ('sup', 'script', 'style'):
            self.suppress += 1

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag in ('sup', 'script', 'style'):
            self.suppress = max(0, self.suppress - 1)
        elif tag in ('td', 'th') and self.cell is not None:
            if self.row is not None:
                self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == 'table':
            self.depth -= 1

    def handle_data(self, text):
        if self.depth and self.cell is not None and not self.suppress:
            self.cell.append(text)


def unique_sorted(rows):
    if not rows:
        raise ValueError('No valid observations returned; refusing an empty load.')
    keys = [r[0] for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate dates/symbols returned; inspect the raw response.')
    return sorted(rows, key=lambda x: x[0])


def parse_fred(body, start, end):
    rows = []
    reader = csv.DictReader(io.StringIO(body.decode('utf-8-sig')))
    if not reader.fieldnames or 'SP500' not in reader.fieldnames:
        raise ValueError('FRED CSV format changed or response is not CSV.')
    for r in reader:
        d = date.fromisoformat(r[reader.fieldnames[0]])
        n = positive(r['SP500'])
        if start <= d <= end and n is not None:
            rows.append((d, n))
    return unique_sorted(rows)


def parse_vix(body, start, end):
    reader = csv.DictReader(io.StringIO(body.decode('utf-8-sig')))
    if not reader.fieldnames or not {'DATE', 'CLOSE'} <= set(reader.fieldnames):
        raise ValueError('Cboe CSV format changed or response is not CSV.')
    rows = []
    for r in reader:
        d = datetime.strptime(r['DATE'], '%m/%d/%Y').date()
        n = positive(r['CLOSE'])
        if start <= d <= end and n is not None:
            rows.append((d, n))
    return unique_sorted(rows)


def parse_pe(body, start, end):
    parser = TableParser('datatable')
    parser.feed(body.decode('utf-8'))
    rows = []
    for r in parser.rows:
        if len(r) < 2:
            continue
        try:
            d = datetime.strptime(r[0], '%b %d, %Y').date()
        except ValueError:
            continue
        # Table may include a current-day estimate. Keep only completed months
        # and the first-of-month observations. Never manufacture daily P/E.
        if d.day != 1 or d >= end.replace(day=1):
            continue
        n = positive(r[1].replace('†', '').strip())
        if start <= d <= end and n is not None:
            rows.append((d, n))
    return unique_sorted(rows)


def parse_roster(body):
    parser = TableParser('constituents')
    parser.feed(body.decode('utf-8'))
    if not parser.rows:
        raise ValueError('Current constituent table missing or website blocked.')
    header = parser.rows[0]
    expected = ['Symbol', 'Security', 'GICS Sector', 'CIK']
    if not all(k in header for k in expected):
        raise ValueError('Constituent table columns changed.')
    indexes = [header.index(k) for k in expected]
    rows = []
    for row in parser.rows[1:]:
        if len(row) <= max(indexes):
            continue
        symbol, name, sector, cik = [row[i].strip() for i in indexes]
        if not re.fullmatch(r'[A-Z0-9.\-]{1,24}', symbol):
            raise ValueError(f'Unexpected ticker: {symbol!r}')
        cik = cik.zfill(10) if cik.isdigit() else None
        rows.append((symbol, symbol.replace('.', '-'), name, sector, cik))
    rows = unique_sorted(rows)
    if not 490 <= len(rows) <= 520:
        raise ValueError(f'Implausible roster size {len(rows)}; inspect source.')
    return rows


def parse_yahoo(body, start, end):
    obj = json.loads(body)
    chart = obj.get('chart', {})
    if chart.get('error') or not chart.get('result'):
        raise ValueError('Yahoo did not return a price series.')
    result = chart['result'][0]
    timestamps = result.get('timestamp') or []
    indicators = result.get('indicators', {})
    quotes = indicators.get('quote', [{}])[0]
    close = quotes.get('close') or []
    adj = indicators.get('adjclose', [{}])[0].get('adjclose') or []
    volume = quotes.get('volume') or []
    if len(close) != len(timestamps):
        raise ValueError('Yahoo timestamp/price lengths do not match.')
    rows = []
    for i, t in enumerate(timestamps):
        d = datetime.fromtimestamp(t, timezone.utc).astimezone(NY).date()
        c = positive(close[i])
        a = positive(adj[i]) if i < len(adj) else None
        v = volume[i] if i < len(volume) else None
        v = int(v) if v is not None and v >= 0 else None
        if start <= d <= end and c is not None:
            rows.append((d, c, a, v))
    return unique_sorted(rows)


def price_url(symbol, start, end):
    # Yahoo period2 is exclusive. Use New York midnight, then filter returned dates.
    a = int(datetime.combine(start, datetime.min.time(), NY).timestamp())
    b = int(datetime.combine(end + timedelta(days=1), datetime.min.time(), NY).timestamp())
    return YAHOO + quote(symbol, safe='') + '?' + urlencode({
        'period1': a, 'period2': b, 'interval': '1d',
        'events': 'div,splits', 'includeAdjustedClose': 'true'})


def download(url, config):
    import subprocess
    cmd = [
        'curl.exe', '-s', '-L',
        '--max-time', str(config.get('http_timeout_seconds', 30)),
        '--resolve', 'query1.finance.yahoo.com:443:69.147.80.15',
        '--resolve', 'query2.finance.yahoo.com:443:69.147.80.15',
        '--resolve', 'cdn.cboe.com:443:104.19.184.30',
        '--resolve', 'cdn-api.cboe.com:443:104.19.184.30',
    ]
    if 'yahoo.com' in url or 'wikipedia.org' in url or 'cboe.com' in url:
        cmd.extend(['-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'])

    cmd.append(url)

    for attempt in range(config['http_attempts']):
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=config.get('http_timeout_seconds', 30) + 5)
            if res.returncode == 0 and res.stdout:
                return res.stdout
            if attempt == config['http_attempts'] - 1:
                raise RuntimeError(f'Public download returned empty or error (code {res.returncode}): {res.stderr.decode(errors="replace")}')
        except Exception as exc:
            if attempt == config['http_attempts'] - 1:
                raise RuntimeError(f'Download failed after retries: {exc}') from None
        time.sleep(min(2 ** (attempt + 1), 10))
    raise RuntimeError('Download failed.')


def odbc_value(value):
    return '{' + str(value).replace('}', '}}') + '}'


def connect(config):
    try:
        import pyodbc
    except ImportError:
        raise RuntimeError('Install requirements.txt using the provided Windows commands.') from None
    driver = config['odbc_driver']
    if driver not in pyodbc.drivers():
        raise RuntimeError(f'Install {driver}. Detected drivers: {pyodbc.drivers()}')
    cs = (f'DRIVER={odbc_value(driver)};SERVER={odbc_value(config["sql_server"])};'
          f'DATABASE={odbc_value(config["sql_database"])};Trusted_Connection=yes;Encrypt=yes;'
          f'TrustServerCertificate={"yes" if config["trust_server_certificate"] else "no"};')
    try:
        conn = pyodbc.connect(cs, timeout=15, autocommit=False)
        if conn.execute("SELECT OBJECT_ID('dbo.FetchAudit', 'U')").fetchone()[0] is None:
            conn.close()
            raise RuntimeError('Run 01_create_database.sql in SSMS first.')
        conn.commit()
        return conn
    except pyodbc.Error as exc:
        raise RuntimeError('SQL connection failed. Match sql_server in config.json to SSMS, '
                           'use the same Windows user, and run 01_create_database.sql. '
                           f'ODBC detail: {exc}') from None


def acquire_lock(conn):
    r = conn.execute("""DECLARE @r int;
        EXEC @r = sys.sp_getapplock @Resource=N'SP500_ingestion',
        @LockMode='Exclusive', @LockOwner='Session', @LockTimeout=0;
        SELECT @r;""").fetchone()[0]
    conn.commit()
    if r < 0:
        raise RuntimeError('Another pipeline is running. Wait for it to finish.')


def replace_series(conn, run_id, code, source, frequency, rows, start, end):
    # Replacement and insertion happen in ONE transaction. Failed insert restores old rows.
    cur = conn.cursor()
    cur.execute('DELETE FROM dbo.SeriesObservation WHERE SeriesCode=? AND ObservationDate BETWEEN ? AND ?',
                code, start, end)
    cur.executemany('INSERT INTO dbo.SeriesObservation '
                    '(SeriesCode,ObservationDate,Value,Frequency,Source,LastLoadRunId) VALUES (?,?,?,?,?,?)',
                    [(code, d, n, frequency, source, run_id) for d, n in rows])


def supplement_series(conn, run_id, code, source, frequency, rows):
    """Fill missing series dates without overwriting primary source observations."""
    if not rows:
        return
    cur = conn.cursor()
    dates = [d for d, _ in rows]
    placeholders = ','.join('?' for _ in dates)
    cur.execute(f'DELETE FROM dbo.SeriesObservation WHERE SeriesCode=? AND ObservationDate IN ({placeholders})',
                code, *dates)
    cur.executemany('INSERT INTO dbo.SeriesObservation '
                    '(SeriesCode,ObservationDate,Value,Frequency,Source,LastLoadRunId) VALUES (?,?,?,?,?,?)',
                    [(code, d, n, frequency, source, run_id) for d, n in rows])


def replace_prices(conn, run_id, symbol, kind, rows, start, end):
    cur = conn.cursor()
    cur.execute('DELETE FROM dbo.DailyPrice WHERE Symbol=? AND PriceDate BETWEEN ? AND ?', symbol, start, end)
    cur.executemany('INSERT INTO dbo.DailyPrice '
                    '(Symbol,PriceDate,CloseSplitAdjusted,CloseTotalReturnAdjusted,Volume,'
                    'InstrumentType,Source,LastLoadRunId) VALUES (?,?,?,?,?,?,?,?)',
                    [(symbol, d, c, a, v, kind, 'Yahoo Finance', run_id) for d, c, a, v in rows])


def save_audit(conn, run_id, audit):
    conn.execute('INSERT INTO dbo.FetchAudit '
                 '(RunId,Dataset,SourceUrl,RetrievedUtc,Status,[RowCount],FirstDate,LastDate,RawFile,Sha256,Note) '
                 'VALUES (?,?,?,?,?,?,?,?,?,?,?)', run_id, audit['dataset'], audit['url'],
                 datetime.fromisoformat(audit['retrieved_utc']), audit['status'], audit['rows'],
                 audit.get('first_date'), audit.get('last_date'), audit.get('raw_file'),
                 audit.get('sha256'), audit.get('note', '')[:2000])


def verify(conn):
    queries = {
        'Most recent runs': 'SELECT TOP (5) StartedUtc, Mode, Status, Summary FROM dbo.PipelineRun ORDER BY StartedUtc DESC',
        'Series coverage': 'SELECT SeriesCode, COUNT(*) AS [Rows], MIN(ObservationDate) AS FirstDate, MAX(ObservationDate) AS LastDate FROM dbo.SeriesObservation GROUP BY SeriesCode',
        'Price coverage': 'SELECT InstrumentType,COUNT(DISTINCT Symbol) AS Symbols,COUNT(*) AS [Rows], MIN(PriceDate) AS FirstDate,MAX(PriceDate) AS LastDate FROM dbo.DailyPrice GROUP BY InstrumentType',
        'Latest roster': 'SELECT COUNT(*) AS Securities FROM dbo.v_LatestConstituents',
    }
    for title, query in queries.items():
        print('\n' + title)
        cur = conn.execute(query)
        print(' | '.join(c[0] for c in cur.description))
        for row in cur.fetchall():
            print(' | '.join(str(v) for v in row))
    conn.commit()


def run(args, config):
    today_ny = datetime.now(NY).date()
    end = args.end or today_ny - timedelta(days=1)
    if end >= today_ny:
        raise ValueError('--end must precede today in New York; intraday bars are excluded.')
    start = args.start or shift_years(end, -config['history_years']) - timedelta(days=config['warmup_calendar_days'])
    if start >= end:
        raise ValueError('Start date must precede end date.')
    pe_start = shift_years(end, -config['pe_history_years'])
    if args.command == 'daily' and (args.start or args.end):
        raise ValueError('daily uses the saved backfill start and automatic end date; omit date arguments.')
    conn = None
    if args.command != 'sample':
        conn = connect(config)
        if args.command in ('dbcheck', 'verify'):
            try:
                if args.command == 'verify':
                    verify(conn)
                else:
                    print('Connected successfully to ' + config['sql_database'])
                return 0
            finally:
                conn.close()
        acquire_lock(conn)
        # Preserve a fixed history origin so a later split/dividend refreshes ALL
        # previously stored Yahoo adjusted prices consistently, including old members.
        previous = conn.execute("SELECT MIN(RequestedStart) FROM dbo.PipelineRun WHERE Mode='backfill' AND Status IN ('success','partial')").fetchone()[0]
        conn.commit()
        if args.command == 'daily':
            if previous is None:
                conn.close()
                raise RuntimeError('Run backfill once before daily.')
            start = previous
        elif previous is not None:
            start = min(start, previous)
        # Prevent a historical rerun from mixing new adjustment factors with newer stored bars.
        existing_end = conn.execute('SELECT MAX(PriceDate) FROM dbo.DailyPrice').fetchone()[0]
        conn.commit()
        if existing_end and end < existing_end:
            conn.close()
            raise RuntimeError('--end is earlier than stored prices. Use the normal automatic end date.')

    run_id = str(uuid.uuid4())
    folder = ROOT / 'data' / 'raw' / run_id
    folder.mkdir(parents=True, exist_ok=True)
    audits = []
    benchmark_dates = set()
    report = {'run_id': run_id, 'mode': args.command, 'start': str(start), 'end': str(end),
              'membership_scope': 'current roster observed at retrieval; not historical membership',
              'datasets': audits, 'status': 'running'}
    if conn:
        conn.execute('INSERT INTO dbo.PipelineRun '
                     '(RunId,StartedUtc,Mode,RequestedStart,RequestedEnd,Status) VALUES (?,?,?,?,?,?)',
                     run_id, utcnow(), args.command, start, end, 'running')
        conn.commit()

    def checkpoint():
        dest = folder / 'report.json'
        temp = folder / 'report.tmp'
        temp.write_text(json.dumps(report, indent=2), encoding='utf-8')
        temp.replace(dest)

    def fetch(dataset, url, parse, write=None, is_roster=False, require_adjusted=False):
        audit = {'dataset': dataset, 'url': url, 'retrieved_utc': utcnow().isoformat(),
                 'status': 'failed', 'rows': 0}
        rows = None
        try:
            body = download(url, config)
            audit['retrieved_utc'] = utcnow().isoformat()
            filename = re.sub(r'[^A-Za-z0-9_.-]', '_', dataset) + '.raw'
            raw_path = folder / filename
            raw_path.write_bytes(body)
            audit.update(raw_file=str(raw_path.relative_to(ROOT)), sha256=hashlib.sha256(body).hexdigest())
            rows = parse(body)
            audit.update(rows=len(rows), status='ok')
            if not is_roster:
                audit.update(first_date=str(rows[0][0]), last_date=str(rows[-1][0]))
                if dataset != 'PE_MONTHLY' and (end - rows[-1][0]).days > 4:
                    audit.update(status='warning', note='Latest available date is more than 4 calendar days before requested end.')
                if dataset.startswith('PRICE_'):
                    actual_dates = {r[0] for r in rows}
                    expected_dates = {d for d in benchmark_dates if d >= rows[0][0]}
                    missing_sessions = expected_dates - actual_dates
                    if missing_sessions:
                        audit.update(status='warning', note=audit.get('note', '') +
                                     f' Missing {len(missing_sessions)} FRED benchmark sessions since first available price.')
                    if len(rows) < 200:
                        audit['note'] = (audit.get('note', '') + ' Fewer than 200 prices; not eligible for SMA200 yet.').strip()
                    missing = sum(r[2] is None for r in rows)
                    if missing:
                        audit.update(status='warning', note=audit.get('note', '') + f' Missing adjusted close on {missing} dates.')
                        if require_adjusted:
                            raise ValueError('ETF adjusted close is missing; cannot support comparable total returns.')
                elif dataset == 'PE_MONTHLY':
                    audit['note'] = 'Completed monthly observations only. Observation date is not historical publication date.'
                    if (end - rows[-1][0]).days > 75:
                        audit.update(status='warning', note=audit['note'] + ' Monthly series appears stale.')
            if conn and write:
                write(rows)
            if conn:
                save_audit(conn, run_id, audit)
                conn.commit()
            logging.info('%s: %s, %d rows, latest=%s %s', dataset, audit['status'], len(rows),
                         audit.get('last_date', 'snapshot'), audit.get('note', ''))
        except Exception as exc:
            if conn:
                conn.rollback()
            audit.update(status='failed', rows=0, note=str(exc)[:2000])
            rows = None
            if conn:
                save_audit(conn, run_id, audit)
                conn.commit()
            logging.error('%s: %s', dataset, exc)
        audits.append(audit)
        checkpoint()
        time.sleep(config['request_pause_seconds'])
        return rows

    try:
        def write_roster(rows):
            conn.cursor().executemany('INSERT INTO dbo.ConstituentSnapshot '
                '(RunId,SnapshotDate,Symbol,ProviderSymbol,CompanyName,Sector,Cik,SourceUrl) VALUES (?,?,?,?,?,?,?,?)',
                [(run_id, today_ny, *r, ROSTER) for r in rows])

        roster = fetch('CURRENT_CONSTITUENTS', ROSTER, parse_roster, write_roster, is_roster=True)
        if roster is None:
            raise RuntimeError('Cannot establish current membership. Run stopped; existing SQL data retained.')
        series = [
            ('SP500', FRED + '?' + urlencode({'id':'SP500', 'cosd':str(start), 'coed':str(end)}),
             parse_fred, start, 'FRED', 'daily'),
            ('VIX', CBOE, parse_vix, start, 'Cboe', 'daily'),
            ('PE_MONTHLY', MULTPL, parse_pe, pe_start, 'Multpl', 'monthly')]
        for code, url, parser, since, source, frequency in series:
            observations = fetch(code, url, lambda b, p=parser, s=since: p(b, s, end),
                  lambda rows, c=code, so=source, f=frequency, s=since:
                      replace_series(conn, run_id, c, so, f, rows, s, end))
            if code == 'SP500':
                fred_dates = {d for d, _ in (observations or [])}
                benchmark_dates.update(fred_dates)
                if not observations or observations[-1][0] < end:
                    fb_start = max(start, end - timedelta(days=10))
                    yahoo_spx = fetch(
                        'SP500_YAHOO_FALLBACK',
                        price_url('^GSPC', fb_start, end),
                        lambda b, s=fb_start: parse_yahoo(b, s, end),
                        lambda rows: supplement_series(
                            conn, run_id, 'SP500', 'Yahoo ^GSPC', 'daily',
                            [(d, round(c, 2)) for d, c, _, _ in rows if d not in fred_dates]
                        ),
                    )
                    if yahoo_spx:
                        added = [d for d, _, _, _ in yahoo_spx if d not in fred_dates]
                        benchmark_dates.update(added)
                        if added:
                            logging.info('SP500 supplemented %d session(s) from Yahoo ^GSPC: %s',
                                         len(added), ', '.join(str(d) for d in added))
        symbols = {r[0]: (r[1], 'stock') for r in roster}
        if args.command == 'sample':
            symbols = {s: symbols[s] for s in ('AAPL', 'MSFT', 'BRK.B') if s in symbols}
        elif conn:
            # Refresh previously captured members too; don't imply they are current members.
            for symbol, in conn.execute("SELECT DISTINCT Symbol FROM dbo.DailyPrice WHERE InstrumentType='stock'").fetchall():
                symbols.setdefault(symbol, (symbol.replace('.', '-'), 'stock'))
            conn.commit()
        symbols.update({'SPY': ('SPY', 'etf'), 'RSP': ('RSP', 'etf')})
        for symbol, (provider_symbol, kind) in sorted(symbols.items()):
            fetch('PRICE_' + symbol, price_url(provider_symbol, start, end),
                  lambda b: parse_yahoo(b, start, end),
                  lambda rows, s=symbol, k=kind: replace_prices(conn, run_id, s, k, rows, start, end),
                  require_adjusted=(kind == 'etf'))
        bad = [a['dataset'] for a in audits if a['status'] != 'ok']
        report['status'] = 'partial' if bad else 'success'
        report['summary'] = (f'{len(audits)} datasets checked; {len(bad)} failed or warned. '
                             'See report.json and FetchAudit. Missing values were not filled.')
        if conn:
            conn.execute('UPDATE dbo.PipelineRun SET FinishedUtc=?,Status=?,Summary=? WHERE RunId=?',
                         utcnow(), report['status'], report['summary'], run_id)
            conn.commit()
        logging.info('%s: %s', report['status'].upper(), report['summary'])
        return 2 if bad else 0
    except BaseException as exc:
        report.update(status='failed', summary=str(exc)[:2000] or 'Interrupted')
        if conn:
            conn.rollback()
            conn.execute('UPDATE dbo.PipelineRun SET FinishedUtc=?,Status=?,Summary=? WHERE RunId=?',
                         utcnow(), 'failed', report['summary'], run_id)
            conn.commit()
        raise
    finally:
        checkpoint()
        logging.info('Run report: %s', folder / 'report.json')
        if conn:
            conn.close()  # Also releases session application lock.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['dbcheck', 'backfill', 'daily', 'verify', 'sample'])
    parser.add_argument('--start', type=date.fromisoformat, help='Optional earliest price date, YYYY-MM-DD; include warm-up.')
    parser.add_argument('--end', type=date.fromisoformat, help='Optional last date, YYYY-MM-DD; default yesterday in New York.')
    parser.add_argument('--config', type=Path, default=ROOT / 'config.json')
    args = parser.parse_args()
    (ROOT / 'logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(ROOT / 'logs' / 'pipeline.log', encoding='utf-8'),
                                  logging.StreamHandler(sys.stdout)])
    try:
        config = json.loads(args.config.read_text(encoding='utf-8-sig'))
        if not 1 <= config['history_years'] <= 8:
            raise ValueError('history_years must be 1..8 (FRED SP500 has limited history).')
        if not 1 <= config['http_attempts'] <= 5 or config['request_pause_seconds'] < 0.5:
            raise ValueError('Use 1..5 HTTP attempts and at least 0.5 seconds between requests.')
        return run(args, config)
    except KeyboardInterrupt:
        logging.error('Interrupted. Completed datasets remain saved. Rerun the same command.')
        return 1
    except Exception as exc:
        logging.error('%s', exc)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
