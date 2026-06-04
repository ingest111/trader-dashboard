
import json
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Deon's Trader Dashboard v23", layout="wide")

MARKETS = ["SPY", "QQQ", "^VIX", "^TNX"]
DEFAULT_SCAN = [
    "NVDA","AMD","AVGO","ARM","MU","TSM","MRVL","CRDO",
    "PLTR","APP","HOOD","HIMS","SOFI","RDDT",
    "META","AMZN","MSFT","GOOGL","TSLA","COIN",
    "SMCI","DELL","ORCL","CEG","VRT","ANET"
]
DEFAULT_WATCHLIST = ["NVDA","AMD","AVGO","MU","TSM","PLTR","CRDO","META","RDDT","HIMS"]

SECTOR = {
    "NVDA":"Semis","AMD":"Semis","AVGO":"Semis","ARM":"Semis","MU":"Semis","TSM":"Semis","MRVL":"Semis","CRDO":"Semis",
    "SMCI":"AI Infra","DELL":"AI Infra","VRT":"AI Infra","ANET":"AI Infra",
    "PLTR":"AI Software","APP":"Software","MSFT":"Mega Cap","GOOGL":"Mega Cap","META":"Mega Cap","AMZN":"Mega Cap",
    "HOOD":"Fintech","SOFI":"Fintech","COIN":"Crypto","MSTR":"Crypto","HIMS":"Momentum","RDDT":"Momentum",
    "TSLA":"High Beta","ORCL":"Software","CEG":"Energy"
}

@st.cache_data(ttl=60)
def get_data(ticker, period="3mo", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        needed = ["Open","High","Low","Close","Volume"]
        if any(c not in df.columns for c in needed):
            return pd.DataFrame()
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def n(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def pct(df, bars):
    if df.empty or len(df) <= bars:
        return 0.0
    a = n(df["Close"].iloc[-bars])
    b = n(df["Close"].iloc[-1])
    return round(((b / a) - 1) * 100, 2) if a > 0 else 0.0

def market_context():
    rows = []
    for t in MARKETS:
        df = get_data(t, "1mo", "1d")
        if df.empty:
            continue
        close = n(df["Close"].iloc[-1])
        ma10 = n(df["Close"].rolling(10).mean().iloc[-1], close)
        rows.append({
            "Market": t,
            "Price": round(close, 2),
            "1D %": pct(df, 2),
            "5D %": pct(df, 6),
            "Trend": "Above 10MA" if close >= ma10 else "Below 10MA",
        })
    return pd.DataFrame(rows)

def market_state(mdf):
    if mdf.empty:
        return "RED", "Defensive", 0, "Market data unavailable"
    def val(sym, col):
        arr = mdf.loc[mdf["Market"] == sym, col].values
        return n(arr[0]) if len(arr) else 0.0
    spy1, qqq1, spy5, qqq5, vix1 = val("SPY","1D %"), val("QQQ","1D %"), val("SPY","5D %"), val("QQQ","5D %"), val("^VIX","1D %")
    score = 50
    score += 12 if spy1 >= 0 else (-5 if spy1 > -0.75 else -15)
    score += 12 if qqq1 >= 0 else (-5 if qqq1 > -0.75 else -15)
    score += 8 if spy5 >= 0 else -8
    score += 8 if qqq5 >= 0 else -8
    score += 10 if vix1 <= 0 else (-5 if vix1 < 3 else -15)
    score = int(max(0, min(100, score)))
    if score >= 65:
        return "GREEN", "Bullish", score, "Risk-on backdrop"
    if score >= 35:
        return "YELLOW", "Mixed", score, "Trade selectively; money flow matters more than index direction"
    return "RED", "Defensive", score, "Weak tape; only strongest money-flow names qualify"

def intraday(ticker):
    df = get_data(ticker, "1d", "5m")
    if df.empty or len(df) < 3:
        return {"Above VWAP": False, "OR Zone": "Unknown", "OR Status": "Unknown", "Intraday Trend": "Unknown", "OR High": np.nan, "OR Low": np.nan, "VWAP": np.nan}
    current = n(df["Close"].iloc[-1])
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    volume = n(df["Volume"].sum())
    vwap = n((typical * df["Volume"]).sum() / volume, current) if volume > 0 else current
    opening = df.head(3)
    high, low = n(opening["High"].max()), n(opening["Low"].min())
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
    return {"Above VWAP": bool(above), "OR Zone": zone, "OR Status": status, "Intraday Trend": trend, "OR High": round(high,2), "OR Low": round(low,2), "VWAP": round(vwap,2)}

def rs_score(stock, spy):
    if stock.empty or spy.empty:
        return 50
    raw = ((pct(stock,6) - pct(spy,6)) * 2) + (pct(stock,22) - pct(spy,22))
    return int(max(0, min(100, round(50 + raw))))

def gap_pct(df):
    if df.empty or len(df) < 2:
        return 0.0
    prev = n(df["Close"].iloc[-2])
    opn = n(df["Open"].iloc[-1])
    return round(((opn / prev) - 1) * 100, 2) if prev > 0 else 0.0

def tier(score):
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "No Trade"

def risk_mult(t):
    return {"A+":1.0, "A":0.75, "B":0.5}.get(t, 0.0)

def setup_scores(intra, above20, above50, dist20, rel_vol, rs, gp, one_day, five_day, one_month, close, high20, near_high, breakout, light):
    red_penalty = -5 if light == "RED" else 0
    green_bonus = 5 if light == "GREEN" else 0

    orb = 0
    orb += {"Breakout":35,"Near breakout":28,"Upper range":18}.get(intra["OR Zone"],0)
    orb += 30 if intra["Intraday Trend"] == "Bullish ORB" else 15 if intra["Intraday Trend"] == "Constructive" else 0
    orb += 15 if intra["Above VWAP"] else 0
    orb += 10 if rel_vol >= 1.5 else 5 if rel_vol >= 1.0 else 0
    orb += 8 if rs >= 70 else 4 if rs >= 60 else 0
    orb += 3 if above20 else 0
    orb += 3 if above50 else 0
    orb += green_bonus + red_penalty
    orb -= 35 if intra["OR Status"] == "Below OR Low" else 0

    vwap = 0
    vwap += 35 if intra["Above VWAP"] else 0
    vwap += 20 if intra["Intraday Trend"] in ["Constructive","Bullish ORB"] else 8 if intra["Intraday Trend"] == "Choppy" else 0
    vwap += 12 if above20 else 0
    vwap += 12 if above50 else 0
    vwap += 12 if -2 <= dist20 <= 10 else -12 if dist20 > 15 else 0
    vwap += 8 if rs >= 70 else 5 if rs >= 60 else 0
    vwap += 5 if rel_vol >= 1.0 else 0
    vwap += red_penalty

    gap = 0
    gap += 30 if gp >= 3 else 24 if gp >= 2 else 15 if gp >= 1 else -25 if gp <= -2 else 0
    gap += 25 if intra["Above VWAP"] else 0
    gap += 20 if intra["OR Zone"] in ["Breakout","Near breakout","Upper range"] else 0
    gap += 15 if rel_vol >= 1.5 else 8 if rel_vol >= 1.0 else 0
    gap += 10 if rs >= 70 else 5 if rs >= 60 else 0
    gap += red_penalty

    mom = 0
    mom += 30 if rs >= 80 else 24 if rs >= 70 else 15 if rs >= 60 else 0
    mom += 18 if five_day > 5 else 12 if five_day > 3 else 5 if five_day > 0 else 0
    mom += 18 if one_month > 12 else 12 if one_month > 8 else 5 if one_month > 0 else 0
    mom += 10 if above20 else 0
    mom += 10 if above50 else 0
    mom += 8 if rel_vol >= 1.25 else 0
    mom -= 10 if one_day > 8 else 0
    mom -= 15 if dist20 > 18 else 8 if dist20 > 12 else 0
    mom += green_bonus + red_penalty

    daily = 0
    daily += 35 if breakout else 25 if near_high else 0
    daily += 12 if above20 else 0
    daily += 12 if above50 else 0
    daily += 12 if rs >= 70 else 7 if rs >= 60 else 0
    daily += 12 if rel_vol >= 1.5 else 6 if rel_vol >= 1.0 else 0
    daily += green_bonus + red_penalty

    scores = {"ORB":orb, "VWAP":vwap, "Gap":gap, "Momentum":mom, "Daily":daily}
    return {k:int(max(0,min(100,v))) for k,v in scores.items()}

def analyze(ticker, spy, light, cash, risk_pct):
    df = get_data(ticker, "3mo", "1d")
    if df.empty or len(df) < 30:
        return None
    close = n(df["Close"].iloc[-1])
    ma20 = n(df["Close"].rolling(20).mean().iloc[-1], close)
    ma50 = n(df["Close"].rolling(50).mean().iloc[-1], close)
    high20 = n(df["High"].rolling(20).max().iloc[-2], close)
    low10 = n(df["Low"].rolling(10).min().iloc[-1], close * 0.95)
    one_day, five_day, one_month = pct(df,2), pct(df,6), pct(df,22)
    avg_vol = n(df["Volume"].rolling(20).mean().iloc[-1])
    rel_vol = n(df["Volume"].iloc[-1]) / avg_vol if avg_vol > 0 else 0
    above20, above50 = close >= ma20, close >= ma50
    dist20 = ((close / ma20) - 1) * 100 if ma20 > 0 else 0
    breakout = close > high20
    near_high = abs((close / high20) - 1) * 100 <= 3 if high20 > 0 else False
    intra = intraday(ticker)
    rs = rs_score(df, spy)
    gp = gap_pct(df)
    scores = setup_scores(intra, above20, above50, dist20, rel_vol, rs, gp, one_day, five_day, one_month, close, high20, near_high, breakout, light)
    best_setup, best_score = sorted(scores.items(), key=lambda x: x[1], reverse=True)[0]
    t = tier(best_score)
    mult = risk_mult(t)
    pattern = {"ORB":"Opening Range Breakout","VWAP":"VWAP Reclaim / Hold","Gap":"Gap-and-Go","Momentum":"Relative Strength Continuation","Daily":"Daily Breakout"}.get(best_setup, "No Clear Pattern")
    stop = round(max(low10, close * 0.94), 2)
    risk_share = max(0, close - stop)
    target1 = round(close + risk_share * 1.25, 2) if risk_share > 0 else round(close * 1.04, 2)
    target2 = round(close + risk_share * 2.0, 2) if risk_share > 0 else round(close * 1.08, 2)
    rr = (target2 - close) / risk_share if risk_share > 0 else 0
    prob = int(max(0, min(95, round(35 + best_score * .55))))
    ev = ((prob/100) * (target1-close)) - ((1-prob/100) * risk_share) if risk_share > 0 else 0

    valid = t in ["A+","A","B"] and ev >= -0.10 and risk_share > 0 and rr >= 1.20 and intra["OR Status"] != "Below OR Low"
    if light == "RED" and t == "B" and rs < 60:
        valid = False

    signal = "TRADE" if valid and t in ["A+","A"] else "SMALL TRADE" if valid and t == "B" else "WATCH" if t == "C" else "NO TRADE"
    shares = min((cash*risk_pct*mult)/risk_share, cash/close) if valid and risk_share > 0 and close > 0 else 0
    money_flow = int(max(0, min(100, round((best_score*.35)+(rs*.25)+(min(rel_vol,3)/3*20)+(max(min(gp,5),-5)+5)+(10 if intra["Above VWAP"] else 0)))))
    reason_parts = []
    if intra["Above VWAP"]: reason_parts.append("Above VWAP")
    if intra["OR Zone"] in ["Breakout","Near breakout","Upper range"]: reason_parts.append(intra["OR Zone"])
    if rs >= 70: reason_parts.append("Strong RS")
    elif rs >= 60: reason_parts.append("Acceptable RS")
    if rel_vol >= 1.5: reason_parts.append("High relative volume")
    elif rel_vol >= 1.0: reason_parts.append("Volume active")
    if gp >= 2: reason_parts.append("Positive gap")
    if best_score >= 80: reason_parts.append(f"{best_setup} engine strong")
    reason = " + ".join(reason_parts) if reason_parts else "No dominant money-flow edge"
    return {
        "Ticker":ticker, "Sector":SECTOR.get(ticker,"Other"), "Signal":signal, "Best Setup":best_setup,
        "Pattern":pattern, "Tier":t, "Best Score":best_score, "Money Flow Score":money_flow, "Reason":reason,
        "ORB Score":scores["ORB"], "VWAP Score":scores["VWAP"], "Gap Score":scores["Gap"], "Momentum Score":scores["Momentum"], "Daily Score":scores["Daily"],
        "Price":round(close,2), "Probability %":prob, "RS Score":rs, "Gap %":gp, "1D %":one_day, "5D %":five_day, "1M %":one_month,
        "Rel Vol":round(rel_vol,2), "Above VWAP":intra["Above VWAP"], "VWAP":intra["VWAP"], "Intraday Trend":intra["Intraday Trend"],
        "OR Status":intra["OR Status"], "OR Zone":intra["OR Zone"], "OR High":intra["OR High"], "OR Low":intra["OR Low"], "Dist 20MA %":round(dist20,2),
        "Stop":stop, "Target 1":target1, "Target 2":target2, "Reward/Risk":round(rr,2), "EV / Share":round(ev,2),
        "Risk Multiplier":mult, "Shares":round(shares,4), "Position $":round(shares*close,2), "Dollar Risk":round(shares*risk_share,2)
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
    return pd.DataFrame(rows).sort_values(["Money Flow Score","Best Score","RS Score","EV / Share"], ascending=False).reset_index(drop=True)

def sector_flow_df(scan):
    sec = scan.groupby("Sector").agg(
        Names=("Ticker","count"),
        Tradeable=("Signal", lambda x: x.isin(["TRADE","SMALL TRADE"]).sum()),
        Avg_Flow=("Money Flow Score","mean"),
        Avg_Setup=("Best Score","mean"),
        Avg_RS=("RS Score","mean"),
        Avg_EV=("EV / Share","mean")
    ).reset_index()
    for c in ["Avg_Flow","Avg_Setup","Avg_RS","Avg_EV"]:
        sec[c] = sec[c].round(2)
    return sec.sort_values(["Tradeable","Avg_Flow","Avg_RS"], ascending=False)

def records(df):
    if df is None or df.empty:
        return []
    return df.replace([np.inf,-np.inf], np.nan).where(pd.notnull(df), None).to_dict(orient="records")

def make_snapshot(scan, mkt, light, regime, score, reason):
    tradeable = scan[scan["Signal"].isin(["TRADE","SMALL TRADE"])]
    no_trade = scan[~scan["Signal"].isin(["TRADE","SMALL TRADE"])]
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market": {"light":light, "regime":regime, "score":int(score), "reason":reason, "context":records(mkt)},
        "top_flow_name": scan.iloc[0].to_dict(),
        "top_tradeable_name": tradeable.iloc[0].to_dict() if not tradeable.empty else None,
        "tradeable_count": int(len(tradeable)),
        "scanned_count": int(len(scan)),
        "top_3": records(scan.head(3)),
        "top_10": records(scan.head(10)),
        "sector_flow": records(sector_flow_df(scan)),
        "no_trade_watch": records(no_trade.head(10))
    }

def decision_packet(snapshot):
    m = snapshot["market"]
    tt = snapshot["top_tradeable_name"]
    tf = snapshot["top_flow_name"]
    lines = [
        "DEON TRADER DASHBOARD v23 - DECISION PACKET",
        f"Timestamp: {snapshot['timestamp']}",
        "",
        "MARKET",
        f"Status: {m['light']} {m['score']}/100 - {m['regime']}",
        f"Reason: {m['reason']}",
    ]
    for r in m["context"]:
        lines.append(f"- {r['Market']}: price {r['Price']}, 1D {r['1D %']}%, 5D {r['5D %']}%, {r['Trend']}")
    lines += ["", "SUMMARY", f"Scanned names: {snapshot['scanned_count']}", f"Tradeable names: {snapshot['tradeable_count']}"]
    if tt:
        lines += [
            "", "TOP APPROVED TRADE",
            f"Ticker: {tt['Ticker']}", f"Signal: {tt['Signal']}", f"Tier: {tt['Tier']}",
            f"Setup: {tt['Best Setup']} / {tt['Pattern']}", f"Money Flow Score: {tt['Money Flow Score']}",
            f"Best Setup Score: {tt['Best Score']}", f"Probability: {tt['Probability %']}%",
            f"Price: {tt['Price']}", f"Stop: {tt['Stop']}", f"Target 1: {tt['Target 1']}", f"Target 2: {tt['Target 2']}",
            f"Shares: {tt['Shares']}", f"Position $: {tt['Position $']}", f"Dollar Risk: {tt['Dollar Risk']}",
            f"EV / Share: {tt['EV / Share']}", f"Reward/Risk: {tt['Reward/Risk']}",
            f"VWAP: {tt['Above VWAP']} at {tt['VWAP']}", f"OR Status: {tt['OR Status']} / {tt['OR Zone']}",
            f"RS Score: {tt['RS Score']}", f"Rel Vol: {tt['Rel Vol']}", f"Reason: {tt['Reason']}"
        ]
    else:
        lines += ["", "TOP APPROVED TRADE", "None.", "", "STRONGEST FLOW NAME",
                  f"Ticker: {tf['Ticker']}", f"Signal: {tf['Signal']}", f"Tier: {tf['Tier']}", f"Setup: {tf['Best Setup']} / {tf['Pattern']}",
                  f"Money Flow Score: {tf['Money Flow Score']}", f"Reason: {tf['Reason']}"]
    lines += ["", "TOP 3 MONEY FLOW"]
    for i, r in enumerate(snapshot["top_3"], 1):
        lines.append(f"{i}. {r['Ticker']} | {r['Sector']} | {r['Signal']} | {r['Tier']} | {r['Best Setup']} | Flow {r['Money Flow Score']} | Score {r['Best Score']} | Price {r['Price']} | Stop {r['Stop']} | T1 {r['Target 1']} | Shares {r['Shares']} | Position ${r['Position $']} | Risk ${r['Dollar Risk']} | Reason: {r['Reason']}")
    lines += ["", "TOP 10 RANKED"]
    for i, r in enumerate(snapshot["top_10"], 1):
        lines.append(f"{i}. {r['Ticker']} | {r['Signal']} | {r['Tier']} | {r['Best Setup']} | Flow {r['Money Flow Score']} | RS {r['RS Score']} | EV {r['EV / Share']} | VWAP {r['Above VWAP']} | OR {r['OR Zone']}")
    lines += ["", "SECTOR FLOW"]
    for i, r in enumerate(snapshot["sector_flow"][:8], 1):
        lines.append(f"{i}. {r['Sector']} | Tradeable {r['Tradeable']} | Avg Flow {r['Avg_Flow']} | Avg Setup {r['Avg_Setup']} | Avg RS {r['Avg_RS']} | Avg EV {r['Avg_EV']}")
    lines += ["", "ASK CHATGPT", "Using this packet, tell me whether to trade now, wait, or avoid. If trade, verify entry/stop/position/risk. Be strict but practical."]
    return "\n".join(lines)

def download_csv(df):
    return df.to_csv(index=False).encode("utf-8")

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

# APP
st.title("Deon's Trader Dashboard v23")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.sidebar.header("Settings")
watchlist_text = st.sidebar.text_area("Manual Watchlist", ",".join(DEFAULT_WATCHLIST), height=90)
scan_text = st.sidebar.text_area("Scanner Universe", ",".join(DEFAULT_SCAN), height=170)
cash = st.sidebar.number_input("Cash available", min_value=0.0, value=855.0, step=25.0)
risk_pct = st.sidebar.number_input("Base risk per trade %", min_value=0.25, max_value=10.0, value=3.0, step=0.25) / 100
st.sidebar.write("A+ max risk:", f"${cash*risk_pct:,.2f}")
st.sidebar.write("A max risk:", f"${cash*risk_pct*.75:,.2f}")
st.sidebar.write("B max risk:", f"${cash*risk_pct*.5:,.2f}")
if st.sidebar.button("Refresh now"):
    st.cache_data.clear()
    st.rerun()

mkt = market_context()
light, regime, mscore, reason = market_state(mkt)
symbols = [x.strip().upper() for x in scan_text.split(",") if x.strip()]
with st.spinner("Scanning money flow..."):
    scan = run_scan(symbols, light, cash, risk_pct)
if scan.empty:
    st.error("No data loaded. Try fewer tickers, wait one minute, then refresh.")
    st.stop()
snapshot = make_snapshot(scan, mkt, light, regime, mscore, reason)
packet = decision_packet(snapshot)

st.header("Copy This for ChatGPT")
st.info("Click in the box, press Ctrl+A, then Ctrl+C. Paste it into ChatGPT. This replaces screenshots.")
st.text_area("Decision Packet", packet, height=520)
c1, c2, c3 = st.columns(3)
c1.download_button("Download Decision Packet TXT", data=packet.encode("utf-8"), file_name="dashboard_decision_packet.txt", mime="text/plain")
c2.download_button("Download Snapshot JSON", data=json.dumps(snapshot, indent=2, default=str).encode("utf-8"), file_name="dashboard_snapshot.json", mime="application/json")
c3.download_button("Download Top 10 CSV", data=download_csv(pd.DataFrame(snapshot["top_10"])), file_name="dashboard_top10.csv", mime="text/csv")

st.header("Market")
st.dataframe(mkt, use_container_width=True)
if light == "GREEN":
    st.success(f"{light} - {regime}")
elif light == "YELLOW":
    st.warning(f"{light} - {regime}")
else:
    st.error(f"{light} - {regime}")
st.progress(mscore)

st.header("Money Flow Dashboard")
tradeable = scan[scan["Signal"].isin(["TRADE","SMALL TRADE"])]
top_flow = scan.iloc[0]
top_trade = tradeable.iloc[0] if not tradeable.empty else None
if top_trade is not None:
    st.success(f"TODAY'S FOCUS: {top_trade['Ticker']} - {top_trade['Tier']} {top_trade['Best Setup']} - {top_trade['Signal']}")
else:
    st.error(f"NO APPROVED TRADE YET. Strongest flow: {top_flow['Ticker']}")
a,b,c,d = st.columns(4)
a.metric("Market", f"{light} {mscore}/100")
b.metric("Tradeable Names", len(tradeable))
c.metric("Strongest Flow", top_flow["Ticker"])
d.metric("Top Flow Score", top_flow["Money Flow Score"])
st.dataframe(scan.head(3)[["Ticker","Sector","Signal","Tier","Best Setup","Money Flow Score","Best Score","Reason","Price","Stop","Target 1","Shares","Position $","Dollar Risk"]], use_container_width=True)

tabs = st.tabs(["Money Flow Board","Trade Plan","Sector Flow","Engine Scores","No Trade / Watch","Participation","Charts"])
with tabs[0]:
    top = scan.head(25).copy()
    top.insert(0, "Rank", range(1, len(top)+1))
    st.dataframe(top[["Rank","Ticker","Sector","Signal","Tier","Best Setup","Money Flow Score","Best Score","Reason","Price","Probability %","EV / Share","Position $","Dollar Risk","Above VWAP","OR Zone","RS Score"]], use_container_width=True, height=600)
    manual = [x.strip().upper() for x in watchlist_text.split(",") if x.strip()]
    st.subheader("Manual Watchlist")
    st.dataframe(scan[scan["Ticker"].isin(manual)], use_container_width=True, height=300)
with tabs[1]:
    selected = st.selectbox("Select opportunity", scan["Ticker"].tolist())
    row = scan[scan["Ticker"] == selected].iloc[0]
    st.metric("Signal", row["Signal"])
    st.metric("Tier / Setup", f"{row['Tier']} {row['Best Setup']}")
    st.write(row["Reason"])
    st.dataframe(pd.DataFrame([row]), use_container_width=True)
with tabs[2]:
    sec = sector_flow_df(scan)
    st.dataframe(sec, use_container_width=True)
    if not sec.empty:
        leader = sec.iloc[0]["Sector"]
        st.subheader(f"Leaders in strongest sector: {leader}")
        st.dataframe(scan[scan["Sector"] == leader].head(5), use_container_width=True)
with tabs[3]:
    st.dataframe(scan[["Ticker","Sector","Signal","Tier","Best Setup","Money Flow Score","Best Score","ORB Score","VWAP Score","Gap Score","Momentum Score","Daily Score","RS Score","EV / Share"]], use_container_width=True, height=560)
with tabs[4]:
    nt = scan[~scan["Signal"].isin(["TRADE","SMALL TRADE"])]
    st.dataframe(nt[["Ticker","Signal","Tier","Best Setup","Money Flow Score","Best Score","Reason","Price","EV / Share","Reward/Risk","Above VWAP","OR Status","OR Zone","RS Score"]], use_container_width=True, height=500)
with tabs[5]:
    part = len(tradeable)/len(scan)*100 if len(scan) else 0
    x,y,z = st.columns(3)
    x.metric("Tradeable %", f"{part:.1f}%")
    y.metric("Tradeable Names", len(tradeable))
    z.metric("Scanned Names", len(scan))
with tabs[6]:
    charts(scan)

st.caption("v23 removes the GitHub/Streamlit Secrets problem and puts the full ChatGPT decision packet at the top.")
