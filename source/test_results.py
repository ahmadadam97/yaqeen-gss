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

    def test_prayer_is_weighted_within_upbringing(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as select * from (values
                ('Protestant','Daily',1,3),('Protestant','Never',6,1),(null,'Daily',1,9),('Protestant',null,null,9))
                r(relig16,pray,pray_value,wtssps_value)""")
            rows = con.execute(analysis("01_prayer")).fetchall()
            self.assertEqual(rows[0], ("Protestant", "Daily", 1, 2, 50, 75, True))
            self.assertEqual(len(rows), 2)

    def test_industry_leader_is_weighted_among_workers_with_a_z_for_the_lead(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as select * from (values
                (true,'BA','Schools',3),(true,'BA','Schools',1),(true,'BA','Hospitals',2),(true,'BA','Farms',1),
                (false,'BA','Farms',90),(true,'BA',null,90))
                r(is_working,degree,indus10,wtssps_value)""")
            query = con.execute(analysis("03_industry"))
            row = dict(zip([column[0] for column in query.description], query.fetchone()))
            self.assertEqual((row["industry"], row["wtssps_pct"], row["n"], row["group_n"]), ("Schools", 57.14, 2, 4))
            self.assertEqual((row["runner_up_industry"], row["runner_up_wtssps_pct"]), ("Hospitals", 28.57))
            self.assertEqual(row["wtssps_lead_z"], 0.59)

    def test_tv_is_limited_to_workers_with_both_answers(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as select * from (values
                (true,'Very satisfied',1,2,3),(true,'Very satisfied',1,4,1),
                (false,'Very satisfied',1,20,50),(true,null,null,1,1))
                r(is_working,satjob,satjob_value,tvhours_value,wtssps_value)""")
            rows = con.execute(analysis("04_tv_satisfaction")).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][1:], ("Very satisfied", 2, 3, 2.5, 2))

    def test_ever_work_bounds_and_industry_narrowing(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as select * from (values
                (false,true,'YES',5,'Schools',3),(false,true,'NO',5,null,1),
                (false,false,null,4,'Farms',2),(false,false,null,4,null,2),(true,false,null,1,'Farms',50))
                r(is_working,ever_work_eligible,evwork,wrkstat_value,indus10,wtssps_value)""")
            query = con.execute(analysis("05_ever_work"))
            row = dict(zip([column[0] for column in query.description], query.fetchone()))
            self.assertEqual((row["nonworking_n"], row["valid_n"], row["job_seekers_routed_out_n"]), (4, 2, 2))
            self.assertEqual(row["wtssps_yes_pct_of_valid"], 75)
            self.assertEqual((row["wtssps_lower_bound_pct"], row["wtssps_upper_bound_pct"]), (37.5, 87.5))
            self.assertEqual(row["wtssps_lower_bound_with_industry_pct"], 62.5)
            self.assertEqual((row["yes_with_industry_n"], row["no_with_industry_n"], row["job_seekers_with_industry_n"]), (1, 0, 1))

    def test_weight_sensitivity_compares_both_weights(self):
        with duckdb.connect() as con:
            con.execute("""create table respondents as select * from (values
                (2014,'YES',3,1,true,null,'Never','BA','Schools'),(2014,'NO',1,3,true,null,'Every day','BA','Farms'))
                r(survey_year,postlife,wtssps_value,wtssnrps_value,is_working,evwork,news,degree,indus10)""")
            rows = {row[0]: row[1:] for row in con.execute(analysis("10_weight_sensitivity")).fetchall()}
            self.assertEqual(rows["Q2 believes in life after death"], ("2014", 75, 25, -50, None))
            self.assertEqual(rows["Q3 share of the leading industry"], ("BA", 75, 75, 0, False))
