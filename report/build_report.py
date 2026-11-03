"""Render the assessment from a successful pipeline run. Optional dependencies: see README."""
import csv
import os
import json
from io import BytesIO
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from snapshot import current_run
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject as N, NumberObject, RectangleObject, TextStringObject
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
RUN, MANIFEST = current_run()
RESULTS = RUN / "results"

def rows(name):
    with (RESULTS / (name + ".csv")).open(encoding="utf8", newline="") as f:
        return list(csv.DictReader(f))

def num(x):
    return f"{int(x):,}"

buf = BytesIO()
c = Canvas(buf, pagesize=(612,792), invariant=1, pdfVersion=(1,5))
c.setTitle("Counting the right interviews | GSS research brief")
c.setAuthor("Yaqeen data engineering assessment | Candidate submission")
ink, teal, muted, pale, cream, amber, light = "#152F37","#00675F","#4D6265","#E1EFEB","#FBFAF5","#AA582F","#D4DEDA"
tabs = ["Sample","Coverage","Findings","Engineering","Research"]
def rect(x,y,w,h,color):
    c.setFillColor(HexColor(color)); c.rect(x,792-y-h,w,h,fill=1,stroke=0)

def txt(x,y,s,size=10,font="Helvetica",color=ink):
    c.setFillColor(HexColor(color)); c.setFont(font,size); c.drawString(x,792-y,str(s))

def para(x,y,s,w=526,size=10.3,leading=14,color=ink):
    for line in simpleSplit(s,"Helvetica",size,w):
        txt(x,y,line,size,color=color); y+=leading
    return y

def section(y,s):
    txt(42,y,s,16,"Times-Bold",ink)

def page(i,title,subtitle):
    c.bookmarkPage(tabs[i]); c.addOutlineEntry(tabs[i],tabs[i],0)
    rect(0,0,612,792,cream); rect(0,0,612,6,teal)
    txt(42,32,"RESEARCH ENGINEERING     /     YAQEEN ASSESSMENT",9,"Helvetica-Bold",teal)
    txt(509,32,f"GSS   /   0{i+1}",9,"Helvetica-Bold",teal)
    for j,label in enumerate(tabs):
        x=42+j*106; rect(x,47,101,25,teal if j==i else pale)
        txt(x+9,63,label,9,"Helvetica-Bold", "#FFFFFF" if j==i else teal)
        c.linkRect(label,label,(x,720,x+101,745),relative=0,thickness=0)
    txt(42,118,title,31,"Times-Bold")
    para(42,144,subtitle,526,11.3,15,muted)
    rect(42,752,528,1,light); txt(42,770,"NORC GENERAL SOCIAL SURVEY    /    2014, 2016, 2018",8,"Helvetica-Bold",muted)
    txt(534,770,f"{i+1}  /  5",9,"Helvetica-Bold",muted)

def bar(x,y,w,v,maximum,col=teal,height=8):
    rect(x,y,w,height,pale); rect(x,y,w*v/maximum,height,col)

def decision(y,label,body):
    rect(42,y,528,55,pale); txt(53,y+16,label,8.6,"Helvetica-Bold",teal)
    para(53,y+32,body,505,9.6,12)

o=rows("07_overlap")[0]; waves=rows("02_afterlife"); change=rows("06_wave_changes")
summary=rows("12_report_summary")[0]
absent_n=num(summary["temporarily_absent_n"])
first_change=next((row for row in change if row["news_z"]),None)
news_error_note=(f"The first news change is {abs(float(first_change['news_z'])):.2f} approximate standard errors from zero."
                 if first_change else "No wave-to-wave news comparison is available.")

page(0,"Counting the right interviews","Two overlapping extracts, three survey waves and one decision that governs every result: who was actually in a position to answer?")
txt(42,242,num(o["distinct_n"]),57,"Times-Bold",teal)
txt(246,218,"distinct survey interviews",18,"Times-Bold")
para(246,239,"One row per survey year and respondent ID. These are repeated cross sections, not a panel following the same people.",316,10.5)
section(299,"Where the two extracts meet")
txt(42,320,"INTERVIEWS BY SURVEY WAVE",8,"Helvetica-Bold",muted)
for idx,w in enumerate(waves):
    x=155+idx*134
    txt(x,345,w["survey_year"],12,"Helvetica-Bold")
    txt(x,365,num(w["interviews"]),13,"Helvetica",muted)
for idx,(label,waves_in) in enumerate([("Cut A",(0,1)),("Cut B",(1,2))]):
    y=379+idx*28; txt(42,y+14,label,10,"Helvetica-Bold")
    for j in waves_in:
        rect(155+j*134,y,119,18,teal if idx==0 else amber)
        txt(163+j*134,y+13,"IN EXTRACT",8,"Helvetica-Bold","#FFFFFF")
para(42,458,f"A has {num(o['a'])} rows; B has {num(o['b'])}. All {num(o['shared'])} shared interviews agree field for field ({o['pct_a']}% of A; {o['pct_b']}% of B). ID alone would collapse {num(o['interviews_lost_using_id_alone'])} separate interviews. Membership remains available for audit.")
section(527,"Why these years?")
para(42,552,"I chose 2014/2016 and 2016/2018. Both cuts are near 5,000 interviews, every requested concept is observed, and 2016 tests whether overlapping answers agree. The earlier 2012-2016 option yielded fewer web-duration observations; including 2021 introduced mode and wording changes.")
decision(619,"TRADEOFF   /   COMPARABILITY OVER RECENCY","These years support the same field definitions across adjacent waves. They do not describe today's audience. Use newer compatible data or a direct audience study for a current decision.")
txt(42,712,"READING PATH",8.5,"Helvetica-Bold",teal)
para(133,712,"Use the tabs above. On Research, switch the survey weight to inspect the estimate.",420,9.5)
c.showPage()

page(1,"Who could answer?","The share missing varies by question. Start with the intended population, then apply only the filters that question needs.")
coverage=rows("09_ballot_coverage")
section(205,"Valid responses by wave")
txt(42,225,"Bars show share of all interviews; each track is 0-100%.",9,"Helvetica",muted)
for j,w in enumerate(waves):
    txt(198+122*j,248,w["survey_year"],9,"Helvetica-Bold")
for i,(key,title) in enumerate([("news","Newspaper"),("tvhours","TV hours"),("wwwhr","Weekly web hours"),("inttech","Technology interest")]):
    y=270+26*i;txt(42,y,title,10)
    for j,w in enumerate(waves):
        part=[r for r in coverage if r["survey_year"]==w["survey_year"] and r["variable"]==key]
        pct=100*sum(int(r["valid_n"]) for r in part)/sum(int(r["interviews"]) for r in part)
        x=198+122*j; bar(x,y-7,66,pct,100);txt(x+70,y,f"{pct:.0f}%",9)
para(42,382,"Ballot C had no valid news, TV, computer-use or web-hours answers in any wave. INTTECH had valid answers on B/X, B/Y and C/Y in 2014, then A/X, A/Y and B/X in 2016 and 2018. Letters before the slash identify the ballot and letters after it identify the form. Technology estimates describe only valid answers; the accompanying CSV provides counts and coverage.",526,10,13)
section(460,"Question map   /   fields and eligibility")
mapping=[
("Work and history","WRKSTAT includes temporary absence as working. EVWORK asks about at least one year. Current workers and job seekers skipped it, so their lifetime duration is unknown. Q5 bounds the missing answers."),
("Education and industry","DEGREE measures credentials; EDUC measures years. Use INDUS10 for current workers so a prior industry's label is not mistaken for a current job."),
("Satisfaction and media",f"In 2016, Ballot A/Form Y used alternate work-satisfaction wording. Q4 keeps only standard SATJOB. Code 3 keeps temporarily absent workers employed. Reclassifying its {absent_n} cases changes Q3-Q5 samples (CSV 14). TVHOURS measures daily duration."),
("Faith and technology","RELIG16 is upbringing, RELIG current preference, ATTEND attendance, RELITEN strength. PRAY is ordered frequency; POSTLIFE is belief. INTTECH is interest, not usage."),
("Web duration","WWWHR + WWWMIN / 60 measures weekly non-email web time. Require both fields. A skip is unknown. Age, sex, region, ballot, form and mode retain context.")]
for i,(label,body) in enumerate(mapping):
    y=484+45*i;txt(42,y,label,9.7,"Helvetica-Bold",teal);para(175,y,body,393,9.4,12)
para(42,721,"Pre-build profile: docs/profile.csv records per-variable, per-year missing shares. All mapped concepts have observations in all three waves.",525,9,12,muted)
c.showPage()

page(2,"What the six analyses show","Each result counts the shared wave once. Percentages on this page describe observed respondents and are unweighted.")
pr=rows("01_prayer"); ind=rows("03_industry"); sat=rows("04_tv_satisfaction"); rank=rows("04_tv_rank_tests")[0]; hist=rows("05_ever_work")[0]
section(197,"01  Prayer and upbringing")
def freq(group):
    r=next(r for r in pr if r["upbringing"]==group and r["frequency"]=="Several times a day")
    return f"{num(r['n'])}/{num(r['group_n'])}"
mus=next(r["upbringing"] for r in pr if "mus" in r["upbringing"].lower() or "islam" in r["upbringing"].lower())
para(42,217,f"Several-times-daily prayer: {freq('Protestant')} raised Protestant, {freq('Catholic')} raised Catholic and {freq(mus)} raised Muslim. The last group is small. CSV 01 includes the full distribution.")
section(270,"02  Belief in life after death")
para(42,290,"Yes among valid answers: "+", ".join(f"{r['survey_year']}: {r['yes_pct']}% ({num(r['yes_n'])}/{num(r['valid_n'])})" for r in waves)+". Counts coded not asked that year were "+", ".join(r["not_asked_year_n"] for r in waves)+", respectively. Uncertain and unanswered items are excluded.")
section(342,"03  Leading industry by degree")
para(42,362,"Among current workers with both answers: "+ "; ".join(f"{r['degree'].lower()}: {r['industry'].lower()} ({r['n']}/{num(r['group_n'])})" for r in ind)+". Each is the most frequent industry, not necessarily a majority.",526,9.8,13)
section(421,"04  TV hours and job satisfaction")
for j,r in enumerate(sat):
    x=42+j*133; txt(x,445,r["satisfaction"],9,"Helvetica-Bold")
    txt(x,470,r["mean_tv_hours"],19,"Times-Bold",teal);txt(x,486,"hours/day; n="+num(r["group_n"]),8.5)
summary=rows("12_report_summary")[0]
satisfied=int(summary["satisfied_n"])
valid=int(summary["satisfaction_valid_n"])
working=int(summary["workers_n"])
web_check=[(r["age_band"],int(r["added_n"]),float(r["median_hours"])) for r in rows("13_web_sensitivity")]
paired_yes=sum(int(r["group_n"]) for r in sat if r["satisfaction"] in ("Very satisfied","Moderately satisfied"))
median_note="Median TV: 2 h in each group. " if int(summary["groups_with_median_not_two"])==0 and int(rank["n"])>0 else ""
para(42,507,f"Of {num(working)} workers, {num(satisfied)}/{num(valid)} who answered were satisfied ({100*satisfied/valid:.2f}%); among TV pairs: {num(paired_yes)}/{num(rank['n'])} ({100*paired_yes/int(rank['n']):.2f}%). {median_note}The observed rank association is very small. Spearman rho {float(rank['rho']):.3f}, p={float(rank['spearman_p']):.2f}; Kruskal-Wallis p={float(rank['kw_p']):.2f}. Tests ignore survey design.",526,9.7,13)
section(567,"05  Ever worked at least one year")
para(42,587,f"Of {num(hist['nonworking_n'])} nonworkers, {hist['job_seekers_routed_out_n']} job seekers were skipped and {hist['eligible_missing_n']} eligible answers missing. Yes: {num(hist['yes_n'])}/{num(hist['valid_n'])} ({hist['yes_pct_of_valid']}%). Across all nonworkers the possible range is {hist['lower_bound_pct']}-{hist['upper_bound_pct']}%.")
section(646,"06  News and TV across waves")
para(42,666,"Daily readership: "+" / ".join(f"{float(w['daily_news_pct']):.1f}%" for w in change)+". Mean TV hours: "+" / ".join(w["mean_tv_hours"] for w in change)+". "+news_error_note+" Errors omit survey design and multiplicity. Weighted, design-based results could change this assessment.")
txt(42,729,"Q7   /   See Sample for the overlap audit. Detailed counts: report/results/01-07.",9,"Helvetica-Bold",teal)
c.showPage()

page(3,"What I built, and why","One local batch, one interview key, and an explicit stopping point when a file, model or test fails.")
section(202,"From immutable file to usable answer")
for j,(a,b) in enumerate([("01  RAW","File + row"),("02  MEMBERSHIP","Year + ID"),("03  ANSWERS","Item + status"),("04  RESPONDENTS","One interview")]):
    x=42+j*134;rect(x,221,124,53,pale);txt(x+7,239,a,8,"Helvetica-Bold",teal);txt(x+7,258,b,11,"Times-Bold")
para(42,297,"Python reads the strict JSON export (the companion is a Python literal), validates aligned arrays and keys, and loads DuckDB in a transaction. dbt tables preserve membership, decode each variable once, then pivot answers. Seeds distinguish zero, routed skips, unknown answers and year/ballot unavailability. source_status retains the original codebook meaning. Lower snake case; _value is numeric, _status explains availability.")
section(379,"Three engineering decisions")
for y,tag,body in [
(396,"MATERIALIZE  /  PAY ONCE","Tables store parsed keys, decoded items and wide interviews once per build. Reusing the wide table speeds the new work-status sensitivity query. Read-time savings add build and storage cost."),
(459,"RERUN  /  VALIDATE AGAIN","Validate reviewed input hashes and counts before building each candidate. A fresh candidate and its input/output manifest must pass dbt and SQL before LATEST is replaced. The prior publication survives a failure. CI uses the same checks."),
(522,"SCALE  /  CHANGE ONLY WHEN NEEDED","DuckDB avoids a server for two periodic extracts. At full scale the dense model approaches 530 million cells. Read only needed fields and rebuild affected waves before adding managed compute.")]:
    decision(y,tag,body)
benchmark=json.loads((ROOT/"report/materialization-costs.json").read_text(encoding="utf8"))
if benchmark["inputs"] != MANIFEST["inputs"] or any(MANIFEST["definitions"].get(name) != value for name,value in (benchmark["model_hashes"] | benchmark["query_hashes"]).items()):
    raise ValueError("Benchmark belongs to different inputs or models; rerun source/benchmark.py")
before,after=benchmark["before_ms"],benchmark["after_ms"]
section(606,benchmark["slowest_query"].split("_",1)[1].removesuffix(".sql").replace("_"," ").capitalize()+"   /   runtime")
for j,(label,v) in enumerate([("Before",before),("After",after)]):
    y=627+17*j;txt(42,y,label,9);bar(103,y-7,170,v,before);txt(281,y,f"{v:.2f} ms",9,"Helvetica-Bold")
cost=benchmark["materialization"][benchmark["changed_model"]]
reads=benchmark["break_even_reads"]
cost_note=(f"Build {cost['build_ms']:.1f} ms; extra storage {cost['incremental_storage_bytes']/1024:.0f} KiB. "
           + (f"Cost recovered after {reads} reads per rebuild." if reads is not None else "No measured read-time saving.")
           + " Excludes dbt startup and upstream tables.")
para(367,625,cost_note,201,8.8,11,muted)
para(42,678,"Oversight and effort: I spent roughly six hours choosing extracts, discussing tradeoffs and reviewing the work. I supplied both cuts and challenged the TV and employment interpretations. Codex wrote the code and SQL, ran checks and helped write the report; an AI reviewer challenged the scope. For population claims I would next add survey strata and sampling units.",526,9.6,13)
c.showPage()

page(4,"Two questions for Yaqeen","The survey can motivate a research question. A decision about Yaqeen's readers still needs evidence from those readers.")
section(198,"01  Does afterlife belief differ by prayer frequency?")
txt(42,219,"Switch weight:",9,"Helvetica-Bold",muted)
controls=[(131,205,221,226),(229,205,341,226)]
for (x,y,r,b),label in zip(controls,["WTSSPS","WTSSNRPS"]):
    rect(x,y,r-x,b-y,pale); txt(x+9,y+14,label,9,"Helvetica-Bold",teal)
faith=rows("10_prayer_afterlife")
for layer,field,title in [("Primary","wtssps_yes_pct","WTSSPS  /  primary"),("Alternate","wtssnrps_yes_pct","WTSSNRPS  /  nonresponse adjustment")]:
    c.addLiteral(f"/OC /{layer} BDC")
    txt(42,250,title,10,"Helvetica-Bold")
    for j,g in enumerate(["At least daily","Less than daily"]):
        txt(42,286+j*40,g,9.7,"Helvetica-Bold")
        for k,r in enumerate([r for r in faith if r["prayer"]==g]):
            x=159+k*135
            if j==0: txt(x,268,r["survey_year"],8.4,color=muted)
            v=float(r[field]);bar(x,278+j*40,65,v,100,teal if j==0 else amber)
            txt(x+69,286+j*40,f"{v:.1f}%",9,"Helvetica-Bold")
            txt(x,299+j*40,"n="+num(r["belief_valid_n"]),8,color=muted)
    c.addLiteral("EMC")
para(42,367,"Both weights give the same direction in every wave. For each group, divide the weights of yes answers by the weights of valid yes/no answers. Daily prayer and afterlife belief are associated; neither question measures Muslim conviction or a causal effect.",526,10,14)
section(433,"02  Does media use differ by age?")
txt(42,456,"2018   /   same respondents answered both items",10,"Helvetica-Bold",muted)
media=[r for r in rows("11_media_by_age") if r["survey_year"]=="2018"]
for x,label in [(42,"AGE"),(115,"PAIRED / KNOWN AGE"),(253,"DAILY NEWS"),(400,"WEB HOURS / WEEK*")]:
    txt(x,481,label,8,"Helvetica-Bold",muted)
for j,r in enumerate(media):
    y=505+j*23;txt(42,y,r["age_band"],10,"Helvetica-Bold")
    txt(115,y,f"{r['paired_n']} / {r['known_age_n']}",10)
    v=float(r["daily_news_pct"]);bar(253,y-7,80,v,100,amber);txt(338,y,f"{v:.1f}%",9)
    h=float(r["median_web_hours_per_week"]);bar(400,y-7,98,h,16);txt(506,y,f"{h:g}",10,"Helvetica-Bold")
extra=sum(r[1] for r in web_check)
web_medians=", ".join(f"{r[2]:g}" for r in web_check)
para(42,575,f"*Median weekly non-email web hours. Axes run to 100% and 16 hours. Ballot C and missing pairs are excluded. Counting explicit nonusers with routed skips as zero adds {extra} interviews in 2018. The resulting age-group medians are {web_medians} hours. Web time alone cannot establish access or format preference.",526,9.4,12)
decision(622,"NEXT DECISION   /   TEST A FORMAT, NOT A FAITH PROFILE","Offer a paper and video on one topic to consenting readers. Compare completion and learning separately. Historical US respondents are not Yaqeen's audience; don't infer preferences or target individuals by religion.")
para(42,705,"If scale requires AWS: versioned S3, scheduled ECS jobs and Redshift; separate roles and track compute and scan cost. Compare Pew at survey level and keep pilot aggregates separate. See docs/production.md for assumptions.",525,9,12,muted)
c.showPage(); c.save()

# Native PDF layers and link actions; no JavaScript or external resources are needed.
w=PdfWriter(clone_from=PdfReader(buf)); p=w.pages[4]; groups=[]
for title in ("Primary","Alternate"):
    group=DictionaryObject({N("/Type"):N("/OCG"),N("/Name"):TextStringObject(title+" weight")})
    groups.append(w._add_object(group))
p["/Resources"][N("/Properties")]=DictionaryObject({N("/Primary"):groups[0],N("/Alternate"):groups[1]})
w.root_object[N("/OCProperties")]=DictionaryObject({N("/OCGs"):ArrayObject(groups),N("/D"):DictionaryObject({
    N("/BaseState"):N("/OFF"),N("/ON"):ArrayObject(groups[:1]),N("/OFF"):ArrayObject(groups[1:]),
    N("/Order"):ArrayObject(groups),N("/RBGroups"):ArrayObject([ArrayObject(groups)])})})
for i,(x,y,r,b) in enumerate(controls):
    action=DictionaryObject({N("/S"):N("/SetOCGState"),N("/State"):ArrayObject([N("/OFF"),groups[1-i],N("/ON"),groups[i]])})
    w.add_annotation(4,DictionaryObject({N("/Type"):N("/Annot"),N("/Subtype"):N("/Link"),
        N("/Rect"):RectangleObject((x,792-b,r,792-y)),N("/Border"):ArrayObject([NumberObject(0)]*3),N("/A"):action}))
w.pdf_header="%PDF-1.5"
out=ROOT/"report/survey-assessment.pdf"
with out.with_suffix(".tmp").open("wb") as f: w.write(f)
out.with_suffix(".tmp").replace(out)
