from pathlib import Path
from tempfile import TemporaryDirectory
import json
import logging
import unittest
from unittest.mock import patch

import duckdb
from load import ROOT
from run import publish_results, publish_run, main
from snapshot import digest, current_run


class ResultsTests(unittest.TestCase):
    def test_complete_run_is_published_and_tampering_is_rejected(self):
        with TemporaryDirectory(dir=ROOT / "build") as tmp:
            build = Path(tmp)
            (build / "runs").mkdir()
            candidate = build / "candidate"
            candidate.mkdir()
            (candidate / "result.csv").write_text("verified")
            manifest = dict(run_id="a"*32, outputs={"result.csv":digest(candidate/"result.csv")})
            publish_run(candidate, build, manifest)
            with patch.dict("os.environ", {}, clear=True):
                folder, checked = current_run(build)
                self.assertEqual(checked["run_id"], "a"*32)
                with patch.dict("os.environ", {"GSS_DB":str(build/"wrong.duckdb")}):
                    with self.assertRaisesRegex(ValueError, "differs"):
                        current_run(build)
                (folder / "result.csv").write_text("changed")
                with self.assertRaisesRegex(ValueError, "changed"):
                    current_run(build)

    def test_failed_pointer_update_preserves_the_previous_publication(self):
        with TemporaryDirectory(dir=ROOT / "build") as tmp:
            build = Path(tmp)
            (build / "runs").mkdir()
            (build / "LATEST").write_text("prior")
            candidate = build / "candidate"
            candidate.mkdir()
            replace = Path.replace
            def fail_pointer(path, target):
                if Path(target).name == "LATEST":
                    raise PermissionError("simulated locked pointer")
                return replace(path, target)
            with patch.object(Path, "replace", fail_pointer):
                with self.assertRaises(PermissionError):
                    publish_run(candidate, build, dict(run_id="b"*32, outputs={}))
            self.assertEqual((build / "LATEST").read_text(), "prior")

    def test_failed_dbt_keeps_latest_and_cleans_candidate(self):
        with TemporaryDirectory(dir=ROOT / "build") as tmp:
            build = Path(tmp)
            (build / "LATEST").write_text("prior")
            with patch.dict("os.environ", {}, clear=True), patch("run.build_root",return_value=build):
                with patch("run.load"), patch("run.logging.FileHandler",return_value=logging.NullHandler()), patch("run.subprocess.run",side_effect=RuntimeError("bad model")):
                    with self.assertRaisesRegex(RuntimeError, "bad model"):
                        main()
            self.assertEqual((build / "LATEST").read_text(), "prior")
            self.assertFalse((build / ".run.lock").exists())
            self.assertEqual(list((build / "runs").iterdir()), [])

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

    def test_zero_coverage_wave_is_visible(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as
                select * from (values (2014,'Very interested'),(2016,null),(2016,null))
                t(survey_year,inttech)""")
            rows = con.execute((ROOT / "source/sql/08_technology_interest.sql").read_text()).fetchall()
            self.assertIn(("2016", "No valid responses", 0, 0, 2, None, 0), rows)

    def test_explicit_nonuser_sensitivity_preserves_ordinary_missing(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as select * from (values
                (2018,1,20,'Every day',null),(2018,2,21,'Never',null),(2018,3,22,'Never',10))
                r(survey_year,respondent_id,age_value,news,web_hours_weekly)""")
            con.execute("""create table answers as select * from (values
                (2018,1,'usewww','NO','answer'),(2018,1,'wwwhr',null,'inapplicable'),(2018,1,'wwwmin',null,'inapplicable'),
                (2018,2,'usewww',null,'no_answer'),(2018,2,'wwwhr',null,'no_answer'),(2018,2,'wwwmin',null,'no_answer'),
                (2018,3,'usewww','YES','answer'),(2018,3,'wwwhr','10','answer'),(2018,3,'wwwmin','0','answer'))
                a(survey_year,respondent_id,variable,answer_label,status)""")
            rows = con.execute((ROOT / "source/sql/13_web_sensitivity.sql").read_text()).fetchall()
            self.assertEqual(rows, [("18-34",1,5)])
