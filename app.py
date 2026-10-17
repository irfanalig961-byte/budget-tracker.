"""Budget Tracker: UK Autumn Budget, Wednesday 28 October 2026.
Start it with:  streamlit run app.py
"""
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Budget Tracker", page_icon="📕", layout="wide")

RED, BLUE, ORANGE, GREEN, GOLD, GREY = "#A51C1C", "#2B6CB0", "#C05621", "#2F855A", "#D69E2E", "#B0B7BF"
CHART = dict(template="simple_white", font=dict(family="Arial", size=14), title_x=0.0,
             margin=dict(l=40, r=30, t=60, b=40), legend=dict(orientation="h", y=1.1, x=0))
LABEL = {"rise": "▲ Rise", "cut": "▼ Cut", "new": "✚ New", "scrapped": "✕ Scrapped", "hold": "● No change",
         "rumour": "▲ Rumoured rise", "ruled": "Ruled out", "watch": "Under review"}

# ---------------------------------------------------------------- data
notes = [
    {"date": "2026-10-07", "title": "Investors warn against a capital gains rise",
     "summary": "Hargreaves Lansdown says a rise would put investors off when the UK needs growth.",
     "tax": "Capital gains tax", "change": "rumour", "source": "City AM",
     "link": "https://www.cityam.com/hargreaves-lansdown-warns-healey-dont-penalise-investors-with-capital-gains-hike/"},
    {"date": "2026-10-13", "title": "Matching capital gains to income tax reportedly ruled out",
     "summary": "A full match with income tax rates looks off the table, but a smaller rise is still possible.",
     "tax": "Capital gains tax", "change": "rumour", "source": "FT (via Newsquawk)",
     "link": "https://www.newsquawk.com/headlines/uk-chancellor-healey-is-reportedly-rejecting-calls-to-equalise-cgt-and-income-tax-rates-ft-reports-citing-sources"},
    {"date": "2026-10-14", "title": "New spending to be paid for without more borrowing",
     "summary": "New measures would be paid for with tax rises or cuts elsewhere, not extra borrowing.",
     "tax": "Taxes or spending cuts", "change": "rumour", "source": "FT (via Reuters)",
     "link": "https://www.devdiscourse.com/article/international/3991997-update-1-uk-finance-minister-healey-set-to-pay-for-budget-measures-without-more-borrowing-ft-reports"},
    {"date": "2026-10-15", "title": "Gambling firms warn about Budget tax rises",
     "summary": "Entain and Rank say new gambling taxes, including on gaming machines, could close venues.",
     "tax": "Gambling duties", "change": "rumour", "source": "City AM",
     "link": "https://www.cityam.com/entain-and-rank-warn-budget-tax-hikes-threaten-betting-shops-and-jobs/"},
    {"date": "2026-10-16", "title": "Bank shares fall on bank tax reports",
     "summary": "Reports say the 3% bank surcharge could rise, possibly reversing the 2023 cut.",
     "tax": "Bank surcharge", "change": "rumour", "source": "City AM",
     "link": "https://www.cityam.com/john-healey-poised-to-target-banks-with-budget-tax-raid/"},
]
news = pd.DataFrame(notes)
news["date"] = pd.to_datetime(news["date"])
news = news.sort_values("date", ascending=False)

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

taxes = {
    "Income tax":         ("hold", "Manifesto pledge: no rise in the rates working people pay.",
                           [("2022-11", "rise", "Top 45% rate starts at £125,140, down from £150,000; thresholds frozen to 2028"),
                            ("2025-11", "rise", "Threshold freeze extended to April 2031"),
                            ("2025-11", "rise", "Dividend tax up 2 points from 2026; savings and property income up 2 points from 2027")]),
    "National Insurance": ("hold", "Manifesto pledge covers the employee rate.",
                           [("2023-11", "cut", "Employee rate 12% to 10% from January 2024"),
                            ("2024-03", "cut", "Employee rate 10% to 8% from April 2024"),
                            ("2024-10", "rise", "Employer rate 13.8% to 15%; starts on pay over £5,000 instead of £9,100")]),
    "VAT":                ("hold", "Manifesto pledge: standard rate stays 20%.",
                           [("2024-10", "new", "20% VAT on private school fees from January 2025"),
                            ("2026-07", "cut", "Home electricity 5% to 0%, 1 Oct 2026 to 31 Mar 2027")]),
    "Capital gains tax":  ("rumour", "Matching income tax rates reportedly ruled out; a smaller rise is possible.",
                           [("2022-11", "rise", "Tax-free allowance £12,300 to £6,000, then £3,000"),
                            ("2024-10", "rise", "Main rates 10% and 20% to 18% and 24%")]),
    "Corporation tax":    ("hold", "Manifesto pledge: capped at 25%.",
                           [("2021-03", "rise", "Main rate 19% to 25% from April 2023")]),
    "Bank surcharge":     ("rumour", "Reports say a rise from 3% is being weighed.",
                           [("2021-10", "cut", "8% to 3% from April 2023")]),
    "Gambling duties":    ("rumour", "Firms warn of further rises in this Budget.",
                           [("2025-11", "rise", "Remote gaming duty 21% to 40%")]),
    "Inheritance tax":    ("rise", "Pension change takes effect April 2027.",
                           [("2024-10", "rise", "Unused pensions count towards estates from April 2027"),
                            ("2025-11", "hold", "£325,000 threshold frozen to April 2031")]),
    "Fuel duty":          ("watch", "5p cut kept to 31 Dec 2026; a rise is due 1 Jan 2027 unless changed.",
                           [("2022-03", "cut", "Cut by 5p to 52.95p a litre"),
                            ("2024-10", "hold", "Freeze and 5p cut kept for another year"),
                            ("2026-05", "hold", "September rise cancelled; cut kept to end of 2026")]),
    "Vapes":              ("new", "New duty starts 1 October 2026.",
                           [("2024-10", "new", "Vaping duty of £2.20 per 10ml from 1 October 2026")]),
    "Mansion tax":        ("new", "Extra council tax on homes over £2m, expected from 2028.",
                           [("2025-11", "new", "Surcharge on homes worth over £2m announced")]),
    "Oil and gas windfall tax": ("rise", "Runs to 2030.",
                           [("2024-10", "rise", "Rate 35% to 38%, extended to 2030")]),
    "Non-dom status":     ("scrapped", "Replaced by residence-based rules.",
                           [("2024-10", "scrapped", "Abolished from April 2025")]),
    "Land value tax":     ("ruled", "The Prime Minister ruled out major property tax changes in this Budget.", []),
}
history = pd.DataFrame([(t, d, c, w) for t, (_, _, h) in taxes.items() for d, c, w in h],
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


@st.cache_data(ttl=3600, show_spinner="Downloading market prices…")
def market_moves():
    import yfinance as yf
    prices = yf.download(list(tickers), start="2021-10-01", progress=False)["Close"]
    prices = prices.rename(columns=tickers).ffill().dropna()
    moves = prices.pct_change() * 100
    return pd.DataFrame({n: moves.loc[:d].iloc[-1] for d, n in budgets.items()}).T.round(2)


# ---------------------------------------------------------------- header
left = datetime(2026, 10, 28, 12, 30, tzinfo=timezone.utc) - datetime.now(timezone.utc)
st.title("📕 Budget Tracker")
st.caption("UK Autumn Budget · Wednesday 28 October 2026 · Chancellor John Healey")
c1, c2, c3 = st.columns(3)
c1.metric("Until the speech", f"{left.days} days" if left.total_seconds() > 0 else "Delivered")
c2.metric("Stories tracked", len(news))
c3.metric("Taxes tracked", len(taxes))

tab_news, tab_compare, tab_markets, tab_taxes, tab_search, tab_promises = st.tabs(
    ["News", "Compare budgets", "Markets", "Taxes", "Search", "Promises"])

# ---------------------------------------------------------------- news
with tab_news:
    src = st.radio("Source", ["All"] + sorted(news["source"].unique()), horizontal=True)
    shown = news if src == "All" else news[news["source"] == src]
    for _, n in shown.iterrows():
        with st.container(border=True):
            st.markdown(f"**[{n.title}]({n.link})**")
            st.caption(f"{n.source} · {n.date:%d %b %Y}")
            st.write(n.summary)
            st.markdown(f"`{LABEL[n.change]}` · {n.tax}")
    st.info("BBC stories aren't copied in. Follow them in your Google Sheet tracker or on bbc.co.uk/news/business.")

# ---------------------------------------------------------------- compare
with tab_compare:
    a, b = st.columns([1, 2])
    pick = a.selectbox("Sector", list(cash.columns), index=1)
    prices_mode = a.radio("Prices", ["After inflation", "Cash"])
    data = real if prices_mode == "After inflation" else cash
    v = data[pick]
    a.metric("Change over five years", f"{(v.iloc[-1] / v.iloc[0] - 1) * 100:+.1f}%")

    fig = go.Figure(go.Bar(x=[f"{y}<br><sub>{p}</sub>" for y, p in zip(years, party)], y=v,
                           marker_color=RED, text=[f"£{x:.0f}bn" for x in v], textposition="outside"))
    fig.update_layout(title=f"{pick}, £ billion ({prices_mode.lower()})", height=430, **CHART)
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE", rangemode="tozero")
    b.plotly_chart(fig, width="stretch")

    ch = ((data.iloc[-1] / data.iloc[0] - 1) * 100).sort_values()
    fig2 = go.Figure(go.Bar(x=ch.values, y=ch.index, orientation="h",
                            marker_color=[BLUE if x >= 0 else ORANGE for x in ch.values],
                            text=[f"{x:+.1f}%" for x in ch.values], textposition="outside"))
    fig2.update_layout(title=f"Every sector: change 2021-22 to 2025-26 ({prices_mode.lower()})", height=460, **CHART)
    fig2.update_xaxes(showgrid=True, gridcolor="#EEEEEE", zeroline=True, zerolinecolor="#333", zerolinewidth=1.5)
    st.plotly_chart(fig2, width="stretch")
    st.caption("Source: HM Treasury, Public Expenditure Statistical Analyses 2026. Welfare and debt interest are UK-wide; "
               "other sectors are departmental budgets, so health and education mostly cover England.")

# ---------------------------------------------------------------- markets
with tab_markets:
    try:
        day = market_moves()
        fig3 = go.Figure()
        colors = {"Pound vs dollar": RED, "FTSE 100": GREEN, "FTSE 250": BLUE, "Gold": GOLD}
        for col in day.columns:
            fig3.add_bar(x=[n.replace(", ", "<br>") for n in day.index], y=day[col], name=col,
                         marker_color=colors[col], text=[f"{x:+.1f}%" for x in day[col]], textposition="outside")
        fig3.update_layout(title="How markets moved on budget day (%)", barmode="group", height=520, **CHART)
        fig3.update_yaxes(showgrid=True, gridcolor="#EEEEEE", zeroline=True, zerolinecolor="#333", zerolinewidth=1.5)
        st.plotly_chart(fig3, width="stretch")
        st.dataframe(day, width="stretch")
    except Exception as e:
        st.warning(f"Couldn't download market prices right now ({type(e).__name__}). Try again in a minute.")

# ---------------------------------------------------------------- taxes
with tab_taxes:
    status = st.multiselect("Show", list(LABEL), default=list(LABEL), format_func=lambda k: LABEL[k])
    for name, (now, note, hist) in taxes.items():
        if now not in status:
            continue
        with st.expander(f"{name} — {LABEL[now]}"):
            st.write(note)
            if hist:
                h = pd.DataFrame(hist, columns=["When", "Change", "What changed"]).sort_values("When", ascending=False)
                h["Change"] = h["Change"].map(LABEL)
                st.dataframe(h, hide_index=True, width="stretch")
            related = news[news["tax"] == name]
            for _, n in related.iterrows():
                st.markdown(f"- [{n.title}]({n.link}) · {n.source}, {n.date:%d %b}")

# ---------------------------------------------------------------- search
with tab_search:
    q = st.text_input("Search taxes, past changes, news and promises", placeholder="fuel, VAT, non-dom…").strip().lower()
    if q:
        h = history[history["Tax"].str.lower().str.contains(q) | history["What changed"].str.lower().str.contains(q)]
        n = news[news["title"].str.lower().str.contains(q) | news["tax"].str.lower().str.contains(q)
                 | news["summary"].str.lower().str.contains(q)]
        p = [(party_name, *row) for party_name, rows in promises.items() for row in rows
             if q in row[0].lower() or q in row[1].lower()]
        st.subheader(f"Past changes ({len(h)})")
        if len(h):
            st.dataframe(h.assign(Change=h["Change"].map(LABEL)), hide_index=True, width="stretch")
        else:
            st.write("None")
        st.subheader(f"News ({len(n)})")
        for _, r in n.iterrows():
            st.markdown(f"- [{r.title}]({r.link}) · {r.source}, {r.date:%d %b} · `{LABEL[r.change]}`")
        if not len(n):
            st.write("None")
        st.subheader(f"Manifesto promises ({len(p)})")
        if p:
            st.dataframe(pd.DataFrame(p, columns=["Party", "Promise", "What happened", "Status"]),
                         hide_index=True, width="stretch")
        else:
            st.write("None")

# ---------------------------------------------------------------- promises
with tab_promises:
    who = st.radio("Party", list(promises), horizontal=True)
    for promise, result, stat in promises[who]:
        with st.container(border=True):
            st.markdown(f"**{promise}**  ·  `{stat}`")
            st.caption(f"What happened: {result}")
