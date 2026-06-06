
import json
import html
from datetime import datetime, date
from zoneinfo import ZoneInfo
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
import requests


# ============================================================
# V35.10 WARM TABLE RENDERER
# Automatically converts Streamlit dataframes from stark white
# grids into warm parchment panels with gold headers.
# ============================================================
_ORIGINAL_ST_DATAFRAME = st.dataframe


def _warm_table_styles(styler):
    """Apply a warm trading-desk table skin to pandas Styler objects."""
    return styler.set_table_styles([
        {
            "selector": "thead th",
            "props": [
                ("background", "linear-gradient(180deg, #ffe6ad 0%, #f5d58b 100%)"),
                ("color", "#061622"),
                ("font-weight", "800"),
                ("border-bottom", "1px solid rgba(184, 134, 11, .35)"),
                ("border-right", "1px solid rgba(184, 134, 11, .15)"),
            ],
        },
        {
            "selector": "tbody td",
            "props": [
                ("background-color", "#fff2d2"),
                ("color", "#061622"),
                ("border-color", "rgba(184, 134, 11, .14)"),
            ],
        },
        {
            "selector": "tbody tr:nth-child(even) td",
            "props": [
                ("background-color", "#f8e8bf"),
            ],
        },
        {
            "selector": "tbody tr:hover td",
            "props": [
                ("background-color", "#ffe0a3"),
            ],
        },
        {
            "selector": "table",
            "props": [
                ("background", "#fff2d2"),
                ("border-collapse", "collapse"),
            ],
        },
    ]).format(precision=2)


def _highlight_trading_cells(val):
    """Semantic color accents inside warm tables without making the grid cold/white."""
    s = str(val).upper()
    if "TRADE CANDIDATE" in s or s == "REAL OK" or s == "ATTACK" or s == "A":
        return "background-color: #dff7df; color: #064e3b; font-weight: 800;"
    if "WAIT" in s or "PROBE" in s or "PAPER" in s or s == "B" or s == "C":
        return "background-color: #ffe5b8; color: #8a3f00; font-weight: 800;"
    if "AVOID" in s or "BLOCK" in s or "NO TRADE" in s or s == "D" or s == "PROTECT":
        return "background-color: #f8d0c3; color: #8f1d1d; font-weight: 800;"
    if "WATCH" in s:
        return "background-color: #dcfce7; color: #065f46; font-weight: 800;"
    return ""


def warm_dataframe(data=None, *args, **kwargs):
    """Drop-in replacement for st.dataframe that avoids pure-white table surfaces."""
    try:
        if isinstance(data, pd.DataFrame):
            styled = _warm_table_styles(data.style.map(_highlight_trading_cells))
            return _ORIGINAL_ST_DATAFRAME(styled, *args, **kwargs)
        if isinstance(data, pd.io.formats.style.Styler):
            return _ORIGINAL_ST_DATAFRAME(_warm_table_styles(data), *args, **kwargs)
    except Exception:
        pass
    return _ORIGINAL_ST_DATAFRAME(data, *args, **kwargs)


st.dataframe = warm_dataframe

st.set_page_config(
    page_title="Deon's Trader Dashboard v35.10 Warm Tables",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ============================================================
   V35 VISUAL SYSTEM
   Palette based on user's preferred hero screenshot:
   midnight teal -> deep emerald -> electric blue
   ============================================================ */

:root {
    --v35-navy: #061622;
    --v35-teal-dark: #083344;
    --v35-teal: #0f766e;
    --v35-emerald: #10b981;
    --v35-blue: #2563eb;
    --v35-blue2: #1d4ed8;
    --v35-cyan: #38bdf8;
    --v35-slate: #334155;
    --v35-soft: #f8fafc;
    --v35-border: rgba(15, 118, 110, 0.22);
    --v35-shadow: 0 20px 48px rgba(6, 22, 34, .16);
}

html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top right, rgba(37, 99, 235, .12), transparent 34%),
        radial-gradient(circle at top left, rgba(16, 185, 129, .09), transparent 28%),
        linear-gradient(180deg, #f8fafc 0%, #eef6f7 100%);
}

.block-container {
    padding-top: 1.65rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #061622 0%, #083344 52%, #0f766e 100%);
    border-right: 1px solid rgba(255,255,255,.10);
}

section[data-testid="stSidebar"] * {
    color: rgba(255,255,255,.93) !important;
}

section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: rgba(255,255,255,.78) !important;
}

section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] select,
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: rgba(255,255,255,.94) !important;
    color: #061622 !important;
    border: 1px solid rgba(255,255,255,.25) !important;
    border-radius: 12px !important;
}

section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] input {
    color: #061622 !important;
}

section[data-testid="stSidebar"] button {
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,.25) !important;
    background: rgba(255,255,255,.10) !important;
    color: white !important;
}

/* Main title */
h1, h2, h3 {
    letter-spacing: -0.045em;
}

h1 {
    color: #061622;
    font-weight: 950 !important;
}

/* Hero */
.v35-hero {
    position: relative;
    overflow: hidden;
    padding: 30px 34px;
    border-radius: 26px;
    background:
        radial-gradient(circle at 14% 12%, rgba(56, 189, 248, .16), transparent 26%),
        radial-gradient(circle at 76% 18%, rgba(16, 185, 129, .14), transparent 30%),
        linear-gradient(120deg, #061622 0%, #083344 31%, #0f766e 62%, #2563eb 100%);
    color: white;
    box-shadow: 0 28px 60px rgba(6, 22, 34, .28);
    margin-bottom: 22px;
    border: 1px solid rgba(255,255,255,.14);
}

.v35-hero:after {
    content: "";
    position: absolute;
    width: 420px;
    height: 420px;
    right: -150px;
    top: -210px;
    background: radial-gradient(circle, rgba(255,255,255,.20), transparent 62%);
    transform: rotate(20deg);
}

.v35-hero h1 {
    position: relative;
    margin: 0;
    color: white !important;
    font-size: clamp(2rem, 3vw, 3rem);
    font-weight: 950;
    letter-spacing: -0.055em;
}

.v35-hero p {
    position: relative;
    margin: 10px 0 0 0;
    color: rgba(255,255,255,.86);
    font-size: 1.02rem;
    font-weight: 550;
}

.v35-hero-row {
    position: relative;
    margin-top: 18px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.v35-chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,.12);
    border: 1px solid rgba(255,255,255,.18);
    color: white;
    font-size: .82rem;
    font-weight: 850;
    backdrop-filter: blur(8px);
}

/* Metrics */
div[data-testid="stMetric"] {
    background:
        linear-gradient(180deg, rgba(255,255,255,.98), rgba(248,250,252,.96)),
        linear-gradient(135deg, rgba(15,118,110,.08), rgba(37,99,235,.07));
    border: 1px solid var(--v35-border);
    padding: 18px 18px;
    border-radius: 20px;
    box-shadow: 0 14px 32px rgba(6, 22, 34, .08);
}

div[data-testid="stMetric"]::before {
    content: "";
    display: block;
    height: 4px;
    margin: -18px -18px 14px -18px;
    border-radius: 20px 20px 0 0;
    background: linear-gradient(90deg, #083344, #0f766e, #2563eb);
}

div[data-testid="stMetricLabel"] {
    color: #64748b;
    font-weight: 900;
}

div[data-testid="stMetricValue"] {
    color: #061622;
    font-weight: 950;
}

/* Alerts */
div[data-testid="stAlert"] {
    border-radius: 18px;
    border-width: 1px;
    box-shadow: 0 10px 28px rgba(6, 22, 34, .06);
}

/* Tabs */
button[data-baseweb="tab"] {
    border-radius: 999px !important;
    margin-right: 6px !important;
    padding: 9px 14px !important;
    background: rgba(255,255,255,.72) !important;
    border: 1px solid rgba(15,118,110,.16) !important;
    color: #0f172a !important;
    font-weight: 850 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(90deg, #083344, #0f766e, #2563eb) !important;
    color: white !important;
    box-shadow: 0 10px 24px rgba(15,118,110,.24);
}

/* Tables */
div[data-testid="stDataFrame"],
div[data-testid="stTable"] {
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid rgba(15,118,110,.16);
    box-shadow: 0 12px 30px rgba(6, 22, 34, .06);
}

/* Inputs */
div[data-baseweb="select"] > div,
input,
textarea {
    border-radius: 14px !important;
    border-color: rgba(15,118,110,.22) !important;
}

/* Buttons */
.stButton button,
.stDownloadButton button,
button[kind="secondary"],
button[kind="primary"] {
    border-radius: 14px !important;
    font-weight: 900 !important;
    border: 1px solid rgba(15,118,110,.20) !important;
    box-shadow: 0 8px 18px rgba(6, 22, 34, .08);
}

.stButton button:hover,
.stDownloadButton button:hover {
    border-color: rgba(37,99,235,.42) !important;
    box-shadow: 0 12px 26px rgba(37,99,235,.14);
}

/* Cards and badges */
.v35-card {
    border: 1px solid rgba(15,118,110,.22);
    border-radius: 22px;
    padding: 18px 20px;
    background:
        linear-gradient(180deg, rgba(255,255,255,.98), rgba(248,250,252,.96));
    box-shadow: 0 16px 38px rgba(6, 22, 34, .07);
    margin-bottom: 16px;
}

.v35-card-dark {
    border: 1px solid rgba(255,255,255,.14);
    border-radius: 22px;
    padding: 18px 20px;
    background: linear-gradient(135deg, #061622 0%, #083344 48%, #0f766e 100%);
    color: white;
    box-shadow: var(--v35-shadow);
    margin-bottom: 16px;
}

.v35-section-title {
    font-size: 1.35rem;
    font-weight: 950;
    margin-top: 22px;
    margin-bottom: 12px;
    letter-spacing: -0.045em;
    color: #061622;
}

.v35-pill {
    display: inline-block;
    padding: 7px 12px;
    border-radius: 999px;
    font-weight: 900;
    font-size: .78rem;
    letter-spacing: .02em;
    margin-right: 8px;
    border: 1px solid transparent;
}

.pill-green { background: #dcfce7; color: #166534; border-color: rgba(22,101,52,.10); }
.pill-yellow { background: #fef3c7; color: #92400e; border-color: rgba(146,64,14,.12); }
.pill-red { background: #fee2e2; color: #991b1b; border-color: rgba(153,27,27,.12); }
.pill-blue { background: #dbeafe; color: #1e40af; border-color: rgba(30,64,175,.12); }
.pill-purple { background: #ede9fe; color: #5b21b6; border-color: rgba(91,33,182,.12); }
.pill-dark { background: #061622; color: white; border-color: rgba(255,255,255,.12); }

.small-muted {
    color: #64748b;
    font-size: .88rem;
    font-weight: 650;
}

hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(15,118,110,.30), transparent);
    margin: 1.2rem 0;
}


/* ============================================================
   V35.3 UI POLISH — extend header/sidebar color language
   across the full app
   ============================================================ */
[data-testid="stHeader"] {
    background: rgba(248, 250, 252, .74) !important;
    backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(15,118,110,.10);
}

.v35-kicker {
    position: relative;
    display: inline-flex;
    padding: 7px 11px;
    border-radius: 999px;
    margin-bottom: 12px;
    color: rgba(255,255,255,.86);
    border: 1px solid rgba(255,255,255,.18);
    background: rgba(255,255,255,.10);
    font-weight: 950;
    font-size: .76rem;
    letter-spacing: .08em;
}

.v35-hero-boost {
    margin-top: 4px;
    box-shadow: 0 32px 82px rgba(6,22,34,.34), inset 0 1px 0 rgba(255,255,255,.16);
}

.v35-trade-desk-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin: 18px 0 22px;
}

.v35-status-card {
    position: relative;
    overflow: hidden;
    min-height: 126px;
    border-radius: 22px;
    padding: 17px 18px;
    background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(241,248,249,.96));
    border: 1px solid rgba(15,118,110,.20);
    box-shadow: 0 16px 40px rgba(6,22,34,.08);
}

.v35-status-card:before {
    content:"";
    position:absolute;
    left:0;
    top:0;
    width:100%;
    height:5px;
    background: linear-gradient(90deg, #061622, #0f766e, #2563eb);
}

.v35-status-card:after {
    content:"";
    position:absolute;
    width:120px;
    height:120px;
    right:-48px;
    bottom:-54px;
    border-radius:50%;
    background: radial-gradient(circle, rgba(56,189,248,.18), transparent 66%);
}

.v35-card-label {
    color: #64748b;
    font-weight: 950;
    text-transform: uppercase;
    letter-spacing: .07em;
    font-size: .72rem;
    margin-bottom: 8px;
}

.v35-card-value {
    color: #061622;
    font-weight: 950;
    letter-spacing: -.05em;
    font-size: 1.85rem;
    line-height: 1.05;
}

.v35-card-sub {
    margin-top: 8px;
    color: #334155;
    font-size: .85rem;
    font-weight: 750;
}

.v35-mode-ATTACK { border-color: rgba(16,185,129,.42); background: linear-gradient(160deg, #ecfdf5 0%, #ffffff 60%, #dbeafe 100%); }
.v35-mode-PROBE { border-color: rgba(245,158,11,.42); background: linear-gradient(160deg, #fffbeb 0%, #ffffff 62%, #e0f2fe 100%); }
.v35-mode-TRAIN { border-color: rgba(37,99,235,.34); background: linear-gradient(160deg, #eff6ff 0%, #ffffff 62%, #ccfbf1 100%); }
.v35-mode-PROTECT { border-color: rgba(239,68,68,.38); background: linear-gradient(160deg, #fef2f2 0%, #ffffff 62%, #e2e8f0 100%); }

.v35-banner {
    border-radius: 24px;
    padding: 18px 20px;
    margin: 16px 0 18px;
    background: linear-gradient(135deg, rgba(6,22,34,.98), rgba(8,51,68,.96) 40%, rgba(15,118,110,.95) 72%, rgba(37,99,235,.94));
    color: white;
    border: 1px solid rgba(255,255,255,.14);
    box-shadow: 0 22px 54px rgba(6,22,34,.18);
}

.v35-banner-title {
    font-size: 1.05rem;
    font-weight: 950;
    letter-spacing: -.035em;
    margin-bottom: 6px;
}

.v35-banner-text {
    opacity: .86;
    font-weight: 650;
    line-height: 1.45;
}

/* Make regular Streamlit sections feel like panels */
section.main div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdownContainer"] h2),
section.main div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdownContainer"] h3) {
    scroll-margin-top: 80px;
}

h2 {
    position: relative;
    padding: 13px 16px 13px 18px;
    margin-top: 1.45rem !important;
    border-radius: 18px;
    color: #061622 !important;
    background: linear-gradient(90deg, rgba(6,22,34,.08), rgba(15,118,110,.08), rgba(37,99,235,.06));
    border: 1px solid rgba(15,118,110,.16);
    box-shadow: 0 10px 24px rgba(6,22,34,.045);
}

h2:before {
    content:"";
    position:absolute;
    left:0;
    top:0;
    bottom:0;
    width:6px;
    border-radius: 18px 0 0 18px;
    background: linear-gradient(180deg, #061622, #0f766e, #2563eb);
}

h3 {
    color: #083344 !important;
    font-weight: 950 !important;
}

/* Sidebar polish */
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    background:
        radial-gradient(circle at top right, rgba(56,189,248,.18), transparent 25%),
        linear-gradient(180deg, #061622 0%, #083344 48%, #0f766e 100%);
}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: white !important;
    background: rgba(255,255,255,.08) !important;
    border: 1px solid rgba(255,255,255,.12) !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] h2:before,
section[data-testid="stSidebar"] h3:before { display:none; }
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,.12) !important;
    border-radius: 16px !important;
    background: rgba(255,255,255,.06) !important;
}

/* Metrics with stronger trade-desk identity */
div[data-testid="stMetric"] {
    position: relative;
    overflow: hidden;
}
div[data-testid="stMetric"]:after {
    content:"";
    position:absolute;
    right:-46px;
    bottom:-52px;
    width:120px;
    height:120px;
    border-radius:50%;
    background: radial-gradient(circle, rgba(37,99,235,.11), transparent 68%);
}
div[data-testid="stMetricDelta"] {
    font-weight: 900 !important;
}

/* Text areas become packet consoles */
textarea {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace !important;
    background: linear-gradient(180deg, #ffffff, #f8fafc) !important;
    border: 1px solid rgba(15,118,110,.25) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.8) !important;
}

/* Dataframe container refinement */
div[data-testid="stDataFrame"] {
    background: white;
}
div[data-testid="stDataFrame"] [role="grid"] {
    border-radius: 18px;
}

/* Alert badges */
div[data-testid="stAlert"] {
    border-left: 6px solid rgba(15,118,110,.65) !important;
}

@media (max-width: 1100px) {
    .v35-trade-desk-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 720px) {
    .v35-trade-desk-grid { grid-template-columns: 1fr; }
    .v35-card-value { font-size: 1.45rem; }
}


/* ============================================================
   V35.3 DEEP UI PASS — command center depth, contrast, and hierarchy
   ============================================================ */
:root {
    --v35-panel: rgba(255,255,255,.86);
    --v35-panel-strong: rgba(255,255,255,.96);
    --v35-ink: #061622;
    --v35-muted: #64748b;
    --v35-line: rgba(15,118,110,.18);
}
.block-container:before {
    content:"";
    position: fixed;
    inset: 0;
    pointer-events:none;
    background-image:
        linear-gradient(rgba(15,118,110,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(37,99,235,.03) 1px, transparent 1px);
    background-size: 42px 42px;
    mask-image: linear-gradient(180deg, rgba(0,0,0,.45), transparent 70%);
}
.v35-hero { min-height: 210px; }
.v35-hero:before {
    content:""; position:absolute; inset:0;
    background: linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px), linear-gradient(180deg, rgba(255,255,255,.04) 1px, transparent 1px);
    background-size: 34px 34px; opacity:.35;
}
.v35-hero h1, .v35-hero p, .v35-hero-row, .v35-kicker { z-index: 1; }
.v35-command-strip { display:grid; grid-template-columns: 1.15fr 1fr 1fr; gap:14px; margin: 8px 0 20px; }
.v35-command-panel { position:relative; overflow:hidden; border-radius: 24px; padding: 18px 20px; background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(241,248,249,.93)); border: 1px solid rgba(15,118,110,.20); box-shadow: 0 18px 44px rgba(6,22,34,.08); }
.v35-command-panel.dark { background: radial-gradient(circle at 92% 10%, rgba(56,189,248,.22), transparent 28%), linear-gradient(135deg, #061622 0%, #083344 54%, #0f766e 100%); color:white; border-color: rgba(255,255,255,.14); }
.v35-command-panel.dark .v35-command-label, .v35-command-panel.dark .v35-command-note { color: rgba(255,255,255,.74); }
.v35-command-label { color:#64748b; font-weight:950; text-transform:uppercase; letter-spacing:.08em; font-size:.72rem; margin-bottom:8px; }
.v35-command-main { font-weight:950; letter-spacing:-.045em; font-size:1.55rem; line-height:1.05; }
.v35-command-note { margin-top:9px; color:#475569; font-weight:700; font-size:.88rem; }
.v35-lane-grid { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:14px; margin: 12px 0 22px; }
.v35-lane-card { border-radius:22px; padding:18px 19px; background: rgba(255,255,255,.94); border:1px solid rgba(15,118,110,.18); box-shadow: 0 16px 40px rgba(6,22,34,.07); position:relative; overflow:hidden; }
.v35-lane-card:before { content:""; position:absolute; left:0; top:0; bottom:0; width:7px; background: linear-gradient(180deg, #061622, #0f766e, #2563eb); }
.v35-lane-title { font-size:.78rem; font-weight:950; letter-spacing:.08em; text-transform:uppercase; color:#0f766e; margin-left:4px; }
.v35-lane-value { margin-top:8px; margin-left:4px; font-size:1.32rem; font-weight:950; color:#061622; letter-spacing:-.04em; }
.v35-lane-detail { margin-top:8px; margin-left:4px; color:#475569; font-weight:700; font-size:.88rem; line-height:1.42; }
.v35-tile-grid { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:14px; margin: 8px 0 24px; }
.v35-opportunity-tile { position:relative; overflow:hidden; border-radius:24px; padding:18px 18px 17px; background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(248,250,252,.95)); border:1px solid rgba(15,118,110,.18); box-shadow: 0 18px 44px rgba(6,22,34,.075); }
.v35-opportunity-tile:after { content:""; position:absolute; right:-70px; top:-70px; width:160px; height:160px; background: radial-gradient(circle, rgba(37,99,235,.16), transparent 68%); border-radius:50%; }
.v35-tile-rank { display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px; border-radius:12px; background: linear-gradient(135deg, #061622, #0f766e); color:white; font-weight:950; margin-bottom:10px; }
.v35-tile-ticker { font-size:1.9rem; font-weight:950; color:#061622; letter-spacing:-.06em; line-height:1; }
.v35-tile-meta { color:#64748b; font-weight:800; margin-top:5px; font-size:.86rem; }
.v35-tile-row { display:flex; gap:8px; flex-wrap:wrap; margin-top:13px; }
.v35-mini-pill { display:inline-flex; padding:6px 9px; border-radius:999px; font-size:.74rem; font-weight:950; border:1px solid rgba(15,118,110,.16); background:#f8fafc; color:#083344; }
.v35-mini-pill.ok { background:#dcfce7; color:#166534; }
.v35-mini-pill.warn { background:#fef3c7; color:#92400e; }
.v35-mini-pill.paper { background:#dbeafe; color:#1e40af; }
.v35-mini-pill.block { background:#fee2e2; color:#991b1b; }
.v35-tile-trigger { margin-top:12px; padding:12px 13px; border-radius:16px; background: linear-gradient(180deg, #f8fafc, #eef6f7); color:#334155; font-weight:750; font-size:.85rem; line-height:1.42; border:1px solid rgba(15,118,110,.13); }
.v35-divider-title { display:flex; align-items:center; gap:10px; margin: 24px 0 10px; color:#061622; font-weight:950; letter-spacing:-.04em; font-size:1.25rem; }
.v35-divider-title:before { content:""; display:block; width:36px; height:10px; border-radius:999px; background: linear-gradient(90deg, #061622, #0f766e, #2563eb); }
.v35-divider-title:after { content:""; flex:1; height:1px; background: linear-gradient(90deg, rgba(15,118,110,.32), transparent); }
.stButton button, .stDownloadButton button { background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(241,248,249,.95)) !important; color:#061622 !important; }
.stButton button:hover, .stDownloadButton button:hover { background: linear-gradient(90deg, #083344, #0f766e, #2563eb) !important; color:white !important; transform: translateY(-1px); }
[data-testid="stExpander"] { border-radius: 18px !important; border: 1px solid rgba(15,118,110,.16) !important; box-shadow: 0 10px 28px rgba(6,22,34,.045); overflow:hidden; }
[data-testid="stExpander"] summary { font-weight:950 !important; color:#083344 !important; }
@media (max-width: 1100px) { .v35-command-strip, .v35-lane-grid, .v35-tile-grid { grid-template-columns: 1fr; } }



/* ============================================================
   V35.4 WARM OPPORTUNITY PALETTE
   Navy/teal/emerald foundation + gold/copper premium accents.
   Gold = best opportunity / target progress. Copper = pending action.
   ============================================================ */
:root {
    --v35-gold: #D4AF37;
    --v35-gold-deep: #B8860B;
    --v35-gold-soft: #FFF7D6;
    --v35-copper: #C97A40;
    --v35-copper-deep: #9A4F22;
    --v35-copper-soft: #FFF1E6;
    --v35-champagne: #D8C3A5;
    --v35-warm-cream: #fffaf0;
    --v35-bronze: #CD7F32;
    --v35-silver: #B8C2CC;
}

.stApp {
    background:
        radial-gradient(circle at 88% 4%, rgba(212,175,55,.13), transparent 29%),
        radial-gradient(circle at 4% 10%, rgba(201,122,64,.10), transparent 24%),
        radial-gradient(circle at top right, rgba(37, 99, 235, .10), transparent 34%),
        radial-gradient(circle at top left, rgba(16, 185, 129, .075), transparent 28%),
        linear-gradient(180deg, #fffaf0 0%, #f8fafc 36%, #eef6f7 100%) !important;
}

section[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at 12% 2%, rgba(212,175,55,.22), transparent 25%),
        linear-gradient(180deg, #061622 0%, #083344 45%, #0f766e 100%) !important;
    box-shadow: inset -1px 0 0 rgba(212,175,55,.16);
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {
    color: #FFF7D6 !important;
}
section[data-testid="stSidebar"] button {
    background: linear-gradient(135deg, rgba(212,175,55,.20), rgba(255,255,255,.08)) !important;
    border-color: rgba(212,175,55,.32) !important;
}
section[data-testid="stSidebar"] button:hover {
    background: linear-gradient(135deg, rgba(212,175,55,.34), rgba(201,122,64,.24)) !important;
}

.v35-hero {
    background:
        radial-gradient(circle at 78% 18%, rgba(212,175,55,.26), transparent 30%),
        radial-gradient(circle at 16% 12%, rgba(56,189,248,.16), transparent 28%),
        linear-gradient(120deg, #061622 0%, #083344 32%, #0f766e 66%, #B8860B 118%) !important;
    border: 1px solid rgba(212,175,55,.28) !important;
    box-shadow: 0 34px 70px rgba(6,22,34,.28), 0 0 0 1px rgba(212,175,55,.10) inset !important;
}
.v35-hero:after {
    background: radial-gradient(circle, rgba(212,175,55,.25), transparent 62%) !important;
}
.v35-kicker {
    color: #FFF7D6 !important;
    text-shadow: 0 0 24px rgba(212,175,55,.22);
}
.v35-chip {
    background: rgba(255,247,214,.13) !important;
    border-color: rgba(212,175,55,.28) !important;
}
.v35-chip:first-child {
    background: linear-gradient(135deg, rgba(212,175,55,.28), rgba(255,255,255,.10)) !important;
    border-color: rgba(212,175,55,.45) !important;
}

/* Warm premium metric cards */
div[data-testid="stMetric"] {
    background:
        radial-gradient(circle at 92% 8%, rgba(212,175,55,.12), transparent 34%),
        linear-gradient(180deg, rgba(255,255,255,.98), rgba(255,250,240,.96)) !important;
    border-color: rgba(201,122,64,.20) !important;
}
div[data-testid="stMetric"]::before {
    background: linear-gradient(90deg, #061622, #0f766e, #D4AF37) !important;
}

/* Command panels */
.v35-command-panel {
    background:
        radial-gradient(circle at 92% 10%, rgba(212,175,55,.12), transparent 30%),
        linear-gradient(180deg, rgba(255,255,255,.97), rgba(255,250,240,.94)) !important;
    border-color: rgba(201,122,64,.18) !important;
}
.v35-command-panel.dark {
    background:
        radial-gradient(circle at 90% 10%, rgba(212,175,55,.30), transparent 30%),
        linear-gradient(135deg, #061622 0%, #083344 48%, #0f766e 82%, #B8860B 130%) !important;
    border-color: rgba(212,175,55,.30) !important;
}
.v35-command-panel.gold {
    background:
        radial-gradient(circle at 86% 8%, rgba(255,247,214,.52), transparent 32%),
        linear-gradient(135deg, #FFF7D6 0%, #ffffff 58%, #f8fafc 100%) !important;
    border-color: rgba(212,175,55,.45) !important;
    box-shadow: 0 22px 50px rgba(184,134,11,.13) !important;
}
.v35-command-panel.copper {
    background:
        radial-gradient(circle at 86% 8%, rgba(255,241,230,.58), transparent 32%),
        linear-gradient(135deg, #FFF1E6 0%, #ffffff 60%, #f8fafc 100%) !important;
    border-color: rgba(201,122,64,.36) !important;
}
.v35-command-panel.gold .v35-command-label,
.v35-command-panel.gold .v35-command-main { color:#7A5200 !important; }
.v35-command-panel.copper .v35-command-label,
.v35-command-panel.copper .v35-command-main { color:#8A421C !important; }

/* Daily mode cards get semantic warmth */
.v35-mode-ATTACK {
    border-color: rgba(16,185,129,.46) !important;
    background: radial-gradient(circle at 88% 10%, rgba(212,175,55,.13), transparent 31%), linear-gradient(160deg, #ecfdf5 0%, #ffffff 60%, #fff7d6 100%) !important;
}
.v35-mode-PROBE {
    border-color: rgba(201,122,64,.46) !important;
    background: radial-gradient(circle at 88% 10%, rgba(201,122,64,.18), transparent 31%), linear-gradient(160deg, #fff1e6 0%, #ffffff 62%, #e0f2fe 100%) !important;
}
.v35-mode-TRAIN {
    border-color: rgba(37,99,235,.34) !important;
    background: linear-gradient(160deg, #eff6ff 0%, #ffffff 62%, #fef3c7 100%) !important;
}
.v35-mode-PROTECT {
    border-color: rgba(239,68,68,.40) !important;
    background: linear-gradient(160deg, #fef2f2 0%, #ffffff 62%, #e2e8f0 100%) !important;
}

/* Warm status cards and banners */
.v35-status-card {
    background:
        radial-gradient(circle at 92% 8%, rgba(212,175,55,.10), transparent 34%),
        linear-gradient(180deg, rgba(255,255,255,.97), rgba(255,250,240,.94)) !important;
    border-color: rgba(201,122,64,.18) !important;
}
.v35-status-card:before {
    background: linear-gradient(90deg, #061622, #0f766e, #D4AF37) !important;
}
.v35-banner {
    background:
        radial-gradient(circle at 90% 12%, rgba(212,175,55,.24), transparent 30%),
        linear-gradient(135deg, #061622 0%, #083344 42%, #0f766e 76%, #B8860B 125%) !important;
    border-color: rgba(212,175,55,.26) !important;
}
.v35-banner-title { color:#FFF7D6 !important; }

/* 3-lane workflow: gold, copper, emerald */
.v35-lane-card:nth-child(1):before { background: linear-gradient(180deg, #B8860B, #D4AF37) !important; }
.v35-lane-card:nth-child(2):before { background: linear-gradient(180deg, #9A4F22, #C97A40) !important; }
.v35-lane-card:nth-child(3):before { background: linear-gradient(180deg, #047857, #10B981) !important; }
.v35-lane-card:nth-child(1) .v35-lane-title { color:#8A6500 !important; }
.v35-lane-card:nth-child(2) .v35-lane-title { color:#9A4F22 !important; }
.v35-lane-card:nth-child(3) .v35-lane-title { color:#047857 !important; }

/* Opportunity podium cards */
.v35-opportunity-tile {
    background:
        radial-gradient(circle at 88% 6%, rgba(212,175,55,.11), transparent 33%),
        linear-gradient(180deg, rgba(255,255,255,.99), rgba(255,250,240,.96)) !important;
    border-color: rgba(201,122,64,.18) !important;
}
.v35-opportunity-tile.rank-1 {
    border-color: rgba(212,175,55,.55) !important;
    box-shadow: 0 24px 60px rgba(184,134,11,.18), 0 0 0 1px rgba(212,175,55,.18) inset !important;
}
.v35-opportunity-tile.rank-1:before {
    content:"TOP OPPORTUNITY";
    position:absolute;
    right:15px;
    top:15px;
    padding:6px 9px;
    border-radius:999px;
    color:#5F4100;
    background: linear-gradient(135deg, #FFF7D6, #D4AF37);
    border:1px solid rgba(184,134,11,.28);
    font-size:.66rem;
    letter-spacing:.08em;
    font-weight:950;
    z-index:2;
}
.v35-opportunity-tile.rank-2 {
    border-color: rgba(184,194,204,.55) !important;
}
.v35-opportunity-tile.rank-3 {
    border-color: rgba(205,127,50,.46) !important;
}
.v35-tile-rank {
    background: linear-gradient(135deg, #061622, #0f766e) !important;
}
.v35-opportunity-tile.rank-1 .v35-tile-rank {
    background: linear-gradient(135deg, #7A5200, #D4AF37) !important;
    color:#061622 !important;
    box-shadow: 0 10px 24px rgba(212,175,55,.28);
}
.v35-opportunity-tile.rank-2 .v35-tile-rank { background: linear-gradient(135deg, #475569, #B8C2CC) !important; }
.v35-opportunity-tile.rank-3 .v35-tile-rank { background: linear-gradient(135deg, #7C3F16, #CD7F32) !important; }
.v35-mini-pill.warn {
    background:#FFF1E6 !important;
    color:#8A421C !important;
    border-color: rgba(201,122,64,.25) !important;
}
.v35-mini-pill.ok {
    background:#dcfce7 !important;
    color:#166534 !important;
    border-color: rgba(16,185,129,.25) !important;
}
.v35-mini-pill.gold {
    background:#FFF7D6 !important;
    color:#7A5200 !important;
    border-color: rgba(212,175,55,.32) !important;
}
.v35-tile-trigger {
    background: linear-gradient(180deg, #fffaf0, #fff1e6) !important;
    border-color: rgba(201,122,64,.17) !important;
}

/* Section dividers and buttons */
.v35-divider-title:before {
    background: linear-gradient(90deg, #061622, #0f766e, #D4AF37) !important;
}
.v35-divider-title:after {
    background: linear-gradient(90deg, rgba(212,175,55,.42), rgba(15,118,110,.22), transparent) !important;
}
.stButton button:hover, .stDownloadButton button:hover {
    background: linear-gradient(90deg, #083344, #0f766e, #C97A40, #D4AF37) !important;
    color:white !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(90deg, #083344, #0f766e, #C97A40) !important;
    box-shadow: 0 10px 24px rgba(201,122,64,.18) !important;
}

/* Warm packet/text area focus */
textarea:focus,
input:focus {
    border-color: rgba(212,175,55,.55) !important;
    box-shadow: 0 0 0 3px rgba(212,175,55,.13) !important;
}

/* Monthly target emphasis */
.v35-target-gold {
    border-radius: 24px;
    padding: 18px 20px;
    background: radial-gradient(circle at 90% 8%, rgba(212,175,55,.30), transparent 30%), linear-gradient(135deg, #061622 0%, #083344 48%, #7A5200 128%);
    color: white;
    border: 1px solid rgba(212,175,55,.28);
    box-shadow: 0 24px 60px rgba(6,22,34,.18);
    margin: 12px 0 18px;
}
.v35-target-gold .label { color: rgba(255,247,214,.80); font-weight:950; text-transform:uppercase; letter-spacing:.08em; font-size:.72rem; }
.v35-target-gold .main { color: #FFF7D6; font-weight:950; font-size:1.65rem; letter-spacing:-.045em; margin-top:6px; }
.v35-target-gold .sub { color: rgba(255,255,255,.82); font-weight:750; margin-top:8px; }




/* ============================================================
   V35.5 ORGANIZATION SYSTEM
   The goal is not more decoration. It is workflow clarity:
   Command -> Discover -> Decide -> Execute -> Review.
   ============================================================ */
.v355-workflow-shell {
    border: 1px solid rgba(212,175,55,.24);
    border-radius: 28px;
    padding: 18px;
    background:
        radial-gradient(circle at 10% 0%, rgba(212,175,55,.16), transparent 30%),
        radial-gradient(circle at 100% 15%, rgba(201,122,64,.13), transparent 28%),
        linear-gradient(135deg, rgba(6,22,34,.98), rgba(8,51,68,.95) 54%, rgba(15,118,110,.86));
    box-shadow: 0 26px 64px rgba(6,22,34,.26);
    margin: 18px 0 22px 0;
    color: white;
}
.v355-workflow-title {
    font-size: 1.1rem;
    font-weight: 950;
    letter-spacing: -.035em;
    margin-bottom: 5px;
}
.v355-workflow-subtitle {
    color: rgba(255,255,255,.74);
    font-size: .88rem;
    font-weight: 650;
    margin-bottom: 16px;
}
.v355-workflow-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(130px, 1fr));
    gap: 12px;
}
.v355-step-card {
    position: relative;
    border-radius: 20px;
    padding: 15px 14px;
    min-height: 116px;
    background: rgba(255,255,255,.09);
    border: 1px solid rgba(255,255,255,.14);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.10);
}
.v355-step-card:before {
    content: "";
    position: absolute;
    left: 14px;
    right: 14px;
    top: 0;
    height: 3px;
    border-radius: 999px;
    background: linear-gradient(90deg, #D4AF37, #C97A40, #10b981);
}
.v355-step-number {
    color: #D4AF37;
    font-weight: 950;
    font-size: .76rem;
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: 8px;
}
.v355-step-title {
    font-size: .98rem;
    font-weight: 950;
    letter-spacing: -.035em;
    margin-bottom: 6px;
}
.v355-step-detail {
    font-size: .78rem;
    line-height: 1.35;
    color: rgba(255,255,255,.72);
    font-weight: 600;
}
.v355-decision-band {
    display: grid;
    grid-template-columns: 1.25fr .95fr .95fr .95fr;
    gap: 14px;
    margin: 14px 0 20px 0;
}
.v355-decision-card {
    border-radius: 24px;
    padding: 18px 18px;
    background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(248,250,252,.94));
    border: 1px solid rgba(15,118,110,.18);
    box-shadow: 0 18px 42px rgba(6,22,34,.10);
    position: relative;
    overflow: hidden;
}
.v355-decision-card:after {
    content: "";
    position: absolute;
    width: 170px;
    height: 170px;
    right: -85px;
    top: -90px;
    background: radial-gradient(circle, rgba(212,175,55,.18), transparent 64%);
}
.v355-decision-card.gold {
    border-color: rgba(212,175,55,.40);
    box-shadow: 0 20px 48px rgba(184,134,11,.15);
}
.v355-decision-card.green { border-color: rgba(16,185,129,.30); }
.v355-decision-card.copper { border-color: rgba(201,122,64,.36); }
.v355-decision-label {
    color: #64748b;
    font-size: .74rem;
    font-weight: 950;
    letter-spacing: .08em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.v355-decision-value {
    color: #061622;
    font-size: 1.55rem;
    line-height: 1.05;
    font-weight: 950;
    letter-spacing: -.055em;
}
.v355-decision-sub {
    color: #475569;
    font-size: .84rem;
    font-weight: 700;
    line-height: 1.35;
    margin-top: 8px;
}
.v355-next-action {
    border-radius: 24px;
    border: 1px solid rgba(212,175,55,.36);
    padding: 20px 22px;
    background:
        linear-gradient(90deg, rgba(212,175,55,.16), rgba(201,122,64,.11), rgba(16,185,129,.09)),
        linear-gradient(180deg, #ffffff, #f8fafc);
    box-shadow: 0 18px 46px rgba(6,22,34,.10);
    margin: 12px 0 20px 0;
}
.v355-next-action .label {
    font-size: .78rem;
    font-weight: 950;
    letter-spacing: .09em;
    text-transform: uppercase;
    color: #92400e;
    margin-bottom: 7px;
}
.v355-next-action .sentence {
    color: #061622;
    font-weight: 950;
    font-size: 1.12rem;
    line-height: 1.35;
    letter-spacing: -.025em;
}
.v355-section-band {
    margin: 28px 0 14px 0;
    padding: 13px 16px;
    border-radius: 18px;
    background: linear-gradient(90deg, #061622, #083344, rgba(15,118,110,.90));
    color: white;
    font-weight: 950;
    letter-spacing: -.03em;
    box-shadow: 0 14px 34px rgba(6,22,34,.13);
}
.v355-section-band span {
    color: #D4AF37;
    margin-right: 8px;
}
@media (max-width: 1000px) {
    .v355-workflow-grid, .v355-decision-band { grid-template-columns: 1fr; }
}



/* v35.7 Strategy Split: keep trading screen clean, tuck ChatGPT/dev packets away */
.v356-clean-note {
    border: 1px solid rgba(212,175,55,.28);
    border-left: 5px solid #D4AF37;
    border-radius: 18px;
    padding: 14px 16px;
    background: linear-gradient(135deg, rgba(255,251,235,.94), rgba(248,250,252,.96));
    box-shadow: 0 10px 26px rgba(6,22,34,.07);
    margin: 12px 0 16px 0;
}
.v356-clean-note .title {font-weight:950; color:#061622; letter-spacing:-.025em;}
.v356-clean-note .body {font-size:.92rem; color:#475569; font-weight:650; margin-top:4px;}
.v356-lab-badge {
    display:inline-flex; align-items:center; gap:8px;
    padding:8px 12px; border-radius:999px;
    background: linear-gradient(90deg, rgba(8,51,68,.96), rgba(201,122,64,.92));
    color:white; font-weight:950; font-size:.78rem;
    border:1px solid rgba(212,175,55,.28);
    box-shadow: 0 12px 28px rgba(6,22,34,.16);
}
.v356-mini-grid {display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; margin:12px 0 18px 0;}
.v356-mini-card {border:1px solid rgba(15,118,110,.18); border-radius:18px; padding:14px 15px; background:rgba(255,255,255,.9); box-shadow:0 10px 24px rgba(6,22,34,.06);}
.v356-mini-card .k {font-size:.75rem; font-weight:950; color:#64748b; text-transform:uppercase; letter-spacing:.07em;}
.v356-mini-card .v {font-size:1.15rem; font-weight:950; color:#061622; margin-top:3px;}
.v356-mini-card.gold {border-color:rgba(212,175,55,.38); background:linear-gradient(135deg, rgba(255,251,235,.98), rgba(255,255,255,.94));}
.v356-mini-card.copper {border-color:rgba(201,122,64,.35); background:linear-gradient(135deg, rgba(255,247,237,.98), rgba(255,255,255,.94));}
@media (max-width: 900px) {.v356-mini-grid {grid-template-columns: 1fr;}}

.v357-mode-note { border-radius:18px; padding:14px 16px; margin:10px 0 18px; background:linear-gradient(135deg, rgba(212,175,55,.12), rgba(15,118,110,.08)); border:1px solid rgba(212,175,55,.32); color:#0f172a; font-weight:850; }
.v357-mode-note span { color:#92400e; font-weight:950; }


/* ============================================================
   V35.8 DEPTH SYSTEM — 10% shadow layer across all boxes
   Goal: make every decision panel feel elevated without muddying the warm theme.
   ============================================================ */
:root {
    --v35-depth-1: 0 4px 12px rgba(6, 22, 34, 0.10);
    --v35-depth-2: 0 8px 24px rgba(6, 22, 34, 0.12);
    --v35-depth-3: 0 14px 36px rgba(6, 22, 34, 0.15);
    --v35-depth-gold: 0 12px 30px rgba(212, 175, 55, 0.16), 0 5px 14px rgba(6, 22, 34, 0.10);
    --v35-depth-copper: 0 12px 30px rgba(201, 122, 64, 0.14), 0 5px 14px rgba(6, 22, 34, 0.10);
    --v35-top-light: inset 0 1px 0 rgba(255, 255, 255, 0.72);
    --v35-bottom-shade: inset 0 -1px 0 rgba(6, 22, 34, 0.035);
}

/* Generic Streamlit surfaces: make them physically stand off the page */
div[data-testid="stMetric"],
div[data-testid="stDataFrame"],
div[data-testid="stTable"],
[data-testid="stExpander"],
.stAlert,
div[data-testid="stAlert"] {
    box-shadow: var(--v35-depth-1), var(--v35-top-light), var(--v35-bottom-shade) !important;
}

/* Main custom cards */
.v35-card,
.v35-status-card,
.v35-lane-card,
.v35-command-panel,
.v357-live-card,
.v357-dev-card,
.v35-opportunity-tile,
.v35-tile-trigger,
.v35-banner,
.v35-card-dark {
    box-shadow: var(--v35-depth-2), var(--v35-top-light), var(--v35-bottom-shade) !important;
}

/* Hero and major command panels get stronger elevation */
.v35-hero,
.v35-hero-boost,
.v35-banner,
.v35-command-panel.dark,
.v35-card-dark {
    box-shadow: var(--v35-depth-3), 0 0 0 1px rgba(255,255,255,.08) inset, var(--v35-top-light) !important;
}

/* Gold/copper semantic elevation */
.v35-command-panel.gold,
.v35-opportunity-tile.rank-1,
.v35-mini-pill.gold {
    box-shadow: var(--v35-depth-gold), var(--v35-top-light), var(--v35-bottom-shade) !important;
}
.v35-command-panel.copper,
.v35-mini-pill.warn,
.v35-mode-PROBE {
    box-shadow: var(--v35-depth-copper), var(--v35-top-light), var(--v35-bottom-shade) !important;
}

/* Tile depth + subtle lift makes opportunity cards easier to scan */
.v35-opportunity-tile {
    transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
}
.v35-opportunity-tile:hover {
    transform: translateY(-2px);
    box-shadow: 0 14px 34px rgba(6,22,34,.14), var(--v35-top-light), var(--v35-bottom-shade) !important;
}
.v35-opportunity-tile.rank-1:hover {
    box-shadow: 0 18px 42px rgba(212,175,55,.22), 0 8px 20px rgba(6,22,34,.12), var(--v35-top-light) !important;
}

/* Buttons should also sit above the canvas */
.stButton button,
.stDownloadButton button,
button[kind="secondary"],
button[kind="primary"] {
    box-shadow: var(--v35-depth-1), var(--v35-top-light) !important;
    transition: transform .14s ease, box-shadow .14s ease, background .14s ease;
}
.stButton button:hover,
.stDownloadButton button:hover,
button[kind="secondary"]:hover,
button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: var(--v35-depth-2), var(--v35-top-light) !important;
}

/* Inputs remain readable but no longer flat */
div[data-baseweb="select"] > div,
input,
textarea {
    box-shadow: 0 3px 9px rgba(6,22,34,.08), inset 0 1px 0 rgba(255,255,255,.70) !important;
}

/* Sidebar controls get depth too, but softer because sidebar is dark */
section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] select,
section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] button {
    box-shadow: 0 4px 12px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.32) !important;
}

/* Tables: shadow plus a soft rim so they read as panels */
div[data-testid="stDataFrame"],
div[data-testid="stTable"] {
    border: 1px solid rgba(201,122,64,.18) !important;
    outline: 1px solid rgba(255,255,255,.42);
    outline-offset: -2px;
}

/* Expander depth: strategy/dev sections stay visually tucked away but clearly clickable */
[data-testid="stExpander"] {
    background: rgba(255,255,255,.74) !important;
    backdrop-filter: blur(6px);
}

/* Extra separation for the live trading summary cards */
.v357-live-card {
    border-color: rgba(212,175,55,.22) !important;
}

/* Keep the whole app premium, not noisy: dark text panels still get a clean top sheen */
.v35-command-panel.dark,
.v35-card-dark,
.v35-banner {
    border-top-color: rgba(255,247,214,.20) !important;
}


/* ============================================================
   V35.9 SHADED PANEL SYSTEM — remove pure-white card surfaces
   Goal: preserve readability while replacing flat white boxes with
   warm, dimensional panels that match the navy/teal/gold desk.
   ============================================================ */
:root {
    --v35-panel-cream: #fff6e6;
    --v35-panel-warm: #f7efe2;
    --v35-panel-mist: #eaf6f4;
    --v35-panel-blue: #eaf1fb;
    --v35-panel-ink: #0b1f33;
    --v35-panel-border: rgba(15, 118, 110, .20);
    --v35-panel-border-warm: rgba(201, 122, 64, .22);
    --v35-panel-shadow: 0 8px 22px rgba(6, 22, 34, .11);
    --v35-panel-inset: inset 0 1px 0 rgba(255, 255, 255, .58), inset 0 -1px 0 rgba(6, 22, 34, .035);
}

/* App canvas: slightly warmer so shaded panels do not sit on a cold flat page */
.stApp {
    background:
        radial-gradient(circle at 92% 4%, rgba(212,175,55,.10), transparent 26%),
        radial-gradient(circle at 8% 2%, rgba(16,185,129,.10), transparent 28%),
        linear-gradient(180deg, #f8efe0 0%, #eef6f7 42%, #e7f0f2 100%) !important;
}

/* Global light surfaces: no pure white cards */
div[data-testid="stMetric"],
.v34-card,
.v35-card,
.v35-status-card,
.v35-lane-card,
.v35-command-panel,
.v357-live-card,
.v357-dev-card,
.v356-mini-card,
.v35-opportunity-tile,
.v35-tile-trigger,
[data-testid="stExpander"],
div[data-testid="stDataFrame"],
div[data-testid="stTable"] {
    background:
        radial-gradient(circle at 88% 8%, rgba(212,175,55,.105), transparent 30%),
        linear-gradient(180deg, var(--v35-panel-cream) 0%, var(--v35-panel-mist) 100%) !important;
    border-color: var(--v35-panel-border) !important;
    box-shadow: var(--v35-panel-shadow), var(--v35-panel-inset) !important;
}

/* Important command panels get richer shading, not more brightness */
.v35-command-panel,
.v357-live-card {
    background:
        radial-gradient(circle at 88% 10%, rgba(212,175,55,.13), transparent 31%),
        linear-gradient(145deg, #fff1d6 0%, #edf7f5 62%, #e6eef8 100%) !important;
}

/* Top opportunity: warm gold tint without yellow glare */
.v35-command-panel.gold,
.v35-opportunity-tile.rank-1,
.v356-mini-card.gold {
    background:
        radial-gradient(circle at 84% 10%, rgba(212,175,55,.25), transparent 32%),
        linear-gradient(145deg, #fff0c2 0%, #f7ead0 43%, #eaf6f4 100%) !important;
    border-color: rgba(212,175,55,.46) !important;
    box-shadow: 0 14px 34px rgba(212,175,55,.18), 0 8px 18px rgba(6,22,34,.10), var(--v35-panel-inset) !important;
}

/* Pending/probe/action panels: copper-tinted, not warning-yellow */
.v35-command-panel.copper,
.v35-mode-PROBE,
.v35-tile-trigger,
.v356-mini-card.copper {
    background:
        radial-gradient(circle at 86% 10%, rgba(201,122,64,.23), transparent 33%),
        linear-gradient(145deg, #ffe6cf 0%, #f5eadf 48%, #eaf2f8 100%) !important;
    border-color: rgba(201,122,64,.38) !important;
    box-shadow: 0 12px 30px rgba(201,122,64,.15), 0 6px 15px rgba(6,22,34,.10), var(--v35-panel-inset) !important;
}

/* Mode cards: keep semantic tinting but remove white centers */
.v35-mode-ATTACK {
    background: radial-gradient(circle at 86% 8%, rgba(16,185,129,.18), transparent 30%), linear-gradient(160deg, #dcfce7 0%, #eaf7f2 58%, #f8ecd4 100%) !important;
}
.v35-mode-TRAIN {
    background: radial-gradient(circle at 86% 8%, rgba(37,99,235,.16), transparent 30%), linear-gradient(160deg, #e7f0ff 0%, #edf7f5 58%, #f7ead0 100%) !important;
}
.v35-mode-PROTECT {
    background: radial-gradient(circle at 86% 8%, rgba(239,68,68,.15), transparent 30%), linear-gradient(160deg, #fee2e2 0%, #f4ebe5 58%, #e6eef8 100%) !important;
}

/* Tables sit inside shaded frames while their internal grid remains readable */
div[data-testid="stDataFrame"] iframe,
div[data-testid="stTable"] table {
    background: transparent !important;
}

/* Inputs and text areas: soft parchment/mist instead of stark white */
input,
textarea,
div[data-baseweb="select"] > div {
    background: linear-gradient(180deg, #fff6e6 0%, #eef7f5 100%) !important;
    border-color: rgba(201,122,64,.22) !important;
    box-shadow: 0 4px 11px rgba(6,22,34,.085), inset 0 1px 0 rgba(255,255,255,.62) !important;
}

/* Buttons keep their premium raised feel but lose the white plastic look */
.stButton button,
.stDownloadButton button,
button[kind="secondary"],
button[kind="primary"] {
    background: linear-gradient(180deg, #fff0cf 0%, #eaf6f4 100%) !important;
    border-color: rgba(201,122,64,.28) !important;
    color: #061622 !important;
}
.stButton button:hover,
.stDownloadButton button:hover,
button[kind="secondary"]:hover,
button[kind="primary"]:hover {
    background: linear-gradient(180deg, #ffe4ad 0%, #dff4ef 100%) !important;
}

/* Expander headers should feel like tucked-away panels, not white accordions */
[data-testid="stExpander"] summary {
    background: linear-gradient(90deg, rgba(255,240,207,.72), rgba(234,246,244,.72)) !important;
    border-radius: 14px !important;
}

/* Data download / text packet areas in developer mode stay readable but visually secondary */
.stTextArea textarea {
    background: linear-gradient(180deg, #f9efd9 0%, #eaf4f3 100%) !important;
    color: #0f172a !important;
}

/* Sidebar input exception: keep dark-sidebar controls readable with warm tint */
section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: linear-gradient(180deg, #fff0cf 0%, #edf7f5 100%) !important;
    color: #061622 !important;
}

/* Plotly chart area warmer, so charts no longer look pasted onto a white canvas */
.js-plotly-plot .plotly,
.js-plotly-plot .main-svg {
    border-radius: 18px !important;
}

</style>
""", unsafe_allow_html=True)



st.markdown("""
<style>
/* ============================================================
   V35.10 WARM TABLE + PANEL OVERRIDE
   This is the final pass that removes the remaining pure-white
   dataframe/card look and replaces it with parchment/gold depth.
   ============================================================ */
:root {
    --v3510-bg-dark: #071927;
    --v3510-panel: #fff0c6;
    --v3510-panel-2: #f7e5b7;
    --v3510-panel-3: #ecd09a;
    --v3510-gold: #d4af37;
    --v3510-copper: #c97a40;
    --v3510-ink: #061622;
    --v3510-grid: rgba(135, 92, 19, .18);
}

/* Section containers behind tables: dark terminal frame + warm inner panel */
div[data-testid="stDataFrame"],
div[data-testid="stTable"] {
    background:
        linear-gradient(180deg, rgba(255, 238, 190, .96) 0%, rgba(247, 226, 179, .96) 100%) !important;
    border: 1px solid rgba(212,175,55,.58) !important;
    border-radius: 22px !important;
    box-shadow:
        0 0 0 1px rgba(255, 246, 218, .55) inset,
        0 3px 0 rgba(255,255,255,.38) inset,
        0 16px 34px rgba(6,22,34,.18),
        0 0 24px rgba(212,175,55,.10) !important;
    overflow: hidden !important;
}

/* Streamlit's dataframe is canvas/grid based, so target every exposed layer aggressively. */
div[data-testid="stDataFrame"] * {
    border-color: var(--v3510-grid) !important;
}

div[data-testid="stDataFrame"] [role="grid"],
div[data-testid="stDataFrame"] [role="rowgroup"],
div[data-testid="stDataFrame"] [role="row"],
div[data-testid="stDataFrame"] [role="gridcell"],
div[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stDataFrame"] canvas,
div[data-testid="stDataFrame"] iframe {
    background-color: #fff0c6 !important;
}

/* For dataframe implementations that expose normal DOM cells. */
div[data-testid="stDataFrame"] th,
div[data-testid="stTable"] th {
    background: linear-gradient(180deg, #ffe8b4 0%, #f1cf83 100%) !important;
    color: var(--v3510-ink) !important;
    font-weight: 900 !important;
    border-color: var(--v3510-grid) !important;
}

div[data-testid="stDataFrame"] td,
div[data-testid="stTable"] td {
    background: #fff0c6 !important;
    color: var(--v3510-ink) !important;
    border-color: var(--v3510-grid) !important;
}

div[data-testid="stTable"] tbody tr:nth-child(even) td,
div[data-testid="stDataFrame"] tbody tr:nth-child(even) td {
    background: #f7e5b7 !important;
}

/* Table section headers get the same premium dark frame from the mockup. */
h2, h3, .v34-section-title, .v35-section-title {
    color: #061622 !important;
}

/* Warm up generic white blocks that Streamlit injects around tables/cards. */
.element-container:has(div[data-testid="stDataFrame"]),
.element-container:has(div[data-testid="stTable"]) {
    background:
        radial-gradient(circle at 98% 4%, rgba(212,175,55,.13), transparent 32%),
        linear-gradient(180deg, rgba(7,25,39,.04), rgba(7,25,39,.015)) !important;
    border-radius: 24px !important;
}

/* Metric/card panels should be parchment, not white. */
div[data-testid="stMetric"],
.v34-card,
.v35-card,
.v35-status-card,
.v35-lane-card,
.v35-opportunity-tile,
.v356-mini-card,
.v357-live-card {
    background:
        radial-gradient(circle at 86% 8%, rgba(212,175,55,.16), transparent 32%),
        linear-gradient(180deg, #fff0c6 0%, #f4e2b0 100%) !important;
    border-color: rgba(212,175,55,.38) !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.62),
        0 12px 28px rgba(6,22,34,.13),
        0 0 18px rgba(212,175,55,.08) !important;
}

/* Rank-one / top-opportunity cards get a stronger gold frame like the reference image. */
.v35-opportunity-tile.rank-1,
.v35-command-panel.gold,
.v356-mini-card.gold {
    background:
        radial-gradient(circle at 84% 10%, rgba(212,175,55,.28), transparent 35%),
        linear-gradient(180deg, #ffe7a8 0%, #f4d58d 100%) !important;
    border-color: rgba(212,175,55,.72) !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.70),
        0 16px 36px rgba(6,22,34,.18),
        0 0 28px rgba(212,175,55,.20) !important;
}

/* Inputs stay warm too. */
input, textarea, div[data-baseweb="select"] > div {
    background: linear-gradient(180deg, #fff0c6 0%, #f6e2ae 100%) !important;
    color: #061622 !important;
    border-color: rgba(212,175,55,.42) !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# DEON'S TRADER DASHBOARD v35.1
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
# V35.3 OPPORTUNITY DISCOVERY UNIVERSE
# ============================================================

OPPORTUNITY_DISCOVERY_UNIVERSE = [
    # Mega-cap liquidity / index leaders
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "AMD", "NFLX",
    # Semis / AI hardware
    "ARM", "MU", "MRVL", "TSM", "SMCI", "ASML", "LRCX", "KLAC", "AMAT", "ON", "MCHP", "QCOM",
    # AI infrastructure / power / networking
    "VRT", "ANET", "DELL", "HPE", "NTAP", "CEG", "VST", "ETN", "GEV", "PWR",
    # Software / AI / cloud
    "PLTR", "APP", "ORCL", "SNOW", "DDOG", "NET", "CRWD", "PANW", "ZS", "MDB", "NOW", "CRM", "ADBE",
    # Fintech / crypto beta
    "HOOD", "SOFI", "COIN", "MSTR", "AFRM", "PYPL", "SQ", "UPST",
    # Momentum / consumer internet / high beta
    "RDDT", "HIMS", "UBER", "DASH", "SHOP", "ROKU", "DKNG", "RBLX", "TTD", "SE", "BABA", "PDD",
    # Biotech / healthcare momentum proxies
    "LLY", "NVO", "MRNA", "VKTX", "TMDX", "ISRG",
    # Industrials / defense / energy beta
    "BA", "GE", "RTX", "LMT", "CAT", "XOM", "CVX", "OXY", "SLB",
    # ETFs used as opportunity and regime proxies
    "SPY", "QQQ", "IWM", "SMH", "SOXX", "XLK", "XLF", "XLE", "ARKK",
]

OPPORTUNITY_SECTOR = {
    "AAPL": "Mega Cap", "NFLX": "Mega Cap",
    "ASML": "Semis", "LRCX": "Semis", "KLAC": "Semis", "AMAT": "Semis", "ON": "Semis", "MCHP": "Semis", "QCOM": "Semis",
    "HPE": "AI Infra", "NTAP": "AI Infra", "VST": "Energy", "ETN": "AI Infra", "GEV": "Energy", "PWR": "AI Infra",
    "SNOW": "Software", "DDOG": "Software", "NET": "Software", "CRWD": "Cybersecurity", "PANW": "Cybersecurity", "ZS": "Cybersecurity", "MDB": "Software", "NOW": "Software", "CRM": "Software", "ADBE": "Software",
    "AFRM": "Fintech", "PYPL": "Fintech", "SQ": "Fintech", "UPST": "Fintech",
    "UBER": "Momentum", "DASH": "Momentum", "SHOP": "Momentum", "ROKU": "High Beta", "DKNG": "High Beta", "RBLX": "High Beta", "TTD": "Software", "SE": "High Beta", "BABA": "China", "PDD": "China",
    "LLY": "Healthcare", "NVO": "Healthcare", "MRNA": "Biotech", "VKTX": "Biotech", "TMDX": "Healthcare", "ISRG": "Healthcare",
    "BA": "Industrials", "GE": "Industrials", "RTX": "Defense", "LMT": "Defense", "CAT": "Industrials", "XOM": "Energy", "CVX": "Energy", "OXY": "Energy", "SLB": "Energy",
    "SPY": "ETF", "QQQ": "ETF", "IWM": "ETF", "SMH": "ETF", "SOXX": "ETF", "XLK": "ETF", "XLF": "ETF", "XLE": "ETF", "ARKK": "ETF",
}
SECTOR.update(OPPORTUNITY_SECTOR)


def ct_now():
    """Central Time timestamp for all dashboard displays and logs."""
    return datetime.now(ZoneInfo("America/Chicago"))


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

    # Composite score. This is v35's main ranking score.
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

LEARNING_FILE = "trade_learning_log_v35_2.csv"
SCAN_HISTORY_FILE = "scan_history_v35_4.csv"
ROBINHOOD_MIRROR_FILE = "robinhood_mirror_v35_2.csv"

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
        return "No v35 professional score available."

    leader = scan.iloc[0]

    lines = []
    lines.append("V35 PROFESSIONAL LAYERS")
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
    v34 repair layer:
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
    v34 repairs missing trade-plan fields and supports Adaptive execution.
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
    lines.append("TRADE EXECUTION ENGINE v35")
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
# V34 DAILY TRADER MODE
# ============================================================

def v34_trade_frequency_score(row):
    score = 0
    signal = str(row.get("Signal", "")).upper()
    verdict = str(row.get("Professional Verdict", row.get("Composite Verdict", ""))).upper()
    setup = str(row.get("Best Setup", "")).upper()
    reason = str(row.get("Reason", "")).upper()
    tier = str(row.get("Tier", "")).upper()

    score += safe_num(row.get("Money Flow Score", 0)) * 0.22
    score += safe_num(row.get("Best Score", 0)) * 0.18
    score += safe_num(row.get("Total Opportunity Score", 0)) * 0.18
    score += safe_num(row.get("RS Score", 0)) * 0.12
    score += safe_num(row.get("ORB Score", 0)) * 0.10
    score += safe_num(row.get("VWAP Score", 0)) * 0.10
    score += safe_num(row.get("Momentum Score", 0)) * 0.10

    if signal == "TRADE":
        score += 12
    elif signal == "SMALL TRADE":
        score += 6
    elif signal == "WATCH":
        score += 3

    if "TRADE CANDIDATE" in verdict:
        score += 10
    elif "WAIT" in verdict:
        score += 6
    elif "AVOID" in verdict:
        score -= 8

    if tier == "A+":
        score += 8
    elif tier == "A":
        score += 5
    elif tier == "B":
        score += 2

    if "ORB" in setup or "BREAKOUT" in reason:
        score += 5
    if "VWAP" in setup or "VWAP" in reason:
        score += 4
    if "RELATIVE" in reason or "STRONG RS" in reason:
        score += 4
    if "GAP" in setup or "GAP" in reason:
        score += 3

    return round(score, 1)


def v34_setup_playbook(row):
    setup = str(row.get("Best Setup", "")).upper()
    reason = str(row.get("Reason", "")).upper()
    above_vwap = bool(row.get("Above VWAP", False))
    or_zone = str(row.get("OR Zone", "")).upper()

    if "ORB" in setup or "BREAKOUT" in reason or "BREAKOUT" in or_zone:
        return "ORB Breakout"
    if "VWAP" in setup and above_vwap:
        return "VWAP Reclaim / Hold"
    if "GAP" in setup or "GAP" in reason:
        return "Gap-and-Go"
    if "MOMENTUM" in setup:
        return "Relative Strength Continuation"
    if "DAILY" in setup:
        return "Daily Breakout"
    return "First Pullback / Watch"


def v34_long_short_bias(row):
    signal = str(row.get("Signal", "")).upper()
    verdict = str(row.get("Professional Verdict", row.get("Composite Verdict", ""))).upper()
    gap = safe_num(row.get("Gap %", 0))
    one_day = safe_num(row.get("1D %", 0))
    above_vwap = bool(row.get("Above VWAP", False))
    or_zone = str(row.get("OR Zone", "")).upper()
    rs = safe_num(row.get("RS Score", 0))
    mf = safe_num(row.get("Money Flow Score", 0))

    if signal in ["TRADE", "SMALL TRADE"] and above_vwap and ("BREAKOUT" in or_zone or rs >= 60 or mf >= 55):
        return "Long Bias"
    if one_day < -2 and gap < -2 and not above_vwap:
        return "Short Bias Watch"
    if "AVOID" in verdict and one_day < -3:
        return "Short Bias Watch"
    return "Neutral / Watch"


def v34_build_daily_opportunity_board(scan_df, candidate_goal=8, frequency_bias=65):
    if scan_df is None or len(scan_df) == 0:
        return pd.DataFrame()

    board = scan_df.copy()
    board["Trade Frequency Score"] = board.apply(v34_trade_frequency_score, axis=1)
    board["Playbook"] = board.apply(v34_setup_playbook, axis=1)
    board["Bias"] = board.apply(v34_long_short_bias, axis=1)

    min_score = 65 - (frequency_bias * 0.35)
    board["Daily Trader Qualified"] = board["Trade Frequency Score"] >= min_score

    def action(row):
        verdict = str(row.get("Professional Verdict", row.get("Composite Verdict", ""))).upper()
        signal = str(row.get("Signal", "")).upper()
        freq = safe_num(row.get("Trade Frequency Score", 0))
        bias = row.get("Bias", "")

        if "Short Bias" in bias:
            return "SHORT WATCH"
        if signal == "TRADE" and "AVOID" not in verdict:
            return "TRADE NOW / VERIFY CHART"
        if signal == "SMALL TRADE" and freq >= 55:
            return "SMALL TRADE / VERIFY CHART"
        if "WAIT" in verdict:
            return "WAIT FOR TRIGGER"
        if freq >= 50:
            return "WATCH ACTIVE"
        return "NO TRADE"

    board["V35 Action"] = board.apply(action, axis=1)
    board = board.sort_values(
        ["Daily Trader Qualified", "Trade Frequency Score", "Total Opportunity Score"],
        ascending=[False, False, False],
    )

    cols = [
        "Ticker", "Sector", "V35 Action", "Bias", "Playbook", "Tier",
        "Trade Frequency Score", "Professional Score", "Composite Score",
        "Total Opportunity Score", "Money Flow Score", "Best Score",
        "Price", "Stop", "Target 1", "Shares", "Position $", "Dollar Risk",
        "Reason"
    ]
    cols = [c for c in cols if c in board.columns]
    return board[cols].head(max(candidate_goal, 3))


# ============================================================
# V35 CANDIDATE GRADING / ORB ENGINE / BROKER MIRROR
# ============================================================

def v35_candidate_grade(row):
    """A/B/C/D grading keeps daily workflow useful without weakening risk gates."""
    prof = safe_num(row.get("Professional Score", 0))
    comp = safe_num(row.get("Composite Score", 0))
    mf = safe_num(row.get("Money Flow Score", 0))
    orb = safe_num(row.get("ORB Score", 0))
    vwap = safe_num(row.get("VWAP Score", 0))
    rs = safe_num(row.get("RS Score", 0))
    ev = safe_num(row.get("EV / Share", 0))
    rr = safe_num(row.get("Reward/Risk", 0))
    verdict = str(row.get("Professional Verdict", row.get("Composite Verdict", ""))).upper()
    signal = str(row.get("Signal", "")).upper()
    or_status = str(row.get("OR Status", ""))
    above_vwap = bool(row.get("Above VWAP", False))
    earnings_timing = str(row.get("Earnings Timing", "")).lower()
    catalyst = safe_num(row.get("Catalyst Score", 50))

    broken = or_status == "Below OR Low"
    earnings_block = "reports" in earnings_timing and "bmo" in earnings_timing

    if earnings_block or catalyst <= 20 or (broken and not above_vwap):
        return "D", "Blocked by earnings/catalyst/OR breakdown risk"

    if signal == "TRADE" and "AVOID" not in verdict and prof >= 72 and mf >= 58 and rr >= 1.2 and ev >= -0.10 and above_vwap:
        return "A", "Actionable after chart/trigger confirmation"

    if ("WAIT" in verdict or signal in ["SMALL TRADE", "WATCH"]) and prof >= 52 and max(orb, vwap, mf, comp) >= 52 and rr >= 1.1 and not broken:
        return "B", "Close candidate; needs OR/VWAP trigger"

    if max(prof, comp, mf, rs) >= 40 or row.get("Chart Needed", False):
        return "C", "Watchlist only; useful but not ready"

    return "D", "Ignore until structure improves"


def v35_orb_status_score(row):
    or_status = str(row.get("OR Status", "Unknown"))
    or_zone = str(row.get("OR Zone", "Unknown"))
    above_vwap = bool(row.get("Above VWAP", False))
    rs = safe_num(row.get("RS Score", 0))
    rvol = safe_num(row.get("Rel Vol", 0))
    score = 50
    if or_status == "Above OR High": score += 25
    elif or_zone in ["Near breakout", "Upper range"]: score += 12
    elif or_status == "Below OR Low": score -= 30
    if above_vwap: score += 12
    else: score -= 8
    if rs >= 70: score += 8
    elif rs >= 60: score += 4
    if rvol >= 1.5: score += 5
    elif rvol < 0.75: score -= 5
    return int(max(0, min(100, score)))


def v35_trigger_text(row):
    grade = str(row.get("Candidate Grade", ""))
    ticker = row.get("Ticker", "")
    or_high = row.get("OR High", np.nan)
    or_low = row.get("OR Low", np.nan)
    vwap = row.get("VWAP", np.nan)
    price = row.get("Price", np.nan)
    if grade == "A":
        return f"{ticker}: confirm price holds above VWAP {vwap} and does not lose OR low {or_low}."
    if grade == "B":
        return f"{ticker}: trigger only on reclaim/break above OR high {or_high} with VWAP hold near {vwap}."
    if grade == "C":
        return f"{ticker}: watch only; needs VWAP reclaim and stronger flow before sizing."
    return f"{ticker}: no trigger; ignore until above VWAP/OR structure improves."


def add_v35_scores(scan):
    scan = scan.copy()
    grades = scan.apply(v35_candidate_grade, axis=1)
    scan["Candidate Grade"] = [g[0] for g in grades]
    scan["Grade Reason"] = [g[1] for g in grades]
    scan["ORB Status Score"] = scan.apply(v35_orb_status_score, axis=1)
    scan["VWAP Confirm Score"] = np.where(scan["Above VWAP"], 70, 35)
    scan["V35 Score"] = (
        scan["Professional Score"] * 0.32 +
        scan["Money Flow Score"] * 0.22 +
        scan["ORB Status Score"] * 0.18 +
        scan["VWAP Confirm Score"] * 0.10 +
        scan["Learning Score"] * 0.08 +
        scan["Catalyst Score"] * 0.10
    ).round(1)
    scan["V35 Trigger"] = scan.apply(v35_trigger_text, axis=1)
    grade_rank = {"A": 4, "B": 3, "C": 2, "D": 1}
    scan["Grade Rank"] = scan["Candidate Grade"].map(grade_rank).fillna(0)
    return scan.sort_values(["Grade Rank", "V35 Score", "Professional Score", "Money Flow Score"], ascending=False).reset_index(drop=True)


def v35_candidate_board(scan, limit=12):
    cols = [
        "Ticker", "Candidate Grade", "V35 Score", "Professional Verdict", "Signal", "Best Setup",
        "ORB Status Score", "OR Status", "OR Zone", "Above VWAP", "VWAP", "OR High", "OR Low",
        "Money Flow Score", "Professional Score", "Composite Score", "RS Score", "Rel Vol",
        "Price", "Stop", "Target 1", "Shares", "Dollar Risk", "V35 Trigger", "Grade Reason"
    ]
    cols = [c for c in cols if c in scan.columns]
    return scan[cols].head(limit)


def v35_robinhood_mirror_text(scan, cash):
    a = int((scan["Candidate Grade"] == "A").sum()) if "Candidate Grade" in scan.columns else 0
    b = int((scan["Candidate Grade"] == "B").sum()) if "Candidate Grade" in scan.columns else 0
    leader = scan.iloc[0]
    lines = [
        "ROBINHOOD REAL / ALPACA PAPER MIRROR v35.1",
        f"Cash baseline: ${cash:,.2f}",
        f"A candidates: {a} | B candidates: {b}",
        f"Top mirror candidate: {leader['Ticker']} / Grade {leader.get('Candidate Grade', 'N/A')} / V35 Score {leader.get('V35 Score', 'N/A')}",
        "Workflow: enter Robinhood manually only after chart trigger; immediately mirror same symbol/size logic in Alpaca paper when configured.",
        "Safety: never route Alpaca live unless endpoint and arming phrase explicitly confirm live mode."
    ]
    return "\n".join(lines)


# ============================================================
# V35.1 DECISION AUDIT / SCAN HISTORY / REAL-PAPER MIRROR
# ============================================================

def v351_rejection_reason(row):
    """Explains why a symbol is not a real-trade candidate right now."""
    reasons = []
    grade = str(row.get("Candidate Grade", ""))
    verdict = str(row.get("Professional Verdict", row.get("Composite Verdict", ""))).upper()
    signal = str(row.get("Signal", "")).upper()
    or_status = str(row.get("OR Status", ""))
    above_vwap = bool(row.get("Above VWAP", False))
    rr = safe_num(row.get("Reward/Risk", 0))
    ev = safe_num(row.get("EV / Share", 0))
    prof = safe_num(row.get("Professional Score", 0))
    v35 = safe_num(row.get("V35 Score", 0))
    mf = safe_num(row.get("Money Flow Score", 0))
    shares = safe_num(row.get("Shares", 0))
    risk = safe_num(row.get("Dollar Risk", 0))
    catalyst = safe_num(row.get("Catalyst Score", 50))
    earnings_timing = str(row.get("Earnings Timing", "")).lower()

    if grade in ["A", "B"]:
        return "Qualified review candidate; final decision still requires chart trigger and risk check."
    if "AVOID" in verdict:
        reasons.append("professional verdict is avoid/watch only")
    if signal not in ["TRADE", "SMALL TRADE"]:
        reasons.append("signal is not tradeable")
    if or_status == "Below OR Low":
        reasons.append("price is below opening-range low")
    if not above_vwap:
        reasons.append("price is not above VWAP")
    if rr < 1.10:
        reasons.append(f"reward/risk too low ({rr:.2f})")
    if ev < -0.10:
        reasons.append(f"expected value/share negative ({ev:.2f})")
    if prof < 52:
        reasons.append(f"professional score below review floor ({prof:.1f})")
    if v35 < 50:
        reasons.append(f"V35.1 score below active threshold ({v35:.1f})")
    if mf < 50:
        reasons.append(f"money-flow score weak ({mf:.0f})")
    if shares <= 0 or risk <= 0:
        reasons.append("no valid position size/risk plan")
    if catalyst <= 25:
        reasons.append(f"negative catalyst score ({catalyst:.0f})")
    if "reports" in earnings_timing and "bmo" in earnings_timing:
        reasons.append("earnings-before-open risk block")

    return "; ".join(reasons[:5]) if reasons else "Not disqualified by one hard rule, but lacks enough combined confirmation."


def v351_action_plan(row):
    grade = str(row.get("Candidate Grade", "D"))
    ticker = row.get("Ticker", "")
    or_high = row.get("OR High", np.nan)
    or_low = row.get("OR Low", np.nan)
    vwap = row.get("VWAP", np.nan)
    stop = row.get("Stop", np.nan)
    setup = row.get("Best Setup", "")

    if grade == "A":
        return f"{ticker}: verify {setup} on chart; long only while holding VWAP {vwap} and above invalidation {max(safe_num(or_low), safe_num(stop)):.2f}."
    if grade == "B":
        return f"{ticker}: wait for trigger above OR high {or_high}; no entry if it rejects VWAP {vwap} or loses OR low {or_low}."
    if grade == "C":
        return f"{ticker}: keep on watch; upgrade only after VWAP reclaim plus stronger money flow/RS."
    return f"{ticker}: skip. Do not force a trade until the rejection reasons clear."


def add_v351_decision_audit(scan):
    scan = scan.copy()
    scan["V35.1 Score"] = (
        scan["V35 Score"] * 0.55 +
        scan["ORB Status Score"] * 0.15 +
        scan["VWAP Confirm Score"] * 0.10 +
        scan["Money Flow Score"] * 0.10 +
        scan["RS Score"] * 0.05 +
        scan["Premarket Score"] * 0.05
    ).round(1)
    scan["Rejection Reason"] = scan.apply(v351_rejection_reason, axis=1)
    scan["Action Plan"] = scan.apply(v351_action_plan, axis=1)
    scan["Real Trade Review"] = scan["Candidate Grade"].isin(["A", "B"])
    scan["Paper Mirror Eligible"] = scan["Candidate Grade"].isin(["A", "B", "C"])
    grade_rank = {"A": 4, "B": 3, "C": 2, "D": 1}
    scan["V35.1 Rank"] = scan["Candidate Grade"].map(grade_rank).fillna(0) * 1000 + scan["V35.1 Score"]
    return scan.sort_values(["V35.1 Rank", "Professional Score", "Money Flow Score"], ascending=False).reset_index(drop=True)


def v351_today_action_plan(scan, market_light, market_score, market_reason):
    lines = []
    grade_counts = scan["Candidate Grade"].value_counts().to_dict() if "Candidate Grade" in scan.columns else {}
    leader = scan.iloc[0]
    review = scan[scan["Candidate Grade"].isin(["A", "B"])].copy()

    lines.append("TODAY'S ACTION PLAN v35.1")
    lines.append(f"Market state: {market_light} / {market_score}/100 / {market_reason}")
    lines.append(f"Grades: A={grade_counts.get('A', 0)} | B={grade_counts.get('B', 0)} | C={grade_counts.get('C', 0)} | D={grade_counts.get('D', 0)}")

    if not review.empty:
        top = review.iloc[0]
        lines.append(f"Primary review: {top['Ticker']} / Grade {top['Candidate Grade']} / V35.1 {top['V35.1 Score']} / {top['Best Setup']}")
        lines.append(f"Trigger: {top['Action Plan']}")
        lines.append(f"Risk plan: entry ref {top['Price']} / stop {top['Stop']} / T1 {top['Target 1']} / shares {top['Shares']} / max risk ${top['Dollar Risk']}")
    else:
        lines.append(f"No A/B real-trade review names. Strongest monitor: {leader['Ticker']} / Grade {leader.get('Candidate Grade', 'N/A')} / reason: {leader.get('Rejection Reason', '')}")

    lines.append("Rule: Robinhood real trade requires A/B grade + chart trigger + defined stop. Alpaca paper can mirror A/B and optionally test C with tiny size only.")
    return "\n".join(lines)


def v351_scan_history_row(scan, market_light, market_score, market_reason):
    grade_counts = scan["Candidate Grade"].value_counts().to_dict() if "Candidate Grade" in scan.columns else {}
    leader = scan.iloc[0]
    return {
        "Timestamp CT": ct_now().strftime("%Y-%m-%d %H:%M:%S"),
        "Market Light": market_light,
        "Market Score": market_score,
        "Market Reason": market_reason,
        "Scanned": len(scan),
        "Grade A": int(grade_counts.get("A", 0)),
        "Grade B": int(grade_counts.get("B", 0)),
        "Grade C": int(grade_counts.get("C", 0)),
        "Grade D": int(grade_counts.get("D", 0)),
        "Top Ticker": leader.get("Ticker", ""),
        "Top Grade": leader.get("Candidate Grade", ""),
        "Top V35.1 Score": leader.get("V35.1 Score", np.nan),
        "Top Setup": leader.get("Best Setup", ""),
        "Top Action Plan": leader.get("Action Plan", ""),
    }


def load_csv_file(path, columns=None):
    try:
        if Path(path).exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return pd.DataFrame(columns=columns or [])


def append_csv_row(path, row):
    existing = load_csv_file(path)
    out = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    out.to_csv(path, index=False)
    return out


# ============================================================

# ============================================================
# V35.3 OPPORTUNITY DISCOVERY ENGINE
# ============================================================

def parse_symbol_text(text):
    if not text:
        return []
    cleaned = str(text).replace("\n", ",").replace(";", ",")
    out = []
    seen = set()
    for raw in cleaned.split(","):
        symbol = raw.strip().upper()
        if symbol and symbol not in seen:
            seen.add(symbol)
            out.append(symbol)
    return out


def clamp_score(value):
    return int(max(0, min(100, round(float(value or 0)))))


def opportunity_tier(score):
    if score >= 78:
        return "PRIME"
    if score >= 66:
        return "ACTIVE"
    if score >= 54:
        return "BENCH"
    return "IGNORE"


def liquidity_bucket(dollar_volume):
    if dollar_volume >= 2_000_000_000:
        return "Institutional"
    if dollar_volume >= 500_000_000:
        return "Liquid"
    if dollar_volume >= 100_000_000:
        return "Tradable"
    return "Thin"


def atr_percent(df):
    if df.empty or len(df) < 15:
        return 0.0
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = safe_num(tr.rolling(14).mean().iloc[-1])
    price = safe_num(close.iloc[-1])
    return round((atr / price) * 100, 2) if price > 0 else 0.0


def discovery_profile(symbol, spy_df, qqq_df):
    df = get_data(symbol, "3mo", "1d")
    if df.empty or len(df) < 30:
        return None

    close = safe_num(df["Close"].iloc[-1])
    if close <= 0:
        return None

    ma10 = safe_num(df["Close"].rolling(10).mean().iloc[-1], close)
    ma20 = safe_num(df["Close"].rolling(20).mean().iloc[-1], close)
    ma50 = safe_num(df["Close"].rolling(50).mean().iloc[-1], close)
    high20 = safe_num(df["High"].rolling(20).max().iloc[-2], close)
    low20 = safe_num(df["Low"].rolling(20).min().iloc[-2], close)
    avg_vol20 = safe_num(df["Volume"].rolling(20).mean().iloc[-1])
    vol_today = safe_num(df["Volume"].iloc[-1])
    rel_vol = vol_today / avg_vol20 if avg_vol20 > 0 else 0.0
    dollar_vol = vol_today * close
    gap = gap_percent(df)
    one_day = pct_change(df, 2)
    five_day = pct_change(df, 6)
    one_month = pct_change(df, 22)
    rs_spy = relative_strength(df, spy_df)
    rs_qqq = relative_strength(df, qqq_df)
    rs_blend = int(round((rs_spy * 0.55) + (rs_qqq * 0.45)))
    atr_pct = atr_percent(df)
    dist20 = ((close / ma20) - 1) * 100 if ma20 > 0 else 0.0
    near_high = abs((close / high20) - 1) * 100 <= 3 if high20 > 0 else False
    breakout = close > high20 if high20 > 0 else False
    above10 = close >= ma10
    above20 = close >= ma20
    above50 = close >= ma50
    trend_stack = above10 and above20 and above50 and ma10 >= ma20

    flow_score = 0
    flow_score += 25 if rel_vol >= 2.5 else 20 if rel_vol >= 1.7 else 14 if rel_vol >= 1.2 else 6 if rel_vol >= 0.9 else 0
    flow_score += 20 if rs_blend >= 78 else 16 if rs_blend >= 68 else 10 if rs_blend >= 58 else 0
    flow_score += 10 if dollar_vol >= 1_000_000_000 else 7 if dollar_vol >= 250_000_000 else 4 if dollar_vol >= 75_000_000 else 0

    structure_score = 0
    structure_score += 20 if breakout else 15 if near_high else 8 if above20 else 0
    structure_score += 14 if trend_stack else 9 if above20 and above50 else 4 if above20 else 0
    structure_score += 8 if -3 <= dist20 <= 10 else 4 if -6 <= dist20 <= 14 else -6 if dist20 > 18 else 0
    structure_score += 6 if close > low20 else 0

    movement_score = 0
    movement_score += 14 if five_day >= 5 else 10 if five_day >= 2 else 5 if five_day > 0 else -4 if five_day < -5 else 0
    movement_score += 12 if one_month >= 12 else 8 if one_month >= 6 else 3 if one_month > 0 else 0
    movement_score += 8 if gap >= 2 else 5 if gap >= 1 else -8 if gap <= -3 else 0
    movement_score += 8 if 2.0 <= atr_pct <= 7.5 else 4 if 1.2 <= atr_pct < 2.0 or 7.5 < atr_pct <= 10 else -4 if atr_pct > 12 else 0

    sector_bonus = 0
    sector = SECTOR.get(symbol, "Other")
    if sector in ["Semis", "AI Infra", "AI Software", "Software", "Momentum", "Fintech", "Crypto"]:
        sector_bonus += 4
    if symbol in ["SPY", "QQQ", "SMH", "SOXX", "XLK", "IWM", "ARKK"]:
        sector_bonus += 3

    raw_score = flow_score + structure_score + movement_score + sector_bonus
    score = clamp_score(raw_score)

    tags = []
    if rel_vol >= 1.5:
        tags.append("RVOL expansion")
    if rs_blend >= 68:
        tags.append("relative strength")
    if breakout:
        tags.append("20D breakout")
    elif near_high:
        tags.append("near 20D high")
    if trend_stack:
        tags.append("trend stack")
    if gap >= 1:
        tags.append("positive gap")
    if 2 <= atr_pct <= 8:
        tags.append("tradable volatility")
    if not tags:
        tags.append("not enough discovery evidence")

    primary_setup = "Relative Strength Breakout" if breakout or near_high else "VWAP/ORB Watch" if rel_vol >= 1.2 and rs_blend >= 58 else "Bench Watch"
    discovery_action = "Send to v35.2 permission engine" if score >= 66 else "Keep on bench unless intraday trigger appears" if score >= 54 else "Do not expand into active scan"

    return {
        "Ticker": symbol,
        "Sector": sector,
        "Discovery Tier": opportunity_tier(score),
        "Discovery Score": score,
        "Discovery Action": discovery_action,
        "Discovery Setup": primary_setup,
        "Discovery Reason": " + ".join(tags[:5]),
        "Price": round(close, 2),
        "1D %": one_day,
        "5D %": five_day,
        "1M %": one_month,
        "Gap %": gap,
        "Rel Vol": round(rel_vol, 2),
        "Dollar Volume": round(dollar_vol, 0),
        "Liquidity": liquidity_bucket(dollar_vol),
        "RS vs SPY": rs_spy,
        "RS vs QQQ": rs_qqq,
        "RS Blend": rs_blend,
        "ATR %": atr_pct,
        "Above 20MA": above20,
        "Above 50MA": above50,
        "Trend Stack": trend_stack,
        "Near 20D High": bool(near_high),
        "20D Breakout": bool(breakout),
        "Distance 20MA %": round(dist20, 2),
    }


@st.cache_data(ttl=180)
def build_opportunity_discovery(universe_symbols, manual_symbols, max_universe=60):
    symbols = []
    seen = set()
    for sym in list(manual_symbols or []) + list(universe_symbols or []):
        sym = str(sym).strip().upper()
        if sym and sym not in seen:
            seen.add(sym)
            symbols.append(sym)
    symbols = symbols[:int(max(1, max_universe))]

    spy_df = get_data("SPY", "3mo", "1d")
    qqq_df = get_data("QQQ", "3mo", "1d")
    rows = []
    for sym in symbols:
        profile = discovery_profile(sym, spy_df, qqq_df)
        if profile:
            profile["Already In Manual Scan"] = sym in set(manual_symbols or [])
            rows.append(profile)

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    out["Discovery Rank"] = out["Discovery Score"].rank(method="first", ascending=False).astype(int)
    return out.sort_values(["Discovery Score", "RS Blend", "Rel Vol", "Dollar Volume"], ascending=False).reset_index(drop=True)


def discovery_to_scan_symbols(manual_symbols, discovery_df, top_n=12, min_score=60, include_etfs=False):
    out = []
    seen = set()
    for sym in manual_symbols:
        sym = str(sym).strip().upper()
        if sym and sym not in seen:
            seen.add(sym)
            out.append(sym)

    if discovery_df is None or discovery_df.empty:
        return out

    candidates = discovery_df.copy()
    if not include_etfs:
        candidates = candidates[candidates["Sector"] != "ETF"]
    candidates = candidates[candidates["Discovery Score"] >= int(min_score)]
    candidates = candidates.head(int(max(0, top_n)))

    for sym in candidates["Ticker"].tolist():
        if sym not in seen:
            seen.add(sym)
            out.append(sym)
    return out


def opportunity_discovery_brief(discovery_df, expanded_symbols, manual_symbols, min_score):
    if discovery_df is None or discovery_df.empty:
        return "Opportunity Discovery Engine found no usable data. Keep the manual scan only."
    active = discovery_df[discovery_df["Discovery Score"] >= min_score]
    prime = discovery_df[discovery_df["Discovery Tier"] == "PRIME"]
    top = discovery_df.iloc[0]
    added = [s for s in expanded_symbols if s not in set(manual_symbols)]
    lines = []
    lines.append("OPPORTUNITY DISCOVERY ENGINE v35.4")
    lines.append(f"Top discovery: {top['Ticker']} / {top['Discovery Tier']} / score {top['Discovery Score']} / {top['Discovery Reason']}.")
    lines.append(f"Prime names: {len(prime)} | Active names above threshold: {len(active)} | Added to scan: {len(added)}.")
    lines.append(f"Added tickers: {', '.join(added[:20]) if added else 'None; manual universe only.'}")
    lines.append("Use this engine to expand the candidate pool; use v35.2 to approve or block real trades.")
    return "\n".join(lines)

# V35.2 DAILY PROFIT / TRADE PERMISSION ENGINE
# ============================================================

def monthly_target_math(month_start_equity, current_equity, monthly_target_pct, trading_days_left, base_risk_pct):
    start = max(float(month_start_equity or 0), 0.01)
    current = max(float(current_equity or start), 0.01)
    target_pct = max(float(monthly_target_pct or 0), 0.0)
    days_left = max(int(trading_days_left or 1), 1)
    risk_pct_local = max(float(base_risk_pct or 0), 0.0001)

    target_profit = start * (target_pct / 100.0)
    target_equity = start + target_profit
    pnl = current - start
    pnl_pct = (pnl / start) * 100.0
    remaining_profit = max(0.0, target_equity - current)
    needed_per_day = remaining_profit / days_left
    needed_daily_pct = (needed_per_day / current) * 100.0 if current > 0 else 0.0
    full_r_dollars = current * risk_pct_local
    current_r = pnl / full_r_dollars if full_r_dollars > 0 else 0.0
    required_r_remaining = remaining_profit / full_r_dollars if full_r_dollars > 0 else 0.0

    if pnl >= target_profit:
        status = "Ahead of monthly target"
    elif pnl_pct >= target_pct * 0.50:
        status = "On pace but still needs selectivity"
    elif needed_daily_pct <= 1.0:
        status = "Recoverable with normal discipline"
    elif needed_daily_pct <= 2.0:
        status = "Behind pace; do not increase risk"
    else:
        status = "Target pressure high; protect capital first"

    return {
        "Month Start Equity": round(start, 2),
        "Current Equity": round(current, 2),
        "Target Equity": round(target_equity, 2),
        "Monthly Target %": round(target_pct, 2),
        "Monthly P/L": round(pnl, 2),
        "Monthly P/L %": round(pnl_pct, 2),
        "Remaining Target $": round(remaining_profit, 2),
        "Trading Days Left": days_left,
        "Needed $ / Day": round(needed_per_day, 2),
        "Needed Daily %": round(needed_daily_pct, 2),
        "Full R $": round(full_r_dollars, 2),
        "Current Month R": round(current_r, 2),
        "Required R Remaining": round(required_r_remaining, 2),
        "Monthly Status": status,
    }


def v352_daily_mode(scan, market_light, daily_pnl, daily_trades_taken, max_daily_loss, max_real_trades, month_math):
    if scan is None or scan.empty:
        return "PROTECT", "No scan data available."

    best = scan.iloc[0]
    grade = str(best.get("Candidate Grade", "D"))
    above_vwap = bool(best.get("Above VWAP", False))
    or_status = str(best.get("OR Status", ""))
    score = safe_num(best.get("V35.1 Score", best.get("V35 Score", 0)))
    prof = safe_num(best.get("Professional Score", 0))
    rr = safe_num(best.get("Reward/Risk", 0))
    pnl = float(daily_pnl or 0)
    trades = int(daily_trades_taken or 0)
    max_loss = abs(float(max_daily_loss or 0))
    max_trades = max(int(max_real_trades or 1), 1)
    monthly_status = str(month_math.get("Monthly Status", ""))

    if max_loss > 0 and pnl <= -max_loss:
        return "PROTECT", f"Daily loss limit reached (${pnl:.2f} <= -${max_loss:.2f})."
    if trades >= max_trades:
        return "PROTECT", f"Real-trade count limit reached ({trades}/{max_trades})."
    if "pressure high" in monthly_status.lower():
        return "PROTECT", "Monthly target pressure is too high; do not solve it with larger intraday risk."
    if grade == "A" and market_light in ["GREEN", "YELLOW"] and above_vwap and or_status != "Below OR Low" and score >= 68 and rr >= 1.2:
        return "ATTACK", "Best candidate has A-grade structure, VWAP support, and acceptable reward/risk."
    if grade in ["A", "B"] and or_status != "Below OR Low" and prof >= 58:
        return "PROBE", "A/B candidate exists, but confirmation or tape quality is not strong enough for full risk."
    if grade in ["B", "C"] or score >= 50:
        return "TRAIN", "There is something to study or paper-test, but real-money edge is not clean enough."
    return "PROTECT", "No qualified setup; observation protects the monthly target."


def v352_permission_for_row(row, daily_mode_value, current_equity, risk_pct_base, max_order_value, max_total_risk):
    grade = str(row.get("Candidate Grade", "D"))
    score = safe_num(row.get("V35.1 Score", row.get("V35 Score", 0)))
    above_vwap = bool(row.get("Above VWAP", False))
    or_status = str(row.get("OR Status", ""))
    rr = safe_num(row.get("Reward/Risk", 0))
    ev = safe_num(row.get("EV / Share", 0))
    shares = safe_num(row.get("Shares", 0))
    dollar_risk = safe_num(row.get("Dollar Risk", 0))
    prof = safe_num(row.get("Professional Score", 0))
    mf = safe_num(row.get("Money Flow Score", 0))

    reasons = []
    real = False
    paper = False
    allowed_r_mult = 0.0

    if daily_mode_value == "PROTECT":
        reasons.append("daily mode blocks new real exposure")
    if grade not in ["A", "B"]:
        reasons.append(f"grade {grade} is not real-trade grade")
    if or_status == "Below OR Low":
        reasons.append("below opening-range low")
    if not above_vwap:
        reasons.append("not holding VWAP")
    if rr < 1.2:
        reasons.append(f"reward/risk below 1.20 ({rr:.2f})")
    if ev < -0.05:
        reasons.append(f"EV/share below floor ({ev:.2f})")
    if shares <= 0 or dollar_risk <= 0:
        reasons.append("no executable share/risk plan")
    if prof < 55:
        reasons.append(f"professional score too low ({prof:.1f})")
    if mf < 50:
        reasons.append(f"money flow too weak ({mf:.0f})")

    if daily_mode_value == "ATTACK" and grade == "A" and not reasons:
        real = True
        allowed_r_mult = 1.00
    elif daily_mode_value in ["ATTACK", "PROBE"] and grade in ["A", "B"] and or_status != "Below OR Low" and rr >= 1.2 and shares > 0 and dollar_risk > 0:
        real = True
        allowed_r_mult = 0.50 if grade == "B" or daily_mode_value == "PROBE" else 0.75

    if grade in ["A", "B", "C"] and daily_mode_value != "PROTECT":
        paper = True
    if daily_mode_value == "TRAIN" and grade in ["B", "C"]:
        paper = True

    raw_allowed = float(current_equity or 0) * float(risk_pct_base or 0) * allowed_r_mult
    allowed_risk = min(raw_allowed, float(max_total_risk or raw_allowed or 0))
    if safe_num(row.get("Position $", 0)) > float(max_order_value or 10**9):
        real = False
        reasons.append("planned position exceeds order-value cap")

    permission = "REAL OK" if real else ("PAPER ONLY" if paper else "BLOCKED")
    if real and allowed_r_mult < 1:
        permission = "REAL REDUCED"
    if not reasons and real:
        reason_text = "real trade may be reviewed after live chart trigger confirms"
    elif not reasons and paper:
        reason_text = "paper test allowed; real entry still needs higher grade or confirmation"
    else:
        reason_text = "; ".join(reasons[:5])

    return pd.Series({
        "V35.2 Permission": permission,
        "V35.2 Permission Reason": reason_text,
        "Allowed R Mult": round(allowed_r_mult, 2),
        "Allowed Risk $": round(max(0.0, allowed_risk), 2),
    })


def add_v352_profit_engine(scan, daily_mode_value, current_equity, risk_pct_base, max_order_value, max_total_risk):
    scan = scan.copy()
    perms = scan.apply(
        lambda r: v352_permission_for_row(r, daily_mode_value, current_equity, risk_pct_base, max_order_value, max_total_risk),
        axis=1,
    )
    scan = pd.concat([scan, perms], axis=1)
    scan["V35.2 Priority Score"] = (
        safe_num(1) * 0 +
        scan["V35.1 Score"] * 0.40 +
        scan["Professional Score"] * 0.20 +
        scan["Money Flow Score"] * 0.15 +
        scan["RS Score"] * 0.10 +
        scan["ORB Status Score"] * 0.10 +
        scan["VWAP Confirm Score"] * 0.05
    ).round(1)
    perm_rank = {"REAL OK": 4, "REAL REDUCED": 3, "PAPER ONLY": 2, "BLOCKED": 1}
    scan["V35.2 Rank"] = scan["V35.2 Permission"].map(perm_rank).fillna(0) * 1000 + scan["V35.2 Priority Score"]
    return scan.sort_values(["V35.2 Rank", "V35.1 Score", "Professional Score"], ascending=False).reset_index(drop=True)


def v352_operating_brief(scan, daily_mode_value, daily_mode_reason, month_math, daily_pnl, daily_trades_taken, max_daily_loss, max_real_trades):
    lines = []
    lines.append("V35.2 DAILY PROFIT ENGINE")
    lines.append(f"Mode: {daily_mode_value} — {daily_mode_reason}")
    lines.append(f"Monthly: {month_math['Monthly P/L']} ({month_math['Monthly P/L %']}%) toward {month_math['Monthly Target %']}% target; remaining ${month_math['Remaining Target $']} with {month_math['Trading Days Left']} trading days left.")
    lines.append(f"Needed pace: ${month_math['Needed $ / Day']}/day or {month_math['Needed Daily %']}%/day; required remaining R: {month_math['Required R Remaining']}R.")
    lines.append(f"Today: P/L ${float(daily_pnl or 0):.2f}; real trades {int(daily_trades_taken or 0)}/{int(max_real_trades or 1)}; daily loss stop ${abs(float(max_daily_loss or 0)):.2f}.")

    real = scan[scan["V35.2 Permission"].isin(["REAL OK", "REAL REDUCED"])] if "V35.2 Permission" in scan.columns else pd.DataFrame()
    paper = scan[scan["V35.2 Permission"].eq("PAPER ONLY")] if "V35.2 Permission" in scan.columns else pd.DataFrame()

    if not real.empty:
        top = real.iloc[0]
        lines.append(f"Primary real-money review: {top['Ticker']} / {top['V35.2 Permission']} / Grade {top['Candidate Grade']} / risk cap ${top['Allowed Risk $']}.")
        lines.append(f"Required trigger: {top.get('Action Plan', '')}")
    elif not paper.empty:
        top = paper.iloc[0]
        lines.append(f"No real-money candidate. Paper focus: {top['Ticker']} / Grade {top['Candidate Grade']} / reason: {top['V35.2 Permission Reason']}.")
    else:
        top = scan.iloc[0]
        lines.append(f"No trade deployment. Top blocked symbol: {top['Ticker']} / {top.get('V35.2 Permission Reason', top.get('Rejection Reason', ''))}.")

    lines.append("Rule stack: real money requires permission + live trigger + manual Robinhood confirmation; Alpaca is for mirrors or training, not for bypassing the block.")
    return "\n".join(lines)

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
    candidates = scan[(scan["Professional Verdict"].isin(["TRADE CANDIDATE", "WAIT FOR TRIGGER"])) | (scan.get("Candidate Grade", pd.Series(index=scan.index, dtype=str)).isin(["A", "B"]))]
    no_trade = scan[~scan["Signal"].isin(["TRADE", "SMALL TRADE"])]

    return {
        "timestamp": ct_now().strftime("%Y-%m-%d %H:%M:%S"),
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
    lines.append("TRADER BRIEFING v35")
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
        lines.append(f"V35 grade: {candidate.get('Candidate Grade', 'N/A')} / score {candidate.get('V35 Score', 'N/A')} / trigger {candidate.get('V35 Trigger', '')}")
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
        lines.append("Execution: use v35 ladder plan before placing any manual orders.")
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
    lines.append("DEON TRADER DASHBOARD v35 - FULL DECISION PACKET")
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
            f"{i}. {row['Ticker']} | Grade {row.get('Candidate Grade', 'N/A')} | {row['Professional Verdict']} | {row['Signal']} | {row['Tier']} {row['Best Setup']} | "
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

    fig.update_layout(
        height=550,
        xaxis_rangeslider_visible=False,
        paper_bgcolor="rgba(248,250,252,0)",
        plot_bgcolor="rgba(248,239,224,.92)",
        font=dict(color="#061622", family="Inter, sans-serif"),
        margin=dict(l=20, r=20, t=35, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(gridcolor="rgba(15,118,110,.10)", zerolinecolor="rgba(15,118,110,.12)"),
        yaxis=dict(gridcolor="rgba(15,118,110,.10)", zerolinecolor="rgba(15,118,110,.12)"),
    )
    return fig



def ui_escape(value):
    return html.escape(str(value))


def permission_pill_class(permission):
    p = str(permission).upper()
    if "REAL OK" in p:
        return "ok"
    if "REAL REDUCED" in p:
        return "warn"
    if "PAPER" in p:
        return "paper"
    return "block"


def render_v353_opportunity_tiles(scan_df):
    if scan_df is None or scan_df.empty:
        return ""
    cards = []
    for rank, (_, row) in enumerate(scan_df.head(3).iterrows(), 1):
        ticker = ui_escape(row.get("Ticker", ""))
        sector = ui_escape(row.get("Sector", ""))
        permission = ui_escape(row.get("V35.2 Permission", row.get("Professional Verdict", "")))
        grade = ui_escape(row.get("Candidate Grade", ""))
        score = ui_escape(row.get("V35.2 Priority Score", row.get("Professional Score", "")))
        setup = ui_escape(row.get("Best Setup", ""))
        trigger = ui_escape(row.get("Action Plan", row.get("V35 Trigger", row.get("Reason", ""))))
        risk = ui_escape(row.get("Allowed Risk $", row.get("Dollar Risk", "")))
        shares = ui_escape(row.get("Shares", ""))
        pill = permission_pill_class(permission)
        card = (
            f'<div class="v35-opportunity-tile rank-{rank}">'
            f'<div class="v35-tile-rank">#{rank}</div>'
            f'<div class="v35-tile-ticker">{ticker}</div>'
            f'<div class="v35-tile-meta">{sector} &middot; {setup}</div>'
            f'<div class="v35-tile-row">'
            f'<span class="v35-mini-pill {pill}">{permission}</span>'
            f'<span class="v35-mini-pill">Grade {grade}</span>'
            f'<span class="v35-mini-pill gold">Score {score}</span>'
            f'<span class="v35-mini-pill">Risk ${risk}</span>'
            f'<span class="v35-mini-pill">Shares {shares}</span>'
            f'</div>'
            f'<div class="v35-tile-trigger">{trigger}</div>'
            f'</div>'
        )
        cards.append(card)
    return '<div class="v35-tile-grid">' + ''.join(cards) + '</div>'

def render_v353_command_strip(daily_mode_value, month_math, scan_df, opportunity_df):
    best_permission = "No real candidate"
    best_ticker = "None"
    best_action = "No active permission yet"
    try:
        eligible = scan_df[scan_df.get("V35.2 Permission", "").isin(["REAL OK", "REAL REDUCED"])]
        if not eligible.empty:
            r = eligible.iloc[0]
            best_ticker = r.get("Ticker", "None")
            best_permission = r.get("V35.2 Permission", "")
            best_action = r.get("Action Plan", r.get("V35 Trigger", "Verify chart trigger"))
    except Exception:
        pass
    discovery_count = 0 if opportunity_df is None or opportunity_df.empty else len(opportunity_df)
    return f"""
    <div class="v35-command-strip">
      <div class="v35-command-panel dark">
        <div class="v35-command-label">Primary Decision</div>
        <div class="v35-command-main">{ui_escape(daily_mode_value)} · {ui_escape(best_ticker)}</div>
        <div class="v35-command-note">{ui_escape(best_permission)} — {ui_escape(best_action)}</div>
      </div>
      <div class="v35-command-panel gold">
        <div class="v35-command-label">20% Target Lens</div>
        <div class="v35-command-main">{ui_escape(month_math.get('Monthly Status',''))}</div>
        <div class="v35-command-note">Needed/day ${ui_escape(month_math.get('Needed $ / Day',''))} · remaining target ${ui_escape(month_math.get('Remaining Target $',''))}</div>
      </div>
      <div class="v35-command-panel copper">
        <div class="v35-command-label">Discovery Breadth</div>
        <div class="v35-command-main">{discovery_count} names ranked</div>
        <div class="v35-command-note">The wide net feeds candidates into the same v35.2 real-money gate.</div>
      </div>
    </div>
    """



# ============================================================
# V35.5 ORGANIZED WORKFLOW UI HELPERS
# ============================================================

def v355_safe_top_row(scan):
    try:
        if scan is not None and not scan.empty:
            return scan.iloc[0]
    except Exception:
        pass
    return pd.Series(dtype="object")


def v355_next_action_sentence(scan, daily_mode_value, month_math):
    row = v355_safe_top_row(scan)
    if row.empty:
        return "OBSERVE: no valid scan rows loaded yet. Keep Robinhood blocked until candidates appear."

    ticker = row.get("Ticker", "N/A")
    permission = str(row.get("V35.2 Permission", row.get("Professional Verdict", "WAIT")))
    grade = row.get("Candidate Grade", "N/A")
    setup = row.get("Best Setup", "setup")
    trigger = row.get("V35 Trigger", row.get("Action Plan", "wait for confirmed trigger"))
    price = safe_num(row.get("Price", 0))
    stop = safe_num(row.get("Stop", 0))
    target = safe_num(row.get("Target 1", 0))
    risk = safe_num(row.get("Allowed Risk $", row.get("Dollar Risk", 0)))

    if "REAL OK" in permission:
        verb = "TRADE REVIEW"
        route = "Robinhood review allowed; mirror in Alpaca."
    elif "REAL REDUCED" in permission:
        verb = "SMALL PROBE"
        route = "Robinhood reduced-risk only; Alpaca mirror preferred."
    elif "PAPER" in permission:
        verb = "PAPER ONLY"
        route = "Keep Robinhood blocked; test the idea in Alpaca."
    elif "BLOCK" in permission:
        verb = "BLOCKED"
        route = "No real trade; use rejection audit before reconsidering."
    else:
        verb = "WAIT"
        route = "No real-money action until trigger and permission improve."

    px = f"entry ref ${price:.2f}" if price > 0 else "entry ref unavailable"
    stp = f"stop ${stop:.2f}" if stop > 0 else "stop unavailable"
    tgt = f"target ${target:.2f}" if target > 0 else "target unavailable"
    return f"{verb}: {ticker} Grade {grade} {setup}. {trigger}. Use {px}, {stp}, {tgt}; allowed risk about ${risk:,.2f}. {route} Monthly status: {month_math.get('Monthly Status', 'Unknown')}."


def render_v355_workflow_nav():
    return """
    <div class="v355-workflow-shell">
      <div class="v355-workflow-title">Workflow Map</div>
      <div class="v355-workflow-subtitle">Read left to right. The dashboard is organized around the actual trading sequence, not around internal features.</div>
      <div class="v355-workflow-grid">
        <div class="v355-step-card"><div class="v355-step-number">Step 01</div><div class="v355-step-title">Command</div><div class="v355-step-detail">Market mode, 20% pace, risk budget, and the single next action.</div></div>
        <div class="v355-step-card"><div class="v355-step-number">Step 02</div><div class="v355-step-title">Discover</div><div class="v355-step-detail">Find fresh movers before they enter the normal watchlist.</div></div>
        <div class="v355-step-card"><div class="v355-step-number">Step 03</div><div class="v355-step-title">Decide</div><div class="v355-step-detail">Grade, permission, trigger, rejection reason, and expected risk.</div></div>
        <div class="v355-step-card"><div class="v355-step-number">Step 04</div><div class="v355-step-title">Execute</div><div class="v355-step-detail">Manual Robinhood plan, Alpaca mirror, ladder, stop, scale-outs.</div></div>
        <div class="v355-step-card"><div class="v355-step-number">Step 05</div><div class="v355-step-title">Review</div><div class="v355-step-detail">Learning log, scan history, setup results, and process mistakes.</div></div>
      </div>
    </div>
    """


def render_v355_decision_band(scan, daily_mode_value, month_math):
    row = v355_safe_top_row(scan)
    ticker = row.get("Ticker", "None") if not row.empty else "None"
    grade = row.get("Candidate Grade", "-") if not row.empty else "-"
    setup = row.get("Best Setup", "No setup") if not row.empty else "No setup"
    permission = row.get("V35.2 Permission", row.get("Professional Verdict", "Unknown")) if not row.empty else "Unknown"
    score = row.get("V35.2 Priority Score", row.get("V35.1 Score", row.get("V35 Score", 0))) if not row.empty else 0
    needed = safe_num(month_math.get("Needed $ / Day", 0)) if isinstance(month_math, dict) else 0
    reqr = month_math.get("Required R Remaining", "-") if isinstance(month_math, dict) else "-"
    monthly_status = month_math.get("Monthly Status", "Unknown") if isinstance(month_math, dict) else "Unknown"
    return f"""
    <div class="v355-decision-band">
      <div class="v355-decision-card gold">
        <div class="v355-decision-label">Best Opportunity</div>
        <div class="v355-decision-value">{ticker} · Grade {grade}</div>
        <div class="v355-decision-sub">{setup} · priority {score}</div>
      </div>
      <div class="v355-decision-card green">
        <div class="v355-decision-label">Permission</div>
        <div class="v355-decision-value">{permission}</div>
        <div class="v355-decision-sub">Real money must pass this gate before execution.</div>
      </div>
      <div class="v355-decision-card copper">
        <div class="v355-decision-label">Market Mode</div>
        <div class="v355-decision-value">{daily_mode_value}</div>
        <div class="v355-decision-sub">Determines full risk, reduced risk, paper only, or protect mode.</div>
      </div>
      <div class="v355-decision-card gold">
        <div class="v355-decision-label">20% Pace</div>
        <div class="v355-decision-value">{monthly_status}</div>
        <div class="v355-decision-sub">Needed/day ${needed:,.2f} · R left {reqr}</div>
      </div>
    </div>
    """


def render_v355_next_action(scan, daily_mode_value, month_math):
    sentence = v355_next_action_sentence(scan, daily_mode_value, month_math)
    return f"""
    <div class="v355-next-action">
      <div class="label">Next Action</div>
      <div class="sentence">{sentence}</div>
    </div>
    """


# ============================================================
# APP
# ============================================================

st.title("Deon's Trader Dashboard v35.4 — Warm Opportunity Command UI")

st.markdown("""
<div class="v35-hero v35-hero-boost">
  <div class="v35-kicker">LIVE TRADE DESK · CENTRAL TIME · V35.4</div>
  <h1>Opportunity Discovery Command Center</h1>
  <p>Broader discovery universe → v35.2 permission engine → Robinhood real-trade review → Alpaca paper mirror. The warmer color system separates opportunity, action, permission, and risk: gold marks top opportunity, copper marks pending action, emerald marks confirmed permission, and navy keeps the command-center structure grounded.</p>
  <div class="v35-hero-row">
    <span class="v35-chip">⚡ Discovery Engine</span>
    <span class="v35-chip">🧭 Daily Profit Mode</span>
    <span class="v35-chip">🛡️ Real-Money Gate</span>
    <span class="v35-chip">📊 Rejection Audit</span>
    <span class="v35-chip">🎯 Robinhood / Alpaca Mirror</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.caption(f"Last updated CT: {ct_now().strftime('%Y-%m-%d %H:%M:%S')}")

st.sidebar.header("Settings")
st.sidebar.markdown("**Warm color legend:** Gold = opportunity, Copper = pending action, Emerald = confirmed permission, Red = blocked risk.")
developer_mode = st.sidebar.checkbox("Developer Mode / Strategy Lab", value=False, help="Turn on only when you want ChatGPT packets, raw diagnostics, screenshot support, and system-development sections.")
if not developer_mode:
    st.sidebar.caption("Trader Mode is active: internal packets and diagnostics are hidden.")
else:
    st.sidebar.warning("Developer Mode is active: diagnostics and ChatGPT review material are visible.")
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

st.sidebar.subheader("V35.2 Profit Engine")
month_start_equity = st.sidebar.number_input("Month start equity", min_value=0.01, value=float(cash), step=25.0)
current_real_equity = st.sidebar.number_input("Current Robinhood equity", min_value=0.01, value=float(cash), step=25.0)
monthly_target_pct = st.sidebar.number_input("Monthly target %", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
trading_days_left = st.sidebar.number_input("Trading days left this month", min_value=1, max_value=23, value=20, step=1)
daily_pnl_input = st.sidebar.number_input("Today's realized P/L", value=0.0, step=5.0)
daily_trades_taken = st.sidebar.number_input("Real trades taken today", min_value=0, max_value=20, value=0, step=1)
max_real_trades_per_day = st.sidebar.number_input("Max real trades/day", min_value=1, max_value=10, value=2, step=1)
max_daily_loss_dollars = st.sidebar.number_input("Max daily real loss $", min_value=0.0, value=max(10.0, float(cash) * risk_pct), step=5.0)
st.sidebar.caption("This layer decides ATTACK / PROBE / TRAIN / PROTECT before any Robinhood action.")

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

st.sidebar.subheader("Daily Trader Mode")
daily_mode = st.sidebar.checkbox("Enable Daily Trader Mode", value=True)
candidate_goal = st.sidebar.slider("Daily candidate goal", min_value=3, max_value=20, value=8, step=1)
frequency_bias = st.sidebar.slider("Frequency vs selectivity", min_value=0, max_value=100, value=65, step=5)
allow_short_watch = st.sidebar.checkbox("Show short-bias watchlist", value=True)
st.sidebar.caption("Higher frequency increases candidates. Risk rules still control sizing and broker submission.")


st.sidebar.subheader("Opportunity Discovery Engine")
opportunity_discovery_enabled = st.sidebar.checkbox("Enable Opportunity Discovery", value=True)
opportunity_universe_text = st.sidebar.text_area(
    "Discovery Universe",
    ",".join(OPPORTUNITY_DISCOVERY_UNIVERSE),
    height=170,
    help="The engine ranks this broader universe, then injects the strongest names into the v35.2 scan."
)
opportunity_max_universe = st.sidebar.slider("Discovery symbols to evaluate", min_value=20, max_value=120, value=70, step=5)
opportunity_add_top_n = st.sidebar.slider("Add top discovery names to active scan", min_value=0, max_value=30, value=12, step=1)
opportunity_min_score = st.sidebar.slider("Minimum discovery score to add", min_value=40, max_value=90, value=62, step=1)
opportunity_include_etfs = st.sidebar.checkbox("Allow ETFs in expanded scan", value=False)
st.sidebar.caption("Discovery expands the scan; it does not bypass v35.2 real-money permission rules.")

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

manual_symbols = [x.strip().upper() for x in scan_text.split(",") if x.strip()]
discovery_universe_symbols = parse_symbol_text(opportunity_universe_text)

if opportunity_discovery_enabled:
    with st.spinner("Running Opportunity Discovery Engine across the broader universe..."):
        opportunity_df = build_opportunity_discovery(discovery_universe_symbols, manual_symbols, opportunity_max_universe)
    symbols = discovery_to_scan_symbols(
        manual_symbols,
        opportunity_df,
        top_n=opportunity_add_top_n,
        min_score=opportunity_min_score,
        include_etfs=opportunity_include_etfs,
    )
else:
    opportunity_df = pd.DataFrame()
    symbols = manual_symbols

opportunity_brief = opportunity_discovery_brief(opportunity_df, symbols, manual_symbols, opportunity_min_score)

with st.spinner("Scanning expanded technicals, news, sector rotation, earnings timing, premarket activity, and learning data..."):
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
    scan = add_v35_scores(scan)
    scan = add_v351_decision_audit(scan)

month_math = monthly_target_math(month_start_equity, current_real_equity, monthly_target_pct, trading_days_left, risk_pct)
daily_mode_value, daily_mode_reason = v352_daily_mode(scan, light, daily_pnl_input, daily_trades_taken, max_daily_loss_dollars, max_real_trades_per_day, month_math)
scan = add_v352_profit_engine(scan, daily_mode_value, current_real_equity, risk_pct, broker_max_order_value, broker_max_total_risk)
v352_brief = v352_operating_brief(scan, daily_mode_value, daily_mode_reason, month_math, daily_pnl_input, daily_trades_taken, max_daily_loss_dollars, max_real_trades_per_day)

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
# TRADE DESK COCKPIT
# ============================================================

mode_css = f"v35-mode-{daily_mode_value}" if daily_mode_value in ["ATTACK", "PROBE", "TRAIN", "PROTECT"] else ""
try:
    top_disc_ticker = opportunity_df.iloc[0]["Ticker"] if opportunity_df is not None and not opportunity_df.empty else "None"
    top_disc_score = int(opportunity_df.iloc[0]["Discovery Score"]) if opportunity_df is not None and not opportunity_df.empty else 0
except Exception:
    top_disc_ticker, top_disc_score = "None", 0
try:
    top_real = scan[scan.get("V35.2 Permission", "") .isin(["REAL OK", "REAL REDUCED"])].iloc[0]
    top_real_ticker = top_real["Ticker"]
    top_real_permission = top_real["V35.2 Permission"]
except Exception:
    top_real_ticker, top_real_permission = "None", "No real trade"

st.markdown(f"""
<div class="v35-trade-desk-grid">
  <div class="v35-status-card {mode_css}">
    <div class="v35-card-label">Daily Mode</div>
    <div class="v35-card-value">{daily_mode_value}</div>
    <div class="v35-card-sub">{daily_mode_reason}</div>
  </div>
  <div class="v35-status-card">
    <div class="v35-card-label">Monthly Pace</div>
    <div class="v35-card-value">{month_math['Monthly P/L %']}%</div>
    <div class="v35-card-sub">Need ${month_math['Needed $ / Day']:,.2f}/day · {month_math['Required R Remaining']}R left</div>
  </div>
  <div class="v35-status-card">
    <div class="v35-card-label">Best Discovery</div>
    <div class="v35-card-value">{top_disc_ticker}</div>
    <div class="v35-card-sub">Discovery score {top_disc_score} · Injected universe filter active</div>
  </div>
  <div class="v35-status-card">
    <div class="v35-card-label">Real-Money Gate</div>
    <div class="v35-card-value">{top_real_ticker}</div>
    <div class="v35-card-sub">{top_real_permission} · v35.2 permission remains final</div>
  </div>
</div>
<div class="v35-banner">
  <div class="v35-banner-title">Color System Upgrade</div>
  <div class="v35-banner-text">Dark navy remains the command structure. Teal marks information, emerald marks confirmation, gold marks the highest opportunity or target progress, copper marks pending action, and red remains reserved for risk blocks.</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='v355-section-band'><span>01</span>Today's Trading Desk</div>", unsafe_allow_html=True)
st.markdown(render_v355_workflow_nav(), unsafe_allow_html=True)
st.markdown(render_v355_decision_band(scan, daily_mode_value, month_math), unsafe_allow_html=True)
st.markdown(render_v355_next_action(scan, daily_mode_value, month_math), unsafe_allow_html=True)
st.markdown(render_v353_command_strip(daily_mode_value, month_math, scan, opportunity_df), unsafe_allow_html=True)

st.markdown(f'''
<div class="v35-target-gold">
  <div class="label">20% Monthly Target Mode</div>
  <div class="main">{month_math['Monthly Status']} · {month_math['Monthly P/L %']}% month-to-date</div>
  <div class="sub">Remaining target ${month_math['Remaining Target $']:,.2f} · Needed/day ${month_math['Needed $ / Day']:,.2f} · Required R left {month_math['Required R Remaining']}R</div>
</div>
''', unsafe_allow_html=True)

st.markdown('<div class="v35-divider-title">Top actionable tiles</div>', unsafe_allow_html=True)
st.markdown(render_v353_opportunity_tiles(scan), unsafe_allow_html=True)
if developer_mode:
    with st.expander('Strategy Development · UI Diagnostics', expanded=False):
        st.caption('Rendered tile HTML is shown only here for troubleshooting. It should never appear in Trader Mode.')
        st.code(render_v353_opportunity_tiles(scan), language='html')

st.markdown("""
<div class="v35-lane-grid">
  <div class="v35-lane-card">
    <div class="v35-lane-title">Lane 1 · Discovery</div>
    <div class="v35-lane-value">Find the move</div>
    <div class="v35-lane-detail">Relative strength, volume expansion, trend structure, liquidity, gap quality, and high proximity decide what enters the active scan.</div>
  </div>
  <div class="v35-lane-card">
    <div class="v35-lane-title">Lane 2 · Permission</div>
    <div class="v35-lane-value">Protect real money</div>
    <div class="v35-lane-detail">v35.2 still controls Robinhood eligibility with daily mode, monthly pace, reward/risk, EV, VWAP, OR status, and risk limits.</div>
  </div>
  <div class="v35-lane-card">
    <div class="v35-lane-title">Lane 3 · Execution</div>
    <div class="v35-lane-value">Scale with intent</div>
    <div class="v35-lane-detail">Execution ladders and Alpaca paper mirrors exist after permission is granted; rejected names stay in the audit trail.</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# 10/10 COMMAND CENTER
# ============================================================

if developer_mode:
    st.markdown('<div class="v357-mode-note"><span>Developer Mode:</span> Strategy Development packets and diagnostics are visible for screenshot/review work.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="v357-mode-note"><span>Trader Mode:</span> internal ChatGPT packets, raw markup, and diagnostics are hidden. Use the trading workflow only.</div>', unsafe_allow_html=True)

st.markdown('<div class="v355-section-band"><span>02</span>Live Trading Summary</div>', unsafe_allow_html=True)
st.markdown("""
<div class="v356-clean-note">
  <div class="title">Clean trading view enabled</div>
  <div class="body">ChatGPT packets, raw decision text, and development diagnostics are now tucked into Strategy Development. Open that area only when you want to send screenshots or ask for system review.</div>
</div>
""", unsafe_allow_html=True)
st.markdown(f"""
<div class="v356-mini-grid">
  <div class="v356-mini-card gold"><div class="k">Primary Screen</div><div class="v">Trading Desk</div></div>
  <div class="v356-mini-card copper"><div class="k">Research Area</div><div class="v">Strategy Development</div></div>
  <div class="v356-mini-card"><div class="k">Packets Available</div><div class="v">{len(auto_news_hits)} news · {len(manual_news_hits)} manual</div></div>
</div>
""", unsafe_allow_html=True)

if developer_mode:
    with st.expander("Strategy Development · ChatGPT review packets and screenshot support", expanded=False):
        st.markdown('<span class="v356-lab-badge">Open this only when sharing screenshots or asking for deeper review</span>', unsafe_allow_html=True)
        st.caption("This section is for ChatGPT/development review, not live trade execution. It keeps the main trading screen clean.")
        st.text_area("Trader Briefing for ChatGPT", briefing, height=430)
        c1, c2, c3 = st.columns(3)
        c1.download_button("Download Trader Briefing TXT", data=briefing.encode("utf-8"), file_name="trader_briefing_v35_8.txt", mime="text/plain")
        c2.download_button("Download Full Packet TXT", data=full_packet.encode("utf-8"), file_name="full_decision_packet_v35_8.txt", mime="text/plain")
        c3.download_button("Download Top 10 CSV", data=df_csv(scan.head(10)), file_name="top10_v35_8.csv", mime="text/csv")

st.header("Daily Profit Engine")
mode_col1, mode_col2, mode_col3, mode_col4 = st.columns(4)
mode_col1.metric("Mode", daily_mode_value)
mode_col2.metric("Monthly P/L", f"${month_math['Monthly P/L']:,.2f}", f"{month_math['Monthly P/L %']}%")
mode_col3.metric("Needed / Day", f"${month_math['Needed $ / Day']:,.2f}", f"{month_math['Needed Daily %']}%")
mode_col4.metric("Required R Left", f"{month_math['Required R Remaining']}R")
if daily_mode_value == "ATTACK":
    st.success(daily_mode_reason)
elif daily_mode_value == "PROBE":
    st.warning(daily_mode_reason)
elif daily_mode_value == "TRAIN":
    st.info(daily_mode_reason)
else:
    st.error(daily_mode_reason)
if developer_mode:
    with st.expander("Strategy Development · V35.2 operating brief", expanded=False):
        st.text_area("V35.2 Operating Brief", v352_brief, height=220)

st.markdown('<div class="v355-section-band"><span>03</span>Discovery · Opportunity Intake</div>', unsafe_allow_html=True)
st.header("V35.3 — Opportunity Discovery Engine")
od1, od2, od3, od4 = st.columns(4)
if opportunity_df is not None and not opportunity_df.empty:
    added_count = len([s for s in symbols if s not in set(manual_symbols)])
    od1.metric("Discovery Names", len(opportunity_df))
    od2.metric("Added to Scan", added_count)
    od3.metric("Top Discovery", opportunity_df.iloc[0]["Ticker"])
    od4.metric("Top Score", int(opportunity_df.iloc[0]["Discovery Score"]))
    if developer_mode:
        with st.expander("Strategy Development · Opportunity discovery notes", expanded=False):
            st.text_area("Opportunity Brief", opportunity_brief, height=120)
else:
    od1.metric("Discovery Names", 0)
    od2.metric("Added to Scan", 0)
    od3.metric("Top Discovery", "None")
    od4.metric("Top Score", 0)
    st.info("Opportunity Discovery is disabled or no data was available. Manual scan is still active.")

st.header("Today's Action Plan")
action_plan_text = v351_today_action_plan(scan, light, market_score, market_reason)
st.info(action_plan_text.split("\n")[0] if action_plan_text else "Action plan unavailable.")
if developer_mode:
    with st.expander("Strategy Development · Full action-plan text", expanded=False):
        st.text_area("Action Plan", action_plan_text, height=190)
if st.button("Save Current Scan Snapshot"):
    hist = append_csv_row(SCAN_HISTORY_FILE, v351_scan_history_row(scan, light, market_score, market_reason))
    st.success(f"Saved scan snapshot. History rows: {len(hist)}")

st.markdown('<div class="v355-section-band"><span>04</span>Decision · Trade Permission</div>', unsafe_allow_html=True)
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

st.markdown('<div class="v355-section-band"><span>05</span>Execution · Manual Plan</div>', unsafe_allow_html=True)
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
    if developer_mode:
        with st.expander("Strategy Development · Execution packet for ChatGPT", expanded=False):
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
        "Ticker", "Sector", "Candidate Grade", "V35 Score", "Professional Verdict", "Signal", "Tier", "Best Setup",
        "Professional Score", "Composite Score", "Earnings Score", "Premarket Score", "Learning Score", "Sector Rotation Score", "Total Opportunity Score", "Catalyst Score", "Catalyst Type", "External Score", "External Source", "Money Flow Score", "Best Score", "Reason", "Price", "Stop",
        "Target 1", "Shares", "Position $", "Dollar Risk", "Chart Needed"
    ]],
    use_container_width=True,
)

# ============================================================
# TABS
# ============================================================

st.markdown('<div class="v355-section-band"><span>06</span>Workflow Tabs · Trader First, Lab Second</div>', unsafe_allow_html=True)

tabs = st.tabs([
    "Trading Desk · Rankings",
    "Trading Desk · Daily Board",
    "Decision · Candidate Grades",
    "Decision · Trade Plan",
    "Strategy Development · Packets",
    "Discovery · Sector Flow",
    "Strategy Development · Engine Scores",
    "Decision · Watch / No Trade",
    "Trading Desk · Participation",
    "Discovery · Catalysts",
    "Discovery · Multi-Source",
    "Discovery · Events",
    "Review · Learning Log",
    "Execution · Ladder Plan",
    "Execution · Alpaca Broker",
    "Execution · Robinhood Mirror",
    "Decision · Charts",
    "Trading Desk · Action Plan",
    "Strategy Development · Rejection Audit",
    "Review · Scan History",
    "Discovery · Opportunity Engine",
    "Trading Desk · Profit Engine",
])

with tabs[0]:
    st.header("Ranked Money Flow Board")
    ranked = scan.head(25).copy()
    ranked.insert(0, "Rank", range(1, len(ranked) + 1))
    st.dataframe(
        ranked[[
            "Rank", "Ticker", "Sector", "Candidate Grade", "V35 Score", "Professional Verdict", "Signal", "Tier", "Best Setup",
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
    st.header("Daily Trader")
    st.write("Frequency-oriented opportunity board using v35 grades, OR/VWAP triggers, and hard risk controls.")
    daily_board = v34_build_daily_opportunity_board(scan, candidate_goal=candidate_goal, frequency_bias=frequency_bias)
    if not daily_board.empty:
        extra_cols = ["Candidate Grade", "V35 Score", "V35 Trigger"]
        show = daily_board.merge(scan[["Ticker"] + extra_cols], on="Ticker", how="left") if all(c in scan.columns for c in extra_cols) else daily_board
        st.dataframe(show, use_container_width=True, height=520)
    else:
        st.warning("No daily trader candidates generated.")
    st.caption("Grade A/B names are eligible for real-trade review; C names are watchlist only; D names are ignored.")

with tabs[2]:
    st.header("V35 Candidate Board")
    st.write("A = actionable after trigger, B = close candidate, C = watchlist, D = ignore. This fixes the v34 all-or-nothing participation problem.")
    st.dataframe(v35_candidate_board(scan, candidate_goal), use_container_width=True, height=520)
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Grade A", int((scan["Candidate Grade"] == "A").sum()))
    g2.metric("Grade B", int((scan["Candidate Grade"] == "B").sum()))
    g3.metric("Grade C", int((scan["Candidate Grade"] == "C").sum()))
    g4.metric("Grade D", int((scan["Candidate Grade"] == "D").sum()))
    st.subheader("Trigger Checklist")
    for _, r in scan[scan["Candidate Grade"].isin(["A", "B", "C"])].head(8).iterrows():
        st.write(f"**{r['Ticker']} — Grade {r['Candidate Grade']}**: {r['V35 Trigger']}")

with tabs[3]:
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
    m2.metric("Grade", row.get("Candidate Grade", "N/A"))
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

with tabs[4]:
    st.header("Strategy Development Packets")
    st.info("Use this area only when you want ChatGPT to audit the system or when you are sending screenshots. It is intentionally separated from the live trading workflow.")
    st.text_area("Full Packet for Deep Review", full_packet, height=560)
    st.download_button("Download Snapshot JSON", data=json.dumps(snapshot, indent=2, default=str).encode("utf-8"), file_name="snapshot_v35_1.json", mime="application/json")

with tabs[5]:
    st.header("Sector Flow")
    sectors = sector_flow(scan)
    st.dataframe(sectors, use_container_width=True)
    if not sectors.empty:
        leader_sector = sectors.iloc[0]["Sector"]
        st.subheader(f"Leaders in strongest sector: {leader_sector}")
        st.dataframe(scan[scan["Sector"] == leader_sector].head(5), use_container_width=True)

with tabs[6]:
    st.header("Strategy Development · Engine Scores")
    st.caption("Diagnostic scoring for improving the system. Not required for live trade execution.")
    st.dataframe(
        scan[[
            "Ticker", "Sector", "Candidate Grade", "V35 Score", "Professional Verdict", "Signal", "Tier", "Best Setup",
            "Professional Score", "Composite Score", "Earnings Score", "Premarket Score", "Learning Score", "Sector Rotation Score", "Total Opportunity Score", "Catalyst Score", "Catalyst Type", "External Score", "External Source", "Money Flow Score", "Best Score", "ORB Score", "VWAP Score", "Gap Score",
            "Momentum Score", "Daily Score", "RS Score", "EV / Share"
        ]],
        use_container_width=True,
        height=560,
    )

with tabs[7]:
    st.header("No Trade / Watch")
    no_trade = scan[~scan["Signal"].isin(["TRADE", "SMALL TRADE"])]
    st.dataframe(
        no_trade[[
            "Ticker", "Composite Verdict", "Signal", "Tier", "Best Setup", "Composite Score", "Sector Rotation Score", "Total Opportunity Score", "Catalyst Score", "External Score", "Money Flow Score",
            "Best Score", "Reason", "Price", "EV / Share", "Reward/Risk",
            "Above VWAP", "OR Status", "OR Zone", "RS Score", "Rejection Reason"
        ]],
        use_container_width=True,
        height=500,
    )

with tabs[8]:
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

with tabs[9]:
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

with tabs[10]:
    st.header("Multi-Source Intelligence")
    st.write("v35 composite score blends technicals, money flow, automated/manual news, sector rotation, and external signals.")
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

with tabs[11]:
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

with tabs[12]:
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

with tabs[13]:
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

with tabs[14]:
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


with tabs[15]:
    st.header("Robinhood Real / Alpaca Paper Mirror")
    st.write("This is the real-money operating checklist. Robinhood remains manual; Alpaca remains the paper mirror unless you deliberately configure live trading.")
    st.text_area("Mirror Plan", v35_robinhood_mirror_text(scan, cash), height=180)

    st.subheader("Manual Robinhood Fill Log")
    with st.form("robinhood_mirror_form", clear_on_submit=True):
        r1, r2, r3, r4 = st.columns(4)
        rh_date = r1.date_input("Trade date", value=date.today())
        rh_ticker = r2.selectbox("Ticker", scan["Ticker"].tolist(), key="rh_ticker")
        rh_side = r3.selectbox("Side", ["BUY", "SELL", "NO TRADE"], key="rh_side")
        rh_account = r4.selectbox("Account", ["Robinhood real", "Alpaca paper", "Both"], key="rh_account")
        r5, r6, r7, r8 = st.columns(4)
        rh_entry = r5.number_input("Fill/entry", min_value=0.0, step=0.01)
        rh_shares = r6.number_input("Shares", min_value=0.0, step=0.0001, format="%.6f")
        rh_stop = r7.number_input("Planned stop", min_value=0.0, step=0.01)
        rh_target = r8.number_input("Target / note price", min_value=0.0, step=0.01)
        rh_notes = st.text_input("Notes / trigger observed")
        if st.form_submit_button("Save Mirror Fill"):
            saved = append_csv_row(ROBINHOOD_MIRROR_FILE, {
                "Timestamp CT": ct_now().strftime("%Y-%m-%d %H:%M:%S"),
                "Trade Date": rh_date.isoformat(),
                "Ticker": rh_ticker,
                "Side": rh_side,
                "Account": rh_account,
                "Entry": rh_entry,
                "Shares": rh_shares,
                "Stop": rh_stop,
                "Target": rh_target,
                "Notes": rh_notes,
            })
            st.success(f"Saved mirror row. Total rows: {len(saved)}")

    st.subheader("Real Trade Review Queue")
    st.dataframe(
        scan[scan["Candidate Grade"].isin(["A", "B"])][[
            "Ticker", "Candidate Grade", "V35.1 Score", "Professional Verdict", "Action Plan",
            "Price", "Stop", "Target 1", "Shares", "Position $", "Dollar Risk", "Best Setup", "Reason"
        ]],
        use_container_width=True,
        height=360,
    )
    mirror_log = load_csv_file(ROBINHOOD_MIRROR_FILE)
    if not mirror_log.empty:
        st.subheader("Saved Mirror Fills")
        st.dataframe(mirror_log.tail(20), use_container_width=True)
    st.warning("A real Robinhood entry requires: Grade A/B, observed trigger, defined stop, and position size you are willing to lose to the stop.")

with tabs[16]:
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


with tabs[17]:
    st.header("V35.1 Action Plan")
    st.text_area("Today's Operating Plan", v351_today_action_plan(scan, light, market_score, market_reason), height=260)
    st.subheader("Top Review Names")
    st.dataframe(
        scan[[
            "Ticker", "Candidate Grade", "V35.1 Score", "Action Plan", "Professional Verdict", "Best Setup",
            "Price", "Stop", "Target 1", "Shares", "Dollar Risk", "Above VWAP", "OR Status", "OR Zone"
        ]].head(12),
        use_container_width=True,
        height=420,
    )

with tabs[18]:
    st.header("Rejection Audit")
    st.write("This tab explains why symbols are not eligible for real-money review. Use it to tune candidate generation without weakening risk rules.")
    audit_cols = [
        "Ticker", "Candidate Grade", "Real Trade Review", "Paper Mirror Eligible", "Rejection Reason",
        "Professional Verdict", "Signal", "V35.1 Score", "Money Flow Score", "Reward/Risk", "EV / Share",
        "Above VWAP", "OR Status", "OR Zone", "Catalyst Score", "Earnings Timing"
    ]
    audit_cols = [c for c in audit_cols if c in scan.columns]
    st.dataframe(scan[audit_cols], use_container_width=True, height=560)

with tabs[19]:
    st.header("Scan History")
    st.write("Save snapshots during the day to learn whether your best candidates appear premarket, at the open, mid-day, or near the close.")
    if st.button("Save Snapshot From History Tab"):
        hist = append_csv_row(SCAN_HISTORY_FILE, v351_scan_history_row(scan, light, market_score, market_reason))
        st.success(f"Saved scan snapshot. History rows: {len(hist)}")
    hist = load_csv_file(SCAN_HISTORY_FILE)
    if hist.empty:
        st.info("No saved scan snapshots yet.")
    else:
        st.dataframe(hist.tail(50), use_container_width=True, height=520)
        st.download_button("Download Scan History CSV", data=df_csv(hist), file_name="scan_history_v35_8.csv", mime="text/csv")



with tabs[20]:
    st.header("Opportunity Discovery Engine")
    st.write("This engine searches a broader universe for fresh movement, liquidity, relative strength, and structure before the v35.2 permission engine decides whether anything deserves real money.")
    st.text_area("Discovery Brief", opportunity_brief, height=150)
    if opportunity_df is None or opportunity_df.empty:
        st.info("No discovery rows available. Enable the engine or reduce the minimum data requirements by scanning fewer symbols first.")
    else:
        od_cols = [
            "Discovery Rank", "Ticker", "Sector", "Discovery Tier", "Discovery Score", "Discovery Action", "Discovery Setup", "Discovery Reason",
            "Already In Manual Scan", "Price", "1D %", "5D %", "1M %", "Gap %", "Rel Vol", "Dollar Volume", "Liquidity",
            "RS vs SPY", "RS vs QQQ", "RS Blend", "ATR %", "Above 20MA", "Above 50MA", "Trend Stack", "Near 20D High", "20D Breakout", "Distance 20MA %"
        ]
        od_cols = [c for c in od_cols if c in opportunity_df.columns]
        st.dataframe(opportunity_df[od_cols], use_container_width=True, height=580)
        active_added = [s for s in symbols if s not in set(manual_symbols)]
        st.subheader("Expanded Active Scan")
        st.write(", ".join(symbols))
        st.caption(f"Manual symbols: {len(manual_symbols)} | Discovery additions: {len(active_added)} | Total scanned by v35.2: {len(symbols)}")
        st.download_button("Download Discovery CSV", data=df_csv(opportunity_df), file_name="opportunity_discovery_v35_8.csv", mime="text/csv")

with tabs[21]:
    st.header("V35.2 Profit Engine")
    st.text_area("Daily Operating Brief", v352_brief, height=260)
    st.subheader("Monthly Pace")
    st.dataframe(pd.DataFrame([month_math]), use_container_width=True)
    st.subheader("Trade Permission Queue")
    permission_cols = [
        "Ticker", "V35.2 Permission", "V35.2 Permission Reason", "Allowed Risk $", "Allowed R Mult",
        "Candidate Grade", "V35.2 Priority Score", "V35.1 Score", "Professional Score", "Money Flow Score",
        "Best Setup", "Action Plan", "Price", "Stop", "Target 1", "Shares", "Dollar Risk",
        "Above VWAP", "OR Status", "OR Zone", "Reward/Risk", "EV / Share"
    ]
    permission_cols = [c for c in permission_cols if c in scan.columns]
    st.dataframe(scan[permission_cols], use_container_width=True, height=560)
    st.subheader("Daily Controls")
    st.write(f"Mode: **{daily_mode_value}**")
    st.write(f"Reason: {daily_mode_reason}")
    st.write(f"Real trades today: {int(daily_trades_taken)} / {int(max_real_trades_per_day)}")
    st.write(f"Daily realized P/L: ${float(daily_pnl_input):,.2f}")
    st.write(f"Daily loss stop: ${float(max_daily_loss_dollars):,.2f}")
    st.warning("The 20% monthly target is treated as a pacing target, not a reason to override risk blocks.")

st.caption("v35.8 adds depth shadows, elevated panels, organized workflow navigation, command-center hierarchy, and the Opportunity Discovery Engine on top of v35.2 profit controls, monthly pace math, real/paper permission logic, and hard trading-mode controls.")
