
import os
from datetime import datetime, date
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Deon's Trader Dashboard v19.1", layout="wide")

MARKETS = ["SPY", "QQQ", "^VIX", "^TNX"]
DEFAULT_SCAN = ["NVDA","AMD","AVGO","ARM","MU","TSM","MRVL","CRDO","PLTR","APP","HOOD","HIMS","SOFI","RDDT","META","AMZN","MSFT","GOOGL","TSLA","COIN","SMCI","DELL","ORCL","CEG","VRT","ANET"]
DEFAULT_WATCHLIST = ["NVDA","AMD","AVGO","MU","TSM","PLTR","CRDO","META"]
JOURNAL_FILE = "trade_journal_v19_1.csv"

SECTOR = {
    "NVDA":"Semis","AMD":"Semis","AVGO":"Semis","ARM":"Semis","MU":"Semis","TSM":"Semis","MRVL":"Semis","CRDO":"Semis",
    "SMCI":"AI Infra","DELL":"AI Infra","VRT":"AI Infra","ANET":"AI Infra","PLTR":"AI Software","APP":"Software",
    "MSFT":"Mega Cap","GOOGL":"Mega Cap","META":"Mega Cap","AMZN":"Mega Cap","HOOD":"Fintech","SOFI":"Fintech",
    "COIN":"Crypto","MSTR":"Crypto","HIMS":"Momentum","RDDT":"Momentum","TSLA":"High Beta","ORCL":"Software","CEG":"Energy"
}

@st.cache_data(ttl=60)
def get_data(ticker, period="3mo", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        for c in ["Open","High","Low","Close","Volume"]:
            if c not in df.columns:
                return pd.DataFrame()
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def num(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def pct(df, bars):
    if df.empty or len(df) <= bars:
        return 0.0
    a = num(df["Close"].iloc[-bars])
    b = num(df["Close"].iloc[-1])
    return round(((b / a) - 1) * 100, 2) if a > 0 else 0.0

def clean_money(x):
    if pd.isna(x):
        return 0.0
    s = str(x).replace("$","").replace(",","").strip()
    neg = "(" in s and ")" in s
    s = s.replace("(","").replace(")","")
    try:
        v = float(s)
        return -v if neg else v
    except Exception:
        return 0.0

def clean_qty(x):
    try:
        return float(str(x).replace(",","").strip())
    except Exception:
        return 0.0

def market_context():
    rows = []
    for t in MARKETS:
        df = get_data(t, "1mo", "1d")
        if df.empty:
            continue
        close = num(df["Close"].iloc[-1])
        ma10 = num(df["Close"].rolling(10).mean().iloc[-1], close)
        rows.append({"Market":t, "Price":round(close,2), "1D %":pct(df,2), "5D %":pct(df,6), "Trend":"Above 10MA" if close >= ma10 else "Below 10MA"})
    return pd.DataFrame(rows)

def market_state(mdf):
    if mdf.empty:
        return "RED","Defensive",0,"Market data unavailable"
    def v(sym, col):
        x = mdf.loc[mdf["Market"] == sym, col].values
        return num(x[0]) if len(x) else 0.0
    score = 50
    score += 15 if v("SPY","1D %") >= 0 else -15
    score += 15 if v("QQQ","1D %") >= 0 else -15
    score += 10 if v("SPY","5D %") >= 0 else -10
    score += 10 if v("QQQ","5D %") >= 0 else -10
    score += 10 if v("^VIX","1D %") <= 0 else -20
    score = int(max(0, min(100, score)))
    if score >= 70:
        return "GREEN","Bullish",score,"Indexes constructive and volatility calm"
    if score >= 45:
        return "YELLOW","Mixed",score,"Mixed tape; be selective"
    return "RED","Defensive",score,"Weak indexes or elevated volatility"

def intraday(ticker):
    df = get_data(ticker, "1d", "5m")
    if df.empty or len(df) < 3:
        return {"Above VWAP":False, "OR Zone":"Unknown", "OR Status":"Unknown", "Intraday Trend":"Unknown", "OR High":np.nan, "OR Low":np.nan, "VWAP":np.nan}
    current = num(df["Close"].iloc[-1])
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    volume = num(df["Volume"].sum())
    vwap = num((typical * df["Volume"]).sum() / volume, current) if volume > 0 else current
    opening = df.head(3)
    high = num(opening["High"].max())
    low = num(opening["Low"].min())
    rng = high - low
    pos = (current - low) / rng if rng > 0 else 0.5
    if current > high:
        status = "Above OR High"
    elif current < low:
        status = "Below OR Low"
    else:
        status = "Inside OR"
    if pos > 1:
        zone = "Breakout"
    elif pos >= .80:
        zone = "Near breakout"
    elif pos >= .60:
        zone = "Upper range"
    elif pos >= .20:
        zone = "Middle"
    elif pos >= 0:
        zone = "Near breakdown"
    else:
        zone = "Breakdown"
    above = current >= vwap
    if above and status == "Above OR High":
        trend = "Bullish ORB"
    elif above and zone in ["Near breakout","Upper range"]:
        trend = "Constructive"
    elif (not above) and status == "Below OR Low":
        trend = "Bearish ORB"
    elif zone in ["Near breakdown","Breakdown"]:
        trend = "Weak"
    else:
        trend = "Choppy"
    return {"Above VWAP":bool(above), "OR Zone":zone, "OR Status":status, "Intraday Trend":trend, "OR High":round(high,2), "OR Low":round(low,2), "VWAP":round(vwap,2)}

def rs_score(stock, spy):
    if stock.empty or spy.empty:
        return 50
    raw = ((pct(stock,6) - pct(spy,6)) * 2) + (pct(stock,22) - pct(spy,22))
    return int(max(0, min(100, round(50 + raw))))

def gap(df):
    if df.empty or len(df) < 2:
        return 0.0
    prev = num(df["Close"].iloc[-2])
    opn = num(df["Open"].iloc[-1])
    return round(((opn / prev) - 1) * 100, 2) if prev > 0 else 0.0

def analyze(ticker, spy, light, cash, risk_pct):
    df = get_data(ticker, "3mo", "1d")
    if df.empty or len(df) < 30:
        return None
    close = num(df["Close"].iloc[-1])
    ma20 = num(df["Close"].rolling(20).mean().iloc[-1], close)
    ma50 = num(df["Close"].rolling(50).mean().iloc[-1], close)
    high20 = num(df["High"].rolling(20).max().iloc[-2], close)
    low10 = num(df["Low"].rolling(10).min().iloc[-1], close * .95)
    avg_vol = num(df["Volume"].rolling(20).mean().iloc[-1])
    rel_vol = num(df["Volume"].iloc[-1]) / avg_vol if avg_vol > 0 else 0
    above20 = close >= ma20
    above50 = close >= ma50
    dist20 = ((close / ma20) - 1) * 100 if ma20 > 0 else 0
    breakout = close > high20
    near_high = abs((close / high20) - 1) * 100 <= 3 if high20 > 0 else False
    intra = intraday(ticker)
    rs = rs_score(df, spy)
    gp = gap(df)
    if intra["Intraday Trend"] == "Bullish ORB":
        pattern = "Bullish ORB"
    elif intra["OR Zone"] == "Near breakout":
        pattern = "OR Breakout Watch"
    elif intra["Above VWAP"] and above20 and above50:
        pattern = "VWAP Continuation"
    elif breakout:
        pattern = "Daily Breakout"
    elif near_high:
        pattern = "Near Daily Breakout"
    elif intra["Intraday Trend"] in ["Weak","Bearish ORB"]:
        pattern = "Weak / Breakdown"
    else:
        pattern = "No Clear Pattern"
    score = 0
    score += 10 if above20 else 0
    score += 10 if above50 else 0
    score += 10 if pct(df,6) > 3 else 0
    score += 10 if pct(df,22) > 8 else 0
    score += 10 if rs >= 70 else 6 if rs >= 60 else -10 if rs < 40 else 0
    score += 8 if rel_vol >= 1.25 else 0
    score += 8 if near_high else 0
    score += 12 if breakout else 0
    score += 16 if intra["OR Zone"] in ["Breakout","Near breakout"] else 0
    score += 8 if intra["OR Zone"] == "Upper range" else 0
    score -= 16 if intra["OR Zone"] in ["Near breakdown","Breakdown"] else 0
    score += 16 if intra["Intraday Trend"] == "Bullish ORB" else 0
    score -= 20 if intra["Intraday Trend"] == "Bearish ORB" else 0
    score += 8 if intra["Above VWAP"] else -6
    score -= 8 if dist20 > 15 else 0
    score -= 6 if pct(df,2) > 8 else 0
    score += 5 if gp >= 2 and intra["Above VWAP"] else -5 if gp <= -2 else 0
    score += 8 if light == "GREEN" else -12 if light == "RED" else 0
    score = max(0, min(100, round(score,1)))
    prob = int(max(0, min(95, round(35 + score * .55))))
    grade = "A+" if prob >= 80 else "A" if prob >= 70 else "B" if prob >= 60 else "C" if prob >= 50 else "No Trade"
    stop = round(max(low10, close * .94), 2)
    risk_share = max(0, close - stop)
    target1 = round(close + risk_share * 1.5, 2) if risk_share > 0 else round(close * 1.05, 2)
    target2 = round(close + risk_share * 2.0, 2) if risk_share > 0 else round(close * 1.10, 2)
    rr = (target2 - close) / risk_share if risk_share > 0 else 0
    ev = ((prob / 100) * (target1 - close)) - ((1 - prob / 100) * risk_share) if risk_share > 0 else 0
    if score >= 75 and intra["OR Status"] == "Above OR High" and ev > 0:
        signal = "BUY NOW"
    elif score >= 62 and intra["OR Zone"] in ["Near breakout","Breakout"] and ev > 0:
        signal = "BUY ON BREAKOUT"
    elif score >= 55:
        signal = "WATCH"
    else:
        signal = "WAIT"
    if (intra["OR Status"] == "Below OR Low" or ev <= 0) and score < 55:
        signal = "AVOID"
    shares = min((cash * risk_pct) / risk_share, cash / close) if risk_share > 0 and close > 0 else 0
    if signal not in ["BUY NOW","BUY ON BREAKOUT"] or grade in ["C","No Trade"] or ev <= 0:
        shares = 0
    if light == "RED":
        shares *= .5
    return {
        "Ticker":ticker, "Sector":SECTOR.get(ticker,"Other"), "Signal":signal, "Pattern":pattern,
        "Price":round(close,2), "Probability %":prob, "Grade":grade, "Score":score, "RS Score":rs,
        "Gap %":gp, "1D %":pct(df,2), "5D %":pct(df,6), "1M %":pct(df,22),
        "Rel Vol":round(rel_vol,2), "Above VWAP":intra["Above VWAP"], "VWAP":intra["VWAP"],
        "Intraday Trend":intra["Intraday Trend"], "OR Status":intra["OR Status"], "OR Zone":intra["OR Zone"],
        "OR High":intra["OR High"], "OR Low":intra["OR Low"], "Dist 20MA %":round(dist20,2),
        "Stop":stop, "Target 1":target1, "Target 2":target2, "Reward/Risk":round(rr,2),
        "EV / Share":round(ev,2), "Shares":round(shares,4), "Position $":round(shares*close,2), "Dollar Risk":round(shares*risk_share,2)
    }

def run_scan(symbols, light, cash, risk_pct):
    spy = get_data("SPY", "3mo", "1d")
    rows, seen = [], set()
    for s in symbols:
        s = s.strip().upper()
        if not s or s in seen:
            continue
        seen.add(s)
        row = analyze(s, spy, light, cash, risk_pct)
        if row:
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["EV / Share","Probability %","Score","RS Score"], ascending=False).reset_index(drop=True)

def empty_journal():
    return pd.DataFrame(columns=["Date","Ticker","Entry","Exit","Shares","P/L","Return %","Pattern","Mistake","Notes"])

def load_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            return pd.read_csv(JOURNAL_FILE)
        except Exception:
            return empty_journal()
    return empty_journal()

def save_journal(df):
    df.to_csv(JOURNAL_FILE, index=False)

def top_answer(scan, light, score, reason):
    best = scan.iloc[0]
    approved = best["Signal"] in ["BUY NOW","BUY ON BREAKOUT"] and best["Position $"] > 0
    st.header("TODAY'S ANSWER")
    if approved:
        st.success(f"FOCUS: {best['Ticker']} - {best['Signal']}")
    elif light == "RED":
        st.error(f"NO TRADE YET. Best watch: {best['Ticker']}")
    else:
        st.warning(f"WATCH ONLY. Best candidate: {best['Ticker']}")
    a,b,c,d,e = st.columns(5)
    a.metric("Ticker", best["Ticker"])
    b.metric("Signal", best["Signal"])
    c.metric("Probability", f"{best['Probability %']}%")
    d.metric("Grade", best["Grade"])
    e.metric("Market", f"{light} {score}/100")
    f,g,h,i = st.columns(4)
    f.metric("Entry", f"${best['Price']:.2f}")
    g.metric("Stop", f"${best['Stop']:.2f}")
    h.metric("Target 1", f"${best['Target 1']:.2f}")
    i.metric("Target 2", f"${best['Target 2']:.2f}")
    j,k,l,m = st.columns(4)
    j.metric("Shares", f"{best['Shares']:.4f}")
    k.metric("Position", f"${best['Position $']:,.2f}")
    l.metric("Risk", f"${best['Dollar Risk']:,.2f}")
    m.metric("EV / Share", f"${best['EV / Share']:.2f}")
    st.write(f"Reason: **{best['Pattern']}**, {best['Intraday Trend']}, OR zone **{best['OR Zone']}**, RS **{best['RS Score']}**, VWAP **{best['Above VWAP']}**")
    st.caption(reason)

def checklist(row, light):
    st.subheader("Checklist")
    checks = [
        ("Market not RED", light != "RED"),
        ("Above VWAP", bool(row["Above VWAP"])),
        ("Near/above OR breakout", row["OR Zone"] in ["Near breakout","Breakout"]),
        ("Probability >= 60%", row["Probability %"] >= 60),
        ("Reward/Risk >= 1.5", row["Reward/Risk"] >= 1.5),
        ("Expected value positive", row["EV / Share"] > 0),
        ("RS Score >= 60", row["RS Score"] >= 60),
        ("Not extended > 15% above 20MA", row["Dist 20MA %"] <= 15),
    ]
    passed = sum(1 for _, ok in checks if ok)
    st.write(f"Score: **{passed}/{len(checks)}**")
    for label, ok in checks:
        st.write(("YES - " if ok else "NO - ") + label)

def journal_tab():
    st.header("Trade Journal")
    j = load_journal()
    if not j.empty:
        j["P/L"] = pd.to_numeric(j["P/L"], errors="coerce").fillna(0)
        wins = j[j["P/L"] > 0]
        losses = j[j["P/L"] < 0]
        total = j["P/L"].sum()
        wr = len(wins) / len(j) * 100 if len(j) else 0
        pf = wins["P/L"].sum() / abs(losses["P/L"].sum()) if not losses.empty else np.inf
        a,b,c = st.columns(3)
        a.metric("Total P/L", f"${total:,.2f}")
        b.metric("Win Rate", f"{wr:.1f}%")
        c.metric("Profit Factor", "infinity" if pf == np.inf else f"{pf:.2f}")
        st.dataframe(j, use_container_width=True)
    else:
        st.info("No journal trades yet.")
    with st.form("journal_form", clear_on_submit=True):
        a,b,c,d = st.columns(4)
        dt = a.date_input("Date", value=date.today())
        ticker = b.text_input("Ticker")
        entry = c.number_input("Entry", min_value=0.0, step=0.01)
        exitp = d.number_input("Exit", min_value=0.0, step=0.01)
        e,f,g,h = st.columns(4)
        shares = e.number_input("Shares", min_value=0.0, step=0.0001, format="%.6f")
        pattern = f.selectbox("Pattern", ["Bullish ORB","OR Breakout Watch","VWAP Continuation","Daily Breakout","Other"])
        mistake = g.selectbox("Mistake", ["None","Chased","Ignored stop","Sold too early","No trigger","Oversized","Revenge trade"])
        notes = h.text_input("Notes")
        if st.form_submit_button("Save Trade"):
            if ticker.strip() and entry > 0 and exitp > 0 and shares > 0:
                pnl = (exitp - entry) * shares
                ret = ((exitp / entry) - 1) * 100
                row = {"Date":dt.isoformat(),"Ticker":ticker.strip().upper(),"Entry":round(entry,2),"Exit":round(exitp,2),"Shares":round(shares,6),"P/L":round(pnl,2),"Return %":round(ret,2),"Pattern":pattern,"Mistake":mistake,"Notes":notes}
                j = pd.concat([j, pd.DataFrame([row])], ignore_index=True)
                save_journal(j)
                st.success("Saved. Click Refresh.")
            else:
                st.error("Ticker, entry, exit, and shares are required.")

def csv_tab():
    st.header("Robinhood CSV Audit")
    uploaded = st.file_uploader("Upload Robinhood CSV", type=["csv"])
    if uploaded is None:
        return
    try:
        raw = pd.read_csv(uploaded, engine="python", on_bad_lines="skip")
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return
    raw.columns = [str(c).strip() for c in raw.columns]
    required = ["Instrument","Trans Code","Quantity","Amount"]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        st.error(f"Missing columns: {missing}")
        st.write(list(raw.columns))
        return
    df = raw.copy()
    df["Amount Clean"] = df["Amount"].apply(clean_money)
    df["Quantity Clean"] = df["Quantity"].apply(clean_qty)
    df["Instrument"] = df["Instrument"].astype(str).str.strip()
    df["Trans Code"] = df["Trans Code"].astype(str).str.strip()
    trades = df[df["Trans Code"].isin(["Buy","Sell"])]
    rows = []
    for ticker, group in trades.groupby("Instrument"):
        buys = group[group["Trans Code"] == "Buy"]
        sells = group[group["Trans Code"] == "Sell"]
        buy_cost = abs(buys["Amount Clean"].sum())
        proceeds = sells["Amount Clean"].sum()
        pnl = proceeds - buy_cost
        rows.append({"Ticker":ticker,"Buy Cost":round(buy_cost,2),"Sell Proceeds":round(proceeds,2),"P/L":round(pnl,2),"Return %":round((pnl/buy_cost*100),2) if buy_cost > 0 else None,"Rows":len(group)})
    out = pd.DataFrame(rows).sort_values("P/L", ascending=False)
    st.metric("Uploaded CSV Total P/L", f"${out['P/L'].sum():,.2f}" if not out.empty else "$0.00")
    st.dataframe(out, use_container_width=True)

def validator(light):
    st.header("Manual Trade Validator")
    a,b,c,d = st.columns(4)
    entry = b.number_input("Entry", min_value=0.0, step=0.01, key="v_entry")
    stop = c.number_input("Stop", min_value=0.0, step=0.01, key="v_stop")
    target = d.number_input("Target", min_value=0.0, step=0.01, key="v_target")
    ticker = a.text_input("Ticker", key="v_ticker")
    e,f,g = st.columns(3)
    shares = e.number_input("Shares", min_value=0.0, step=0.0001, format="%.6f", key="v_shares")
    above_vwap = f.checkbox("Above VWAP?")
    above_or = g.checkbox("Above OR High?")
    if st.button("Validate Trade"):
        fails = []
        if light == "RED": fails.append("Market is RED.")
        if entry <= 0 or stop <= 0 or target <= 0 or shares <= 0: fails.append("Missing entry/stop/target/shares.")
        elif stop >= entry: fails.append("Stop must be below entry.")
        elif target <= entry: fails.append("Target must be above entry.")
        else:
            rr = (target - entry)/(entry - stop)
            if rr < 1.5: fails.append(f"Reward/risk too low: {rr:.2f}")
        if not above_vwap: fails.append("Not above VWAP.")
        if not above_or: fails.append("Not above OR high.")
        if fails:
            st.error("NO TRADE")
            for x in fails: st.write("NO - " + x)
        else:
            st.success("TRADE ALLOWED BY RULES")
        if entry > 0 and stop > 0 and target > entry and shares > 0:
            st.metric("Dollar Risk", f"${(entry-stop)*shares:,.2f}")
            st.metric("Dollar Reward", f"${(target-entry)*shares:,.2f}")

def charts(scan):
    st.header("Charts")
    ticker = st.selectbox("Ticker", scan["Ticker"].tolist())
    tf = st.radio("Timeframe", ["5m","15m","Daily"], horizontal=True)
    df = get_data(ticker, "1d", "5m") if tf == "5m" else get_data(ticker, "5d", "15m") if tf == "15m" else get_data(ticker, "3mo", "1d")
    if df.empty:
        st.warning("Chart unavailable.")
        return
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=ticker))
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"].rolling(20).mean(), mode="lines", name="20MA"))
    if tf == "5m" and len(df) >= 3:
        fig.add_hline(y=df.head(3)["High"].max(), line_dash="dash", annotation_text="OR High")
        fig.add_hline(y=df.head(3)["Low"].min(), line_dash="dash", annotation_text="OR Low")
    fig.update_layout(height=550, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

st.title("Deon's Trader Dashboard v19.1")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.sidebar.header("Settings")
watchlist_text = st.sidebar.text_area("Manual Watchlist", ",".join(DEFAULT_WATCHLIST), height=90)
scan_text = st.sidebar.text_area("Scanner Universe", ",".join(DEFAULT_SCAN), height=170)
cash = st.sidebar.number_input("Cash available", min_value=0.0, value=855.0, step=25.0)
risk_input = st.sidebar.number_input("Risk per trade %", min_value=0.25, max_value=10.0, value=3.0, step=0.25)
risk_pct = risk_input / 100
st.sidebar.write("Max risk:", f"${cash*risk_pct:,.2f}")
if st.sidebar.button("Refresh now"):
    st.cache_data.clear()
    st.rerun()

mkt = market_context()
light, regime, mscore, reason = market_state(mkt)
st.header("Market")
st.dataframe(mkt, use_container_width=True)
if light == "GREEN": st.success(f"{light} - {regime}")
elif light == "YELLOW": st.warning(f"{light} - {regime}")
else: st.error(f"{light} - {regime}")
st.progress(mscore)

symbols = [x.strip().upper() for x in scan_text.split(",") if x.strip()]
with st.spinner("Scanning now..."):
    scan = run_scan(symbols, light, cash, risk_pct)
if scan.empty:
    st.error("No data loaded. Try fewer tickers, wait one minute, then refresh.")
    st.stop()

top_answer(scan, light, mscore, reason)

tabs = st.tabs(["Scanner","Trade Plan","No Trade List","Sector Strength","Validator","Journal","Robinhood CSV","Charts"])

with tabs[0]:
    st.header("Ranked Scanner")
    top = scan.head(15).copy()
    top.insert(0, "Rank", range(1, len(top)+1))
    st.dataframe(top[["Rank","Ticker","Sector","Signal","Pattern","Price","Probability %","Grade","Score","RS Score","EV / Share","Position $","Above VWAP","OR Zone","Rel Vol"]], use_container_width=True, height=520)
    st.subheader("Manual Watchlist")
    manual = [x.strip().upper() for x in watchlist_text.split(",") if x.strip()]
    st.dataframe(scan[scan["Ticker"].isin(manual)], use_container_width=True, height=320)

with tabs[1]:
    top_answer(scan, light, mscore, reason)
    checklist(scan.iloc[0], light)

with tabs[2]:
    st.header("No Trade List")
    avoid = scan[(scan["Signal"] == "AVOID") | (scan["EV / Share"] <= 0) | (scan["Above VWAP"] == False) | (scan["RS Score"] < 40)]
    st.dataframe(avoid[["Ticker","Signal","Price","EV / Share","Above VWAP","RS Score","Intraday Trend","OR Zone"]], use_container_width=True, height=450)

with tabs[3]:
    st.header("Sector Strength")
    sec = scan.groupby("Sector").agg(Names=("Ticker","count"), Avg_RS=("RS Score","mean"), Avg_Score=("Score","mean"), Positive_EV=("EV / Share", lambda x: (x > 0).sum())).reset_index()
    sec["Avg_RS"] = sec["Avg_RS"].round(1)
    sec["Avg_Score"] = sec["Avg_Score"].round(1)
    st.dataframe(sec.sort_values(["Avg_RS","Avg_Score"], ascending=False), use_container_width=True)

with tabs[4]:
    validator(light)

with tabs[5]:
    journal_tab()

with tabs[6]:
    csv_tab()

with tabs[7]:
    charts(scan)

st.caption("Decision support only. Built to give one clear answer fast: trade, watch, or stay cash.")
