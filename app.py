
import os
from datetime import datetime, date
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ============================================================
# DEON'S TRADER DASHBOARD v19.2
# Opportunity Expansion Engine
#
# Goal:
# - Reduce no-trade days by scoring multiple setup types
# - Keep risk controlled through A+/A/B/C tier sizing
# - Produce 3 best opportunities, not just 1 all-or-nothing answer
# ============================================================

st.set_page_config(page_title="Deon's Trader Dashboard v19.2", layout="wide")

MARKETS = ["SPY", "QQQ", "^VIX", "^TNX"]

DEFAULT_SCAN = [
    "NVDA", "AMD", "AVGO", "ARM", "MU", "TSM", "MRVL", "CRDO",
    "PLTR", "APP", "HOOD", "HIMS", "SOFI", "RDDT",
    "META", "AMZN", "MSFT", "GOOGL", "TSLA", "COIN",
    "SMCI", "DELL", "ORCL", "CEG", "VRT", "ANET",
]

DEFAULT_WATCHLIST = ["NVDA", "AMD", "AVGO", "MU", "TSM", "PLTR", "CRDO", "META"]

SECTOR = {
    "NVDA": "Semis", "AMD": "Semis", "AVGO": "Semis", "ARM": "Semis",
    "MU": "Semis", "TSM": "Semis", "MRVL": "Semis", "CRDO": "Semis",
    "SMCI": "AI Infra", "DELL": "AI Infra", "VRT": "AI Infra", "ANET": "AI Infra",
    "PLTR": "AI Software", "APP": "Software", "MSFT": "Mega Cap", "GOOGL": "Mega Cap",
    "META": "Mega Cap", "AMZN": "Mega Cap", "HOOD": "Fintech", "SOFI": "Fintech",
    "COIN": "Crypto", "MSTR": "Crypto", "HIMS": "Momentum", "RDDT": "Momentum",
    "TSLA": "High Beta", "ORCL": "Software", "CEG": "Energy",
}

JOURNAL_FILE = "trade_journal_v19_2.csv"


# ============================================================
# DATA HELPERS
# ============================================================

@st.cache_data(ttl=60)
def get_data(ticker, period="3mo", interval="1d"):
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )

        if df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in df.columns:
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

    first = num(df["Close"].iloc[-bars])
    last = num(df["Close"].iloc[-1])

    if first <= 0:
        return 0.0

    return round(((last / first) - 1) * 100, 2)


def clean_money(x):
    if pd.isna(x):
        return 0.0

    s = str(x).replace("$", "").replace(",", "").strip()
    neg = "(" in s and ")" in s
    s = s.replace("(", "").replace(")", "")

    try:
        val = float(s)
        return -val if neg else val
    except Exception:
        return 0.0


def clean_qty(x):
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return 0.0


# ============================================================
# MARKET ENGINE
# ============================================================

def market_context():
    rows = []

    for ticker in MARKETS:
        df = get_data(ticker, "1mo", "1d")

        if df.empty:
            continue

        close = num(df["Close"].iloc[-1])
        ma10 = num(df["Close"].rolling(10).mean().iloc[-1], close)

        rows.append({
            "Market": ticker,
            "Price": round(close, 2),
            "1D %": pct(df, 2),
            "5D %": pct(df, 6),
            "Trend": "Above 10MA" if close >= ma10 else "Below 10MA",
        })

    return pd.DataFrame(rows)


def market_state(mdf):
    if mdf.empty:
        return "RED", "Defensive", 0, "Market data unavailable"

    def v(sym, col):
        arr = mdf.loc[mdf["Market"] == sym, col].values
        return num(arr[0]) if len(arr) else 0.0

    score = 50
    score += 15 if v("SPY", "1D %") >= 0 else -15
    score += 15 if v("QQQ", "1D %") >= 0 else -15
    score += 10 if v("SPY", "5D %") >= 0 else -10
    score += 10 if v("QQQ", "5D %") >= 0 else -10
    score += 10 if v("^VIX", "1D %") <= 0 else -20

    score = int(max(0, min(100, score)))

    if score >= 70:
        return "GREEN", "Bullish", score, "Indexes constructive and volatility calm"
    if score >= 45:
        return "YELLOW", "Mixed", score, "Mixed tape; be selective"

    return "RED", "Defensive", score, "Weak indexes or elevated volatility"


# ============================================================
# TECHNICAL CONTEXT
# ============================================================

def intraday(ticker):
    df = get_data(ticker, "1d", "5m")

    if df.empty or len(df) < 3:
        return {
            "Above VWAP": False,
            "OR Zone": "Unknown",
            "OR Status": "Unknown",
            "Intraday Trend": "Unknown",
            "OR High": np.nan,
            "OR Low": np.nan,
            "VWAP": np.nan,
        }

    current = num(df["Close"].iloc[-1])

    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    volume = num(df["Volume"].sum())

    if volume > 0:
        vwap = num((typical * df["Volume"]).sum() / volume, current)
    else:
        vwap = current

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
    elif pos >= 0.80:
        zone = "Near breakout"
    elif pos >= 0.60:
        zone = "Upper range"
    elif pos >= 0.20:
        zone = "Middle"
    elif pos >= 0:
        zone = "Near breakdown"
    else:
        zone = "Breakdown"

    above = current >= vwap

    if above and status == "Above OR High":
        trend = "Bullish ORB"
    elif above and zone in ["Near breakout", "Upper range"]:
        trend = "Constructive"
    elif (not above) and status == "Below OR Low":
        trend = "Bearish ORB"
    elif zone in ["Near breakdown", "Breakdown"]:
        trend = "Weak"
    else:
        trend = "Choppy"

    return {
        "Above VWAP": bool(above),
        "OR Zone": zone,
        "OR Status": status,
        "Intraday Trend": trend,
        "OR High": round(high, 2),
        "OR Low": round(low, 2),
        "VWAP": round(vwap, 2),
    }


def rs_score(stock_df, spy_df):
    if stock_df.empty or spy_df.empty:
        return 50

    raw = ((pct(stock_df, 6) - pct(spy_df, 6)) * 2) + (pct(stock_df, 22) - pct(spy_df, 22))
    return int(max(0, min(100, round(50 + raw))))


def gap_pct(df):
    if df.empty or len(df) < 2:
        return 0.0

    prev = num(df["Close"].iloc[-2])
    opn = num(df["Open"].iloc[-1])

    if prev <= 0:
        return 0.0

    return round(((opn / prev) - 1) * 100, 2)


# ============================================================
# OPPORTUNITY ENGINES
# ============================================================

def score_orb(intra, above20, above50, rel_vol, rs, market_light):
    score = 0

    if intra["OR Zone"] == "Breakout":
        score += 35
    elif intra["OR Zone"] == "Near breakout":
        score += 28
    elif intra["OR Zone"] == "Upper range":
        score += 18

    if intra["Intraday Trend"] == "Bullish ORB":
        score += 30
    elif intra["Intraday Trend"] == "Constructive":
        score += 15

    if intra["Above VWAP"]:
        score += 15

    if rel_vol >= 1.5:
        score += 10
    elif rel_vol >= 1.0:
        score += 5

    if rs >= 70:
        score += 8
    elif rs >= 60:
        score += 4

    if above20:
        score += 3
    if above50:
        score += 3

    if market_light == "GREEN":
        score += 5
    elif market_light == "RED":
        score -= 10

    if intra["OR Status"] == "Below OR Low":
        score -= 35

    return int(max(0, min(100, score)))


def score_vwap(intra, above20, above50, dist20, rs, rel_vol, market_light):
    score = 0

    if intra["Above VWAP"]:
        score += 35

    if intra["Intraday Trend"] in ["Constructive", "Bullish ORB"]:
        score += 20
    elif intra["Intraday Trend"] == "Choppy":
        score += 8

    if above20:
        score += 12
    if above50:
        score += 12

    if -2 <= dist20 <= 10:
        score += 12
    elif dist20 > 15:
        score -= 12

    if rs >= 70:
        score += 8
    elif rs >= 60:
        score += 5

    if rel_vol >= 1.0:
        score += 5

    if market_light == "RED":
        score -= 8

    return int(max(0, min(100, score)))


def score_gap(gap, intra, rel_vol, rs, market_light):
    score = 0

    if gap >= 3:
        score += 30
    elif gap >= 2:
        score += 24
    elif gap >= 1:
        score += 15
    elif gap <= -2:
        score -= 25

    if intra["Above VWAP"]:
        score += 25

    if intra["OR Zone"] in ["Breakout", "Near breakout", "Upper range"]:
        score += 20

    if rel_vol >= 1.5:
        score += 15
    elif rel_vol >= 1.0:
        score += 8

    if rs >= 70:
        score += 10
    elif rs >= 60:
        score += 5

    if market_light == "RED":
        score -= 10

    return int(max(0, min(100, score)))


def score_momentum(one_day, five_day, one_month, rs, above20, above50, rel_vol, dist20, market_light):
    score = 0

    if rs >= 80:
        score += 30
    elif rs >= 70:
        score += 24
    elif rs >= 60:
        score += 15

    if five_day > 5:
        score += 18
    elif five_day > 3:
        score += 12
    elif five_day > 0:
        score += 5

    if one_month > 12:
        score += 18
    elif one_month > 8:
        score += 12
    elif one_month > 0:
        score += 5

    if above20:
        score += 10
    if above50:
        score += 10

    if rel_vol >= 1.25:
        score += 8

    if one_day > 8:
        score -= 10

    if dist20 > 18:
        score -= 15
    elif dist20 > 12:
        score -= 8

    if market_light == "GREEN":
        score += 5
    elif market_light == "RED":
        score -= 8

    return int(max(0, min(100, score)))


def score_daily_breakout(close, high20, near_high, breakout, above20, above50, rs, rel_vol, market_light):
    score = 0

    if breakout:
        score += 35
    elif near_high:
        score += 25

    if above20:
        score += 12
    if above50:
        score += 12

    if rs >= 70:
        score += 12
    elif rs >= 60:
        score += 7

    if rel_vol >= 1.5:
        score += 12
    elif rel_vol >= 1.0:
        score += 6

    if market_light == "GREEN":
        score += 5
    elif market_light == "RED":
        score -= 8

    return int(max(0, min(100, score)))


def tier_from_score(score):
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "No Trade"


def risk_multiplier(tier):
    if tier == "A+":
        return 1.00
    if tier == "A":
        return 0.75
    if tier == "B":
        return 0.50
    return 0.00


def best_setup_from_engines(scores):
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ordered[0][0], ordered[0][1]


# ============================================================
# ANALYSIS
# ============================================================

def analyze(ticker, spy, market_light, cash, risk_pct):
    df = get_data(ticker, "3mo", "1d")

    if df.empty or len(df) < 30:
        return None

    close = num(df["Close"].iloc[-1])
    ma20 = num(df["Close"].rolling(20).mean().iloc[-1], close)
    ma50 = num(df["Close"].rolling(50).mean().iloc[-1], close)
    high20 = num(df["High"].rolling(20).max().iloc[-2], close)
    low10 = num(df["Low"].rolling(10).min().iloc[-1], close * 0.95)

    one_day = pct(df, 2)
    five_day = pct(df, 6)
    one_month = pct(df, 22)

    avg_vol = num(df["Volume"].rolling(20).mean().iloc[-1])
    rel_vol = num(df["Volume"].iloc[-1]) / avg_vol if avg_vol > 0 else 0

    above20 = close >= ma20
    above50 = close >= ma50
    dist20 = ((close / ma20) - 1) * 100 if ma20 > 0 else 0
    breakout = close > high20
    near_high = abs((close / high20) - 1) * 100 <= 3 if high20 > 0 else False

    intra = intraday(ticker)
    rs = rs_score(df, spy)
    gp = gap_pct(df)

    engines = {
        "ORB": score_orb(intra, above20, above50, rel_vol, rs, market_light),
        "VWAP": score_vwap(intra, above20, above50, dist20, rs, rel_vol, market_light),
        "Gap": score_gap(gp, intra, rel_vol, rs, market_light),
        "Momentum": score_momentum(one_day, five_day, one_month, rs, above20, above50, rel_vol, dist20, market_light),
        "Daily": score_daily_breakout(close, high20, near_high, breakout, above20, above50, rs, rel_vol, market_light),
    }

    best_setup, best_score = best_setup_from_engines(engines)
    tier = tier_from_score(best_score)
    multiplier = risk_multiplier(tier)

    if best_setup == "ORB":
        pattern = "Opening Range Breakout"
    elif best_setup == "VWAP":
        pattern = "VWAP Reclaim / Hold"
    elif best_setup == "Gap":
        pattern = "Gap-and-Go"
    elif best_setup == "Momentum":
        pattern = "Relative Strength Continuation"
    elif best_setup == "Daily":
        pattern = "Daily Breakout"
    else:
        pattern = "No Clear Pattern"

    stop = round(max(low10, close * 0.94), 2)
    risk_share = max(0, close - stop)

    target1 = round(close + risk_share * 1.25, 2) if risk_share > 0 else round(close * 1.04, 2)
    target2 = round(close + risk_share * 2.00, 2) if risk_share > 0 else round(close * 1.08, 2)

    rr = (target2 - close) / risk_share if risk_share > 0 else 0

    probability = int(max(0, min(95, round(35 + best_score * 0.55))))

    ev = 0
    if risk_share > 0:
        ev = ((probability / 100) * (target1 - close)) - ((1 - probability / 100) * risk_share)

    # v19.2: B setups are allowed with half-risk if EV is non-negative and not structurally broken.
    setup_is_valid = (
        tier in ["A+", "A", "B"]
        and ev >= -0.05
        and risk_share > 0
        and rr >= 1.25
        and intra["OR Status"] != "Below OR Low"
    )

    # In RED market, only A/A+ are allowed unless user toggles aggressive mode.
    if market_light == "RED" and tier == "B":
        setup_is_valid = False

    if setup_is_valid and tier in ["A+", "A"]:
        signal = "TRADE"
    elif setup_is_valid and tier == "B":
        signal = "SMALL TRADE"
    elif tier == "C":
        signal = "WATCH"
    else:
        signal = "NO TRADE"

    max_risk = cash * risk_pct * multiplier

    shares = min(max_risk / risk_share, cash / close) if risk_share > 0 and close > 0 else 0

    if not setup_is_valid:
        shares = 0

    position = shares * close
    dollar_risk = shares * risk_share

    return {
        "Ticker": ticker,
        "Sector": SECTOR.get(ticker, "Other"),
        "Signal": signal,
        "Best Setup": best_setup,
        "Pattern": pattern,
        "Tier": tier,
        "Best Score": best_score,
        "ORB Score": engines["ORB"],
        "VWAP Score": engines["VWAP"],
        "Gap Score": engines["Gap"],
        "Momentum Score": engines["Momentum"],
        "Daily Score": engines["Daily"],
        "Price": round(close, 2),
        "Probability %": probability,
        "RS Score": rs,
        "Gap %": gp,
        "1D %": one_day,
        "5D %": five_day,
        "1M %": one_month,
        "Rel Vol": round(rel_vol, 2),
        "Above VWAP": intra["Above VWAP"],
        "VWAP": intra["VWAP"],
        "Intraday Trend": intra["Intraday Trend"],
        "OR Status": intra["OR Status"],
        "OR Zone": intra["OR Zone"],
        "OR High": intra["OR High"],
        "OR Low": intra["OR Low"],
        "Dist 20MA %": round(dist20, 2),
        "Stop": stop,
        "Target 1": target1,
        "Target 2": target2,
        "Reward/Risk": round(rr, 2),
        "EV / Share": round(ev, 2),
        "Risk Multiplier": multiplier,
        "Shares": round(shares, 4),
        "Position $": round(position, 2),
        "Dollar Risk": round(dollar_risk, 2),
    }


def run_scan(symbols, light, cash, risk_pct):
    spy = get_data("SPY", "3mo", "1d")
    rows = []
    seen = set()

    for symbol in symbols:
        symbol = symbol.strip().upper()
        if not symbol or symbol in seen:
            continue

        seen.add(symbol)
        result = analyze(symbol, spy, light, cash, risk_pct)

        if result:
            rows.append(result)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    return df.sort_values(
        ["Best Score", "Probability %", "RS Score", "EV / Share"],
        ascending=False,
    ).reset_index(drop=True)


# ============================================================
# JOURNAL
# ============================================================

def empty_journal():
    return pd.DataFrame(columns=["Date", "Ticker", "Entry", "Exit", "Shares", "P/L", "Return %", "Pattern", "Mistake", "Notes"])


def load_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            return pd.read_csv(JOURNAL_FILE)
        except Exception:
            return empty_journal()
    return empty_journal()


def save_journal(df):
    df.to_csv(JOURNAL_FILE, index=False)


# ============================================================
# UI COMPONENTS
# ============================================================

def show_top_opportunities(scan, light, score, reason):
    st.header("TODAY'S BEST OPPORTUNITIES")

    tradeable = scan[scan["Signal"].isin(["TRADE", "SMALL TRADE"])].copy()
    top3 = scan.head(3)

    if tradeable.empty:
        st.error("NO APPROVED TRADE YET")
        st.write("Best candidates are watch-only. Wait for stronger setup alignment.")
    else:
        best = tradeable.iloc[0]
        st.success(f"FOCUS: {best['Ticker']} - {best['Tier']} {best['Best Setup']} - {best['Signal']}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Market", f"{light} {score}/100")
    c2.metric("Tradeable Names", len(tradeable))
    c3.metric("Top Score", scan.iloc[0]["Best Score"])
    c4.metric("Top Setup", scan.iloc[0]["Best Setup"])

    st.caption(reason)

    display = top3[[
        "Ticker", "Signal", "Tier", "Best Setup", "Best Score", "Probability %",
        "Price", "Stop", "Target 1", "Shares", "Position $", "Dollar Risk",
        "EV / Share", "Above VWAP", "OR Zone", "RS Score"
    ]]

    st.dataframe(display, use_container_width=True)


def show_trade_plan(row, light):
    st.header("Trade Plan")

    if row is None:
        st.info("No setup selected.")
        return

    if row["Signal"] in ["TRADE", "SMALL TRADE"]:
        if row["Signal"] == "TRADE":
            st.success(f"{row['Ticker']} is tradeable as {row['Tier']} {row['Best Setup']}")
        else:
            st.warning(f"{row['Ticker']} is a SMALL TRADE only")
    else:
        st.error(f"{row['Ticker']} is not approved yet")

    a, b, c, d, e = st.columns(5)
    a.metric("Ticker", row["Ticker"])
    b.metric("Setup", row["Best Setup"])
    c.metric("Tier", row["Tier"])
    d.metric("Score", row["Best Score"])
    e.metric("Probability", f"{row['Probability %']}%")

    f, g, h, i = st.columns(4)
    f.metric("Entry", f"${row['Price']:.2f}")
    g.metric("Stop", f"${row['Stop']:.2f}")
    h.metric("Target 1", f"${row['Target 1']:.2f}")
    i.metric("Target 2", f"${row['Target 2']:.2f}")

    j, k, l, m = st.columns(4)
    j.metric("Shares", f"{row['Shares']:.4f}")
    k.metric("Position", f"${row['Position $']:,.2f}")
    l.metric("Dollar Risk", f"${row['Dollar Risk']:,.2f}")
    m.metric("Risk Multiplier", f"{row['Risk Multiplier']:.2f}x")

    st.write(f"Pattern: **{row['Pattern']}**")
    st.write(f"Context: VWAP **{row['Above VWAP']}**, OR Zone **{row['OR Zone']}**, Intraday **{row['Intraday Trend']}**, RS **{row['RS Score']}**")

    checklist(row, light)


def checklist(row, light):
    st.subheader("Rules Checklist")

    checks = [
        ("Tier is A+, A, or B", row["Tier"] in ["A+", "A", "B"]),
        ("Market not RED for B setup", not (light == "RED" and row["Tier"] == "B")),
        ("EV is non-negative", row["EV / Share"] >= -0.05),
        ("Reward/Risk >= 1.25", row["Reward/Risk"] >= 1.25),
        ("Not below OR low", row["OR Status"] != "Below OR Low"),
        ("Setup score >= 70", row["Best Score"] >= 70),
        ("Relative strength acceptable", row["RS Score"] >= 50),
        ("Risk position generated", row["Position $"] > 0),
    ]

    passed = sum(1 for _, ok in checks if ok)

    st.write(f"Checklist Score: **{passed}/{len(checks)}**")

    for label, ok in checks:
        st.write(("YES - " if ok else "NO - ") + label)


def show_engine_scores(scan):
    st.header("Setup Engine Scores")

    st.dataframe(
        scan[[
            "Ticker", "Sector", "Signal", "Tier", "Best Setup", "Best Score",
            "ORB Score", "VWAP Score", "Gap Score", "Momentum Score", "Daily Score",
            "Price", "Probability %", "RS Score", "EV / Share"
        ]],
        use_container_width=True,
        height=520,
    )


def show_sector_strength(scan):
    st.header("Sector Strength")

    sec = scan.groupby("Sector").agg(
        Names=("Ticker", "count"),
        Tradeable=("Signal", lambda x: x.isin(["TRADE", "SMALL TRADE"]).sum()),
        Avg_Best_Score=("Best Score", "mean"),
        Avg_RS=("RS Score", "mean"),
        Avg_EV=("EV / Share", "mean"),
    ).reset_index()

    sec["Avg_Best_Score"] = sec["Avg_Best_Score"].round(1)
    sec["Avg_RS"] = sec["Avg_RS"].round(1)
    sec["Avg_EV"] = sec["Avg_EV"].round(2)

    st.dataframe(sec.sort_values(["Tradeable", "Avg_Best_Score"], ascending=False), use_container_width=True)


def show_no_trade(scan):
    st.header("No Trade / Watch List")

    nt = scan[~scan["Signal"].isin(["TRADE", "SMALL TRADE"])].copy()

    if nt.empty:
        st.success("Everything in the top scan is at least small-trade eligible.")
        return

    st.dataframe(
        nt[[
            "Ticker", "Signal", "Tier", "Best Setup", "Best Score", "Price",
            "EV / Share", "Reward/Risk", "Above VWAP", "OR Status", "OR Zone", "RS Score"
        ]],
        use_container_width=True,
        height=420,
    )


def show_participation(scan):
    st.header("Participation Target")

    tradeable = scan[scan["Signal"].isin(["TRADE", "SMALL TRADE"])]
    participation = len(tradeable) / len(scan) * 100 if len(scan) else 0

    a, b, c = st.columns(3)
    a.metric("Tradeable %", f"{participation:.1f}%")
    b.metric("Tradeable Names", len(tradeable))
    c.metric("Scanned Names", len(scan))

    if participation >= 70:
        st.success("Participation is high. Be careful not to overtrade.")
    elif participation >= 40:
        st.warning("Participation is moderate. Good balance if quality remains acceptable.")
    else:
        st.error("Participation is low. Conditions are still selective.")


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

        a, b, c = st.columns(3)
        a.metric("Total P/L", f"${total:,.2f}")
        b.metric("Win Rate", f"{wr:.1f}%")
        c.metric("Profit Factor", "infinity" if pf == np.inf else f"{pf:.2f}")

        st.dataframe(j, use_container_width=True)
    else:
        st.info("No journal trades yet.")

    with st.form("journal_form", clear_on_submit=True):
        a, b, c, d = st.columns(4)
        dt = a.date_input("Date", value=date.today())
        ticker = b.text_input("Ticker")
        entry = c.number_input("Entry", min_value=0.0, step=0.01)
        exitp = d.number_input("Exit", min_value=0.0, step=0.01)

        e, f, g, h = st.columns(4)
        shares = e.number_input("Shares", min_value=0.0, step=0.0001, format="%.6f")
        pattern = f.selectbox("Pattern", ["ORB", "VWAP", "Gap", "Momentum", "Daily", "Other"])
        mistake = g.selectbox("Mistake", ["None", "Chased", "Ignored stop", "Sold too early", "No trigger", "Oversized", "Revenge trade"])
        notes = h.text_input("Notes")

        if st.form_submit_button("Save Trade"):
            if ticker.strip() and entry > 0 and exitp > 0 and shares > 0:
                pnl = (exitp - entry) * shares
                ret = ((exitp / entry) - 1) * 100

                row = {
                    "Date": dt.isoformat(),
                    "Ticker": ticker.strip().upper(),
                    "Entry": round(entry, 2),
                    "Exit": round(exitp, 2),
                    "Shares": round(shares, 6),
                    "P/L": round(pnl, 2),
                    "Return %": round(ret, 2),
                    "Pattern": pattern,
                    "Mistake": mistake,
                    "Notes": notes,
                }

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
    required = ["Instrument", "Trans Code", "Quantity", "Amount"]
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

    trades = df[df["Trans Code"].isin(["Buy", "Sell"])]

    rows = []

    for ticker, group in trades.groupby("Instrument"):
        buys = group[group["Trans Code"] == "Buy"]
        sells = group[group["Trans Code"] == "Sell"]

        buy_cost = abs(buys["Amount Clean"].sum())
        proceeds = sells["Amount Clean"].sum()
        pnl = proceeds - buy_cost

        rows.append({
            "Ticker": ticker,
            "Buy Cost": round(buy_cost, 2),
            "Sell Proceeds": round(proceeds, 2),
            "P/L": round(pnl, 2),
            "Return %": round((pnl / buy_cost * 100), 2) if buy_cost > 0 else None,
            "Rows": len(group),
        })

    out = pd.DataFrame(rows).sort_values("P/L", ascending=False)

    st.metric("Uploaded CSV Total P/L", f"${out['P/L'].sum():,.2f}" if not out.empty else "$0.00")
    st.dataframe(out, use_container_width=True)


def validator(light):
    st.header("Manual Trade Validator")

    a, b, c, d = st.columns(4)
    ticker = a.text_input("Ticker", key="v_ticker")
    entry = b.number_input("Entry", min_value=0.0, step=0.01, key="v_entry")
    stop = c.number_input("Stop", min_value=0.0, step=0.01, key="v_stop")
    target = d.number_input("Target", min_value=0.0, step=0.01, key="v_target")

    e, f, g = st.columns(3)
    shares = e.number_input("Shares", min_value=0.0, step=0.0001, format="%.6f", key="v_shares")
    above_vwap = f.checkbox("Above VWAP?")
    above_or = g.checkbox("Above OR High?")

    if st.button("Validate Trade"):
        fails = []

        if light == "RED":
            fails.append("Market is RED. Only A/A+ setups preferred.")

        if entry <= 0 or stop <= 0 or target <= 0 or shares <= 0:
            fails.append("Missing entry/stop/target/shares.")
        elif stop >= entry:
            fails.append("Stop must be below entry.")
        elif target <= entry:
            fails.append("Target must be above entry.")
        else:
            rr = (target - entry) / (entry - stop)
            if rr < 1.25:
                fails.append(f"Reward/risk too low: {rr:.2f}")

        if not above_vwap:
            fails.append("Not above VWAP.")

        if not above_or:
            fails.append("Not above OR high.")

        if fails:
            st.error("NO TRADE")
            for item in fails:
                st.write("NO - " + item)
        else:
            st.success("TRADE ALLOWED BY RULES")

        if entry > 0 and stop > 0 and target > entry and shares > 0:
            st.metric("Dollar Risk", f"${(entry - stop) * shares:,.2f}")
            st.metric("Dollar Reward", f"${(target - entry) * shares:,.2f}")


def charts(scan):
    st.header("Charts")

    ticker = st.selectbox("Ticker", scan["Ticker"].tolist())
    tf = st.radio("Timeframe", ["5m", "15m", "Daily"], horizontal=True)

    if tf == "5m":
        df = get_data(ticker, "1d", "5m")
    elif tf == "15m":
        df = get_data(ticker, "5d", "15m")
    else:
        df = get_data(ticker, "3mo", "1d")

    if df.empty:
        st.warning("Chart unavailable.")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
        )
    )

    fig.add_trace(go.Scatter(x=df.index, y=df["Close"].rolling(20).mean(), mode="lines", name="20MA"))

    if tf == "5m" and len(df) >= 3:
        fig.add_hline(y=df.head(3)["High"].max(), line_dash="dash", annotation_text="OR High")
        fig.add_hline(y=df.head(3)["Low"].min(), line_dash="dash", annotation_text="OR Low")

    fig.update_layout(height=550, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# APP
# ============================================================

st.title("Deon's Trader Dashboard v19.2")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.sidebar.header("Settings")

watchlist_text = st.sidebar.text_area("Manual Watchlist", ",".join(DEFAULT_WATCHLIST), height=90)
scan_text = st.sidebar.text_area("Scanner Universe", ",".join(DEFAULT_SCAN), height=170)

cash = st.sidebar.number_input("Cash available", min_value=0.0, value=855.0, step=25.0)
risk_input = st.sidebar.number_input("Base risk per trade %", min_value=0.25, max_value=10.0, value=3.0, step=0.25)
risk_pct = risk_input / 100

st.sidebar.write("A+ max risk:", f"${cash * risk_pct:,.2f}")
st.sidebar.write("A max risk:", f"${cash * risk_pct * 0.75:,.2f}")
st.sidebar.write("B max risk:", f"${cash * risk_pct * 0.50:,.2f}")

if st.sidebar.button("Refresh now"):
    st.cache_data.clear()
    st.rerun()

mkt = market_context()
light, regime, mscore, reason = market_state(mkt)

st.header("Market")
st.dataframe(mkt, use_container_width=True)

if light == "GREEN":
    st.success(f"{light} - {regime}")
elif light == "YELLOW":
    st.warning(f"{light} - {regime}")
else:
    st.error(f"{light} - {regime}")

st.progress(mscore)

symbols = [x.strip().upper() for x in scan_text.split(",") if x.strip()]

with st.spinner("Scanning opportunity engines..."):
    scan = run_scan(symbols, light, cash, risk_pct)

if scan.empty:
    st.error("No data loaded. Try fewer tickers, wait one minute, then refresh.")
    st.stop()

show_top_opportunities(scan, light, mscore, reason)

tabs = st.tabs([
    "Opportunities",
    "Trade Plan",
    "Engine Scores",
    "No Trade / Watch",
    "Sector Strength",
    "Participation",
    "Validator",
    "Journal",
    "Robinhood CSV",
    "Charts",
])

with tabs[0]:
    st.header("Ranked Opportunity Board")
    top = scan.head(20).copy()
    top.insert(0, "Rank", range(1, len(top) + 1))

    st.dataframe(
        top[[
            "Rank", "Ticker", "Sector", "Signal", "Tier", "Best Setup", "Best Score",
            "Price", "Probability %", "EV / Share", "Shares", "Position $",
            "Dollar Risk", "Above VWAP", "OR Zone", "RS Score"
        ]],
        use_container_width=True,
        height=560,
    )

    st.subheader("Manual Watchlist")
    manual = [x.strip().upper() for x in watchlist_text.split(",") if x.strip()]
    st.dataframe(scan[scan["Ticker"].isin(manual)], use_container_width=True, height=320)

with tabs[1]:
    selected = st.selectbox("Select opportunity", scan["Ticker"].tolist(), key="plan_select")
    row = scan[scan["Ticker"] == selected].iloc[0]
    show_trade_plan(row, light)

with tabs[2]:
    show_engine_scores(scan)

with tabs[3]:
    show_no_trade(scan)

with tabs[4]:
    show_sector_strength(scan)

with tabs[5]:
    show_participation(scan)

with tabs[6]:
    validator(light)

with tabs[7]:
    journal_tab()

with tabs[8]:
    csv_tab()

with tabs[9]:
    charts(scan)

st.caption("v19.2 expands opportunity by scoring ORB, VWAP, Gap, Momentum, and Daily Breakout setups separately. Risk is scaled by tier.")
