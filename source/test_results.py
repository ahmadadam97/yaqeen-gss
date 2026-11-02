from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import duckdb
from load import ROOT
from run import publish_results


class ResultsTests(unittest.TestCase):
    def test_late_query_failure_preserves_prior_outputs(self):
        with TemporaryDirectory(dir=ROOT) as tmp, duckdb.connect() as con:
            folder = Path(tmp)
            results = folder / "results"
            results.mkdir()
            old = results / "01.csv"
            old.write_text("previous successful result")
            (folder / "01.sql").write_text("select 1 as example")
            (folder / "02.sql").write_text("select * from missing_table")
            with self.assertRaises(duckdb.CatalogException):
                publish_results(con, folder, results)
            self.assertEqual(old.read_text(), "previous successful result")
            self.assertFalse((results / "_SUCCESS").exists())

    def test_zero_coverage_wave_is_visible(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as
                select * from (values (2014,'Very interested'),(2016,null),(2016,null))
                t(survey_year,inttech)""")
            sql = (ROOT / "source/sql/08_technology_interest.sql").read_text()
            rows = con.execute(sql).fetchall()
            self.assertIn(("2016", "No valid responses", 0, 0, 2, None, 0), rows)
