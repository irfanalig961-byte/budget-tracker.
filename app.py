"""Budget Tracker: UK Autumn Budget, Wednesday 28 October 2026.
Start it with:  streamlit run app.py

Live news is read from the BBC, FT and City AM feeds every 15 minutes.
Each story is labelled automatically (rise, cut, new, scrapped, no change, rumoured)
and any tax the app hasn't seen before is added to the Taxes tab on its own.
The Library tab loads the full text of every budget speech from GOV.UK.
"""
import html
import re
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Budget Tracker", page_icon="📕", layout="wide")

RED, BLUE, ORANGE, GREEN, GOLD, GREY = "#A51C1C", "#2B6CB0", "#C05621", "#2F855A", "#D69E2E", "#B0B7BF"

# ---- the red "Budget box" look from the design
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,500..800&family=Public+Sans:wght@400;500;600;700&display=swap');
.stApp { background:#F1F3F2; }
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp button { font-family:'Public Sans', system-ui, sans-serif; }
header[data-testid="stHeader"] { background:transparent; }
.block-container { padding-top:1.4rem; max-width:1150px; }
.stApp h1, .stApp h2, .stApp h3 { font-family:'Archivo','Arial Narrow',sans-serif; font-stretch:85%; color:#15191D; }
.bt-head { background:#A51C1C; color:#fff; border-radius:14px; padding:22px 26px; display:flex; flex-wrap:wrap;
           justify-content:space-between; align-items:flex-end; gap:12px 24px; margin-bottom:6px; }
.bt-brand { font-family:'Archivo','Arial Narrow',sans-serif; font-stretch:75%; font-weight:800; font-size:42px; line-height:1; }
.bt-sub { color:#F7D5D5; font-size:14px; margin-top:8px; }
.bt-count { text-align:right; }
.bt-count b { display:block; font-family:'Archivo',sans-serif; font-stretch:80%; font-weight:700; font-size:28px; line-height:1.1; }
.bt-count span { color:#F7D5D5; font-size:13px; }
.stTabs [data-baseweb="tab-list"] { gap:4px; flex-wrap:wrap; }
.stTabs [data-baseweb="tab"] { font-weight:600; padding:8px 12px; }
.stTabs [data-baseweb="tab"] p { font-size:15px; }
.stTabs [aria-selected="true"] p { color:#A51C1C; }
.stTabs [data-baseweb="tab-highlight"] { background:#A51C1C; }
.bt-card { background:#fff; border:1px solid #D7DDDA; border-radius:12px; padding:14px 16px; margin-bottom:10px; }
.bt-card a.h { display:block; font-weight:700; font-size:16px; line-height:1.35; color:#15191D !important; text-decoration:none; margin:6px 0 8px; }
.bt-card a.h:hover { text-decoration:underline; }
.bt-card p { margin:0 0 8px; color:#58616A; font-size:14px; }
.bt-meta { font-size:13px; color:#58616A; display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center; }
.bt-src { color:#fff; font-weight:700; font-size:12px; padding:2px 8px; border-radius:5px; background:#3A434C; }
.bt-src.bbc { background:#B01818; } .bt-src.ft { background:#7A4A2E; } .bt-src.cityam { background:#1F3A5F; }
.bt-chip { display:inline-block; font-size:12px; font-weight:700; padding:3px 10px; border-radius:999px; white-space:nowrap; }
.bt-chip.rise { background:#FBE3D3; color:#86300A; } .bt-chip.cut { background:#DCE5FB; color:#173B9C; }
.bt-chip.new { background:#E7E1F8; color:#3D2A86; } .bt-chip.rumour, .bt-chip.watch, .bt-chip.disputed { background:#F7ECD3; color:#694806; }
.bt-chip.hold, .bt-chip.scrapped, .bt-chip.ruled, .bt-chip.mention, .bt-chip.out { background:#E3E6E4; color:#3A434C; }
.bt-chip.kept, .bt-chip.done { background:#DCF0E8; color:#0B5A45; }
.bt-auto { font-size:12px; color:#58616A; }
.bt-panel { background:#fff; border:1px solid #D7DDDA; border-radius:12px; padding:16px 18px; }
.bt-panel h4 { font-family:'Archivo',sans-serif; font-stretch:85%; font-size:20px; margin:0 0 2px; }
.bt-row { display:flex; justify-content:space-between; gap:12px; align-items:center; padding:9px 0; border-bottom:1px solid #E3E6E4; }
.bt-row:last-child { border-bottom:0; }
.bt-row .nm { font-weight:600; } .bt-row .sub { font-size:13px; color:#58616A; }
.bt-promise { background:#fff; border:1px solid #D7DDDA; border-radius:12px; padding:14px 16px; margin-bottom:10px; }
.bt-promise .top { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; font-weight:700; font-size:16px; }
.bt-promise .what { color:#58616A; font-size:14px; margin-top:6px; }
.stButton > button { border-radius:999px; border:1px solid #A51C1C; color:#A51C1C; background:#fff; }
.stButton > button:hover { background:#A51C1C; color:#fff; }
</style>
""", unsafe_allow_html=True)


def esc(s):
    return html.escape(str(s if s is not None else ""))


def chip(change, label=None):
    return f'<span class="bt-chip {esc(change)}">{esc(label or LABEL.get(change, change))}</span>'


def src_class(source):
    s = source.lower()
    return "bbc" if s.startswith("bbc") else "ft" if s.startswith("ft") else "cityam" if "city" in s else ""
BUDGET_DAY = datetime(2026, 10, 28, 12, 30, tzinfo=timezone.utc)
UA = {"User-Agent": "Mozilla/5.0 (BudgetTracker classroom app)"}
LABEL = {"rise": "▲ Rise", "cut": "▼ Cut", "new": "✚ New", "scrapped": "✕ Scrapped", "hold": "● No change",
         "rumour": "▲ Rumoured rise", "ruled": "Ruled out", "watch": "Under review", "mention": "Mentioned"}


def style(fig, title, height=460, legend_below=False, bottom=60):
    """One look for every chart: white background, title on its own line, legend clear of the title."""
    fig.update_layout(
        template="simple_white", height=height, font=dict(family="Arial", size=14),
        title=dict(text=title, x=0, xanchor="left", y=0.98, yanchor="top", font=dict(size=18)),
        margin=dict(l=50, r=30, t=70 if legend_below else 110, b=bottom + (90 if legend_below else 0)),
        legend=(dict(orientation="h", x=0, xanchor="left", y=-0.22, yanchor="top") if legend_below
                else dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom")),
        uniformtext=dict(minsize=10, mode="hide"),
    )
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True, showgrid=True, gridcolor="#EEEEEE")
    return fig


# ================================================================ reference data
saved_notes = [
    {"date": "2026-10-07", "title": "Hargreaves Lansdown warns Healey: Don’t ‘penalise investors’ with capital gains hike",
     "tax": "Capital gains tax", "change": "rumour", "source": "City AM",
     "link": "https://www.cityam.com/hargreaves-lansdown-warns-healey-dont-penalise-investors-with-capital-gains-hike/"},
    {"date": "2026-10-13", "title": "Healey reportedly rejects calls to equalise capital gains and income tax rates",
     "tax": "Capital gains tax", "change": "rumour", "source": "FT (via Newsquawk)",
     "link": "https://www.newsquawk.com/headlines/uk-chancellor-healey-is-reportedly-rejecting-calls-to-equalise-cgt-and-income-tax-rates-ft-reports-citing-sources"},
    {"date": "2026-10-14", "title": "Healey set to pay for Budget measures without more borrowing",
     "tax": "Taxes or spending cuts", "change": "rumour", "source": "FT (via Reuters)",
     "link": "https://www.devdiscourse.com/article/international/3991997-update-1-uk-finance-minister-healey-set-to-pay-for-budget-measures-without-more-borrowing-ft-reports"},
    {"date": "2026-10-15", "title": "Entain and Rank warn Budget tax hikes threaten betting shops and jobs",
     "tax": "Gambling duties", "change": "rumour", "source": "City AM",
     "link": "https://www.cityam.com/entain-and-rank-warn-budget-tax-hikes-threaten-betting-shops-and-jobs/"},
    {"date": "2026-10-16", "title": "Lloyds and Barclays shares fall as Healey ‘poised’ to hike bank tax",
     "tax": "Bank surcharge", "change": "rumour", "source": "City AM",
     "link": "https://www.cityam.com/john-healey-poised-to-target-banks-with-budget-tax-raid/"},
]

FEEDS = {
    "BBC": ["https://feeds.bbci.co.uk/news/business/rss.xml", "https://feeds.bbci.co.uk/news/politics/rss.xml"],
    "FT": ["https://www.ft.com/rss/home/uk", "https://www.ft.com/uk-economy?format=rss"],
    "City AM": ["https://www.cityam.com/feed/"],
}

years = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
party = ["Conservative", "Conservative", "Conservative", "Shared", "Labour"]
cash = pd.DataFrame({
    "Welfare benefits":       [233.3, 246.6, 280.6, 311.8, 331.9],
    "Health and social care": [187.3, 182.1, 188.6, 204.7, 217.4],
    "Education":              [72.2, 78.0, 84.1, 90.5, 97.3],
    "Debt interest":          [70.9, 108.1, 83.2, 85.4, 96.9],
    "Defence":                [45.9, 52.8, 53.9, 60.2, 62.0],
    "Transport":              [29.6, 28.9, 30.0, 28.5, 29.0],
    "Home Office":            [14.5, 17.2, 19.4, 19.2, 19.6],
    "Science and technology": [10.2, 11.3, 12.9, 13.7, 15.0],
    "Justice":                [10.1, 10.7, 11.9, 12.7, 14.1],
}, index=years)
real = pd.DataFrame({
    "Welfare benefits":       [282.9, 279.4, 302.0, 322.5, 331.9],
    "Health and social care": [227.1, 206.4, 203.0, 211.8, 217.4],
    "Education":              [87.6, 88.4, 90.5, 93.6, 97.3],
    "Debt interest":          [86.0, 122.4, 89.6, 88.3, 96.9],
    "Defence":                [55.7, 59.8, 58.1, 62.3, 62.0],
    "Transport":              [35.9, 32.8, 32.3, 29.4, 29.0],
    "Home Office":            [17.5, 19.5, 20.9, 19.9, 19.6],
    "Science and technology": [12.4, 12.8, 13.9, 14.2, 15.0],
    "Justice":                [12.2, 12.1, 12.8, 13.1, 14.1],
}, index=years)

# name: (status now, note, history, words that identify it in a headline)
taxes = {
    "Income tax": ("hold", "Manifesto pledge: no rise in the rates working people pay.",
                   [("2022-11", "rise", "Top 45% rate starts at £125,140, down from £150,000; thresholds frozen to 2028"),
                    ("2025-11", "rise", "Threshold freeze extended to April 2031"),
                    ("2025-11", "rise", "Dividend tax up 2 points from 2026; savings and property income up 2 points from 2027")],
                   ["income tax", "tax threshold", "personal allowance", "dividend tax"]),
    "National Insurance": ("hold", "Manifesto pledge covers the employee rate.",
                           [("2023-11", "cut", "Employee rate 12% to 10% from January 2024"),
                            ("2024-03", "cut", "Employee rate 10% to 8% from April 2024"),
                            ("2024-10", "rise", "Employer rate 13.8% to 15%; starts on pay over £5,000 instead of £9,100")],
                           ["national insurance", " ni ", "employer ni", "salary sacrifice"]),
    "VAT": ("hold", "Manifesto pledge: standard rate stays 20%.",
            [("2024-10", "new", "20% VAT on private school fees from January 2025"),
             ("2026-07", "cut", "Home electricity 5% to 0%, 1 Oct 2026 to 31 Mar 2027")],
            ["vat"]),
    "Capital gains tax": ("rumour", "Matching income tax rates reportedly ruled out; a smaller rise is possible.",
                          [("2022-11", "rise", "Tax-free allowance £12,300 to £6,000, then £3,000"),
                           ("2024-10", "rise", "Main rates 10% and 20% to 18% and 24%")],
                          ["capital gains", "cgt"]),
    "Corporation tax": ("hold", "Manifesto pledge: capped at 25%.",
                        [("2021-03", "rise", "Main rate 19% to 25% from April 2023")],
                        ["corporation tax"]),
    "Bank surcharge": ("rumour", "Reports say a rise from 3% is being weighed.",
                       [("2021-10", "cut", "8% to 3% from April 2023")],
                       ["bank tax", "bank surcharge", "bank levy", "banks", "lenders"]),
    "Gambling duties": ("rumour", "Firms warn of further rises in this Budget.",
                        [("2025-11", "rise", "Remote gaming duty 21% to 40%")],
                        ["gambling", "betting", "gaming duty", "bookmaker"]),
    "Inheritance tax": ("rise", "Pension change takes effect April 2027.",
                        [("2024-10", "rise", "Unused pensions count towards estates from April 2027"),
                         ("2025-11", "hold", "£325,000 threshold frozen to April 2031")],
                        ["inheritance tax", "iht", "death tax"]),
    "Fuel duty": ("watch", "5p cut kept to 31 Dec 2026; a rise is due 1 Jan 2027 unless changed.",
                  [("2022-03", "cut", "Cut by 5p to 52.95p a litre"),
                   ("2024-10", "hold", "Freeze and 5p cut kept for another year"),
                   ("2026-05", "hold", "September rise cancelled; cut kept to end of 2026")],
                  ["fuel duty", "petrol", "diesel"]),
    "Vapes": ("new", "New duty starts 1 October 2026.",
              [("2024-10", "new", "Vaping duty of £2.20 per 10ml from 1 October 2026")],
              ["vape", "vaping"]),
    "Mansion tax": ("new", "Extra council tax on homes over £2m, expected from 2028.",
                    [("2025-11", "new", "Surcharge on homes worth over £2m announced")],
                    ["mansion tax", "council tax"]),
    "Stamp duty": ("watch", "Property tax on buying homes.", [], ["stamp duty"]),
    "Business rates": ("watch", "Property tax on shops, offices and warehouses.", [], ["business rates"]),
    "Pension tax relief": ("watch", "Tax relief on pension saving.", [], ["pension tax relief", "tax-free lump sum", "pension relief"]),
    "Oil and gas windfall tax": ("rise", "Runs to 2030.",
                                 [("2024-10", "rise", "Rate 35% to 38%, extended to 2030")],
                                 ["windfall tax", "energy profits levy"]),
    "Non-dom status": ("scrapped", "Replaced by residence-based rules.",
                       [("2024-10", "scrapped", "Abolished from April 2025")],
                       ["non-dom", "non dom"]),
    "Land value tax": ("ruled", "The Prime Minister ruled out major property tax changes in this Budget.", [],
                       ["land value tax"]),
}
history = pd.DataFrame([(t, d, c, w) for t, (_, _, h, _) in taxes.items() for d, c, w in h],
                       columns=["Tax", "When", "Change", "What changed"])

promises = {
    "Labour (in government)": [
        ("No rise in income tax, NI or VAT for working people", "Workers' rates unchanged; employer NI raised 13.8% to 15% in April 2025", "Disputed"),
        ("Keep corporation tax capped at 25%", "Still 25%", "Kept"),
        ("Add VAT to private school fees", "20% from January 2025", "Done"),
        ("Abolish non-dom status", "Abolished April 2025", "Done"),
        ("Extend the oil and gas windfall tax", "35% to 38%, extended to 2030", "Done"),
    ],
    "Conservative (lost the election)": [
        ("Cut employee NI by another 2p", "Not carried out; stayed at 8%", "Not in power"),
        ("Abolish the main rate of self-employed NI", "Not carried out", "Not in power"),
    ],
}

budgets = {"2021-10-27": "Sunak, Budget 2021", "2022-09-23": "Kwarteng, mini-budget",
           "2022-11-17": "Hunt, Autumn Statement 2022", "2023-11-22": "Hunt, Autumn Statement 2023",
           "2024-10-30": "Reeves, Budget 2024", "2025-11-26": "Reeves, Budget 2025"}
tickers = {"GBPUSD=X": "Pound vs dollar", "^FTSE": "FTSE 100", "^FTMC": "FTSE 250", "GC=F": "Gold"}

# Budget speeches on GOV.UK (full text comes from the GOV.UK content API)
SPEECHES = {
    "Sunak · Autumn Budget 2021 (27 Oct 2021)": ["autumn-budget-and-spending-review-2021-speech"],
    "Kwarteng · Growth Plan, mini-budget (23 Sep 2022)": ["the-growth-plan-2022-speech"],
    "Hunt · Autumn Statement 2022 (17 Nov 2022)": ["the-autumn-statement-2022-speech"],
    "Hunt · Spring Budget 2023 (15 Mar 2023)": ["spring-budget-2023-speech"],
    "Hunt · Autumn Statement 2023 (22 Nov 2023)": ["autumn-statement-2023-speech"],
    "Hunt · Spring Budget 2024 (6 Mar 2024)": ["spring-budget-2024-speech"],
    "Reeves · Autumn Budget 2024 (30 Oct 2024)": ["autumn-budget-2024-speech"],
    "Reeves · Spring Statement 2025 (26 Mar 2025)": ["spring-statement-2025-speech"],
    "Reeves · Budget 2025 (26 Nov 2025)": ["budget-2025-speech"],
    "Healey · Budget 2026 (28 Oct 2026)": ["budget-2026-speech", "autumn-budget-2026-speech"],
}
STOP = set("""a about above after again against all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have having he her here
hers him his how i if in into is it its itself just me more most my no nor not now of off on once only or other our ours
out over own same she should so some such than that the their theirs them then there these they this those through to
too under until up very was we were what when where which while who whom why will with would you your yours madam deputy
speaker mr today year years per cent will also make made one two three million billion £ s us let""".split())


# ================================================================ automatic tagging ("self-optimising")
RISE = r"\b(rise|rises|raise|raises|raising|hike|hikes|increase|increases|higher|hit|raid|grab|squeeze|lift)\b"
CUT = r"\b(cut|cuts|slash|slashes|reduce|reduces|lower|lowers|relief|scrap fuel duty)\b"
SCRAP = r"\b(scrap|scraps|scrapped|abolish|abolishes|abolished|axe|axes|axed)\b"
HOLD = r"\b(freeze|frozen|freezes|unchanged|keep|keeps|kept)\b"
RULED = r"\b(rule out|rules out|ruled out|rejects|rejected|no plans)\b"
NEW = r"\bnew\b(?:[ -][a-z]+){0,2} (tax|levy|duty|surcharge)\b|\b(introduce|introduces|introducing)\b"
DROP = set("""eyes eye new a an the to on of for in plans plan raise raises hike hikes cut cuts scrap scraps hit hits
consider considers considering weighs mulls urged calls call target targets impose imposes introduce introduces
treasury chancellor healey reeves budget uk govt government would could may will set his her its their""".split())
MAYBE = r"\b(could|may|might|set to|poised|considering|consider|weighs|weighing|reportedly|expected|plans?|mull|eyes|warn|warns|urged|calls?)\b"
BUDGET_WORDS = r"\b(budget|chancellor|healey|treasury|tax|taxes|duty|levy|obr|fiscal|reeves|spending review)\b"
NEW_TAX = re.compile(r"\b((?:[A-Za-z]+[ -]){0,2}[A-Za-z]+) (tax|duty|levy|surcharge)\b", re.I)
GENERIC = {"tax", "the tax", "a tax", "new tax", "tax", "taxes", "budget tax", "stealth tax", "income", "this tax", "that tax"}


def tag_story(text, when):
    """Work out which tax a story is about and which way it points."""
    t = " " + text.lower() + " "
    tax = next((name for name, (*_, words) in taxes.items() if any(w in t for w in words)), None)
    spotted = None
    if tax is None:
        for m in NEW_TAX.finditer(text):
            lead = [w for w in re.split(r"[ -]", m.group(1)) if w]
            while lead and lead[0].lower() in DROP:
                lead.pop(0)
            name = " ".join(lead + [m.group(2).lower()])
            if lead and name.lower() not in GENERIC:
                spotted = name.capitalize()
                break
    after = when is not None and when >= BUDGET_DAY
    if re.search(RULED, t):
        change = "ruled"
    elif re.search(SCRAP, t):
        change = "scrapped"
    elif re.search(NEW, t):
        change = "new"
    elif re.search(RISE, t):
        change = "rise" if after and not re.search(MAYBE, t) else "rumour"
    elif re.search(CUT, t):
        change = "cut" if after else "watch"
    elif re.search(HOLD, t):
        change = "hold"
    else:
        change = "mention"
    return tax or spotted or "", change, bool(spotted)


@st.cache_data(ttl=900, show_spinner=False)
def live_news():
    """Read every feed, keep Budget and tax stories, tag them. Refreshes every 15 minutes."""
    import feedparser
    rows, status = [], {}
    for source, urls in FEEDS.items():
        got = 0
        for url in urls:
            try:
                r = requests.get(url, headers=UA, timeout=10)
                feed = feedparser.parse(r.content)
            except Exception:
                continue
            for e in feed.entries:
                title = html.unescape(e.get("title", "")).strip()
                summary = re.sub("<[^>]+>", "", html.unescape(e.get("summary", ""))).strip()
                if not title or not re.search(BUDGET_WORDS, (title + " " + summary).lower()):
                    continue
                when = None
                for key in ("published", "updated"):
                    if e.get(key):
                        try:
                            when = parsedate_to_datetime(e[key]).astimezone(timezone.utc)
                            break
                        except Exception:
                            pass
                tax, change, spotted = tag_story(title + ". " + summary, when)
                rows.append({"when": when, "title": title, "summary": summary[:300], "source": source,
                             "link": e.get("link", ""), "tax": tax, "change": change, "spotted": spotted})
                got += 1
        status[source] = got
    df = pd.DataFrame(rows, columns=["when", "title", "summary", "source", "link", "tax", "change", "spotted"])
    if len(df):
        df = df.drop_duplicates("link").sort_values("when", ascending=False, na_position="last")
    return df, status, datetime.now(timezone.utc)


@st.cache_data(ttl=3600, show_spinner="Downloading market prices…")
def market_moves():
    import yfinance as yf
    prices = yf.download(list(tickers), start="2021-10-01", progress=False)["Close"]
    prices = prices.rename(columns=tickers).ffill().dropna()
    moves = prices.pct_change() * 100
    return pd.DataFrame({n: moves.loc[:d].iloc[-1] for d, n in budgets.items()}).T.round(2)


@st.cache_data(ttl=86400, show_spinner="Loading the speech from GOV.UK…")
def speech_text(slugs):
    """Full text of a budget speech from the GOV.UK content API. None if not published yet."""
    from bs4 import BeautifulSoup
    for slug in slugs:
        try:
            r = requests.get(f"https://www.gov.uk/api/content/government/speeches/{slug}", headers=UA, timeout=15)
            if r.status_code != 200:
                continue
            body = r.json().get("details", {}).get("body", "")
            paras = [p.get_text(" ", strip=True) for p in BeautifulSoup(body, "html.parser").find_all(["p", "li", "h2", "h3"])]
            text = "\n\n".join(p for p in paras if p)
            if text:
                return text, f"https://www.gov.uk/government/speeches/{slug}"
        except Exception:
            continue
    return None, None


def words_of(text):
    return re.findall(r"[a-z][a-z'\-]+", text.lower())


def news_card(title, link, source, when, change, tax, auto=False, summary=""):
    safe = link if str(link).startswith("http") else ""
    head = f'<a class="h" href="{esc(safe)}" target="_blank">{esc(title)}</a>' if safe else f'<div class="h" style="font-weight:700;margin:6px 0 8px">{esc(title)}</div>'
    st.markdown(
        f'<div class="bt-card"><div class="bt-meta"><span class="bt-src {src_class(source)}">{esc(source)}</span>'
        f'<span>{esc(when)}</span></div>{head}'
        + (f'<p>{esc(summary[:220])}</p>' if summary else "")
        + f'<div class="bt-meta">{chip(change) if change else ""}<span>{esc(tax)}</span>'
        + ('<span class="bt-auto">· labelled automatically</span>' if auto else "") + "</div></div>",
        unsafe_allow_html=True)


# ================================================================ header
left = BUDGET_DAY - datetime.now(timezone.utc)
if left.days >= 1:
    big, small = f"{left.days + (1 if left.seconds else 0)} days to go", "Speech after PMQs, about 12:30"
elif left.total_seconds() > 0:
    big, small = f"Today · {left.seconds // 3600}h {(left.seconds % 3600) // 60}m", "Speech starts about 12:30"
else:
    big, small = "Budget delivered", "Wednesday 28 October 2026"
st.markdown(f"""<div class="bt-head"><div><div class="bt-brand">Budget Tracker</div>
<div class="bt-sub">UK Autumn Budget · Wednesday 28 October 2026 · Chancellor John Healey</div></div>
<div class="bt-count"><b>{esc(big)}</b><span>{esc(small)}</span></div></div>""", unsafe_allow_html=True)

tabs = st.tabs(["News", "Compare budgets", "Markets", "Taxes", "Library", "Search", "Promises"])
tab_news, tab_compare, tab_markets, tab_taxes, tab_library, tab_search, tab_promises = tabs

# ================================================================ news (refreshes itself)
with tab_news:
    @st.fragment(run_every="15m")
    def news_panel():
        live, status, fetched = live_news()
        top = st.columns([3, 1])
        top[0].caption("Live from " + ", ".join(f"{s} ({n})" for s, n in status.items())
                       + f" · checked {fetched:%H:%M} UTC · refreshes every 15 minutes")
        if top[1].button("Refresh now"):
            live_news.clear()
            st.rerun()
        feed_col, watch_col = st.columns([1.7, 1], gap="large")
        with feed_col:
            src = st.radio("Source", ["All", "BBC", "FT", "City AM"], horizontal=True, key="src")
            shown = live if src == "All" else live[live["source"] == src]
            today = shown[shown["when"].notna() & (shown["when"].dt.date == datetime.now(timezone.utc).date())]
            st.subheader(f"Today ({len(today)})")
            if len(today):
                for _, n in today.iterrows():
                    news_card(n.title, n.link, n.source, f"{n.when:%H:%M}", n.change, n.tax, auto=True, summary=n.summary)
            else:
                st.write("No Budget stories yet today from this source.")
            older = shown.drop(today.index)
            if len(older):
                with st.expander(f"Earlier live stories ({len(older)})"):
                    for _, n in older.iterrows():
                        news_card(n.title, n.link, n.source, f"{n.when:%d %b %H:%M}" if pd.notna(n.when) else "",
                                  n.change, n.tax, auto=True)
            st.subheader("Saved stories")
            for n in sorted(saved_notes, key=lambda x: x["date"], reverse=True):
                news_card(n["title"], n["link"], n["source"], datetime.fromisoformat(n["date"]).strftime("%d %b %Y"), n["change"], n["tax"])
        with watch_col:
            rows = "".join(
                f'<div class="bt-row"><div><div class="nm">{esc(name)}</div><div class="sub">{esc(note)}</div></div>{chip(now)}</div>'
                for name, (now, note, _, _) in taxes.items() if now in ("rumour", "new", "rise", "cut", "watch", "ruled"))
            st.markdown(f'<div class="bt-panel"><h4>Tax watch</h4><div class="sub" style="color:#58616A;font-size:13px">'
                        f'Where things stand before Budget day.</div>{rows}</div>', unsafe_allow_html=True)
    news_panel()

# ================================================================ compare
with tab_compare:
    a, b = st.columns([1, 2])
    pick = a.selectbox("Sector", list(cash.columns), index=1)
    prices_mode = a.radio("Prices", ["After inflation", "Cash"])
    data = real if prices_mode == "After inflation" else cash
    v = data[pick]
    a.metric("Change over five years", f"{(v.iloc[-1] / v.iloc[0] - 1) * 100:+.1f}%")
    fig = go.Figure(go.Bar(x=[f"{y}<br>{p}" for y, p in zip(years, party)], y=v, marker_color=RED,
                           text=[f"£{x:.0f}bn" for x in v], textposition="outside", cliponaxis=False))
    b.plotly_chart(style(fig, f"{pick}, £ billion ({prices_mode.lower()})", 440, bottom=80), width="stretch")

    ch = ((data.iloc[-1] / data.iloc[0] - 1) * 100).sort_values()
    fig2 = go.Figure(go.Bar(x=ch.values, y=ch.index, orientation="h", cliponaxis=False,
                            marker_color=[BLUE if x >= 0 else ORANGE for x in ch.values],
                            text=[f"{x:+.1f}%" for x in ch.values], textposition="outside"))
    style(fig2, f"Every sector: change 2021-22 to 2025-26 ({prices_mode.lower()})", 480)
    fig2.update_xaxes(zeroline=True, zerolinecolor="#333", zerolinewidth=1.5, range=[ch.min() - 8, ch.max() + 8])
    fig2.update_layout(margin=dict(l=180, t=70))
    st.plotly_chart(fig2, width="stretch")
    st.caption("Source: HM Treasury, Public Expenditure Statistical Analyses 2026. Welfare and debt interest are UK-wide; "
               "other sectors are departmental budgets, so health and education mostly cover England.")

# ================================================================ markets
with tab_markets:
    try:
        day = market_moves()
        colors = {"Pound vs dollar": RED, "FTSE 100": GREEN, "FTSE 250": BLUE, "Gold": GOLD}
        fig3 = go.Figure()
        for col in ["Pound vs dollar", "FTSE 100", "FTSE 250", "Gold"]:
            fig3.add_bar(x=[n.replace(", ", "<br>") for n in day.index], y=day[col], name=col, marker_color=colors[col],
                         text=[f"{x:+.1f}%" for x in day[col]], textposition="outside", textfont_size=11, cliponaxis=False)
        style(fig3, "How markets moved on budget day (%)", 560, legend_below=True, bottom=40)
        fig3.update_layout(barmode="group", bargap=0.25)
        fig3.update_yaxes(zeroline=True, zerolinecolor="#333", zerolinewidth=1.5, title="% change on the day")
        st.plotly_chart(fig3, width="stretch")
        st.dataframe(day, width="stretch")
    except Exception as e:
        st.warning(f"Couldn't download market prices right now ({type(e).__name__}). Try again in a minute.")

# ================================================================ taxes (adds new ones by itself)
with tab_taxes:
    live, _, _ = live_news()
    status_pick = st.multiselect("Show", [k for k in LABEL if k != "mention"], default=[k for k in LABEL if k != "mention"],
                                 format_func=lambda k: LABEL[k])
    spotted = live[live["spotted"]] if len(live) else live
    if len(spotted):
        st.subheader("New in the news")
        st.caption("Taxes the app found in today's stories that aren't in its list yet. Added automatically.")
        for name, grp in spotted.groupby("tax"):
            latest = grp.iloc[0]
            with st.expander(f"{name} — {LABEL.get(latest.change, latest.change)} · {len(grp)} {'story' if len(grp) == 1 else 'stories'}"):
                for _, n in grp.iterrows():
                    st.markdown(f"- [{n.title}]({n.link}) · {n.source}")
    st.subheader("Every tax")
    for name, (now, note, hist, _) in taxes.items():
        if now not in status_pick:
            continue
        with st.expander(f"{name} — {LABEL[now]}"):
            st.markdown(f'{chip(now)} &nbsp;<span style="color:#58616A">{esc(note)}</span>', unsafe_allow_html=True)
            if hist:
                h = pd.DataFrame(hist, columns=["When", "Change", "What changed"]).sort_values("When", ascending=False)
                h["Change"] = h["Change"].map(LABEL)
                st.dataframe(h, hide_index=True, width="stretch")
            related = [n for n in saved_notes if n["tax"] == name]
            rel_live = live[live["tax"] == name] if len(live) else live
            for n in related:
                st.markdown(f"- [{n['title']}]({n['link']}) · {n['source']}, {n['date']}")
            for _, n in rel_live.iterrows():
                st.markdown(f"- [{n.title}]({n.link}) · {n.source} · `{LABEL.get(n.change, n.change)}` (live)")

# ================================================================ library: every word of every budget speech
with tab_library:
    st.subheader("Budget speech library")
    st.caption("The full text of each speech, word for word, from GOV.UK. Budget 2026 appears here automatically once GOV.UK publishes it.")
    choice = st.selectbox("Speech", list(SPEECHES), index=len(SPEECHES) - 2)
    text, url = speech_text(tuple(SPEECHES[choice]))
    if text is None:
        st.info("This speech isn't on GOV.UK yet. It's added automatically after the Chancellor sits down.")
    else:
        words = words_of(text)
        k1, k2, k3 = st.columns(3)
        k1.metric("Words", f"{len(words):,}")
        k2.metric("Times “tax” is said", sum(w.startswith("tax") for w in words))
        k3.metric("Times “growth” is said", words.count("growth"))
        common = Counter(w for w in words if w not in STOP and len(w) > 2).most_common(15)[::-1]
        figw = go.Figure(go.Bar(x=[c for _, c in common], y=[w for w, _ in common], orientation="h", marker_color=RED,
                                text=[c for _, c in common], textposition="outside", cliponaxis=False))
        style(figw, "Most used words in this speech", 480)
        figw.update_layout(margin=dict(l=120, t=70))
        st.plotly_chart(figw, width="stretch")

        find = st.text_input("Find a word or phrase in this speech", placeholder="fuel duty, growth, pensions…").strip()
        if find:
            sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n\n", " "))
            hits = [s for s in sentences if find.lower() in s.lower()]
            st.write(f"**{len(hits)}** sentences mention “{find}”.")
            for s in hits[:40]:
                st.markdown("> " + re.sub(re.escape(find), lambda m: f"**{m.group(0)}**", s, flags=re.I))
        with st.expander("Read the whole speech"):
            st.markdown(text)
        st.caption(f"Source: [GOV.UK]({url}) · Crown copyright, Open Government Licence v3.0")

    st.subheader("Compare words across budgets")
    compare_words = st.text_input("Words to compare, separated by commas", "growth, tax, debt, investment, NHS")
    wanted = [w.strip().lower() for w in compare_words.split(",") if w.strip()]
    if wanted:
        rows = {}
        for name, slugs in SPEECHES.items():
            t, _ = speech_text(tuple(slugs))
            if t:
                low = " " + " ".join(words_of(t)) + " "
                rows[name.split(" (")[0]] = {w: low.count(" " + w) for w in wanted}
        if rows:
            counts = pd.DataFrame(rows).T
            figc = go.Figure()
            palette = [RED, BLUE, GREEN, GOLD, ORANGE, GREY]
            for i, w in enumerate(counts.columns):
                figc.add_bar(x=[n.replace(" · ", "<br>") for n in counts.index], y=counts[w], name=w,
                             marker_color=palette[i % len(palette)])
            style(figc, "How often each word was used", 560, legend_below=True, bottom=60)
            figc.update_layout(barmode="group")
            st.plotly_chart(figc, width="stretch")

    st.subheader("Official documents")
    for name in SPEECHES:
        label = name.split(" · ")[1].split(" (")[0]
        st.markdown(f"- {name}: [all documents on GOV.UK](https://www.gov.uk/search/all?keywords={label.replace(' ', '+')}&order=relevance)")

# ================================================================ search
with tab_search:
    q = st.text_input("Search taxes, past changes, news, promises and speeches",
                      placeholder="fuel, VAT, non-dom…").strip().lower()
    if q:
        live, _, _ = live_news()
        h = history[history["Tax"].str.lower().str.contains(q, regex=False) | history["What changed"].str.lower().str.contains(q, regex=False)]
        st.subheader(f"Past changes ({len(h)})")
        if len(h):
            st.dataframe(h.assign(Change=h["Change"].map(LABEL)), hide_index=True, width="stretch")
        else:
            st.write("None")
        found = [n for n in saved_notes if q in n["title"].lower() or q in n["tax"].lower()]
        lv = live[live["title"].str.lower().str.contains(q, regex=False) | live["tax"].str.lower().str.contains(q, regex=False)] if len(live) else live
        st.subheader(f"News ({len(found) + len(lv)})")
        for n in found:
            st.markdown(f"- [{n['title']}]({n['link']}) · {n['source']}, {n['date']} · `{LABEL[n['change']]}`")
        for _, n in lv.iterrows():
            st.markdown(f"- [{n.title}]({n.link}) · {n.source} · `{LABEL.get(n.change, n.change)}` (live)")
        p = [(pn, *row) for pn, rows in promises.items() for row in rows if q in row[0].lower() or q in row[1].lower()]
        st.subheader(f"Manifesto promises ({len(p)})")
        if p:
            st.dataframe(pd.DataFrame(p, columns=["Party", "Promise", "What happened", "Status"]), hide_index=True, width="stretch")
        else:
            st.write("None")
        st.subheader("Budget speeches")
        for name, slugs in SPEECHES.items():
            t, u = speech_text(tuple(slugs))
            if t and q in t.lower():
                n_hits = t.lower().count(q)
                first = next(s for s in re.split(r"(?<=[.!?])\s+", t.replace("\n\n", " ")) if q in s.lower())
                st.markdown(f"- **{name}**: said {n_hits} {'time' if n_hits == 1 else 'times'}. “{first[:220]}…” [Read]({u})")

# ================================================================ promises
with tab_promises:
    who = st.radio("Party", list(promises), horizontal=True)
    for promise, result, stat in promises[who]:
        st.markdown(f'<div class="bt-promise"><div class="top"><span>{esc(promise)}</span>{chip(stat.lower().replace(" in power", "").replace("not", "out"), stat)}</div>'
                    f'<div class="what"><b>What happened:</b> {esc(result)}</div></div>', unsafe_allow_html=True)
