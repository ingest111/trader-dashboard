
import os
import json
from datetime import datetime, date
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ============================================================
# DEON'S TRADER DASHBOARD v21
# SNAPSHOT ENGINE
#
# Based on v20 Money Flow Engine.
# New:
# - Export dashboard_snapshot.csv
# - Export dashboard_snapshot.json
# - Export top10, top3, sectors, no-trade lists
# - Copy/paste text summary for ChatGPT
# ============================================================

st.set_page_config(page_title="Deon's Trader Dashboard v21", layout="wide")

MARKETS = ["SPY", "QQQ", "^VIX", "^TNX"]

DEFAULT_SCAN = [
    "NVDA", "AMD", "AVGO", "ARM", "MU", "TSM", "MRVL", "CRDO",
    "PLTR", "APP", "HOOD", "HIMS", "SOFI", "RDDT",
    "META", "AMZN", "MSFT", "GOOGL", "TSLA", "COIN",
    "SMCI", "DELL", "ORCL", "CEG", "VRT", "ANET",
]

DEFAULT_WATCHLIST = ["NVDA", "AMD", "AVGO", "MU", "TSM", "PLTR", "CRDO", "META", "RDDT", "HIMS"]

SECTOR = {
    "NVDA": "Semis", "AMD": "Semis", "AVGO": "Semis", "ARM": "Semis",
    "MU": "Semis", "TSM": "Semis", "MRVL": "Semis", "CRDO": "Semis",
    "SMCI": "AI Infra", "DELL": "AI Infra", "VRT": "AI Infra", "ANET": "AI Infra",
    "PLTR": "AI Software", "APP": "Software", "MSFT": "Mega Cap", "GOOGL": "Mega Cap",
    "META": "Mega Cap", "AMZN": "Mega Cap", "HOOD": "Fintech", "SOFI": "Fintech",
    "COIN": "Crypto", "MSTR": "Crypto", "HIMS": "Momentum", "RDDT": "Momentum",
    "TSLA": "High Beta", "ORCL": "Software", "CEG": "Energy",
}

JOURNAL_FILE = "trade_journal_v21.csv"


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

    spy_1d = v("SPY", "1D %")
    qqq_1d = v("QQQ", "1D %")
    spy_5d = v("SPY", "5D %")
    qqq_5d = v("QQQ", "5D %")
    vix_1d = v("^VIX", "1D %")

    score = 50

    if spy_1d >= 0:
        score += 12
    elif spy_1d > -0.75:
        score -= 5
    else:
        score -= 15

    if qqq_1d >= 0:
        score += 12
    elif qqq_1d > -0.75:
        score -= 5
    else:
        score -= 15

    if spy_5d >= 0:
        score += 8
    else:
        score -= 8

    if qqq_5d >= 0:
        score += 8
    else:
        score -= 8

    if vix_1d <= 0:
        score += 10
    elif vix_1d < 3:
        score -= 5
    else:
        score -= 15

    score = int(max(0, min(100, score)))

    if score >= 65:
        return "GREEN", "Bullish", score, "Risk-on backdrop"
    if score >= 35:
        return "YELLOW", "Mixed", score, "Trade selectively; money flow matters more than index direction"

    return "RED", "Defensive", score, "Weak tape; only strongest money-flow names qualify"


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
# SETUP ENGINES
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
        score -= 5

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
        score -= 5

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
        score -= 5

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
        score -= 5

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
        score -= 5

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

    pattern_map = {
        "ORB": "Opening Range Breakout",
        "VWAP": "VWAP Reclaim / Hold",
        "Gap": "Gap-and-Go",
        "Momentum": "Relative Strength Continuation",
        "Daily": "Daily Breakout",
    }

    pattern = pattern_map.get(best_setup, "No Clear Pattern")

    stop = round(max(low10, close * 0.94), 2)
    risk_share = max(0, close - stop)

    target1 = round(close + risk_share * 1.25, 2) if risk_share > 0 else round(close * 1.04, 2)
    target2 = round(close + risk_share * 2.00, 2) if risk_share > 0 else round(close * 1.08, 2)

    rr = (target2 - close) / risk_share if risk_share > 0 else 0

    probability = int(max(0, min(95, round(35 + best_score * 0.55))))

    ev = 0
    if risk_share > 0:
        ev = ((probability / 100) * (target1 - close)) - ((1 - probability / 100) * risk_share)

    setup_is_valid = (
        tier in ["A+", "A", "B"]
        and ev >= -0.10
        and risk_share > 0
        and rr >= 1.20
        and intra["OR Status"] != "Below OR Low"
    )

    if market_light == "RED" and tier == "B" and rs < 60:
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

    money_flow = (
        (best_score * 0.35)
        + (rs * 0.25)
        + (min(rel_vol, 3.0) / 3.0 * 20)
        + (max(min(gp, 5), -5) + 5)
        + (10 if intra["Above VWAP"] else 0)
    )

    money_flow = int(max(0, min(100, round(money_flow))))

    reason_parts = []
    if intra["Above VWAP"]:
        reason_parts.append("Above VWAP")
    if intra["OR Zone"] in ["Breakout", "Near breakout", "Upper range"]:
        reason_parts.append(intra["OR Zone"])
    if rs >= 70:
        reason_parts.append("Strong RS")
    elif rs >= 60:
        reason_parts.append("Acceptable RS")
    if rel_vol >= 1.5:
        reason_parts.append("High relative volume")
    elif rel_vol >= 1.0:
        reason_parts.append("Volume active")
    if gp >= 2:
        reason_parts.append("Positive gap")
    if best_score >= 80:
        reason_parts.append(f"{best_setup} engine strong")

    reason = " + ".join(reason_parts) if reason_parts else "No dominant money-flow edge"

    return {
        "Ticker": ticker,
        "Sector": SECTOR.get(ticker, "Other"),
        "Signal": signal,
        "Best Setup": best_setup,
        "Pattern": pattern,
        "Tier": tier,
        "Best Score": best_score,
        "Money Flow Score": money_flow,
        "Reason": reason,
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
        ["Money Flow Score", "Best Score", "RS Score", "EV / Share"],
        ascending=False,
    ).reset_index(drop=True)


# ============================================================
# SNAPSHOT ENGINE
# ============================================================

def sector_flow_df(scan):
    if scan.empty:
        return pd.DataFrame()

    sec = scan.groupby("Sector").agg(
        Names=("Ticker", "count"),
        Tradeable=("Signal", lambda x: x.isin(["TRADE", "SMALL TRADE"]).sum()),
        Avg_Flow=("Money Flow Score", "mean"),
        Avg_Setup=("Best Score", "mean"),
        Avg_RS=("RS Score", "mean"),
        Avg_EV=("EV / Share", "mean"),
    ).reset_index()

    sec["Avg_Flow"] = sec["Avg_Flow"].round(1)
    sec["Avg_Setup"] = sec["Avg_Setup"].round(1)
    sec["Avg_RS"] = sec["Avg_RS"].round(1)
    sec["Avg_EV"] = sec["Avg_EV"].round(2)

    return sec.sort_values(["Tradeable", "Avg_Flow", "Avg_RS"], ascending=False)


def make_snapshot(scan, mkt, light, regime, mscore, reason):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tradeable = scan[scan["Signal"].isin(["TRADE", "SMALL TRADE"])].copy()
    top = scan.iloc[0].to_dict()
    top_trade = tradeable.iloc[0].to_dict() if not tradeable.empty else None
    sectors = sector_flow_df(scan)

    snapshot = {
        "timestamp": timestamp,
        "market": {
            "light": light,
            "regime": regime,
            "score": int(mscore),
            "reason": reason,
            "context": mkt.to_dict(orient="records"),
        },
        "top_flow_name": top,
        "top_tradeable_name": top_trade,
        "tradeable_count": int(len(tradeable)),
        "scanned_count": int(len(scan)),
        "top_3": scan.head(3).to_dict(orient="records"),
        "top_10": scan.head(10).to_dict(orient="records"),
        "sector_flow": sectors.to_dict(orient="records"),
        "no_trade_watch": scan[~scan["Signal"].isin(["TRADE", "SMALL TRADE"])].head(10).to_dict(orient="records"),
    }

    return snapshot


def snapshot_summary_text(snapshot):
    market = snapshot["market"]
    top_trade = snapshot["top_tradeable_name"]
    top_flow = snapshot["top_flow_name"]

    lines = []
    lines.append("DASHBOARD SNAPSHOT")
    lines.append(f"Timestamp: {snapshot['timestamp']}")
    lines.append(f"Market: {market['light']} {market['score']}/100 - {market['regime']}")
    lines.append(f"Market reason: {market['reason']}")
    lines.append("")
    lines.append(f"Scanned names: {snapshot['scanned_count']}")
    lines.append(f"Tradeable names: {snapshot['tradeable_count']}")
    lines.append("")

    if top_trade:
        lines.append("TOP TRADEABLE NAME")
        lines.append(f"Ticker: {top_trade['Ticker']}")
        lines.append(f"Signal: {top_trade['Signal']}")
        lines.append(f"Tier: {top_trade['Tier']}")
        lines.append(f"Best Setup: {top_trade['Best Setup']}")
        lines.append(f"Money Flow Score: {top_trade['Money Flow Score']}")
        lines.append(f"Price: {top_trade['Price']}")
        lines.append(f"Stop: {top_trade['Stop']}")
        lines.append(f"Target 1: {top_trade['Target 1']}")
        lines.append(f"Shares: {top_trade['Shares']}")
        lines.append(f"Position $: {top_trade['Position $']}")
        lines.append(f"Dollar Risk: {top_trade['Dollar Risk']}")
        lines.append(f"Reason: {top_trade['Reason']}")
    else:
        lines.append("TOP TRADEABLE NAME")
        lines.append("None approved yet.")
        lines.append("")
        lines.append("STRONGEST FLOW NAME")
        lines.append(f"Ticker: {top_flow['Ticker']}")
        lines.append(f"Signal: {top_flow['Signal']}")
        lines.append(f"Tier: {top_flow['Tier']}")
        lines.append(f"Best Setup: {top_flow['Best Setup']}")
        lines.append(f"Money Flow Score: {top_flow['Money Flow Score']}")
        lines.append(f"Reason: {top_flow['Reason']}")

    lines.append("")
    lines.append("TOP 3")
    for i, row in enumerate(snapshot["top_3"], start=1):
        lines.append(
            f"{i}. {row['Ticker']} | {row['Signal']} | {row['Tier']} | {row['Best Setup']} | "
            f"Flow {row['Money Flow Score']} | Price {row['Price']} | Reason: {row['Reason']}"
        )

    lines.append("")
    lines.append("SECTOR FLOW")
    for i, row in enumerate(snapshot["sector_flow"][:5], start=1):
        lines.append(
            f"{i}. {row['Sector']} | Tradeable {row['Tradeable']} | Avg Flow {row['Avg_Flow']} | Avg RS {row['Avg_RS']}"
        )

    return "\n".join(lines)


def convert_df_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def convert_json(obj):
    return json.dumps(obj, indent=2, default=str).encode("utf-8")


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
# UI
# ============================================================

def money_flow_dashboard(scan, light, score, reason):
    st.header("MONEY FLOW DASHBOARD")

    tradeable = scan[scan["Signal"].isin(["TRADE", "SMALL TRADE"])].copy()

    top_flow = scan.iloc[0]
    top_trade = tradeable.iloc[0] if not tradeable.empty else None

    if top_trade is not None:
        st.success(f"TODAY'S FOCUS: {top_trade['Ticker']} - {top_trade['Tier']} {top_trade['Best Setup']} - {top_trade['Signal']}")
    else:
        st.error(f"NO APPROVED TRADE YET. Strongest flow: {top_flow['Ticker']}")

    a, b, c, d = st.columns(4)
    a.metric("Market", f"{light} {score}/100")
    b.metric("Tradeable Names", len(tradeable))
    c.metric("Strongest Flow", top_flow["Ticker"])
    d.metric("Top Flow Score", top_flow["Money Flow Score"])

    st.caption(reason)

    st.subheader("Top 3 Money Flow Names")
    top3 = scan.head(3).copy()

    st.dataframe(
        top3[[
            "Ticker", "Sector", "Signal", "Tier", "Best Setup", "Money Flow Score",
            "Best Score", "Reason", "Price", "Stop", "Target 1",
            "Shares", "Position $", "Dollar Risk"
        ]],
        use_container_width=True,
    )


def snapshot_tab(scan, mkt, light, regime, mscore, reason):
    st.header("Dashboard Snapshot Export")

    snapshot = make_snapshot(scan, mkt, light, regime, mscore, reason)
    summary_text = snapshot_summary_text(snapshot)
    sectors = sector_flow_df(scan)
    tradeable = scan[scan["Signal"].isin(["TRADE", "SMALL TRADE"])].copy()
    no_trade = scan[~scan["Signal"].isin(["TRADE", "SMALL TRADE"])].copy()

    st.subheader("Copy/Paste Snapshot for ChatGPT")
    st.text_area("Snapshot text", summary_text, height=420)

    st.download_button(
        "Download snapshot JSON",
        data=convert_json(snapshot),
        file_name="dashboard_snapshot.json",
        mime="application/json",
    )

    st.download_button(
        "Download top 10 CSV",
        data=convert_df_csv(scan.head(10)),
        file_name="dashboard_top10.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download full scan CSV",
        data=convert_df_csv(scan),
        file_name="dashboard_full_scan.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download sector flow CSV",
        data=convert_df_csv(sectors),
        file_name="dashboard_sector_flow.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download tradeable names CSV",
        data=convert_df_csv(tradeable),
        file_name="dashboard_tradeable.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download no-trade watchlist CSV",
        data=convert_df_csv(no_trade),
        file_name="dashboard_no_trade_watch.csv",
        mime="text/csv",
    )

    st.info("Fastest workflow: copy the Snapshot text box and paste it into ChatGPT. Best data workflow: download dashboard_snapshot.json or dashboard_top10.csv and upload it.")


def trade_plan(row, light):
    st.header("Trade Plan")

    if row["Signal"] in ["TRADE", "SMALL TRADE"]:
        st.success(f"{row['Ticker']} is eligible: {row['Signal']}")
    else:
        st.error(f"{row['Ticker']} is not eligible yet")

    a, b, c, d, e = st.columns(5)
    a.metric("Ticker", row["Ticker"])
    b.metric("Setup", row["Best Setup"])
    c.metric("Tier", row["Tier"])
    d.metric("Money Flow", row["Money Flow Score"])
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

    st.write(f"Reason: **{row['Reason']}**")
    st.write(f"Context: VWAP **{row['Above VWAP']}**, OR Zone **{row['OR Zone']}**, Intraday **{row['Intraday Trend']}**, RS **{row['RS Score']}**")

    checklist(row, light)


def checklist(row, light):
    st.subheader("Rules Checklist")

    checks = [
        ("Tier is A+, A, or B", row["Tier"] in ["A+", "A", "B"]),
        ("Money Flow Score >= 65", row["Money Flow Score"] >= 65),
        ("Market allows setup", not (light == "RED" and row["Tier"] == "B" and row["RS Score"] < 60)),
        ("EV not deeply negative", row["EV / Share"] >= -0.10),
        ("Reward/Risk >= 1.20", row["Reward/Risk"] >= 1.20),
        ("Not below OR low", row["OR Status"] != "Below OR Low"),
        ("Relative strength acceptable", row["RS Score"] >= 50),
        ("Risk position generated", row["Position $"] > 0),
    ]

    passed = sum(1 for _, ok in checks if ok)
    st.write(f"Checklist Score: **{passed}/{len(checks)}**")

    for label, ok in checks:
        st.write(("YES - " if ok else "NO - ") + label)


def show_ranked_board(scan):
    st.header("Ranked Money Flow Board")

    top = scan.head(25).copy()
    top.insert(0, "Rank", range(1, len(top) + 1))

    st.dataframe(
        top[[
            "Rank", "Ticker", "Sector", "Signal", "Tier", "Best Setup",
            "Money Flow Score", "Best Score", "Reason", "Price", "Probability %",
            "EV / Share", "Position $", "Dollar Risk", "Above VWAP", "OR Zone", "RS Score"
        ]],
        use_container_width=True,
        height=600,
    )


def sector_flow_ui(scan):
    st.header("Sector Money Flow")

    sec = sector_flow_df(scan)

    st.dataframe(sec, use_container_width=True)

    if not sec.empty:
        leader_sector = sec.iloc[0]["Sector"]
        leaders = scan[scan["Sector"] == leader_sector].head(5)

        st.subheader(f"Leaders in strongest sector: {leader_sector}")
        st.dataframe(
            leaders[[
                "Ticker", "Signal", "Tier", "Best Setup", "Money Flow Score",
                "Best Score", "Reason", "Price", "Position $"
            ]],
            use_container_width=True,
        )


def engine_scores(scan):
    st.header("Setup Engine Scores")

    st.dataframe(
        scan[[
            "Ticker", "Sector", "Signal", "Tier", "Best Setup", "Money Flow Score", "Best Score",
            "ORB Score", "VWAP Score", "Gap Score", "Momentum Score", "Daily Score",
            "Price", "RS Score", "EV / Share"
        ]],
        use_container_width=True,
        height=560,
    )


def watch_no_trade(scan):
    st.header("No Trade / Watch Board")

    nt = scan[~scan["Signal"].isin(["TRADE", "SMALL TRADE"])].copy()

    if nt.empty:
        st.success("All names in scan are at least small-trade eligible.")
        return

    st.dataframe(
        nt[[
            "Ticker", "Signal", "Tier", "Best Setup", "Money Flow Score",
            "Best Score", "Reason", "Price", "EV / Share",
            "Reward/Risk", "Above VWAP", "OR Status", "OR Zone", "RS Score"
        ]],
        use_container_width=True,
        height=500,
    )


def participation(scan):
    st.header("Participation Target")

    tradeable = scan[scan["Signal"].isin(["TRADE", "SMALL TRADE"])]
    participation_rate = len(tradeable) / len(scan) * 100 if len(scan) else 0

    a, b, c, d = st.columns(4)
    a.metric("Tradeable %", f"{participation_rate:.1f}%")
    b.metric("Tradeable Names", len(tradeable))
    c.metric("Scanned Names", len(scan))
    d.metric("Goal", "70-85%")

    if participation_rate >= 70:
        st.success("Participation target reached. Do not overtrade; take best ranked setups only.")
    elif participation_rate >= 40:
        st.warning("Participation is moderate. Good if top setups are strong.")
    else:
        st.error("Participation is still low. Conditions remain selective.")


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
            fails.append("Market is RED. Only strongest setups preferred.")

        if entry <= 0 or stop <= 0 or target <= 0 or shares <= 0:
            fails.append("Missing entry/stop/target/shares.")
        elif stop >= entry:
            fails.append("Stop must be below entry.")
        elif target <= entry:
            fails.append("Target must be above entry.")
        else:
            rr = (target - entry) / (entry - stop)
            if rr < 1.20:
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

st.title("Deon's Trader Dashboard v21")
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

with st.spinner("Scanning money flow..."):
    scan = run_scan(symbols, light, cash, risk_pct)

if scan.empty:
    st.error("No data loaded. Try fewer tickers, wait one minute, then refresh.")
    st.stop()

money_flow_dashboard(scan, light, mscore, reason)

tabs = st.tabs([
    "Snapshot Export",
    "Money Flow Board",
    "Trade Plan",
    "Sector Flow",
    "Engine Scores",
    "No Trade / Watch",
    "Participation",
    "Validator",
    "Journal",
    "Robinhood CSV",
    "Charts",
])

with tabs[0]:
    snapshot_tab(scan, mkt, light, regime, mscore, reason)

with tabs[1]:
    show_ranked_board(scan)

    st.subheader("Manual Watchlist")
    manual = [x.strip().upper() for x in watchlist_text.split(",") if x.strip()]
    st.dataframe(scan[scan["Ticker"].isin(manual)], use_container_width=True, height=320)

with tabs[2]:
    selected = st.selectbox("Select opportunity", scan["Ticker"].tolist(), key="plan_select")
    row = scan[scan["Ticker"] == selected].iloc[0]
    trade_plan(row, light)

with tabs[3]:
    sector_flow_ui(scan)

with tabs[4]:
    engine_scores(scan)

with tabs[5]:
    watch_no_trade(scan)

with tabs[6]:
    participation(scan)

with tabs[7]:
    validator(light)

with tabs[8]:
    journal_tab()

with tabs[9]:
    csv_tab()

with tabs[10]:
    charts(scan)

st.caption("v21 adds Snapshot Export so ChatGPT can review structured dashboard state instead of screenshots.")
