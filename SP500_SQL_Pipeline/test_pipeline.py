"""Offline integrity checks. Run: python -m unittest -v test_pipeline.py"""
import json
import sqlite3
import unittest
from datetime import date, datetime, timezone
import pipeline as p


class ParsingTests(unittest.TestCase):
    def test_fred_skips_market_holidays_without_interpolating(self):
        body = b'observation_date,SP500\n2022-06-15,3789.99\n2022-06-16,.\n'
        self.assertEqual(p.parse_fred(body, date(2022,6,1), date(2022,6,30)), [(date(2022,6,15),3789.99)])

    def test_fred_excludes_future(self):
        body = b'DATE,SP500\n2022-06-15,3789.99\n2022-06-16,4000\n'
        self.assertEqual(len(p.parse_fred(body, date(2022,6,1), date(2022,6,15))), 1)

    def test_vix_uses_close(self):
        body = b'DATE,OPEN,HIGH,LOW,CLOSE\n06/15/2022,30,31,28,29.62\n'
        self.assertEqual(p.parse_vix(body, date(2022,6,1), date(2022,6,30))[0][1], 29.62)

    def test_pe_does_not_mislabel_live_estimate_as_monthly_history(self):
        body = b'''<table id="datatable"><tr><th>Date</th><th>Value</th></tr>
        <tr><td>Nov 10, 2026</td><td>30.0</td></tr>
        <tr><td>Nov 1, 2026</td><td>29.0</td></tr>
        <tr><td>Oct 1, 2026</td><td>28.0</td></tr></table>'''
        self.assertEqual(p.parse_pe(body, date(2025,1,1), date(2026,11,10)), [(date(2026,10,1),28.0)])

    def test_rejects_duplicate_dates(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            p.unique_sorted([(date(2022,1,1), 1), (date(2022,1,1), 2)])

    def test_rejects_blocked_html(self):
        with self.assertRaises(ValueError):
            p.parse_fred(b'<html>Access denied</html>', date(2022,1,1), date(2022,2,1))

    def test_prices_preserve_two_adjustment_types_and_missing_values(self):
        timestamps = [int(datetime(2022,6,d,13,30,tzinfo=timezone.utc).timestamp()) for d in (14,15,16)]
        data = {'chart': {'result': [{'timestamp':timestamps, 'indicators': {
            'quote':[{'close':[100,101,None],'volume':[10,None,20]}],
            'adjclose':[{'adjclose':[98,None,None]}]}}], 'error':None}}
        rows = p.parse_yahoo(json.dumps(data).encode(), date(2022,6,1), date(2022,6,30))
        self.assertEqual(rows, [(date(2022,6,14),100,98,10),(date(2022,6,15),101,None,None)])

    def test_empty_or_nonfinite_values_not_inserted(self):
        for value in [None, '', 'NaN', 'inf', -1, 0]:
            self.assertIsNone(p.positive(value))

    def test_roster_keeps_share_classes_and_maps_provider_symbol(self):
        rows = ''.join(f'<tr><td>A{i}</td><td>Name</td><td>Tech</td><td>123</td></tr>' for i in range(498))
        rows += '<tr><td>BRK.B</td><td>Berkshire</td><td>Financials</td><td>1067983</td></tr>'
        rows += '<tr><td>GOOG</td><td>Alphabet</td><td>Communication</td><td>1652044</td></tr>'
        rows += '<tr><td>GOOGL</td><td>Alphabet</td><td>Communication</td><td>1652044</td></tr>'
        body = ('<table id="constituents"><tr><th>Symbol</th><th>Security</th><th>GICS Sector</th><th>CIK</th></tr>'+rows+'</table>').encode()
        roster = p.parse_roster(body)
        self.assertEqual(len(roster), 501)
        brk = next(r for r in roster if r[0]=='BRK.B')
        self.assertEqual(brk[1], 'BRK-B')
        self.assertEqual(brk[4], '0001067983')

    def test_roster_rejects_suspiciously_short_response(self):
        body = b'<table id="constituents"><tr><th>Symbol</th><th>Security</th><th>GICS Sector</th><th>CIK</th></tr><tr><td>AAPL</td><td>Apple</td><td>Tech</td><td>320193</td></tr></table>'
        with self.assertRaisesRegex(ValueError, 'roster size'):
            p.parse_roster(body)

    def test_odbc_escapes_connection_value(self):
        self.assertEqual(p.odbc_value('server};password=x'), '{server}};password=x}')

    def test_leap_year_start(self):
        self.assertEqual(p.shift_years(date(2024,2,29), -1), date(2023,2,28))


class TransactionLogicTests(unittest.TestCase):
    """Exercise atomic replacement in a local SQL harness, NOT a SQL Server integration test."""
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute("ATTACH DATABASE ':memory:' AS dbo")
        self.db.execute('CREATE TABLE dbo.SeriesObservation (SeriesCode TEXT, ObservationDate TEXT, '
                        'Value REAL CHECK(Value>0), Frequency TEXT, Source TEXT, LastLoadRunId TEXT, '
                        'PRIMARY KEY(SeriesCode,ObservationDate))')
        self.db.execute('CREATE TABLE dbo.DailyPrice (Symbol TEXT, PriceDate TEXT, '
                        'CloseSplitAdjusted REAL CHECK(CloseSplitAdjusted>0), '
                        'CloseTotalReturnAdjusted REAL, Volume INTEGER, InstrumentType TEXT, Source TEXT, '
                        'LastLoadRunId TEXT, PRIMARY KEY(Symbol,PriceDate))')
        db = self.db
        class Adapter:
            def cursor(self):
                return self
            def execute(self, sql, *params):
                return db.execute(sql, tuple(v.isoformat() if isinstance(v,date) else v for v in params))
            def executemany(self, sql, params):
                return db.executemany(sql, [tuple(v.isoformat() if isinstance(v,date) else v for v in row) for row in params])
        self.conn = Adapter()

    def tearDown(self):
        self.db.close()

    def test_failed_replacement_rolls_back_to_prior_good_data(self):
        start, end = date(2022,6,1), date(2022,6,30)
        p.replace_series(self.conn, 'run1', 'SP500', 'FRED', 'daily', [(date(2022,6,15),3789.99)], start, end)
        self.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            p.replace_series(self.conn, 'run2', 'SP500', 'FRED', 'daily', [(date(2022,6,15),-1)], start, end)
        self.db.rollback()
        self.assertEqual(self.db.execute('SELECT Value,LastLoadRunId FROM dbo.SeriesObservation').fetchone(), (3789.99,'run1'))

    def test_rerun_updates_adjustments_without_duplicate_prices(self):
        d = date(2022,6,15)
        p.replace_prices(self.conn,'run1','SPY','etf',[(d,100,98,10)],d,d)
        self.db.commit()
        p.replace_prices(self.conn,'run2','SPY','etf',[(d,100,97,10)],d,d)
        self.db.commit()
        self.assertEqual(self.db.execute('SELECT COUNT(*),CloseTotalReturnAdjusted FROM dbo.DailyPrice').fetchone(), (1,97))


if __name__ == '__main__':
    unittest.main()
