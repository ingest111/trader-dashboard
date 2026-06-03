
import os
from datetime import datetime, date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


# ============================================================
# DEON'S TRADER DASHBOARD v19
# Production reset:
# Market Health + Opportunity Scanner + Best Trade Card
# Trade Validator + Journal + Robinhood CSV Audit + Charts
# ============================================================

st.set_page_config(page_title="Deon's Trader Dashboard v19", layout="wide")

DEFAULT_WATCHLIST = ["NVDA", "MRVL", "CRDO", "MU", "TSM", "AVGO", "PLTR", "AMD"]

DEFAULT_SCAN_UNIVERSE = [
    "NVDA", "AMD", "AVGO", "ARM", "MU", "TSM", "MRVL", "CRDO",
    "PLTR", "TEM", "APP", "HOOD", "HIMS", "SOFI", "RDDT",
    "META", "AMZN", "MSFT", "GOOGL", "TSLA", "COIN", "MSTR",
    "SMCI", "DELL", "ORCL", "CEG", "VRT", "ANET",
]

MARKETS = ["SPY", "QQQ", "^VIX", "^TNX"]

SECTOR_MAP = {
    "NVDA": "Semiconductors",
    "AMD": "Semiconductors",
    "AVGO": "Semiconductors",
    "ARM": "Semiconductors",
    "MU": "Semiconductors",
    "TSM": "Semiconductors",
    "MRVL": "Semiconductors",
    "CRDO": "Semiconductors",
    "SMCI": "AI Infrastructure",
    "DELL": "AI Infrastructure",
    "VRT": "AI Infrastructure",
    "ANET": "AI Infrastructure",
    "PLTR": "AI Software",
    "TEM": "AI Software",
    "APP": "Software Momentum",
    "MSFT": "Mega Cap Tech",
    "GOOGL": "Mega Cap Tech",
    "META": "Mega Cap Tech",
    "AMZN": "Mega Cap Tech",
    "HOOD": "Fintech Momentum",
    "SOFI": "Fintech Momentum",
    "COIN": "Crypto Momentum",
    "MSTR": "Crypto Momentum",
    "HIMS": "Consumer Momentum",
    "RDDT": "Consumer Momentum",
    "TSLA": "High Beta Momentum",
    "ORCL": "Enterprise Software",
    "CEG": "Power / Energy",
}

JOURNAL_FILE = "trade_journal_v19.csv"


# ============================================================
# DATA
# ============================================================

@st.cache_data(ttl=60)
def get_data(ticker, period="3mo", interval="1d"):
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False,
        )

        if df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        needed = ["Open", "High", "Low", "Close", "Volume"]
        for col in needed:
            if col not in df.columns:
                return pd.DataFrame()

        return df.dropna()

    except Exception:
        return pd.DataFrame()


def pct_change(df, bars):
    if df.empty or len(df) <= bars:
        return np.nan
    try:
        return ((float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-bars])) - 1) * 100
    except Exception:
        return np.nan


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def clean_money(x):
    if pd.isna(x):
        return 0.0

    s = str(x).replace("$", "").replace(",", "").strip()
    negative = "(" in s and ")" in s
    s = s.replace("(", "").replace(")", "")

    try:
        value = float(s)
        return -value if negative else value
    except Exception:
        return 0.0


def clean_number(x):
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return 0.0


# ============================================================
# MARKET HEALTH
# ============================================================

def build_market_context():
    rows = []

    for ticker in MARKETS:
        df = get_data(ticker, "3mo", "1d")
        if df.empty:
            continue

        close = safe_float(df["Close"].iloc[-1])
        ma20 = safe_float(df["Close"].rolling(20).mean().iloc[-1], close)
        trend = "Above 20MA" if close >= ma20 else "Below 20MA"

        rows.append({
            "Market": ticker,
            "Price": round(close, 2),
            "1D %": round(pct_change(df, 2), 2),
            "5D %": round(pct_change(df, 6), 2),
            "1M %": round(pct_change(df, 22), 2),
            "Trend": trend,
        })

    return pd.DataFrame(rows)


def market_health(market_df):
    if market_df.empty:
        return {
            "Regime": "Unknown",
            "Light": "GRAY",
            "Score": 0,
            "Reason": "Market data unavailable",
            "Risk Mode": "Wait",
        }

    def get_value(symbol, col):
        values = market_df.loc[market_df["Market"] == symbol, col].values
        if len(values) == 0:
            return 0
        return safe_float(values[0])

    spy_1d = get_value("SPY", "1D %")
    qqq_1d = get_value("QQQ", "1D %")
    vix_1d = get_value("^VIX", "1D %")

    spy_5d = get_value("SPY", "5D %")
    qqq_5d = get_value("QQQ", "5D %")

    score = 50

    score += 15 if spy_1d > 0 else -15
    score += 15 if qqq_1d > 0 else -15
    score += 10 if spy_5d > 0 else -10
    score += 10 if qqq_5d > 0 else -10
    score += 10 if vix_1d <= 0 else -20

    score = int(max(0, min(100, score)))

    if score >= 70:
        light = "GREEN"
        regime = "Bullish"
        risk_mode = "Normal risk"
        reason = "Indexes constructive and volatility contained"
    elif score >= 45:
        light = "YELLOW"
        regime = "Mixed"
        risk_mode = "Reduced risk"
        reason = "Mixed index backdrop or volatility pressure"
    else:
        light = "RED"
        regime = "Defensive"
        risk_mode = "Capital preservation"
        reason = "Weak index backdrop or elevated volatility"

    return {
        "Regime": regime,
        "Light": light,
        "Score": score,
        "Reason": reason,
        "Risk Mode": risk_mode,
    }


def show_market_health(market_df, health):
    st.header("Market Health Engine")
    st.dataframe(market_df, use_container_width=True)

    if health["Light"] == "GREEN":
        st.success("GREEN - Aggressive but controlled")
    elif health["Light"] == "YELLOW":
        st.warning("YELLOW - Selective only")
    elif health["Light"] == "RED":
        st.error("RED - Capital preservation")
    else:
        st.info("UNKNOWN - Wait")

    st.progress(int(health["Score"]))

    c1, c2, c3 = st.columns(3)
    c1.metric("Market Score", f"{health['Score']}/100")
    c2.metric("Regime", health["Regime"])
    c3.metric("Risk Mode", health["Risk Mode"])

    st.caption(health["Reason"])


# ============================================================
# SCANNER ENGINE
# ============================================================

def intraday_context(ticker):
    intraday = get_data(ticker, "1d", "5m")

    if intraday.empty or len(intraday) < 3:
        return {
            "Intraday Trend": "Unknown",
            "OR High": np.nan,
            "OR Low": np.nan,
            "OR Status": "Unknown",
            "OR Zone": "Unknown",
            "OR Position": np.nan,
            "Above VWAP": False,
            "VWAP": np.nan,
        }

    current = safe_float(intraday["Close"].iloc[-1])

    typical = (intraday["High"] + intraday["Low"] + intraday["Close"]) / 3
    volume_sum = safe_float(intraday["Volume"].sum())

    if volume_sum > 0:
        vwap = safe_float((typical * intraday["Volume"]).sum() / volume_sum, current)
    else:
        vwap = current

    opening_range = intraday.head(3)
    or_high = safe_float(opening_range["High"].max())
    or_low = safe_float(opening_range["Low"].min())
    or_range = or_high - or_low

    if or_range > 0:
        or_position = (current - or_low) / or_range
    else:
        or_position = np.nan

    if current > or_high:
        or_status = "Above OR High"
    elif current < or_low:
        or_status = "Below OR Low"
    else:
        or_status = "Inside OR"

    if np.isnan(or_position):
        or_zone = "Unknown"
    elif or_position > 1:
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

    if above_vwap and current > or_high:
        intraday_trend = "Bullish ORB"
    elif above_vwap and or_zone in ["Near breakout", "Upper range"]:
        intraday_trend = "Constructive"
    elif current < vwap and current < or_low:
        intraday_trend = "Bearish ORB"
    elif or_zone in ["Near breakdown", "Breakdown"]:
        intraday_trend = "Weak intraday"
    else:
        intraday_trend = "Choppy"

    return {
        "Intraday Trend": intraday_trend,
        "OR High": round(or_high, 2),
        "OR Low": round(or_low, 2),
        "OR Status": or_status,
        "OR Zone": or_zone,
        "OR Position": round(or_position, 2) if not np.isnan(or_position) else np.nan,
        "Above VWAP": bool(above_vwap),
        "VWAP": round(vwap, 2),
    }


def relative_strength_score(stock_df, spy_df):
    if stock_df.empty or spy_df.empty:
        return 50

    stock_5d = pct_change(stock_df, 6)
    stock_1m = pct_change(stock_df, 22)
    spy_5d = pct_change(spy_df, 6)
    spy_1m = pct_change(spy_df, 22)

    if any(np.isnan(x) for x in [stock_5d, stock_1m, spy_5d, spy_1m]):
        return 50

    spread = ((stock_5d - spy_5d) * 2) + (stock_1m - spy_1m)
    score = 50 + spread

    return int(max(0, min(100, round(score))))


def gap_percent(df):
    if df.empty or len(df) < 2:
        return 0.0

    prior_close = safe_float(df["Close"].iloc[-2])
    today_open = safe_float(df["Open"].iloc[-1])

    if prior_close <= 0:
        return 0.0

    return round(((today_open / prior_close) - 1) * 100, 2)


def pattern_label(row_data):
    if row_data["Intraday Trend"] == "Bullish ORB":
        return "Bullish ORB"
    if row_data["OR Zone"] == "Near breakout":
        return "OR Breakout Watch"
    if row_data["Above VWAP"] and row_data["Above 20MA"] and row_data["Above 50MA"]:
        return "VWAP Continuation"
    if row_data["Daily Breakout"]:
        return "Daily Breakout"
    if row_data["Near 20D High"]:
        return "Near Daily Breakout"
    if row_data["Intraday Trend"] in ["Weak intraday", "Bearish ORB"]:
        return "Weak / Breakdown"
    return "No Clear Pattern"


def analyze_symbol(ticker, spy_df, health, cash_available, risk_per_trade):
    df = get_data(ticker, "3mo", "1d")
    if df.empty or len(df) < 50:
        return None

    close = safe_float(df["Close"].iloc[-1])
    ma20 = safe_float(df["Close"].rolling(20).mean().iloc[-1], close)
    ma50 = safe_float(df["Close"].rolling(50).mean().iloc[-1], close)

    high20 = safe_float(df["High"].rolling(20).max().iloc[-2], close)
    low10 = safe_float(df["Low"].rolling(10).min().iloc[-1], close * 0.95)

    one_day = pct_change(df, 2)
    five_day = pct_change(df, 6)
    one_month = pct_change(df, 22)

    avg_vol20 = safe_float(df["Volume"].rolling(20).mean().iloc[-1])
    rel_vol = safe_float(df["Volume"].iloc[-1]) / avg_vol20 if avg_vol20 > 0 else 0

    above20 = close >= ma20
    above50 = close >= ma50

    dist20 = ((close / ma20) - 1) * 100 if ma20 > 0 else 0
    near_high = abs((close / high20) - 1) * 100 <= 3 if high20 > 0 else False
    breakout = close > high20 if high20 > 0 else False

    rs_score = relative_strength_score(df, spy_df)
    gap = gap_percent(df)
    intra = intraday_context(ticker)

    base = {
        "Above 20MA": above20,
        "Above 50MA": above50,
        "Daily Breakout": breakout,
        "Near 20D High": near_high,
        **intra,
    }

    pattern = pattern_label(base)

    score = 0

    if above20:
        score += 10
    if above50:
        score += 10
    if five_day > 3:
        score += 10
    if one_month > 8:
        score += 10
    if rel_vol >= 1.25:
        score += 8
    if near_high:
        score += 8
    if breakout:
        score += 12
    if intra["OR Zone"] in ["Near breakout", "Breakout"]:
        score += 15
    if intra["OR Zone"] == "Upper range":
        score += 8
    if intra["OR Zone"] in ["Near breakdown", "Breakdown"]:
        score -= 18
    if intra["Intraday Trend"] == "Bullish ORB":
        score += 18
    if intra["Intraday Trend"] == "Bearish ORB":
        score -= 22
    if intra["Above VWAP"]:
        score += 8
    if rs_score >= 80:
        score += 10
    elif rs_score >= 65:
        score += 5
    elif rs_score < 40:
        score -= 8
    if gap >= 2 and intra["Above VWAP"]:
        score += 5
    elif gap <= -2:
        score -= 5
    if dist20 > 15:
        score -= 10
    if one_day > 8:
        score -= 8

    if health["Light"] == "GREEN":
        score += 8
    elif health["Light"] == "RED":
        score -= 12

    score = max(0, min(100, round(score, 1)))

    # Probability is intentionally related to score but not identical.
    probability = int(max(0, min(95, round(35 + (score * 0.55)))))

    if probability >= 80:
        grade = "A+"
    elif probability >= 70:
        grade = "A"
    elif probability >= 60:
        grade = "B"
    elif probability >= 50:
        grade = "C"
    else:
        grade = "No Trade"

    stop = round(max(low10, close * 0.94), 2)
    risk_per_share = max(0, close - stop)

    target1 = round(close + (risk_per_share * 1.5), 2) if risk_per_share > 0 else round(close * 1.05, 2)
    target2 = round(close + (risk_per_share * 2.0), 2) if risk_per_share > 0 else round(close * 1.10, 2)

    reward_risk = ((target2 - close) / risk_per_share) if risk_per_share > 0 else 0

    expected_value = 0
    if risk_per_share > 0:
        probability_decimal = probability / 100
        reward = target1 - close
        expected_value = (probability_decimal * reward) - ((1 - probability_decimal) * risk_per_share)

    if score >= 75 and intra["OR Status"] == "Above OR High" and expected_value > 0:
        signal = "BUY NOW"
    elif score >= 62 and intra["OR Zone"] in ["Near breakout", "Breakout"]:
        signal = "BUY ON BREAKOUT"
    elif score >= 55:
        signal = "WATCH"
    else:
        signal = "WAIT"

    if intra["OR Status"] == "Below OR Low" or expected_value < 0:
        signal = "AVOID" if score < 45 else signal

    max_risk_dollars = cash_available * risk_per_trade
    if risk_per_share > 0:
        shares_by_risk = max_risk_dollars / risk_per_share
        shares_by_cash = cash_available / close if close > 0 else 0
        suggested_shares = min(shares_by_risk, shares_by_cash)
    else:
        suggested_shares = 0

    if signal not in ["BUY NOW", "BUY ON BREAKOUT"] or grade in ["No Trade", "C"] or expected_value <= 0:
        suggested_shares = 0

    suggested_position = suggested_shares * close

    if health["Light"] == "RED":
        suggested_position *= 0.5
        suggested_shares = suggested_position / close if close > 0 else 0

    return {
        "Ticker": ticker,
        "Sector": SECTOR_MAP.get(ticker, "Other"),
        "Signal": signal,
        "Pattern": pattern,
        "Price": round(close, 2),
        "Score": score,
        "Probability %": probability,
        "Grade": grade,
        "RS Score": rs_score,
        "Gap %": gap,
        "1D %": round(one_day, 2),
        "5D %": round(five_day, 2),
        "1M %": round(one_month, 2),
        "Rel Vol": round(rel_vol, 2),
        "Above VWAP": intra["Above VWAP"],
        "VWAP": intra["VWAP"],
        "Intraday Trend": intra["Intraday Trend"],
        "OR Status": intra["OR Status"],
        "OR Zone": intra["OR Zone"],
        "OR Position": intra["OR Position"],
        "OR High": intra["OR High"],
        "OR Low": intra["OR Low"],
        "20MA": round(ma20, 2),
        "50MA": round(ma50, 2),
        "Dist 20MA %": round(dist20, 2),
        "Stop": stop,
        "Target 1": target1,
        "Target 2": target2,
        "Reward/Risk": round(reward_risk, 2),
        "EV / Share": round(expected_value, 2),
        "Suggested Shares": round(suggested_shares, 4),
        "Suggested Position $": round(suggested_position, 2),
        "Dollar Risk": round(suggested_shares * risk_per_share, 2),
    }


def scan_symbols(symbols, health, cash_available, risk_per_trade):
    spy_df = get_data("SPY", "3mo", "1d")
    rows = []
    seen = set()

    for symbol in symbols:
        symbol = symbol.strip().upper()
        if not symbol or symbol in seen:
            continue

        seen.add(symbol)
        result = analyze_symbol(symbol, spy_df, health, cash_available, risk_per_trade)

        if result is not None:
            rows.append(result)

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)

    return out.sort_values(
        ["EV / Share", "Probability %", "Score", "RS Score"],
        ascending=False,
    ).reset_index(drop=True)


# ============================================================
# VISUAL COMPONENTS
# ============================================================

def show_top_trade_card(scan_df, health):
    st.header("Top Trade of the Day")

    if scan_df.empty:
        st.info("No scan results yet.")
        return

    best = scan_df.iloc[0]

    if health["Light"] == "RED" and best["Signal"] not in ["BUY NOW", "BUY ON BREAKOUT"]:
        st.error("No approved trade yet. Market is defensive and best candidate is only a watch.")
    elif best["Suggested Position $"] > 0:
        st.success(f"Best actionable candidate: {best['Ticker']}")
    else:
        st.warning(f"Best watch candidate: {best['Ticker']}")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Ticker", best["Ticker"])
    c2.metric("Signal", best["Signal"])
    c3.metric("Grade", best["Grade"])
    c4.metric("Probability", f"{best['Probability %']}%")
    c5.metric("Score", best["Score"])

    c6, c7, c8, c9 = st.columns(4)
    c6.metric("Entry Area", f"${best['Price']:.2f}")
    c7.metric("Stop", f"${best['Stop']:.2f}")
    c8.metric("Target 1", f"${best['Target 1']:.2f}")
    c9.metric("Target 2", f"${best['Target 2']:.2f}")

    c10, c11, c12, c13 = st.columns(4)
    c10.metric("Suggested Position", f"${best['Suggested Position $']:,.2f}")
    c11.metric("Shares", f"{best['Suggested Shares']:.4f}")
    c12.metric("Dollar Risk", f"${best['Dollar Risk']:,.2f}")
    c13.metric("EV / Share", f"${best['EV / Share']:.2f}")

    st.write(f"Sector: **{best['Sector']}**")
    st.write(f"Pattern: **{best['Pattern']}**")
    st.write(f"Intraday: **{best['Intraday Trend']}** | OR Zone: **{best['OR Zone']}** | Above VWAP: **{best['Above VWAP']}**")


def show_checklist(row, health):
    st.header("Trade Checklist")

    if row is None:
        st.info("No candidate selected.")
        return

    checks = [
        ("Market not RED", health["Light"] != "RED"),
        ("Above VWAP", bool(row["Above VWAP"])),
        ("Near/above OR breakout", row["OR Zone"] in ["Near breakout", "Breakout"]),
        ("Probability >= 60%", row["Probability %"] >= 60),
        ("Reward/Risk >= 1.5", row["Reward/Risk"] >= 1.5),
        ("Expected value positive", row["EV / Share"] > 0),
        ("Relative strength >= 60", row["RS Score"] >= 60),
        ("Not extended over 20MA", row["Dist 20MA %"] <= 12),
    ]

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)

    st.write(f"Checklist Score: **{passed}/{total}**")

    for label, ok in checks:
        st.write(("YES - " if ok else "NO - ") + label)

    if passed == total:
        st.success("TRADEABLE")
    elif passed >= 6:
        st.warning("WATCH ONLY / WAIT FOR TRIGGER")
    else:
        st.error("NO TRADE")


def show_do_not_trade(scan_df):
    st.header("Do Not Trade List")

    if scan_df.empty:
        st.info("No scan results.")
        return

    avoid = scan_df[
        (scan_df["Signal"] == "AVOID") |
        (scan_df["EV / Share"] <= 0) |
        (scan_df["Above VWAP"] == False) |
        (scan_df["RS Score"] < 40)
    ].copy()

    if avoid.empty:
        st.success("No major avoid names from current scan.")
        return

    reasons = []

    for _, row in avoid.iterrows():
        r = []
        if row["Signal"] == "AVOID":
            r.append("Avoid signal")
        if row["EV / Share"] <= 0:
            r.append("Negative EV")
        if not row["Above VWAP"]:
            r.append("Below VWAP")
        if row["RS Score"] < 40:
            r.append("Weak RS")
        reasons.append(", ".join(r))

    avoid["Reason"] = reasons

    st.dataframe(
        avoid[["Ticker", "Sector", "Price", "Signal", "Reason", "RS Score", "EV / Share", "Intraday Trend", "OR Zone"]],
        use_container_width=True,
        height=340,
    )


def show_opportunity_scanner(scan_df):
    st.header("Opportunity Scanner")

    if scan_df.empty:
        st.warning("No scanner results.")
        return

    top = scan_df.head(10).copy()
    top.insert(0, "Rank", range(1, len(top) + 1))

    st.subheader("Top 10 Ranked Opportunities")
    st.dataframe(
        top[[
            "Rank", "Ticker", "Sector", "Signal", "Pattern", "Price", "Probability %",
            "Grade", "Score", "RS Score", "Gap %", "EV / Share", "Suggested Position $",
            "Intraday Trend", "OR Zone", "Above VWAP",
        ]],
        use_container_width=True,
        height=420,
    )


def show_sector_strength(scan_df):
    st.header("Sector Strength Ranking")

    if scan_df.empty:
        st.info("No scan data.")
        return

    sector = (
        scan_df.groupby("Sector")
        .agg(
            Names=("Ticker", "count"),
            Avg_RS=("RS Score", "mean"),
            Avg_Score=("Score", "mean"),
            Avg_5D=("5D %", "mean"),
            Avg_1M=("1M %", "mean"),
            Positive_EV=("EV / Share", lambda x: (x > 0).sum()),
        )
        .reset_index()
    )

    for col in ["Avg_RS", "Avg_Score", "Avg_5D", "Avg_1M"]:
        sector[col] = sector[col].round(2)

    sector = sector.sort_values(["Avg_RS", "Avg_Score"], ascending=False)

    st.dataframe(sector, use_container_width=True, height=380)


def show_gap_scanner(scan_df):
    st.header("Gap Scanner")

    if scan_df.empty:
        st.info("No scan data.")
        return

    gap = scan_df.sort_values("Gap %", ascending=False)

    st.subheader("Positive Gaps")
    st.dataframe(
        gap[gap["Gap %"] > 0][["Ticker", "Sector", "Gap %", "Price", "Signal", "RS Score", "Above VWAP", "EV / Share"]],
        use_container_width=True,
        height=280,
    )

    st.subheader("Negative Gaps")
    st.dataframe(
        gap[gap["Gap %"] < 0][["Ticker", "Sector", "Gap %", "Price", "Signal", "RS Score", "Above VWAP", "EV / Share"]],
        use_container_width=True,
        height=280,
    )


def show_watchlist_builder(scan_df, health):
    st.header("AI Watchlist Builder")

    if scan_df.empty:
        st.info("No scan data.")
        return

    if health["Light"] == "RED":
        candidates = scan_df[(scan_df["RS Score"] >= 60) & (scan_df["Above VWAP"] == True)].head(8)
        st.warning("RED market: conservative watchlist only.")
    else:
        candidates = scan_df[(scan_df["Probability %"] >= 50) | (scan_df["RS Score"] >= 65)].head(10)

    if candidates.empty:
        st.error("No suitable candidates. Cash is the watchlist.")
        return

    st.code(",".join(candidates["Ticker"].tolist()))

    st.dataframe(
        candidates[["Ticker", "Sector", "Signal", "Pattern", "Probability %", "RS Score", "EV / Share"]],
        use_container_width=True,
    )


# ============================================================
# TRADE VALIDATOR
# ============================================================

def show_trade_validator(health):
    st.header("Pre-Trade Validator")

    c1, c2, c3, c4 = st.columns(4)
    ticker = c1.text_input("Ticker", value="")
    entry = c2.number_input("Entry", min_value=0.0, step=0.01)
    stop = c3.number_input("Stop", min_value=0.0, step=0.01)
    target = c4.number_input("Target", min_value=0.0, step=0.01)

    c5, c6, c7, c8 = st.columns(4)
    shares = c5.number_input("Shares", min_value=0.0, step=0.0001, format="%.6f")
    probability = c6.slider("Probability %", 0, 100, 60)
    above_vwap = c7.checkbox("Above VWAP?")
    above_or = c8.checkbox("Above OR High?")

    already_traded = st.checkbox("Already traded today?")
    revenge_risk = st.checkbox("Revenge trade risk?")

    if st.button("Validate"):
        fails = []
        passes = []

        if entry <= 0 or stop <= 0 or target <= 0:
            fails.append("Entry, stop, and target must be above zero.")
        elif stop >= entry:
            fails.append("Stop must be below entry.")
        elif target <= entry:
            fails.append("Target must be above entry.")
        else:
            risk = entry - stop
            reward = target - entry
            rr = reward / risk if risk > 0 else 0
            if rr >= 1.5:
                passes.append(f"Reward/risk acceptable: {rr:.2f}")
            else:
                fails.append(f"Reward/risk too weak: {rr:.2f}")

        if health["Light"] == "RED":
            fails.append("Market is RED. Only elite setups allowed.")
        else:
            passes.append("Market is not RED.")

        if above_vwap:
            passes.append("Above VWAP.")
        else:
            fails.append("Below VWAP or unconfirmed.")

        if above_or:
            passes.append("Above opening range high.")
        else:
            fails.append("No OR breakout confirmation.")

        if probability >= 60:
            passes.append("Probability acceptable.")
        else:
            fails.append("Probability too low.")

        if shares > 0:
            passes.append("Share size entered.")
        else:
            fails.append("Shares must be greater than zero.")

        if already_traded:
            fails.append("Already traded today. Avoid overtrading.")
        if revenge_risk:
            fails.append("Revenge trade risk flagged.")

        if fails:
            st.error("FAIL - Do not take this trade yet.")
        else:
            st.success("PASS - Trade meets minimum rules.")

        if entry > 0 and stop > 0 and target > 0 and shares > 0 and entry > stop and target > entry:
            risk_per_share = entry - stop
            reward_per_share = target - entry
            rr = reward_per_share / risk_per_share
            dollar_risk = risk_per_share * shares
            dollar_reward = reward_per_share * shares
            ev = ((probability / 100) * dollar_reward) - ((1 - probability / 100) * dollar_risk)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Risk / Share", f"${risk_per_share:.2f}")
            m2.metric("Reward / Share", f"${reward_per_share:.2f}")
            m3.metric("Reward/Risk", f"{rr:.2f}")
            m4.metric("Expected Value", f"${ev:.2f}")

        st.subheader("Pass Reasons")
        for item in passes:
            st.write("YES - " + item)

        st.subheader("Fail Reasons")
        for item in fails:
            st.write("NO - " + item)


# ============================================================
# JOURNAL + CSV AUDIT
# ============================================================

def show_journal():
    journal = load_journal()
    journal_report(journal)

    st.subheader("Add Trade Journal Entry")

    with st.form("journal_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        trade_date = c1.date_input("Date", value=date.today())
        ticker = c2.text_input("Ticker")
        pattern = c3.selectbox(
            "Pattern",
            ["Bullish ORB", "OR Breakout Watch", "VWAP Continuation", "Daily Breakout",
             "Near Daily Breakout", "Weak / Breakdown", "No Clear Pattern", "Other"],
        )
        grade = c4.selectbox("Grade", ["A+", "A", "B", "C", "No Trade"])

        c5, c6, c7, c8 = st.columns(4)
        signal = c5.selectbox("Signal", ["BUY NOW", "BUY ON BREAKOUT", "WATCH", "WAIT", "AVOID", "Manual"])
        entry = c6.number_input("Entry", min_value=0.0, step=0.01)
        exit_price = c7.number_input("Exit", min_value=0.0, step=0.01)
        stop = c8.number_input("Stop", min_value=0.0, step=0.01)

        c9, c10, c11, c12 = st.columns(4)
        target = c9.number_input("Target", min_value=0.0, step=0.01)
        shares = c10.number_input("Shares", min_value=0.0, step=0.0001, format="%.6f")
        mistake = c11.selectbox(
            "Mistake",
            ["None", "Chased", "Ignored stop", "Sold too early", "Entered without trigger",
             "Oversized", "Revenge trade", "Other"],
        )
        notes = c12.text_input("Notes")

        submitted = st.form_submit_button("Add Journal Entry")

        if submitted:
            ticker_clean = ticker.strip().upper()

            if not ticker_clean:
                st.error("Ticker is required.")
            elif entry <= 0 or exit_price <= 0 or shares <= 0:
                st.error("Entry, exit, and shares must be greater than zero.")
            else:
                pnl = (exit_price - entry) * shares
                ret = ((exit_price / entry) - 1) * 100
                result = "Win" if pnl > 0 else "Loss" if pnl < 0 else "Breakeven"

                row = {
                    "Date": trade_date.isoformat(),
                    "Ticker": ticker_clean,
                    "Pattern": pattern,
                    "Setup Grade": grade,
                    "Signal": signal,
                    "Market Regime": "",
                    "Entry": round(entry, 2),
                    "Exit": round(exit_price, 2),
                    "Stop": round(stop, 2),
                    "Target": round(target, 2),
                    "Shares": round(shares, 6),
                    "P/L": round(pnl, 2),
                    "Return %": round(ret, 2),
                    "Result": result,
                    "Mistake": mistake,
                    "Pre-Trade Screenshot": "",
                    "Exit Screenshot": "",
                    "Notes": notes,
                }

                journal = pd.concat([journal, pd.DataFrame([row])], ignore_index=True)
                save_journal(journal)
                st.success("Trade saved. Click Refresh to update the report card.")

    if not journal.empty and st.button("Clear Journal"):
        save_journal(empty_journal())
        st.warning("Journal cleared. Click Refresh.")


def show_robinhood_upload():
    uploaded = st.file_uploader("Upload Robinhood CSV trade history", type=["csv"])

    if uploaded is None:
        st.info("Upload a Robinhood CSV to audit realized trade performance.")
        return

    trade_history_audit(uploaded)


def trade_history_audit(uploaded_file):
    try:
        raw = pd.read_csv(uploaded_file, engine="python", on_bad_lines="skip")
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return

    raw.columns = [str(c).strip() for c in raw.columns]
    required = ["Activity Date", "Instrument", "Trans Code", "Quantity", "Price", "Amount"]
    missing = [c for c in required if c not in raw.columns]

    if missing:
        st.error(f"Missing required columns: {missing}")
        st.write("Columns found:", list(raw.columns))
        return

    df = raw.copy()
    df["Amount Clean"] = df["Amount"].apply(clean_money)
    df["Quantity Clean"] = df["Quantity"].apply(clean_number)
    df["Trans Code"] = df["Trans Code"].astype(str).str.strip()
    df["Instrument"] = df["Instrument"].astype(str).str.strip()

    trades = df[df["Trans Code"].isin(["Buy", "Sell"])].copy()

    if trades.empty:
        st.warning("No Buy/Sell trades found.")
        return

    rows = []

    for ticker, group in trades.groupby("Instrument"):
        buys = group[group["Trans Code"] == "Buy"]
        sells = group[group["Trans Code"] == "Sell"]

        buy_cost = abs(buys["Amount Clean"].sum())
        sell_proceeds = sells["Amount Clean"].sum()
        buy_qty = buys["Quantity Clean"].sum()
        sell_qty = sells["Quantity Clean"].sum()
        net_qty = buy_qty - sell_qty
        pnl = sell_proceeds - buy_cost
        ret = (pnl / buy_cost * 100) if buy_cost > 0 else np.nan

        rows.append({
            "Ticker": ticker,
            "Status": "Closed" if abs(net_qty) < 0.0001 else "Open / Partial",
            "Buy Qty": round(buy_qty, 6),
            "Sell Qty": round(sell_qty, 6),
            "Net Qty": round(net_qty, 6),
            "Buy Cost": round(buy_cost, 2),
            "Sell Proceeds": round(sell_proceeds, 2),
            "P/L": round(pnl, 2),
            "Return %": round(ret, 2) if not np.isnan(ret) else None,
            "Rows": len(group),
        })

    summary = pd.DataFrame(rows).sort_values("P/L", ascending=False)

    total_cost = summary["Buy Cost"].sum()
    total_pnl = summary["P/L"].sum()
    total_return = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    winners = summary[summary["P/L"] > 0]
    losers = summary[summary["P/L"] < 0]
    win_rate = (len(winners) / len(summary) * 100) if len(summary) else 0
    profit_factor = winners["P/L"].sum() / abs(losers["P/L"].sum()) if not losers.empty else np.inf

    st.header("Robinhood CSV Audit")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total P/L", f"${total_pnl:,.2f}")
    c2.metric("Total Return", f"{total_return:.2f}%")
    c3.metric("Win Rate", f"{win_rate:.1f}%")
    c4.metric("Profit Factor", "infinity" if profit_factor == np.inf else f"{profit_factor:.2f}")

    st.dataframe(summary, use_container_width=True)
    st.caption("CSV audits can overstate P/L if sells are included without their matching buys.")


# ============================================================
# CHARTS
# ============================================================

def make_chart(ticker, timeframe):
    if timeframe == "5m intraday":
        df = get_data(ticker, "1d", "5m")
        title = f"{ticker} - 5m Intraday"
    elif timeframe == "15m intraday":
        df = get_data(ticker, "5d", "15m")
        title = f"{ticker} - 15m Intraday"
    else:
        df = get_data(ticker, "3mo", "1d")
        title = f"{ticker} - 3 Month Daily"

    if df.empty:
        return None

    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

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

    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], mode="lines", name="20MA"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], mode="lines", name="50MA"))

    if timeframe == "5m intraday" and len(df) >= 3:
        fig.add_hline(y=df.head(3)["High"].max(), line_dash="dash", annotation_text="OR High")
        fig.add_hline(y=df.head(3)["Low"].min(), line_dash="dash", annotation_text="OR Low")

    fig.update_layout(height=550, title=title, xaxis_rangeslider_visible=False)
    return fig


# ============================================================
# APP
# ============================================================

st.title("Deon's Trader Dashboard v19")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.sidebar.header("Settings")

watchlist_text = st.sidebar.text_area("Manual Watchlist", ",".join(DEFAULT_WATCHLIST), height=100)
scan_text = st.sidebar.text_area("Scanner Universe", ",".join(DEFAULT_SCAN_UNIVERSE), height=180)

cash_available = st.sidebar.number_input("Cash available", min_value=0.0, value=855.0, step=25.0)
risk_per_trade_pct = st.sidebar.number_input("Risk per trade %", min_value=0.25, max_value=10.0, value=3.0, step=0.25)
risk_per_trade = risk_per_trade_pct / 100

st.sidebar.write("Max risk per trade:", f"${cash_available * risk_per_trade:,.2f}")

if st.sidebar.button("Refresh now"):
    st.cache_data.clear()
    st.rerun()

manual_symbols = [x.strip().upper() for x in watchlist_text.split(",") if x.strip()]
scan_symbols_input = [x.strip().upper() for x in scan_text.split(",") if x.strip()]

market_df = build_market_context()
health = market_health(market_df)
show_market_health(market_df, health)

with st.spinner("Scanning stocks..."):
    scan_df = scan_symbols(scan_symbols_input, health, cash_available, risk_per_trade)

if scan_df.empty:
    st.error("No scanner data loaded. Reduce the scanner universe or refresh.")
    st.stop()

manual_df = scan_df[scan_df["Ticker"].isin(manual_symbols)].copy()

show_top_trade_card(scan_df, health)

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "Opportunity Scanner",
    "Trade Plan",
    "Do Not Trade",
    "Sector Strength",
    "Gap Scanner",
    "AI Watchlist",
    "Validator",
    "Journal / CSV",
    "Charts",
])

with tab1:
    show_opportunity_scanner(scan_df)

    st.subheader("Manual Watchlist Board")
    if manual_df.empty:
        st.info("None of the manual watchlist names returned usable data.")
    else:
        st.dataframe(
            manual_df[[
                "Ticker", "Sector", "Signal", "Pattern", "Price", "Probability %",
                "Grade", "Score", "RS Score", "EV / Share", "Suggested Position $",
                "Intraday Trend", "OR Zone", "Above VWAP",
            ]],
            use_container_width=True,
            height=360,
        )

with tab2:
    best_row = scan_df.iloc[0] if not scan_df.empty else None
    show_top_trade_card(scan_df, health)
    show_checklist(best_row, health)

with tab3:
    show_do_not_trade(scan_df)

with tab4:
    show_sector_strength(scan_df)

with tab5:
    show_gap_scanner(scan_df)

with tab6:
    show_watchlist_builder(scan_df, health)

with tab7:
    show_trade_validator(health)

with tab8:
    sub1, sub2 = st.tabs(["Trade Journal", "Robinhood CSV Audit"])
    with sub1:
        show_journal()
    with sub2:
        show_robinhood_upload()

with tab9:
    selected = st.selectbox("Ticker", scan_df["Ticker"].tolist())
    timeframe = st.radio("Timeframe", ["5m intraday", "15m intraday", "3mo daily"], horizontal=True)
    chart = make_chart(selected, timeframe)
    if chart is not None:
        st.plotly_chart(chart, use_container_width=True)
    else:
        st.warning("Chart data unavailable.")

st.caption(
    "Data comes from Yahoo Finance via yfinance and may be delayed or incomplete. "
    "Use this dashboard as decision support, not blind execution."
)
