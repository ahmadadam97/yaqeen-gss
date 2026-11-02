from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import duckdb
from load import ROOT
from run import publish_results


class ResultsTests(unittest.TestCase):
    def test_retired_query_is_not_published(self):
        with TemporaryDirectory(dir=ROOT) as tmp, duckdb.connect() as con:
            folder = Path(tmp)
            results = folder / "results"
            results.mkdir()
            (results / "old.csv").write_text("retired")
            (folder / "new.sql").write_text("select 1 as n")
            with patch("run.summarize", return_value={"n":1}):
                publish_results(con, folder, results)
            self.assertEqual({f.name for f in results.iterdir()}, {"new.csv","04_tv_rank_tests.csv","_SUCCESS"})

    def test_weighted_denominator_and_media_routing(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as select * from (values
                (2014,1,'YES',1,2,18,'Every day',0), (2014,2,'NO',3,2,34,'Never',10),
                (2014,1,null,90,90,30,'Every day',null), (2014,6,'NO',1,1,55,null,null))
                r(survey_year,pray_value,postlife,wtssps_value,wtssnrps_value,age_value,news,web_hours_weekly)""")
            root = ROOT / "source/sql"
            faith = con.execute((root / "10_prayer_afterlife.sql").read_text()).fetchall()
            self.assertEqual(faith[0][2:], (3,2,1,50,2,25,2,50))
            self.assertEqual(faith[1][-1], 0)
            media = con.execute((root / "11_media_by_age.sql").read_text()).fetchall()
            self.assertEqual(media[0][2:], (3,3,2,2,66.67,50,5))
            self.assertEqual(media[1][-3:], (0,None,None))

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
