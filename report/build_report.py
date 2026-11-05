"""Render the report from a successful pipeline run. Optional dependency: see README.

Every survey result comes from the published CSVs, and every measurement from the evidence files beside this script.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from snapshot import current_run
from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, HRFlowable, KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
RUN, MANIFEST = current_run()
MAX_BODY_PAGES = 5

INK, TEAL, MUTED, PALE, RULE, AMBER = (colors.HexColor(c) for c in ("#152F37", "#00675F", "#566B6E", "#E8F2EF", "#D5E0DD", "#A5522A"))
BANNER, BANNER_TEXT, AMBER_PALE = (colors.HexColor(c) for c in ("#0F3A44", "#BFD9D4", "#F8ECE3"))
SERIES_NEVER, SERIES_DAILY, HEAT_PEAK = (colors.HexColor(c) for c in ("#008A7E", "#C4622D", "#6FBBAE"))
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=12.2, textColor=INK, spaceAfter=4, alignment=TA_LEFT)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.5, leading=10.8, spaceAfter=0)
SMALL_RIGHT = ParagraphStyle("small_right", parent=SMALL, alignment=TA_RIGHT)
HEAD = ParagraphStyle("head", parent=SMALL, fontName="Helvetica-Bold", fontSize=8.2)
HEAD_RIGHT = ParagraphStyle("head_right", parent=HEAD, alignment=TA_RIGHT)
FIGURE = ParagraphStyle("figure", parent=BODY, fontName="Helvetica-Bold", fontSize=16, leading=18, spaceAfter=1)
FIGURE_LABEL = ParagraphStyle("figure_label", parent=SMALL, fontSize=7.9, leading=9.6, textColor=MUTED)
NOTE = ParagraphStyle("note", parent=BODY, fontSize=8.5, leading=11.2, textColor=MUTED)
SUBTITLE = ParagraphStyle("subtitle", parent=BODY, fontSize=9.6, leading=12.4, textColor=BANNER_TEXT, spaceAfter=0)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=12, leading=14.5, textColor=TEAL, spaceBefore=6, spaceAfter=1)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=9.8, leading=13, spaceBefore=3, spaceAfter=1, keepWithNext=1)
WIDTH = letter[0] - 1.4 * inch
BANNER_HEIGHT = 74


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


def table(header, body, widths, right=(), fills=()):
    """A ruled table whose text wraps. Widths are shares of the page, right names numeric columns, fills are (column, row, color)."""
    right = set(right)
    data = [[Paragraph(cell, HEAD_RIGHT if column in right else HEAD) for column, cell in enumerate(header)]]
    data += [[Paragraph(str(cell), SMALL_RIGHT if column in right else SMALL) for column, cell in enumerate(row)] for row in body]
    result = Table(data, colWidths=[share * WIDTH for share in widths], repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), PALE), ("VALIGN", (0, 0), (-1, 0), "BOTTOM"), ("VALIGN", (0, 1), (-1, -1), "TOP"),
             ("LINEBELOW", (0, 0), (-1, 0), 0.9, TEAL), ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE), ("TOPPADDING", (0, 0), (-1, -1), 1.8),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    for column, row, color in fills:
        style += [("BACKGROUND", (column, row + 1), (column, row + 1), color), ("BOX", (column, row + 1), (column, row + 1), 1, colors.white)]
    result.setStyle(TableStyle(style))
    return result


def shade(value, peak):
    """One-hue sequential tint, so a darker cell means a larger share."""
    amount = min(float(value) / peak, 1)
    return colors.Color(*(1 + (channel - 1) * amount for channel in HEAT_PEAK.rgb()))


class Chip(Flowable):
    """A small rounded label. Its words carry the meaning, so color is never the only signal."""

    def __init__(self, text, tone):
        super().__init__()
        self.text, self.tone = text, tone
        self.width, self.height = stringWidth(text, "Helvetica-Bold", 7.4) + 12, 12

    def wrap(self, available_width, available_height):
        return self.width, self.height

    def draw(self):
        fill, ink = (AMBER_PALE, AMBER) if self.tone == "caution" else (PALE, TEAL)
        self.canv.setFillColor(fill)
        self.canv.roundRect(0, 0, self.width, self.height, 3, stroke=0, fill=1)
        self.canv.setFillColor(ink)
        self.canv.setFont("Helvetica-Bold", 7.4)
        self.canv.drawCentredString(self.width / 2, 3.4, self.text)


def question(title, trust, tone="good"):
    """A question heading with its trust level at the right."""
    row = Table([[Paragraph(title, H2), Chip(f"Trust: {trust}", tone)]], colWidths=[WIDTH - 130, 130])
    row.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    row.keepWithNext = True
    return row


def headline_figures(items):
    """A row of large numbers, each with a short label."""
    row = Table([[[Paragraph(number, FIGURE), Paragraph(label, FIGURE_LABEL)] for number, label in items]], colWidths=[WIDTH / len(items)] * len(items))
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBEFORE", (1, 0), (-1, 0), 0.5, RULE), ("LEFTPADDING", (0, 0), (0, 0), 0),
                             ("LEFTPADDING", (1, 0), (-1, 0), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 0),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return row


def beside(left, right, left_share=0.63):
    """Text with a figure to its right."""
    row = Table([[left, right]], colWidths=[left_share * WIDTH, (1 - left_share) * WIDTH])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, 0), 0), ("LEFTPADDING", (1, 0), (1, 0), 12),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return row


def newspaper_chart(waves, width):
    """Weighted newspaper shares by wave: two series on one zero-based axis, labelled at both ends and with a legend."""
    height, left, right, top, bottom, peak = 92, 24, width - 34, 62, 14, 50
    x = {r["survey_year"]: left + (right - left) * index / (len(waves) - 1) for index, r in enumerate(waves)}
    y = lambda share: bottom + (top - bottom) * float(share) / peak
    chart = Drawing(width, height)
    chart.add(String(0, height - 8, "Share of valid newspaper answers, weighted", fontName="Helvetica-Bold", fontSize=7.6, fillColor=INK))
    for tick in (0, 25, 50):
        chart.add(Line(left, y(tick), right, y(tick), strokeColor=RULE, strokeWidth=0.4))
        chart.add(String(left - 5, y(tick) - 2.4, f"{tick}%", fontName="Helvetica", fontSize=6.8, fillColor=MUTED, textAnchor="end"))
    for r in waves:
        chart.add(String(x[r["survey_year"]], 3, r["survey_year"], fontName="Helvetica", fontSize=6.8, fillColor=MUTED, textAnchor="middle"))
    legend_x = 0
    for column, name, color, label_offset in (("wtssps_never_news_pct", "Never reads", SERIES_NEVER, 4.5), ("wtssps_daily_news_pct", "Reads daily", SERIES_DAILY, -9)):
        points = [(x[r["survey_year"]], y(r[column])) for r in waves]
        chart.add(PolyLine([value for point in points for value in point], strokeColor=color, strokeWidth=1.5))
        for px, py in points:
            chart.add(Circle(px, py, 2.4, fillColor=color, strokeColor=colors.white, strokeWidth=0.8))
        chart.add(String(points[-1][0] + 5, points[-1][1] - 2.4, f"{one(waves[-1][column])}%", fontName="Helvetica-Bold", fontSize=7.2, fillColor=INK))
        chart.add(String(points[0][0] - 2, points[0][1] + label_offset, f"{one(waves[0][column])}%", fontName="Helvetica", fontSize=7, fillColor=MUTED))
        chart.add(Circle(legend_x + 3, height - 17.5, 2.4, fillColor=color, strokeColor=color, strokeWidth=0))
        chart.add(String(legend_x + 8, height - 20, name, fontName="Helvetica", fontSize=7, fillColor=INK))
        legend_x += 56
    return chart


def callout(text):
    box = Table([[Paragraph(text, ParagraphStyle("callout", parent=BODY, spaceAfter=0))]], colWidths=[WIDTH])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("LINEBEFORE", (0, 0), (0, -1), 3, TEAL),
                             ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                             ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    return box


def gap(points=5):
    return Spacer(1, points)


class Report(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch, topMargin=0.6 * inch,
                         bottomMargin=0.64 * inch, invariant=1, title="GSS survey pipeline report",
                         author="Candidate submission", subject="Yaqeen data engineering assignment")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        first_height = letter[1] - BANNER_HEIGHT - 12 - self.bottomMargin
        first = Frame(self.leftMargin, self.bottomMargin, self.width, first_height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="first", frames=first, onPage=self.first_page), PageTemplate(id="page", frames=frame, onPage=self.furniture)])
        self.appendix_page = None

    def first_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BANNER)
        canvas.rect(0, letter[1] - BANNER_HEIGHT, letter[0], BANNER_HEIGHT, stroke=0, fill=1)
        canvas.setFillColor(TEAL)
        canvas.rect(0, letter[1] - BANNER_HEIGHT - 3, letter[0], 3, stroke=0, fill=1)
        canvas.setFillColor(BANNER_TEXT)
        canvas.setFont("Helvetica-Bold", 7.4)
        canvas.drawString(self.leftMargin, letter[1] - 19, "DATA ENGINEERING TECHNICAL ASSIGNMENT")
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 20)
        canvas.drawString(self.leftMargin, letter[1] - 42, "GSS survey pipeline report")
        subtitle = Paragraph("Religiosity and media use, 2014 to 2018: how the data was built, what it shows and how far to trust it.", SUBTITLE)
        _, used = subtitle.wrap(self.width, 40)
        subtitle.drawOn(canvas, self.leftMargin, letter[1] - 49 - used)
        canvas.restoreState()
        self.furniture(canvas, doc)

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
    weight_checks = rows("10_weight_sensitivity")
    if any(r["same_leader"].lower() == "false" for r in weight_checks):
        raise ValueError("A Q3 leader changes under WTSSNRPS; the weight paragraph says none does")
    largest_weight_shift = max(abs(float(r["difference_pp"])) for r in weight_checks)
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
    standard, alternative = "Standard: codes 1-3", "Alternative: codes 1-2"
    if any(sensitivity[("Q3", standard, degree)]["detail"] != sensitivity[("Q3", alternative, degree)]["detail"] for degree in leaders):
        raise ValueError("A Q3 leader changes without temporarily absent workers; Appendix C says none does")
    def bound(definition, name):
        return one(sensitivity[("Q5", definition, name)]["wtssps_estimate"])
    wave_interviews = {year: sum(int(r["interviews"]) for r in ballots if r["survey_year"] == year and r["variable"] == "news") for year in ("2014", "2016", "2018")}
    table_groups = sorted({r["upbringing"]: int(r["group_n"]) for r in rows("01_prayer") if int(r["group_n"]) >= 50}.items(), key=lambda item: -item[1])
    frequencies = [r["frequency"] for r in rows("01_prayer") if r["upbringing"] == "Protestant"]
    narrow_leads = [r for r in industry if float(r["wtssps_lead_z"]) < 2]
    clear_leads = [r for r in industry if float(r["wtssps_lead_z"]) >= 2]
    tv_means = [float(r["wtssps_mean_tv_hours"]) for r in tv]
    tv_cohort = sum(int(r["group_n"]) for r in tv)
    if work["no_with_industry_n"] != "0":
        raise ValueError("The Q5 text says no one who answered no has a recorded industry; review it")
    scale_rows = []
    for shape in scale:
        if "failed_at" not in shape:
            outcome = f"{shape['database_gb']} GB database"
        elif "Out of Memory" in shape["error"] or "not enough space" in shape["error"]:
            outcome = "<b>Out of memory and temporary disk</b> building marts.answers"
        else:
            outcome = f"<b>Failed</b> in {shape['failed_at']}"
        scale_rows.append([f"{shape['rows']:,} x {shape['columns']:,}", f"{shape['answer_rows'] / 1e6:.1f} M", f"{shape['json_mb']:,} MB",
                           f"{shape.get('load_s', '-')} s", f"{shape.get('dbt_s', '-')} s", outcome])
    worked = [shape for shape in scale if "failed_at" not in shape]
    failed = [shape for shape in scale if "failed_at" in shape]
    largest, breaking = worked[-1], failed[0]

    s = [
        NextPageTemplate("page"),
        headline_figures([
            (count(overlap["distinct_n"]), "distinct interviews, each counted once"),
            (count(overlap["shared_n"]), "held by both cuts, matching field for field"),
            (f"{one(third['wtssps_never_news_pct'])}%", f"never read a newspaper in 2018, up from {one(first['wtssps_never_news_pct'])}% in 2014"),
            (third["wtssps_mean_tv_hours"], f"TV hours a day in 2018, against {first['wtssps_mean_tv_hours']} in 2014: no clear change"),
        ]),
        gap(6),
        callout(f"<b>In short.</b> Two overlapping NORC extracts load into DuckDB, and dbt turns them into one table of interviews. One command rebuilds everything; "
                f"it publishes only if every check passes, and otherwise the last good run stays in place. "
                f"The clearest finding is the rise in never-readers of newspapers. TV viewing shows no clear link to job satisfaction. "
                f"Estimates use the WTSSPS survey weight unless marked otherwise, with raw counts alongside."),

        h1("1. The extracts and why these years"),
        table(["", "Survey years", "Interviews", "Shared with the other cut"],
              [["<b>Cut A</b>", "2014, 2016", count(overlap["cut_a_n"]), f"{count(overlap['shared_n'])} ({overlap['shared_of_cut_a_pct']}%)"],
               ["<b>Cut B</b>", "2016, 2018", count(overlap["cut_b_n"]), f"{count(overlap['shared_n'])} ({overlap['shared_of_cut_b_pct']}%)"],
               ["<b>Union</b>", "2014, 2016, 2018", count(overlap["distinct_n"]), "Limit is 10,000 distinct"]],
              [0.14, 0.26, 0.14, 0.46], right=(2,)),
        gap(),
        p("Each cut is near 5,000 records and holds a year the other lacks. Sharing a whole wave is the natural overlap, and it tests whether two "
          "independent exports agree: all shared interviews match field for field. I chose 2014 to 2018 because every concept is observed under the "
          "same definitions; 2012 gave fewer web-duration answers, and 2021 changed survey mode and wording. The cost is recency: these results describe those years, not today."),

        h1("2. Which variable answers each question"),
        table(["Question", "Variable", "Why, and how non-answers are handled"], [
            ["Working status", "WRKSTAT", f"Code 3 (job, temporarily absent) counts as working; Appendix C tests moving those {count(summary['temporarily_absent_n'])} people."],
            ["If working, over 12 months in lifetime?", "EVWORK", "<b>Cannot be answered for workers.</b> The item skips workers and job seekers, and asks about at least one year. Reported for nonworkers with bounds."],
            ["Education level", "DEGREE, EDUC", "DEGREE is the credential and is used for grouping. EDUC gives years of schooling."],
            ["Industry", "INDUS10", "Nonworkers can report an earlier job, so current industry needs the working filter."],
            ["Satisfaction with work", "SATJOB", "2016 ballot A, form Y is marked not asked. Job seekers and homemakers also answer it, so Q4 filters to workers."],
            ["Life after death", "POSTLIFE", "Asked on every ballot. Don't know and no answer are counted separately."],
            ["Prayer", "PRAY", "Ordered frequency; 99% valid."],
            ["Religion raised in", "RELIG16", "Upbringing, kept apart from current RELIG."],
            ["Newspaper", "NEWS", "Ballots A and B only, about two thirds of each wave. Ballot C is marked not asked."],
            ["TV", "TVHOURS", "Same ballots. It measures hours per day, not how often someone watches."],
            ["Interest in technology", "INTTECH", "Ballot and form vary by year; about half of each wave. It measures interest, not use."],
        ], [0.25, 0.14, 0.61]),
        gap(3),
        Paragraph("Also carried: RELIG, ATTEND, RELITEN, WWWHR, WWWMIN, AGE, SEX, REGION, BALLOT, FORM, MODE and both weights.", NOTE),

        h1("3. Data profile"),
        p(f"Written before any pipeline code, in <font face='Courier' size='8.5'>docs/profile.md</font>, with missing shares for every variable and year in "
          f"<font face='Courier' size='8.5'>docs/profile.csv</font>. Interviews per wave: {count(wave_interviews['2014'])} in 2014, {count(wave_interviews['2016'])} in 2016 and {count(wave_interviews['2018'])} in 2018. "
          "The media items only cover ballots A and B, which GSS assigns at random, and the routed items only describe the people they were routed to. No selected concept is missing a whole wave. "
          f"Valid answers as a share of all interviews in 2014, 2016 and 2018: NEWS {shares('news')}; TVHOURS {shares('tvhours')}; WWWHR {shares('wwwhr')}; INTTECH {shares('inttech')}."),
        KeepTogether([table(["In the export", "Stored status", "Meaning"], [
            [".d", "dont_know", "Asked, and the respondent did not know."],
            [".n", "no_answer", "Asked, and no answer was recorded."],
            [".i", "inapplicable", "Skipped by routing, such as a worker on EVWORK."],
            [".i outside a reviewed ballot or form", "not_asked_ballot", "This ballot never had the question. The original code stays in source_status."],
            [".y, or a field missing from a file", "not_asked_year, absent_field", "Not asked that year, or left out of the extract. Neither is a survey answer."],
        ], [0.32, 0.2, 0.48])]),

        h1("4. Database and data model"),
        p("<b>DuckDB</b> gives analytical SQL and dbt support in one local file, with no server or cost for a reviewer. The model has one key: "
          "<b>(survey year, respondent ID)</b>. ID alone would merge "
          f"{count(overlap['interviews_lost_using_id_alone'])} separate interviews because IDs repeat each wave."),
        table(["Schema", "Object", "One row per", "Stored", "Why, and what changes at full scale"], [
            ["raw", "records, files", "file + row", "Table", "Exactly what was received. At scale: columnar files by wave."],
            ["staging", "stg_membership, stg_answers", "file + row; interview + field", "View", "Which file holds each interview, and the JSON unpacked. Read once per build, so they stay views."],
            ["marts", "answers", "interview + variable", "Table", "Decodes every item once. At scale: incremental by wave, with only the needed variables."],
            ["marts", "respondents", "interview", "Table", "What analysts query. Saves re-pivoting on every read. At scale: stays a table, with fewer columns."],
            ["metadata", "seeds", "code, variable or rule", "Seed", "Versioned meaning of each code, and where it is valid."],
        ], [0.09, 0.16, 0.19, 0.07, 0.49]),
        gap(),
        p("Status lives on <font face='Courier' size='8.5'>marts.answers</font>, so no missing type can pass for an answer; a null in the wide table means no genuine answer, and "
          "<font face='Courier' size='8.5'>answers.status</font> says why. To add a variable, an analyst re-exports, reviews the new hash in the manifest and adds rows to two seeds; no model changes. "
          "The naming convention is in <font face='Courier' size='8.5'>docs/naming.md</font>."),
        p(f"<b>Weight.</b> WTSSPS is primary, because NORC's FAQ names it for most analyses and it keeps continuity. NORC's report MR135 recommends WTSSNRPS for cross sections, so CSV 10 runs the headline estimates under both: "
          f"none moves by more than {largest_weight_shift:.1f} points and no Q3 leader changes."),

        h1("5. Libraries, and what I did not use"),
        table(["Used", "For", "Not used", "Why not"], [
            ["DuckDB", "Storage and SQL", "Postgres, SQLite", "A server to run, or weak analytics. Neither helps at this size."],
            ["dbt Core", "Models, tests, docs", "dbt packages", "A few singular tests were clearer than another dependency."],
            ["Python standard library, SciPy", "Loading and checks; Q4 rank tests", "pandas, Airflow, Dagster", "SQL handles the aggregation, and a scheduler for a manual two-file batch adds more than it saves."],
            ["Hash-locked virtual env", "Reproducible install", "Docker", "A second install path to maintain; the lock file already pins every wheel by hash. I would add it for a shared server."],
            ["ReportLab", "This report", "Terraform", "Nothing is deployed; <font face='Courier' size='8.5'>docs/production.md</font> sketches AWS."],
        ], [0.2, 0.17, 0.15, 0.48]),

        h1("6. Results, and how far to trust them"),
        p("Q2 and Q6 are reported by wave. Q1, Q3, Q4 and Q5 ask about people rather than change, so they pool the three waves. WTSSPS sums to the interviews in each wave, so each wave counts by its sample size."),
        question("Q1. Prayer by religion raised in (weighted share of each group)", "good, large groups"),
        table(["Raised in", "n"] + frequencies,
              [[group, count(group_n)] + [f"{one(prayer[(group, frequency)]['wtssps_pct'])}%" if (group, frequency) in prayer else "-" for frequency in frequencies] for group, group_n in table_groups],
              [0.15, 0.07, 0.13, 0.13, 0.14, 0.13, 0.13, 0.12], right=range(1, 8),
              fills=[(column + 2, row, shade(prayer[(group, frequency)]["wtssps_pct"], 40))
                     for row, (group, _) in enumerate(table_groups) for column, frequency in enumerate(frequencies) if (group, frequency) in prayer]),
        gap(3),
        p(f"Among those raised with no religion, {one(prayer[('None', 'Never')]['wtssps_pct'])}% never pray. Raised Muslim, {pray_daily('Muslim/Islam')} pray several times a day. "
          f"<b>Caveat:</b> {', '.join(small_groups)} each have under 50 people and are flagged in CSV 01; read them as indications only."),
        question("Q2. Belief in life after death", "high"),
        p(f"Yes among valid answers: {one(afterlife[0]['wtssps_yes_pct'])}% in 2014, {one(afterlife[1]['wtssps_yes_pct'])}% in 2016, {one(afterlife[2]['wtssps_yes_pct'])}% in 2018. "
          f"Not asked: {sum(int(r['not_asked_year_n']) + int(r['not_asked_ballot_n']) for r in afterlife)} respondents in any wave. "
          f"Don't know: {count(afterlife[0]['dont_know_n'])}, {count(afterlife[1]['dont_know_n'])} and {count(afterlife[2]['dont_know_n'])}, excluded and not treated as no. The wave differences are small."),
        question("Q3. Most common industry among current workers, by degree", "medium", "caution"),
        table(["Degree", "Leading industry", "Share", "n", "Runner-up", "Share", "z"],
              [[r["degree"], r["industry"], f"{one(r['wtssps_pct'])}%", f"{count(r['n'])} of {count(r['group_n'])}", r["runner_up_industry"], f"{one(r['runner_up_wtssps_pct'])}%", f"{float(r['wtssps_lead_z']):.2f}"] for r in industry],
              [0.18, 0.22, 0.065, 0.11, 0.285, 0.075, 0.065], right=(2, 3, 5, 6)),
        gap(3),
        p(f"<b>Caveat:</b> no industry holds a majority, so each leader is only the largest of many fine-grained labels. Column z is the lead over the runner-up in standard errors: only {' and '.join(r['degree'] for r in clear_leads)} clears 2, and the other {len(narrow_leads)} could reverse in another sample."),
        question("Q4. TV hours and job satisfaction", "good, no large link"),
        table(["Current workers", "n", "Effective n", "TV hours/day, weighted", "Unweighted"],
              [[r["satisfaction"], count(r["group_n"]), count(r["effective_n"]), f"{float(r['wtssps_mean_tv_hours']):.2f}", f"{float(r['mean_tv_hours']):.2f}"] for r in tv],
              [0.36, 0.12, 0.14, 0.22, 0.16], right=(1, 2, 3, 4)),
        gap(3),
        p(f"<b>No visible relationship.</b> Weighted means differ by at most {max(tv_means) - min(tv_means):.2f} hours among the {count(tv_cohort)} of {count(summary['workers_n'])} workers with both answers, and the direction is not stable: the unweighted figures rise from {very_sat['mean_tv_hours']} to {very_dis['mean_tv_hours']} as satisfaction falls, "
          f"while the weighted ones fall from {very_sat['wtssps_mean_tv_hours']} to {very_dis['wtssps_mean_tv_hours']}. Median TV is 2 hours in every group. Unweighted rank tests agree (Spearman rho {float(tv_tests['rho']):.3f}, p={float(tv_tests['spearman_p']):.2f}; "
          f"Kruskal-Wallis p={float(tv_tests['kw_p']):.2f}). <b>Caveat:</b> this cannot rule out a small link, the very dissatisfied group is small, and it shows association only."),
        question("Q5. Nonworkers who ever worked for a year", "good, for those asked"),
        p(f"{one(work['wtssps_yes_pct_of_valid'])}% of the {count(work['valid_n'])} who answered ({one(work['yes_pct_of_valid'])}% unweighted). The {count(work['job_seekers_routed_out_n'])} job seekers were never asked, and {work['eligible_missing_n']} answers are missing. "
          f"Across all {count(work['nonworking_n'])} nonworkers the possible range is {one(work['wtssps_lower_bound_pct'])}% to {one(work['wtssps_upper_bound_pct'])}%. "
          f"<b>Mitigation:</b> none of the {int(work['valid_n']) - int(work['yes_n'])} who said no has an industry on record, while {count(work['yes_with_industry_n'])} of the {count(work['yes_n'])} who said yes and {work['job_seekers_with_industry_n']} of the {work['job_seekers_routed_out_n']} job seekers do. "
          f"Counting those job seekers as having worked narrows the range to {one(work['wtssps_lower_bound_with_industry_pct'])}% to {one(work['wtssps_upper_bound_pct'])}%. "
          f"<b>Caveat:</b> the narrowed range assumes a recorded industry means at least a year of work, which the data cannot prove; only the wider range is free of that assumption."),
        question("Q6. Newspaper reading and TV from wave to wave", "medium", "caution"),
        table(["Wave", "Never reads", "Change", "z", "Reads daily", "Change", "z", "TV hours", "Change", "z"],
              [[r["survey_year"], f"{one(r['wtssps_never_news_pct'])}%", r["wtssps_never_change_pp"] or "-", r["wtssps_never_z"] or "-",
                f"{one(r['wtssps_daily_news_pct'])}%", r["wtssps_news_change_pp"] or "-", r["wtssps_news_z"] or "-",
                r["wtssps_mean_tv_hours"], r["wtssps_tv_change_hours"] or "-", r["wtssps_tv_z"] or "-"] for r in waves],
              [0.09, 0.13, 0.09, 0.08, 0.13, 0.09, 0.08, 0.12, 0.1, 0.09], right=range(1, 10)),
        gap(3),
        beside(p(f"<b>Newspaper reading fell, TV did not clearly change.</b> Never-readers grew by {second['wtssps_never_change_pp']} and {third['wtssps_never_change_pp']} points, 3 to 4 standard errors each time. "
          f"Daily reading fell {abs(float(second['wtssps_news_change_pp'])):.2f} and {abs(float(third['wtssps_news_change_pp'])):.2f} points. Neither step clears 2 standard errors alone, but the four-year drop of {abs(float(third['wtssps_news_since_first_pp'])):.1f} points does (z {third['wtssps_news_since_first_z']}). "
          f"<b>Caveat:</b> these are repeated cross sections and not the same people, and the errors allow for weights but not for strata or clusters. Two steps cannot establish a long-run trend."), newspaper_chart(waves, 0.37 * WIDTH - 12)),
        h2("Overlap audit: is anyone counted twice?"),
        p(f"Cut A holds {count(overlap['cut_a_n'])}, cut B {count(overlap['cut_b_n'])}, both {count(overlap['shared_n'])} ({overlap['shared_of_cut_a_pct']}% of A, {overlap['shared_of_cut_b_pct']}% of B), and {count(overlap['distinct_n'])} are distinct overall. "
          f"The analysis table has {count(overlap['analysis_rows'])} rows and {overlap['duplicate_analysis_rows']} duplicates. Every result above reads that table."),

        h1("7. Efficiency"),
        p(f"<b>Query plan.</b> The slowest query, <font face='Courier' size='8.5'>{costs['slowest_query'].removesuffix('.sql')}</font>, took {costs['before_ms']:.0f} ms when <font face='Courier' size='8.5'>respondents</font> was a view and {costs['after_ms']:.0f} ms as a table, "
          f"because it no longer re-pivots {count(MANIFEST['row_counts']['answers'])} answer rows. The table costs {costs['materialization']['respondents']['build_ms']:.0f} ms to build and repays that in {costs['break_even_reads']} reads per rebuild. Appendix A has the plan. "
          f"<b>A new extract:</b> everything rebuilds, in about 15 seconds here, with no partial state. A changed hash or new year must be reviewed first. "
          f"<b>Deliberately not built:</b> incremental models, partitioning, a scheduler, containers and cloud resources. None pays for itself at this size."),

        h1("8. Running it, and what happens when it fails"),
        p("<b>Order:</b> <font face='Courier' size='8.5'>source/run.py</font> validates and loads, runs dbt build (seeds, models, tests), generates docs, runs the analyses, then publishes. <b>Trigger:</b> a person after reviewing a new extract, and CI on each push. "
          "<b>Failure:</b> any failed step stops the rest, including a failed test, which blocks docs and results. Only a final pointer swap publishes a run, so a rerun is always safe. "
          "<b>Evidence:</b> <font face='Courier' size='8.5'>build/run.log</font> names each stage and any failed test, and each run's manifest records hashes of inputs, definitions and outputs. "
          "<b>Configuration:</b> no credentials exist; the only setting is the optional <font face='Courier' size='8.5'>GSS_BUILD</font>. <b>Tested on</b> Windows 11 with Python 3.12."),
        p(f"<b>Bad input</b> stops the whole run and names the problem. "
          f"Appendix B lists {len(failures)} corruptions run with <font face='Courier' size='8.5'>source/failure_check.py</font>. Loading twice or in either order gives identical data."),

        h1("9. Risk as data and sources grow"),
        table(["Rows x columns", "Answer rows", "JSON size", "Load", "dbt build", "Result"], scale_rows, [0.17, 0.12, 0.12, 0.1, 0.12, 0.37], right=(1, 2, 3, 4)),
        gap(3),
        Paragraph("One Windows machine (16 logical cores, 32 GB), synthetic rows copied from real records: <font face='Courier' size='8.5'>source/scale_check.py</font>.", NOTE),
        p(f"<b>What breaks first:</b> the dbt build of <font face='Courier' size='8.5'>marts.answers</font>. It handled {largest['columns']} variables and failed at {breaking['columns']}, when memory filled and its temporary spill then used up the disk, which is only {100 * breaking['columns'] / 7000:.0f}% of the variables in the full file. It crosses every interview with every variable. "
          f"<b>What grows fastest:</b> that same table, respondents times variables, which is about 530 million rows for the full file. "
          f"<b>What I would change, in order:</b> load only the variables needed (about {largest['columns']} work today), hold typed columns in staging instead of JSON, build by wave, and store only non-skipped answers. "
          f"With more sources, manual review of each code and routing rule becomes the real bottleneck."),

        h1("10. Limitations and what remains unsolved"),
        table(["Limitation", "What I did", "Still open"], [
            ["EVWORK skips workers and job seekers", "Bounds, narrowed using recorded industry", "Work history of current workers is unknowable from these extracts"],
            ["No strata or cluster fields: I did not select VSTRAT or VPSU", "Weighted estimates with Kish effective n", "True design-based errors need a new export (section 13)"],
            ["Misaligned columns upstream", "Overlap comparison covers 2016 only", "A shift inside a single-cut wave is not detectable (Appendix B)"],
        ], [0.38, 0.27, 0.35]),

        h1("11. Trade-offs I chose"),
        table(["Choice", "What it gains", "What it costs"], [
            ["Full rebuild on each run", "No partial state, and a simple recovery story", "Wasteful at scale"],
            ["Stop on any bad input", "Nothing that fails a check is published", "One bad row blocks the whole run"],
            ["Built and checked for these two extracts and three waves", "Exact checks and a simple design that fit the assignment", "A different input needs review and new expected counts first"],
            ["Long answers table plus a wide table", "Add variables with no model change, and easy analyst queries", "A dense table that grows quickly"],
        ], [0.34, 0.36, 0.3]),

        CondPageBreak(230),
        h1("12. What I missed first, and how I fixed it"),
        p("AI reviews of my earlier versions (section 15) found these. Each fix is covered by a test or the evidence files."),
        table(["What was wrong", "Why it mattered", "Fix"], [
            ["Required answers were unweighted, although I had named a primary weight", "The Q6 and Q4 conclusions were partly artifacts", "Weighted columns on Q1 to Q6, with Q4 and Q6 rewritten"],
            ["A truncated or empty wave could publish", "Half of 2018 could vanish with every check green", "Per-wave row counts and coverage floors as dbt tests"],
            ["Routing gaps", "Impossible answers could pass", "SATJOB, web-time and unknown-ballot rules"],
            ["Renaming a cut made the audit report 0", "A silent wrong answer", "Cuts named in a seed; a rename now fails a test"],
            ["Nothing checked the weights behind the headlines", "One bad weight could swing a published figure", "Each wave's WTSSPS must sum to its interviews"],
            ["The Q5 range ignored evidence in the data", "A ten-point range that could be narrowed", "A labelled narrowing beside the strict bounds"],
            ["dbt was flat, with queries outside it", "No layers, lineage or seed documentation", "Staging unpacks, marts decode; analyses use ref(); seeds documented"],
        ], [0.38, 0.32, 0.3]),

        h1("13. Future considerations"),
        p("These go beyond the two chosen extracts, so I did not build them. Section 9 covers scale. For the rest:"),
        table(["Not built", "How I would do it"], [
            ["True survey errors", "Re-export with VSTRAT and VPSU, review the new manifest, replace Kish z with design-based errors, and weight the Q4 rank tests."],
            ["Subtler bad values", "Reviewed per-wave bands for category shares, a weight cap, and row-level quarantine for agreed cases. Today's checks miss a wave of weights all set to 1, or a loss under about 20%."],
            ["Deeper tests", "A truth table for the <font face='Courier' size='8.5'>work_status</font> seed, and fixtures for the remaining queries and standard errors."],
            ["Other machines", "Linux and macOS commands in the README, and a hash lock for the report renderer."],
            ["Production and sources", "The AWS design in <font face='Courier' size='8.5'>docs/production.md</font>. Pew's Religious Landscape Study as a survey-level check, never joined at person level; Yaqeen format data only in aggregate, with permission and no religious identifiers."],
        ], [0.2, 0.8]),

        h1("14. Assumptions and divergence from the design note"),
        p("<b>Assumptions:</b> equal-length columns align by position in the export; code meanings hold across these waves; ID is unique within a wave; NORC's released counts are correct. "
          "<b>Divergence:</b> the design planned to insert new files into one database; the build instead rebuilds a fresh candidate and publishes atomically, which makes recovery trivial. "
          "See <font face='Courier' size='8.5'>docs/design.md</font>."),

        h1("15. AI use and human oversight"),
        p("<b>Tools:</b> Codex wrote the original code and SQL and helped write the report; an AI reviewer challenged the scope. Claude Code later reviewed the submission, ran it against corrupted data, recomputed the required answers from the raw JSON with separate code (all matched), and implemented the section 12 fixes and this report. "
          "<b>Extent:</b> most code and much of the prose was AI-written, so \"I\" here often means work I directed and did not type. <b>My part:</b> I chose the extracts and years, supplied both cuts, challenged the TV and employment interpretations, and decided which review findings to act on. "
          "For example, I limited the final review to the brief's inputs and moved most findings that depended on other inputs to section 13. "
          "<b>Time:</b> roughly six hours in total."),
        PageBreak(),

        h1("Appendix A. Query plan for the most expensive query"),
        p(f"Query: <font face='Courier' size='8.5'>{costs['slowest_query']}</font>. One thread, the median of three warm runs. The full plans are in <font face='Courier' size='8.5'>report/query-plans.txt</font>."),
        table(["", "Before: respondents as a view", "After: respondents as a table"], [
            ["<b>Plan</b>", f"Scan {count(MANIFEST['row_counts']['answers'])} rows of answers, hash-group them into one row per interview, hash-join work status, then run the query", f"Scan {count(MANIFEST['row_counts']['respondents'])} rows of respondents, then run the query"],
            ["<b>Read time</b>", f"{costs['before_ms']:.1f} ms", f"{costs['after_ms']:.1f} ms"],
            ["<b>Extra cost</b>", "None", f"{costs['materialization']['respondents']['build_ms']:.0f} ms build, {costs['materialization']['respondents']['incremental_storage_bytes'] / 1024:.0f} KiB storage"],
            ["<b>Result rows</b>", str(costs["equal_result_rows"]), f"{costs['equal_result_rows']} (checked equal)"],
        ], [0.16, 0.5, 0.34]),
        gap(),
        Paragraph("Timings vary by machine. At full scale the view would re-pivot hundreds of millions of rows on every read, so the difference would grow with the data.", NOTE),

        h1("Appendix B. What happens to bad input"),
        p(f"Each row corrupts a fresh copy of the project and runs the real pipeline. The previous published run survived every failure. Reproduce with <font face='Courier' size='8.5'>python source/failure_check.py</font>."),
        table(["What goes wrong", "Stopped by"],
              [[r["problem"], "<font color='#A5522A'><b>Not detected</b></font> (known limit, section 10)" if r["stopped_by"] == "not detected" else r["stopped_by"]] for r in failures],
              [0.62, 0.38]),

        h1("Appendix C. Sensitivity of Q5 to temporarily absent workers"),
        p(f"Counting the {count(summary['temporarily_absent_n'])} people with a job who were temporarily absent as not working moves the weighted Q5 range from {bound(standard, 'Lower bound')}%-{bound(standard, 'Upper bound')}% to {bound(alternative, 'Lower bound')}%-{bound(alternative, 'Upper bound')}%. The Q3 leaders do not change. See <font face='Courier' size='8.5'>report/results/14_work_status_sensitivity.csv</font>, which also has the unweighted figures."),

        h1("Source"),
        Paragraph("Davern, Michael; Bautista, Rene; Freese, Jeremy; Herd, Pamela; and Morgan, Stephen L.; General Social Surveys, 1972-2024 [machine-readable data file]. Principal Investigator, Smith, Tom W.; "
                  "Co-Principal Investigators, Rene Bautista, Jeremy Freese, Pamela Herd, and Stephen L. Morgan; Sponsored by National Science Foundation. NORC ed. Chicago: NORC, 2025: NORC at the University of Chicago [producer and distributor]. "
                  "Data accessed from the GSS Data Explorer at gssdataexplorer.norc.org.", NOTE),
    ]
    flowing = []
    for flowable in s:
        if isinstance(flowable, Paragraph) and flowable.style.name == "h1":
            flowing.append(CondPageBreak(70))
            flowing += [flowable, HRFlowable(width="100%", thickness=0.5, color=RULE, spaceBefore=0, spaceAfter=3)]
            continue
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
