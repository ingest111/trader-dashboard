
import json
from datetime import datetime, date
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
import requests

# ============================================================
# DEON'S TRADER DASHBOARD v31
# BROKER EXECUTION INFRASTRUCTURE BUILD
#
# Goal:
# - Make the "10/10" workflow happen inside the app.
# - No routine screenshots.
# - One short briefing for ChatGPT.
# - One full packet for deeper review.
# - Explicit TRADE / WAIT / AVOID operating logic.
# - Chart screenshot only when a setup is close.
# ============================================================

st.set_page_config(page_title="Deon's Trader Dashboard v32", layout="wide")

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


POSITIVE_NEWS_KEYWORDS = {
    "earnings beat": 30,
    "beats estimates": 28,
    "beat estimates": 28,
    "raises guidance": 35,
    "raised guidance": 35,
    "strong guidance": 30,
    "upgrade": 22,
    "upgraded": 22,
    "price target raised": 18,
    "raises price target": 18,
    "contract": 20,
    "partnership": 20,
    "collaboration": 14,
    "ai": 14,
    "artificial intelligence": 14,
    "data center": 16,
    "semiconductor": 10,
    "record revenue": 22,
    "surges": 16,
    "jumps": 14,
    "buy rating": 14,
    "outperform": 14,
}

NEGATIVE_NEWS_KEYWORDS = {
    "earnings miss": -30,
    "misses estimates": -28,
    "missed estimates": -28,
    "lowers guidance": -35,
    "lowered guidance": -35,
    "cuts guidance": -35,
    "downgrade": -25,
    "downgraded": -25,
    "price target cut": -20,
    "cuts price target": -20,
    "sec investigation": -35,
    "investigation": -22,
    "lawsuit": -18,
    "offering": -32,
    "share offering": -35,
    "dilution": -35,
    "resigns": -18,
    "weak demand": -22,
    "falls": -12,
    "plunges": -22,
    "sell rating": -18,
    "underperform": -18,
}


@st.cache_data(ttl=900)
def fetch_ticker_news(ticker, max_items=6):
    """
    Free catalyst source using yfinance ticker.news.
    Limitations:
    - Not guaranteed complete
    - Can be delayed
    - Sometimes returns generic market news
    - Still better than ignoring catalysts entirely
    """
    try:
        tk = yf.Ticker(ticker)
        items = tk.news or []
        rows = []

        for item in items[:max_items]:
            title = item.get("title", "") or ""
            publisher = item.get("publisher", "") or ""
            link = item.get("link", "") or ""
            provider_time = item.get("providerPublishTime", None)

            published = ""
            if provider_time:
                try:
                    published = datetime.fromtimestamp(provider_time).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    published = ""

            rows.append({
                "Ticker": ticker,
                "News Title": title,
                "Publisher": publisher,
                "Published": published,
                "Link": link,
            })

        return pd.DataFrame(rows)

    except Exception:
        return pd.DataFrame(columns=["Ticker", "News Title", "Publisher", "Published", "Link"])


def score_news_titles(news_df):
    if news_df is None or news_df.empty:
        return {
            "Auto Catalyst Type": "None / Unknown",
            "Auto Catalyst Score": 50,
            "Auto Catalyst Note": "No recent Yahoo Finance news pulled",
            "News Headlines": "",
        }

    all_titles = " | ".join(news_df["News Title"].fillna("").astype(str).tolist())
    text = all_titles.lower()

    raw = 0
    hits = []

    for key, value in POSITIVE_NEWS_KEYWORDS.items():
        if key in text:
            raw += value
            hits.append(key)

    for key, value in NEGATIVE_NEWS_KEYWORDS.items():
        if key in text:
            raw += value
            hits.append(key)

    raw = max(-45, min(45, raw))
    score = int(max(0, min(100, 50 + raw)))

    if score >= 80:
        ctype = "Strong positive news"
    elif score >= 65:
        ctype = "Positive news"
    elif score <= 20:
        ctype = "Strong negative news"
    elif score <= 35:
        ctype = "Negative news"
    else:
        ctype = "Neutral / unclear news"

    note = ", ".join(hits[:8]) if hits else "News found, but no strong catalyst keywords detected"

    return {
        "Auto Catalyst Type": ctype,
        "Auto Catalyst Score": score,
        "Auto Catalyst Note": note,
        "News Headlines": all_titles[:1000],
    }


def build_auto_catalysts(symbols, enabled=True, max_symbols=12):
    """
    Pulls Yahoo Finance news for only the first N scanned tickers to avoid slow dashboard loads.
    User can prioritize tickers by ordering Scanner Universe in sidebar.
    """
    if not enabled:
        return pd.DataFrame(columns=[
            "Ticker", "Auto Catalyst Type", "Auto Catalyst Score",
            "Auto Catalyst Note", "News Headlines"
        ])

    rows = []
    seen = set()

    for symbol in symbols[:max_symbols]:
        symbol = symbol.strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)

        news_df = fetch_ticker_news(symbol)
        scored = score_news_titles(news_df)
        scored["Ticker"] = symbol
        rows.append(scored)

    if not rows:
        return pd.DataFrame(columns=[
            "Ticker", "Auto Catalyst Type", "Auto Catalyst Score",
            "Auto Catalyst Note", "News Headlines"
        ])

    return pd.DataFrame(rows)


def combine_manual_and_auto_catalysts(manual_df, auto_df):
    """
    Manual catalyst overrides are stronger than automatic news guesses.
    If manual exists for a ticker, use manual score as primary.
    If not, use auto score.
    """
    manual_df = manual_df.copy() if manual_df is not None else pd.DataFrame()
    auto_df = auto_df.copy() if auto_df is not None else pd.DataFrame()

    if manual_df.empty and auto_df.empty:
        return pd.DataFrame(columns=[
            "Ticker", "Catalyst Type", "Freshness", "Catalyst Note",
            "Auto Catalyst Type", "Auto Catalyst Score", "Auto Catalyst Note", "News Headlines",
            "Catalyst Source"
        ])

    if manual_df.empty:
        out = auto_df.copy()
        out["Catalyst Type"] = out["Auto Catalyst Type"]
        out["Freshness"] = "Auto"
        out["Catalyst Note"] = out["Auto Catalyst Note"]
        out["Catalyst Source"] = "Auto news"
        return out

    manual_df["Ticker"] = manual_df["Ticker"].astype(str).str.upper().str.strip()
    manual_df["Catalyst Source"] = "Manual override"

    if auto_df.empty:
        manual_df["Auto Catalyst Type"] = "None / Unknown"
        manual_df["Auto Catalyst Score"] = 50
        manual_df["Auto Catalyst Note"] = ""
        manual_df["News Headlines"] = ""
        return manual_df

    auto_df["Ticker"] = auto_df["Ticker"].astype(str).str.upper().str.strip()

    merged = auto_df.merge(
        manual_df,
        on="Ticker",
        how="outer",
        suffixes=("_auto", "_manual")
    )

    rows = []
    for _, r in merged.iterrows():
        ticker = r["Ticker"]

        manual_type = r.get("Catalyst Type", np.nan)
        has_manual = pd.notna(manual_type) and str(manual_type).strip() != ""

        if has_manual:
            rows.append({
                "Ticker": ticker,
                "Catalyst Type": r.get("Catalyst Type", "None / Unknown"),
                "Freshness": r.get("Freshness", "Today"),
                "Catalyst Note": r.get("Catalyst Note", ""),
                "Auto Catalyst Type": r.get("Auto Catalyst Type", "None / Unknown"),
                "Auto Catalyst Score": r.get("Auto Catalyst Score", 50),
                "Auto Catalyst Note": r.get("Auto Catalyst Note", ""),
                "News Headlines": r.get("News Headlines", ""),
                "Catalyst Source": "Manual override",
            })
        else:
            rows.append({
                "Ticker": ticker,
                "Catalyst Type": r.get("Auto Catalyst Type", "None / Unknown"),
                "Freshness": "Auto",
                "Catalyst Note": r.get("Auto Catalyst Note", ""),
                "Auto Catalyst Type": r.get("Auto Catalyst Type", "None / Unknown"),
                "Auto Catalyst Score": r.get("Auto Catalyst Score", 50),
                "Auto Catalyst Note": r.get("Auto Catalyst Note", ""),
                "News Headlines": r.get("News Headlines", ""),
                "Catalyst Source": "Auto news",
            })

    return pd.DataFrame(rows)


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
    if f in ["auto", "automatic", "yahoo"]:
        return 1.00

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
        scan["Auto Catalyst Type"] = scan.get("Auto Catalyst Type", "None / Unknown")
        scan["Auto Catalyst Score"] = scan.get("Auto Catalyst Score", 50)
        scan["Auto Catalyst Note"] = scan.get("Auto Catalyst Note", "")
        scan["News Headlines"] = scan.get("News Headlines", "")
        scan["Catalyst Source"] = scan.get("Catalyst Source", "None")

        scan["Catalyst Score"] = scan.apply(
            lambda r: int(r["Auto Catalyst Score"]) if str(r.get("Catalyst Source", "")).lower() == "auto news" and pd.notna(r.get("Auto Catalyst Score", np.nan)) else catalyst_score(r["Catalyst Type"], r["Freshness"]),
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



def parse_external_signals(text):
    """
    Expected format:
    TICKER | Source | Score | Note
    Examples:
    NVDA | FinancialJuice | 75 | semis positive after macro headline
    PLTR | X sentiment | 80 | strong AI contract chatter
    AMD | TradingView | 70 | premarket relative volume strong
    """
    rows = []
    if not text or not text.strip():
        return pd.DataFrame(columns=["Ticker", "External Source", "External Score", "External Note"])

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        ticker = parts[0].upper() if len(parts) >= 1 else ""
        source = parts[1] if len(parts) >= 2 else "External"
        score = parts[2] if len(parts) >= 3 else "50"
        note = parts[3] if len(parts) >= 4 else ""

        try:
            score = int(float(score))
        except Exception:
            score = 50

        score = max(0, min(100, score))

        if ticker:
            rows.append({
                "Ticker": ticker,
                "External Source": source,
                "External Score": score,
                "External Note": note,
            })

    return pd.DataFrame(rows)


def apply_external_signals(scan, external_df):
    scan = scan.copy()

    if external_df is None or external_df.empty:
        scan["External Source"] = "None"
        scan["External Score"] = 50
        scan["External Note"] = ""
        return scan

    external_df = external_df.copy()
    external_df["Ticker"] = external_df["Ticker"].astype(str).str.upper().str.strip()

    # If multiple lines are entered for a ticker, average the score and combine notes.
    grouped = external_df.groupby("Ticker").agg(
        External_Source=("External Source", lambda x: ", ".join(sorted(set([str(v) for v in x if str(v).strip()])))),
        External_Score=("External Score", "mean"),
        External_Note=("External Note", lambda x: " | ".join([str(v) for v in x if str(v).strip()])),
    ).reset_index()

    grouped = grouped.rename(columns={
        "External_Source": "External Source",
        "External_Score": "External Score",
        "External_Note": "External Note",
    })

    grouped["External Score"] = grouped["External Score"].round(0).astype(int)

    scan = scan.merge(grouped, how="left", on="Ticker")
    scan["External Source"] = scan["External Source"].fillna("None")
    scan["External Score"] = scan["External Score"].fillna(50).astype(int)
    scan["External Note"] = scan["External Note"].fillna("")

    return scan


def add_sector_rotation_scores(scan):
    scan = scan.copy()

    sector_stats = scan.groupby("Sector").agg(
        Sector_Avg_Flow=("Money Flow Score", "mean"),
        Sector_Avg_RS=("RS Score", "mean"),
        Sector_Tradeable=("Signal", lambda x: x.isin(["TRADE", "SMALL TRADE"]).sum()),
        Sector_Count=("Ticker", "count"),
        Sector_Avg_Catalyst=("Catalyst Score", "mean"),
    ).reset_index()

    sector_stats["Sector Tradeable %"] = np.where(
        sector_stats["Sector_Count"] > 0,
        sector_stats["Sector_Tradeable"] / sector_stats["Sector_Count"] * 100,
        0
    )

    sector_stats["Sector Rotation Score"] = (
        (sector_stats["Sector_Avg_Flow"] * 0.40)
        + (sector_stats["Sector_Avg_RS"] * 0.25)
        + (sector_stats["Sector_Avg_Catalyst"] * 0.20)
        + (sector_stats["Sector Tradeable %"] * 0.15)
    ).round(1)

    scan = scan.merge(
        sector_stats[[
            "Sector", "Sector_Avg_Flow", "Sector_Avg_RS", "Sector_Avg_Catalyst",
            "Sector_Tradeable", "Sector_Count", "Sector Tradeable %", "Sector Rotation Score"
        ]],
        how="left",
        on="Sector",
    )

    return scan


def add_multi_source_scores(scan):
    scan = scan.copy()

    # Score components normalized into explicit columns.
    scan["Technical Score"] = scan["Best Score"]
    scan["News Score"] = scan["Catalyst Score"]
    scan["Money Flow Component"] = scan["Money Flow Score"]
    scan["Sector Component"] = scan["Sector Rotation Score"].fillna(50)
    scan["External Component"] = scan["External Score"].fillna(50)

    # Composite score. This is v31's main ranking score.
    scan["Composite Score"] = (
        (scan["Technical Score"] * 0.25)
        + (scan["Money Flow Component"] * 0.25)
        + (scan["News Score"] * 0.20)
        + (scan["Sector Component"] * 0.20)
        + (scan["External Component"] * 0.10)
    ).round(1)

    verdicts = []
    for _, row in scan.iterrows():
        verdict = row["Catalyst-Adjusted Verdict"]

        if row["Composite Score"] >= 78 and row["Money Flow Score"] >= 62 and row["OR Status"] != "Below OR Low":
            if row["Signal"] in ["TRADE", "SMALL TRADE"]:
                verdict = "TRADE CANDIDATE"
            else:
                verdict = "WAIT FOR TRIGGER"

        if row["Composite Score"] >= 68 and verdict == "AVOID / WATCH ONLY" and row["OR Status"] != "Below OR Low":
            verdict = "WAIT FOR TRIGGER"

        if row["Composite Score"] <= 40:
            verdict = "AVOID / WATCH ONLY"

        if row["Catalyst Score"] <= 25 and row["External Score"] <= 40:
            verdict = "AVOID / WATCH ONLY"

        verdicts.append(verdict)

    scan["Composite Verdict"] = verdicts

    scan = scan.sort_values(
        ["Composite Score", "Sector Rotation Score", "Money Flow Score", "Catalyst Score", "Best Score"],
        ascending=False
    ).reset_index(drop=True)

    return scan


def multi_source_summary(scan):
    if scan.empty or "Composite Score" not in scan.columns:
        return "No multi-source score available."

    leader = scan.iloc[0]
    lines = []
    lines.append("MULTI-SOURCE INTELLIGENCE SUMMARY")
    lines.append(
        f"Top composite name: {leader['Ticker']} / Composite {leader['Composite Score']} / "
        f"Verdict {leader['Composite Verdict']} / Sector {leader['Sector']}"
    )

    strongest_sector = scan.sort_values("Sector Rotation Score", ascending=False).iloc[0]
    lines.append(
        f"Strongest sector signal: {strongest_sector['Sector']} / "
        f"Sector rotation {strongest_sector['Sector Rotation Score']}"
    )

    return "\n".join(lines)


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
# EARNINGS / PREMARKET / LEARNING ENGINE
# ============================================================

LEARNING_FILE = "trade_learning_log_v31.csv"

def parse_earnings_text(text):
    """
    Expected format:
    TICKER | Timing | Date | Note

    Timing examples:
    Reports BMO
    Reports AMC
    Reported BMO
    Reported AMC
    No event

    Example:
    NVDA | Reports AMC | 2026-06-10 | earnings after close
    CRDO | Reported AMC | 2026-06-03 | beat and raised guide
    """
    rows = []

    if not text or not text.strip():
        return pd.DataFrame(columns=["Ticker", "Earnings Timing", "Earnings Date", "Earnings Note"])

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        ticker = parts[0].upper() if len(parts) >= 1 else ""
        timing = parts[1] if len(parts) >= 2 else "Unknown"
        edate = parts[2] if len(parts) >= 3 else ""
        note = parts[3] if len(parts) >= 4 else ""

        if ticker:
            rows.append({
                "Ticker": ticker,
                "Earnings Timing": timing,
                "Earnings Date": edate,
                "Earnings Note": note,
            })

    return pd.DataFrame(rows)


def earnings_score_from_row(timing, edate):
    timing_l = str(timing).lower().strip()

    if "reported" in timing_l and ("bmo" in timing_l or "amc" in timing_l):
        return 75, "Post-earnings catalyst window"

    if "reports" in timing_l and "bmo" in timing_l:
        return 35, "Reports before open soon; elevated risk"

    if "reports" in timing_l and "amc" in timing_l:
        return 42, "Reports after close soon; avoid forced late entries"

    if "no event" in timing_l:
        return 50, "No known earnings event"

    if "unknown" in timing_l or not timing_l:
        return 50, "Earnings timing unknown"

    return 50, "Earnings timing entered but neutral"


def apply_earnings_timing(scan, earnings_df):
    scan = scan.copy()

    if earnings_df is None or earnings_df.empty:
        scan["Earnings Timing"] = "Unknown"
        scan["Earnings Date"] = ""
        scan["Earnings Note"] = ""
    else:
        earnings_df = earnings_df.copy()
        earnings_df["Ticker"] = earnings_df["Ticker"].astype(str).str.upper().str.strip()
        earnings_df = earnings_df.drop_duplicates(subset=["Ticker"], keep="last")
        scan = scan.merge(earnings_df, on="Ticker", how="left")
        scan["Earnings Timing"] = scan["Earnings Timing"].fillna("Unknown")
        scan["Earnings Date"] = scan["Earnings Date"].fillna("")
        scan["Earnings Note"] = scan["Earnings Note"].fillna("")

    scores = scan.apply(lambda r: earnings_score_from_row(r["Earnings Timing"], r["Earnings Date"]), axis=1)
    scan["Earnings Score"] = [x[0] for x in scores]
    scan["Earnings Risk Note"] = [x[1] for x in scores]

    return scan


def parse_premarket_text(text):
    """
    Expected format:
    TICKER | Gap % | Premarket RVOL | Note

    Example:
    CRDO | 4.2 | 3.5 | earnings gap with volume
    NVDA | 1.1 | 1.4 | modest premarket activity
    """
    rows = []

    if not text or not text.strip():
        return pd.DataFrame(columns=["Ticker", "Premarket Gap %", "Premarket RVOL", "Premarket Note"])

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        ticker = parts[0].upper() if len(parts) >= 1 else ""

        try:
            gap = float(parts[1]) if len(parts) >= 2 else 0.0
        except Exception:
            gap = 0.0

        try:
            rvol = float(parts[2]) if len(parts) >= 3 else 1.0
        except Exception:
            rvol = 1.0

        note = parts[3] if len(parts) >= 4 else ""

        if ticker:
            rows.append({
                "Ticker": ticker,
                "Premarket Gap %": gap,
                "Premarket RVOL": rvol,
                "Premarket Note": note,
            })

    return pd.DataFrame(rows)


def premarket_score(gap, rvol):
    score = 50

    if gap >= 5:
        score += 25
    elif gap >= 3:
        score += 18
    elif gap >= 1:
        score += 8
    elif gap <= -5:
        score -= 25
    elif gap <= -3:
        score -= 18
    elif gap <= -1:
        score -= 8

    if rvol >= 5:
        score += 25
    elif rvol >= 3:
        score += 18
    elif rvol >= 2:
        score += 12
    elif rvol >= 1.25:
        score += 6
    elif rvol < 0.75:
        score -= 8

    return int(max(0, min(100, score)))


def apply_premarket_activity(scan, premarket_df):
    scan = scan.copy()

    if premarket_df is None or premarket_df.empty:
        scan["Premarket Gap %"] = 0.0
        scan["Premarket RVOL"] = 1.0
        scan["Premarket Note"] = ""
    else:
        premarket_df = premarket_df.copy()
        premarket_df["Ticker"] = premarket_df["Ticker"].astype(str).str.upper().str.strip()
        premarket_df = premarket_df.drop_duplicates(subset=["Ticker"], keep="last")
        scan = scan.merge(premarket_df, on="Ticker", how="left")
        scan["Premarket Gap %"] = scan["Premarket Gap %"].fillna(0.0)
        scan["Premarket RVOL"] = scan["Premarket RVOL"].fillna(1.0)
        scan["Premarket Note"] = scan["Premarket Note"].fillna("")

    scan["Premarket Score"] = scan.apply(
        lambda r: premarket_score(r["Premarket Gap %"], r["Premarket RVOL"]),
        axis=1,
    )

    return scan


def empty_learning_log():
    return pd.DataFrame(columns=[
        "Date", "Ticker", "Setup", "Verdict", "Composite Score",
        "Entry", "Exit", "Shares", "P/L", "Return %",
        "Mistake", "Notes"
    ])


def load_learning_log():
    try:
        if Path(LEARNING_FILE).exists():
            return pd.read_csv(LEARNING_FILE)
    except Exception:
        pass
    return empty_learning_log()


def save_learning_log(df):
    df.to_csv(LEARNING_FILE, index=False)


def learning_stats(log_df):
    if log_df is None or log_df.empty:
        return pd.DataFrame(columns=["Setup", "Trades", "Win Rate %", "Total P/L", "Avg Return %", "Learning Score"])

    df = log_df.copy()
    df["P/L"] = pd.to_numeric(df["P/L"], errors="coerce").fillna(0)
    df["Return %"] = pd.to_numeric(df["Return %"], errors="coerce").fillna(0)

    grouped = df.groupby("Setup").agg(
        Trades=("Ticker", "count"),
        Wins=("P/L", lambda x: (x > 0).sum()),
        Total_PL=("P/L", "sum"),
        Avg_Return=("Return %", "mean"),
    ).reset_index()

    grouped["Win Rate %"] = np.where(grouped["Trades"] > 0, grouped["Wins"] / grouped["Trades"] * 100, 0).round(1)
    grouped["Total P/L"] = grouped["Total_PL"].round(2)
    grouped["Avg Return %"] = grouped["Avg_Return"].round(2)

    # Neutral 50, adjusted by win rate and average return.
    grouped["Learning Score"] = (
        50
        + ((grouped["Win Rate %"] - 50) * 0.40)
        + (grouped["Avg Return %"] * 4)
    ).round(1)

    grouped["Learning Score"] = grouped["Learning Score"].clip(lower=0, upper=100)

    return grouped[["Setup", "Trades", "Win Rate %", "Total P/L", "Avg Return %", "Learning Score"]]


def apply_learning_scores(scan, log_df):
    scan = scan.copy()
    stats = learning_stats(log_df)

    if stats.empty:
        scan["Learning Score"] = 50
        scan["Historical Setup Trades"] = 0
        scan["Historical Setup Win Rate %"] = 0.0
        return scan

    stats_small = stats.rename(columns={
        "Setup": "Best Setup",
        "Trades": "Historical Setup Trades",
        "Win Rate %": "Historical Setup Win Rate %",
    })[["Best Setup", "Historical Setup Trades", "Historical Setup Win Rate %", "Learning Score"]]

    scan = scan.merge(stats_small, on="Best Setup", how="left")
    scan["Learning Score"] = scan["Learning Score"].fillna(50)
    scan["Historical Setup Trades"] = scan["Historical Setup Trades"].fillna(0).astype(int)
    scan["Historical Setup Win Rate %"] = scan["Historical Setup Win Rate %"].fillna(0.0)

    return scan


def add_v31_scores(scan):
    scan = scan.copy()

    scan["Professional Score"] = (
        (scan["Composite Score"] * 0.45)
        + (scan["Earnings Score"] * 0.15)
        + (scan["Premarket Score"] * 0.15)
        + (scan["Learning Score"] * 0.10)
        + (scan["Sector Rotation Score"] * 0.15)
    ).round(1)

    verdicts = []

    for _, row in scan.iterrows():
        verdict = row["Composite Verdict"]

        # Earnings risk overrides.
        timing = str(row.get("Earnings Timing", "")).lower()
        if "reports" in timing and "bmo" in timing:
            verdict = "AVOID / WATCH ONLY"

        if row["Professional Score"] >= 80 and row["Signal"] in ["TRADE", "SMALL TRADE"] and row["OR Status"] != "Below OR Low":
            verdict = "TRADE CANDIDATE"
        elif row["Professional Score"] >= 68 and row["OR Status"] != "Below OR Low":
            verdict = "WAIT FOR TRIGGER"

        if row["Professional Score"] <= 42:
            verdict = "AVOID / WATCH ONLY"

        verdicts.append(verdict)

    scan["Professional Verdict"] = verdicts

    scan = scan.sort_values(
        ["Professional Score", "Composite Score", "Premarket Score", "Earnings Score", "Sector Rotation Score"],
        ascending=False
    ).reset_index(drop=True)

    return scan


def v31_summary(scan):
    if scan.empty or "Professional Score" not in scan.columns:
        return "No v31 professional score available."

    leader = scan.iloc[0]

    lines = []
    lines.append("V31 PROFESSIONAL LAYERS")
    lines.append(
        f"Top professional score: {leader['Ticker']} / {leader['Professional Score']} / "
        f"{leader['Professional Verdict']}"
    )
    lines.append(
        f"Earnings: {leader['Earnings Timing']} {leader['Earnings Date']} / score {leader['Earnings Score']} / {leader['Earnings Risk Note']}"
    )
    lines.append(
        f"Premarket: gap {leader['Premarket Gap %']}% / RVOL {leader['Premarket RVOL']} / score {leader['Premarket Score']}"
    )
    lines.append(
        f"Learning: setup {leader['Best Setup']} / score {leader['Learning Score']} / "
        f"trades {leader['Historical Setup Trades']} / win rate {leader['Historical Setup Win Rate %']}%"
    )

    return "\n".join(lines)



# ============================================================
# TRADE EXECUTION ENGINE
# ============================================================


def adaptive_execution_style(row):
    setup = str(row.get("Best Setup", "")).upper()
    or_zone = str(row.get("OR Zone", "")).lower()
    above_vwap = bool(row.get("Above VWAP", False))
    signal = str(row.get("Signal", ""))
    tier = str(row.get("Tier", ""))
    momentum_score = safe_num(row.get("Momentum Score", 0))
    vwap_score = safe_num(row.get("VWAP Score", 0))
    orb_score = safe_num(row.get("ORB Score", 0))
    gap_score = safe_num(row.get("Gap Score", 0))

    if "ORB" in setup or orb_score >= max(vwap_score, momentum_score, gap_score):
        if "breakout" in or_zone or "upper" in or_zone:
            return "Breakout confirmation"

    if "VWAP" in setup or (above_vwap and vwap_score >= 70):
        return "Starter then add"

    if "GAP" in setup and gap_score >= 70:
        return "Starter then add"

    if "MOMENTUM" in setup and tier in ["A+", "A"]:
        return "Pullback ladder"

    if signal == "SMALL TRADE":
        return "Pullback ladder"

    return "Pullback ladder"


def ensure_trade_plan_fields(row, cash, risk_pct):
    """
    v32 repair layer:
    If the broker engine receives a ranked row with missing/zero shares, stop, or targets,
    create a conservative executable plan from price, setup strength, and risk settings.
    """
    r = row.copy() if hasattr(row, "copy") else pd.Series(row)

    price = safe_num(r.get("Price", 0))
    stop = safe_num(r.get("Stop", 0))
    target1 = safe_num(r.get("Target 1", 0))
    target2 = safe_num(r.get("Target 2", 0))
    shares = safe_num(r.get("Shares", 0))

    if price <= 0:
        return r

    setup = str(r.get("Best Setup", "")).upper()
    tier = str(r.get("Tier", ""))
    signal = str(r.get("Signal", ""))
    professional_score = safe_num(r.get("Professional Score", r.get("Composite Score", 50)))

    # Stop distance adapts to setup type and score.
    if stop <= 0 or stop >= price:
        if "ORB" in setup:
            stop_pct = 0.012 if professional_score >= 70 else 0.018
        elif "VWAP" in setup:
            stop_pct = 0.014 if professional_score >= 70 else 0.020
        elif "GAP" in setup:
            stop_pct = 0.018 if professional_score >= 70 else 0.025
        elif "MOMENTUM" in setup:
            stop_pct = 0.020 if professional_score >= 70 else 0.030
        else:
            stop_pct = 0.020

        stop = round(price * (1 - stop_pct), 2)
        r["Stop"] = stop

    risk_per_share = max(0.01, price - stop)

    if target1 <= price:
        r["Target 1"] = round(price + risk_per_share * 1.25, 2)
    if target2 <= price:
        r["Target 2"] = round(price + risk_per_share * 2.0, 2)

    # Risk multiplier by quality.
    if tier == "A+":
        mult = 1.0
    elif tier == "A":
        mult = 0.75
    elif tier == "B":
        mult = 0.50
    else:
        mult = 0.25

    # If dashboard says only WAIT, size smaller.
    verdict = str(r.get("Professional Verdict", r.get("Composite Verdict", "")))
    if "WAIT" in verdict:
        mult *= 0.50
    if "AVOID" in verdict:
        mult = 0.0

    risk_budget = cash * risk_pct * mult
    max_affordable = cash / price if price > 0 else 0
    calc_shares = min(risk_budget / risk_per_share, max_affordable) if risk_per_share > 0 else 0

    if shares <= 0 and calc_shares > 0:
        r["Shares"] = round(calc_shares, 4)
        r["Position $"] = round(calc_shares * price, 2)
        r["Dollar Risk"] = round(calc_shares * risk_per_share, 2)
        r["Risk Multiplier"] = mult

    return r

def build_ladder_plan(row, cash, risk_pct, entry_style="Pullback ladder", tranches=4):
    """
    Creates an execution plan and broker-ready ladder.
    v32 repairs missing trade-plan fields and supports Adaptive execution.
    """
    if entry_style == "Adaptive":
        entry_style = adaptive_execution_style(row)

    row = ensure_trade_plan_fields(row, cash, risk_pct)

    price = safe_num(row.get("Price", 0))
    stop = safe_num(row.get("Stop", 0))
    target1 = safe_num(row.get("Target 1", 0))
    target2 = safe_num(row.get("Target 2", 0))
    shares_total = safe_num(row.get("Shares", 0))
    ticker = row.get("Ticker", "")

    if price <= 0 or stop <= 0 or shares_total <= 0 or stop >= price:
        return {
            "valid": False,
            "reason": "No valid execution plan because price, stop, or shares are invalid.",
            "entry_table": pd.DataFrame(),
            "exit_table": pd.DataFrame(),
            "instructions": "No order plan generated.",
            "summary": {},
        }

    tranches = int(max(1, min(6, tranches)))
    risk_per_share = price - stop
    total_risk = shares_total * risk_per_share

    # Entry allocations: front-loaded for breakout, evenly distributed for pullback.
    if entry_style == "Breakout confirmation":
        entry_weights = np.array([0.50, 0.25, 0.15, 0.10, 0, 0])[:tranches]
    elif entry_style == "Pullback ladder":
        entry_weights = np.array([0.25, 0.25, 0.25, 0.25, 0, 0])[:tranches]
    elif entry_style == "Starter then add":
        entry_weights = np.array([0.35, 0.35, 0.20, 0.10, 0, 0])[:tranches]
    else:
        entry_weights = np.ones(tranches) / tranches

    entry_weights = entry_weights / entry_weights.sum()

    # Entry prices.
    if entry_style == "Breakout confirmation":
        entry_prices = np.linspace(price, price + risk_per_share * 0.30, tranches)
    elif entry_style == "Starter then add":
        entry_prices = np.array([
            price,
            price + risk_per_share * 0.20,
            price + risk_per_share * 0.40,
            max(price - risk_per_share * 0.20, stop + risk_per_share * 0.35),
            price,
            price,
        ])[:tranches]
    else:
        # Pullback ladder from current/reference entry down toward but not into stop.
        deepest = max(stop + risk_per_share * 0.30, price - risk_per_share * 0.75)
        entry_prices = np.linspace(price, deepest, tranches)

    entry_rows = []
    for i in range(tranches):
        shares = shares_total * entry_weights[i]
        ep = round(float(entry_prices[i]), 2)
        dollar = shares * ep
        tranche_risk = max(0, ep - stop) * shares
        entry_rows.append({
            "Step": i + 1,
            "Action": "BUY",
            "Ticker": ticker,
            "Entry Type": entry_style,
            "Limit Price": ep,
            "Shares": round(shares, 4),
            "Approx $": round(dollar, 2),
            "Risk to Stop": round(tranche_risk, 2),
        })

    entry_table = pd.DataFrame(entry_rows)

    avg_entry = (entry_table["Limit Price"] * entry_table["Shares"]).sum() / entry_table["Shares"].sum()
    avg_entry = round(float(avg_entry), 2)

    # Recalculate targets from average entry for scale-out.
    effective_risk = avg_entry - stop
    t1 = round(avg_entry + effective_risk * 1.0, 2)
    t2 = round(avg_entry + effective_risk * 1.5, 2)
    t3 = round(avg_entry + effective_risk * 2.0, 2)
    runner = round(avg_entry + effective_risk * 3.0, 2)

    # Use dashboard targets if they are more conservative than derived targets.
    if target1 > 0:
        t1 = min(t1, target1) if target1 > avg_entry else t1
    if target2 > 0:
        t3 = min(t3, target2) if target2 > avg_entry else t3

    exit_weights = np.array([0.30, 0.30, 0.25, 0.15])
    exit_prices = [t1, t2, t3, runner]
    exit_labels = ["Scale 1", "Scale 2", "Scale 3", "Runner"]

    exit_rows = []
    for i in range(4):
        shares = shares_total * exit_weights[i]
        xp = exit_prices[i]
        reward = max(0, xp - avg_entry) * shares
        exit_rows.append({
            "Step": i + 1,
            "Action": "SELL",
            "Ticker": ticker,
            "Exit Type": exit_labels[i],
            "Limit Price": round(xp, 2),
            "Shares": round(shares, 4),
            "Approx Reward": round(reward, 2),
        })

    exit_table = pd.DataFrame(exit_rows)

    break_even_trigger = t1
    hard_stop = round(stop, 2)
    emergency_exit = round(max(stop, avg_entry - effective_risk * 0.70), 2)

    instructions = []
    instructions.append(f"TRADE EXECUTION PLAN FOR {ticker}")
    instructions.append(f"Reference entry: ${price:.2f}")
    instructions.append(f"Planned average entry: ${avg_entry:.2f}")
    instructions.append(f"Hard stop: ${hard_stop:.2f}")
    instructions.append(f"Total planned shares: {shares_total:.4f}")
    instructions.append(f"Estimated total risk: ${total_risk:.2f}")
    instructions.append("")
    instructions.append("ENTRY LADDER")
    for _, r in entry_table.iterrows():
        instructions.append(
            f"{int(r['Step'])}. BUY {r['Shares']} shares limit ${r['Limit Price']} "
            f"(risk to stop approx ${r['Risk to Stop']})"
        )
    instructions.append("")
    instructions.append("EXIT LADDER")
    for _, r in exit_table.iterrows():
        instructions.append(
            f"{int(r['Step'])}. SELL {r['Shares']} shares limit ${r['Limit Price']} "
            f"({r['Exit Type']})"
        )
    instructions.append("")
    instructions.append("STOP RULE")
    instructions.append(f"- Hard stop for remaining shares: ${hard_stop:.2f}")
    instructions.append(f"- After first scale at ${break_even_trigger:.2f}, consider moving stop to breakeven near ${avg_entry:.2f}")
    instructions.append(f"- If price loses VWAP or breaks OR low before first target, emergency review/exit zone: ${emergency_exit:.2f}")
    instructions.append("")
    instructions.append("ROBINHOOD MANUAL SEQUENCE")
    instructions.append("1. Do not enter all shares at once unless the setup is A+ and actively breaking out.")
    instructions.append("2. Place first buy limit only.")
    instructions.append("3. After fill, immediately set stop discipline manually.")
    instructions.append("4. Add next tranche only if price confirms or pulls into planned level without breaking structure.")
    instructions.append("5. Place scale-out sell limits after position is built.")
    instructions.append("6. If stopped, do not re-enter without a fresh dashboard/ChatGPT review.")

    summary = {
        "Ticker": ticker,
        "Reference Entry": round(price, 2),
        "Planned Avg Entry": avg_entry,
        "Hard Stop": hard_stop,
        "Total Shares": round(shares_total, 4),
        "Total Risk": round(total_risk, 2),
        "First Target": round(t1, 2),
        "Break Even Trigger": round(break_even_trigger, 2),
        "Emergency Review": round(emergency_exit, 2),
        "Entry Style": entry_style,
        "Tranches": tranches,
    }

    return {
        "valid": True,
        "reason": "Execution plan generated.",
        "entry_table": entry_table,
        "exit_table": exit_table,
        "instructions": "\n".join(instructions),
        "summary": summary,
    }


def execution_packet(row, ladder_plan):
    if not ladder_plan["valid"]:
        return "No valid execution packet."

    s = ladder_plan["summary"]
    lines = []
    lines.append("TRADE EXECUTION ENGINE v32")
    lines.append(f"Ticker: {s['Ticker']}")
    lines.append(f"Entry style: {s['Entry Style']}")
    lines.append(f"Reference entry: {s['Reference Entry']}")
    lines.append(f"Planned average entry: {s['Planned Avg Entry']}")
    lines.append(f"Hard stop: {s['Hard Stop']}")
    lines.append(f"Total shares: {s['Total Shares']}")
    lines.append(f"Total estimated risk: ${s['Total Risk']}")
    lines.append(f"First target: {s['First Target']}")
    lines.append(f"Breakeven trigger: {s['Break Even Trigger']}")
    lines.append(f"Emergency review zone: {s['Emergency Review']}")
    lines.append("")
    lines.append("Entry ladder:")
    for _, r in ladder_plan["entry_table"].iterrows():
        lines.append(f"- BUY {r['Shares']} @ {r['Limit Price']} | approx risk ${r['Risk to Stop']}")
    lines.append("")
    lines.append("Exit ladder:")
    for _, r in ladder_plan["exit_table"].iterrows():
        lines.append(f"- SELL {r['Shares']} @ {r['Limit Price']} | {r['Exit Type']} | approx reward ${r['Approx Reward']}")
    lines.append("")
    lines.append("Ask ChatGPT to verify whether this execution ladder matches the setup, market regime, VWAP/OR structure, and risk limits.")
    return "\n".join(lines)



# ============================================================
# BROKER EXECUTION INFRASTRUCTURE
# ============================================================

def secret_value(name, default=None):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return default


def alpaca_config():
    key = secret_value("APCA_API_KEY_ID", "")
    secret = secret_value("APCA_API_SECRET_KEY", "")
    base_url = secret_value("APCA_BASE_URL", "https://paper-api.alpaca.markets")
    live_enabled = str(secret_value("LIVE_TRADING_ENABLED", "false")).lower().strip() == "true"

    temp_key = st.session_state.get("TEMP_APCA_API_KEY_ID", "")
    temp_secret = st.session_state.get("TEMP_APCA_API_SECRET_KEY", "")
    temp_base_url = st.session_state.get("TEMP_APCA_BASE_URL", "")
    temp_live_enabled = st.session_state.get("TEMP_LIVE_TRADING_ENABLED", False)

    if temp_key and temp_secret:
        key = temp_key
        secret = temp_secret
        base_url = temp_base_url or "https://paper-api.alpaca.markets"
        live_enabled = bool(temp_live_enabled)

    return {
        "key": key,
        "secret": secret,
        "base_url": base_url.rstrip("/"),
        "live_enabled": live_enabled,
        "configured": bool(key and secret),
        "is_paper": "paper-api" in base_url,
    }


def alpaca_headers(cfg):
    return {
        "APCA-API-KEY-ID": cfg["key"],
        "APCA-API-SECRET-KEY": cfg["secret"],
        "Content-Type": "application/json",
    }


def alpaca_get_account(cfg):
    if not cfg["configured"]:
        return False, "Alpaca is not configured.", None

    try:
        url = cfg["base_url"] + "/v2/account"
        resp = requests.get(url, headers=alpaca_headers(cfg), timeout=15)
        if resp.status_code == 200:
            return True, "Connected.", resp.json()
        return False, f"Account check failed: {resp.status_code} {resp.text[:300]}", None
    except Exception as e:
        return False, f"Connection error: {e}", None


def alpaca_submit_order(cfg, payload):
    if not cfg["configured"]:
        return False, "Alpaca is not configured.", None

    try:
        url = cfg["base_url"] + "/v2/orders"
        resp = requests.post(url, headers=alpaca_headers(cfg), json=payload, timeout=20)
        if resp.status_code in [200, 201]:
            return True, "Order submitted.", resp.json()
        return False, f"Order failed: {resp.status_code} {resp.text[:500]}", None
    except Exception as e:
        return False, f"Order error: {e}", None


def alpaca_cancel_all_orders(cfg):
    if not cfg["configured"]:
        return False, "Alpaca is not configured.", None

    try:
        url = cfg["base_url"] + "/v2/orders"
        resp = requests.delete(url, headers=alpaca_headers(cfg), timeout=20)
        if resp.status_code in [200, 204, 207]:
            return True, "Cancel request sent.", resp.text
        return False, f"Cancel failed: {resp.status_code} {resp.text[:500]}", None
    except Exception as e:
        return False, f"Cancel error: {e}", None


def make_alpaca_bracket_payload(symbol, qty, limit_price, take_profit_price, stop_price, tif="day"):
    return {
        "symbol": symbol,
        "qty": str(round(float(qty), 4)),
        "side": "buy",
        "type": "limit",
        "time_in_force": tif,
        "limit_price": str(round(float(limit_price), 2)),
        "order_class": "bracket",
        "take_profit": {
            "limit_price": str(round(float(take_profit_price), 2))
        },
        "stop_loss": {
            "stop_price": str(round(float(stop_price), 2))
        }
    }


def build_broker_order_batch(ladder_plan):
    """
    Converts the ladder into one bracket order per entry tranche.
    Each tranche gets its own take-profit target and shared stop.
    """
    if not ladder_plan["valid"]:
        return []

    entry = ladder_plan["entry_table"].copy()
    exits = ladder_plan["exit_table"].copy()
    summary = ladder_plan["summary"]

    orders = []
    symbol = summary["Ticker"]
    stop = summary["Hard Stop"]

    for i, r in entry.iterrows():
        exit_idx = min(i, len(exits) - 1)
        target = float(exits.iloc[exit_idx]["Limit Price"])

        qty = float(r["Shares"])
        limit_price = float(r["Limit Price"])

        if qty <= 0 or limit_price <= 0 or target <= limit_price or stop >= limit_price:
            continue

        orders.append(make_alpaca_bracket_payload(
            symbol=symbol,
            qty=qty,
            limit_price=limit_price,
            take_profit_price=target,
            stop_price=stop,
        ))

    return orders


def broker_safety_check(ladder_plan, cash, max_order_value, max_total_risk):
    if not ladder_plan["valid"]:
        return False, ["Invalid ladder plan."]

    issues = []
    summary = ladder_plan["summary"]
    total_risk = float(summary["Total Risk"])
    total_value = float(ladder_plan["entry_table"]["Approx $"].sum())

    if total_value > cash:
        issues.append(f"Planned order value ${total_value:.2f} exceeds cash ${cash:.2f}.")

    if total_value > max_order_value:
        issues.append(f"Planned order value ${total_value:.2f} exceeds max order value ${max_order_value:.2f}.")

    if total_risk > max_total_risk:
        issues.append(f"Planned risk ${total_risk:.2f} exceeds max allowed risk ${max_total_risk:.2f}.")

    if total_risk <= 0:
        issues.append("Total risk is zero or invalid.")

    if len(ladder_plan["entry_table"]) == 0:
        issues.append("No entry orders generated.")

    return len(issues) == 0, issues


# ============================================================
# PACKETS / SUMMARY
# ============================================================

def sector_flow(scan):
    sec = scan.groupby("Sector").agg(
        Names=("Ticker", "count"),
        Tradeable=("Signal", lambda x: x.isin(["TRADE", "SMALL TRADE"]).sum()),
        Avg_Professional=("Professional Score", "mean"),
        Avg_Composite=("Composite Score", "mean"),
        Avg_Sector_Rotation=("Sector Rotation Score", "mean"),
        Avg_Flow=("Money Flow Score", "mean"),
        Avg_Catalyst=("Catalyst Score", "mean"),
        Avg_External=("External Score", "mean"),
        Avg_Setup=("Best Score", "mean"),
        Avg_RS=("RS Score", "mean"),
        Avg_EV=("EV / Share", "mean"),
    ).reset_index()

    for col in ["Avg_Professional", "Avg_Composite", "Avg_Sector_Rotation", "Avg_Flow", "Avg_Catalyst", "Avg_External", "Avg_Setup", "Avg_RS", "Avg_EV"]:
        sec[col] = sec[col].round(2)

    return sec.sort_values(["Avg_Professional", "Avg_Composite", "Tradeable", "Avg_Flow", "Avg_RS"], ascending=False)


def safe_records(df):
    if df is None or df.empty:
        return []
    return df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), None).to_dict(orient="records")


def build_snapshot(scan, market_df, light, regime, score, reason):
    tradeable = scan[scan["Signal"].isin(["TRADE", "SMALL TRADE"])]
    candidates = scan[scan["Professional Verdict"].isin(["TRADE CANDIDATE", "WAIT FOR TRIGGER"])]
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
    lines.append("TRADER BRIEFING v32")
    lines.append(f"Time: {snapshot['timestamp']}")
    lines.append(f"Market: {m['light']} {m['score']}/100 - {m['regime']}")
    lines.append(f"Market reason: {m['reason']}")
    lines.append(f"Tradeable names: {snapshot['tradeable_count']} of {snapshot['scanned_count']}")
    lines.append(f"Close candidates needing chart review: {snapshot['candidate_count']} of {snapshot['scanned_count']}")
    lines.append("")
    lines.append(catalyst_summary(pd.DataFrame(snapshot["top_10"])))
    lines.append(multi_source_summary(pd.DataFrame(snapshot["top_10"])))
    lines.append(v31_summary(pd.DataFrame(snapshot["top_10"])))
    lines.append("")

    if candidate:
        lines.append("PRIMARY CANDIDATE")
        lines.append(f"Ticker: {candidate['Ticker']}")
        lines.append(f"Technical verdict: {candidate['App Verdict']}")
        lines.append(f"Catalyst-adjusted verdict: {candidate['Catalyst-Adjusted Verdict']}")
        lines.append(f"Composite verdict: {candidate['Composite Verdict']}")
        lines.append(f"Professional verdict: {candidate['Professional Verdict']}")
        lines.append(f"Signal: {candidate['Signal']}")
        lines.append(f"Tier/setup: {candidate['Tier']} {candidate['Best Setup']}")
        lines.append(f"Pattern: {candidate['Pattern']}")
        lines.append(f"Professional Score: {candidate['Professional Score']}")
        lines.append(f"Composite Score: {candidate['Composite Score']}")
        lines.append(f"Total Opportunity Score: {candidate['Total Opportunity Score']}")
        lines.append(f"Sector Rotation Score: {candidate['Sector Rotation Score']}")
        lines.append(f"External Score: {candidate['External Score']} / {candidate['External Source']} / {candidate['External Note']}")
        lines.append(f"Earnings: {candidate['Earnings Timing']} / {candidate['Earnings Date']} / score {candidate['Earnings Score']} / {candidate['Earnings Risk Note']}")
        lines.append(f"Premarket: gap {candidate['Premarket Gap %']}% / RVOL {candidate['Premarket RVOL']} / score {candidate['Premarket Score']} / {candidate['Premarket Note']}")
        lines.append(f"Learning: score {candidate['Learning Score']} / setup trades {candidate['Historical Setup Trades']} / win rate {candidate['Historical Setup Win Rate %']}%")
        lines.append(f"Money Flow Score: {candidate['Money Flow Score']}")
        lines.append(f"Catalyst Score: {candidate['Catalyst Score']}")
        lines.append(f"Catalyst: {candidate['Catalyst Type']} / {candidate['Catalyst Freshness']} / {candidate['Catalyst Note']}")
        lines.append(f"Catalyst source: {candidate.get('Catalyst Source', 'Unknown')}")
        lines.append(f"Auto news type: {candidate.get('Auto Catalyst Type', 'None / Unknown')}")
        lines.append(f"News headlines: {candidate.get('News Headlines', '')}")
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
        lines.append("Execution: use v31 ladder plan before placing any manual orders.")
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
    lines.append("DEON TRADER DASHBOARD v32 - FULL DECISION PACKET")
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
            f"{i}. {row['Ticker']} | {row['Professional Verdict']} | {row['Signal']} | {row['Tier']} {row['Best Setup']} | "
            f"Professional {row['Professional Score']} | Composite {row['Composite Score']} | Total {row['Total Opportunity Score']} | Catalyst {row['Catalyst Score']} | Earnings {row['Earnings Score']} | Premarket {row['Premarket Score']} | Learning {row['Learning Score']} | Sector {row['Sector Rotation Score']} | External {row['External Score']} | Flow {row['Money Flow Score']} | Setup {row['Best Score']} | RS {row['RS Score']} | "
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

st.title("Deon's Trader Dashboard v32")
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

st.sidebar.subheader("Automated News Scan")
auto_news_enabled = st.sidebar.checkbox("Use Yahoo Finance news scan", value=True)
auto_news_limit = st.sidebar.slider("Auto-news tickers to scan", min_value=5, max_value=25, value=12, step=1)
st.sidebar.caption("Tip: put your most important tickers first in Scanner Universe. Yahoo news scan is free but can be delayed/incomplete.")

st.sidebar.subheader("External Source Signals")
external_signal_text = st.sidebar.text_area(
    "Optional: TICKER | Source | Score 0-100 | Note",
    value="",
    height=140,
    help="Examples: NVDA | FinancialJuice | 75 | macro headline supports semis"
)
with st.sidebar.expander("External signal examples"):
    st.code("NVDA | FinancialJuice | 75 | semis supported by macro headline\nPLTR | X sentiment | 80 | AI contract chatter\nAMD | TradingView | 70 | strong premarket relative volume")

st.sidebar.subheader("Earnings Timing")
earnings_text = st.sidebar.text_area(
    "Optional: TICKER | Timing | Date | Note",
    value="",
    height=130,
    help="Example: NVDA | Reports AMC | 2026-06-10 | earnings after close"
)
with st.sidebar.expander("Earnings examples"):
    st.code("NVDA | Reports AMC | 2026-06-10 | earnings after close\nCRDO | Reported AMC | 2026-06-03 | beat and raised guidance\nAMD | No event | | no near-term report")

st.sidebar.subheader("Premarket Activity")
premarket_text = st.sidebar.text_area(
    "Optional: TICKER | Gap % | Premarket RVOL | Note",
    value="",
    height=130,
    help="Example: CRDO | 4.2 | 3.5 | earnings gap with volume"
)
with st.sidebar.expander("Premarket examples"):
    st.code("CRDO | 4.2 | 3.5 | earnings gap with volume\nNVDA | 1.1 | 1.4 | modest premarket activity\nPLTR | -2.2 | 2.1 | weak gap with volume")
cash = st.sidebar.number_input("Cash available", min_value=0.0, value=855.0, step=25.0)
risk_pct = st.sidebar.number_input("Base risk per trade %", min_value=0.25, max_value=10.0, value=3.0, step=0.25) / 100

st.sidebar.write("A+ max risk:", f"${cash * risk_pct:,.2f}")
st.sidebar.write("A max risk:", f"${cash * risk_pct * 0.75:,.2f}")
st.sidebar.write("B max risk:", f"${cash * risk_pct * 0.50:,.2f}")

st.sidebar.subheader("Execution Engine")
entry_style_setting = st.sidebar.selectbox(
    "Default entry style",
    ["Adaptive", "Pullback ladder", "Breakout confirmation", "Starter then add"],
    index=0,
)
tranche_count_setting = st.sidebar.slider("Entry tranches", min_value=1, max_value=4, value=4, step=1)
st.sidebar.caption("Execution engine creates a manual order plan. Broker tab can submit to Alpaca only if configured.")

st.sidebar.subheader("Temporary Alpaca API Connection")
st.sidebar.caption("Use this because Streamlit Secrets is not editable right now. These values are not stored permanently.")
temp_alpaca_key = st.sidebar.text_input("Alpaca API Key", type="password")
temp_alpaca_secret = st.sidebar.text_input("Alpaca Secret Key", type="password")
temp_alpaca_base = st.sidebar.selectbox(
    "Alpaca Endpoint",
    ["https://paper-api.alpaca.markets", "https://api.alpaca.markets"],
    index=0,
)
temp_live_enabled = st.sidebar.checkbox("Allow live endpoint", value=False)

if st.sidebar.button("Use temporary Alpaca keys"):
    st.session_state["TEMP_APCA_API_KEY_ID"] = temp_alpaca_key.strip()
    st.session_state["TEMP_APCA_API_SECRET_KEY"] = temp_alpaca_secret.strip()
    st.session_state["TEMP_APCA_BASE_URL"] = temp_alpaca_base.strip()
    st.session_state["TEMP_LIVE_TRADING_ENABLED"] = temp_live_enabled
    st.sidebar.success("Temporary Alpaca keys loaded for this session.")

st.sidebar.subheader("Broker Safety Limits")
broker_max_order_value = st.sidebar.number_input("Max total order value", min_value=0.0, value=500.0, step=25.0)
broker_max_total_risk = st.sidebar.number_input("Max total trade risk", min_value=0.0, value=25.0, step=5.0)
st.sidebar.caption("Paper endpoint is safest while account review is pending. Live endpoint still requires explicit arming.")

if st.sidebar.button("Refresh now"):
    st.cache_data.clear()
    st.rerun()

market_df = market_context()
light, regime, market_score, market_reason = market_state(market_df)

symbols = [x.strip().upper() for x in scan_text.split(",") if x.strip()]

with st.spinner("Scanning technicals, news, sector rotation, earnings timing, premarket activity, and learning data..."):
    base_scan = run_scan(symbols, light, cash, risk_pct)
    manual_catalyst_df = parse_catalyst_text(catalyst_text)
    auto_catalyst_df = build_auto_catalysts(symbols, enabled=auto_news_enabled, max_symbols=auto_news_limit)
    catalyst_df = combine_manual_and_auto_catalysts(manual_catalyst_df, auto_catalyst_df)
    scan = apply_catalysts(base_scan, catalyst_df)
    external_df = parse_external_signals(external_signal_text)
    scan = apply_external_signals(scan, external_df)
    scan = add_sector_rotation_scores(scan)
    scan = add_multi_source_scores(scan)
    earnings_df = parse_earnings_text(earnings_text)
    premarket_df = parse_premarket_text(premarket_text)
    learning_log = load_learning_log()
    scan = apply_earnings_timing(scan, earnings_df)
    scan = apply_premarket_activity(scan, premarket_df)
    scan = apply_learning_scores(scan, learning_log)
    scan = add_v31_scores(scan)

if scan.empty:
    st.error("No data loaded. Try fewer tickers, wait one minute, then refresh.")
    st.stop()

snapshot = build_snapshot(scan, market_df, light, regime, market_score, market_reason)
top_execution_row = pd.Series(snapshot["top_candidate"]) if snapshot["top_candidate"] else scan.iloc[0]
top_execution_row = ensure_trade_plan_fields(top_execution_row, cash, risk_pct)
default_ladder_plan = build_ladder_plan(top_execution_row, cash, risk_pct, entry_style_setting, tranche_count_setting)
execution_text = execution_packet(top_execution_row, default_ladder_plan)
briefing = make_trader_briefing(snapshot)
full_packet = make_full_packet(snapshot) + "\n\n" + execution_text

auto_news_hits = scan[scan.get("Catalyst Source", "") == "Auto news"] if "Catalyst Source" in scan.columns else pd.DataFrame()
manual_news_hits = scan[scan.get("Catalyst Source", "") == "Manual override"] if "Catalyst Source" in scan.columns else pd.DataFrame()

# ============================================================
# 10/10 COMMAND CENTER
# ============================================================

st.header("Step 1 — Copy This Trader Briefing")
st.success("This is the main v31 workflow. Copy this box into ChatGPT first. Do not send screenshots unless the briefing says a chart is needed.")
st.caption(f"Auto-news scanned: {len(auto_news_hits)} tickers | Manual overrides: {len(manual_news_hits)} tickers")
st.text_area("Trader Briefing for ChatGPT", briefing, height=430)

c1, c2, c3 = st.columns(3)
c1.download_button("Download Trader Briefing TXT", data=briefing.encode("utf-8"), file_name="trader_briefing_v32.txt", mime="text/plain")
c2.download_button("Download Full Packet TXT", data=full_packet.encode("utf-8"), file_name="full_decision_packet_v32.txt", mime="text/plain")
c3.download_button("Download Top 10 CSV", data=df_csv(scan.head(10)), file_name="top10_v32.csv", mime="text/csv")

st.header("Step 2 — Dashboard's Preliminary Answer")
top_candidate = snapshot["top_candidate"]
tradeable = scan[scan["Signal"].isin(["TRADE", "SMALL TRADE"])]

if top_candidate:
    if top_candidate["Composite Verdict"] == "TRADE CANDIDATE":
        st.success(f"TRADE CANDIDATE: {top_candidate['Ticker']} — professional-layer confirmed. Paste the briefing into ChatGPT for final verification.")
    elif top_candidate["Composite Verdict"] == "WAIT FOR TRIGGER":
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

st.header("Step 3 — Trade Execution Plan")
if default_ladder_plan["valid"]:
    st.success(f"Execution ladder built for {default_ladder_plan['summary']['Ticker']}. This is a manual plan, not an automatic order.")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Planned Avg Entry", f"${default_ladder_plan['summary']['Planned Avg Entry']:.2f}")
    e2.metric("Hard Stop", f"${default_ladder_plan['summary']['Hard Stop']:.2f}")
    e3.metric("Total Shares", f"{default_ladder_plan['summary']['Total Shares']:.4f}")
    e4.metric("Total Risk", f"${default_ladder_plan['summary']['Total Risk']:.2f}")
    st.subheader("Entry Ladder")
    st.dataframe(default_ladder_plan["entry_table"], use_container_width=True)
    st.subheader("Exit Ladder")
    st.dataframe(default_ladder_plan["exit_table"], use_container_width=True)
    st.text_area("Execution Packet for ChatGPT", execution_text, height=320)
else:
    st.error(default_ladder_plan["reason"])

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
        "Ticker", "Sector", "Professional Verdict", "Signal", "Tier", "Best Setup",
        "Professional Score", "Composite Score", "Earnings Score", "Premarket Score", "Learning Score", "Sector Rotation Score", "Total Opportunity Score", "Catalyst Score", "Catalyst Type", "External Score", "External Source", "Money Flow Score", "Best Score", "Reason", "Price", "Stop",
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
    "Multi-Source",
    "Earnings/Premarket",
    "Learning Log",
    "Execution Engine",
    "Broker Execution",
    "Charts",
])

with tabs[0]:
    st.header("Ranked Money Flow Board")
    ranked = scan.head(25).copy()
    ranked.insert(0, "Rank", range(1, len(ranked) + 1))
    st.dataframe(
        ranked[[
            "Rank", "Ticker", "Sector", "Professional Verdict", "Signal", "Tier", "Best Setup",
            "Professional Score", "Composite Score", "Earnings Score", "Premarket Score", "Learning Score", "Sector Rotation Score", "Total Opportunity Score", "Catalyst Score", "Catalyst Type", "External Score", "External Source", "Money Flow Score", "Best Score", "Reason", "Price", "Probability %",
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

    if row["Composite Verdict"] == "TRADE CANDIDATE":
        st.success(f"{row['Ticker']} is a professional-layer trade candidate pending ChatGPT/chart verification.")
    elif row["Composite Verdict"] == "WAIT FOR TRIGGER":
        st.warning(f"{row['Ticker']} is close, but waiting for trigger.")
    else:
        st.error(f"{row['Ticker']} is not trade-ready.")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Ticker", row["Ticker"])
    m2.metric("Verdict", row["Composite Verdict"])
    m3.metric("Setup", row["Best Setup"])
    m4.metric("Tier", row["Tier"])
    m5.metric("Professional", row["Professional Score"])

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
    st.download_button("Download Snapshot JSON", data=json.dumps(snapshot, indent=2, default=str).encode("utf-8"), file_name="snapshot_v32.json", mime="application/json")

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
            "Ticker", "Sector", "Professional Verdict", "Signal", "Tier", "Best Setup",
            "Professional Score", "Composite Score", "Earnings Score", "Premarket Score", "Learning Score", "Sector Rotation Score", "Total Opportunity Score", "Catalyst Score", "Catalyst Type", "External Score", "External Source", "Money Flow Score", "Best Score", "ORB Score", "VWAP Score", "Gap Score",
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
            "Ticker", "Composite Verdict", "Signal", "Tier", "Best Setup", "Composite Score", "Sector Rotation Score", "Total Opportunity Score", "Catalyst Score", "External Score", "Money Flow Score",
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
    st.header("Automated Catalyst Intelligence")
    st.write("Automatic Yahoo Finance news plus manual catalyst entries affect Total Opportunity Score and Catalyst-Adjusted Verdict.")
    st.dataframe(
        scan[[
            "Ticker", "Composite Verdict", "Catalyst-Adjusted Verdict", "Catalyst Source", "Catalyst Type", "Catalyst Freshness",
            "Catalyst Score", "Auto Catalyst Type", "Auto Catalyst Score", "Catalyst Bias", "Catalyst Note",
            "News Headlines", "Total Opportunity Score", "Money Flow Score", "Best Setup", "Signal"
        ]],
        use_container_width=True,
        height=520,
    )
    st.subheader("How to enter catalysts")
    st.code("CRDO | Raised guidance | Today | earnings beat and raised outlook\nPLTR | Major contract / partnership | Yesterday | defense AI contract\nNVDA | Analyst upgrade | Today | price target raised")

with tabs[8]:
    st.header("Multi-Source Intelligence")
    st.write("v31 composite score blends technicals, money flow, automated/manual news, sector rotation, and external signals.")
    st.dataframe(
        scan[[
            "Ticker", "Composite Verdict", "Composite Score",
            "Technical Score", "Money Flow Component", "News Score",
            "Sector Component", "External Component",
            "Sector Rotation Score", "Catalyst Score", "External Score",
            "Signal", "Best Setup", "Reason"
        ]],
        use_container_width=True,
        height=560,
    )
    st.subheader("Scoring weights")
    st.write("Professional Score = 45% Composite + 15% Earnings + 15% Premarket + 10% Learning + 15% Sector Rotation. Composite still blends technicals, money flow, news, sector, and external signals.")

with tabs[9]:
    st.header("Earnings & Premarket Risk")
    st.write("Use this tab to see event risk and premarket participation. Manual inputs come from the sidebar.")
    st.dataframe(
        scan[[
            "Ticker", "Professional Verdict", "Professional Score",
            "Earnings Timing", "Earnings Date", "Earnings Score", "Earnings Risk Note", "Earnings Note",
            "Premarket Gap %", "Premarket RVOL", "Premarket Score", "Premarket Note",
            "Signal", "Best Setup", "Price"
        ]],
        use_container_width=True,
        height=560,
    )

with tabs[10]:
    st.header("Trade Outcome Learning")
    st.write("Record closed trades here so the dashboard can learn which setup types are actually working for you.")
    learning_log_current = load_learning_log()
    stats = learning_stats(learning_log_current)
    st.subheader("Learning Stats by Setup")
    st.dataframe(stats, use_container_width=True)

    with st.form("learning_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        l_date = c1.date_input("Date", value=date.today())
        l_ticker = c2.text_input("Ticker")
        l_setup = c3.selectbox("Setup", ["ORB", "VWAP", "Gap", "Momentum", "Daily", "Other"])
        l_verdict = c4.selectbox("Verdict", ["TRADE CANDIDATE", "WAIT FOR TRIGGER", "AVOID / WATCH ONLY"])

        c5, c6, c7, c8 = st.columns(4)
        l_score = c5.number_input("Composite/Professional Score", min_value=0.0, max_value=100.0, value=50.0, step=0.1)
        l_entry = c6.number_input("Entry", min_value=0.0, step=0.01)
        l_exit = c7.number_input("Exit", min_value=0.0, step=0.01)
        l_shares = c8.number_input("Shares", min_value=0.0, step=0.0001, format="%.6f")

        c9, c10 = st.columns(2)
        l_mistake = c9.selectbox("Mistake", ["None", "Chased", "Ignored stop", "Sold too early", "No trigger", "Oversized", "Revenge trade"])
        l_notes = c10.text_input("Notes")

        if st.form_submit_button("Save Learning Trade"):
            if l_ticker.strip() and l_entry > 0 and l_exit > 0 and l_shares > 0:
                pnl = (l_exit - l_entry) * l_shares
                ret = ((l_exit / l_entry) - 1) * 100
                row = {
                    "Date": l_date.isoformat(),
                    "Ticker": l_ticker.strip().upper(),
                    "Setup": l_setup,
                    "Verdict": l_verdict,
                    "Composite Score": round(l_score, 1),
                    "Entry": round(l_entry, 2),
                    "Exit": round(l_exit, 2),
                    "Shares": round(l_shares, 6),
                    "P/L": round(pnl, 2),
                    "Return %": round(ret, 2),
                    "Mistake": l_mistake,
                    "Notes": l_notes,
                }
                learning_log_current = pd.concat([learning_log_current, pd.DataFrame([row])], ignore_index=True)
                save_learning_log(learning_log_current)
                st.success("Saved. Click Refresh now.")
            else:
                st.error("Ticker, entry, exit, and shares are required.")

with tabs[11]:
    st.header("Trade Execution Engine")
    st.write("This creates a manual ladder plan. It does not connect to Robinhood or place live orders.")

    selected_exec = st.selectbox("Select ticker for execution plan", scan["Ticker"].tolist(), index=0, key="exec_select")
    exec_row = scan[scan["Ticker"] == selected_exec].iloc[0]

    c1, c2 = st.columns(2)
    exec_style_options = ["Adaptive", "Pullback ladder", "Breakout confirmation", "Starter then add"]
    exec_style = c1.selectbox(
        "Entry style",
        exec_style_options,
        index=exec_style_options.index(entry_style_setting) if entry_style_setting in exec_style_options else 0,
        key="exec_style_tab",
    )
    exec_tranches = c2.slider("Entry tranches", min_value=1, max_value=4, value=tranche_count_setting, step=1, key="exec_tranches_tab")

    plan = build_ladder_plan(exec_row, cash, risk_pct, exec_style, exec_tranches)

    if plan["valid"]:
        s = plan["summary"]
        a, b, c, d = st.columns(4)
        a.metric("Ticker", s["Ticker"])
        b.metric("Avg Entry", f"${s['Planned Avg Entry']:.2f}")
        c.metric("Hard Stop", f"${s['Hard Stop']:.2f}")
        d.metric("Total Risk", f"${s['Total Risk']:.2f}")

        st.subheader("Entry Ladder")
        st.dataframe(plan["entry_table"], use_container_width=True)

        st.subheader("Exit Ladder")
        st.dataframe(plan["exit_table"], use_container_width=True)

        st.subheader("Manual Broker Instructions")
        st.text_area("Instructions", plan["instructions"], height=430)

        st.download_button(
            "Download Execution Plan TXT",
            data=execution_packet(exec_row, plan).encode("utf-8"),
            file_name=f"execution_plan_{s['Ticker']}.txt",
            mime="text/plain",
        )
    else:
        st.error(plan["reason"])

with tabs[12]:
    st.header("Broker Execution — Alpaca")
    st.warning("This tab can place orders only if Alpaca keys are configured. Use paper trading first. This is not a promise of income.")

    cfg = alpaca_config()

    if cfg["configured"]:
        mode = "PAPER" if cfg["is_paper"] else "LIVE"
        if cfg["is_paper"]:
            st.success(f"Alpaca configured in {mode} mode.")
        else:
            st.error(f"Alpaca configured in {mode} mode.")
    else:
        st.error("Alpaca is not configured.")
        st.write("Either add Streamlit secrets later, or use the Temporary Alpaca API Connection fields in the sidebar now:")
        st.code(
            'APCA_API_KEY_ID = "your_key"\n'
            'APCA_API_SECRET_KEY = "your_secret"\n'
            'APCA_BASE_URL = "https://paper-api.alpaca.markets"\n'
            'LIVE_TRADING_ENABLED = "false"'
        )

    if st.button("Test Alpaca Connection"):
        ok, msg, acct = alpaca_get_account(cfg)
        if ok:
            st.success(msg)
            safe_acct = {
                "status": acct.get("status"),
                "cash": acct.get("cash"),
                "buying_power": acct.get("buying_power"),
                "portfolio_value": acct.get("portfolio_value"),
                "trading_blocked": acct.get("trading_blocked"),
                "account_blocked": acct.get("account_blocked"),
                "pattern_day_trader": acct.get("pattern_day_trader"),
            }
            st.json(safe_acct)
        else:
            st.error(msg)

    st.subheader("Build Broker Order Batch")
    selected_broker = st.selectbox("Ticker to route", scan["Ticker"].tolist(), index=0, key="broker_select")
    broker_row = scan[scan["Ticker"] == selected_broker].iloc[0]

    b1, b2 = st.columns(2)
    broker_style_options = ["Adaptive", "Pullback ladder", "Breakout confirmation", "Starter then add"]
    broker_style = b1.selectbox(
        "Entry style",
        broker_style_options,
        index=broker_style_options.index(entry_style_setting) if entry_style_setting in broker_style_options else 0,
        key="broker_style",
    )
    broker_tranches = b2.slider("Entry tranches", min_value=1, max_value=4, value=tranche_count_setting, step=1, key="broker_tranches")

    broker_plan = build_ladder_plan(broker_row, cash, risk_pct, broker_style, broker_tranches)
    broker_orders = build_broker_order_batch(broker_plan)

    if broker_plan["valid"]:
        if "WAIT" in str(broker_row.get("Professional Verdict", "")):
            st.warning("This ticker is WAIT FOR TRIGGER. Orders are buildable, but do not submit unless the chart trigger confirms.")
        if "AVOID" in str(broker_row.get("Professional Verdict", "")):
            st.error("This ticker is AVOID / WATCH ONLY. Submission should remain blocked by sizing/risk rules.")
        st.write("Execution summary:")
        st.json(broker_plan["summary"])

        ok_safety, safety_issues = broker_safety_check(
            broker_plan,
            cash=cash,
            max_order_value=broker_max_order_value,
            max_total_risk=broker_max_total_risk,
        )

        if ok_safety:
            st.success("Safety check passed.")
        else:
            st.error("Safety check failed.")
            for issue in safety_issues:
                st.write("- " + issue)

        st.subheader("Orders to Submit")
        st.json(broker_orders)
    else:
        st.error(broker_plan["reason"])
        ok_safety = False

    st.subheader("Arming Controls")
    st.write("To submit orders, type exactly:")
    st.code("ARM PAPER TRADE")
    arm_text = st.text_input("Arming phrase", value="", key="arm_phrase")

    live_blocked = (not cfg["is_paper"]) and (not cfg["live_enabled"])

    if live_blocked:
        st.error("LIVE endpoint detected, but LIVE_TRADING_ENABLED is false. Orders are blocked.")

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("Submit Bracket Ladder Orders"):
            if not cfg["configured"]:
                st.error("Alpaca is not configured.")
            elif live_blocked:
                st.error("Live trading is blocked by LIVE_TRADING_ENABLED=false.")
            elif arm_text != "ARM PAPER TRADE" and cfg["is_paper"]:
                st.error("Arming phrase incorrect.")
            elif not cfg["is_paper"] and arm_text != "ARM LIVE TRADE":
                st.error("Live mode requires exact phrase: ARM LIVE TRADE")
            elif not ok_safety:
                st.error("Safety check did not pass.")
            elif not broker_orders:
                st.error("No valid broker orders generated.")
            else:
                results = []
                for payload in broker_orders:
                    ok, msg, data = alpaca_submit_order(cfg, payload)
                    results.append({"ok": ok, "message": msg, "order": data if ok else None, "payload": payload})
                st.write("Submission results:")
                st.json(results)

    with col_b:
        if st.button("Cancel All Open Alpaca Orders"):
            ok, msg, data = alpaca_cancel_all_orders(cfg)
            if ok:
                st.success(msg)
                st.write(data)
            else:
                st.error(msg)

with tabs[13]:
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

st.caption("v32 adds Adaptive Execution: converts ranked setups into valid entry, stop, target, shares, and Alpaca bracket-order ladders.")
