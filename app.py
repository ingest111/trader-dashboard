
import json
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ============================================================
# DEON'S TRADER DASHBOARD v26
# CATALYST & NEWS ENGINE BUILD
#
# Goal:
# - Make the "10/10" workflow happen inside the app.
# - No routine screenshots.
# - One short briefing for ChatGPT.
# - One full packet for deeper review.
# - Explicit TRADE / WAIT / AVOID operating logic.
# - Chart screenshot only when a setup is close.
# ============================================================

st.set_page_config(page_title="Deon's Trader Dashboard v26", layout="wide")

MARKETS = ["SPY", "QQQ", "^VIX", "^TNX"]

DEFAULT_SCAN = [
    "NVDA", "AMD", "AVGO", "ARM", "MU", "TSM", "MRVL", "CRDO",
    "PLTR", "APP", "HOOD", "HIMS", "SOFI", "RDDT",
    "META", "AMZN", "MSFT", "GOOGL", "TSLA", "COIN",
    "SMCI", "DELL", "ORCL", "CEG", "VRT", "ANET"
]

DEFAULT_WATCHLIST = ["NVDA", "AMD", "AVGO", "MU", "TSM", "PLTR", "CRDO", "META", "RDDT", "HIMS"]

SECTOR = {
    "NVDA": "Semis", "AMD": "Semis", "AVGO": "Semis", "ARM": "Semis",
    "MU": "Semis", "TSM": "Semis", "MRVL": "Semis", "CRDO": "Semis",
    "SMCI": "AI Infra", "DELL": "AI Infra", "VRT": "AI Infra", "ANET": "AI Infra",
    "PLTR": "AI Software", "APP": "Software", "MSFT": "Mega Cap", "GOOGL": "Mega Cap",
    "META": "Mega Cap", "AMZN": "Mega Cap", "HOOD": "Fintech", "SOFI": "Fintech",
    "COIN": "Crypto", "MSTR": "Crypto", "HIMS": "Momentum", "RDDT": "Momentum",
    "TSLA": "High Beta", "ORCL": "Software", "CEG": "Energy"
}


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

        required = ["Open", "High", "Low", "Close", "Volume"]
        if any(col not in df.columns for col in required):
            return pd.DataFrame()

        return df.dropna()
    except Exception:
        return pd.DataFrame()


def safe_num(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def pct_change(df, bars):
    if df.empty or len(df) <= bars:
        return 0.0

    start = safe_num(df["Close"].iloc[-bars])
    end = safe_num(df["Close"].iloc[-1])

    if start <= 0:
        return 0.0

    return round(((end / start) - 1) * 100, 2)


# ============================================================
# MARKET ENGINE
# ============================================================

def market_context():
    rows = []

    for ticker in MARKETS:
        df = get_data(ticker, "1mo", "1d")

        if df.empty:
            continue

        close = safe_num(df["Close"].iloc[-1])
        ma10 = safe_num(df["Close"].rolling(10).mean().iloc[-1], close)

        rows.append({
            "Market": ticker,
            "Price": round(close, 2),
            "1D %": pct_change(df, 2),
            "5D %": pct_change(df, 6),
            "Trend": "Above 10MA" if close >= ma10 else "Below 10MA",
        })

    return pd.DataFrame(rows)


def market_state(mdf):
    if mdf.empty:
        return "RED", "Defensive", 0, "Market data unavailable"

    def value(symbol, column):
        arr = mdf.loc[mdf["Market"] == symbol, column].values
        return safe_num(arr[0]) if len(arr) else 0.0

    spy_1d = value("SPY", "1D %")
    qqq_1d = value("QQQ", "1D %")
    spy_5d = value("SPY", "5D %")
    qqq_5d = value("QQQ", "5D %")
    vix_1d = value("^VIX", "1D %")

    score = 50
    score += 12 if spy_1d >= 0 else (-5 if spy_1d > -0.75 else -15)
    score += 12 if qqq_1d >= 0 else (-5 if qqq_1d > -0.75 else -15)
    score += 8 if spy_5d >= 0 else -8
    score += 8 if qqq_5d >= 0 else -8
    score += 10 if vix_1d <= 0 else (-5 if vix_1d < 3 else -15)
    score = int(max(0, min(100, score)))

    if score >= 65:
        return "GREEN", "Bullish", score, "Risk-on backdrop"
    if score >= 35:
        return "YELLOW", "Mixed", score, "Trade selectively; money flow matters more than index direction"
    return "RED", "Defensive", score, "Weak tape; only strongest money-flow names qualify"


# ============================================================
# INTRADAY / SETUP ENGINE
# ============================================================

def intraday_context(ticker):
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

    current = safe_num(df["Close"].iloc[-1])

    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    volume = safe_num(df["Volume"].sum())
    vwap = safe_num((typical * df["Volume"]).sum() / volume, current) if volume > 0 else current

    opening = df.head(3)
    or_high = safe_num(opening["High"].max())
    or_low = safe_num(opening["Low"].min())
    or_range = or_high - or_low
    or_position = (current - or_low) / or_range if or_range > 0 else 0.5

    if current > or_high:
        or_status = "Above OR High"
    elif current < or_low:
        or_status = "Below OR Low"
    else:
        or_status = "Inside OR"

    if or_position > 1:
        or_zone = "Breakout"
    elif or_position >= 0.80:
        or_zone = "Near breakout"
    elif or_position >= 0.60:
        or_zone = "Upper range"
    elif or_position >= 0.20:
        or_zone = "Middle"
    elif or_position >= 0:
        or_zone = "Near breakdown"
    else:
        or_zone = "Breakdown"

    above_vwap = current >= vwap

    if above_vwap and or_status == "Above OR High":
        trend = "Bullish ORB"
    elif above_vwap and or_zone in ["Near breakout", "Upper range"]:
        trend = "Constructive"
    elif not above_vwap and or_status == "Below OR Low":
        trend = "Bearish ORB"
    elif or_zone in ["Near breakdown", "Breakdown"]:
        trend = "Weak"
    else:
        trend = "Choppy"

    return {
        "Above VWAP": bool(above_vwap),
        "OR Zone": or_zone,
        "OR Status": or_status,
        "Intraday Trend": trend,
        "OR High": round(or_high, 2),
        "OR Low": round(or_low, 2),
        "VWAP": round(vwap, 2),
    }


def relative_strength(stock_df, spy_df):
    if stock_df.empty or spy_df.empty:
        return 50

    raw = ((pct_change(stock_df, 6) - pct_change(spy_df, 6)) * 2) + (
        pct_change(stock_df, 22) - pct_change(spy_df, 22)
    )

    return int(max(0, min(100, round(50 + raw))))


def gap_percent(df):
    if df.empty or len(df) < 2:
        return 0.0

    prior_close = safe_num(df["Close"].iloc[-2])
    today_open = safe_num(df["Open"].iloc[-1])

    if prior_close <= 0:
        return 0.0

    return round(((today_open / prior_close) - 1) * 100, 2)


def setup_tier(score):
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
    return {"A+": 1.0, "A": 0.75, "B": 0.50}.get(tier, 0.0)


def build_setup_scores(ctx):
    intra = ctx["intra"]
    light = ctx["market_light"]
    red_penalty = -5 if light == "RED" else 0
    green_bonus = 5 if light == "GREEN" else 0
    rs = ctx["rs"]
    rel_vol = ctx["rel_vol"]
    gp = ctx["gap"]
    above20 = ctx["above20"]
    above50 = ctx["above50"]
    dist20 = ctx["dist20"]

    orb = 0
    orb += {"Breakout": 35, "Near breakout": 28, "Upper range": 18}.get(intra["OR Zone"], 0)
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
    vwap += 20 if intra["Intraday Trend"] in ["Constructive", "Bullish ORB"] else 8 if intra["Intraday Trend"] == "Choppy" else 0
    vwap += 12 if above20 else 0
    vwap += 12 if above50 else 0
    vwap += 12 if -2 <= dist20 <= 10 else -12 if dist20 > 15 else 0
    vwap += 8 if rs >= 70 else 5 if rs >= 60 else 0
    vwap += 5 if rel_vol >= 1.0 else 0
    vwap += red_penalty

    gap = 0
    gap += 30 if gp >= 3 else 24 if gp >= 2 else 15 if gp >= 1 else -25 if gp <= -2 else 0
    gap += 25 if intra["Above VWAP"] else 0
    gap += 20 if intra["OR Zone"] in ["Breakout", "Near breakout", "Upper range"] else 0
    gap += 15 if rel_vol >= 1.5 else 8 if rel_vol >= 1.0 else 0
    gap += 10 if rs >= 70 else 5 if rs >= 60 else 0
    gap += red_penalty

    momentum = 0
    momentum += 30 if rs >= 80 else 24 if rs >= 70 else 15 if rs >= 60 else 0
    momentum += 18 if ctx["five_day"] > 5 else 12 if ctx["five_day"] > 3 else 5 if ctx["five_day"] > 0 else 0
    momentum += 18 if ctx["one_month"] > 12 else 12 if ctx["one_month"] > 8 else 5 if ctx["one_month"] > 0 else 0
    momentum += 10 if above20 else 0
    momentum += 10 if above50 else 0
    momentum += 8 if rel_vol >= 1.25 else 0
    momentum -= 10 if ctx["one_day"] > 8 else 0
    momentum -= 15 if dist20 > 18 else 8 if dist20 > 12 else 0
    momentum += green_bonus + red_penalty

    daily = 0
    daily += 35 if ctx["breakout"] else 25 if ctx["near_high"] else 0
    daily += 12 if above20 else 0
    daily += 12 if above50 else 0
    daily += 12 if rs >= 70 else 7 if rs >= 60 else 0
    daily += 12 if rel_vol >= 1.5 else 6 if rel_vol >= 1.0 else 0
    daily += green_bonus + red_penalty

    scores = {
        "ORB": orb,
        "VWAP": vwap,
        "Gap": gap,
        "Momentum": momentum,
        "Daily": daily,
    }

    return {k: int(max(0, min(100, v))) for k, v in scores.items()}


def analyze_symbol(ticker, spy_df, market_light, cash, risk_pct):
    df = get_data(ticker, "3mo", "1d")

    if df.empty or len(df) < 30:
        return None

    close = safe_num(df["Close"].iloc[-1])
    ma20 = safe_num(df["Close"].rolling(20).mean().iloc[-1], close)
    ma50 = safe_num(df["Close"].rolling(50).mean().iloc[-1], close)
    high20 = safe_num(df["High"].rolling(20).max().iloc[-2], close)
    low10 = safe_num(df["Low"].rolling(10).min().iloc[-1], close * 0.95)

    avg_vol = safe_num(df["Volume"].rolling(20).mean().iloc[-1])
    rel_vol = safe_num(df["Volume"].iloc[-1]) / avg_vol if avg_vol > 0 else 0

    ctx = {
        "ticker": ticker,
        "market_light": market_light,
        "intra": intraday_context(ticker),
        "one_day": pct_change(df, 2),
        "five_day": pct_change(df, 6),
        "one_month": pct_change(df, 22),
        "rel_vol": rel_vol,
        "above20": close >= ma20,
        "above50": close >= ma50,
        "dist20": ((close / ma20) - 1) * 100 if ma20 > 0 else 0,
        "breakout": close > high20,
        "near_high": abs((close / high20) - 1) * 100 <= 3 if high20 > 0 else False,
        "rs": relative_strength(df, spy_df),
        "gap": gap_percent(df),
    }

    scores = build_setup_scores(ctx)
    best_setup, best_score = sorted(scores.items(), key=lambda x: x[1], reverse=True)[0]
    tier = setup_tier(best_score)
    multiplier = risk_multiplier(tier)

    pattern = {
        "ORB": "Opening Range Breakout",
        "VWAP": "VWAP Reclaim / Hold",
        "Gap": "Gap-and-Go",
        "Momentum": "Relative Strength Continuation",
        "Daily": "Daily Breakout",
    }.get(best_setup, "No Clear Pattern")

    stop = round(max(low10, close * 0.94), 2)
    risk_per_share = max(0, close - stop)
    target1 = round(close + risk_per_share * 1.25, 2) if risk_per_share > 0 else round(close * 1.04, 2)
    target2 = round(close + risk_per_share * 2.0, 2) if risk_per_share > 0 else round(close * 1.08, 2)
    reward_risk = (target2 - close) / risk_per_share if risk_per_share > 0 else 0
    probability = int(max(0, min(95, round(35 + best_score * 0.55))))

    ev = ((probability / 100) * (target1 - close)) - ((1 - probability / 100) * risk_per_share) if risk_per_share > 0 else 0

    valid = (
        tier in ["A+", "A", "B"]
        and ev >= -0.10
        and risk_per_share > 0
        and reward_risk >= 1.20
        and ctx["intra"]["OR Status"] != "Below OR Low"
    )

    if market_light == "RED" and tier == "B" and ctx["rs"] < 60:
        valid = False

    if valid and tier in ["A+", "A"]:
        signal = "TRADE"
    elif valid and tier == "B":
        signal = "SMALL TRADE"
    elif tier == "C":
        signal = "WATCH"
    else:
        signal = "NO TRADE"

    shares = min((cash * risk_pct * multiplier) / risk_per_share, cash / close) if valid and risk_per_share > 0 and close > 0 else 0
    position = shares * close
    dollar_risk = shares * risk_per_share

    money_flow = int(max(0, min(100, round(
        (best_score * 0.35)
        + (ctx["rs"] * 0.25)
        + (min(rel_vol, 3) / 3 * 20)
        + (max(min(ctx["gap"], 5), -5) + 5)
        + (10 if ctx["intra"]["Above VWAP"] else 0)
    ))))

    reason_parts = []
    if ctx["intra"]["Above VWAP"]:
        reason_parts.append("Above VWAP")
    if ctx["intra"]["OR Zone"] in ["Breakout", "Near breakout", "Upper range"]:
        reason_parts.append(ctx["intra"]["OR Zone"])
    if ctx["rs"] >= 70:
        reason_parts.append("Strong RS")
    elif ctx["rs"] >= 60:
        reason_parts.append("Acceptable RS")
    if rel_vol >= 1.5:
        reason_parts.append("High relative volume")
    elif rel_vol >= 1.0:
        reason_parts.append("Volume active")
    if ctx["gap"] >= 2:
        reason_parts.append("Positive gap")
    if best_score >= 80:
        reason_parts.append(f"{best_setup} engine strong")

    reason = " + ".join(reason_parts) if reason_parts else "No dominant money-flow edge"

    # This is the app's own preliminary answer, not final trade instruction.
    if signal in ["TRADE", "SMALL TRADE"] and money_flow >= 65 and ctx["intra"]["Above VWAP"]:
        app_verdict = "TRADE CANDIDATE"
    elif signal in ["TRADE", "SMALL TRADE", "WATCH"] and money_flow >= 55:
        app_verdict = "WAIT FOR TRIGGER"
    else:
        app_verdict = "AVOID / WATCH ONLY"

    chart_needed = app_verdict in ["TRADE CANDIDATE", "WAIT FOR TRIGGER"]

    return {
        "Ticker": ticker,
        "Sector": SECTOR.get(ticker, "Other"),
        "Signal": signal,
        "App Verdict": app_verdict,
        "Chart Needed": chart_needed,
        "Best Setup": best_setup,
        "Pattern": pattern,
        "Tier": tier,
        "Best Score": best_score,
        "Money Flow Score": money_flow,
        "Reason": reason,
        "ORB Score": scores["ORB"],
        "VWAP Score": scores["VWAP"],
        "Gap Score": scores["Gap"],
        "Momentum Score": scores["Momentum"],
        "Daily Score": scores["Daily"],
        "Price": round(close, 2),
        "Probability %": probability,
        "RS Score": ctx["rs"],
        "Gap %": ctx["gap"],
        "1D %": ctx["one_day"],
        "5D %": ctx["five_day"],
        "1M %": ctx["one_month"],
        "Rel Vol": round(rel_vol, 2),
        "Above VWAP": ctx["intra"]["Above VWAP"],
        "VWAP": ctx["intra"]["VWAP"],
        "Intraday Trend": ctx["intra"]["Intraday Trend"],
        "OR Status": ctx["intra"]["OR Status"],
        "OR Zone": ctx["intra"]["OR Zone"],
        "OR High": ctx["intra"]["OR High"],
        "OR Low": ctx["intra"]["OR Low"],
        "Dist 20MA %": round(ctx["dist20"], 2),
        "Stop": stop,
        "Target 1": target1,
        "Target 2": target2,
        "Reward/Risk": round(reward_risk, 2),
        "EV / Share": round(ev, 2),
        "Risk Multiplier": multiplier,
        "Shares": round(shares, 4),
        "Position $": round(position, 2),
        "Dollar Risk": round(dollar_risk, 2),
    }


def run_scan(symbols, market_light, cash, risk_pct):
    spy_df = get_data("SPY", "3mo", "1d")
    rows = []
    seen = set()

    for symbol in symbols:
        symbol = symbol.strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        row = analyze_symbol(symbol, spy_df, market_light, cash, risk_pct)
        if row:
            rows.append(row)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values(
        ["Money Flow Score", "Best Score", "RS Score", "EV / Share"],
        ascending=False
    ).reset_index(drop=True)



# ============================================================
# CATALYST / NEWS ENGINE
# ============================================================

CATALYST_WEIGHTS = {
    "None / Unknown": 0,
    "Earnings beat": 35,
    "Earnings miss": -30,
    "Raised guidance": 35,
    "Lowered guidance": -35,
    "Analyst upgrade": 22,
    "Analyst downgrade": -25,
    "Price target raise": 14,
    "Price target cut": -18,
    "Major AI news": 28,
    "Major contract / partnership": 26,
    "Product launch": 16,
    "Sector sympathy strength": 14,
    "Sector sympathy weakness": -16,
    "Legal / regulatory risk": -30,
    "Dilution / offering risk": -35,
    "Management issue": -22,
    "Rumor / unconfirmed": 6,
}

def parse_catalyst_text(text):
    """
    Expected format:
    TICKER | catalyst type | freshness | note
    Example:
    CRDO | Raised guidance | Today | earnings beat and raised outlook
    """
    rows = []
    if not text or not text.strip():
        return pd.DataFrame(columns=["Ticker", "Catalyst Type", "Freshness", "Catalyst Note"])

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]

        ticker = parts[0].upper() if len(parts) >= 1 else ""
        catalyst_type = parts[1] if len(parts) >= 2 else "None / Unknown"
        freshness = parts[2] if len(parts) >= 3 else "Today"
        note = parts[3] if len(parts) >= 4 else ""

        if ticker:
            rows.append({
                "Ticker": ticker,
                "Catalyst Type": catalyst_type,
                "Freshness": freshness,
                "Catalyst Note": note,
            })

    return pd.DataFrame(rows)


def catalyst_freshness_multiplier(freshness):
    f = str(freshness).strip().lower()

    if f in ["today", "same day", "premarket", "intraday"]:
        return 1.00
    if f in ["yesterday", "1 day", "last night"]:
        return 0.80
    if f in ["this week", "2-5 days", "recent"]:
        return 0.55
    if f in ["older", "last week", "stale"]:
        return 0.25

    return 0.60


def catalyst_score(catalyst_type, freshness):
    base = CATALYST_WEIGHTS.get(str(catalyst_type).strip(), 0)
    mult = catalyst_freshness_multiplier(freshness)
    raw = base * mult

    # Convert into 0-100 scale where 50 = neutral.
    return int(max(0, min(100, round(50 + raw))))


def catalyst_bias(catalyst_score_value):
    # Converts 0-100 catalyst score into ranking adjustment.
    # Neutral 50 = 0. Positive catalysts help; negative catalysts hurt.
    return round((catalyst_score_value - 50) * 0.45, 2)


def apply_catalysts(scan, catalyst_df):
    scan = scan.copy()

    if catalyst_df is None or catalyst_df.empty:
        scan["Catalyst Type"] = "None / Unknown"
        scan["Catalyst Freshness"] = "None"
        scan["Catalyst Note"] = ""
        scan["Catalyst Score"] = 50
        scan["Catalyst Bias"] = 0.0
    else:
        catalyst_df = catalyst_df.copy()
        catalyst_df["Ticker"] = catalyst_df["Ticker"].astype(str).str.upper().str.strip()

        # If duplicates exist, keep the last entered line so user can override quickly.
        catalyst_df = catalyst_df.drop_duplicates(subset=["Ticker"], keep="last")

        scan = scan.merge(catalyst_df, how="left", on="Ticker")
        scan["Catalyst Type"] = scan["Catalyst Type"].fillna("None / Unknown")
        scan["Freshness"] = scan["Freshness"].fillna("None")
        scan["Catalyst Note"] = scan["Catalyst Note"].fillna("")

        scan["Catalyst Score"] = scan.apply(
            lambda r: catalyst_score(r["Catalyst Type"], r["Freshness"]),
            axis=1,
        )
        scan["Catalyst Freshness"] = scan["Freshness"]
        scan = scan.drop(columns=["Freshness"], errors="ignore")
        scan["Catalyst Bias"] = scan["Catalyst Score"].apply(catalyst_bias)

    scan["Total Opportunity Score"] = (
        (scan["Money Flow Score"] * 0.45)
        + (scan["Best Score"] * 0.25)
        + (scan["RS Score"] * 0.15)
        + (scan["Catalyst Score"] * 0.15)
    ).round(1)

    # Catalyst upgrades/downgrades the app verdict only when technical structure is not broken.
    upgraded = []
    for _, row in scan.iterrows():
        verdict = row["App Verdict"]

        if row["Catalyst Score"] >= 75 and row["Money Flow Score"] >= 58 and row["OR Status"] != "Below OR Low":
            if verdict == "AVOID / WATCH ONLY":
                verdict = "WAIT FOR TRIGGER"
            elif verdict == "WAIT FOR TRIGGER" and row["Signal"] in ["TRADE", "SMALL TRADE"]:
                verdict = "TRADE CANDIDATE"

        if row["Catalyst Score"] <= 25:
            if verdict == "TRADE CANDIDATE":
                verdict = "WAIT FOR TRIGGER"
            elif verdict == "WAIT FOR TRIGGER":
                verdict = "AVOID / WATCH ONLY"

        upgraded.append(verdict)

    scan["Catalyst-Adjusted Verdict"] = upgraded

    scan = scan.sort_values(
        ["Total Opportunity Score", "Catalyst Score", "Money Flow Score", "Best Score", "RS Score"],
        ascending=False,
    ).reset_index(drop=True)

    return scan


def catalyst_summary(scan):
    if scan.empty or "Catalyst Score" not in scan.columns:
        return "No catalyst data entered."

    catalyst_names = scan[scan["Catalyst Type"] != "None / Unknown"].copy()

    if catalyst_names.empty:
        return "No manual catalysts entered. Rankings are technical/money-flow only."

    lines = []
    lines.append("CATALYST SUMMARY")
    for _, row in catalyst_names.head(10).iterrows():
        lines.append(
            f"- {row['Ticker']}: {row['Catalyst Type']} / {row['Catalyst Freshness']} "
            f"/ score {row['Catalyst Score']} / note: {row['Catalyst Note']}"
        )

    return "\n".join(lines)


# ============================================================
# PACKETS / SUMMARY
# ============================================================

def sector_flow(scan):
    sec = scan.groupby("Sector").agg(
        Names=("Ticker", "count"),
        Tradeable=("Signal", lambda x: x.isin(["TRADE", "SMALL TRADE"]).sum()),
        Avg_Flow=("Money Flow Score", "mean"),
        Avg_Setup=("Best Score", "mean"),
        Avg_RS=("RS Score", "mean"),
        Avg_EV=("EV / Share", "mean"),
    ).reset_index()

    for col in ["Avg_Flow", "Avg_Setup", "Avg_RS", "Avg_EV"]:
        sec[col] = sec[col].round(2)

    return sec.sort_values(["Tradeable", "Avg_Flow", "Avg_RS"], ascending=False)


def safe_records(df):
    if df is None or df.empty:
        return []
    return df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), None).to_dict(orient="records")


def build_snapshot(scan, market_df, light, regime, score, reason):
    tradeable = scan[scan["Signal"].isin(["TRADE", "SMALL TRADE"])]
    candidates = scan[scan["Catalyst-Adjusted Verdict"].isin(["TRADE CANDIDATE", "WAIT FOR TRIGGER"])]
    no_trade = scan[~scan["Signal"].isin(["TRADE", "SMALL TRADE"])]

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market": {
            "light": light,
            "regime": regime,
            "score": int(score),
            "reason": reason,
            "context": safe_records(market_df),
        },
        "top_flow_name": scan.iloc[0].to_dict(),
        "top_tradeable_name": tradeable.iloc[0].to_dict() if not tradeable.empty else None,
        "top_candidate": candidates.iloc[0].to_dict() if not candidates.empty else None,
        "tradeable_count": int(len(tradeable)),
        "candidate_count": int(len(candidates)),
        "scanned_count": int(len(scan)),
        "top_3": safe_records(scan.head(3)),
        "top_10": safe_records(scan.head(10)),
        "sector_flow": safe_records(sector_flow(scan)),
        "no_trade_watch": safe_records(no_trade.head(10)),
    }


def make_trader_briefing(snapshot):
    m = snapshot["market"]
    candidate = snapshot["top_candidate"]
    top_trade = snapshot["top_tradeable_name"]
    top_flow = snapshot["top_flow_name"]

    lines = []
    lines.append("TRADER BRIEFING v26")
    lines.append(f"Time: {snapshot['timestamp']}")
    lines.append(f"Market: {m['light']} {m['score']}/100 - {m['regime']}")
    lines.append(f"Market reason: {m['reason']}")
    lines.append(f"Tradeable names: {snapshot['tradeable_count']} of {snapshot['scanned_count']}")
    lines.append(f"Close candidates needing chart review: {snapshot['candidate_count']} of {snapshot['scanned_count']}")
    lines.append("")
    lines.append(catalyst_summary(pd.DataFrame(snapshot["top_10"])))
    lines.append("")

    if candidate:
        lines.append("PRIMARY CANDIDATE")
        lines.append(f"Ticker: {candidate['Ticker']}")
        lines.append(f"Technical verdict: {candidate['App Verdict']}")
        lines.append(f"Catalyst-adjusted verdict: {candidate['Catalyst-Adjusted Verdict']}")
        lines.append(f"Signal: {candidate['Signal']}")
        lines.append(f"Tier/setup: {candidate['Tier']} {candidate['Best Setup']}")
        lines.append(f"Pattern: {candidate['Pattern']}")
        lines.append(f"Total Opportunity Score: {candidate['Total Opportunity Score']}")
        lines.append(f"Money Flow Score: {candidate['Money Flow Score']}")
        lines.append(f"Catalyst Score: {candidate['Catalyst Score']}")
        lines.append(f"Catalyst: {candidate['Catalyst Type']} / {candidate['Catalyst Freshness']} / {candidate['Catalyst Note']}")
        lines.append(f"Best Setup Score: {candidate['Best Score']}")
        lines.append(f"Probability: {candidate['Probability %']}%")
        lines.append(f"Entry reference: {candidate['Price']}")
        lines.append(f"Stop: {candidate['Stop']}")
        lines.append(f"Target 1: {candidate['Target 1']}")
        lines.append(f"Target 2: {candidate['Target 2']}")
        lines.append(f"Shares: {candidate['Shares']}")
        lines.append(f"Position size: ${candidate['Position $']}")
        lines.append(f"Max dollar risk: ${candidate['Dollar Risk']}")
        lines.append(f"Reward/Risk: {candidate['Reward/Risk']}")
        lines.append(f"EV/share: {candidate['EV / Share']}")
        lines.append(f"VWAP: {candidate['Above VWAP']} at {candidate['VWAP']}")
        lines.append(f"OR status: {candidate['OR Status']} / {candidate['OR Zone']}")
        lines.append(f"RS Score: {candidate['RS Score']}")
        lines.append(f"Relative volume: {candidate['Rel Vol']}")
        lines.append(f"Reason: {candidate['Reason']}")
        lines.append(f"Chart screenshot needed: {candidate['Chart Needed']}")
    elif top_trade:
        lines.append("PRIMARY CANDIDATE")
        lines.append(f"Ticker: {top_trade['Ticker']}")
        lines.append(f"Dashboard verdict: {top_trade['App Verdict']}")
        lines.append(f"Signal: {top_trade['Signal']}")
        lines.append(f"Reason: {top_trade['Reason']}")
    else:
        lines.append("PRIMARY CANDIDATE")
        lines.append("None approved yet.")
        lines.append(f"Strongest flow: {top_flow['Ticker']} / {top_flow['Best Setup']}")
        lines.append(f"Flow score: {top_flow['Money Flow Score']}")
        lines.append(f"Reason: {top_flow['Reason']}")

    lines.append("")
    lines.append("TOP 3 TO WATCH")
    for i, row in enumerate(snapshot["top_3"], 1):
        lines.append(
            f"{i}. {row['Ticker']} | {row['App Verdict']} | {row['Signal']} | "
            f"{row['Tier']} {row['Best Setup']} | Flow {row['Money Flow Score']} | "
            f"Price {row['Price']} | Stop {row['Stop']} | Risk ${row['Dollar Risk']} | "
            f"Chart needed {row['Chart Needed']} | {row['Reason']}"
        )

    lines.append("")
    lines.append("CHATGPT RESPONSE FORMAT REQUEST")
    lines.append("Give me exactly one answer: TRADE, WAIT, or AVOID.")
    lines.append("If TRADE: verify entry, stop, target, shares, max loss, and invalidation.")
    lines.append("If WAIT: tell me the exact trigger required.")
    lines.append("If AVOID: tell me the exact reason and which ticker remains on watch.")

    return "\n".join(lines)


def make_full_packet(snapshot):
    lines = []
    lines.append("DEON TRADER DASHBOARD v26 - FULL DECISION PACKET")
    lines.append(f"Timestamp: {snapshot['timestamp']}")
    m = snapshot["market"]
    lines.append("")
    lines.append(f"MARKET: {m['light']} {m['score']}/100 - {m['regime']} - {m['reason']}")
    for row in m["context"]:
        lines.append(f"- {row['Market']}: {row['Price']} | 1D {row['1D %']}% | 5D {row['5D %']}% | {row['Trend']}")

    lines.append("")
    lines.append("TOP 10 RANKED")
    for i, row in enumerate(snapshot["top_10"], 1):
        lines.append(
            f"{i}. {row['Ticker']} | {row['Catalyst-Adjusted Verdict']} | {row['Signal']} | {row['Tier']} {row['Best Setup']} | "
            f"Total {row['Total Opportunity Score']} | Catalyst {row['Catalyst Score']} | Flow {row['Money Flow Score']} | Setup {row['Best Score']} | RS {row['RS Score']} | "
            f"EV {row['EV / Share']} | VWAP {row['Above VWAP']} | OR {row['OR Zone']} | Reason: {row['Reason']}"
        )

    lines.append("")
    lines.append("SECTOR FLOW")
    for i, row in enumerate(snapshot["sector_flow"][:8], 1):
        lines.append(
            f"{i}. {row['Sector']} | Tradeable {row['Tradeable']} | Avg Flow {row['Avg_Flow']} | "
            f"Avg Setup {row['Avg_Setup']} | Avg RS {row['Avg_RS']} | Avg EV {row['Avg_EV']}"
        )

    return "\n".join(lines)


def df_csv(df):
    return df.to_csv(index=False).encode("utf-8")


# ============================================================
# VISUALS
# ============================================================

def make_chart(ticker, timeframe):
    if timeframe == "5m":
        df = get_data(ticker, "1d", "5m")
    elif timeframe == "15m":
        df = get_data(ticker, "5d", "15m")
    else:
        df = get_data(ticker, "3mo", "1d")

    if df.empty:
        return None

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name=ticker,
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"].rolling(20).mean(),
        mode="lines",
        name="20MA",
    ))

    if timeframe == "5m" and len(df) >= 3:
        fig.add_hline(y=df.head(3)["High"].max(), line_dash="dash", annotation_text="OR High")
        fig.add_hline(y=df.head(3)["Low"].min(), line_dash="dash", annotation_text="OR Low")

    fig.update_layout(height=550, xaxis_rangeslider_visible=False)
    return fig


# ============================================================
# APP
# ============================================================

st.title("Deon's Trader Dashboard v26")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.sidebar.header("Settings")
watchlist_text = st.sidebar.text_area("Manual Watchlist", ",".join(DEFAULT_WATCHLIST), height=90)
scan_text = st.sidebar.text_area("Scanner Universe", ",".join(DEFAULT_SCAN), height=170)

st.sidebar.subheader("Manual News / Catalyst Input")
catalyst_text = st.sidebar.text_area(
    "One per line: TICKER | Catalyst Type | Freshness | Note",
    value="",
    height=150,
    help="Example: CRDO | Raised guidance | Today | earnings beat and raised outlook"
)

with st.sidebar.expander("Allowed catalyst types"):
    st.write(", ".join(CATALYST_WEIGHTS.keys()))
cash = st.sidebar.number_input("Cash available", min_value=0.0, value=855.0, step=25.0)
risk_pct = st.sidebar.number_input("Base risk per trade %", min_value=0.25, max_value=10.0, value=3.0, step=0.25) / 100

st.sidebar.write("A+ max risk:", f"${cash * risk_pct:,.2f}")
st.sidebar.write("A max risk:", f"${cash * risk_pct * 0.75:,.2f}")
st.sidebar.write("B max risk:", f"${cash * risk_pct * 0.50:,.2f}")

if st.sidebar.button("Refresh now"):
    st.cache_data.clear()
    st.rerun()

market_df = market_context()
light, regime, market_score, market_reason = market_state(market_df)

symbols = [x.strip().upper() for x in scan_text.split(",") if x.strip()]

with st.spinner("Scanning money flow, catalysts, and building ChatGPT briefing..."):
    base_scan = run_scan(symbols, light, cash, risk_pct)
    catalyst_df = parse_catalyst_text(catalyst_text)
    scan = apply_catalysts(base_scan, catalyst_df)

if scan.empty:
    st.error("No data loaded. Try fewer tickers, wait one minute, then refresh.")
    st.stop()

snapshot = build_snapshot(scan, market_df, light, regime, market_score, market_reason)
briefing = make_trader_briefing(snapshot)
full_packet = make_full_packet(snapshot)

# ============================================================
# 10/10 COMMAND CENTER
# ============================================================

st.header("Step 1 — Copy This Trader Briefing")
st.success("This is the main v25 workflow. Copy this box into ChatGPT first. Do not send screenshots unless the briefing says a chart is needed.")
st.text_area("Trader Briefing for ChatGPT", briefing, height=430)

c1, c2, c3 = st.columns(3)
c1.download_button("Download Trader Briefing TXT", data=briefing.encode("utf-8"), file_name="trader_briefing_v26.txt", mime="text/plain")
c2.download_button("Download Full Packet TXT", data=full_packet.encode("utf-8"), file_name="full_decision_packet_v26.txt", mime="text/plain")
c3.download_button("Download Top 10 CSV", data=df_csv(scan.head(10)), file_name="top10_v26.csv", mime="text/csv")

st.header("Step 2 — Dashboard's Preliminary Answer")
top_candidate = snapshot["top_candidate"]
tradeable = scan[scan["Signal"].isin(["TRADE", "SMALL TRADE"])]

if top_candidate:
    if top_candidate["Catalyst-Adjusted Verdict"] == "TRADE CANDIDATE":
        st.success(f"TRADE CANDIDATE: {top_candidate['Ticker']} — catalyst-adjusted. Paste the briefing into ChatGPT for final verification.")
    elif top_candidate["Catalyst-Adjusted Verdict"] == "WAIT FOR TRIGGER":
        st.warning(f"WAIT FOR TRIGGER: {top_candidate['Ticker']} is close but needs confirmation.")
    else:
        st.error("AVOID / WATCH ONLY")
else:
    st.error("NO PRIMARY CANDIDATE. Stay patient unless the dashboard changes.")

st.write("Chart screenshot rule:")
if top_candidate and top_candidate["Chart Needed"]:
    st.warning(f"Chart likely needed for {top_candidate['Ticker']} if you want final entry confirmation.")
else:
    st.info("No chart screenshot needed yet. Paste the Trader Briefing first.")

# ============================================================
# MARKET SUMMARY
# ============================================================

st.header("Market")
st.dataframe(market_df, use_container_width=True)

if light == "GREEN":
    st.success(f"{light} - {regime}")
elif light == "YELLOW":
    st.warning(f"{light} - {regime}")
else:
    st.error(f"{light} - {regime}")

st.progress(market_score)
st.caption(market_reason)

# ============================================================
# MONEY FLOW
# ============================================================

st.header("Money Flow Dashboard")
top_flow = scan.iloc[0]
top_trade = tradeable.iloc[0] if not tradeable.empty else None

if top_trade is not None:
    st.success(f"Top tradeable: {top_trade['Ticker']} — {top_trade['Tier']} {top_trade['Best Setup']} — {top_trade['Signal']}")
else:
    st.error(f"No approved trade yet. Strongest flow: {top_flow['Ticker']}")

a, b, c, d = st.columns(4)
a.metric("Tradeable Names", len(tradeable))
b.metric("Close Candidates", snapshot["candidate_count"])
c.metric("Strongest Flow", top_flow["Ticker"])
d.metric("Top Flow Score", top_flow["Money Flow Score"])

st.subheader("Top 3 Money Flow")
st.dataframe(
    scan.head(3)[[
        "Ticker", "Sector", "Catalyst-Adjusted Verdict", "Signal", "Tier", "Best Setup",
        "Total Opportunity Score", "Catalyst Score", "Catalyst Type", "Money Flow Score", "Best Score", "Reason", "Price", "Stop",
        "Target 1", "Shares", "Position $", "Dollar Risk", "Chart Needed"
    ]],
    use_container_width=True,
)

# ============================================================
# TABS
# ============================================================

tabs = st.tabs([
    "Money Flow Board",
    "Trade Plan",
    "Full Packet",
    "Sector Flow",
    "Engine Scores",
    "No Trade / Watch",
    "Participation",
    "Catalysts",
    "Charts",
])

with tabs[0]:
    st.header("Ranked Money Flow Board")
    ranked = scan.head(25).copy()
    ranked.insert(0, "Rank", range(1, len(ranked) + 1))
    st.dataframe(
        ranked[[
            "Rank", "Ticker", "Sector", "Catalyst-Adjusted Verdict", "Signal", "Tier", "Best Setup",
            "Total Opportunity Score", "Catalyst Score", "Catalyst Type", "Money Flow Score", "Best Score", "Reason", "Price", "Probability %",
            "EV / Share", "Position $", "Dollar Risk", "Above VWAP", "OR Zone", "RS Score"
        ]],
        use_container_width=True,
        height=600,
    )

    manual = [x.strip().upper() for x in watchlist_text.split(",") if x.strip()]
    st.subheader("Manual Watchlist")
    st.dataframe(scan[scan["Ticker"].isin(manual)], use_container_width=True, height=320)

with tabs[1]:
    st.header("Trade Plan")
    selected = st.selectbox("Select opportunity", scan["Ticker"].tolist())
    row = scan[scan["Ticker"] == selected].iloc[0]

    if row["Catalyst-Adjusted Verdict"] == "TRADE CANDIDATE":
        st.success(f"{row['Ticker']} is a catalyst-adjusted trade candidate pending ChatGPT/chart verification.")
    elif row["Catalyst-Adjusted Verdict"] == "WAIT FOR TRIGGER":
        st.warning(f"{row['Ticker']} is close, but waiting for trigger.")
    else:
        st.error(f"{row['Ticker']} is not trade-ready.")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Ticker", row["Ticker"])
    m2.metric("Verdict", row["Catalyst-Adjusted Verdict"])
    m3.metric("Setup", row["Best Setup"])
    m4.metric("Tier", row["Tier"])
    m5.metric("Flow", row["Money Flow Score"])

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Entry Ref", f"${row['Price']:.2f}")
    p2.metric("Stop", f"${row['Stop']:.2f}")
    p3.metric("Target 1", f"${row['Target 1']:.2f}")
    p4.metric("Target 2", f"${row['Target 2']:.2f}")

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Shares", f"{row['Shares']:.4f}")
    r2.metric("Position $", f"${row['Position $']:,.2f}")
    r3.metric("Dollar Risk", f"${row['Dollar Risk']:,.2f}")
    r4.metric("Reward/Risk", f"{row['Reward/Risk']:.2f}")

    st.write(f"Reason: **{row['Reason']}**")
    st.write(f"Catalyst: **{row['Catalyst Type']}** / **{row['Catalyst Freshness']}** / Score **{row['Catalyst Score']}**")
    st.write(f"VWAP: **{row['Above VWAP']}** at {row['VWAP']}")
    st.write(f"Opening Range: **{row['OR Status']} / {row['OR Zone']}**")
    st.write(f"Chart screenshot needed: **{row['Chart Needed']}**")

with tabs[2]:
    st.header("Full Decision Packet")
    st.text_area("Full Packet for Deep Review", full_packet, height=560)
    st.download_button("Download Snapshot JSON", data=json.dumps(snapshot, indent=2, default=str).encode("utf-8"), file_name="snapshot_v26.json", mime="application/json")

with tabs[3]:
    st.header("Sector Flow")
    sectors = sector_flow(scan)
    st.dataframe(sectors, use_container_width=True)
    if not sectors.empty:
        leader_sector = sectors.iloc[0]["Sector"]
        st.subheader(f"Leaders in strongest sector: {leader_sector}")
        st.dataframe(scan[scan["Sector"] == leader_sector].head(5), use_container_width=True)

with tabs[4]:
    st.header("Engine Scores")
    st.dataframe(
        scan[[
            "Ticker", "Sector", "Catalyst-Adjusted Verdict", "Signal", "Tier", "Best Setup",
            "Total Opportunity Score", "Catalyst Score", "Catalyst Type", "Money Flow Score", "Best Score", "ORB Score", "VWAP Score", "Gap Score",
            "Momentum Score", "Daily Score", "RS Score", "EV / Share"
        ]],
        use_container_width=True,
        height=560,
    )

with tabs[5]:
    st.header("No Trade / Watch")
    no_trade = scan[~scan["Signal"].isin(["TRADE", "SMALL TRADE"])]
    st.dataframe(
        no_trade[[
            "Ticker", "Catalyst-Adjusted Verdict", "Signal", "Tier", "Best Setup", "Total Opportunity Score", "Catalyst Score", "Money Flow Score",
            "Best Score", "Reason", "Price", "EV / Share", "Reward/Risk",
            "Above VWAP", "OR Status", "OR Zone", "RS Score"
        ]],
        use_container_width=True,
        height=500,
    )

with tabs[6]:
    st.header("Participation Target")
    participation = len(tradeable) / len(scan) * 100 if len(scan) else 0
    x1, x2, x3, x4 = st.columns(4)
    x1.metric("Tradeable %", f"{participation:.1f}%")
    x2.metric("Tradeable Names", len(tradeable))
    x3.metric("Close Candidates", snapshot["candidate_count"])
    x4.metric("Scanned Names", len(scan))

    if participation >= 70:
        st.success("High participation. Use discipline: only take the top-ranked confirmed setup.")
    elif participation >= 40:
        st.warning("Moderate participation. This is probably a healthy balance.")
    else:
        st.error("Low participation. Conditions are still selective.")

with tabs[7]:
    st.header("Catalyst & News Engine")
    st.write("Manual catalyst entries affect Total Opportunity Score and Catalyst-Adjusted Verdict.")
    st.dataframe(
        scan[[
            "Ticker", "Catalyst-Adjusted Verdict", "Catalyst Type", "Catalyst Freshness",
            "Catalyst Score", "Catalyst Bias", "Catalyst Note",
            "Total Opportunity Score", "Money Flow Score", "Best Setup", "Signal"
        ]],
        use_container_width=True,
        height=520,
    )
    st.subheader("How to enter catalysts")
    st.code("CRDO | Raised guidance | Today | earnings beat and raised outlook\nPLTR | Major contract / partnership | Yesterday | defense AI contract\nNVDA | Analyst upgrade | Today | price target raised")

with tabs[8]:
    st.header("Charts")
    default_chart = top_candidate["Ticker"] if top_candidate else scan.iloc[0]["Ticker"]
    tickers = scan["Ticker"].tolist()
    index = tickers.index(default_chart) if default_chart in tickers else 0
    selected_chart = st.selectbox("Ticker", tickers, index=index)
    timeframe = st.radio("Timeframe", ["5m", "15m", "Daily"], horizontal=True)
    fig = make_chart(selected_chart, timeframe)

    if fig is None:
        st.warning("Chart unavailable.")
    else:
        st.plotly_chart(fig, use_container_width=True)

st.caption("v26 adds a Catalyst & News Engine: copy briefing first, include catalyst context, chart only when needed, decision format is TRADE / WAIT / AVOID.")
