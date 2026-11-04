"""Render the report from a successful pipeline run. Optional dependency: see README.

Every survey result comes from the published CSVs, and every measurement from the evidence files beside this script.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from snapshot import current_run
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parents[1]
RUN, MANIFEST = current_run()
MAX_BODY_PAGES = 5

INK, TEAL, MUTED, PALE, RULE, AMBER = (colors.HexColor(c) for c in ("#152F37", "#00675F", "#4D6265", "#E1EFEB", "#C9D6D2", "#A5522A"))
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.6, leading=12.9, textColor=INK, spaceAfter=5, alignment=TA_LEFT)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.5, leading=11.2, spaceAfter=0)
HEAD = ParagraphStyle("head", parent=SMALL, fontName="Helvetica-Bold", textColor=colors.white)
NOTE = ParagraphStyle("note", parent=BODY, fontSize=8.5, leading=11.2, textColor=MUTED)
TITLE = ParagraphStyle("title", parent=BODY, fontName="Helvetica-Bold", fontSize=21, leading=25, spaceAfter=3)
SUBTITLE = ParagraphStyle("subtitle", parent=BODY, fontSize=10.5, leading=14, textColor=MUTED, spaceAfter=8)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=12.5, leading=15, textColor=TEAL, spaceBefore=8, spaceAfter=3)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=9.8, leading=13, spaceBefore=3, spaceAfter=1, keepWithNext=1)
WIDTH = letter[0] - 1.5 * inch


def rows(name):
    with (RUN / "results" / f"{name}.csv").open(encoding="utf8", newline="") as f:
        return list(csv.DictReader(f))


def evidence(name):
    return json.loads((ROOT / "report" / name).read_text(encoding="utf8"))


def count(value):
    return f"{int(float(value)):,}"


def one(value):
    return f"{float(value):.1f}"


def p(text):
    return Paragraph(text, BODY)


def h1(text):
    return Paragraph(text, H1)


def h2(text):
    return Paragraph(text, H2)


def table(header, body, widths):
    """A ruled table whose text wraps. Widths are shares of the page."""
    data = [[Paragraph(cell, HEAD) for cell in header]] + [[Paragraph(str(cell), SMALL) for cell in row] for row in body]
    result = Table(data, colWidths=[share * WIDTH for share in widths], repeatRows=1)
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE), ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return result


def callout(text):
    box = Table([[Paragraph(text, ParagraphStyle("callout", parent=BODY, spaceAfter=0))]], colWidths=[WIDTH])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("LINEBEFORE", (0, 0), (0, -1), 3, TEAL),
                             ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                             ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    return box


def gap(points=5):
    return Spacer(1, points)


class Report(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.62 * inch,
                         bottomMargin=0.64 * inch, invariant=1, title="GSS survey pipeline report",
                         author="Candidate submission", subject="Yaqeen data engineering assignment")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="page", frames=frame, onPage=self.furniture))
        self.appendix_page = None

    def furniture(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(self.leftMargin, 0.42 * inch, "GSS survey pipeline report  |  Data: NORC General Social Survey, 2014, 2016, 2018")
        canvas.drawRightString(letter[0] - self.rightMargin, 0.42 * inch, f"Page {doc.page}")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(self.leftMargin, 0.56 * inch, letter[0] - self.rightMargin, 0.56 * inch)
        canvas.restoreState()

    def afterFlowable(self, flowable):
        """Add section bookmarks so a reader can jump around, and remember where the appendices start."""
        if isinstance(flowable, Paragraph) and flowable.style.name == "h1":
            text = flowable.getPlainText()
            key = f"section-{id(flowable)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0)
            if text.startswith("Appendix") and self.appendix_page is None:
                self.appendix_page = self.page


def story():
    prayer = {(r["upbringing"], r["frequency"]): r for r in rows("01_prayer")}
    small_groups = sorted({r["upbringing"] for r in rows("01_prayer") if r["is_small_group"].lower() == "true"})
    afterlife = rows("02_afterlife")
    industry = rows("03_industry")
    tv = rows("04_tv_satisfaction")
    tv_tests = rows("04_tv_rank_tests")[0]
    work = rows("05_ever_work")[0]
    waves = rows("06_wave_changes")
    overlap = rows("07_overlap")[0]
    summary = rows("12_report_summary")[0]
    ballots = rows("09_ballot_coverage")
    sensitivity = {(r["question"], r["definition"], r["subgroup"]): r for r in rows("14_work_status_sensitivity")}
    costs = evidence("materialization-costs.json")
    scale = evidence("scale-evidence.json")
    with (ROOT / "report/failure-evidence.csv").open(encoding="utf8", newline="") as f:
        failures = list(csv.DictReader(f))
    if any(r["as_expected"] != "true" for r in failures):
        raise ValueError("failure-evidence.csv shows an unexpected result; rerun source/failure_check.py")
    if costs["inputs"] != MANIFEST["inputs"] or any(MANIFEST["definitions"].get(name) != value for name, value in (costs["model_hashes"] | costs["query_hashes"]).items()):
        raise ValueError("Benchmark belongs to different inputs or models; rerun source/benchmark.py")

    def valid_share(year, variable):
        cells = [r for r in ballots if r["survey_year"] == year and r["variable"] == variable]
        return round(100 * sum(int(r["valid_n"]) for r in cells) / sum(int(r["interviews"]) for r in cells))

    def shares(variable):
        values = [valid_share(year, variable) for year in ("2014", "2016", "2018")]
        return f"{values[0]}% in each" if len(set(values)) == 1 else ", ".join(f"{value}%" for value in values)

    def pray_daily(group):
        r = prayer[(group, "Several times a day")]
        return f"{one(r['wtssps_pct'])}% (n={count(r['group_n'])})"

    if summary["groups_with_median_not_two"] != "0":
        raise ValueError("The Q4 text says median TV is 2 hours in every group; review it")
    first, second, third = waves
    tv_by_group = {r["satisfaction"]: r for r in tv}
    very_sat, very_dis = tv_by_group["Very satisfied"], tv_by_group["Very dissatisfied"]
    leaders = {r["degree"]: r for r in industry}
    absent = sensitivity[("Q5", "Alternative: codes 1-2", "Lower bound")]
    scale_rows = []
    for shape in scale:
        if "failed_at" not in shape:
            outcome = f"{shape['database_gb']} GB database"
        elif "Out of Memory" in shape["error"]:
            outcome = "<b>Out of memory</b> building marts.answers"
        else:
            outcome = f"<b>Failed</b> in {shape['failed_at']}"
        scale_rows.append([f"{shape['rows']:,} x {shape['columns']:,}", f"{shape['answer_rows'] / 1e6:.1f} M", f"{shape['json_mb']:,} MB",
                           f"{shape.get('load_s', '-')} s", f"{shape.get('dbt_s', '-')} s", outcome])
    worked = [shape for shape in scale if "failed_at" not in shape]
    failed = [shape for shape in scale if "failed_at" in shape]
    largest, breaking = worked[-1], failed[0]

    s = [
        Paragraph("GSS survey pipeline report", TITLE),
        Paragraph("Religiosity and media use in the General Social Survey, 2014 to 2018: how the data was built, what it shows and how far to trust it.", SUBTITLE),
        callout(f"<b>In short.</b> Two overlapping NORC extracts load into DuckDB and dbt turns them into one table of "
                f"<b>{count(overlap['distinct_n'])} distinct interviews</b>, each counted once. One command rebuilds everything; "
                f"it publishes only if every check passes, and otherwise the last good run stays in place. "
                f"The clearest finding: the share who <b>never</b> read a newspaper rose from {one(first['wtssps_never_news_pct'])}% "
                f"to {one(third['wtssps_never_news_pct'])}% in four years. TV viewing barely moved and shows no link to job satisfaction. "
                f"Estimates in this report use the WTSSPS survey weight unless marked otherwise, with raw counts alongside."),

        h1("1. The extracts and why these years"),
        table(["", "Survey years", "Interviews", "Shared with the other cut"],
              [["<b>Cut A</b>", "2014, 2016", count(overlap["a"]), f"{count(overlap['shared'])} ({overlap['pct_a']}%)"],
               ["<b>Cut B</b>", "2016, 2018", count(overlap["b"]), f"{count(overlap['shared'])} ({overlap['pct_b']}%)"],
               ["<b>Union</b>", "2014, 2016, 2018", count(overlap["distinct_n"]), "Limit is 10,000 distinct"]],
              [0.14, 0.26, 0.2, 0.4]),
        gap(),
        p("Each cut is near 5,000 records and holds a year the other lacks. Sharing a whole wave is the natural overlap, and it tests whether two "
          "independent exports agree: all shared interviews match field for field. I preferred 2014 to 2018 because every concept is observed under the "
          "same definitions. An earlier 2012 to 2016 option gave fewer web-duration answers, and 2021 changed survey mode and wording. The cost is recency, "
          "so these results describe those years and not today."),

        h1("2. Which variable answers each question"),
        table(["Question", "Variable", "Why, and how non-answers are handled"], [
            ["Working status", "WRKSTAT", f"Code 3 (job, temporarily absent) counts as working. Moving those {count(summary['temporarily_absent_n'])} people changes Q3 to Q5 samples; see CSV 14."],
            ["If working, over 12 months in lifetime?", "EVWORK", "<b>Cannot be answered.</b> The item skips workers and job seekers, and it asks about at least one year, not over 12 months. Reported for nonworkers with bounds."],
            ["Education level", "DEGREE, EDUC", "DEGREE is the credential and is used for grouping. EDUC gives years of schooling."],
            ["Industry", "INDUS10", "Nonworkers can report an earlier job, so current industry needs the working filter."],
            ["Satisfaction with work", "SATJOB", "2016 ballot A, form Y used other wording and is marked not asked. Job seekers and homemakers also answer it, so Q4 filters to workers."],
            ["Life after death", "POSTLIFE", "Asked on every ballot. Don't know and no answer are counted separately."],
            ["Prayer", "PRAY", "Ordered frequency; 99% valid."],
            ["Religion raised in", "RELIG16", "Upbringing, kept apart from current RELIG."],
            ["Newspaper", "NEWS", "Ballots A and B only, about two thirds of each wave. Ballot C is marked not asked."],
            ["TV", "TVHOURS", "Same ballots. It measures hours per day, not how often someone watches."],
            ["Interest in technology", "INTTECH", "Ballot and form vary by year; about half of each wave. It measures interest, not use."],
        ], [0.25, 0.14, 0.61]),
        gap(3),
        Paragraph("All variables cover all three waves. Also carried: RELIG, ATTEND, RELITEN, WWWHR, WWWMIN, AGE, SEX, REGION, BALLOT, FORM, MODE, WTSSPS and WTSSNRPS.", NOTE),

        h1("3. Data profile"),
        p("Written before any pipeline code, in <font face='Courier'>docs/profile.md</font>, with missing shares for every variable and year in "
          "<font face='Courier'>docs/profile.csv</font>. What it means for honest answers: the media items can only describe ballots A and B, and "
          "the routed items only describe the people they were routed to. No selected concept is missing a whole wave, so there is no wave to fill in. "
          f"Valid answers as a share of all interviews in 2014, 2016 and 2018: NEWS {shares('news')}; TVHOURS {shares('tvhours')}; WWWHR {shares('wwwhr')}; INTTECH {shares('inttech')}."),
        table(["In the export", "Stored status", "Meaning"], [
            [".d", "dont_know", "Asked, and the respondent did not know."],
            [".n", "no_answer", "Asked, and no answer was recorded."],
            [".i", "inapplicable", "Skipped by routing, such as a worker on EVWORK."],
            [".i outside a reviewed ballot or form", "not_asked_ballot", "This ballot never had the question. The original code stays in source_status."],
            [".y", "not_asked_year", "Not asked that year. Zero cases in these waves for POSTLIFE."],
            ["Field missing from a file", "absent_field", "The extract did not include it, which is different from any survey code."],
        ], [0.32, 0.2, 0.48]),

        h1("4. Database and data model"),
        p("<b>DuckDB</b> gives analytical SQL and dbt support in one local file, with no server or cost for a reviewer. The model has one key: "
          "<b>(survey year, respondent ID)</b>. ID alone would merge "
          f"{count(overlap['interviews_lost_using_id_alone'])} separate interviews because IDs repeat each wave."),
        table(["Schema", "Object", "One row per", "Stored as", "Why, and what changes at full scale"], [
            ["raw", "records, files", "file + row", "Table", "Exactly what was received, written only by the loader. At scale: columnar files partitioned by wave."],
            ["staging", "stg_membership", "file + row", "View", "Cheap to compute and rarely read. Stays a view."],
            ["marts", "answers", "interview + variable", "Table", "Decodes every item once. At scale: incremental by wave, with only the needed variables."],
            ["marts", "respondents", "interview", "Table", "What analysts query. Saves re-pivoting on every read. At scale: stays a table, with fewer projected columns."],
            ["metadata", "seeds", "code, variable or rule", "Seed", "Versioned meaning of each code, and where it is valid. Models read it rather than repeat it."],
        ], [0.1, 0.16, 0.16, 0.08, 0.5]),
        gap(),
        p("Status lives on <font face='Courier'>marts.answers</font>, so no missing type can pass for an answer; a null in the wide table means no genuine answer, and "
          "<font face='Courier'>answers.status</font> says why. To add a variable, an analyst adds rows to two seeds and changes no model. "
          "Naming is lower snake case with <font face='Courier'>_value</font> for numbers, <font face='Courier'>_status</font> for availability and "
          "<font face='Courier'>wtssps_</font> for weighted results; the full convention is in <font face='Courier'>docs/naming.md</font>."),

        h1("5. Libraries, and what I did not use"),
        table(["Used", "For", "Not used", "Why not"], [
            ["DuckDB", "Storage and SQL", "Postgres, SQLite", "A server to run, or weak analytics. Neither helps at this size."],
            ["dbt Core", "Models, tests, docs", "dbt packages", "A few singular tests were clearer than another dependency."],
            ["Python standard library", "Loading and checks", "pandas", "Validation is row by row, and SQL handles the aggregation."],
            ["SciPy", "Q4 rank tests", "Airflow, Dagster", "A scheduler for a manual two-file batch adds more to run than it saves. A short script covers order and failure."],
            ["Hash-locked virtual env", "Reproducible install", "Docker", "The brief allows a pinned local setup. Docker is a second install path to maintain, while the lock file already pins every wheel by hash. I would add it for a shared server."],
            ["ReportLab", "This report", "Terraform", "Nothing is deployed. <font face='Courier'>docs/production.md</font> sketches AWS instead."],
        ], [0.2, 0.17, 0.15, 0.48]),

        h1("6. Results, and how far to trust them"),
        h2("Q1. Prayer by religion raised in"),
        p(f"Praying several times a day: raised Protestant {pray_daily('Protestant')}, Catholic {pray_daily('Catholic')}, raised with no religion {pray_daily('None')}, "
          f"Muslim {pray_daily('Muslim/Islam')}. <b>Trust:</b> good for the large groups. {', '.join(small_groups)} each have under 50 people and are flagged in CSV 01; read them as indications only."),
        h2("Q2. Belief in life after death"),
        p(f"Yes among valid answers: {one(afterlife[0]['wtssps_yes_pct'])}% in 2014, {one(afterlife[1]['wtssps_yes_pct'])}% in 2016, {one(afterlife[2]['wtssps_yes_pct'])}% in 2018. "
          f"Not asked: {sum(int(r['not_asked_year_n']) + int(r['not_asked_ballot_n']) for r in afterlife)} respondents in any wave. "
          f"Don't know: {count(afterlife[0]['dont_know_n'])}, {count(afterlife[1]['dont_know_n'])} and {count(afterlife[2]['dont_know_n'])}, which are excluded and not treated as no. <b>Trust:</b> high, and the wave differences are small."),
        h2("Q3. Most common industry among current workers, by degree"),
        table(["Degree", "Leading industry", "Share", "n", "Runner-up", "Share"],
              [[r["degree"], r["industry"], f"{one(r['wtssps_pct'])}%", f"{count(r['n'])} of {count(r['group_n'])}", r["runner_up_industry"], f"{one(r['runner_up_wtssps_pct'])}%"] for r in industry],
              [0.19, 0.25, 0.08, 0.13, 0.27, 0.08]),
        gap(3),
        p("<b>Trust:</b> medium. No industry holds a majority, so each leader is only the largest of many. The high school and less-than-high-school leads over restaurants are narrow and could reverse in another sample."),
        h2("Q4. TV hours and job satisfaction"),
        table(["Current workers", "n", "Effective n", "TV hours/day, weighted", "Unweighted"],
              [[r["satisfaction"], count(r["group_n"]), count(r["effective_n"]), f"{float(r['wtssps_mean_tv_hours']):.2f}", f"{float(r['mean_tv_hours']):.2f}"] for r in tv],
              [0.36, 0.12, 0.14, 0.22, 0.16]),
        gap(3),
        p(f"<b>No relationship.</b> Weighted means differ by under 0.1 hour, and the direction is not stable: the unweighted figures rise from {very_sat['mean_tv_hours']} to {very_dis['mean_tv_hours']} as satisfaction falls, "
          f"while the weighted ones fall from {very_sat['wtssps_mean_tv_hours']} to {very_dis['wtssps_mean_tv_hours']}. Median TV is 2 hours in every group. Unweighted rank tests agree (Spearman rho {float(tv_tests['rho']):.3f}, p={float(tv_tests['spearman_p']):.2f}; "
          f"Kruskal-Wallis p={float(tv_tests['kw_p']):.2f}). <b>Trust:</b> good for no large link. It cannot rule out a small one, and the very dissatisfied group is small."),
        h2("Q5. Nonworkers who ever worked for a year"),
        p(f"{one(work['wtssps_yes_pct_of_valid'])}% of the {count(work['valid_n'])} who answered ({one(work['yes_pct_of_valid'])}% unweighted). The {count(work['job_seekers_routed_out_n'])} job seekers were never asked, and {work['eligible_missing_n']} answers are missing. "
          f"Across all {count(work['nonworking_n'])} nonworkers the possible range is {one(work['wtssps_lower_bound_pct'])}% to {one(work['wtssps_upper_bound_pct'])}%. "
          f"<b>Trust:</b> good for those asked. The whole group is only known as a range, and job seekers probably push it toward the top."),
        h2("Q6. Newspaper reading and TV from wave to wave"),
        table(["Wave", "Never reads", "Change", "z", "Reads daily", "Change", "z", "TV hours", "Change", "z"],
              [[r["survey_year"], f"{one(r['wtssps_never_news_pct'])}%", r["wtssps_never_change_pp"] or "-", r["wtssps_never_z"] or "-",
                f"{one(r['wtssps_daily_news_pct'])}%", r["wtssps_news_change_pp"] or "-", r["wtssps_news_z"] or "-",
                r["wtssps_mean_tv_hours"], r["wtssps_tv_change_hours"] or "-", r["wtssps_tv_z"] or "-"] for r in waves],
              [0.09, 0.13, 0.09, 0.08, 0.13, 0.09, 0.08, 0.12, 0.1, 0.09]),
        gap(3),
        p(f"<b>Newspaper reading fell, TV did not clearly change.</b> Never-readers grew by about 7 points per wave, 3 to 4 standard errors each time, which is the one change I would state with confidence. "
          f"Daily reading fell about 2.8 points in each step, with neither step beyond 2 standard errors on its own. Unweighted, the first drop looked significant (z {float(second['news_z']):.2f}) and the second did not (z {float(third['news_z']):.2f}); that pattern came from not using the weight. "
          f"<b>Trust:</b> medium. These are repeated cross sections and not the same people, and the errors allow for weights but not for strata or clusters. Two steps cannot establish a long-run trend."),
        h2("Overlap audit: is anyone counted twice?"),
        p(f"Cut A holds {count(overlap['a'])}, cut B {count(overlap['b'])}, both {count(overlap['shared'])} ({overlap['pct_a']}% of A, {overlap['pct_b']}% of B), and {count(overlap['distinct_n'])} are distinct overall. "
          f"The analysis table has {count(overlap['analysis_rows'])} rows and {overlap['duplicate_analysis_rows']} duplicates. Every result above reads that table."),

        h1("7. Efficiency"),
        p(f"<b>Query plan.</b> The slowest query, <font face='Courier'>{costs['slowest_query'].removesuffix('.sql')}</font>, took {costs['before_ms']:.0f} ms when <font face='Courier'>respondents</font> was a view and {costs['after_ms']:.0f} ms as a table, "
          f"because it no longer re-pivots {count(MANIFEST['row_counts']['answers'])} answer rows. The table costs {costs['materialization']['respondents']['build_ms']:.0f} ms to build and repays that in {costs['break_even_reads']} reads per rebuild. Appendix A has the plan. "
          f"<b>A new extract:</b> everything rebuilds, which takes about 15 seconds here and avoids any partial state. A changed hash or a new year must be reviewed first. "
          f"<b>Deliberately not built:</b> incremental models, partitioning, a scheduler, containers, cloud resources, and row-level quarantine. None pays for itself at this size."),

        h1("8. Running it, and what happens when it fails"),
        p("<b>Order:</b> <font face='Courier'>source/run.py</font> validates and loads, runs dbt build (seeds, models, tests), generates docs, runs the analyses, then publishes. <b>Trigger:</b> a person runs it after reviewing a new extract, and a CI workflow is configured to run it on each push. "
          "<b>Failure:</b> any failed step stops the rest, including a failed test, which blocks docs and results. Each run builds a new database, and only a final pointer swap publishes it, so a rerun is always safe. "
          "<b>Evidence:</b> <font face='Courier'>build/run.log</font> names each stage and any failed test, <font face='Courier'>dbt/logs/dbt.log</font> has detail, and each run's manifest records hashes of inputs, definitions and outputs. "
          "<b>Configuration:</b> no credentials exist; the only setting is the optional <font face='Courier'>GSS_BUILD</font>. <b>Tested on</b> Windows 11 with Python 3.12."),
        p(f"<b>Bad input</b> stops the whole run and names the problem, because silently missing respondents are worse than no result. "
          f"Appendix B lists {len(failures)} corruptions I ran with <font face='Courier'>source/failure_check.py</font>. Loading twice or in either order gives identical data, and a unit test confirms it on the real cuts."),

        h1("9. Risk as data and sources grow"),
        table(["Rows x columns", "Answer rows", "JSON size", "Load", "dbt build", "Result"], scale_rows, [0.2, 0.13, 0.13, 0.12, 0.13, 0.29]),
        gap(3),
        Paragraph("One Windows machine (16 logical cores, 32 GB), synthetic rows copied from real records: <font face='Courier'>source/scale_check.py</font>.", NOTE),
        p(f"<b>What breaks first:</b> the dbt build of <font face='Courier'>marts.answers</font>. It handled {largest['columns']} variables and ran out of memory at {breaking['columns']}, which is only {100 * breaking['columns'] / 7000:.0f}% of the variables in the full file. It unpacks JSON for every row, removes overlap duplicates and crosses every interview with every variable. "
          f"The loader failed first until I limited its overlap scan to shared interviews; it now reads {breaking['columns']} variables in {breaking['load_s']:.0f} seconds. "
          f"<b>What grows fastest:</b> that same table, respondents times variables, which is about 530 million rows for the full file. "
          f"<b>What I would change, in order:</b> load only the variables needed (about {largest['columns']} work today), hold typed columns in staging instead of JSON, build by wave, and store only non-skipped answers. "
          f"With more sources, the manual review of each code and routing rule becomes the real bottleneck: it grows with people's time, not with compute."),

        h1("10. Limitations and what remains unsolved"),
        table(["Limitation", "What I did", "Still open"], [
            ["EVWORK skips workers and job seekers", "Reported with bounds", "Lifetime work history of current workers is unknowable from GSS"],
            ["No strata or cluster fields in the extracts", "Weighted estimates with Kish effective n", "True design-based errors need VSTRAT and VPSU"],
            ["Misaligned columns upstream", "Overlap comparison covers 2016 only", "A shift inside a single-cut wave is not detectable (Appendix B)"],
        ], [0.38, 0.27, 0.35]),

        h1("11. What I missed first, and how I fixed it"),
        p("An independent review of my first submission found these. All are now fixed and covered by tests or evidence."),
        table(["What was wrong", "Why it mattered", "Fix"], [
            ["Required answers were unweighted, although I had named a primary weight", f"The Q6 and Q4 conclusions were partly artifacts, and the never-reader rise went unreported", "Weighted columns on Q1 to Q6, with Q4 and Q6 rewritten"],
            ["A truncated or empty wave could publish", "Half of 2018 could vanish with every check green", "Per-wave row counts and coverage floors as dbt tests"],
            ["Routing gaps", "Impossible answers could pass", "SATJOB, web-time and unknown-ballot rules"],
            ["Overlap scan unpacked every row", "The loader ran out of memory at 300 columns", "Scan only interviews held by more than one file"],
            ["Renaming a cut made the audit report 0", "A silent wrong answer", "Cuts named in a seed; a rename now fails a test"],
            ["A checkout under a folder named logs lost its provenance", "The manifest silently recorded nothing", "Filter on repository-relative paths"],
            ["dbt was flat, with queries outside it", "No layers, lineage or seed documentation", "Staging and marts, analyses using ref(), seeds documented"],
        ], [0.38, 0.32, 0.3]),

        h1("12. Trade-offs I chose"),
        table(["Choice", "What it gains", "What it costs"], [
            ["Full rebuild on each run", "No partial state, and a simple recovery story", "Wasteful at scale; would become incremental by wave"],
            ["Stop on any bad input", "Nothing wrong is published", "One bad row blocks everything; no quarantine"],
            ["Long answers table plus a wide table", "Add variables with no model change, and easy analyst queries", "A dense table that grows quickly"],
            ["Manual review of each new extract", "A person checks every change in meaning", "Slow, and it will not scale to many sources"],
        ], [0.34, 0.36, 0.3]),

        h1("13. Future considerations"),
        p("<b>First, with more time:</b> add VSTRAT and VPSU for true survey errors, and row-level quarantine for agreed cases. "
          "<b>As data grows:</b> partition by wave, store sparse answers and build incrementally. "
          "<b>In production:</b> the AWS design in <font face='Courier'>docs/production.md</font>. "
          "<b>More sources:</b> Pew's Religious Landscape Study as an external check at survey level, and never joined at person level; aggregate Yaqeen format data only with permission and no religious identifiers. "),

        h1("14. Assumptions and divergence from the design note"),
        p("<b>Assumptions:</b> equal-length columns align by position in the export; code meanings hold across these waves; ID is unique within a wave; NORC's released counts are correct. "
          "<b>Divergence:</b> the design planned to insert new files into one database. The final build rebuilds a fresh candidate on each run and publishes atomically, because recovery became trivial. "
          "Metadata also grew beyond the codebook once profiling showed routing mattered more than expected. Details are in <font face='Courier'>docs/design.md</font>."),

        h1("15. AI use and human oversight"),
        p("<b>Tools:</b> Codex wrote the original code and SQL, ran checks and helped write the report; an AI reviewer challenged the scope. Claude Code later reviewed the finished submission, ran it against corrupted data, and implemented the section 11 fixes and this redesigned report. "
          "<b>Extent:</b> most code and much of the prose was AI-written. <b>My part:</b> I chose the extracts and years, supplied both cuts, challenged the TV and employment interpretations, and decided which review findings to act on. "
          "<b>Time:</b> roughly six hours on the original submission, with the review and fixes after that."),
        PageBreak(),

        h1("Appendix A. Query plan for the most expensive query"),
        p(f"Query: <font face='Courier'>{costs['slowest_query']}</font>. One thread, the median of three warm runs. The full plans are in <font face='Courier'>report/query-plans.txt</font>."),
        table(["", "Before: respondents as a view", "After: respondents as a table"], [
            ["<b>Plan</b>", f"Scan {count(MANIFEST['row_counts']['answers'])} rows of answers, hash-group them into one row per interview, hash-join work status, then run the query", f"Scan {count(MANIFEST['row_counts']['respondents'])} rows of respondents, then run the query"],
            ["<b>Read time</b>", f"{costs['before_ms']:.1f} ms", f"{costs['after_ms']:.1f} ms"],
            ["<b>Extra cost</b>", "None", f"{costs['materialization']['respondents']['build_ms']:.0f} ms build, {costs['materialization']['respondents']['incremental_storage_bytes'] / 1024:.0f} KiB storage"],
            ["<b>Result rows</b>", str(costs["equal_result_rows"]), f"{costs['equal_result_rows']} (checked equal)"],
        ], [0.16, 0.5, 0.34]),
        gap(),
        Paragraph("Timings vary by machine. At full scale the view would re-pivot hundreds of millions of rows on every read, so the difference would grow with the data.", NOTE),

        h1("Appendix B. What happens to bad input"),
        p(f"Each row corrupts a fresh copy of the project and runs the real pipeline. The previous published run survived every failure. Reproduce with <font face='Courier'>python source/failure_check.py</font>."),
        table(["What goes wrong", "Stopped by"],
              [[r["problem"], "<font color='#A5522A'><b>Not detected</b></font> (known limit, section 10)" if r["stopped_by"] == "not detected" else r["stopped_by"]] for r in failures],
              [0.62, 0.38]),

        h1("Appendix C. Sensitivity of Q5 to temporarily absent workers"),
        p(f"Counting the {count(summary['temporarily_absent_n'])} people with a job who were temporarily absent as not working widens the unweighted Q5 range to start at {absent['value']}%. The Q3 leaders do not change. See <font face='Courier'>report/results/14_work_status_sensitivity.csv</font>."),

        h1("Source"),
        Paragraph("Davern, Michael; Bautista, Rene; Freese, Jeremy; Herd, Pamela; and Morgan, Stephen L.; General Social Surveys, 1972-2024 [machine-readable data file]. Principal Investigator, Smith, Tom W.; "
                  "Co-Principal Investigators, Rene Bautista, Jeremy Freese, Pamela Herd, and Stephen L. Morgan; Sponsored by National Science Foundation. NORC ed. Chicago: NORC, 2025: NORC at the University of Chicago [producer and distributor]. "
                  "Data accessed from the GSS Data Explorer at gssdataexplorer.norc.org.", NOTE),
    ]
    flowing = []
    for flowable in s:
        if isinstance(flowable, Paragraph) and flowable.style.name == "h1":
            flowing.append(CondPageBreak(70))
        flowing.append(flowable)
    return flowing


def main():
    out = ROOT / "report/survey-assessment.pdf"
    temp = out.with_suffix(".tmp")
    doc = Report(temp)
    doc.build(story())
    body_pages = doc.appendix_page - 1
    if body_pages > MAX_BODY_PAGES:
        temp.unlink()
        raise ValueError(f"The report body is {body_pages} pages; the limit is {MAX_BODY_PAGES}")
    temp.replace(out)
    print(f"Wrote {out.name}: {body_pages} body pages, {doc.page} in total")


if __name__ == "__main__":
    main()
