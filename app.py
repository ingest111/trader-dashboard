
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date
import os

# ============================================================
# DEON'S TRADER DASHBOARD v16
# v15 + Expanded Universe Scanner + Top Opportunities Engine
# ============================================================

st.set_page_config(page_title="Deon's Trader Dashboard v16", layout="wide")

DEFAULT_WATCHLIST = ["NVDA", "MRVL", "CRDO", "MU", "TSM", "AVGO", "PLTR", "AMD"]

SCAN_UNIVERSE = [
    "NVDA", "AMD", "AVGO", "ARM", "MU", "TSM", "MRVL", "CRDO",
    "PLTR", "TEM", "APP", "HOOD", "HIMS", "SOFI", "RDDT",
    "META", "AMZN", "MSFT", "GOOGL", "TSLA", "COIN", "MSTR",
    "SMCI", "DELL", "ORCL", "CEG", "VRT", "ANET",
]

MARKETS = ["SPY", "QQQ", "^VIX", "^TNX"]

DAY_TRADE_CAPITAL_DEFAULT = 855
RISK_PER_TRADE_DEFAULT = 0.03
JOURNAL_FILE = "trade_journal_v16.csv"


@st.cache_data(ttl=45)
def get_data(ticker, period="3mo", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except Exception:
        return pd.DataFrame()


def safe_pct_change(df, bars):
    if df.empty or len(df) <= bars:
        return np.nan
    try:
        return ((df["Close"].iloc[-1] / df["Close"].iloc[-bars]) - 1) * 100
    except Exception:
        return np.nan


def clean_money(x):
    if pd.isna(x):
        return 0.0
    s = str(x).replace("$", "").replace(",", "").strip()
    is_negative = "(" in s and ")" in s
    s = s.replace("(", "").replace(")", "")
    try:
        value = float(s)
        return -value if is_negative else value
    except ValueError:
        return 0.0


def clean_number(x):
    if pd.isna(x):
        return 0.0
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return 0.0


def empty_journal():
    return pd.DataFrame(columns=[
        "Date", "Ticker", "Pattern", "Setup Grade", "Signal", "Market Regime",
        "Entry", "Exit", "Stop", "Target", "Shares", "P/L", "Return %",
        "Result", "Mistake", "Pre-Trade Screenshot", "Exit Screenshot", "Notes",
    ])


def load_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            return pd.read_csv(JOURNAL_FILE)
        except Exception:
            return empty_journal()
    return empty_journal()


def save_journal(df):
    df.to_csv(JOURNAL_FILE, index=False)


def journal_report(journal):
    st.header("Trade Journal Report Card")

    if journal.empty:
        st.info("No journal entries yet. Add trades below to start tracking your real performance.")
        return

    journal = journal.copy()
    journal["P/L"] = pd.to_numeric(journal["P/L"], errors="coerce").fillna(0)
    journal["Return %"] = pd.to_numeric(journal["Return %"], errors="coerce").fillna(0)

    total_pnl = journal["P/L"].sum()
    wins = journal[journal["P/L"] > 0]
    losses = journal[journal["P/L"] < 0]

    win_rate = len(wins) / len(journal) * 100 if len(journal) else 0
    avg_win = wins["P/L"].mean() if not wins.empty else 0
    profit_factor = wins["P/L"].sum() / abs(losses["P/L"].sum()) if not losses.empty else np.inf

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Journal P/L", f"${total_pnl:,.2f}")
    c2.metric("Win Rate", f"{win_rate:.1f}%")
    c3.metric("Trades", len(journal))
    c4.metric("Avg Win", f"${avg_win:,.2f}")
    c5.metric("Profit Factor", "infinity" if profit_factor == np.inf else f"{profit_factor:.2f}")

    st.subheader("Journal Entries")
    st.dataframe(journal.sort_values("Date", ascending=False), use_container_width=True)

    st.subheader("Pattern Performance")
    pattern_perf = (
        journal.groupby("Pattern")
        .agg(
            Trades=("P/L", "count"),
            Total_PL=("P/L", "sum"),
            Avg_PL=("P/L", "mean"),
            Win_Rate=("P/L", lambda x: (x > 0).mean() * 100),
        )
        .reset_index()
        .sort_values("Total_PL", ascending=False)
    )
    pattern_perf["Total_PL"] = pattern_perf["Total_PL"].round(2)
    pattern_perf["Avg_PL"] = pattern_perf["Avg_PL"].round(2)
    pattern_perf["Win_Rate"] = pattern_perf["Win_Rate"].round(1)
    st.dataframe(pattern_perf, use_container_width=True)

    st.subheader("Mistake Tracker")
    mistakes = journal[journal["Mistake"].astype(str).str.lower() != "none"]
    if mistakes.empty:
        st.success("No recorded mistakes yet.")
    else:
        mistake_perf = (
            mistakes.groupby("Mistake")
            .agg(Count=("P/L", "count"), Total_PL=("P/L", "sum"), Avg_PL=("P/L", "mean"))
            .reset_index()
            .sort_values("Total_PL", ascending=True)
        )
        mistake_perf["Total_PL"] = mistake_perf["Total_PL"].round(2)
        mistake_perf["Avg_PL"] = mistake_perf["Avg_PL"].round(2)
        st.dataframe(mistake_perf, use_container_width=True)


def trade_history_audit(uploaded_file):
    try:
        raw = pd.read_csv(uploaded_file, engine="python", on_bad_lines="skip")
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return None

    raw.columns = [str(col).strip() for col in raw.columns]
    required_cols = ["Activity Date", "Instrument", "Trans Code", "Quantity", "Price", "Amount"]
    missing_cols = [col for col in required_cols if col not in raw.columns]

    if missing_cols:
        st.error(f"Missing required columns: {missing_cols}")
        st.write("Columns found:", list(raw.columns))
        return None

    df = raw.copy()
    df["Amount Clean"] = df["Amount"].apply(clean_money)
    df["Quantity Clean"] = df["Quantity"].apply(clean_number)
    df["Price Clean"] = df["Price"].apply(clean_number)
    df["Trans Code"] = df["Trans Code"].astype(str).str.strip()
    df["Instrument"] = df["Instrument"].astype(str).str.strip()

    trades = df[df["Trans Code"].isin(["Buy", "Sell"])].copy()
    if trades.empty:
        st.warning("No Buy/Sell trades found in the uploaded file.")
        return None

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
        return_pct = (pnl / buy_cost * 100) if buy_cost > 0 else np.nan
        rows.append({
            "Ticker": ticker,
            "Status": "Closed" if abs(net_qty) < 0.0001 else "Open / Partial",
            "Buy Qty": round(buy_qty, 6),
            "Sell Qty": round(sell_qty, 6),
            "Net Qty": round(net_qty, 6),
            "Buy Cost": round(buy_cost, 2),
            "Sell Proceeds": round(sell_proceeds, 2),
            "P/L": round(pnl, 2),
            "Return %": round(return_pct, 2) if not np.isnan(return_pct) else None,
            "Rows": len(group),
        })

    summary = pd.DataFrame(rows).sort_values("P/L", ascending=False)
    total_buy_cost = summary["Buy Cost"].sum()
    total_pnl = summary["P/L"].sum()
    total_return = (total_pnl / total_buy_cost * 100) if total_buy_cost > 0 else 0
    winners = summary[summary["P/L"] > 0]
    losers = summary[summary["P/L"] < 0]
    win_rate = (len(winners) / len(summary) * 100) if len(summary) else 0
    avg_win = winners["P/L"].mean() if not winners.empty else 0
    profit_factor = winners["P/L"].sum() / abs(losers["P/L"].sum()) if not losers.empty else np.inf

    st.header("Uploaded Robinhood CSV Audit")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total P/L", f"${total_pnl:,.2f}")
    col2.metric("Total Return", f"{total_return:.2f}%")
    col3.metric("Win Rate", f"{win_rate:.1f}%")
    col4.metric("Avg Winner", f"${avg_win:,.2f}")
    col5.metric("Profit Factor", "infinity" if profit_factor == np.inf else f"{profit_factor:.2f}")
    st.dataframe(summary, use_container_width=True)
    st.caption("Note: CSV audit may overstate P/L when the uploaded range contains sells without matching buys.")
    return summary


def market_context():
    rows = []
    for ticker in MARKETS:
        df = get_data(ticker, "5d", "1d")
        if df.empty:
            continue
        rows.append({
            "Market": ticker,
            "Price": round(float(df["Close"].iloc[-1]), 2),
            "1D %": round(safe_pct_change(df, 2), 2),
        })
    return pd.DataFrame(rows)


def get_market_regime(market_df):
    if market_df.empty or "Market" not in market_df.columns:
        return "Unknown", "Market data unavailable", 0, "GRAY"

    spy = market_df.loc[market_df["Market"] == "SPY", "1D %"].values
    qqq = market_df.loc[market_df["Market"] == "QQQ", "1D %"].values
    vix = market_df.loc[market_df["Market"] == "^VIX", "1D %"].values

    spy_val = spy[0] if len(spy) > 0 else 0
    qqq_val = qqq[0] if len(qqq) > 0 else 0
    vix_val = vix[0] if len(vix) > 0 else 0

    if spy_val > 0 and qqq_val > 0 and vix_val <= 0:
        return "Bullish", "SPY positive, QQQ positive, VIX calm", 8, "GREEN"
    if spy_val > 0 and qqq_val > 0 and vix_val > 0:
        return "Mixed", "SPY positive, QQQ positive, but VIX rising", 0, "YELLOW"
    return "Defensive", "Weak index backdrop or elevated volatility", -12, "RED"


def intraday_snapshot(ticker):
    intraday = get_data(ticker, "1d", "5m")
    if intraday.empty or len(intraday) < 3:
        return {
            "Intraday Trend": "Unknown", "OR High": np.nan, "OR Low": np.nan,
            "OR Status": "Unknown", "OR Position": np.nan, "OR Zone": "Unknown",
            "Above VWAP": False, "VWAP Approx": np.nan,
        }

    current = float(intraday["Close"].iloc[-1])
    typical = (intraday["High"] + intraday["Low"] + intraday["Close"]) / 3
    total_volume = intraday["Volume"].sum()
    vwap = float((typical * intraday["Volume"]).sum() / total_volume) if total_volume > 0 else current

    opening_range = intraday.head(3)
    or_high = float(opening_range["High"].max())
    or_low = float(opening_range["Low"].min())
    or_range = or_high - or_low
    or_position = (current - or_low) / or_range if or_range > 0 else np.nan

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

    above_vwap = current > vwap

    if above_vwap and current > or_high:
        trend = "Bullish ORB"
    elif above_vwap and or_zone in ["Near breakout", "Upper range"]:
        trend = "Constructive"
    elif current < vwap and current < or_low:
        trend = "Bearish ORB"
    elif or_zone in ["Near breakdown", "Breakdown"]:
        trend = "Weak intraday"
    else:
        trend = "Choppy"

    return {
        "Intraday Trend": trend, "OR High": round(or_high, 2), "OR Low": round(or_low, 2),
        "OR Status": or_status,
        "OR Position": round(or_position, 2) if not np.isnan(or_position) else np.nan,
        "OR Zone": or_zone, "Above VWAP": above_vwap, "VWAP Approx": round(vwap, 2),
    }


def setup_grade(probability):
    if probability >= 80:
        return "A+ Setup"
    if probability >= 70:
        return "A Setup"
    if probability >= 60:
        return "B Setup"
    if probability >= 50:
        return "C Setup"
    return "No Trade"


def probability_engine(row, regime):
    probability = 45
    if row["Signal"] == "BUY NOW":
        probability += 12
    elif row["Signal"] == "BUY ON OR BREAKOUT":
        probability += 8
    elif row["Signal"] == "WATCH":
        probability += 2
    elif row["Signal"] == "AVOID":
        probability -= 15

    if row["OR Zone"] in ["Breakout", "Near breakout"]:
        probability += 10
    elif row["OR Zone"] == "Upper range":
        probability += 5
    elif row["OR Zone"] == "Middle":
        probability -= 2
    elif row["OR Zone"] in ["Near breakdown", "Breakdown"]:
        probability -= 12

    if row["Intraday Trend"] == "Bullish ORB":
        probability += 12
    elif row["Intraday Trend"] == "Constructive":
        probability += 6
    elif row["Intraday Trend"] == "Weak intraday":
        probability -= 8
    elif row["Intraday Trend"] == "Bearish ORB":
        probability -= 15

    probability += 6 if row["Above VWAP"] else -4

    if row["Reward/Risk"] >= 2:
        probability += 8
    elif row["Reward/Risk"] >= 1.5:
        probability += 4
    elif row["Reward/Risk"] < 1:
        probability -= 10

    if row["Rel Vol"] >= 1.5:
        probability += 6
    elif row["Rel Vol"] >= 1.0:
        probability += 2
    elif row["Rel Vol"] < 0.75:
        probability -= 5

    if row["Dist 20MA %"] > 18:
        probability -= 12
    elif row["Dist 20MA %"] > 12:
        probability -= 6
    elif -2 <= row["Dist 20MA %"] <= 8:
        probability += 4

    if row["1D %"] > 8 or row["1D %"] < -3:
        probability -= 8

    if regime == "Bullish":
        probability += 6
    elif regime == "Defensive":
        probability -= 10

    return int(max(0, min(95, round(probability))))


def expected_value_per_share(row):
    price = row["Price"]
    stop = row["Stop"]
    target = row["Target 1"]
    probability = row["Probability %"] / 100
    if price <= 0 or stop <= 0 or target <= price or price <= stop:
        return 0.0
    reward = target - price
    risk = price - stop
    return round((probability * reward) - ((1 - probability) * risk), 2)


def kelly_fraction(row):
    probability = row["Probability %"] / 100
    rr = row["Reward/Risk"]
    if rr <= 0 or np.isnan(rr):
        return 0.0
    kelly = probability - ((1 - probability) / rr)
    return round(max(0.0, min(kelly, 0.25)) * 100, 2)


def capital_allocation(row, cash_available, risk_per_trade):
    if row["Setup Grade"] in ["No Trade", "C Setup"]:
        return 0.0, 0.0, "No edge"
    if row["Probability %"] < 60:
        return 0.0, 0.0, "Probability too low"
    if row["Expected Value / Share"] <= 0:
        return 0.0, 0.0, "Negative EV"
    if row["Signal"] not in ["BUY NOW", "BUY ON OR BREAKOUT"]:
        return 0.0, 0.0, "No entry trigger"

    price = row["Price"]
    stop = row["Stop"]
    if price <= 0 or stop <= 0 or price <= stop:
        return 0.0, 0.0, "Invalid risk"

    risk_dollars = cash_available * risk_per_trade
    risk_per_share = price - stop
    shares_by_risk = risk_dollars / risk_per_share
    shares_by_cash = cash_available / price
    shares = max(0, min(shares_by_risk, shares_by_cash))
    position_value = shares * price

    if row["Setup Grade"] == "A+ Setup":
        note = "Max planned size"
    elif row["Setup Grade"] == "A Setup":
        position_value *= 0.75
        shares = position_value / price
        note = "Three-quarter size"
    else:
        position_value *= 0.50
        shares = position_value / price
        note = "Half size"

    return round(shares, 4), round(position_value, 2), note


def classify_pattern(snap, breakout, near_breakout, above20, above50):
    if snap["Intraday Trend"] == "Bullish ORB":
        return "Bullish ORB"
    if snap["OR Zone"] == "Near breakout":
        return "OR Breakout Watch"
    if snap["Above VWAP"] and above20 and above50:
        return "VWAP Continuation"
    if breakout:
        return "Daily Breakout"
    if near_breakout:
        return "Near Daily Breakout"
    if snap["Intraday Trend"] in ["Weak intraday", "Bearish ORB"]:
        return "Weak / Breakdown"
    return "No Clear Pattern"


def analyze_ticker(ticker, regime, regime_points):
    daily = get_data(ticker, "3mo", "1d")
    if daily.empty or len(daily) < 50:
        return None

    close = float(daily["Close"].iloc[-1])
    ma20 = float(daily["Close"].rolling(20).mean().iloc[-1])
    ma50 = float(daily["Close"].rolling(50).mean().iloc[-1])
    high20 = float(daily["High"].rolling(20).max().iloc[-2])
    low10 = float(daily["Low"].rolling(10).min().iloc[-1])

    one_day = safe_pct_change(daily, 2)
    five_day = safe_pct_change(daily, 6)
    one_month = safe_pct_change(daily, 22)
    avg_vol20 = float(daily["Volume"].rolling(20).mean().iloc[-1])
    rel_vol = float(daily["Volume"].iloc[-1]) / avg_vol20 if avg_vol20 > 0 else np.nan
    dist20 = ((close / ma20) - 1) * 100

    above20 = close > ma20
    above50 = close > ma50
    near_breakout = abs((close / high20) - 1) * 100 <= 3
    breakout = close > high20

    stop = round(max(low10, close * 0.94), 2)
    risk = close - stop
    target1 = round(close * 1.05, 2)
    target2 = round(close * 1.10, 2)
    rr = ((target2 - close) / risk) if risk > 0 else np.nan

    snap = intraday_snapshot(ticker)
    pattern = classify_pattern(snap, breakout, near_breakout, above20, above50)

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
    if near_breakout:
        score += 10
    if breakout:
        score += 12
    if snap["OR Zone"] in ["Near breakout", "Breakout"]:
        score += 18
    if snap["OR Zone"] == "Upper range":
        score += 10
    if snap["OR Zone"] in ["Near breakdown", "Breakdown"]:
        score -= 20
    if snap["Intraday Trend"] == "Bullish ORB":
        score += 20
    if snap["Intraday Trend"] == "Bearish ORB":
        score -= 25
    if snap["Above VWAP"]:
        score += 8
    if dist20 > 15:
        score -= 12
    if one_day > 8:
        score -= 10

    score += regime_points
    score = max(0, min(100, round(score, 1)))

    if score >= 75 and snap["OR Status"] == "Above OR High":
        signal = "BUY NOW"
    elif score >= 60 and snap["OR Zone"] == "Near breakout":
        signal = "BUY ON OR BREAKOUT"
    elif score >= 55:
        signal = "WATCH"
    else:
        signal = "WAIT"
    if snap["OR Status"] == "Below OR Low":
        signal = "AVOID"

    return {
        "Signal": signal, "Ticker": ticker, "Pattern": pattern, "Price": round(close, 2),
        "Today Trade Score": score, "Intraday Trend": snap["Intraday Trend"],
        "OR Status": snap["OR Status"], "OR Zone": snap["OR Zone"], "OR Position": snap["OR Position"],
        "Above VWAP": snap["Above VWAP"], "VWAP Approx": snap["VWAP Approx"],
        "OR High": snap["OR High"], "OR Low": snap["OR Low"],
        "1D %": round(one_day, 2), "5D %": round(five_day, 2), "1M %": round(one_month, 2),
        "Rel Vol": round(rel_vol, 2), "20 MA": round(ma20, 2), "50 MA": round(ma50, 2),
        "Dist 20MA %": round(dist20, 2), "Reward/Risk": round(rr, 2) if not np.isnan(rr) else np.nan,
        "Stop": stop, "Target 1": target1, "Target 2": target2,
    }


def finalize_decision_board(df, regime, cash_available, risk_per_trade):
    if df.empty:
        return df
    df = df.copy()
    df["Probability %"] = df.apply(lambda row: probability_engine(row, regime), axis=1)
    df["Setup Grade"] = df["Probability %"].apply(setup_grade)
    df["Expected Value / Share"] = df.apply(expected_value_per_share, axis=1)
    df["Kelly %"] = df.apply(kelly_fraction, axis=1)
    allocations = df.apply(lambda row: capital_allocation(row, cash_available, risk_per_trade), axis=1)
    df["Suggested Shares"] = [x[0] for x in allocations]
    df["Suggested Position $"] = [x[1] for x in allocations]
    df["Allocation Note"] = [x[2] for x in allocations]
    return df.sort_values(["Expected Value / Share", "Probability %", "Today Trade Score"], ascending=False)


def validate_trade(entry, stop, target, shares, regime, above_vwap, above_or_high, probability, already_traded_today, revenge_trade_risk):
    pass_reasons = []
    fail_reasons = []

    if entry <= 0 or stop <= 0 or target <= 0:
        fail_reasons.append("Entry, stop, and target must be above zero.")
    elif stop >= entry:
        fail_reasons.append("Stop must be below entry for a long trade.")
    elif target <= entry:
        fail_reasons.append("Target must be above entry for a long trade.")
    else:
        rr = (target - entry) / (entry - stop)
        if rr >= 2:
            pass_reasons.append(f"Reward/risk is strong at {rr:.2f}.")
        elif rr >= 1.5:
            pass_reasons.append(f"Reward/risk is acceptable at {rr:.2f}.")
        else:
            fail_reasons.append(f"Reward/risk is weak at {rr:.2f}. Minimum preferred is 1.5.")

    if regime == "Defensive":
        fail_reasons.append("Market is RED/Defensive. Only A+ setups should be considered.")
    else:
        pass_reasons.append("Market is not RED.")

    if above_vwap:
        pass_reasons.append("Price is above VWAP.")
    else:
        fail_reasons.append("Price is not above VWAP.")

    if above_or_high:
        pass_reasons.append("Price is above opening range high.")
    else:
        fail_reasons.append("No opening range breakout confirmation.")

    if probability >= 70:
        pass_reasons.append(f"Probability is strong at {probability}%.")
    elif probability >= 60:
        pass_reasons.append(f"Probability is acceptable at {probability}%.")
    else:
        fail_reasons.append(f"Probability is too low at {probability}%.")

    if already_traded_today:
        fail_reasons.append("You already traded today. Avoid overtrading.")
    else:
        pass_reasons.append("No prior trade recorded today.")

    if revenge_trade_risk:
        fail_reasons.append("Revenge trade risk is present.")
    else:
        pass_reasons.append("No revenge-trade flag.")

    if shares <= 0:
        fail_reasons.append("Shares must be greater than zero.")

    return ("PASS" if not fail_reasons else "FAIL"), pass_reasons, fail_reasons


def trade_validator_section(regime):
    st.header("Pre-Trade Validator")
    st.caption("Use this before entering a manual trade. It is designed to stop impulsive trades.")

    c1, c2, c3, c4 = st.columns(4)
    ticker = c1.text_input("Ticker", value="")
    entry = c2.number_input("Planned Entry", min_value=0.0, step=0.01)
    stop = c3.number_input("Planned Stop", min_value=0.0, step=0.01)
    target = c4.number_input("Planned Target", min_value=0.0, step=0.01)

    c5, c6, c7, c8 = st.columns(4)
    shares = c5.number_input("Planned Shares", min_value=0.0, step=0.0001, format="%.6f")
    probability = c6.slider("Estimated Probability %", min_value=0, max_value=100, value=50, step=1)
    above_vwap = c7.checkbox("Above VWAP?")
    above_or_high = c8.checkbox("Above OR High?")

    c9, c10 = st.columns(2)
    already_traded_today = c9.checkbox("Already traded today?")
    revenge_trade_risk = c10.checkbox("Revenge trade risk?")

    if st.button("Validate Trade"):
        verdict, pass_reasons, fail_reasons = validate_trade(
            entry, stop, target, shares, regime, above_vwap, above_or_high,
            probability, already_traded_today, revenge_trade_risk
        )

        if verdict == "PASS":
            st.success("PASS: This trade meets the minimum rules.")
        else:
            st.error("FAIL: Do not take this trade yet.")

        if entry > 0 and stop > 0 and target > 0 and entry > stop and target > entry:
            risk = entry - stop
            reward = target - entry
            rr = reward / risk
            planned_risk = risk * shares
            planned_reward = reward * shares
            ev = (probability / 100 * planned_reward) - ((1 - probability / 100) * planned_risk)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Risk/Share", f"${risk:.2f}")
            k2.metric("Reward/Share", f"${reward:.2f}")
            k3.metric("R/R", f"{rr:.2f}")
            k4.metric("Expected Value", f"${ev:.2f}")

        st.subheader("Pass Reasons")
        for reason in pass_reasons:
            st.write(f"Yes - {reason}")
        if not pass_reasons:
            st.write("None")

        st.subheader("Fail Reasons")
        for reason in fail_reasons:
            st.write(f"No - {reason}")
        if not fail_reasons:
            st.write("None")


def daily_trading_coach(regime, market_light, df):
    st.header("Daily Trading Coach")
    if market_light == "RED":
        st.error("Today's mode: CAPITAL PRESERVATION")
        st.write("Primary goal: protect cash. Do not force trades.")
        st.write("Allowed trades: only A+ setups with positive expected value and confirmed breakout.")
        st.write("Avoid: chasing, averaging down, buying below VWAP, and revenge trades.")
    elif market_light == "YELLOW":
        st.warning("Today's mode: SELECTIVE")
        st.write("Primary goal: take only clean setups.")
        st.write("Allowed trades: A or B setups with positive expected value.")
        st.write("Avoid: low-volume moves and middle-of-range entries.")
    elif market_light == "GREEN":
        st.success("Today's mode: AGGRESSIVE BUT CONTROLLED")
        st.write("Primary goal: take the best confirmed setups, not every setup.")
        st.write("Allowed trades: A+, A, and strong B setups with defined stops.")
        st.write("Avoid: oversized positions and late breakouts.")
    else:
        st.info("Today's mode: UNKNOWN")
        st.write("Market data is incomplete. Trade smaller or wait.")

    if df is not None and not df.empty:
        best = df.iloc[0]
        st.subheader("Best Current Candidate")
        st.write(f"Ticker: **{best['Ticker']}**")
        st.write(f"Signal: **{best['Signal']}**")
        st.write(f"Pattern: **{best['Pattern']}**")
        st.write(f"Probability: **{best['Probability %']}%**")
        st.write(f"Expected Value / Share: **${best['Expected Value / Share']:.2f}**")
        if best["Suggested Position $"] > 0:
            st.success(f"Suggested position: ${best['Suggested Position $']:,.2f}")
        else:
            st.warning("Suggested position: $0. Wait for confirmation.")


def premarket_scanner_section(scan_df, market_light):
    st.header("Pre-Market / Live Opportunity Scanner v16")
    st.caption("This scans a wider universe than the sidebar watchlist and ranks the strongest current setups.")

    if scan_df.empty:
        st.warning("No scanner data loaded.")
        return

    top = scan_df.head(10)
    st.subheader("Top Opportunities")
    st.dataframe(
        top[[
            "Ticker", "Signal", "Pattern", "Price", "Probability %", "Setup Grade",
            "Expected Value / Share", "Today Trade Score", "Intraday Trend",
            "OR Zone", "Above VWAP", "1D %", "5D %", "Rel Vol"
        ]],
        use_container_width=True,
        height=360,
    )

    avoid = scan_df[scan_df["Signal"] == "AVOID"].head(10)
    st.subheader("Avoid / Weak Names")
    if avoid.empty:
        st.info("No avoid names from this scan.")
    else:
        st.dataframe(
            avoid[["Ticker", "Signal", "Pattern", "Price", "Intraday Trend", "OR Zone", "1D %", "Expected Value / Share"]],
            use_container_width=True,
        )

    if market_light == "RED":
        st.error("Scanner verdict: RED market. Treat all ideas as watchlist only unless an A+ confirmed breakout appears.")
    elif len(top) and top.iloc[0]["Suggested Position $"] > 0:
        st.success(f"Scanner verdict: Best deployable idea is {top.iloc[0]['Ticker']}.")
    else:
        st.warning("Scanner verdict: No clean deployable setup yet. Keep watching the top 3 only.")


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

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=ticker))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], mode="lines", name="20 MA"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], mode="lines", name="50 MA"))

    if timeframe == "5m intraday" and len(df) >= 3:
        fig.add_hline(y=df.head(3)["High"].max(), line_dash="dash", annotation_text="OR High")
        fig.add_hline(y=df.head(3)["Low"].min(), line_dash="dash", annotation_text="OR Low")

    fig.update_layout(title=title, height=550, xaxis_rangeslider_visible=False)
    return fig


st.title("Deon's Trader Dashboard v16")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.sidebar.header("Settings")
watchlist_text = st.sidebar.text_area("Manual Watchlist", ",".join(DEFAULT_WATCHLIST))
symbols = [x.strip().upper() for x in watchlist_text.split(",") if x.strip()]

scan_text = st.sidebar.text_area("Scanner Universe", ",".join(SCAN_UNIVERSE), height=180)
scan_symbols = [x.strip().upper() for x in scan_text.split(",") if x.strip()]

cash_available = st.sidebar.number_input("Cash available", min_value=0.0, value=float(DAY_TRADE_CAPITAL_DEFAULT), step=25.0)
risk_per_trade = st.sidebar.number_input("Risk per trade %", min_value=0.5, max_value=10.0, value=float(RISK_PER_TRADE_DEFAULT * 100), step=0.5) / 100
st.sidebar.write("Max risk per trade:", f"${cash_available * risk_per_trade:,.2f}")

if st.sidebar.button("Refresh now"):
    st.cache_data.clear()
    st.rerun()

st.header("Market Context")
market_df = market_context()
st.dataframe(market_df, use_container_width=True)

regime, regime_text, regime_points, market_light = get_market_regime(market_df)

if market_light == "GREEN":
    st.success(f"Green Market Status - {regime} - {regime_text}")
elif market_light == "YELLOW":
    st.warning(f"Yellow Market Status - {regime} - {regime_text}")
elif market_light == "RED":
    st.error(f"Red Market Status - {regime} - {regime_text}")
else:
    st.info(f"Unknown Market Status - {regime_text}")

st.header("Manual Watchlist Decision Board v16")
rows = []
for symbol in symbols:
    result = analyze_ticker(symbol, regime, regime_points)
    if result:
        rows.append(result)

df = pd.DataFrame(rows)
if df.empty:
    st.error("No manual watchlist data loaded. Try Refresh, check internet, or reduce the watchlist.")
    st.stop()

df = finalize_decision_board(df, regime, cash_available, risk_per_trade)
daily_trading_coach(regime, market_light, df)

display_cols = [
    "Signal", "Ticker", "Pattern", "Price", "Probability %", "Setup Grade",
    "Expected Value / Share", "Kelly %", "Today Trade Score", "Suggested Position $",
    "Suggested Shares", "Allocation Note", "Intraday Trend", "OR Status", "OR Zone",
    "OR Position", "Above VWAP", "VWAP Approx", "1D %", "5D %", "1M %",
    "Rel Vol", "Dist 20MA %", "Reward/Risk", "Stop", "Target 1", "Target 2",
]
st.dataframe(df[display_cols], use_container_width=True, height=500)

scan_tab, coach_tab, journal_tab, upload_tab, simulator_tab, chart_tab = st.tabs(
    ["Opportunity Scanner", "Pre-Trade Validator", "Trade Journal", "Robinhood CSV Upload", "Trade Simulator", "Charts"]
)

with scan_tab:
    with st.spinner("Scanning expanded universe..."):
        scan_rows = []
        seen = set()
        for symbol in scan_symbols:
            if symbol in seen:
                continue
            seen.add(symbol)
            result = analyze_ticker(symbol, regime, regime_points)
            if result:
                scan_rows.append(result)
        scan_df = pd.DataFrame(scan_rows)
        if not scan_df.empty:
            scan_df = finalize_decision_board(scan_df, regime, cash_available, risk_per_trade)
    premarket_scanner_section(scan_df if "scan_df" in locals() else pd.DataFrame(), market_light)

with coach_tab:
    trade_validator_section(regime)

with journal_tab:
    journal = load_journal()
    journal_report(journal)

    st.subheader("Add Trade Journal Entry")
    with st.form("journal_entry_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        trade_date = c1.date_input("Date", value=date.today())
        ticker_input = c2.text_input("Ticker", value="")
        pattern_input = c3.selectbox("Pattern", ["Bullish ORB", "OR Breakout Watch", "VWAP Continuation", "Daily Breakout", "Near Daily Breakout", "Weak / Breakdown", "No Clear Pattern", "Other"])
        grade_input = c4.selectbox("Setup Grade", ["A+ Setup", "A Setup", "B Setup", "C Setup", "No Trade"])

        c5, c6, c7, c8 = st.columns(4)
        signal_input = c5.selectbox("Signal", ["BUY NOW", "BUY ON OR BREAKOUT", "WATCH", "WAIT", "AVOID", "Manual"])
        entry_input = c6.number_input("Entry", min_value=0.0, step=0.01)
        exit_input = c7.number_input("Exit", min_value=0.0, step=0.01)
        stop_input = c8.number_input("Stop", min_value=0.0, step=0.01)

        c9, c10, c11, c12 = st.columns(4)
        target_input = c9.number_input("Target", min_value=0.0, step=0.01)
        shares_input = c10.number_input("Shares", min_value=0.0, step=0.0001, format="%.6f")
        mistake_input = c11.selectbox("Mistake", ["None", "Chased", "Ignored stop", "Sold too early", "Entered without trigger", "Oversized", "Revenge trade", "Other"])
        notes_input = c12.text_input("Notes", value="")

        c13, c14 = st.columns(2)
        pre_trade_screenshot = c13.text_input("Pre-trade screenshot link/path", value="")
        exit_screenshot = c14.text_input("Exit screenshot link/path", value="")

        submitted = st.form_submit_button("Add Journal Entry")
        if submitted:
            ticker_clean = ticker_input.strip().upper()
            if not ticker_clean:
                st.error("Ticker is required.")
            elif entry_input <= 0 or exit_input <= 0 or shares_input <= 0:
                st.error("Entry, exit, and shares must be greater than zero.")
            else:
                pnl = (exit_input - entry_input) * shares_input
                ret_pct = ((exit_input / entry_input) - 1) * 100
                result = "Win" if pnl > 0 else "Loss" if pnl < 0 else "Breakeven"
                new_row = {
                    "Date": trade_date.isoformat(), "Ticker": ticker_clean, "Pattern": pattern_input,
                    "Setup Grade": grade_input, "Signal": signal_input, "Market Regime": regime,
                    "Entry": round(entry_input, 2), "Exit": round(exit_input, 2),
                    "Stop": round(stop_input, 2), "Target": round(target_input, 2),
                    "Shares": round(shares_input, 6), "P/L": round(pnl, 2),
                    "Return %": round(ret_pct, 2), "Result": result, "Mistake": mistake_input,
                    "Pre-Trade Screenshot": pre_trade_screenshot, "Exit Screenshot": exit_screenshot,
                    "Notes": notes_input,
                }
                journal = pd.concat([journal, pd.DataFrame([new_row])], ignore_index=True)
                save_journal(journal)
                st.success("Journal entry saved. Click Refresh now to update the report card.")

    if not journal.empty:
        if st.button("Clear entire journal"):
            save_journal(empty_journal())
            st.warning("Journal cleared. Click Refresh now.")

with upload_tab:
    uploaded = st.file_uploader("Upload Robinhood CSV trade history", type=["csv"])
    if uploaded is not None:
        trade_history_audit(uploaded)

with simulator_tab:
    st.header("Trade Simulator")
    sim_cols = [
        "Ticker", "Signal", "Pattern", "Probability %", "Setup Grade", "Price", "Stop",
        "Target 1", "Target 2", "Reward/Risk", "Expected Value / Share", "Kelly %",
        "Suggested Shares", "Suggested Position $", "Allocation Note",
    ]
    st.dataframe(df[sim_cols], use_container_width=True)

    positive_ev = df[df["Expected Value / Share"] > 0]
    deployable = df[df["Suggested Position $"] > 0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Positive EV Setups", len(positive_ev))
    c2.metric("Deployable Setups", len(deployable))
    c3.metric("Suggested Total Deployment", f"${df['Suggested Position $'].sum():,.2f}")

    if deployable.empty:
        st.info("Simulator verdict: deploy $0. Wait for a cleaner setup.")
    else:
        st.success("Simulator verdict: one or more setups are deployable under current rules.")

with chart_tab:
    st.header("Charts")
    selected = st.selectbox("Select chart", df["Ticker"].tolist())
    timeframe = st.radio("Chart timeframe", ["5m intraday", "15m intraday", "3mo daily"], horizontal=True)
    chart = make_chart(selected, timeframe)
    if chart:
        st.plotly_chart(chart, use_container_width=True)

st.caption("Data comes from yfinance/Yahoo Finance and may be delayed or incomplete. Use this dashboard as decision support, not blind execution.")
