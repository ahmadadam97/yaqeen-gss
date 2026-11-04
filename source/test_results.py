from pathlib import Path
from tempfile import TemporaryDirectory
import json
import logging
import re
import unittest
from unittest.mock import patch

import duckdb
from load import ROOT
from run import definition_paths, log_dbt_failures, publish_run, main
from snapshot import definition_digest, digest, current_run


def analysis(name):
    """The dbt analysis with each ref() reduced to a bare table name, so a test can supply small fixtures."""
    sql = (ROOT / "dbt/analyses" / f"{name}.sql").read_text(encoding="utf8")
    return re.sub(r"\{\{ ref\('(\w+)'\) \}\}", r"\1", sql)


class ResultsTests(unittest.TestCase):
    def test_definitions_ignore_folders_above_the_repository(self):
        with TemporaryDirectory(dir=ROOT) as tmp:
            root = Path(tmp) / "logs" / "repo"
            for name in ("docs/extracts.csv", "requirements.lock", "dbt/models/a.sql", "dbt/dbt_project.yml",
                         "dbt/seeds/b.csv", "source/c.py", "dbt/target/d.sql", "dbt/logs/e.sql"):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text("x")
            found = {p.relative_to(root).as_posix() for p in definition_paths(root)}
            self.assertEqual(found, {"docs/extracts.csv", "requirements.lock", "dbt/models/a.sql",
                                     "dbt/dbt_project.yml", "dbt/seeds/b.csv", "source/c.py"})

    def test_definition_hash_ignores_line_endings(self):
        with TemporaryDirectory(dir=ROOT) as tmp:
            lf, crlf = Path(tmp) / "lf.sql", Path(tmp) / "crlf.sql"
            lf.write_bytes(b"select 1\nfrom t\n")
            crlf.write_bytes(b"select 1\r\nfrom t\r\n")
            self.assertEqual(definition_digest(lf), definition_digest(crlf))

    def test_failed_dbt_nodes_are_named_in_the_run_log(self):
        with TemporaryDirectory(dir=ROOT) as tmp:
            target = Path(tmp)
            (target / "run_results.json").write_text(json.dumps({"results": [
                {"status": "pass", "unique_id": "test.gss.fine", "message": None},
                {"status": "fail", "unique_id": "test.gss.wave_coverage", "message": "Got 1 result"}]}))
            with self.assertLogs(level="ERROR") as logs:
                log_dbt_failures(target)
            self.assertEqual(len(logs.output), 1)
            self.assertIn("wave_coverage", logs.output[0])
            log_dbt_failures(target / "absent")

    def test_required_answers_are_weighted_over_valid_answers_only(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as select * from (values
                (2014,'YES','answer',1),(2014,'NO','answer',3),(2014,null,'dont_know',90),(2014,null,'not_asked_ballot',90))
                r(survey_year,postlife,postlife_status,wtssps_value)""")
            row = con.execute(analysis("02_afterlife")).fetchone()
            self.assertEqual(row[:6], (2014,4,2,1,50,25))
            self.assertEqual(row[6:9], (0,1,0))

    def test_wave_change_reports_weighted_news_and_tv(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as select * from (values
                (2014,'Every day',2,3),(2014,'Never',4,1),(2016,'Every day',2,1),(2016,'Never',4,3))
                r(survey_year,news,tvhours_value,wtssps_value)""")
            query = con.execute(analysis("06_wave_changes"))
            names = [column[0] for column in query.description]
            first, second = [dict(zip(names, row)) for row in query.fetchall()]
            self.assertEqual((first["daily_news_pct"], first["wtssps_daily_news_pct"]), (50, 75))
            self.assertEqual((second["wtssps_daily_news_pct"], second["wtssps_news_change_pp"]), (25, -50))
            self.assertEqual((first["wtssps_mean_tv_hours"], second["wtssps_mean_tv_hours"]), (2.5, 3.5))
            self.assertEqual(second["wtssps_never_change_pp"], 50)

    def test_overlap_audit_finds_cuts_through_the_seed(self):
        with duckdb.connect() as con:
            con.execute("""create table stg_membership as select * from (values
                ('renamed_a.json',2014,1),('renamed_a.json',2016,2),('renamed_b.json',2016,2))
                m(filename,survey_year,respondent_id)""")
            con.execute("create table extract_cuts as select * from (values ('renamed_a.json','A'),('renamed_b.json','B')) c(filename,cut)")
            con.execute("create table respondents as select distinct survey_year,respondent_id from stg_membership")
            self.assertEqual(con.execute(analysis("07_overlap")).fetchone()[:4], (2,1,1,2))

    def test_complete_run_is_published_and_tampering_is_rejected(self):
        with TemporaryDirectory(dir=ROOT) as tmp:
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
        with TemporaryDirectory(dir=ROOT) as tmp:
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
        with TemporaryDirectory(dir=ROOT) as tmp:
            build = Path(tmp)
            (build / "LATEST").write_text("prior")
            with patch.dict("os.environ", {}, clear=True), patch("run.build_root",return_value=build):
                with patch("run.load"), patch("run.logging.FileHandler",return_value=logging.NullHandler()), patch("run.subprocess.run",side_effect=RuntimeError("bad model")):
                    with self.assertLogs(level="ERROR"), self.assertRaisesRegex(RuntimeError, "bad model"):
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
            faith = con.execute(analysis("10_prayer_afterlife")).fetchall()
            self.assertEqual(faith[0][2:], (3,2,1,50,2,25,2,50))
            self.assertEqual(faith[1][-1], 0)
            media = con.execute(analysis("11_media_by_age")).fetchall()
            self.assertEqual(media[0][2:], (3,3,2,2,66.67,50,5))
            self.assertEqual(media[1][-3:], (0,None,None))

    def test_pair_overlap_stays_scoped_when_a_third_cut_is_added(self):
        with duckdb.connect() as con:
            con.execute("""create table stg_membership as select * from (values
                ('yaqeen_cut_a_2014_2016.json',2014,1),('yaqeen_cut_a_2014_2016.json',2016,2),
                ('yaqeen_cut_b_2016_2018.json',2016,2),('yaqeen_cut_b_2016_2018.json',2018,1),
                ('third.json',2016,2),('third.json',2018,9))
                m(filename,survey_year,respondent_id)""")
            con.execute("""create table extract_cuts as select * from (values
                ('yaqeen_cut_a_2014_2016.json','A'),('yaqeen_cut_b_2016_2018.json','B')) c(filename,cut)""")
            con.execute("""create table respondents as
                select distinct survey_year,respondent_id from stg_membership""")
            sql = analysis("07_overlap")
            row = con.execute(sql).fetchone()
            self.assertEqual(row, (2,2,1,3,3,3,2,50,50,0,1))
            con.execute("insert into respondents values (2016,2)")
            row = con.execute(sql).fetchone()
            self.assertEqual((row[4],row[5],row[9]), (4,3,1))

    def test_report_summary_recomputes_temporary_absence_count(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as select * from (values
                (3,true,'Very satisfied',2),(1,true,'Very satisfied',2),(4,false,null,null))
                r(wrkstat_value,is_working,satjob,tvhours_value)""")
            sql = analysis("12_report_summary")
            self.assertEqual(con.execute(sql).fetchone(), (1,2,2,2,0))
            con.execute("insert into respondents values (3,true,'Very satisfied',2)")
            self.assertEqual(con.execute(sql).fetchone(), (2,3,3,3,0))

    def test_zero_coverage_wave_is_visible(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as
                select * from (values (2014,'Very interested'),(2016,null),(2016,null))
                t(survey_year,inttech)""")
            rows = con.execute(analysis("08_technology_interest")).fetchall()
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
            rows = con.execute(analysis("13_web_sensitivity")).fetchall()
            self.assertEqual(rows, [("18-34",1,5)])
