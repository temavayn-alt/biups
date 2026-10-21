import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import requests
from datetime import datetime, timedelta, date
import calendar
import html
import math
import json
import os
import re
import urllib.parse

try:
    from anthropic import Anthropic
except ImportError:  # AI-аналітик просто вимкнеться, якщо пакет не встановлено
    Anthropic = None

# ==============================================================================
# 🔗 1. НАЛАШТУВАННЯ ТАБЛИЦЬ ТА API
# ==============================================================================
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fUOV3bYgqMHd23lFp-dL7fkO3SxsbO0c2CCoRi8BczQ/edit?usp=sharing"
WEEKLY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fUOV3bYgqMHd23lFp-dL7fkO3SxsbO0c2CCoRi8BczQ/edit?gid=1342107748#gid=1342107748"
NINTENDO_MONTHLY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fUOV3bYgqMHd23lFp-dL7fkO3SxsbO0c2CCoRi8BczQ/edit?gid=1182691055#gid=1182691055"
XBOX_MONTHLY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fUOV3bYgqMHd23lFp-dL7fkO3SxsbO0c2CCoRi8BczQ/edit?gid=1981339676#gid=1981339676"
ACTIVITY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fUOV3bYgqMHd23lFp-dL7fkO3SxsbO0c2CCoRi8BczQ/edit?gid=962012405#gid=962012405"
GOOGLE_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzrYmeab3xtC4TW9id-N60pI6UmOk6OJj7L2OebkV48omIzqD_h827g3C1mSUpt_WusyA/exec"
ANTHROPIC_API_KEY = ""

CERTIFICATION_SHEET_NAME = "Certification"
LEADS_SHEET_NAME = "Leads"          # лист, куди webhook записує ліди з калькулятора
LOGO_FILE = "up4.png"
DEFAULT_IMAGE = "https://img.icons8.com/isometric/100/controller.png"

# ==============================================================================
# 💱 2. ДОВІДНИКИ, ЦІЛІ ТА МОДЕЛІ
# ==============================================================================
SECTIONS = [
    "🎮 Портфоліо",
    "🎯 Цілі та KPI 2026",
    "📈 Динаміка продажів",
    "📅 Календар і сейли",
    "🚀 Релізи",
    "🧮 Прогнози та ліди",
]

PLATFORMS = ["Switch", "PS", "Xbox"]
PLATFORM_LABEL = {"Switch": "Nintendo Switch", "PS": "PlayStation", "Xbox": "Xbox"}
PLATFORM_COLORS = {"Nintendo Switch": "#e60012", "PlayStation": "#3b82f6", "Xbox": "#107c10"}
WEEKLY_PREFIX = {"Switch": "Nintendo", "PS": "PS", "Xbox": "Xbox"}  # префікси колонок тижневого листа

FX_RATES = {
    "USD": 1.00, "EUR": 1.09, "GBP": 1.28, "AUD": 0.67, "NZD": 0.61, "CAD": 0.74,
    "CHF": 1.15, "JPY": 0.0068, "CZK": 0.044, "PLN": 0.26, "ZAR": 0.055, "BRL": 0.18,
    "MXN": 0.052, "SEK": 0.096, "NOK": 0.093, "DKK": 0.146, "CLP": 0.0011, "COP": 0.00024,
    "PEN": 0.27, "ARS": 0.0010, "HKD": 0.128, "KRW": 0.00075, "TWD": 0.031
}

UKR_MONTH_NAMES = ["", "Січ", "Лют", "Бер", "Кві", "Тра", "Чер", "Лип", "Сер", "Вер", "Жов", "Лис", "Гру"]

# 🎯 ЦІЛІ НА 2026 РІК ($500k)
GOAL_YEAR = 2026
TARGETS_2026 = {
    "2026 (рік)": {"Revenue": 500000.0, "Nintendo_Revenue": 130000.0, "PS_Revenue": 250000.0, "Xbox_Revenue": 120000.0,
                   "Deals": 20, "Calls": 100, "Contacts": 500, "Leads": 6000},
    "Q1 2026": {"Revenue": 90000.0, "Nintendo_Revenue": 23500.0, "PS_Revenue": 45000.0, "Xbox_Revenue": 21500.0,
                "Deals": 4, "Calls": 20, "Contacts": 100, "Leads": 1200},
    "Q2 2026": {"Revenue": 110000.0, "Nintendo_Revenue": 28500.0, "PS_Revenue": 55000.0, "Xbox_Revenue": 26500.0,
                "Deals": 5, "Calls": 25, "Contacts": 125, "Leads": 1500},
    "Q3 2026": {"Revenue": 130000.0, "Nintendo_Revenue": 34000.0, "PS_Revenue": 65000.0, "Xbox_Revenue": 31000.0,
                "Deals": 5, "Calls": 25, "Contacts": 125, "Leads": 1500},
    "Q4 2026": {"Revenue": 170000.0, "Nintendo_Revenue": 44000.0, "PS_Revenue": 85000.0, "Xbox_Revenue": 41000.0,
                "Deals": 6, "Calls": 30, "Contacts": 150, "Leads": 1800},
}

# Статус сейлу ("йде зараз / майбутній / завершився") тепер рахується автоматично від сьогоднішньої дати
NINTENDO_SCHEDULE = [
    {"name": "Autumn Sale", "start": "2026-09-11", "end": "2026-09-24", "region": "Global / EU / US"},
    {"name": "Halloween Sale", "start": "2026-10-26", "end": "2026-11-15", "region": "Global"},
    {"name": "Holiday Sale (EU)", "start": "2026-12-17", "end": "2027-01-10", "region": "Europe / Australia"},
    {"name": "Holiday Sale (US)", "start": "2026-12-21", "end": "2027-01-11", "region": "Americas"},
]

XBOX_SCHEDULE = [
    {"name": "Deep Discounts Sale (ID)", "start": "2026-11-05", "end": "2026-11-11", "deadline": "2026-10-01", "feedback": "2026-10-14",
     "limit": 10, "min_price": 0.0, "min_discount": 65, "type": "ID Sale (Глибокі знижки)",
     "note": "Знижка 65% або більше. Ліміт: до 10 тайтлів."},
    {"name": "Black Friday Sale", "start": "2026-11-20", "end": "2026-12-02", "deadline": "2026-10-02", "feedback": "2026-10-15",
     "limit": 5, "min_price": 9.99, "min_discount": 10, "type": "Tentpole Sale",
     "note": "Базова ціна від $9.99. Ліміт: до 5 тайтлів. Кулдаун знято тільки між BF та Countdown."},
    {"name": "Countdown Sale", "start": "2026-12-17", "end": "2027-01-06", "deadline": "2026-10-30", "feedback": "2026-11-13",
     "limit": 5, "min_price": 9.99, "min_discount": 10, "type": "Tentpole Sale",
     "note": "Базова ціна від $9.99. Ліміт: до 5 тайтлів."},
]
NINTENDO_COOLDOWN_DAYS = 30

GENRE_DATABASE = {
    "Simulator: Animal Chaos / Cat Meme (3D)": {"PS": 3.2, "Xbox": 1.25, "Switch": 1.35, "Decay": 1.25, "Desc": "Bad Cat, Bad Raccoon, Angry Dog, Smash Cat"},
    "Simulator: Crime / Black Market (3D)": {"PS": 4.0, "Xbox": 4.2, "Switch": 0.4, "Decay": 1.20, "Desc": "Drug Dealer Empire (Xbox феномен)"},
    "Simulator: Cozy Cafe / Animal Job Sim": {"PS": 1.8, "Xbox": 1.1, "Switch": 1.35, "Decay": 1.25, "Desc": "Funny Animal Cafe, Tricky Monkey Zoo, Funny Folks Cafe"},
    "Simulator: Shop / Supermarket / Store (3D)": {"PS": 2.2, "Xbox": 1.2, "Switch": 1.85, "Decay": 1.35, "Desc": "My Supermarket Simulator (Лідер на Switch)"},
    "Simulator: Job / Service / Business (3D)": {"PS": 1.5, "Xbox": 1.1, "Switch": 0.95, "Decay": 1.20, "Desc": "Waterpark Manager, Street Food Simulator, Digging Sim"},
    "Simulator: Truck / Heavy Logistics (3D/2D)": {"PS": 1.4, "Xbox": 1.55, "Switch": 2.10, "Decay": 1.25, "Desc": "Heavy Duty, Trucker Ben"},
    "Simulator: Farming / Homestead / Ranch": {"PS": 0.9, "Xbox": 1.1, "Switch": 2.6, "Decay": 1.35, "Desc": "Монополія аудиторії Nintendo"},
    "Simulator: Casual Flight / Paper Plane": {"PS": 0.3, "Xbox": 0.20, "Switch": 0.25, "Decay": 1.15, "Desc": "🔴 Paperly, Fly for Fly (Зона низької конверсії)"},
    "Horror: 3D PSX / Retro / VHS Style": {"PS": 1.6, "Xbox": 2.6, "Switch": 0.35, "Decay": 1.20, "Desc": "Skinwalker, TROX, Is Today Another Day (Xbox домінує)"},
    "Horror: 3D First-Person Atmospheric": {"PS": 1.4, "Xbox": 1.1, "Switch": 0.32, "Decay": 1.15, "Desc": "Cornfield, Death Attraction, Dr. Psycho, Captive, Seishin"},
    "Horror: 3D Anomaly / Walking Sim / Backrooms": {"PS": 2.4, "Xbox": 1.5, "Switch": 0.8, "Decay": 1.15, "Desc": "Exit 8, Don't Scream (PS попит)"},
    "Survival: Bunker / Hardcore Crafting (3D/2D)": {"PS": 1.8, "Xbox": 3.2, "Switch": 1.8, "Decay": 1.30, "Desc": "From the Bunker, Survival After War (Xbox + Switch)"},
    "Survival: Open-World / Island Crafting (3D)": {"PS": 1.6, "Xbox": 1.8, "Switch": 1.4, "Decay": 1.25, "Desc": "Call of Island, WinterCraft"},
    "Platformer: 3D Physics / Character Adventure": {"PS": 1.8, "Xbox": 1.6, "Switch": 1.5, "Decay": 1.20, "Desc": "Super Adventure Hand"},
    "Platformer: 3D Obby / Roblox-style": {"PS": 1.6, "Xbox": 1.2, "Switch": 1.8, "Decay": 1.20, "Desc": "Obby Parkour, Blade Ball"},
    "Physics: 3D Ragdoll / Sandbox Chaos": {"PS": 2.8, "Xbox": 1.1, "Switch": 1.4, "Decay": 1.15, "Desc": "Mr. Dude, Action Playground, Car Crash"},
    "Physics: Rage / Climbing / 'Only Up'": {"PS": 1.6, "Xbox": 1.0, "Switch": 1.3, "Decay": 1.15, "Desc": "Super Rock Climber"},
    "Cozy: Organization / Packing / Decor": {"PS": 0.7, "Xbox": 0.4, "Switch": 2.6, "Decay": 1.40, "Desc": "Packit List, Unpacking-вайб"},
    "Puzzle: 2D Mobile-style / Jigsaw / Color": {"PS": 0.5, "Xbox": 0.6, "Switch": 1.4, "Decay": 1.30, "Desc": "Find Sort Match, Trainlax, Pixel House"},
    "Puzzle: Suika / Drop & Merge / Watermelon": {"PS": 0.5, "Xbox": 0.4, "Switch": 2.2, "Decay": 1.20, "Desc": "Suika Balls, Fruit Merge"},
    "Puzzle: Hidden Object / Detective Quest": {"PS": 1.4, "Xbox": 0.95, "Switch": 1.70, "Decay": 1.35, "Desc": "Conquistadorio, Minima, Dollmaker"},
    "Racing: 3D Arcade / Traffic Driving": {"PS": 2.2, "Xbox": 0.6, "Switch": 1.30, "Decay": 1.20, "Desc": "Hyper Cars Ramp Crash, Gran Carismo"},
    "Action: 3D Top-Down / Extraction Shooter": {"PS": 1.6, "Xbox": 1.5, "Switch": 1.00, "Decay": 1.25, "Desc": "Bunker 22, Zombiescraper"},
    "Action: 2D Hack'n'Slash / Beat'em Up": {"PS": 1.1, "Xbox": 0.9, "Switch": 1.2, "Decay": 1.20, "Desc": "Bob the Warrior, Street Combat"},
    "Fighting: 2D/3D Local Party / Brawler": {"PS": 0.6, "Xbox": 0.5, "Switch": 0.50, "Decay": 1.15, "Desc": "Street Combat Fighting"},
    "Roguelike: Auto-Shooter / 'Survivor-like'": {"PS": 1.3, "Xbox": 1.75, "Switch": 2.35, "Decay": 1.25, "Desc": "Nom Nom Apocalypse"},
    "Card Game / Deckbuilder / Narrative": {"PS": 0.9, "Xbox": 1.35, "Switch": 0.70, "Decay": 1.20, "Desc": "Rabbit Samurai"},
    "Metroidvania: 2D Pixel / Action Platformer": {"PS": 0.8, "Xbox": 0.47, "Switch": 0.15, "Decay": 1.15, "Desc": "⚠️ ABSURDIKA: Rebuild"},
    "Strategy: Tower Defense / Castle Defense": {"PS": 1.4, "Xbox": 1.10, "Switch": 1.28, "Decay": 1.25, "Desc": "Epic Empire, Wizard's Fortress"},
    "Visual Novel: Western / Narrative Choice": {"PS": 0.8, "Xbox": 0.52, "Switch": 0.31, "Decay": 1.25, "Desc": "Choice of Life: Wild Islands"},
    "Idle / Clicker / Incremental": {"PS": 0.5, "Xbox": 0.4, "Switch": 1.00, "Decay": 1.20, "Desc": "Loaders Inc., Let's Journey"},
}
DEFAULT_GENRE = "Simulator: Job / Service / Business (3D)"

PRICE_MODIFIERS = {1.99: 1.40, 4.99: 1.20, 5.99: 1.10, 6.99: 1.05, 9.99: 1.00, 14.99: 0.70, 19.99: 0.50, 49.99: 0.20, 99.99: 0.10}

# 🧠 Єдина модель життєвого циклу — використовується в «Інсайтах», «Аналітиці» та калькуляторі
LTV_MULT = {"M3": 1.35, "M6": 1.70, "1Y": 3.0}
PERIODS = ["M1", "M3", "M6", "1Y"]
PERIOD_DAYS = {"M1": 30, "M3": 90, "M6": 180, "1Y": 365}
# True  — колонки "3 month", "6 month", "1 year" накопичувальні (виручка з дня релізу)
# False — кожна колонка містить виручку лише за свій відрізок; код сам їх підсумує
PERIOD_COLS_ARE_CUMULATIVE = True
DEV_OK_BAND = 15  # ±% — «в межах моделі»

# 💵 Фінансові параметри за замовчуванням (змінюються слайдерами у «Портфоліо → P&L»)
DEFAULT_STORE_CUT = 30
DEFAULT_TAX_CUT = 7
DEFAULT_DEV_SPLIT = 50

ACTIVITY_CHECKBOX_COLS = [
    "Keymailer page", "Instagram", "YouTube", "PS Form", "PS Trailer",
    "Xbox Trailer", "Xbox Shorts", "Xbox Form", "IGN Trailer", "Press Release", "Trophy Guide", "Keys"
]

TODAY = date.today()

# ==============================================================================
# 🎨 3. СТОРІНКА, CSS ТА ТЕМА ГРАФІКІВ
# ==============================================================================
st.set_page_config(
    page_title="Upscale Studio | Console BI & Growth Hub",
    page_icon=LOGO_FILE if os.path.exists(LOGO_FILE) else "🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2.5rem; max-width: 96% !important; }
    section[data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem !important; }

    section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child,
    section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"],
    section[data-testid="stSidebar"] [data-testid="stRadioButtonCustom"],
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        display: none !important; visibility: hidden !important; width: 0 !important; height: 0 !important; margin: 0 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"],
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div,
    section[data-testid="stSidebar"] div[role="radiogroup"] { width: 100% !important; }
    section[data-testid="stSidebar"] div[role="radiogroup"] { display: flex !important; flex-direction: column !important; align-items: stretch !important; gap: 6px !important; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label { flex: 1 1 auto !important; max-width: none !important; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: #161622 !important; border: 1px solid #28283c !important; border-radius: 9px !important;
        padding: 10px 14px !important; margin: 0 !important; cursor: pointer !important; transition: all 0.2s ease !important;
        display: flex !important; align-items: center !important; width: 100% !important; box-sizing: border-box !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: #202033 !important; border-color: #a855f7 !important; transform: translateX(3px) !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked),
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(90deg, rgba(217, 70, 239, 0.22) 0%, rgba(249, 115, 22, 0.16) 100%) !important;
        border: 1px solid #d946ef !important; box-shadow: 0 3px 12px rgba(217, 70, 239, 0.18) !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label p { color: #94a3b8 !important; font-size: 13.5px !important; font-weight: 600 !important; margin: 0 !important; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p,
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] p { color: #ffffff !important; font-weight: 700 !important; }

    .stTabs [data-baseweb="tab-list"] { gap: 16px; border-bottom: 1px solid #28283c; background-color: transparent !important; padding-bottom: 0px; }
    .stTabs [data-baseweb="tab"] {
        height: 38px; background-color: transparent !important; border: none !important; border-bottom: 2px solid transparent !important;
        padding: 4px 10px; color: #94a3b8 !important; font-size: 14px; font-weight: 500; transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover { color: #e2e8f0 !important; }
    .stTabs [aria-selected="true"] { background-color: transparent !important; color: #ffffff !important; font-weight: 700 !important; border-bottom: 2px solid #d946ef !important; }

    .kpi-card {
        background: linear-gradient(135deg, #1e1e2d 0%, #161622 100%); border: 1px solid #2e2e44; border-radius: 12px;
        padding: 16px 20px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25); margin-bottom: 10px; height: 100%;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .kpi-label { font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 4px; }
    .kpi-value { font-size: 24px; font-weight: 800; color: #ffffff; margin-bottom: 4px; font-family: -apple-system, sans-serif; }
    .kpi-badge { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; width: fit-content; }
    .badge-total { background-color: rgba(99, 102, 241, 0.2); color: #a5b4fc; }
    .badge-switch { background-color: rgba(230, 0, 18, 0.18); color: #ff6b6b; }
    .badge-ps { background-color: rgba(0, 55, 145, 0.25); color: #60a5fa; }
    .badge-xbox { background-color: rgba(16, 124, 16, 0.25); color: #4ade80; }

    .top-podium-card { background: #181824; border: 1px solid #2b2b3f; border-radius: 10px; padding: 12px; text-align: center; }
    .sandbox-box { background: #171724; border: 1px solid #2f2f45; border-radius: 12px; padding: 20px; margin-bottom: 15px; }
    .alert-card-red { background: linear-gradient(135deg, #2d141e 0%, #1c0d13 100%); border: 1px solid #7f1d1d; border-left: 5px solid #ef4444; border-radius: 10px; padding: 14px; margin-bottom: 12px; }
    .alert-card-yellow { background: linear-gradient(135deg, #2d2414 0%, #1c170d 100%); border: 1px solid #854d0e; border-left: 5px solid #eab308; border-radius: 10px; padding: 14px; margin-bottom: 12px; }

    /* ---------- Календар: тижні як CSS-grid, багатоденні події — суцільні смуги ---------- */
    .cal-container { background: #13131e; border: 1px solid #28283c; border-radius: 12px; overflow: hidden; margin-top: 15px; }
    .cal-header { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); background: #1a1a27; border-bottom: 1px solid #28283c; }
    .cal-header-cell { padding: 10px; text-align: center; font-size: 12px; font-weight: 700; color: #94a3b8; text-transform: uppercase; }
    .cal-week { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); min-height: 112px; border-bottom: 1px solid #242436; }
    .cal-week:last-child { border-bottom: none; }
    .cal-bg { background: #161622; border-right: 1px solid #242436; }
    .cal-bg:nth-child(7) { border-right: none; }
    .cal-bg.other-month { background: #11111a; }
    .cal-bg.today { background: #1d182b; box-shadow: inset 0 0 0 1.5px #d946ef; }
    .cal-num { z-index: 1; font-size: 11px; font-weight: 700; color: #94a3b8; text-align: right; padding: 5px 8px 0 0; }
    .cal-num.other-month { opacity: 0.4; }
    .cal-num.today { color: #f0abfc; }
    .cal-bar {
        z-index: 2; align-self: center; height: 18px; line-height: 14px; box-sizing: border-box; margin: 0 4px;
        font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: default;
    }
    .cal-bar.cont-left { margin-left: 0; border-top-left-radius: 0; border-bottom-left-radius: 0; border-left-width: 0; }
    .cal-bar.cont-right { margin-right: 0; border-top-right-radius: 0; border-bottom-right-radius: 0; }
    .cal-more { z-index: 2; font-size: 9.5px; color: #94a3b8; font-weight: 700; padding: 1px 6px; }
    .pill-release { background: rgba(139, 92, 246, 0.25); border-left: 3px solid #a855f7; color: #e9d5ff; }
    .pill-nintendo { background: rgba(230, 0, 18, 0.2); border-left: 3px solid #ff4d4f; color: #ffccc7; }
    .pill-xbox { background: rgba(16, 124, 16, 0.22); border-left: 3px solid #52c41a; color: #d9f7be; }
    .pill-deadline { background: rgba(245, 158, 11, 0.25); border-left: 3px solid #faad14; color: #ffe58f; font-weight: 700; }

    /* ---------- Інсайти (LTV): картка з фактом + «+» для прогнозів ---------- */
    .lc-card { position: relative; display: flex; gap: 16px; background: #161622; border: 1px solid #28283c; border-radius: 12px; padding: 16px; margin-bottom: 12px; align-items: flex-start; }
    .lc-chips { display: flex; flex-wrap: wrap; gap: 8px; }
    .lc-chip { background: #13131e; border: 1px solid #28283c; border-radius: 6px; padding: 6px 10px; font-size: 12px; min-width: 150px; }
    .lc-toggle > summary {
        list-style: none; position: absolute; top: 14px; right: 14px; width: 28px; height: 28px; border-radius: 7px;
        border: 1px solid #3a3a55; background: #1e1e2d; color: #d946ef; font-size: 20px; font-weight: 700;
        line-height: 25px; text-align: center; cursor: pointer; user-select: none; transition: all 0.2s ease;
    }
    .lc-toggle > summary::-webkit-details-marker { display: none; }
    .lc-toggle > summary:hover { border-color: #d946ef; background: #2a1d35; }
    .lc-toggle[open] > summary { transform: rotate(45deg); border-color: #d946ef; background: #2a1d35; }
    .lc-panel { margin-top: 12px; padding-top: 12px; border-top: 1px dashed #2e2e44; display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 12px; }
    .lc-section { background: #0f0f17; border: 1px solid #28283c; border-radius: 10px; padding: 12px; }
    .lc-section-title { font-size: 13px; font-weight: 700; color: #e2e8f0; margin-bottom: 2px; }
    .lc-section-sub { font-size: 11px; color: #64748b; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# Одна тема для всіх графіків замість повторення paper_bgcolor/plot_bgcolor у кожному
pio.templates["upscale"] = go.layout.Template(layout=dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"),
    xaxis=dict(gridcolor="#28283c", zerolinecolor="#28283c"), yaxis=dict(gridcolor="#28283c", zerolinecolor="#28283c"),
    margin=dict(t=30, b=20, l=10, r=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title_text=""),
))
pio.templates.default = "plotly_dark+upscale"

# ==============================================================================
# 🌐 3.0 СЛОВНИК ПЕРЕКЛАДІВ: "українська фраза": ("русский", "English")
# ==============================================================================
# Фрази шукаються в усьому, що виводиться на екран, від найдовшої до найкоротшої.
# Якщо якийсь текст не перекладено — додай сюди рядок з точною українською фразою.
TR = {
    # ---------- Навігація та загальне ----------
    "🎮 Портфоліо": ("🎮 Портфолио", "🎮 Portfolio"),
    "🎯 Цілі та KPI 2026": ("🎯 Цели и KPI 2026", "🎯 Goals & KPI 2026"),
    "📈 Динаміка продажів": ("📈 Динамика продаж", "📈 Sales dynamics"),
    "📅 Календар і сейли": ("📅 Календарь и сейлы", "📅 Calendar & sales"),
    "🚀 Релізи": ("🚀 Релизы", "🚀 Releases"),
    "🧮 Прогнози та ліди": ("🧮 Прогнозы и лиды", "🧮 Forecasts & leads"),
    "🌐 Мова:": ("🌐 Язык:", "🌐 Language:"),
    "📍 НАВІГАЦІЯ ХАБУ:": ("📍 НАВИГАЦИЯ ХАБА:", "📍 HUB NAVIGATION:"),
    "Навігація:": ("Навигация:", "Navigation:"),
    "🔍 ФІЛЬТРАЦІЯ КАТАЛОГУ:": ("🔍 ФИЛЬТРАЦИЯ КАТАЛОГА:", "🔍 CATALOG FILTERS:"),
    "Пошук гри...": ("Поиск игры...", "Search game..."),
    "Пошук гри:": ("Поиск игры:", "Search game:"),
    "Жанри:": ("Жанры:", "Genres:"),
    "Усі жанри": ("Все жанры", "All genres"),
    "🔄 Оновити дані з Google Sheets": ("🔄 Обновить данные из Google Sheets", "🔄 Refresh data from Google Sheets"),
    "🤖 AI-аналітик": ("🤖 AI-аналитик", "🤖 AI analyst"),
    "Запитай базу даних:": ("Спроси базу данных:", "Ask the database:"),
    "Напр.: Яка конверсія лідів у контракти?": ("Напр.: Какая конверсия лидов в контракты?", "E.g.: What is the lead-to-contract conversion?"),
    "⚡ Запитати Claude": ("⚡ Спросить Claude", "⚡ Ask Claude"),
    "Пакет `anthropic` не встановлено.": ("Пакет `anthropic` не установлен.", "The `anthropic` package is not installed."),
    "❌ Введи валідний ключ Anthropic (sk-ant-...)!": ("❌ Введи валидный ключ Anthropic (sk-ant-...)!", "❌ Enter a valid Anthropic key (sk-ant-...)!"),
    "Введи запитання.": ("Введи вопрос.", "Enter a question."),
    "Claude аналізує базу...": ("Claude анализирует базу...", "Claude is analyzing the data..."),
    "##### 💡 Результат аналізу:": ("##### 💡 Результат анализа:", "##### 💡 Analysis result:"),
    "❌ Помилка Anthropic API:": ("❌ Ошибка Anthropic API:", "❌ Anthropic API error:"),
    "👋 Вкажи валідне посилання на Google Таблицю у рядку `GOOGLE_SHEET_URL`.": (
        "👋 Укажи валидную ссылку на Google Таблицу в строке `GOOGLE_SHEET_URL`.",
        "👋 Set a valid Google Sheets link in `GOOGLE_SHEET_URL`."),
    "сьогодні": ("сегодня", "today"),
    "Весь період": ("Весь период", "All time"),
    "весь період": ("весь период", "all time"),
    "(рік)": ("(год)", "(year)"),
    "Період:": ("Период:", "Period:"),
    "Період": ("Период", "Period"),
    "Квартал, рік або місяць:": ("Квартал, год или месяц:", "Quarter, year or month:"),

    # ---------- Портфоліо ----------
    "📊 Портфоліо Upscale Studio": ("📊 Портфолио Upscale Studio", "📊 Upscale Studio portfolio"),
    "Фактичні результати випущених ігор • У вибірці:": ("Фактические результаты вышедших игр • В выборке:", "Actual results of released games • In selection:"),
    "Загальна каса (All-Time)": ("Общая касса (All-Time)", "Total gross (All-Time)"),
    "частка": ("доля", "share"),
    "📈 Аналітика": ("📈 Аналитика", "📈 Analytics"),
    "🧠 Інсайти (LTV)": ("🧠 Инсайты (LTV)", "🧠 Insights (LTV)"),
    "💵 P&L, зарплати та роялті": ("💵 P&L, зарплаты и роялти", "💵 P&L, salaries & royalties"),
    "📑 Таблиця та One-Pager": ("📑 Таблица и One-Pager", "📑 Table & One-Pager"),
    "🏆 Топ-3 бестселери портфоліо": ("🏆 Топ-3 бестселлера портфолио", "🏆 Top-3 portfolio bestsellers"),
    "🧩 Які жанри приносять гроші": ("🧩 Какие жанры приносят деньги", "🧩 Which genres make money"),
    "🎮 Топ-15: на яких консолях тримається гра": ("🎮 Топ-15: на каких консолях держится игра", "🎮 Top-15: which consoles carry each game"),
    "Немає ігор із виручкою у вибірці.": ("Нет игр с выручкой в выборке.", "No games with revenue in the selection."),
    "Немає ігор у вибірці.": ("Нет игр в выборке.", "No games in the selection."),
    "Портфоліо": ("Портфолио", "Portfolio"),
    "Без жанру": ("Без жанра", "No genre"),
    "портфоліо": ("портфолио", "of portfolio"),
    "Топ жанри:": ("Топ жанры:", "Top genres:"),
    "виручки,": ("выручки,", "of revenue,"),
    "на гру": ("на игру", "per game"),
    "Інше / без платформи": ("Другое / без платформы", "Other / no platform"),
    "Інше:": ("Другое:", "Other:"),
    "Виторг ($)": ("Выручка ($)", "Revenue ($)"),
    "⏳ Крива життєвого циклу: факт vs модель": ("⏳ Кривая жизненного цикла: факт vs модель", "⏳ Lifecycle curve: actual vs model"),
    "Медіанний множник до M1 по іграх, у яких період уже повністю минув. Деталі по кожній грі — у вкладці «Інсайти».": (
        "Медианный множитель к M1 по играм, у которых период уже полностью прошёл. Детали по каждой игре — во вкладке «Инсайты».",
        "Median multiplier vs M1 across games whose period has fully passed. Per-game details are in the «Insights» tab."),
    "Факт (медіана)": ("Факт (медиана)", "Actual (median)"),
    "Модель": ("Модель", "Model"),
    "× від M1": ("× от M1", "× of M1"),

    # ---------- Інсайти ----------
    "🧠 Життєвий цикл та LTV (M1 ➔ M3 ➔ M6 ➔ 1Y)": ("🧠 Жизненный цикл и LTV (M1 ➔ M3 ➔ M6 ➔ 1Y)", "🧠 Lifecycle & LTV (M1 ➔ M3 ➔ M6 ➔ 1Y)"),
    "Картка показує фактичні продажі • Натисни «+», щоб побачити прогнози • Модель:": (
        "Карточка показывает фактические продажи • Нажми «+», чтобы увидеть прогнозы • Модель:",
        "The card shows actual sales • Press «+» to see forecasts • Model:"),
    "Показати тільки ігри з зафіксованим фактом M1": ("Показать только игры с зафиксированным фактом M1", "Show only games with actual M1"),
    "Сортування:": ("Сортировка:", "Sort:"),
    "Як у таблиці": ("Как в таблице", "As in the table"),
    "Найбільше відхилення від прогнозу": ("Наибольшее отклонение от прогноза", "Largest deviation from forecast"),
    "Найновіші релізи": ("Новейшие релизы", "Newest releases"),
    "Найбільший M1": ("Наибольший M1", "Largest M1"),
    "Ціна:": ("Цена:", "Price:"),
    "Реліз: —": ("Релиз: —", "Release: —"),
    "Реліз:": ("Релиз:", "Release:"),
    "дн. у продажу": ("дн. в продаже", "days on sale"),
    "вихід через": ("выход через", "release in"),
    "🔥 Сильний старт": ("🔥 Сильный старт", "🔥 Strong start"),
    "🟡 Стабільна динаміка": ("🟡 Стабильная динамика", "🟡 Steady performance"),
    "⚠️ Слабкий M1": ("⚠️ Слабый M1", "⚠️ Weak M1"),
    "⏳ Очікує релізу / Немає M1": ("⏳ Ждёт релиза / Нет M1", "⏳ Awaiting release / No M1"),
    "Високий органічний попит. Рекомендовано тримати знижки не глибше 30–45% у перші 6 місяців.": (
        "Высокий органический спрос. Рекомендуется держать скидки не глубже 30–45% в первые 6 месяцев.",
        "High organic demand. Keep discounts no deeper than 30–45% for the first 6 months."),
    "Збалансований темп. Основний добір каси — між 3-м та 6-м місяцями на сезонних сейлах (60–70%).": (
        "Сбалансированный темп. Основной добор кассы — между 3-м и 6-м месяцами на сезонных сейлах (60–70%).",
        "Balanced pace. Most of the remaining revenue comes between months 3 and 6 on seasonal sales (60–70%)."),
    "Органіки за фулпрайс недостатньо. Рекомендовано швидше виходити на імпульсну ціну ($1.99–$2.49) для потрапляння в 'Great Deals'.": (
        "Органики по фулпрайсу недостаточно. Рекомендуется быстрее выходить на импульсную цену ($1.99–$2.49), чтобы попасть в 'Great Deals'.",
        "Not enough organic sales at full price. Move to an impulse price ($1.99–$2.49) sooner to get into 'Great Deals'."),
    "випереджає модель на": ("опережает модель на", "is ahead of the model by"),
    "— довгий хвіст сильніший за середній, з глибокими знижками можна не поспішати.": (
        "— длинный хвост сильнее среднего, с глубокими скидками можно не спешить.",
        "— the long tail is stronger than average, no need to rush deep discounts."),
    "відстає від моделі на": ("отстаёт от модели на", "is behind the model by"),
    "— хвіст продажів слабший, варто раніше підключати сейли та бандли.": (
        "— хвост продаж слабее, стоит раньше подключать сейлы и бандлы.",
        "— the sales tail is weaker, add sales and bundles earlier."),
    "у межах ±": ("в пределах ±", "within ±"),
    "% від моделі (": ("% от модели (", "% of the model ("),
    "Очікуваний річний LTV:": ("Ожидаемый годовой LTV:", "Expected 1-year LTV:"),
    "Інсайт та рекомендація:": ("Инсайт и рекомендация:", "Insight & recommendation:"),
    "Звітних даних першого місяця ще немає. Прогноз до релізу (з даних інших платформ) — під кнопкою «+».": (
        "Отчётных данных первого месяца ещё нет. Прогноз до релиза (по данным других платформ) — под кнопкой «+».",
        "No first-month data yet. The pre-release forecast (from other platforms' data) is under the «+» button."),
    "Показати прогнози": ("Показать прогнозы", "Show forecasts"),
    "вихід через": ("выход через", "release in"),
    "дані через": ("данные через", "data in"),
    "поки що · ще": ("пока что · ещё", "so far · left:"),
    "період завершено": ("период завершён", "period closed"),
    "дата релізу невідома": ("дата релиза неизвестна", "release date unknown"),
    "немає даних": ("нет данных", "no data"),
    "Факт: немає даних": ("Факт: нет данных", "Actual: no data"),
    "Факт:": ("Факт:", "Actual:"),
    "Зараз:": ("Сейчас:", "Now:"),
    "Ще не вийшла": ("Ещё не вышла", "Not released yet"),
    "📈 Прогноз на основі M1": ("📈 Прогноз на основе M1", "📈 Forecast based on M1"),
    "База: факт першого місяця": ("База: факт первого месяца", "Base: first-month actual"),
    "Розрахується після появи продажів за перший місяць.": ("Рассчитается после появления продаж за первый месяц.", "Will be calculated once first-month sales appear."),
    "База: факт M1": ("База: факт M1", "Base: actual M1"),
    "(місяць ще триває — прогноз попередній)": ("(месяц ещё идёт — прогноз предварительный)", "(month still running — preliminary forecast)"),
    "🔮 Прогноз до релізу (дані з інших платформ)": ("🔮 Прогноз до релиза (данные с других платформ)", "🔮 Pre-release forecast (other platforms' data)"),
    "У каталозі немає вхідних метрик з платформ для цієї гри.": ("В каталоге нет входных метрик с платформ для этой игры.", "The catalog has no source-platform metrics for this game."),
    "Джерело:": ("Источник:", "Source:"),
    "авто": ("авто", "auto"),
    "· база $": ("· база $", "· base $"),
    "Прогноз M1": ("Прогноз M1", "Forecast M1"),
    "Прогноз": ("Прогноз", "Forecast"),
    "Факт M1": ("Факт M1", "Actual M1"),
    "Факт M3": ("Факт M3", "Actual M3"),
    "Факт M6": ("Факт M6", "Actual M6"),
    "Факт 1Y": ("Факт 1Y", "Actual 1Y"),
    "прогноз M1": ("прогноз M1", "M1 forecast"),
    "до релізу": ("до релиза", "pre-release"),
    "факт": ("факт", "actual"),
    "Розподіл доходу (All Time)": ("Распределение дохода (All Time)", "Revenue split (All Time)"),
    "Продажів ще немає": ("Продаж ещё нет", "No sales yet"),

    # ---------- P&L / таблиця ----------
    "💵 Фінансовий P&L, зарплати портингу та роялті девелоперів": ("💵 Финансовый P&L, зарплаты портинга и роялти девелоперов", "💵 Financial P&L, porting salaries & developer royalties"),
    "⚙️ Параметри комісій і податків (діють і в калькуляторі лідів)": ("⚙️ Параметры комиссий и налогов (действуют и в калькуляторе лидов)", "⚙️ Fees & taxes settings (also used in the lead calculator)"),
    "Комісія сторів (%):": ("Комиссия сторов (%):", "Store fee (%):"),
    "Податки та резерви (%):": ("Налоги и резервы (%):", "Taxes & reserves (%):"),
    "Спліт девелопера за замовчуванням (%):": ("Сплит девелопера по умолчанию (%):", "Default developer split (%):"),
    "Використовується, якщо в каталозі немає колонки Revenue Split для гри": ("Используется, если в каталоге нет колонки Revenue Split для игры", "Used when the catalog has no Revenue Split column for a game"),
    "Net у банку ($)": ("Net в банке ($)", "Net in bank ($)"),
    "Net у банку (": ("Net в банке (", "Net in bank ("),
    "Виплати роялті авторам": ("Выплаты роялти авторам", "Royalty payouts"),
    "🔥 Чистий прибуток Upscale Studio": ("🔥 Чистая прибыль Upscale Studio", "🔥 Upscale Studio net profit"),
    "🔥 Чистий прибуток студії ($)": ("🔥 Чистая прибыль студии ($)", "🔥 Studio net profit ($)"),
    "Зарплати:": ("Зарплаты:", "Salaries:"),
    "Зарплата розробника ($)": ("Зарплата разработчика ($)", "Developer salary ($)"),
    "Роялті автору ($)": ("Роялти автору ($)", "Author royalty ($)"),
    "Гра": ("Игра", "Game"),
    "📑 Повна фінансова таблиця портфоліо": ("📑 Полная финансовая таблица портфолио", "📑 Full portfolio financial table"),
    "Обкладинка": ("Обложка", "Cover"),
    "📥 Експортувати дані (.CSV)": ("📥 Экспортировать данные (.CSV)", "📥 Export data (.CSV)"),
    "📄 One-Pager Executive звіт": ("📄 One-Pager Executive отчёт", "📄 One-Pager executive report"),
    "📥 Завантажити One-Pager (.HTML / PDF)": ("📥 Скачать One-Pager (.HTML / PDF)", "📥 Download One-Pager (.HTML / PDF)"),

    # ---------- Цілі ----------
    "Ціль на 2026 рік: **$500,000 консольної виручки** • Факт береться з тижневого листа Weekly Updates": (
        "Цель на 2026 год: **$500,000 консольной выручки** • Факт берётся из недельного листа Weekly Updates",
        "2026 goal: **$500,000 console revenue** • Actuals come from the Weekly Updates sheet"),
    "⚠️ Немає тижневих даних. Перевір `WEEKLY_SHEET_URL`.": ("⚠️ Нет недельных данных. Проверь `WEEKLY_SHEET_URL`.", "⚠️ No weekly data. Check `WEEKLY_SHEET_URL`."),
    "📌 Період:": ("📌 Период:", "📌 Period:"),
    "Фінансовий таргет •": ("Финансовый таргет •", "Financial target •"),
    "💰 Виручка: $": ("💰 Выручка: $", "💰 Revenue: $"),
    "Тижневих звітів:": ("Недельных отчётов:", "Weekly reports:"),
    "(останній:": ("(последний:", "(latest:"),
    "минуло": ("прошло", "elapsed"),
    "% періоду •": ("% периода •", "% of period •"),
    "очікувано на сьогодні: $": ("ожидалось на сегодня: $", "expected by today: $"),
    "темп:": ("темп:", "pace:"),
    "% від графіка": ("% от графика", "% of schedule"),
    "виконання плану": ("выполнение плана", "of plan achieved"),
    "ℹ️ У тижневому листі ще немає звітів за цей період — факт поки нульовий.": (
        "ℹ️ В недельном листе ещё нет отчётов за этот период — факт пока нулевой.",
        "ℹ️ The weekly sheet has no reports for this period yet — actuals are zero for now."),
    "🎮 Виконання плану за платформами": ("🎮 Выполнение плана по платформам", "🎮 Plan achievement by platform"),
    "% від цілі (": ("% от цели (", "% of goal ("),
    "% від цілі": ("% от цели", "% of goal"),
    "🤝 BizDev воронка: план vs факт": ("🤝 BizDev воронка: план vs факт", "🤝 BizDev funnel: plan vs actual"),
    "📊 План vs факт по платформах ($)": ("📊 План vs факт по платформам ($)", "📊 Plan vs actual by platform ($)"),
    "📋 Зведення по кварталах": ("📋 Сводка по кварталам", "📋 Quarterly summary"),
    "Квартал": ("Квартал", "Quarter"),
    "Факт ($)": ("Факт ($)", "Actual ($)"),
    "План ($)": ("План ($)", "Plan ($)"),
    "Виконання (%)": ("Выполнение (%)", "Achieved (%)"),
    "Угоди": ("Сделки", "Deals"),
    "Платформа": ("Платформа", "Platform"),
    "Тип": ("Тип", "Type"),
    "Факт": ("Факт", "Actual"),
    "План": ("План", "Plan"),
    "🔮 На скільки закриємо 2026 рік": ("🔮 На сколько закроем 2026 год", "🔮 Where will 2026 close"),
    "🔮 На скільки закриємо": ("🔮 На сколько закроем", "🔮 Where will we close"),
    "рік": ("год", "year"),
    "У тижневому листі ще немає звітів за": ("В недельном листе ещё нет отчётов за", "The weekly sheet has no reports for"),
    "рік — прогноз поки неможливий.": ("год — прогноз пока невозможен.", "yet — forecast not possible."),
    "Поточний темп рахувати за останні:": ("Текущий темп считать за последние:", "Measure current pace over the last:"),
    "тиж.": ("нед.", "wk"),
    "Дані покривають період до": ("Данные покрывают период до", "Data covers the period up to"),
    "до кінця року лишилось": ("до конца года осталось", "remaining in the year:"),
    "дн.** • Два сценарії: темп останніх тижнів (враховує свіжі релізи й сейли) і середній темп з початку року (згладжений).": (
        "дн.** • Два сценария: темп последних недель (учитывает свежие релизы и сейлы) и средний темп с начала года (сглаженный).",
        "days** • Two scenarios: pace of recent weeks (reflects new releases and sales) and the average pace since the start of the year (smoothed)."),
    "Факт 2026 (до": ("Факт 2026 (до", "Actual 2026 (to"),
    "% річної цілі": ("% годовой цели", "% of annual goal"),
    "Прогноз на 31.12 · темп": ("Прогноз на 31.12 · темп", "Forecast for 31.12 · pace"),
    "Прогноз на 31.12 · середній темп року": ("Прогноз на 31.12 · средний темп года", "Forecast for 31.12 · average pace"),
    "% від": ("% от", "% of"),
    "Потрібно на тиждень до кінця року": ("Нужно в неделю до конца года", "Needed per week until year-end"),
    "🎉 Ціль уже досягнута": ("🎉 Цель уже достигнута", "🎉 Goal already reached"),
    "зараз": ("сейчас", "now"),
    "/тиж": ("/нед", "/wk"),
    "від поточного": ("от текущего", "vs current"),
    "При темпі останніх": ("При темпе последних", "At the pace of the last"),
    "тижнів рік закриється на": ("недель год закроется на", "weeks the year will close at"),
    "це на": ("это на", "that is"),
    "більше** за ціль.": ("больше** цели.", "above** the goal."),
    "менше** за ціль.": ("меньше** цели.", "below** the goal."),
    "План (накопичено)": ("План (накоплено)", "Plan (cumulative)"),
    "Факт (накопичено)": ("Факт (накоплено)", "Actual (cumulative)"),
    "Прогноз · темп": ("Прогноз · темп", "Forecast · pace"),
    "Прогноз · середній темп року": ("Прогноз · средний темп года", "Forecast · average pace"),
    "Прогноз (свіжий темп)": ("Прогноз (свежий темп)", "Forecast (recent pace)"),
    "Прогноз (середній темп)": ("Прогноз (средний темп)", "Forecast (average pace)"),
    "Ціль": ("Цель", "Goal"),
    "Факт YTD ($)": ("Факт YTD ($)", "Actual YTD ($)"),
    "Прогноз 31.12 ·": ("Прогноз 31.12 ·", "Forecast 31.12 ·"),
    "тиж. ($)": ("нед. ($)", "wk ($)"),
    "Прогноз 31.12 · сер. темп ($)": ("Прогноз 31.12 · ср. темп ($)", "Forecast 31.12 · avg pace ($)"),
    "Ціль ($)": ("Цель ($)", "Goal ($)"),
    "Прогноз / ціль (%)": ("Прогноз / цель (%)", "Forecast / goal (%)"),
    "Темп зараз ($/тиж)": ("Темп сейчас ($/нед)", "Current pace ($/wk)"),
    "Потрібно ($/тиж)": ("Нужно ($/нед)", "Needed ($/wk)"),

    # ---------- Динаміка ----------
    "Тижнева звітність, BizDev воронка, соцмережі та помісячні звіти сторів • гнучкий вибір періоду, платформ і групування": (
        "Недельная отчётность, BizDev воронка, соцсети и помесячные отчёты сторов • гибкий выбор периода, платформ и группировки",
        "Weekly reporting, BizDev funnel, social media and monthly store reports • flexible period, platform and grouping filters"),
    "⚠️ Немає ні тижневих, ні помісячних даних. Перевір `WEEKLY_SHEET_URL` та посилання на звіти сторів.": (
        "⚠️ Нет ни недельных, ни помесячных данных. Проверь `WEEKLY_SHEET_URL` и ссылки на отчёты сторов.",
        "⚠️ No weekly or monthly data. Check `WEEKLY_SHEET_URL` and the store report links."),
    "Формат вибору періоду:": ("Формат выбора периода:", "Period selection:"),
    "⚡ Останній тиждень": ("⚡ Последняя неделя", "⚡ Last week"),
    "↔️ Останні N тижнів": ("↔️ Последние N недель", "↔️ Last N weeks"),
    "🎯 Квартал / рік / місяць": ("🎯 Квартал / год / месяц", "🎯 Quarter / year / month"),
    "🗓️ Довільні дати": ("🗓️ Произвольные даты", "🗓️ Custom dates"),
    "📅 Весь період": ("📅 Весь период", "📅 All time"),
    "Кількість останніх тижнів:": ("Количество последних недель:", "Number of recent weeks:"),
    "Діапазон дат:": ("Диапазон дат:", "Date range:"),
    "тиждень": ("неделя", "week"),
    "останні": ("последние", "last"),
    "Платформи:": ("Платформы:", "Platforms:"),
    "Групування графіків:": ("Группировка графиков:", "Chart grouping:"),
    "Тижні": ("Недели", "Weeks"),
    "Місяці": ("Месяцы", "Months"),
    "Квартали": ("Кварталы", "Quarters"),
    "тижні": ("недели", "weeks"),
    "місяці": ("месяцы", "months"),
    "квартали": ("кварталы", "quarters"),
    "Порівняти з попер. періодом": ("Сравнить с пред. периодом", "Compare with previous period"),
    "% vs попер. період": ("% vs пред. период", "% vs previous period"),
    "Обрано:": ("Выбрано:", "Selected:"),
    "тижневих звітів:": ("недельных отчётов:", "weekly reports:"),
    "• попередній період для порівняння:": ("• предыдущий период для сравнения:", "• previous period for comparison:"),
    "💰 Виторг": ("💰 Выручка", "💰 Revenue"),
    "📦 Продано копій": ("📦 Продано копий", "📦 Units sold"),
    "💰 Виторг і продажі": ("💰 Выручка и продажи", "💰 Revenue & sales"),
    "🤝 BizDev воронка": ("🤝 BizDev воронка", "🤝 BizDev funnel"),
    "🗓️ Помісячно (звіти сторів)": ("🗓️ Помесячно (отчёты сторов)", "🗓️ Monthly (store reports)"),
    "📱 Соцмережі": ("📱 Соцсети", "📱 Social media"),
    "📑 Таблиця": ("📑 Таблица", "📑 Table"),
    "Немає тижневих даних за обраний період.": ("Нет недельных данных за выбранный период.", "No weekly data for the selected period."),
    "Виторг ($) •": ("Выручка ($) •", "Revenue ($) •"),
    "Продажі в копіях •": ("Продажи в копиях •", "Unit sales •"),
    "Копій (шт)": ("Копий (шт)", "Units"),
    "Вішлісти •": ("Вишлисты •", "Wishlists •"),
    "Період=": ("Период=", "Period="),
    "Немає даних соцмереж за обраний період.": ("Нет данных соцсетей за выбранный период.", "No social media data for the selected period."),
    "📱 Ріст аудиторії та соцмереж (по тижнях)": ("📱 Рост аудитории и соцсетей (по неделям)", "📱 Audience & social growth (weekly)"),
    "Мережі:": ("Сети:", "Networks:"),
    "за період": ("за период", "for the period"),
    "📥 Експортувати тижневий звіт (.CSV)": ("📥 Экспортировать недельный отчёт (.CSV)", "📥 Export weekly report (.CSV)"),
    "🎯 Воронка залучення проєктів (Leads ➔ Deals)": ("🎯 Воронка привлечения проектов (Leads ➔ Deals)", "🎯 Project acquisition funnel (Leads ➔ Deals)"),
    "Немає даних воронки за обраний період.": ("Нет данных воронки за выбранный период.", "No funnel data for the selected period."),
    "% від попер. етапу": ("% от пред. этапа", "% of previous stage"),
    "Конверсія рахується лише з реальних даних; якщо на попередньому етапі 0 — показується без %.": (
        "Конверсия считается только по реальным данным; если на предыдущем этапе 0 — показывается без %.",
        "Conversion uses real data only; if the previous stage is 0, no % is shown."),
    "Додані ліди": ("Добавленные лиды", "Leads added"),
    "Кому написали": ("Кому написали", "Contacted"),
    "Отримано відповідей": ("Получено ответов", "Replies received"),
    "Зацікавлені": ("Заинтересованные", "Interested"),
    "Дзвінки": ("Звонки", "Calls"),
    "Підписані договори": ("Подписанные договоры", "Contracts signed"),
    "📊 Динаміка воронки •": ("📊 Динамика воронки •", "📊 Funnel dynamics •"),
    "Платформа:": ("Платформа:", "Platform:"),
    "🔴 Nintendo eShop": ("🔴 Nintendo eShop", "🔴 Nintendo eShop"),
    "🌐 Всі консолі (Switch + Xbox)": ("🌐 Все консоли (Switch + Xbox)", "🌐 All consoles (Switch + Xbox)"),
    "Немає даних помісячного звіту для цієї платформи. Перевір посилання на звіт.": (
        "Нет данных помесячного отчёта для этой платформы. Проверь ссылку на отчёт.",
        "No monthly report data for this platform. Check the report link."),
    "Місяці (з фільтра періоду, можна змінити):": ("Месяцы (из фильтра периода, можно изменить):", "Months (from the period filter, editable):"),
    "ℹ️ За обраним періодом у звіті місяців немає — показано останній. Доступно:": (
        "ℹ️ За выбранный период в отчёте месяцев нет — показан последний. Доступно:",
        "ℹ️ The report has no months in the selected period — showing the latest. Available:"),
    "Виторг (": ("Выручка (", "Revenue ("),
    "міс.": ("мес.", "mo."),
    "Активних тайтлів": ("Активных тайтлов", "Active titles"),
    "З продажами": ("С продажами", "With sales"),
    "Лідер періоду": ("Лидер периода", "Period leader"),
    "Каса платформи All-Time": ("Касса платформы All-Time", "Platform gross All-Time"),
    "Повна база": ("Полная база", "Full base"),
    "🏆 Топ-10 за період (": ("🏆 Топ-10 за период (", "🏆 Top-10 for the period ("),
    "Назва гри / DLC": ("Название игры / DLC", "Game / DLC"),
    "Виторг за період ($)": ("Выручка за период ($)", "Period revenue ($)"),
    "Частка (%)": ("Доля (%)", "Share (%)"),
    "📥 Звіт за період (.CSV)": ("📥 Отчёт за период (.CSV)", "📥 Period report (.CSV)"),
    "🔥 Теплова карта виторгу (топ-20)": ("🔥 Тепловая карта выручки (топ-20)", "🔥 Revenue heatmap (top-20)"),
    "Шкала:": ("Шкала:", "Scale:"),
    "💵 Абсолютні $": ("💵 Абсолютные $", "💵 Absolute $"),
    "📐 Сезонність (% від піку гри)": ("📐 Сезонность (% от пика игры)", "📐 Seasonality (% of game's peak)"),
    "% від найкращого місяця гри": ("% от лучшего месяца игры", "% of the game's best month"),
    "% піку": ("% пика", "% of peak"),
    "Кожен рядок масштабовано до найкращого місяця цієї гри (= 100%) — видно сезонність і згасання кожного тайтлу, незалежно від його розміру. Абсолютні суми — у підказці.": (
        "Каждая строка масштабирована к лучшему месяцу этой игры (= 100%) — видна сезонность и затухание каждого тайтла, независимо от его размера. Абсолютные суммы — в подсказке.",
        "Each row is scaled to the game's best month (= 100%) — showing seasonality and decay of every title regardless of size. Absolute amounts are in the tooltip."),
    "📈 Тренд окремої гри": ("📈 Тренд отдельной игры", "📈 Single game trend"),
    "Гра:": ("Игра:", "Game:"),
    "Місяць": ("Месяц", "Month"),
    "📑 Повна помісячна матриця за всі місяці": ("📑 Полная помесячная матрица за все месяцы", "📑 Full monthly matrix (all months)"),
    "Всього ($)": ("Всего ($)", "Total ($)"),
    "📥 Повна матриця (.CSV)": ("📥 Полная матрица (.CSV)", "📥 Full matrix (.CSV)"),

    # ---------- Календар ----------
    "📅 Календар релізів і розпродажів": ("📅 Календарь релизов и распродаж", "📅 Releases & sales calendar"),
    "Релізи портфоліо й пайплайну, сейли Nintendo/Xbox і дедлайни подачі — плюс інструменти підготовки сейлів": (
        "Релизы портфолио и пайплайна, сейлы Nintendo/Xbox и дедлайны подачи — плюс инструменты подготовки сейлов",
        "Portfolio and pipeline releases, Nintendo/Xbox sales and submission deadlines — plus sale preparation tools"),
    "📅 Календар": ("📅 Календарь", "📅 Calendar"),
    "🔴 Сейл Nintendo (bookmarklet)": ("🔴 Сейл Nintendo (bookmarklet)", "🔴 Nintendo sale (bookmarklet)"),
    "🟢 Сейл Xbox (подача)": ("🟢 Сейл Xbox (подача)", "🟢 Xbox sale (submission)"),
    "🗓️ Місяць:": ("🗓️ Месяц:", "🗓️ Month:"),
    "Фільтр:": ("Фильтр:", "Filter:"),
    "Всі події": ("Все события", "All events"),
    "🎮 Релізи": ("🎮 Релизы", "🎮 Releases"),
    "🏷️ Сейли й дедлайни": ("🏷️ Сейлы и дедлайны", "🏷️ Sales & deadlines"),
    "Вигляд:": ("Вид:", "View:"),
    "📅 Місяць": ("📅 Месяц", "📅 Month"),
    "📊 Таймлайн 90 днів": ("📊 Таймлайн 90 дней", "📊 90-day timeline"),
    "📋 Список (Agenda)": ("📋 Список (Agenda)", "📋 Agenda"),
    "Релізи": ("Релизы", "Releases"),
    "Nintendo сейли": ("Nintendo сейлы", "Nintendo sales"),
    "Xbox сейли": ("Xbox сейлы", "Xbox sales"),
    "Дедлайни подачі": ("Дедлайны подачи", "Submission deadlines"),
    "Пн": ("Пн", "Mon"), "Вт": ("Вт", "Tue"), "Ср": ("Ср", "Wed"), "Чт": ("Чт", "Thu"),
    "Пт": ("Пт", "Fri"), "Сб": ("Сб", "Sat"), "Нд": ("Вс", "Sun"),
    "+ ще": ("+ ещё", "+ more"),
    "🎮 Реліз:": ("🎮 Релиз:", "🎮 Release:"),
    "🎮 Реліз": ("🎮 Релиз", "🎮 Release"),
    "🚀 Реліз NSW:": ("🚀 Релиз NSW:", "🚀 NSW release:"),
    "Вихід гри": ("Выход игры", "Release of"),
    "на консолях": ("на консолях", "on consoles"),
    "Плановий вихід порту (розробник:": ("Плановый выход порта (разработчик:", "Planned port release (developer:"),
    "Розпродаж Nintendo eShop (": ("Распродажа Nintendo eShop (", "Nintendo eShop sale ("),
    "⏰ ДЕДЛАЙН:": ("⏰ ДЕДЛАЙН:", "⏰ DEADLINE:"),
    "Крайній строк подачі в Microsoft.": ("Крайний срок подачи в Microsoft.", "Microsoft submission deadline."),
    "Знижка 65% або більше. Ліміт: до 10 тайтлів.": ("Скидка 65% или больше. Лимит: до 10 тайтлов.", "Discount of 65% or more. Limit: up to 10 titles."),
    "Базова ціна від $9.99. Ліміт: до 5 тайтлів. Кулдаун знято тільки між BF та Countdown.": (
        "Базовая цена от $9.99. Лимит: до 5 тайтлов. Кулдаун снят только между BF и Countdown.",
        "Base price from $9.99. Limit: up to 5 titles. Cooldown waived only between BF and Countdown."),
    "Базова ціна від $9.99. Ліміт: до 5 тайтлів.": ("Базовая цена от $9.99. Лимит: до 5 тайтлов.", "Base price from $9.99. Limit: up to 5 titles."),
    "ID Sale (Глибокі знижки)": ("ID Sale (Глубокие скидки)", "ID Sale (Deep discounts)"),
    "Наведи на смугу, щоб побачити дати й опис • ◂ ▸ — подія триває з попереднього / на наступний тиждень": (
        "Наведи на полосу, чтобы увидеть даты и описание • ◂ ▸ — событие продолжается с предыдущей / на следующую неделю",
        "Hover over a bar to see dates and details • ◂ ▸ — event continues from the previous / into the next week"),
    "Від тижня тому до +90 днів від сьогодні • вибір місяця тут не діє": (
        "От недели назад до +90 дней от сегодня • выбор месяца здесь не действует",
        "From a week ago to +90 days from today • month selection does not apply here"),
    "💡 Найближчі 90 днів подій немає.": ("💡 В ближайшие 90 дней событий нет.", "💡 No events in the next 90 days."),
    "💡 У цьому місяці немає подій.": ("💡 В этом месяце нет событий.", "💡 No events this month."),
    "🔥 СЬОГОДНІ": ("🔥 СЕГОДНЯ", "🔥 TODAY"),
    "🔥 Йде зараз": ("🔥 Идёт сейчас", "🔥 Live now"),
    "⏳ Через": ("⏳ Через", "⏳ In"),
    "🗓️ Через": ("🗓️ Через", "🗓️ In"),
    "Минуло": ("Прошло", "Ended"),
    "дн. тому": ("дн. назад", "days ago"),
    "✔️ Завершився": ("✔️ Завершился", "✔️ Ended"),
    "⏳ Залишилось": ("⏳ Осталось", "⏳ Left:"),
    "🚨 Дедлайн СЬОГОДНІ!": ("🚨 Дедлайн СЕГОДНЯ!", "🚨 Deadline TODAY!"),
    "✖️ Минув": ("✖️ Прошёл", "✖️ Passed"),
    "🎮 Реліз": ("🎮 Релиз", "🎮 Release"),
    "🔴 Nintendo сейл": ("🔴 Nintendo сейл", "🔴 Nintendo sale"),
    "🟢 Xbox сейл": ("🟢 Xbox сейл", "🟢 Xbox sale"),
    "⏰ Дедлайн подачі": ("⏰ Дедлайн подачи", "⏰ Submission deadline"),
    "Подія": ("Событие", "Event"),
    "Дати": ("Даты", "Dates"),
    "Опис": ("Описание", "Description"),
    "Сейл": ("Сейл", "Sale"),
    "Початок": ("Начало", "Start"),
    "Кінець": ("Конец", "End"),
    "Статус": ("Статус", "Status"),
    "🔴 Підготовка розпродажу Nintendo eShop": ("🔴 Подготовка распродажи Nintendo eShop", "🔴 Nintendo eShop sale preparation"),
    "Сейл:": ("Сейл:", "Sale:"),
    "⚪ Немає дати релізу": ("⚪ Нет даты релиза", "⚪ No release date"),
    "⏳ Вийде після старту сейлу": ("⏳ Выйдет после старта сейла", "⏳ Releases after sale start"),
    "🟢 Готова": ("🟢 Готова", "🟢 Ready"),
    "🟡 Кулдаун (ще": ("🟡 Кулдаун (ещё", "🟡 Cooldown (left:"),
    "дн.)": ("дн.)", "days)"),
    "Включити": ("Включить", "Include"),
    "Включити в сейл": ("Включить в сейл", "Include in sale"),
    "Знижка (%)": ("Скидка (%)", "Discount (%)"),
    "Дата релізу": ("Дата релиза", "Release date"),
    "Обрано ігор:": ("Выбрано игр:", "Games selected:"),
    "⚡ Згенерувати Bookmarklet для Nintendo": ("⚡ Сгенерировать Bookmarklet для Nintendo", "⚡ Generate Nintendo bookmarklet"),
    "Оберіть хоча б одну гру галочкою!": ("Отметьте хотя бы одну игру галочкой!", "Tick at least one game!"),
    "🎉 Bookmarklet згенеровано для": ("🎉 Bookmarklet сгенерирован для", "🎉 Bookmarklet generated for"),
    "##### 📌 Код закладки:": ("##### 📌 Код закладки:", "##### 📌 Bookmark code:"),
    "##### 📋 Список назв:": ("##### 📋 Список названий:", "##### 📋 Title list:"),
    "Назви ігор:": ("Названия игр:", "Game titles:"),
    "Букмарклет враховує правила eShop: для Данії та ПАР ціни кратні 0.25, ціни в песо Чилі й Колумбії — цілі числа, а в країнах Америки ціна не опускається нижче мінімуму Nintendo (тоді знижка буде меншою за задану).": (
        "Букмарклет учитывает правила eShop: для Дании и ЮАР цены кратны 0.25, цены в песо Чили и Колумбии — целые числа, а в странах Америки цена не опускается ниже минимума Nintendo (тогда скидка будет меньше заданной).",
        "The bookmarklet follows eShop rules: prices in Denmark and South Africa are multiples of 0.25, Chilean and Colombian peso prices are whole numbers, and in the Americas the price never goes below Nintendo's minimum (the discount is then smaller than the target)."),
    "🟢 Подача на розпродажі Xbox": ("🟢 Подача на распродажи Xbox", "🟢 Xbox sale submission"),
    "— дедлайн": ("— дедлайн", "— deadline"),
    "🎯 Розпродаж": ("🎯 Распродажа", "🎯 Sale"),
    "🔒 Ліміт тайтлів": ("🔒 Лимит тайтлов", "🔒 Title limit"),
    "до": ("до", "up to"),
    "💡 **Вимоги Microsoft:**": ("💡 **Требования Microsoft:**", "💡 **Microsoft requirements:**"),
    "🟢 Проходить": ("🟢 Проходит", "🟢 Eligible"),
    "🔴 Не підходить (": ("🔴 Не подходит (", "🔴 Not eligible ("),
    "ціна $": ("цена $", "price $"),
    "Подати": ("Подать", "Submit"),
    "Подати в Microsoft": ("Подать в Microsoft", "Submit to Microsoft"),
    "Базова ціна ($)": ("Базовая цена ($)", "Base price ($)"),
    "Ціна на сейлі ($)": ("Цена на сейле ($)", "Sale price ($)"),
    "Вимоги": ("Требования", "Requirements"),
    "⚠️ Обрано": ("⚠️ Выбрано", "⚠️ Selected"),
    "ігор, а ліміт сейлу —": ("игр, а лимит сейла —", "games, but the sale limit is"),
    ". Зніми зайві галочки.": (". Сними лишние галочки.", ". Untick the extras."),
    "Обрано": ("Выбрано", "Selected"),
    "можливих.": ("возможных.", "allowed."),
    "📥 Список для подачі (.CSV)": ("📥 Список для подачи (.CSV)", "📥 Submission list (.CSV)"),

    # ---------- Релізи ----------
    "🚀 Релізи: сертифікація, команда та маркетинг": ("🚀 Релизы: сертификация, команда и маркетинг", "🚀 Releases: certification, team & marketing"),
    "Лист": ("Лист", "Sheet"),
    "+ маркетинговий чек-лист • Контроль швидкості портування та готовності до релізу": (
        "+ маркетинговый чек-лист • Контроль скорости портирования и готовности к релизу",
        "+ marketing checklist • Porting speed and release readiness control"),
    "⚠️ Не вдалося завантажити лист": ("⚠️ Не удалось загрузить лист", "⚠️ Could not load sheet"),
    ". Перевір назву листа в Google Таблиці.": (". Проверь название листа в Google Таблице.", ". Check the sheet name in Google Sheets."),
    "Всього тайтлів": ("Всего тайтлов", "Total titles"),
    "Лист Certification": ("Лист Certification", "Certification sheet"),
    "Білдів завантажено": ("Билдов загружено", "Builds uploaded"),
    "Готові до сабміту": ("Готовы к сабмиту", "Ready for submission"),
    "Зараз у роботі": ("Сейчас в работе", "In progress now"),
    "Включно з простроченими": ("Включая просроченные", "Including overdue"),
    "Зриви дедлайнів": ("Срывы дедлайнов", "Missed deadlines"),
    "Затримка / Прострочено": ("Задержка / Просрочено", "Delayed / Overdue"),
    "Вчасність здачі": ("Своевременность сдачи", "On-time delivery"),
    "🚨 Критичні зриви:": ("🚨 Критические срывы:", "🚨 Critical slips:"),
    "білд(ів) прострочено й досі не завантажено": ("билд(ов) просрочено и до сих пор не загружено", "build(s) overdue and still not uploaded"),
    "(Розробник:": ("(Разработчик:", "(Developer:"),
    "План фінішу був": ("План финиша был", "Planned finish was"),
    "Старт:": ("Старт:", "Start:"),
    "• Вердикт:": ("• Вердикт:", "• Verdict:"),
    "📋 Трекер і дедлайни": ("📋 Трекер и дедлайны", "📋 Tracker & deadlines"),
    "👨\u200d💻 Команда: KPI": ("👨\u200d💻 Команда: KPI", "👨\u200d💻 Team KPI"),
    "📅 Roadmap": ("📅 Roadmap", "📅 Roadmap"),
    "📣 Маркетинг-готовність": ("📣 Маркетинг-готовность", "📣 Marketing readiness"),
    "Немає даних сертифікації.": ("Нет данных сертификации.", "No certification data."),
    "Розробник:": ("Разработчик:", "Developer:"),
    "Всі розробники": ("Все разработчики", "All developers"),
    "Не призначено": ("Не назначено", "Unassigned"),
    "Етап:": ("Этап:", "Stage:"),
    "Всі": ("Все", "All"),
    "🟢 Завантажені": ("🟢 Загруженные", "🟢 Uploaded"),
    "⏳ В роботі": ("⏳ В работе", "⏳ In progress"),
    "🚨 Затримка / прострочка": ("🚨 Задержка / просрочка", "🚨 Delayed / overdue"),
    "⚪ В черзі": ("⚪ В очереди", "⚪ Queued"),
    "Розробник": ("Разработчик", "Developer"),
    "Вердикт": ("Вердикт", "Verdict"),
    "Дата старту": ("Дата старта", "Start date"),
    "План здачі білда": ("План сдачи билда", "Planned build delivery"),
    "Дата завантаження білда": ("Дата загрузки билда", "Build upload date"),
    "Реліз Nintendo": ("Релиз Nintendo", "Nintendo release"),
    "План (дн)": ("План (дн)", "Plan (days)"),
    "Факт (дн)": ("Факт (дн)", "Actual (days)"),
    "Відхилення (дн)": ("Отклонение (дн)", "Deviation (days)"),
    "Відхилення (днів)": ("Отклонение (дней)", "Deviation (days)"),
    "Маркетинг (%)": ("Маркетинг (%)", "Marketing (%)"),
    "🟢 Білд завантажено": ("🟢 Билд загружен", "🟢 Build uploaded"),
    "🟢 Вчасно здано": ("🟢 Сдано вовремя", "🟢 Delivered on time"),
    "🔴 Затримка (+": ("🔴 Задержка (+", "🔴 Delayed (+"),
    "🚨 Прострочено (+": ("🚨 Просрочено (+", "🚨 Overdue (+"),
    "⏳ В розробці (у плані)": ("⏳ В разработке (по плану)", "⏳ In development (on plan)"),
    "дн)": ("дн)", "d)"),
    "📥 Експортувати реєстр (.CSV)": ("📥 Экспортировать реестр (.CSV)", "📥 Export register (.CSV)"),
    "⏳ План vs Факт по здачі білдів": ("⏳ План vs Факт по сдаче билдов", "⏳ Plan vs actual build delivery"),
    "Ті самі фільтри, що й у таблиці • Червоне = затримка, зелене = вчасно або раніше": (
        "Те же фильтры, что и в таблице • Красное = задержка, зелёное = вовремя или раньше",
        "Same filters as the table • Red = delayed, green = on time or early"),
    "Для обраного фільтра ще немає зданих білдів із планом і фактом.": (
        "Для выбранного фильтра ещё нет сданных билдов с планом и фактом.",
        "No delivered builds with plan and actual for this filter yet."),
    "дн": ("дн", "d"),
    "Проєкт потрапляє в період за датою плану здачі (або завантаження / старту) • У вибірці:": (
        "Проект попадает в период по дате плана сдачи (или загрузки / старта) • В выборке:",
        "A project falls into a period by its planned delivery (or upload / start) date • In selection:"),
    "За цей період немає проєктів із призначеним розробником.": ("За этот период нет проектов с назначенным разработчиком.", "No projects with an assigned developer in this period."),
    "##### 📊 Завантаження команди (": ("##### 📊 Загрузка команды (", "##### 📊 Team workload ("),
    "##### 📋 KPI розробників (": ("##### 📋 KPI разработчиков (", "##### 📋 Developer KPI ("),
    "Здано": ("Сдано", "Delivered"),
    "В роботі": ("В работе", "In progress"),
    "Прострочено": ("Просрочено", "Overdue"),
    "В черзі": ("В очереди", "Queued"),
    "Всього ігор": ("Всего игр", "Total games"),
    "Здано білдів": ("Сдано билдов", "Builds delivered"),
    "Сер. план (дн)": ("Ср. план (дн)", "Avg plan (days)"),
    "Сер. факт (дн)": ("Ср. факт (дн)", "Avg actual (days)"),
    "Сер. відхилення (дн)": ("Ср. отклонение (дн)", "Avg deviation (days)"),
    "% вчасно": ("% вовремя", "% on time"),
    "⚪ Немає проєктів": ("⚪ Нет проектов", "⚪ No projects"),
    "🟢 Топ-перформер": ("🟢 Топ-перформер", "🟢 Top performer"),
    "🟡 Норма": ("🟡 Норма", "🟡 Normal"),
    "🔴 Зона ботлнеку": ("🔴 Зона ботлнека", "🔴 Bottleneck"),
    "ℹ️ Як рахується KPI": ("ℹ️ Как считается KPI", "ℹ️ How KPI is calculated"),
    "- **45 балів** — частка зданих білдів від усіх ігор розробника за період": (
        "- **45 баллов** — доля сданных билдов от всех игр разработчика за период",
        "- **45 points** — share of delivered builds out of the developer's games in the period"),
    "- **35 балів** — % здач вчасно (якщо зданих ще немає — нейтральні 25)": (
        "- **35 баллов** — % сдач вовремя (если сданных ещё нет — нейтральные 25)",
        "- **35 points** — % delivered on time (neutral 25 if nothing delivered yet)"),
    "- **+20** базових балів": ("- **+20** базовых баллов", "- **+20** base points"),
    "- **−2** за кожен день середньої затримки, **−5** за кожну гру, прострочену зараз": (
        "- **−2** за каждый день средней задержки, **−5** за каждую игру, просроченную сейчас",
        "- **−2** per day of average delay, **−5** per currently overdue game"),
    "📅 Графік зайнятості та план здачі ігор": ("📅 График занятости и план сдачи игр", "📅 Workload schedule & delivery plan"),
    "Жовта лінія — сьогодні • Повзунок унизу — масштабування": ("Жёлтая линия — сегодня • Ползунок внизу — масштабирование", "Yellow line — today • Slider below — zoom"),
    "Немає даних із датами для побудови графіка.": ("Нет данных с датами для построения графика.", "No dated data to build the chart."),
    "🟢 Здано вчасно": ("🟢 Сдано вовремя", "🟢 Delivered on time"),
    "🔴 Здано з затримкою": ("🔴 Сдано с задержкой", "🔴 Delivered late"),
    "🚨 Прострочено": ("🚨 Просрочено", "🚨 Overdue"),
    "🔵 В роботі": ("🔵 В работе", "🔵 In progress"),
    "🟣 Заплановано": ("🟣 Запланировано", "🟣 Planned"),
    "Старт": ("Старт", "Start"),
    "Тривалість": ("Длительность", "Duration"),
    "СЬОГОДНІ (": ("СЕГОДНЯ (", "TODAY ("),
    "📣 Маркетингова готовність до релізів": ("📣 Маркетинговая готовность к релизам", "📣 Marketing readiness for releases"),
    "⚠️ Не вдалося завантажити маркетинговий чек-лист. Перевір `ACTIVITY_SHEET_URL`.": (
        "⚠️ Не удалось загрузить маркетинговый чек-лист. Проверь `ACTIVITY_SHEET_URL`.",
        "⚠️ Could not load the marketing checklist. Check `ACTIVITY_SHEET_URL`."),
    "🎮 Ігор у трекері": ("🎮 Игр в трекере", "🎮 Games in tracker"),
    "🛠️ В роботі": ("🛠️ В работе", "🛠️ In progress"),
    "Підготовка": ("Подготовка", "Preparation"),
    "🟢 Випущено": ("🟢 Выпущено", "🟢 Released"),
    "📊 Середня готовність": ("📊 Средняя готовность", "📊 Average readiness"),
    "По всій базі": ("По всей базе", "Across all"),
    "реліз через": ("релиз через", "release in"),
    "дн., маркетинг готовий на": ("дн., маркетинг готов на", "days, marketing ready at"),
    "Не закрито:": ("Не закрыто:", "Open items:"),
    "##### 🧩 Матриця «гра × активність»": ("##### 🧩 Матрица «игра × активность»", "##### 🧩 «Game × activity» matrix"),
    "Показати:": ("Показать:", "Show:"),
    "🟡 Тільки в роботі": ("🟡 Только в работе", "🟡 In progress only"),
    "Всі ігри": ("Все игры", "All games"),
    "Немає ігор для відображення.": ("Нет игр для отображения.", "No games to show."),
    "без дати": ("без даты", "no date"),
    "✅ Зроблено": ("✅ Сделано", "✅ Done"),
    "🚨 Не зроблено — реліз": ("🚨 Не сделано — релиз", "🚨 Not done — release"),
    "⬜ Не зроблено": ("⬜ Не сделано", "⬜ Not done"),
    "через": ("через", "in"),
    "🟩 зроблено • ⬛ не зроблено • 🟥 не зроблено, а реліз ближче ніж": (
        "🟩 сделано • ⬛ не сделано • 🟥 не сделано, а релиз ближе чем через",
        "🟩 done • ⬛ not done • 🟥 not done and release is closer than"),
    "дн. (або вже вийшла) • рядки відсортовано за датою релізу": (
        "дн. (или уже вышла) • строки отсортированы по дате релиза",
        "days (or already out) • rows sorted by release date"),
    "Найчастіше не закрито:": ("Чаще всего не закрыто:", "Most often missing:"),
    "📑 Таблиця чек-листа": ("📑 Таблица чек-листа", "📑 Checklist table"),
    "Готовність": ("Готовность", "Readiness"),
    "Готовність (%)": ("Готовность (%)", "Readiness (%)"),
    "📥 Експортувати звіт активностей (.CSV)": ("📥 Экспортировать отчёт активностей (.CSV)", "📥 Export activity report (.CSV)"),

    # ---------- Прогнози та ліди ----------
    "Оцінка нових лідів за 30 піджанрами, пайплайн лідів і перевірка точності моделі на випущених іграх": (
        "Оценка новых лидов по 30 поджанрам, пайплайн лидов и проверка точности модели на вышедших играх",
        "New lead scoring across 30 sub-genres, lead pipeline and model accuracy check on released games"),
    "🧮 Калькулятор ліда": ("🧮 Калькулятор лида", "🧮 Lead calculator"),
    "📋 Пайплайн лідів": ("📋 Пайплайн лидов", "📋 Lead pipeline"),
    "🎯 Точність моделі (план vs факт M1)": ("🎯 Точность модели (план vs факт M1)", "🎯 Model accuracy (plan vs actual M1)"),
    "#### 1. Вхідні дані ліда": ("#### 1. Входные данные лида", "#### 1. Lead inputs"),
    "Назва гри / ліда:": ("Название игры / лида:", "Game / lead name:"),
    "🔗 Посилання на гру (Steam / GP / itch / Web):": ("🔗 Ссылка на игру (Steam / GP / itch / Web):", "🔗 Game link (Steam / GP / itch / Web):"),
    "Джерело аналізу:": ("Источник анализа:", "Source for analysis:"),
    "Steam All-Time Revenue ($):": ("Steam All-Time Revenue ($):", "Steam All-Time Revenue ($):"),
    "Завантаження Google Play (Installs):": ("Загрузки Google Play (Installs):", "Google Play installs:"),
    "Кількість відгуків / оцінок:": ("Количество отзывов / оценок:", "Number of reviews / ratings:"),
    "Оцінки itch.io:": ("Оценки itch.io:", "itch.io ratings:"),
    "#### 2. Жанр і ціна": ("#### 2. Жанр и цена", "#### 2. Genre & price"),
    "Точний піджанр гри:": ("Точный поджанр игры:", "Exact sub-genre:"),
    "Планова ціна на консолях ($):": ("Плановая цена на консолях ($):", "Planned console price ($):"),
    "### 📈 Розрахунок:": ("### 📈 Расчёт:", "### 📈 Estimate:"),
    "Органічна база: **$": ("Органическая база: **$", "Organic base: **$"),
    "Ціновий множник:": ("Ценовой множитель:", "Price multiplier:"),
    "Частка студії:": ("Доля студии:", "Studio share:"),
    "(з налаштувань P&L)": ("(из настроек P&L)", "(from P&L settings)"),
    "🟢 **ТОП ЛІД:** рекомендовано надсилати пітч (M1 > $6.5k)": ("🟢 **ТОП ЛИД:** рекомендуется отправлять питч (M1 > $6.5k)", "🟢 **TOP LEAD:** send a pitch (M1 > $6.5k)"),
    "🟡 **СТАНДАРТНИЙ ТАЙТЛ:** стабільний кандидат ($3k–$6.5k)": ("🟡 **СТАНДАРТНЫЙ ТАЙТЛ:** стабильный кандидат ($3k–$6.5k)", "🟡 **STANDARD TITLE:** solid candidate ($3k–$6.5k)"),
    "🔴 **ВИСОКИЙ РИЗИК:** низька прогнозована каса (M1 < $3k)": ("🔴 **ВЫСОКИЙ РИСК:** низкая прогнозируемая касса (M1 < $3k)", "🔴 **HIGH RISK:** low projected revenue (M1 < $3k)"),
    "Студії:": ("Студии:", "Studio:"),
    "➕ Зберегти лід (у таблицю та Google Sheets)": ("➕ Сохранить лид (в таблицу и Google Sheets)", "➕ Save lead (table & Google Sheets)"),
    "🚀 Записано в Google Таблицю (лист Leads)!": ("🚀 Записано в Google Таблицу (лист Leads)!", "🚀 Saved to Google Sheets (Leads sheet)!"),
    "⚠️ Webhook відповів": ("⚠️ Webhook ответил", "⚠️ Webhook returned"),
    ", лід збережено локально": (", лид сохранён локально", ", lead saved locally"),
    "Збережено локально. Помилка webhook:": ("Сохранено локально. Ошибка webhook:", "Saved locally. Webhook error:"),
    "✅ Лід": ("✅ Лид", "✅ Lead"),
    "збережено!": ("сохранён!", "saved!"),
    "📋 Пайплайн нових лідів": ("📋 Пайплайн новых лидов", "📋 New lead pipeline"),
    "💡 Лідів поки немає. Розрахуй гру в калькуляторі та натисни «➕ Зберегти лід».": (
        "💡 Лидов пока нет. Рассчитай игру в калькуляторе и нажми «➕ Сохранить лид».",
        "💡 No leads yet. Estimate a game in the calculator and press «➕ Save lead»."),
    "З Google Sheets:": ("Из Google Sheets:", "From Google Sheets:"),
    "Додано в цій сесії:": ("Добавлено в этой сессии:", "Added this session:"),
    "(ще не підтягнулись із таблиці)": ("(ещё не подтянулись из таблицы)", "(not yet synced from the sheet)"),
    "Зібрано лідів": ("Собрано лидов", "Leads collected"),
    "Потенціал Gross M1": ("Потенциал Gross M1", "Gross M1 potential"),
    "Очікуваний дохід студії (": ("Ожидаемый доход студии (", "Expected studio revenue ("),
    "Відкрити ↗": ("Открыть ↗", "Open ↗"),
    "📥 Експортувати ліди (.CSV)": ("📥 Экспортировать лиды (.CSV)", "📥 Export leads (.CSV)"),
    "🗑️ Очистити ліди цієї сесії": ("🗑️ Очистить лиды этой сессии", "🗑️ Clear this session's leads"),
    "Дата": ("Дата", "Date"),
    "Назва гри": ("Название игры", "Game"),
    "Посилання": ("Ссылка", "Link"),
    "Джерело": ("Источник", "Source"),
    "Жанр": ("Жанр", "Genre"),
    "Ціна ($)": ("Цена ($)", "Price ($)"),
    "Рекомендація": ("Рекомендация", "Recommendation"),
    "✅ ТОП ЛІД": ("✅ ТОП ЛИД", "✅ TOP LEAD"),
    "⚠️ СТАНДАРТ": ("⚠️ СТАНДАРТ", "⚠️ STANDARD"),
    "❌ РИЗИК": ("❌ РИСК", "❌ RISK"),
    "🎯 Точність прогнозу M1 на випущених іграх": ("🎯 Точность прогноза M1 на вышедших играх", "🎯 M1 forecast accuracy on released games"),
    "Та сама формула, що й у калькуляторі: база з джерела × жанровий коефіцієнт × ціновий множник": (
        "Та же формула, что и в калькуляторе: база из источника × жанровый коэффициент × ценовой множитель",
        "Same formula as the calculator: source base × genre coefficient × price multiplier"),
    "🟢 Перевищила план": ("🟢 Превысила план", "🟢 Beat the plan"),
    "🔴 Нижче плану": ("🔴 Ниже плана", "🔴 Below plan"),
    "🟡 У плані (±25%)": ("🟡 В плане (±25%)", "🟡 On plan (±25%)"),
    "⚪ Немає вхідних метрик": ("⚪ Нет входных метрик", "⚪ No input metrics"),
    "⚪ Немає факту M1": ("⚪ Нет факта M1", "⚪ No actual M1"),
    "Жанр (модель)": ("Жанр (модель)", "Genre (model)"),
    "Платформи": ("Платформы", "Platforms"),
    "Факт M1 ($)": ("Факт M1 ($)", "Actual M1 ($)"),
    "Прогноз M1 ($)": ("Прогноз M1 ($)", "Forecast M1 ($)"),
    "Різниця ($)": ("Разница ($)", "Difference ($)"),
    "Точність (%)": ("Точность (%)", "Accuracy (%)"),
    "Середня точність моделі": ("Средняя точность модели", "Average model accuracy"),
    "🟢 Перевищили план": ("🟢 Превысили план", "🟢 Beat the plan"),
    "🟡 У межах (±25%)": ("🟡 В пределах (±25%)", "🟡 Within (±25%)"),
    "🔴 Нижче прогнозу": ("🔴 Ниже прогноза", "🔴 Below forecast"),

    # ---------- Описи жанрів (калькулятор) ----------
    "Drug Dealer Empire (Xbox феномен)": ("Drug Dealer Empire (Xbox феномен)", "Drug Dealer Empire (Xbox phenomenon)"),
    "My Supermarket Simulator (Лідер на Switch)": ("My Supermarket Simulator (Лидер на Switch)", "My Supermarket Simulator (Switch leader)"),
    "Монополія аудиторії Nintendo": ("Монополия аудитории Nintendo", "Nintendo audience stronghold"),
    "🔴 Paperly, Fly for Fly (Зона низької конверсії)": ("🔴 Paperly, Fly for Fly (Зона низкой конверсии)", "🔴 Paperly, Fly for Fly (low conversion zone)"),
    "Skinwalker, TROX, Is Today Another Day (Xbox домінує)": ("Skinwalker, TROX, Is Today Another Day (Xbox доминирует)", "Skinwalker, TROX, Is Today Another Day (Xbox dominates)"),
    "Exit 8, Don't Scream (PS попит)": ("Exit 8, Don't Scream (спрос на PS)", "Exit 8, Don't Scream (PS demand)"),
    "Packit List, Unpacking-вайб": ("Packit List, Unpacking-вайб", "Packit List, Unpacking vibe"),

    # ---------- Імена розробників ----------
    "Сергій": ("Сергей", "Serhii"), "Ігор": ("Игорь", "Ihor"), "Іван": ("Иван", "Ivan"),
    "Максим": ("Максим", "Maksym"), "Дмитро": ("Дмитрий", "Dmytro"), "Влад": ("Влад", "Vlad"),

    # ---------- Одиниці та дрібні слова ----------
    "ігор": ("игр", "games"),
    "дн. тому": ("дн. назад", "days ago"),
    "дн.": ("дн.", "days"),
    "ще": ("ещё", "left:"),
    "з": ("из", "of"),
}


# ==============================================================================
# 🌐 3.1 МОВИ ІНТЕРФЕЙСУ (UA / RU / EN)
# ==============================================================================
# Код і дані лишаються українською. Переклад робиться «на виході»: усе, що Streamlit показує на екрані
# (заголовки, кнопки, вкладки, таблиці, графіки Plotly, HTML-картки), проганяється через словник TR.
# Щоб додати / виправити переклад — достатньо змінити TR внизу файлу, логіку чіпати не треба.
import functools
import streamlit.delta_generator as _st_dg

LANGS = {"uk": "🇺🇦 Українська", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
LANG_NAMES_FOR_AI = {"uk": "українською мовою", "ru": "на русском языке", "en": "in English"}
MONTHS_I18N = {
    "ru": ["", "Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"],
    "en": ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}
_CYR = re.compile(r"[А-Яа-яІіЇїЄєҐґЁёЪъЫыЭэ]")
_MONTH_RE = re.compile(r"(?<![\w])(" + "|".join(UKR_MONTH_NAMES[1:]) + r")(?=\s+\d{4})")
_TR_STATE = {"regex": None, "lookup": {}, "lang": None}
_IN_TR = {"depth": 0}


def cur_lang():
    lang = st.session_state.get("lang", "uk")
    return lang if lang in LANGS else "uk"


def _phrase_regex(lang):
    if _TR_STATE["lang"] != lang:
        idx = 0 if lang == "ru" else 1
        lookup = {k: v[idx] for k, v in TR.items()}
        keys = sorted(lookup, key=len, reverse=True)
        # межі слова перевіряємо лише там, де фраза починається / закінчується буквою чи цифрою
        alts = [(r"(?<!\w)" if re.match(r"\w", k) else "") + re.escape(k) + (r"(?!\w)" if re.search(r"\w$", k) else "")
                for k in keys]
        _TR_STATE.update(lang=lang, lookup=lookup, regex=re.compile("|".join(alts)) if alts else None)
    return _TR_STATE["regex"], _TR_STATE["lookup"]


@functools.lru_cache(maxsize=20000)
def _translate_cached(text, lang):
    text = _MONTH_RE.sub(lambda m: MONTHS_I18N[lang][UKR_MONTH_NAMES.index(m.group(1))], text)
    rx, lookup = _phrase_regex(lang)
    return rx.sub(lambda m: lookup.get(m.group(0), m.group(0)), text) if rx else text


def tr(text):
    """Перекладає рядок інтерфейсу на поточну мову (для української — без змін)."""
    if not isinstance(text, str) or not text:
        return text
    lang = cur_lang()
    if lang == "uk" or not _CYR.search(text):
        return text
    return _translate_cached(text, lang)


def _tr_deep(obj):
    if isinstance(obj, str):
        return tr(obj)
    if hasattr(obj, "dtype") and hasattr(obj, "tolist") and getattr(obj, "dtype", None) == object:  # numpy-масиви підписів у Plotly
        return type(obj)(_tr_deep(obj.tolist())) if not hasattr(obj, "shape") else __import__("numpy").array(_tr_deep(obj.tolist()), dtype=object)
    if isinstance(obj, list):
        return [_tr_deep(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_tr_deep(x) for x in obj)
    if isinstance(obj, dict):
        return {k: _tr_deep(v) for k, v in obj.items()}
    return obj


def _tr_df(df):
    """Копія DataFrame з перекладеними назвами колонок і текстовими значеннями + карта зворотних назв."""
    if not isinstance(df, pd.DataFrame) or cur_lang() == "uk":
        return df, {}
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_object_dtype(out[c]) or pd.api.types.is_string_dtype(out[c]):
            out[c] = out[c].map(lambda v: tr(v) if isinstance(v, str) else v)
    names = {c: tr(c) if isinstance(c, str) else c for c in out.columns}
    out = out.rename(columns=names)
    return out, {v: k for k, v in names.items()}


def _tr_column_config(cfg):
    if not cfg or cur_lang() == "uk":
        return cfg
    return {(tr(k) if isinstance(k, str) else k): (_tr_deep(v) if isinstance(v, dict) else v) for k, v in cfg.items()}


def _wrap_text(fn, pos=(0,), kws=("body", "label", "help", "placeholder", "value", "delta", "text")):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        if cur_lang() != "uk" and _IN_TR["depth"] == 0:
            args = list(args)
            for i in pos:
                if i < len(args):
                    args[i] = _tr_deep(args[i])
            for k in kws:
                if k in kwargs:
                    kwargs[k] = _tr_deep(kwargs[k])
        _IN_TR["depth"] += 1
        try:
            return fn(*args, **kwargs)
        finally:
            _IN_TR["depth"] -= 1
    return inner


def _wrap_choice(fn, off):
    """radio / selectbox / multiselect / select_slider: перекладаємо підпис і те, як показано варіанти; значення не змінюються."""
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        if cur_lang() != "uk":
            args = list(args)
            if len(args) > off:
                args[off] = tr(args[off])
            elif "label" in kwargs:
                kwargs["label"] = tr(kwargs["label"])
            orig = kwargs.get("format_func") or str
            kwargs["format_func"] = lambda o, _f=orig: tr(str(_f(o)))
            for k in ("help", "placeholder"):
                if k in kwargs:
                    kwargs[k] = tr(kwargs[k])
        return fn(*args, **kwargs)
    return inner


def _wrap_dataframe(fn, off):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        if cur_lang() != "uk":
            args = list(args)
            if len(args) > off:
                args[off], _ = _tr_df(args[off])
            elif "data" in kwargs:
                kwargs["data"], _ = _tr_df(kwargs["data"])
            if "column_config" in kwargs:
                kwargs["column_config"] = _tr_column_config(kwargs["column_config"])
        return fn(*args, **kwargs)
    return inner


def _wrap_data_editor(fn, off):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        if cur_lang() == "uk":
            return fn(*args, **kwargs)
        args = list(args)
        data = args[off] if len(args) > off else kwargs.get("data")
        shown, back = _tr_df(data)
        if len(args) > off:
            args[off] = shown
        else:
            kwargs["data"] = shown
        if "column_config" in kwargs:
            kwargs["column_config"] = _tr_column_config(kwargs["column_config"])
        if isinstance(kwargs.get("disabled"), (list, tuple)):
            kwargs["disabled"] = [tr(c) for c in kwargs["disabled"]]
        res = fn(*args, **kwargs)
        if isinstance(res, pd.DataFrame) and isinstance(data, pd.DataFrame):
            res = res.rename(columns=back)
            # повертаємо оригінальні (українські) текстові значення — логіка працює як раніше
            if len(res) == len(data):
                for c in data.columns:
                    if c in res.columns and (pd.api.types.is_object_dtype(data[c]) or pd.api.types.is_string_dtype(data[c])):
                        res[c] = data[c].values
        return res
    return inner


def _wrap_plotly(fn, off):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        if cur_lang() != "uk" and len(args) > off and isinstance(args[off], go.Figure):
            args = list(args)
            args[off] = go.Figure(_tr_deep(args[off].to_plotly_json()))
        return fn(*args, **kwargs)
    return inner


def _wrap_tabs(fn, off):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        if cur_lang() != "uk" and len(args) > off:
            args = list(args)
            args[off] = [tr(x) for x in args[off]]
        return fn(*args, **kwargs)
    return inner


_TEXT_METHODS = ["title", "header", "subheader", "caption", "markdown", "info", "warning", "success", "error",
                 "text", "button", "download_button", "checkbox", "toggle", "expander", "slider", "number_input",
                 "text_input", "text_area", "date_input", "toast"]
for _name in _TEXT_METHODS:
    if hasattr(_st_dg.DeltaGenerator, _name):  # col.markdown(...), st.sidebar.button(...) — перший аргумент self
        setattr(_st_dg.DeltaGenerator, _name, _wrap_text(getattr(_st_dg.DeltaGenerator, _name), pos=(1,)))
    if hasattr(st, _name):                     # st.markdown(...)
        setattr(st, _name, _wrap_text(getattr(st, _name), pos=(0,)))
for _name, _wrapper in [("radio", _wrap_choice), ("selectbox", _wrap_choice), ("multiselect", _wrap_choice),
                        ("select_slider", _wrap_choice), ("dataframe", _wrap_dataframe), ("data_editor", _wrap_data_editor),
                        ("plotly_chart", _wrap_plotly), ("tabs", _wrap_tabs)]:
    setattr(_st_dg.DeltaGenerator, _name, _wrapper(getattr(_st_dg.DeltaGenerator, _name), 1))
    setattr(st, _name, _wrapper(getattr(st, _name), 0))
_st_dg.DeltaGenerator.metric = _wrap_text(_st_dg.DeltaGenerator.metric, pos=(1, 2, 3))
st.metric = _wrap_text(st.metric, pos=(0, 1, 2))
st.spinner = _wrap_text(st.spinner, pos=(0,))


# ---------------- Запам'ятовування налаштувань між сесіями ----------------
# Мова, розділ і вибрані фільтри зберігаються в браузері (localStorage) і відновлюються при наступному відкритті.
# Для цього потрібен пакет streamlit-js-eval (додай у requirements.txt). Без нього налаштування
# зберігаються в адресі сторінки — тоді достатньо додати сторінку в закладки.
PREF_KEYS = ["lang", "nav", "dyn_mode", "dyn_group", "dyn_plats", "dyn_period", "goals_period", "monthly_platform",
             "heat_mode", "cal_view", "cal_filter", "mkt_scope", "pipe_stage", "team_period"]
PREF_LIST_KEYS = {"dyn_plats"}
PREF_STORE_KEY = "upscale_bi_prefs_v1"
try:
    from streamlit_js_eval import streamlit_js_eval
except ImportError:
    streamlit_js_eval = None


def _apply_prefs(prefs):
    # зберігаємо окремо від віджетів: Streamlit видаляє стан віджетів зі сторінок, які зараз не показані
    store = st.session_state.setdefault("_prefs", {})
    for k, v in prefs.items():
        if k in PREF_KEYS and v not in (None, "", []):
            v = list(v) if k in PREF_LIST_KEYS else v
            store[k] = v
            st.session_state[k] = v


if not st.session_state.get("_prefs_loaded"):
    if streamlit_js_eval is not None:
        _raw = streamlit_js_eval(js_expressions=f"localStorage.getItem('{PREF_STORE_KEY}') || '{{}}'", key="_prefs_load")
        if _raw is not None:  # None = браузер ще не відповів; сторінка поки показується з типовими налаштуваннями
            try:
                _apply_prefs(json.loads(_raw))
            except (ValueError, TypeError):
                pass
            st.session_state["_prefs_loaded"] = True
            st.session_state["_prefs_saved"] = _raw
    else:
        _qp = st.query_params
        _apply_prefs({k: (_qp.get_all(k) if k in PREF_LIST_KEYS else _qp.get(k)) for k in PREF_KEYS if k in _qp})
        st.session_state["_prefs_loaded"] = True


def persisted(key, options=None, **defaults):
    """Для віджета зі збереженим значенням: перевіряє, що значення ще є серед варіантів,
    і не передає типове значення (інакше Streamlit сварився б на конфлікт)."""
    def valid(v):
        return options is None or (all(x in options for x in v) if isinstance(v, list) else v in options)
    saved = st.session_state.get("_prefs", {})
    if key not in st.session_state and key in saved and valid(saved[key]):
        st.session_state[key] = saved[key]  # повертаємо значення після переходу між сторінками
    if key in st.session_state and not valid(st.session_state[key]):
        del st.session_state[key]
    return {} if key in st.session_state else defaults


def save_prefs():
    if not st.session_state.get("_prefs_loaded"):
        return  # не перезаписуємо збережене типовими значеннями, поки воно не прочитане
    prefs = st.session_state.setdefault("_prefs", {})
    for k in PREF_KEYS:
        if k in st.session_state:  # віджет показаний у цьому запуску — беремо його поточне значення
            v = st.session_state[k]
            prefs[k] = list(v) if isinstance(v, (list, tuple)) else v
    data = json.dumps(prefs, ensure_ascii=False, sort_keys=True)
    if data == st.session_state.get("_prefs_saved"):
        return
    if streamlit_js_eval is not None:
        streamlit_js_eval(js_expressions=f"localStorage.setItem('{PREF_STORE_KEY}', {json.dumps(data)})",
                          key="_prefs_save_" + str(abs(hash(data)) % 10**10))
    else:
        st.query_params.from_dict({k: v for k, v in prefs.items()})
    st.session_state["_prefs_saved"] = data

# ---------------- Шапка сайдбару + перемикач мови (до будь-якого іншого тексту) ----------------
with st.sidebar:
    _col_logo, _col_title = st.columns([1, 2.8])
    with _col_logo:
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, width=64)
        else:
            st.markdown("<div style='font-size:38px; text-align:center;'>🎮</div>", unsafe_allow_html=True)
    with _col_title:
        st.markdown(
            "<h3 style='margin:0; padding-top:2px; font-weight:800; color:#fff; letter-spacing:0.5px; font-size:20px; white-space:nowrap;'>Upscale Studio</h3>"
            "<p style='margin:0; font-size:11px; font-weight:700; color:#d946ef; text-transform:uppercase; letter-spacing:0.8px;'>Publishing BI Hub</p>",
            unsafe_allow_html=True,
        )
    st.selectbox("🌐 Мова:", list(LANGS), format_func=lambda c: LANGS[c], key="lang", label_visibility="collapsed", **persisted("lang", list(LANGS)))

# ==============================================================================
# ⚙️ 4. БАЗОВІ ХЕЛПЕРИ
# ==============================================================================
def is_blank(v):
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    return str(v).strip().lower() in ("", "nan", "none", "null", "-", "—", "nat")


def safe_str(v):
    return "" if is_blank(v) else str(v).strip()


def parse_flexible_date(d_val):
    if is_blank(d_val):
        return None
    if isinstance(d_val, datetime):
        return d_val
    if isinstance(d_val, date):
        return datetime(d_val.year, d_val.month, d_val.day)
    d_str = str(d_val).strip()
    for fmt in ["%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y.%m.%d", "%m/%d/%Y"]:
        try:
            return datetime.strptime(d_str[:10], fmt)
        except ValueError:
            continue
    try:
        dt = pd.to_datetime(d_str, dayfirst=True)
        if pd.notna(dt):
            return dt.to_pydatetime()
    except Exception:
        pass
    return None


def to_date(v):
    dt = parse_flexible_date(v)
    return dt.date() if dt else None


def clean_num_val(val):
    if is_blank(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("$", "").replace("€", "").replace("%", "").replace("\xa0", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.find(".") < s.find(",") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def is_truthy(val):
    return (not is_blank(val)) and str(val).strip().lower() in ["true", "истина", "1", "yes", "да", "✅", "done", "t"]


def contains_japanese(text):
    return bool(text) and bool(re.search(r"[぀-ヿ㐀-䶿一-鿿]", str(text)))


def find_col(columns, *patterns, exclude=()):
    """Перша колонка, що містить один із patterns (у порядку пріоритету) і не містить exclude."""
    cols = list(columns)
    for p in patterns:
        for c in cols:
            cl = str(c).lower()
            if p in cl and not any(x in cl for x in exclude):
                return c
    return None


def fmt_usd(v, force_decimals=False):
    if v is None:
        return "—"
    if force_decimals or abs(v) < 100:
        return f"${v:,.2f}"
    return f"${v:,.0f}"


def safe_pct(part, whole):
    return (part / whole * 100) if whole else None


def kpi_card(col, label, value, badge="", badge_cls="badge-total", color=None):
    style = f' style="color:{color};"' if color else ""
    badge_html = f'<span class="kpi-badge {badge_cls}">{badge}</span>' if badge else ""
    col.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value"{style}>{value}</div>{badge_html}</div>',
        unsafe_allow_html=True,
    )


def show_fig(fig, height=None, **layout):
    if height:
        layout["height"] = height
    layout.setdefault("paper_bgcolor", "rgba(0,0,0,0)")
    layout.setdefault("plot_bgcolor", "rgba(0,0,0,0)")
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, theme=None)


def today_vline(fig, label="сьогодні", **kw):
    fig.add_vline(x=datetime.combine(TODAY, datetime.min.time()).timestamp() * 1000, line_dash=kw.pop("line_dash", "dot"),
                  line_color="#fbbf24", annotation_text=label, annotation_font_color="#fbbf24", **kw)


def csv_button(df, label, file_name, key=None):
    st.download_button(label, data=df.to_csv(index=False).encode("utf-8"), file_name=file_name, mime="text/csv", key=key)


# ---------------- Періоди (одна логіка вибору кварталу/року на весь застосунок) ----------------
def quarter_of(d):
    return (d.month - 1) // 3 + 1


def month_label(d):
    return f"{UKR_MONTH_NAMES[d.month]} {d.year}"


def month_label_to_date(label):
    try:
        name, y = str(label).split(" ")
        return date(int(y), UKR_MONTH_NAMES.index(name), 1)
    except (ValueError, IndexError):
        return None


def period_options(dates, include_months=False, extras=()):
    ds = sorted({d for d in (to_date(x) for x in dates) if d})
    opts = list(extras) + ["Весь період"]
    for y in sorted({d.year for d in ds}, reverse=True):
        opts.append(f"{y} (рік)")
        for q in sorted({quarter_of(d) for d in ds if d.year == y}, reverse=True):
            opts.append(f"Q{q} {y}")
            if include_months:
                for m in sorted({d.month for d in ds if d.year == y and quarter_of(d) == q}, reverse=True):
                    opts.append(f"{UKR_MONTH_NAMES[m]} {y}")
    return opts


def period_bounds(label):
    """Повертає (start, end) для 'Весь період' / '2026 (рік)' / 'Q3 2026' / 'Жов 2026'."""
    m = re.match(r"^(\d{4}) \(рік\)$", label)
    if m:
        y = int(m.group(1))
        return date(y, 1, 1), date(y, 12, 31)
    m = re.match(r"^Q([1-4]) (\d{4})$", label)
    if m:
        q, y = int(m.group(1)), int(m.group(2))
        end_month = q * 3
        return date(y, end_month - 2, 1), date(y, end_month, calendar.monthrange(y, end_month)[1])
    d = month_label_to_date(label)
    if d:
        return d, date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])
    return None, None


def period_picker(dates, key, label="Період:", include_months=False, extras=(), default=None):
    opts = period_options(dates, include_months=include_months, extras=extras)
    default = default or f"Q{quarter_of(TODAY)} {TODAY.year}"
    idx = opts.index(default) if default in opts else opts.index("Весь період")
    return st.selectbox(label, opts, key=key, **persisted(key, opts, index=idx))


def in_bounds(d, start, end):
    d = to_date(d)
    if d is None:
        return start is None and end is None
    return (start is None or d >= start) and (end is None or d <= end)


# ==============================================================================
# 📥 5. ЗАВАНТАЖЕННЯ ДАНИХ
# ==============================================================================
def get_export_url(url_or_id, sheet_name=None):
    if not url_or_id:
        return ""
    url_str = str(url_or_id).strip()
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url_str)
    sheet_id = match.group(1) if match else url_str
    if sheet_name:
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(str(sheet_name).strip())}"
    gid_match = re.search(r"[?#&]gid=([0-9]+)", url_str)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


@st.cache_data(ttl=300, show_spinner=False)
def load_sheet(url, sheet_name=None, no_header=False):
    """Єдиний завантажувач будь-якого листа Google Sheets у DataFrame (усі значення — текст)."""
    if not url:
        return pd.DataFrame()
    try:
        return pd.read_csv(get_export_url(url, sheet_name), dtype=str, header=None if no_header else "infer")
    except Exception:
        return pd.DataFrame()


TEXT_COLUMN_KEYS = ["cover", "image", "постер", "url", "фото", "link", "посилання", "date", "дата", "name", "назва",
                    "genre", "жанр", "status", "статус", "platform", "insights", "formula", "source", "developer"]


def load_catalog(url):
    df = load_sheet(url).copy()
    if df.empty:
        return df
    for col in df.columns:
        cl = str(col).lower()
        # "ai" шукаємо як окреме слово, щоб не зачепити Retail / Daily / Gain
        if any(k in cl for k in TEXT_COLUMN_KEYS) or re.search(r"\bai\b", cl):
            continue
        df[col] = df[col].apply(clean_num_val)
    name_col = find_col(df.columns, "game name", "game", "title", "назва") or df.columns[0]
    df = df.rename(columns={name_col: "Game_Name_Clean"})
    df["Game_Name_Clean"] = df["Game_Name_Clean"].apply(safe_str)
    return df[df["Game_Name_Clean"] != ""].reset_index(drop=True)


WEEKLY_COL_MAP = [
    "From", "To",
    "Nintendo_Sales", "Nintendo_Sales_Diff", "Nintendo_Wishlists", "Nintendo_Wishlists_Diff", "Nintendo_Revenue", "Nintendo_Revenue_Diff",
    "PS_Sales", "PS_Sales_Diff", "PS_Wishlists", "PS_Wishlists_Diff", "PS_Revenue", "PS_Revenue_Diff",
    "Xbox_Sales", "Xbox_Sales_Diff", "Xbox_Wishlists", "Xbox_Wishlists_Diff", "Xbox_Revenue", "Xbox_Revenue_Diff",
    "Leads", "Leads_Diff", "Sequence_Started", "Sequence_Started_Diff", "Contacts", "Contacts_Diff",
    "Opportunities", "Opportunities_Diff", "Calls", "Calls_Diff", "Deals", "Deals_Diff",
    "Twitter", "Twitter_Diff", "Instagram", "Instagram_Diff", "TikTok", "TikTok_Diff", "YouTube", "YouTube_Diff", "Discord", "Discord_Diff",
]
FUNNEL_STAGES = [("Leads", "🔍 Leads", "Додані ліди"), ("Sequence_Started", "🚀 Sequence", "Кому написали"),
                 ("Contacts", "✉️ Contacts", "Отримано відповідей"), ("Opportunities", "🎯 Opps", "Зацікавлені"),
                 ("Calls", "📞 Calls", "Дзвінки"), ("Deals", "🤝 Deals", "Підписані договори")]
SOCIAL_COLS = ["Twitter", "TikTok", "YouTube", "Discord", "Instagram"]


def load_weekly(url):
    raw_w = load_sheet(url, no_header=True)
    if raw_w.empty:
        return pd.DataFrame()
    head_rows = [" ".join(str(x) for x in raw_w.iloc[i].tolist() if not is_blank(x)).lower() for i in range(min(2, len(raw_w)))]
    if len(head_rows) > 1 and any(k in head_rows[1] for k in ["from", "sales", "to"]):
        data_df = raw_w.iloc[2:]
    elif any(k in head_rows[0] for k in ["from", "sales"]):
        data_df = raw_w.iloc[1:]
    else:
        data_df = raw_w
    data_df = data_df.reset_index(drop=True)

    out = pd.DataFrame({name: data_df.iloc[:, i] for i, name in enumerate(WEEKLY_COL_MAP) if i < data_df.shape[1]})
    for c in out.columns:
        if c not in ("From", "To"):
            out[c] = out[c].apply(clean_num_val)
    out["Parsed_Date"] = pd.to_datetime(out["From"].apply(parse_flexible_date), errors="coerce")
    # сортуємо за датою — «останній тиждень» і WoW більше не залежать від порядку рядків у листі
    out = out.dropna(subset=["Parsed_Date"]).sort_values("Parsed_Date").reset_index(drop=True)
    for col in ["PS_Revenue", "Nintendo_Revenue", "Xbox_Revenue", "PS_Sales", "Nintendo_Sales", "Xbox_Sales"]:
        if col not in out.columns:
            out[col] = 0.0
    out["Total_Revenue"] = out["PS_Revenue"] + out["Nintendo_Revenue"] + out["Xbox_Revenue"]
    out["Total_Sales"] = out["PS_Sales"] + out["Nintendo_Sales"] + out["Xbox_Sales"]
    out["Week"] = out["Parsed_Date"].dt.strftime("%d.%m.%Y")
    return out


# ---------------- Помісячні звіти сторів ----------------
def parse_nintendo_monthly_data(df_raw):
    date_cols = [c for c in df_raw.columns if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", str(c).strip())]
    if not date_cols:
        return pd.DataFrame(), []

    cost_col = find_col(df_raw.columns, "points", "cost", "price", "ціна")
    curr_col = find_col(df_raw.columns, "curr", "валют")
    title_code_col = find_col(df_raw.columns, "titlecode", "title code")
    target_name_col = find_col(df_raw.columns, "itemname", "item name") or find_col(df_raw.columns, "titlename", "title name") or df_raw.columns[1]

    code_to_english = {}
    if title_code_col:
        for _, r in df_raw.iterrows():
            t_code, name = safe_str(r.get(title_code_col)), safe_str(r.get(target_name_col))
            if t_code and name and not contains_japanese(name):
                code_to_english.setdefault(t_code[:9], name)
                code_to_english.setdefault(t_code, name)

    def label_for(c_str):
        try:
            m, _, y = c_str.split("/")
            y = int(y) if int(y) >= 2000 else 2000 + int(y)
            return f"{UKR_MONTH_NAMES[int(m)]} {y}"
        except (ValueError, IndexError):
            return c_str

    label_map = {c: label_for(c) for c in date_cols}
    records = []
    for _, row in df_raw.iterrows():
        name = safe_str(row.get(target_name_col))
        if not name:
            continue
        t_code = safe_str(row.get(title_code_col)) if title_code_col else ""
        if contains_japanese(name):
            name = code_to_english.get(t_code) or code_to_english.get(t_code[:9]) or name
        fx = FX_RATES.get(safe_str(row.get(curr_col)).upper() or "USD", 1.0) if curr_col else 1.0
        cost = clean_num_val(row.get(cost_col)) if cost_col else 0.0
        rec = {"Назва гри / DLC": name}
        for d in date_cols:
            rec[label_map[d]] = rec.get(label_map[d], 0.0) + clean_num_val(row.get(d)) * cost * fx
        records.append(rec)
    if not records:
        return pd.DataFrame(), []

    labels = sorted(set(label_map.values()), key=lambda l: month_label_to_date(l) or date(2000, 1, 1))
    grouped = pd.DataFrame(records).groupby("Назва гри / DLC")[labels].sum().reset_index()
    grouped["Всього ($)"] = grouped[labels].sum(axis=1)
    return grouped.sort_values("Всього ($)", ascending=False).reset_index(drop=True), labels


def parse_xbox_monthly_data(df_raw):
    if df_raw.empty:
        return pd.DataFrame(), []
    title_col = next((c for c in df_raw.columns if c.lower().strip() in ["titlename", "parentproductname", "назва", "title"]), None)
    date_col = next((c for c in df_raw.columns if "datestamp" in c.lower() or c.lower().strip() == "date"), None)
    usd_col = find_col(df_raw.columns, "purchasepriceusdamount", "priceusdamount")
    if not (title_col and date_col and usd_col):
        return pd.DataFrame(), []

    df = pd.DataFrame({
        "Назва гри / DLC": df_raw[title_col].apply(safe_str),
        "d": df_raw[date_col].apply(to_date),
        "USD": df_raw[usd_col].apply(clean_num_val),
    })
    df = df[(df["Назва гри / DLC"] != "") & df["d"].notna()]
    if df.empty:
        return pd.DataFrame(), []
    df["Month"] = df["d"].apply(month_label)
    labels = sorted(df["Month"].unique(), key=month_label_to_date)
    pivot = df.pivot_table(index="Назва гри / DLC", columns="Month", values="USD", aggfunc="sum", fill_value=0.0).reset_index()
    pivot = pivot[["Назва гри / DLC"] + labels]
    pivot.columns.name = None
    pivot["Всього ($)"] = pivot[labels].sum(axis=1)
    return pivot.sort_values("Всього ($)", ascending=False).reset_index(drop=True), labels


def combine_monthly_matrices(n_matrix, x_matrix, n_months, x_months):
    frames = [m for m in (n_matrix, x_matrix) if not m.empty]
    if not frames:
        return pd.DataFrame(), []
    months = sorted(set(n_months) | set(x_months), key=lambda l: month_label_to_date(l) or date(2000, 1, 1))
    combined = pd.concat([f.drop(columns=["Всього ($)"]) for f in frames], ignore_index=True).fillna(0.0)
    combined = combined.groupby("Назва гри / DLC")[months].sum().reset_index()
    combined["Всього ($)"] = combined[months].sum(axis=1)
    return combined.sort_values("Всього ($)", ascending=False).reset_index(drop=True), months


# ==============================================================================
# 🧩 6. ДОМЕННА ЛОГІКА
# ==============================================================================
# ---------------- Каталог: колонки ----------------
def detect_catalog_columns(df):
    cols = df.columns
    return {
        "cover": find_col(cols, "cover", "image", "постер", "обкладинка"),
        "discount": find_col(cols, "target discount", "discount", "знижк"),
        "porting": find_col(cols, "porting cost", "porting", "витрати"),
        "split": find_col(cols, "revenue split", "split"),
        "recoup": find_col(cols, "recoup", "рекуп"),
        "release": find_col(cols, "release date", "дата релізу", "дата релиза", "release", exclude=("pred",)) or find_col(cols, "date", "дата"),
        "genre": find_col(cols, "genre", "жанр"),
        "price": find_col(cols, "price consoles", "ціна", "price", exclude=("pred", "forecast")),
        "total": next((c for c in cols if str(c).lower().strip() == "total" or "всього" in str(c).lower()), None),
        "source": find_col(cols, "platform source", "source", "джерело"),
    }


def platform_of(cl):
    if "playstation" in cl or re.search(r"(^|[^a-z])ps\d?([^a-z]|$)", cl):
        return "PS"
    if "switch" in cl or "nintendo" in cl or "nsw" in cl:
        return "Switch"
    if "xbox" in cl:
        return "Xbox"
    return None


def match_period(cl):
    """До якого періоду (M1/M3/M6/1Y) належить колонка ФАКТИЧНИХ продажів. Прогнози й дублікати (.1) ігноруються."""
    if any(x in cl for x in ["pred", "forecast", "план", "target", "прогноз", "all"]) or re.search(r"\.\d+$", cl):
        return None
    if "year" in cl or re.search(r"(^|[^a-z0-9])1y([^a-z0-9]|$)", cl):
        return "1Y"
    if re.search(r"6\s*month", cl) or re.search(r"(^|[^a-z0-9])m6([^0-9]|$)", cl):
        return "M6"
    if re.search(r"3\s*month", cl) or re.search(r"(^|[^a-z0-9])m3([^0-9]|$)", cl):
        return "M3"
    if "1st" in cl or "month 1" in cl or re.search(r"(^|[^a-z0-9])m1([^0-9]|$)", cl):
        return "M1"
    return None


def classify_sales_columns(df):
    period_cols = {p: {k: [] for k in PLATFORMS + [None]} for p in PERIODS}
    all_time = {k: [] for k in PLATFORMS}
    for c in df.columns:
        cl = str(c).lower()
        plat = platform_of(cl)
        p = match_period(cl)
        if p:
            period_cols[p][plat].append(c)
        elif plat and "all" in cl and not any(x in cl for x in ["pred", "forecast"]):
            all_time[plat].append(c)
    return period_cols, all_time


def row_period_fact(r, p, plat=None):
    """Факт за період: по платформі або сума платформ (якщо платформних колонок немає — загальні)."""
    if plat:
        cols = PERIOD_COLS[p][plat]
    else:
        cols = [c for k in PLATFORMS for c in PERIOD_COLS[p][k]] or PERIOD_COLS[p][None]
    total = sum(v for v in (clean_num_val(r[c]) for c in cols) if v > 0)
    return total if total > 0 else None


def game_price(r):
    return clean_num_val(r.get(COL["price"])) if COL["price"] else 0.0


def game_cover(r):
    v = safe_str(r.get(COL["cover"])) if COL["cover"] else ""
    return v if v.startswith("http") else DEFAULT_IMAGE


def game_release(r):
    return to_date(r.get(COL["release"])) if COL["release"] else None


# Колонки Xbox і Switch за періоди заповнює скрипт зі звітів сторів — це факт.
# Колонки PlayStation за періоди в таблиці містять оцінки, тому для PS беремо тільки All Time.
FACT_PERIOD_PLATFORMS = ("Xbox", "Switch")


def game_plat_total(r, p):
    """All Time по платформі. Для Xbox і Switch: якщо All Time порожня або менша за факт періоду
    (виручка за весь час не може бути меншою), беремо найбільший факт M1/M3/M6/1Y."""
    at = clean_num_val(r.get(ALL_TIME_COLS[p][0])) if ALL_TIME_COLS[p] else 0.0
    if p in FACT_PERIOD_PLATFORMS:
        at = max([at] + [row_period_fact(r, q, p) or 0.0 for q in PERIODS])
    return at


def game_total(r):
    plat_sum = sum(game_plat_total(r, p) for p in PLATFORMS)
    if COL["total"]:
        return max(clean_num_val(r.get(COL["total"])), plat_sum)
    return plat_sum


def portfolio_totals(df):
    plat = {p: float(sum(game_plat_total(r, p) for _, r in df.iterrows())) for p in PLATFORMS}
    total = float(sum(game_total(r) for _, r in df.iterrows()))
    return total, plat


# ---------------- Життєвий цикл / LTV ----------------
def period_state(p, days_live):
    if days_live is None:
        return "unknown"
    if days_live < 0:
        return "future"
    return "done" if days_live >= PERIOD_DAYS[p] else "running"


def build_lifecycle(df):
    items = []
    for _, r in df.iterrows():
        name = safe_str(r.get("Game_Name_Clean"))
        if not name:
            continue
        facts = {p: row_period_fact(r, p) for p in PERIODS}
        if not PERIOD_COLS_ARE_CUMULATIVE:
            running = 0.0
            for p in PERIODS:
                if facts[p] is not None:
                    running += facts[p]
                    facts[p] = running
        m1 = facts["M1"] or 0.0
        rel = game_release(r)
        days_live = (TODAY - rel).days if rel else None

        forecasts, states, devs = {}, {}, {}
        for p in PERIODS:
            states[p] = period_state(p, days_live)
            if p == "M1":
                continue
            forecasts[p] = m1 * LTV_MULT[p] if m1 > 0 else None
            ok = forecasts[p] and facts[p] and states[p] in ("done", "unknown")
            devs[p] = (facts[p] - forecasts[p]) / forecasts[p] * 100 if ok else None
        last_dev_p = next((p for p in ["1Y", "M6", "M3"] if devs.get(p) is not None), None)

        # 🔮 Прогноз до релізу — та сама формула, що у вкладці «Точність моделі»
        base = row_base_metric(r)
        genre_key = match_genre(r.get(COL["genre"]) if COL["genre"] else "")
        m1_plats = [p for p in PLATFORMS if (row_period_fact(r, "M1", p) or 0) > 0]
        pre = {"base": base, "genre": genre_key, "platforms": m1_plats or ["Switch"],
               "source": safe_str(r.get(COL["source"])) if COL["source"] else "", "forecasts": {}, "devs": {}}
        if base > 0:
            pre_m1 = sum(forecast_m1(base, genre_key, game_price(r) or 9.99, pre["platforms"]).values())
            for p in PERIODS:
                fc = pre_m1 * (1.0 if p == "M1" else LTV_MULT[p])
                pre["forecasts"][p] = fc
                ok = fc and facts[p] and states[p] in ("done", "unknown")
                pre["devs"][p] = (facts[p] - fc) / fc * 100 if ok else None

        items.append({
            "name": name, "img": game_cover(r), "price": game_price(r), "rel": rel, "days_live": days_live,
            "m1": m1, "m1_by_plat": {p: row_period_fact(r, "M1", p) or 0.0 for p in PLATFORMS},
            "facts": facts, "forecasts": forecasts, "states": states, "devs": devs,
            "last_dev_p": last_dev_p, "last_dev": devs.get(last_dev_p) if last_dev_p else None,
            "pre": pre, "plat_total": {p: game_plat_total(r, p) for p in PLATFORMS},
        })
    return items


# ---------------- Прогноз M1 (одна формула для калькулятора й аудиту точності) ----------------
def base_metric_from_source(source, value):
    s = str(source).lower()
    if value <= 0:
        return 0.0
    if "steam" in s:
        return value * 0.10 + 500.0
    if "google" in s or "play" in s:
        return math.sqrt(value) * 2.0 + 800.0
    if "crazy" in s or "web" in s:
        return value * 0.05 + 900.0
    if "itch" in s:
        return value * 10.0 + 400.0
    return 0.0


def match_genre(genre_str):
    g = safe_str(genre_str).lower()
    if g:
        for k in GENRE_DATABASE:
            if k.lower() in g or g in k.lower():
                return k
    return DEFAULT_GENRE


def forecast_m1(base, genre_key, price, platforms=PLATFORMS):
    cfg = GENRE_DATABASE[genre_key]
    pm = PRICE_MODIFIERS.get(round(price, 2), 1.0)
    return {p: (base * cfg[p] * pm if p in platforms else 0.0) for p in PLATFORMS}


def finance_settings():
    store = st.session_state.get("fin_store", DEFAULT_STORE_CUT)
    tax = st.session_state.get("fin_tax", DEFAULT_TAX_CUT)
    split = st.session_state.get("fin_split", DEFAULT_DEV_SPLIT)
    return store, tax, split


def studio_share():
    """Частка студії від gross (без рекупу): (100 − комісія стору − податки) × (1 − спліт девелопера)."""
    store, tax, split = finance_settings()
    return (100 - store - tax) / 100.0 * (1 - split / 100.0)


# ---------------- Сертифікація ----------------
STAGE_DONE, STAGE_WIP, STAGE_OVERDUE, STAGE_BACKLOG = "Uploaded / In Cert", "In Porting", "Overdue Dev", "Backlog"


def normalize_dev_name(raw_name):
    n = safe_str(raw_name)
    if not n:
        return "Не призначено"
    nl = n.lower()
    for keys, canon in [(("серг",), "Сергій"), (("ігор", "игор"), "Ігор"), (("іван", "иван"), "Іван"),
                        (("максим",), "Максим"), (("дим", "дмитр"), "Дмитро"), (("влад",), "Влад")]:
        if any(k in nl for k in keys):
            return canon
    return n


def process_certification_table(df_raw):
    if df_raw.empty:
        return pd.DataFrame()
    cols = df_raw.columns
    c_game = find_col(cols, "game name", "игра", "назва", "title") or cols[0]
    c_status = find_col(cols, "status", "статус")
    c_dev = find_col(cols, "developer", "разработчик", "розробник", "dev")
    c_rel = find_col(cols, "release date", "дата релиза")
    c_start = find_col(cols, "старт", "start")
    c_plan = find_col(cols, "планируемая дата", "plan finish")
    c_upload = find_col(cols, "загружен", "uploaded")
    c_plan_days = find_col(cols, "планируемый срок", "plan days")
    c_fact_days = find_col(cols, "фактический срок", "fact days")
    g = lambda r, c: r.get(c) if c else None

    records = []
    for _, r in df_raw.iterrows():
        name = safe_str(g(r, c_game))
        if not name:
            continue
        d_start, d_plan, d_upload, d_rel = (parse_flexible_date(g(r, c)) for c in (c_start, c_plan, c_upload, c_rel))

        p_days = clean_num_val(g(r, c_plan_days))
        if p_days == 0 and d_start and d_plan:
            p_days = max(1, (d_plan - d_start).days)
        f_days = clean_num_val(g(r, c_fact_days))
        if f_days == 0 and d_start and d_upload:
            f_days = max(1, (d_upload - d_start).days)

        delta = None
        if f_days > 0 and p_days > 0:
            delta = int(f_days - p_days)
        elif d_upload and d_plan:
            delta = (d_upload - d_plan).days

        if d_upload:
            stage = STAGE_DONE
            verdict = "🟢 Білд завантажено" if delta is None else ("🟢 Вчасно здано" if delta <= 0 else f"🔴 Затримка (+{delta} дн)")
        elif d_start and d_plan and TODAY > d_plan.date():
            stage, verdict = STAGE_OVERDUE, f"🚨 Прострочено (+{(TODAY - d_plan.date()).days} дн)"
        elif d_start:
            stage, verdict = STAGE_WIP, "⏳ В розробці (у плані)"
        else:
            stage, verdict = STAGE_BACKLOG, "⚪ В черзі"

        fmt = lambda d: d.strftime("%d.%m.%Y") if d else "—"
        records.append({
            "Гра": name, "Розробник": normalize_dev_name(g(r, c_dev)),
            "Статус у базі": safe_str(g(r, c_status)) or stage, "Етап": stage,
            "Дата старту": fmt(d_start), "План здачі білда": fmt(d_plan), "Дата завантаження білда": fmt(d_upload),
            "Реліз Nintendo": fmt(d_rel),
            "План (дн)": int(p_days) if p_days > 0 else None, "Факт (дн)": int(f_days) if f_days > 0 else None,
            "Відхилення (дн)": delta, "Вердикт": verdict,
            "_d_start": d_start, "_d_plan": d_plan, "_d_upload": d_upload, "_d_release": d_rel, "_delta": delta,
        })
    return pd.DataFrame(records)


def project_date(row):
    """Дата, за якою проєкт потрапляє в період: план здачі → завантаження → старт."""
    for cand in (row.get("_d_plan"), row.get("_d_upload"), row.get("_d_start")):
        if cand is not None and not pd.isna(cand):
            return to_date(cand)
    return None


def build_dev_kpi(df_sub, devs):
    rows = []
    for dev in devs:
        g = df_sub[df_sub["Розробник"] == dev]
        tot = len(g)
        done = int((g["Етап"] == STAGE_DONE).sum())
        overdue = int((g["Етап"] == STAGE_OVERDUE).sum())
        plan_d = pd.to_numeric(g["План (дн)"], errors="coerce").dropna()
        fact_d = pd.to_numeric(g["Факт (дн)"], errors="coerce").dropna()
        deltas = pd.to_numeric(g["_delta"], errors="coerce").dropna()
        on_time = float((deltas <= 0).mean() * 100) if not deltas.empty else None
        avg_delay = float(deltas.mean()) if not deltas.empty else None

        if tot:
            score = done / tot * 45 + (on_time * 0.35 if on_time is not None else 25.0) + 20.0
            score -= max(0.0, (avg_delay or 0.0) * 2) + overdue * 5
            kpi = round(min(100.0, max(0.0, score)), 1)
        else:
            kpi = None
        status = ("⚪ Немає проєктів" if kpi is None else "🟢 Топ-перформер" if kpi >= 80
                  else "🟡 Норма" if kpi >= 65 else "🔴 Зона ботлнеку")
        rows.append({
            "Розробник": dev, "Всього ігор": tot, "Здано білдів": done,
            "В роботі": int((g["Етап"] == STAGE_WIP).sum()), "Прострочено": overdue,
            "В черзі": int((g["Етап"] == STAGE_BACKLOG).sum()),
            "Сер. план (дн)": round(plan_d.mean(), 1) if not plan_d.empty else None,
            "Сер. факт (дн)": round(fact_d.mean(), 1) if not fact_d.empty else None,
            "Сер. відхилення (дн)": round(avg_delay, 1) if avg_delay is not None else None,
            "% вчасно": round(on_time) if on_time is not None else None,
            "KPI (0-100)": kpi, "Статус": status,
        })
    out = pd.DataFrame(rows)
    return out if out.empty else out.sort_values(["Всього ігор", "KPI (0-100)"], ascending=[False, False], na_position="last").reset_index(drop=True)


# ---------------- Сейли ----------------
def sale_dates(s):
    return (datetime.strptime(s["start"], "%Y-%m-%d").date(), datetime.strptime(s["end"], "%Y-%m-%d").date())


def sale_status(s):
    start, end = sale_dates(s)
    if TODAY < start:
        return f"🗓️ Через {(start - TODAY).days} дн."
    if TODAY <= end:
        return "🔥 Йде зараз"
    return "✔️ Завершився"


def default_sale_index(schedule, key_date="start"):
    """Перший сейл, який ще не завершився (або в якого ще не минув дедлайн)."""
    for i, s in enumerate(schedule):
        d = datetime.strptime(s[key_date] if key_date in s else s["end"], "%Y-%m-%d").date()
        if d >= TODAY:
            return i
    return len(schedule) - 1


def deadline_badge(deadline_str):
    d = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    days = (d - TODAY).days
    if days > 0:
        return f"⏳ Залишилось {days} дн."
    if days == 0:
        return "🚨 Дедлайн СЬОГОДНІ!"
    return f"✖️ Минув {-days} дн. тому"

# ==============================================================================
# 🚀 7. ЗАВАНТАЖЕННЯ ОСНОВНИХ ДАНИХ
# ==============================================================================
raw_df = load_catalog(GOOGLE_SHEET_URL)
if raw_df.empty:
    st.info("👋 Вкажи валідне посилання на Google Таблицю у рядку `GOOGLE_SHEET_URL`.")
    st.stop()

COL = detect_catalog_columns(raw_df)
PERIOD_COLS, ALL_TIME_COLS = classify_sales_columns(raw_df)
pipe_df = process_certification_table(load_sheet(GOOGLE_SHEET_URL, CERTIFICATION_SHEET_NAME))
weekly_df = load_weekly(WEEKLY_SHEET_URL)


def build_ai_context():
    lines = ["Game|Genre|Price|DevCost|DevSplit|Recoup|Release|M1|PS_All|Switch_All|Xbox_All|Total"]
    for _, r in raw_df.iterrows():
        plat_all = {p: int(game_plat_total(r, p)) for p in PLATFORMS}
        rel = game_release(r)
        lines.append("|".join(str(x) for x in [
            r["Game_Name_Clean"], safe_str(r.get(COL["genre"])) if COL["genre"] else "—", game_price(r),
            clean_num_val(r.get(COL["porting"])) if COL["porting"] else 0,
            clean_num_val(r.get(COL["split"])) if COL["split"] else DEFAULT_DEV_SPLIT,
            clean_num_val(r.get(COL["recoup"])) if COL["recoup"] else 0,
            rel.isoformat() if rel else "—", int(row_period_fact(r, "M1") or 0),
            plat_all["PS"], plat_all["Switch"], plat_all["Xbox"], int(game_total(r)),
        ]))
    pipe_txt = pipe_df[["Гра", "Розробник", "Вердикт", "Відхилення (дн)"]].to_csv(index=False) if not pipe_df.empty else "No cert data"
    weekly_cols = ["Week", "Total_Revenue", "PS_Revenue", "Nintendo_Revenue", "Xbox_Revenue"] + [s[0] for s in FUNNEL_STAGES]
    weekly_txt = weekly_df[[c for c in weekly_cols if c in weekly_df.columns]].tail(26).to_csv(index=False) if not weekly_df.empty else "No weekly data"
    return "\n".join(lines), pipe_txt, weekly_txt


# ==============================================================================
# 🧭 8. САЙДБАР
# ==============================================================================
with st.sidebar:
    divider = "<div style='border-bottom: 1px solid #28283c; margin: 14px 0;'></div>"
    st.markdown(divider, unsafe_allow_html=True)

    st.caption("📍 НАВІГАЦІЯ ХАБУ:")
    app_mode = st.radio("Навігація:", SECTIONS, label_visibility="collapsed", key="nav", **persisted("nav", SECTIONS, index=0))

    # Фільтри каталогу показуємо лише там, де вони працюють
    filtered_df = raw_df
    if app_mode == SECTIONS[0]:
        st.markdown(divider, unsafe_allow_html=True)
        st.caption("🔍 ФІЛЬТРАЦІЯ КАТАЛОГУ:")
        search = st.text_input("Пошук гри:", "", label_visibility="collapsed", placeholder="Пошук гри...")
        if COL["genre"]:
            genres_all = sorted({safe_str(g) for g in raw_df[COL["genre"]] if safe_str(g)})
            sel_genres = st.multiselect("Жанри:", genres_all, default=[], placeholder="Усі жанри")
            if sel_genres:
                filtered_df = filtered_df[filtered_df[COL["genre"]].apply(safe_str).isin(sel_genres)]
        if search:
            filtered_df = filtered_df[filtered_df["Game_Name_Clean"].str.contains(search, case=False, na=False, regex=False)]

    st.markdown(divider, unsafe_allow_html=True)
    if st.button("🔄 Оновити дані з Google Sheets", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(divider, unsafe_allow_html=True)
    with st.expander("🤖 AI-аналітик", expanded=False):
        claude_key = ANTHROPIC_API_KEY
        if not claude_key:
            try:
                claude_key = st.secrets.get("ANTHROPIC_API_KEY", "")
            except Exception:  # немає secrets.toml
                claude_key = ""
        if not claude_key:
            claude_key = st.text_input("Anthropic Key:", type="password", placeholder="sk-ant-...")
        ai_query = st.text_area("Запитай базу даних:", placeholder="Напр.: Яка конверсія лідів у контракти?")
        if st.button("⚡ Запитати Claude", use_container_width=True):
            key = str(claude_key or "").strip()
            if Anthropic is None:
                st.error("Пакет `anthropic` не встановлено.")
            elif not key.startswith("sk-ant"):
                st.error("❌ Введи валідний ключ Anthropic (sk-ant-...)!")
            elif not ai_query.strip():
                st.warning("Введи запитання.")
            else:
                with st.spinner("Claude аналізує базу..."):
                    try:
                        portfolio_txt, pipe_txt, weekly_txt = build_ai_context()
                        prompt = (
                            "Ти — фінансовий директор і аналітик консольного видавництва Upscale Studio (Україна).\n"
                            f"Портфоліо ({len(raw_df)} ігор):\n{portfolio_txt}\n\n"
                            f"Сертифікація та швидкість девелоперів:\n{pipe_txt}\n\n"
                            f"Тижнева звітність і BizDev воронка (останні 26 тижнів):\n{weekly_txt}\n\n"
                            f'Запитання: "{ai_query}"\n\n'
                            f"Дай точну відповідь ({LANG_NAMES_FOR_AI[cur_lang()]}) з реальними цифрами та висновками. Відповідай саме цією мовою. Суми пиши як \"USD 1,500\"."
                        )
                        client = Anthropic(api_key=key)
                        try:
                            msg = client.messages.create(model="claude-haiku-4-5", max_tokens=900, messages=[{"role": "user", "content": prompt}])
                        except Exception:
                            msg = client.messages.create(model="claude-3-5-haiku-20241022", max_tokens=900, messages=[{"role": "user", "content": prompt}])
                        st.markdown("##### 💡 Результат аналізу:")
                        st.markdown(re.sub(r"(?<!\\)\$", r"\\$", msg.content[0].text))
                    except Exception as e:
                        st.error(f"❌ Помилка Anthropic API: {e}")

# ==============================================================================
# 🎮 РОЗДІЛ 1: ПОРТФОЛІО
# ==============================================================================
def render_portfolio():
    st.title("📊 Портфоліо Upscale Studio")
    st.caption(f"Фактичні результати випущених ігор • У вибірці: **{len(filtered_df)}** ігор")

    total_gross, plat_rev = portfolio_totals(filtered_df)
    share = lambda v: f"↑ {round(v / total_gross * 100) if total_gross else 0}% частка"
    c = st.columns(4)
    kpi_card(c[0], "Загальна каса (All-Time)", fmt_usd(total_gross, True), "100% Total Gross")
    kpi_card(c[1], "Nintendo Switch", fmt_usd(plat_rev["Switch"], True), share(plat_rev["Switch"]), "badge-switch", "#ff6b6b")
    kpi_card(c[2], "PlayStation", fmt_usd(plat_rev["PS"], True), share(plat_rev["PS"]), "badge-ps", "#60a5fa")
    kpi_card(c[3], "Xbox", fmt_usd(plat_rev["Xbox"], True), share(plat_rev["Xbox"]), "badge-xbox", "#4ade80")
    st.markdown("<br>", unsafe_allow_html=True)

    items = build_lifecycle(filtered_df)
    tab_analytics, tab_insights, tab_pnl, tab_table = st.tabs([
        "📈 Аналітика", "🧠 Інсайти (LTV)", "💵 P&L, зарплати та роялті", "📑 Таблиця та One-Pager",
    ])

    with tab_analytics:
        render_portfolio_analytics(items)
    with tab_insights:
        render_insights(items)
    with tab_pnl:
        render_pnl()
    with tab_table:
        render_table_report(total_gross, plat_rev)


TREEMAP_PALETTE = ["#a855f7", "#38bdf8", "#f59e0b", "#10b981", "#f43f5e", "#6366f1", "#14b8a6",
                   "#eab308", "#ec4899", "#8b5cf6", "#22c55e", "#fb7185", "#0ea5e9", "#f97316"]


def render_genre_treemap(df):
    genre = df[COL["genre"]].apply(safe_str).replace("", "Без жанру") if COL["genre"] else "Без жанру"
    tm = pd.DataFrame({"Жанр": genre, "Гра": df["Game_Name_Clean"], "Виручка": df["_total"]})
    tm = tm[tm["Виручка"] > 0]
    if tm.empty:
        st.info("Немає ігор із виручкою у вибірці.")
        return
    fig = px.treemap(tm, path=[px.Constant("Портфоліо"), "Жанр", "Гра"], values="Виручка", color="Жанр",
                     color_discrete_sequence=TREEMAP_PALETTE)
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percentRoot:.1%}",
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percentRoot:.1%} портфоліо<extra></extra>",
        root_color="rgba(0,0,0,0)", marker=dict(line=dict(color="#0e1117", width=1.5)), tiling=dict(pad=2),
    )
    show_fig(fig, height=520, margin=dict(t=10, b=0, l=0, r=0))

    g = tm.groupby("Жанр").agg(rev=("Виручка", "sum"), n=("Гра", "count")).sort_values("rev", ascending=False)
    total = g["rev"].sum()
    st.caption("Топ жанри: " + " • ".join(
        f"**{name}** — {row.rev / total * 100:.0f}% виручки, {int(row.n)} ігор, ~{fmt_usd(row.rev / row.n)} на гру"
        for name, row in g.head(3).iterrows()))


def render_top_stacked(df):
    top = df.nlargest(15, "_total").sort_values("_total")
    if top.empty:
        st.info("Немає ігор у вибірці.")
        return
    fig = go.Figure()
    plat_sum = pd.Series(0.0, index=top.index)
    for p in PLATFORMS:
        if not ALL_TIME_COLS[p]:
            continue
        vals = top.apply(lambda r: game_plat_total(r, p), axis=1)
        plat_sum += vals
        lbl = PLATFORM_LABEL[p]
        fig.add_trace(go.Bar(y=top["Game_Name_Clean"], x=vals, orientation="h", name=lbl, marker_color=PLATFORM_COLORS[lbl],
                             hovertemplate=f"<b>%{{y}}</b><br>{lbl}: $%{{x:,.0f}}<extra></extra>"))
    other = (top["_total"] - plat_sum).clip(lower=0)
    if other.max() > 1:
        fig.add_trace(go.Bar(y=top["Game_Name_Clean"], x=other, orientation="h", name="Інше / без платформи", marker_color="#475569",
                             hovertemplate="<b>%{y}</b><br>Інше: $%{x:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=top["_total"], y=top["Game_Name_Clean"], mode="text", text=[f"  ${v:,.0f}" for v in top["_total"]],
                             textposition="middle right", textfont=dict(color="#e2e8f0", size=11), showlegend=False, hoverinfo="skip"))
    show_fig(fig, height=520, barmode="stack", xaxis_title="Виторг ($)", yaxis_title="",
             xaxis=dict(range=[0, float(top["_total"].max()) * 1.2]))


def render_portfolio_analytics(items):
    df = filtered_df.assign(_total=filtered_df.apply(game_total, axis=1))

    st.subheader("🏆 Топ-3 бестселери портфоліо")
    p_cols = st.columns(3)
    for idx, (_, row) in enumerate(df.nlargest(3, "_total").iterrows()):
        p_cols[idx].markdown(
            f'<div class="top-podium-card"><img src="{game_cover(row)}" style="width:100%; height:135px; object-fit:cover; border-radius:6px; margin-bottom:8px;">'
            f'<h4 style="margin:0 0 4px 0; color:#fff;">#{idx + 1} {row["Game_Name_Clean"]}</h4>'
            f'<p style="margin:0; font-size:18px; color:#34d399; font-weight:bold;">{fmt_usd(row["_total"], True)}</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_right = st.columns([1.15, 1.35])
    with c_left:
        st.subheader("🧩 Які жанри приносять гроші")
        render_genre_treemap(df)
    with c_right:
        st.subheader("🎮 Топ-15: на яких консолях тримається гра")
        render_top_stacked(df)

    # Замість «спагеті» з лінією на кожну гру — одна крива: реальний медіанний множник vs модель
    st.markdown("---")
    st.subheader("⏳ Крива життєвого циклу: факт vs модель")
    st.caption("Медіанний множник до M1 по іграх, у яких період уже повністю минув. Деталі по кожній грі — у вкладці «Інсайти».")
    curve = []
    for p in ["M3", "M6", "1Y"]:
        ratios = [it["facts"][p] / it["m1"] for it in items
                  if it["m1"] > 0 and it["facts"][p] and it["states"][p] in ("done", "unknown")]
        curve.append({"Період": p, "Факт (медіана)": round(pd.Series(ratios).median(), 2) if ratios else None,
                      "Модель": LTV_MULT[p], "Ігор": len(ratios)})
    curve_df = pd.DataFrame([{"Період": "M1", "Факт (медіана)": 1.0, "Модель": 1.0, "Ігор": None}] + curve)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve_df["Період"], y=curve_df["Модель"], name="Модель", mode="lines+markers",
                             line=dict(color="#d946ef", dash="dash")))
    fig.add_trace(go.Scatter(x=curve_df["Період"], y=curve_df["Факт (медіана)"], name="Факт (медіана)", mode="lines+markers+text",
                             text=[f"{v:.2f}x" if v else "" for v in curve_df["Факт (медіана)"]], textposition="top center",
                             line=dict(color="#34d399", width=3)))
    show_fig(fig, height=340, yaxis_title="× від M1")
    st.caption(" • ".join(f"{r['Період']}: {r['Ігор']} ігор" for r in curve))


def lifecycle_badge(m1):
    if m1 >= 3000:
        return ("🔥 Сильний старт", "rgba(16,185,129,0.2)", "#34d399",
                "Високий органічний попит. Рекомендовано тримати знижки не глибше 30–45% у перші 6 місяців.")
    if m1 >= 1000:
        return ("🟡 Стабільна динаміка", "rgba(56,189,248,0.2)", "#38bdf8",
                "Збалансований темп. Основний добір каси — між 3-м та 6-м місяцями на сезонних сейлах (60–70%).")
    return ("⚠️ Слабкий M1", "rgba(245,158,11,0.2)", "#fbbf24",
            "Органіки за фулпрайс недостатньо. Рекомендовано швидше виходити на імпульсну ціну ($1.99–$2.49) для потрапляння в 'Great Deals'.")


def dev_badge(dev):
    if dev is None:
        return ""
    if dev >= DEV_OK_BAND:
        color, bg = "#34d399", "rgba(16,185,129,0.18)"
    elif dev <= -DEV_OK_BAND:
        color, bg = "#f87171", "rgba(239,68,68,0.18)"
    else:
        color, bg = "#fbbf24", "rgba(245,158,11,0.16)"
    return f'<span style="background:{bg}; color:{color}; font-weight:700; padding:1px 6px; border-radius:4px; margin-left:4px;">{dev:+.0f}%</span>'


PRE_COLOR = "#f59e0b"
SPLIT_COLORS = {"Switch": ("#e60012", "#ff6b6b", "Switch"), "PS": ("#3b82f6", "#60a5fa", "PlayStation"), "Xbox": ("#107c10", "#4ade80", "Xbox")}


def trajectory_svg(it):
    """Міні-графік: прогноз від M1 (пунктир), прогноз до релізу (крапки) і факт (суцільна лінія)."""
    w, h, pad_x, pad_top, pad_bot = 210, 82, 14, 12, 18
    fc_vals = [it["m1"] or None] + [it["forecasts"].get(p) for p in ["M3", "M6", "1Y"]]
    pre_vals = [it["pre"]["forecasts"].get(p) for p in PERIODS]
    fact_vals = [it["facts"]["M1"]] + [it["facts"][p] if it["states"][p] != "future" else None for p in ["M3", "M6", "1Y"]]
    all_v = [v for v in fc_vals + pre_vals + fact_vals if v]
    if not all_v:
        return ""
    lo, hi = min(all_v), max(all_v)
    use_log = hi / lo > 8  # прогноз до релізу буває в десятки разів більший за факт — тоді лог-шкала, щоб було видно всі лінії
    if use_log:
        l_lo, l_hi = math.log(lo * 0.8), math.log(hi * 1.15)
        frac = lambda v: (math.log(v) - l_lo) / (l_hi - l_lo)
    else:
        frac = lambda v: v / (hi * 1.08)
    xs = [pad_x + i * (w - 2 * pad_x) / 3 for i in range(4)]
    y = lambda v: pad_top + (1 - frac(v)) * (h - pad_top - pad_bot)
    pts = lambda vals: " ".join(f"{xs[i]:.1f},{y(v):.1f}" for i, v in enumerate(vals) if v)
    fact_idx = [i for i, v in enumerate(fact_vals) if v]
    dots = "".join(
        f'<circle cx="{xs[i]:.1f}" cy="{y(fact_vals[i]):.1f}" r="3.2" '
        f'fill="{"#161622" if it["states"][PERIODS[i]] == "running" else "#34d399"}" stroke="#34d399" stroke-width="1.5"/>'
        for i in fact_idx
    )
    labels = "".join(f'<text x="{xs[i]:.1f}" y="{h - 4}" fill="#64748b" font-size="9" text-anchor="middle">{p}</text>' for i, p in enumerate(PERIODS))
    log_mark = f'<text x="{w - 2}" y="9" fill="#475569" font-size="8" text-anchor="end">log</text>' if use_log else ""
    lines = ""
    if any(pre_vals):
        lines += f'<polyline points="{pts(pre_vals)}" fill="none" stroke="{PRE_COLOR}" stroke-width="1.8" stroke-dasharray="1.5 3" stroke-linecap="round"/>'
    if any(fc_vals[1:]):
        lines += f'<polyline points="{pts(fc_vals)}" fill="none" stroke="#d946ef" stroke-width="1.8" stroke-dasharray="4 3"/>'
    if fact_idx:
        lines += f'<polyline points="{pts(fact_vals)}" fill="none" stroke="#34d399" stroke-width="2"/>'
    legend = []
    if any(fc_vals[1:]):
        legend.append('<span style="color:#d946ef;">┅</span> прогноз M1')
    if any(pre_vals):
        legend.append(f'<span style="color:{PRE_COLOR};">┈</span> до релізу')
    if fact_idx:
        legend.append('<span style="color:#34d399;">━</span> факт')
    return (
        '<div style="display:flex; flex-direction:column; align-items:center; flex-shrink:0;">'
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{lines}{dots}{labels}{log_mark}</svg>'
        '<div style="font-size:10px; color:#94a3b8; text-align:center; margin-top:2px; white-space:nowrap;">'
        + " &nbsp; ".join(legend) + "</div></div>"
    )


def platform_split_html(it):
    """Смуга розподілу доходу (All Time) по платформах."""
    vals = {p: it["plat_total"].get(p, 0.0) for p in PLATFORMS}
    total = sum(vals.values())
    head = '<div style="font-size:11px; color:#94a3b8; margin-bottom:2px;">Розподіл доходу (All Time)</div>'
    if total <= 0:
        body = '<div style="font-size:11px; color:#64748b; margin-top:6px;">Продажів ще немає</div>'
    else:
        segs = "".join(
            f'<div title="{SPLIT_COLORS[p][2]}: {fmt_usd(v)} ({v / total * 100:.0f}%)" '
            f'style="width:{v / total * 100:.2f}%; background:{SPLIT_COLORS[p][0]};"></div>'
            for p, v in vals.items() if v > 0)
        bar = f'<div style="display:flex; height:10px; border-radius:5px; overflow:hidden; background:#28283c; margin:6px 0 8px;">{segs}</div>'
        rows = "".join(
            f'<div style="display:flex; justify-content:space-between; gap:10px; font-size:11px; color:{"#cbd5e1" if v > 0 else "#475569"}; line-height:1.6;">'
            f'<span><span style="color:{SPLIT_COLORS[p][1]};">●</span> {SPLIT_COLORS[p][2]}</span>'
            f'<span>{fmt_usd(v)} · <b>{v / total * 100:.0f}%</b></span></div>'
            for p, v in vals.items())
        body = bar + rows
    return f'<div style="width:190px; flex-shrink:0;">{head}{body}</div>'


# ---------------- Картки інсайтів: факт + розгортання прогнозів ----------------
PERIOD_COLOR = {"M1": "#34d399", "M3": "#38bdf8", "M6": "#a855f7", "1Y": "#d946ef"}
LC_CHIP = ('<div class="lc-chip"><div style="color:#94a3b8;">{title}</div>'
           '<div style="color:{color}; font-size:14px; font-weight:700;">{value}</div>'
           '<div style="font-size:11px; color:#94a3b8; margin-top:2px;">{sub}</div></div>')
MUTED = '<span style="color:#64748b;">{}</span>'


def fact_chips_html(it):
    """Основний вигляд картки: лише фактичні продажі по періодах."""
    chips = []
    current = next((p for p in PERIODS if it["states"][p] == "running"), None)
    for p in PERIODS:
        v, s = it["facts"][p], it["states"][p]
        if s == "future":
            value, sub = "—", MUTED.format(f"вихід через {-it['days_live']} дн.")
        elif s == "running" and p != current:
            value, sub = "—", MUTED.format(f"дані через {PERIOD_DAYS[p] - it['days_live']} дн.")
        elif s == "running":
            value, sub = (fmt_usd(v) if v else "—"), MUTED.format(f"поки що · ще {PERIOD_DAYS[p] - it['days_live']} дн.")
        elif v:
            value, sub = fmt_usd(v), ("період завершено" if s == "done" else MUTED.format("дата релізу невідома"))
        else:
            value, sub = "—", MUTED.format("немає даних")
        chips.append(LC_CHIP.format(title=f"Факт {p}", color=PERIOD_COLOR[p] if value != "—" else "#475569", value=value, sub=sub))
    return '<div class="lc-chips" style="margin:10px 0;">' + "".join(chips) + "</div>"


def fact_line(it, p, dev):
    fact_v, st_p = it["facts"][p], it["states"][p]
    if st_p in ("done", "unknown") and fact_v:
        return f'Факт: <b style="color:#e2e8f0;">{fmt_usd(fact_v)}</b>{dev_badge(dev)}'
    if st_p == "running":
        now_v = f"{fmt_usd(fact_v)} · " if fact_v else ""
        return MUTED.format(f"Зараз: {now_v}ще {PERIOD_DAYS[p] - it['days_live']} дн.")
    if st_p == "future":
        return MUTED.format("Ще не вийшла")
    return MUTED.format("Факт: немає даних")


def lc_section(title, subtitle, body):
    return (f'<div class="lc-section"><div class="lc-section-title">{title}</div>'
            f'<div class="lc-section-sub">{subtitle}</div>{body}</div>')


def m1_forecast_html(it):
    title = "📈 Прогноз на основі M1"
    if it["m1"] <= 0:
        return lc_section(title, "База: факт першого місяця", MUTED.format("<i>Розрахується після появи продажів за перший місяць.</i>"))
    note = f"База: факт M1 {fmt_usd(it['m1'])}" + (" (місяць ще триває — прогноз попередній)" if it["states"]["M1"] == "running" else "")
    chips = "".join(LC_CHIP.format(title=f"Прогноз {p} ({LTV_MULT[p]:.2f}x)", color=PERIOD_COLOR[p],
                                   value=fmt_usd(it["forecasts"][p]), sub=fact_line(it, p, it["devs"][p]))
                    for p in ["M3", "M6", "1Y"])
    return lc_section(title, note, f'<div class="lc-chips">{chips}</div>')


def prerelease_html(it):
    pre = it["pre"]
    title = "🔮 Прогноз до релізу (дані з інших платформ)"
    if not pre["forecasts"]:
        return lc_section(title, "Steam / Google Play / CrazyGames / itch",
                          MUTED.format("<i>У каталозі немає вхідних метрик з платформ для цієї гри.</i>"))
    sub = (f"Джерело: {html.escape(pre['source']) or 'авто'} · база ${pre['base']:,.0f} · {pre['genre']} · "
           f"{' + '.join(PLATFORM_LABEL[p] for p in pre['platforms'])}")
    chips = "".join(LC_CHIP.format(title="Прогноз M1" if p == "M1" else f"Прогноз {p} ({LTV_MULT[p]:.2f}x)",
                                   color=PERIOD_COLOR[p], value=fmt_usd(pre["forecasts"][p]), sub=fact_line(it, p, pre["devs"][p]))
                    for p in PERIODS)
    return lc_section(title, sub, f'<div class="lc-chips">{chips}</div>')


def render_insights(items):
    st.subheader("🧠 Життєвий цикл та LTV (M1 ➔ M3 ➔ M6 ➔ 1Y)")
    st.caption(f"Картка показує фактичні продажі • Натисни «+», щоб побачити прогнози • Модель: M3 = {LTV_MULT['M3']}×M1 • "
               f"M6 = {LTV_MULT['M6']}×M1 • 1Y = {LTV_MULT['1Y']}×M1")

    f1, f2 = st.columns([1.3, 1])
    only_m1 = f1.checkbox("Показати тільки ігри з зафіксованим фактом M1", value=False)
    sort_mode = f2.selectbox("Сортування:", ["Як у таблиці", "Найбільше відхилення від прогнозу", "Найновіші релізи", "Найбільший M1"],
                             label_visibility="collapsed")

    cards = [it for it in items if it["m1"] > 0] if only_m1 else list(items)
    if sort_mode == "Найбільше відхилення від прогнозу":
        cards.sort(key=lambda it: abs(it["last_dev"]) if it["last_dev"] is not None else -1, reverse=True)
    elif sort_mode == "Найновіші релізи":
        cards.sort(key=lambda it: it["rel"] or date(1900, 1, 1), reverse=True)
    elif sort_mode == "Найбільший M1":
        cards.sort(key=lambda it: it["m1"], reverse=True)

    badge_tpl = '<span style="background:{bg}; color:{fg}; font-size:11px; font-weight:bold; padding:2px 8px; border-radius:5px;">{txt}</span>'

    for it in cards:
        m1 = it["m1"]
        price_tag = f"${it['price']:.2f}" if it["price"] > 0 else "—"
        if it["rel"]:
            live = f" · {it['days_live']} дн. у продажу" if it["days_live"] >= 0 else f" · вихід через {-it['days_live']} дн."
            rel_tag = f"Реліз: {it['rel'].strftime('%d.%m.%Y')}{live}"
        else:
            rel_tag = "Реліз: —"

        if m1 > 0:
            txt, bg, fg, base_text = lifecycle_badge(m1)
            badge = badge_tpl.format(bg=bg, fg=fg, txt=txt)
            if it["last_dev"] is not None:
                p, d = it["last_dev_p"], it["last_dev"]
                if d >= DEV_OK_BAND:
                    dev_text = f" 📈 Факт {p} випереджає модель на <b>{d:+.0f}%</b> — довгий хвіст сильніший за середній, з глибокими знижками можна не поспішати."
                elif d <= -DEV_OK_BAND:
                    dev_text = f" 📉 Факт {p} відстає від моделі на <b>{d:.0f}%</b> — хвіст продажів слабший, варто раніше підключати сейли та бандли."
                else:
                    dev_text = f" ✅ Факт {p} у межах ±{DEV_OK_BAND}% від моделі ({d:+.0f}%)."
            else:
                dev_text = f" Очікуваний річний LTV: <b>~{fmt_usd(it['forecasts']['1Y'])}</b>."
            insight = base_text + dev_text
            svg = trajectory_svg(it)
        else:
            badge = badge_tpl.format(bg="rgba(100,116,139,0.2)", fg="#94a3b8", txt="⏳ Очікує релізу / Немає M1")
            insight = "Звітних даних першого місяця ще немає. Прогноз до релізу (з даних інших платформ) — під кнопкою «+»."
            svg = trajectory_svg(it)

        toggle = ('<details class="lc-toggle"><summary title="Показати прогнози">+</summary>'
                  f'<div class="lc-panel">{m1_forecast_html(it)}{prerelease_html(it)}</div></details>')

        st.markdown(
            '<div class="lc-card">'
            f'<img src="{it["img"]}" style="width:85px; height:105px; object-fit:cover; border-radius:8px; flex-shrink:0;" onerror="this.src=\'{DEFAULT_IMAGE}\'">'
            '<div style="flex-grow:1; min-width:0;">'
            '<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; padding-right:40px;">'
            f'<h4 style="margin:0; color:#fff; font-size:16px;">🎮 {html.escape(it["name"])} '
            f'<span style="font-size:12px; color:#94a3b8; font-weight:normal;">(Ціна: {price_tag} · {rel_tag})</span></h4>{badge}</div>'
            f'<div style="display:flex; gap:18px; align-items:center; flex-wrap:wrap;"><div style="flex-grow:1;">{fact_chips_html(it)}</div>'
            f'<div style="display:flex; gap:22px; align-items:center; flex-wrap:wrap;">{svg}{platform_split_html(it)}</div></div>'
            '<div style="background:#0f0f17; border-left:3px solid #d946ef; border-radius:4px; padding:8px 12px; font-size:12px; color:#cbd5e1; line-height:1.4;">'
            f'💡 <b>Інсайт та рекомендація:</b> {insight}</div>'
            f'{toggle}</div></div>',
            unsafe_allow_html=True,
        )


def render_pnl():
    st.subheader("💵 Фінансовий P&L, зарплати портингу та роялті девелоперів")
    with st.expander("⚙️ Параметри комісій і податків (діють і в калькуляторі лідів)", expanded=False):
        s1, s2, s3 = st.columns(3)
        store, tax, default_split = finance_settings()
        # зберігаємо в окремі (не віджетні) ключі, щоб значення жили і на інших сторінках
        st.session_state["fin_store"] = s1.slider("Комісія сторів (%):", 15, 35, store, step=1)
        st.session_state["fin_tax"] = s2.slider("Податки та резерви (%):", 0, 15, tax, step=1)
        st.session_state["fin_split"] = s3.slider("Спліт девелопера за замовчуванням (%):", 0, 100, default_split, step=5,
                                                  help="Використовується, якщо в каталозі немає колонки Revenue Split для гри")
    store, tax, default_split = finance_settings()
    net_pct = (100 - store - tax) / 100.0

    rows = []
    for _, r in filtered_df.iterrows():
        gross = game_total(r)
        salary = clean_num_val(r.get(COL["porting"])) if COL["porting"] else 0.0
        split = clean_num_val(r.get(COL["split"])) if COL["split"] else 0.0
        split = split if split > 0 else default_split
        recoup = clean_num_val(r.get(COL["recoup"])) if COL["recoup"] else 0.0

        net = gross * net_pct
        if recoup > 0:
            recouped, distrib = min(net, recoup), max(0.0, net - recoup)
            royalty = distrib * split / 100
            margin = recouped + distrib * (1 - split / 100)
        else:
            royalty = net * split / 100
            margin = net * (1 - split / 100)
        rows.append({
            "Гра": r["Game_Name_Clean"], "Gross ($)": round(gross, 2), "Net у банку ($)": round(net, 2),
            "Зарплата розробника ($)": round(salary, 2), "Роялті автору ($)": round(royalty, 2),
            "🔥 Чистий прибуток студії ($)": round(margin - salary, 2),
            "ROI": round(margin / salary, 1) if salary > 0 else None,
        })
    pnl = pd.DataFrame(rows)
    if pnl.empty:
        st.info("Немає ігор у вибірці.")
        return
    p = st.columns(3)
    p[0].metric(f"Net у банку ({net_pct * 100:.0f}%)", fmt_usd(pnl["Net у банку ($)"].sum(), True))
    p[1].metric("Виплати роялті авторам", fmt_usd(pnl["Роялті автору ($)"].sum(), True))
    p[2].metric("🔥 Чистий прибуток Upscale Studio", fmt_usd(pnl["🔥 Чистий прибуток студії ($)"].sum(), True),
                f"Зарплати: {fmt_usd(pnl['Зарплата розробника ($)'].sum())}", delta_color="off")
    st.dataframe(pnl.sort_values("Gross ($)", ascending=False), hide_index=True, use_container_width=True, height=400,
                 column_config={"ROI": st.column_config.NumberColumn(format="%.1fx")})


def render_table_report(total_gross, plat_rev):
    st.subheader("📑 Повна фінансова таблиця портфоліо")
    cfg = {COL["cover"]: st.column_config.ImageColumn("Обкладинка", width="small")} if COL["cover"] else {}
    st.dataframe(filtered_df, column_config=cfg, use_container_width=True, height=420)
    csv_button(filtered_df, "📥 Експортувати дані (.CSV)", "console_sales_portfolio.csv")

    st.markdown("---")
    st.subheader("📄 One-Pager Executive звіт")
    cards = [("TOTAL CONSOLE GROSS", total_gross, "#38bdf8"), ("PLAYSTATION", plat_rev["PS"], "#60a5fa"),
             ("NINTENDO SWITCH", plat_rev["Switch"], "#f87171"), ("XBOX", plat_rev["Xbox"], "#4ade80")]
    cards_html = "".join(f'<div class="card"><div>{t}</div><div class="val" style="color:{c};">${v:,.0f}</div></div>' for t, v, c in cards)
    report = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Upscale Studio Executive Report</title>
<style>
body {{ background:#0f172a; color:#f8fafc; font-family:-apple-system, sans-serif; padding:30px; }}
.card {{ background:#1e293b; border:1px solid #334155; border-radius:10px; padding:16px; text-align:center; }}
.grid {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:15px; margin:20px 0; }}
.title {{ font-size:24px; font-weight:bold; }} .val {{ font-size:26px; font-weight:800; margin-top:6px; }}
</style></head><body>
<div style="display:flex; justify-content:space-between; border-bottom:1px solid #334155; padding-bottom:15px;">
<div><div class="title">UPSCALE STUDIO</div><div>Console Operations Executive Report</div></div>
<div><b>Date:</b> {datetime.now().strftime('%B %Y')}</div></div>
<div class="grid">{cards_html}</div></body></html>"""
    st.download_button("📥 Завантажити One-Pager (.HTML / PDF)", data=report,
                       file_name=f"Upscale_Studio_Executive_Report_{datetime.now().strftime('%Y_%m')}.html", mime="text/html")

# ==============================================================================
# 🎯 РОЗДІЛ 2: ЦІЛІ ТА KPI 2026
# ==============================================================================
GOAL_PERIODS = ["2026 (рік)", "Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026"]


def weekly_between(start, end):
    if weekly_df.empty:
        return weekly_df
    return weekly_df[weekly_df["Parsed_Date"].apply(lambda d: in_bounds(d, start, end))]


def render_goals_page():
    st.title("🎯 Цілі та KPI 2026")
    st.caption("Ціль на 2026 рік: **$500,000 консольної виручки** • Факт береться з тижневого листа Weekly Updates")
    if weekly_df.empty:
        st.warning("⚠️ Немає тижневих даних. Перевір `WEEKLY_SHEET_URL`.")
        return

    cur_q = f"Q{quarter_of(TODAY)} {TODAY.year}"
    period = st.radio("📌 Період:", GOAL_PERIODS, horizontal=True, key="goals_period",
                      **persisted("goals_period", GOAL_PERIODS, index=GOAL_PERIODS.index(cur_q) if cur_q in GOAL_PERIODS else 0))
    start, end = period_bounds(period)
    target = TARGETS_2026[period]
    fact = weekly_between(start, end)
    f_rev = float(fact["Total_Revenue"].sum())
    rev_pct = safe_pct(f_rev, target["Revenue"]) or 0.0

    # Темп: скільки мало бути зароблено на сьогодні, якщо рівномірно йти до цілі
    elapsed = min(1.0, max(0.0, ((TODAY - start).days + 1) / ((end - start).days + 1)))
    pace_target = target["Revenue"] * elapsed
    pace_pct = safe_pct(f_rev, pace_target) if pace_target else None
    color = "#10b981" if (pace_pct or 0) >= 95 or rev_pct >= 100 else ("#f59e0b" if (pace_pct or 0) >= 70 else "#ef4444")
    last_week = fact["Week"].iloc[-1] if not fact.empty else "—"

    st.markdown(f"""
    <div style="background:#171724; border:1px solid #2f2f45; border-radius:12px; padding:22px; margin:10px 0 15px 0;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div>
          <span style="font-size:12px; font-weight:600; color:#94a3b8; text-transform:uppercase;">Фінансовий таргет • {period}</span>
          <h2 style="margin:2px 0 0 0; color:#fff;">💰 Виручка: ${f_rev:,.0f} <span style="font-size:18px; color:#94a3b8; font-weight:normal;">/ ${target['Revenue']:,.0f}</span></h2>
          <p style="margin:4px 0 0 0; font-size:12px; color:#94a3b8;">Тижневих звітів: {len(fact)} (останній: {last_week}) • минуло {elapsed * 100:.0f}% періоду •
          очікувано на сьогодні: ${pace_target:,.0f}{f" • темп: <b style='color:{color};'>{pace_pct:.0f}% від графіка</b>" if pace_pct is not None and elapsed > 0 else ""}</p>
        </div>
        <div style="text-align:right;">
          <span style="font-size:28px; font-weight:800; color:{color};">{rev_pct:.1f}%</span>
          <p style="margin:0; font-size:12px; color:#94a3b8;">виконання плану</p>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)
    st.progress(min(rev_pct / 100.0, 1.0))
    if fact.empty and elapsed > 0:
        st.info("ℹ️ У тижневому листі ще немає звітів за цей період — факт поки нульовий.")

    st.subheader("🎮 Виконання плану за платформами")
    k = st.columns(3)
    plat_rows = []
    for i, p in enumerate(PLATFORMS):
        f_v = float(fact[f"{WEEKLY_PREFIX[p]}_Revenue"].sum())
        t_v = target[f"{WEEKLY_PREFIX[p]}_Revenue"]
        k[i].metric(PLATFORM_LABEL[p], fmt_usd(f_v), f"{safe_pct(f_v, t_v):.1f}% від цілі ({fmt_usd(t_v)})", delta_color="off")
        plat_rows += [{"Платформа": PLATFORM_LABEL[p], "Тип": "Факт", "$": f_v}, {"Платформа": PLATFORM_LABEL[p], "Тип": "План", "$": t_v}]

    st.subheader("🤝 BizDev воронка: план vs факт")
    b = st.columns(4)
    for i, (col, lbl) in enumerate([("Deals", "🤝 Deals"), ("Calls", "📞 Calls"), ("Contacts", "✉️ Contacts"), ("Leads", "🔍 Leads")]):
        f_v = int(fact[col].sum()) if col in fact.columns else 0
        b[i].metric(lbl, f"{f_v} / {target[col]}", f"{safe_pct(f_v, target[col]):.0f}% від цілі", delta_color="off")

    st.markdown("---")
    c1, c2 = st.columns([1.4, 1])
    with c1:
        st.subheader("📊 План vs факт по платформах ($)")
        show_fig(px.bar(pd.DataFrame(plat_rows), x="Платформа", y="$", color="Тип", barmode="group",
                        color_discrete_map={"Факт": "#10b981", "План": "#d946ef"}), height=360, xaxis_title="", yaxis_title="$")
    with c2:
        st.subheader("📋 Зведення по кварталах")
        rows = []
        for q in GOAL_PERIODS[1:]:
            qf = weekly_between(*period_bounds(q))
            f_q = float(qf["Total_Revenue"].sum())
            rows.append({"Квартал": q, "Факт ($)": f_q, "План ($)": TARGETS_2026[q]["Revenue"],
                         "Виконання (%)": safe_pct(f_q, TARGETS_2026[q]["Revenue"]),
                         "Угоди": f"{int(qf['Deals'].sum()) if 'Deals' in qf.columns else 0}/{TARGETS_2026[q]['Deals']}"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, column_config={
            "Факт ($)": st.column_config.NumberColumn(format="$%.0f"), "План ($)": st.column_config.NumberColumn(format="$%.0f"),
            "Виконання (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
        })

    st.markdown("---")
    render_year_end_forecast()


def render_year_end_forecast():
    """Прогноз виручки на 31.12 за поточним темпом + накопичувальний графік факт / план / прогноз."""
    st.subheader(f"🔮 На скільки закриємо {GOAL_YEAR} рік")
    year_start, year_end = date(GOAL_YEAR, 1, 1), date(GOAL_YEAR, 12, 31)
    year = weekly_between(year_start, year_end)
    if year.empty:
        st.info(f"У тижневому листі ще немає звітів за {GOAL_YEAR} рік — прогноз поки неможливий.")
        return

    covered_end = min(year["Parsed_Date"].iloc[-1].date() + timedelta(days=6), year_end)  # останній день, покритий звітами
    days_done = (covered_end - year_start).days + 1
    days_left = (year_end - covered_end).days

    c_ctrl, c_note = st.columns([1.3, 2.7])
    n_weeks = c_ctrl.select_slider("Поточний темп рахувати за останні:", options=[4, 8, 12, 26], value=8,
                                   format_func=lambda n: f"{n} тиж.", key="goal_pace_weeks")
    recent = year.tail(n_weeks)
    c_note.caption(f"Дані покривають період до **{covered_end:%d.%m.%Y}** • до кінця року лишилось **{days_left} дн.** • "
                   "Два сценарії: темп останніх тижнів (враховує свіжі релізи й сейли) і середній темп з початку року (згладжений).")

    year_target = TARGETS_2026[f"{GOAL_YEAR} (рік)"]

    def project(col, tgt):
        ytd = float(year[col].sum())
        rate_recent = float(recent[col].sum()) / (len(recent) * 7)
        rate_avg = ytd / days_done
        return {"ytd": ytd, "target": tgt, "week_now": rate_recent * 7,
                "recent": ytd + rate_recent * days_left, "avg": ytd + rate_avg * days_left,
                "week_need": max(0.0, tgt - ytd) / days_left * 7 if days_left > 0 else 0.0}

    tot = project("Total_Revenue", year_target["Revenue"])
    pct_recent = safe_pct(tot["recent"], tot["target"]) or 0.0
    pct_avg = safe_pct(tot["avg"], tot["target"]) or 0.0
    color = "#10b981" if pct_recent >= 100 else ("#f59e0b" if pct_recent >= 85 else "#ef4444")

    k = st.columns(4)
    kpi_card(k[0], f"Факт {GOAL_YEAR} (до {covered_end:%d.%m})", fmt_usd(tot["ytd"]),
             f"{safe_pct(tot['ytd'], tot['target']):.0f}% річної цілі")
    kpi_card(k[1], f"Прогноз на 31.12 · темп {n_weeks} тиж.", fmt_usd(tot["recent"]),
             f"{pct_recent:.0f}% від {fmt_usd(tot['target'])}", "badge-total", color)
    kpi_card(k[2], "Прогноз на 31.12 · середній темп року", fmt_usd(tot["avg"]),
             f"{pct_avg:.0f}% від {fmt_usd(tot['target'])}", "badge-ps", "#38bdf8")
    if tot["week_need"] <= 0:
        kpi_card(k[3], "Потрібно на тиждень до кінця року", "$0", "🎉 Ціль уже досягнута", "badge-xbox", "#4ade80")
    else:
        ratio = tot["week_need"] / tot["week_now"] if tot["week_now"] else None
        ratio_txt = f" · ×{ratio:.1f} від поточного" if ratio else ""
        kpi_card(k[3], "Потрібно на тиждень до кінця року", fmt_usd(tot["week_need"]),
                 f"зараз {fmt_usd(tot['week_now'])}/тиж{ratio_txt}",
                 "badge-xbox" if (ratio or 99) <= 1 else "badge-switch", "#4ade80" if (ratio or 99) <= 1 else "#f87171")

    gap = tot["recent"] - tot["target"]
    verdict = (f"При темпі останніх {n_weeks} тижнів рік закриється на **{fmt_usd(tot['recent'])}** — "
               + (f"це на **{fmt_usd(gap)} більше** за ціль." if gap >= 0 else f"це на **{fmt_usd(-gap)} менше** за ціль."))
    (st.success if gap >= 0 else st.warning if pct_recent >= 85 else st.error)(verdict)

    # ---- Накопичена виручка: план, факт і два сценарії прогнозу ----
    plan_pts, cum = [], 0.0
    for q in GOAL_PERIODS[1:]:
        qs, qe = period_bounds(q)
        plan_pts.append({"Дата": qs, "План": cum})
        cum += TARGETS_2026[q]["Revenue"]
        plan_pts.append({"Дата": qe, "План": cum})
    plan_df = pd.DataFrame(plan_pts)
    fact_x = year["Parsed_Date"] + pd.Timedelta(days=6)  # накопичене значення — на кінець тижня
    fact_y = year["Total_Revenue"].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plan_df["Дата"], y=plan_df["План"], name="План (накопичено)", line=dict(color="#d946ef", dash="dash")))
    fig.add_trace(go.Scatter(x=fact_x, y=fact_y, name="Факт (накопичено)", mode="lines+markers", line=dict(color="#10b981", width=3),
                             hovertemplate="%{x|%d.%m.%Y}<br>$%{y:,.0f}<extra>Факт</extra>"))
    if days_left > 0:
        fig.add_trace(go.Scatter(x=[covered_end, year_end], y=[tot["ytd"], tot["recent"]], name=f"Прогноз · темп {n_weeks} тиж.",
                                 mode="lines+markers+text", line=dict(color=color, width=2.5, dash="dot"),
                                 text=["", f"{fmt_usd(tot['recent'])}"], textposition="top left", textfont=dict(color=color, size=12),
                                 hovertemplate="%{x|%d.%m.%Y}<br>$%{y:,.0f}<extra>Прогноз (свіжий темп)</extra>"))
        fig.add_trace(go.Scatter(x=[covered_end, year_end], y=[tot["ytd"], tot["avg"]], name="Прогноз · середній темп року",
                                 mode="lines+markers+text", line=dict(color="#38bdf8", width=2, dash="dot"),
                                 text=["", f"{fmt_usd(tot['avg'])}"], textposition="bottom left", textfont=dict(color="#38bdf8", size=12),
                                 hovertemplate="%{x|%d.%m.%Y}<br>$%{y:,.0f}<extra>Прогноз (середній темп)</extra>"))
    fig.add_hline(y=tot["target"], line_dash="dot", line_color="#64748b",
                  annotation_text=f"Ціль {fmt_usd(tot['target'])}", annotation_position="top left", annotation_font_color="#94a3b8")
    today_vline(fig)
    show_fig(fig, height=420, yaxis_title="$", xaxis_title="", xaxis=dict(range=[year_start, year_end + timedelta(days=10)]))

    # ---- Прогноз по платформах ----
    rows = []
    for p in PLATFORMS:
        pr = project(f"{WEEKLY_PREFIX[p]}_Revenue", year_target[f"{WEEKLY_PREFIX[p]}_Revenue"])
        rows.append({"Платформа": PLATFORM_LABEL[p], "Факт YTD ($)": pr["ytd"], f"Прогноз 31.12 · {n_weeks} тиж. ($)": pr["recent"],
                     "Прогноз 31.12 · сер. темп ($)": pr["avg"], "Ціль ($)": pr["target"],
                     "Прогноз / ціль (%)": safe_pct(pr["recent"], pr["target"]),
                     "Темп зараз ($/тиж)": pr["week_now"], "Потрібно ($/тиж)": pr["week_need"]})
    money = st.column_config.NumberColumn(format="$%.0f")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, column_config={
        "Факт YTD ($)": money, f"Прогноз 31.12 · {n_weeks} тиж. ($)": money, "Прогноз 31.12 · сер. темп ($)": money,
        "Ціль ($)": money, "Темп зараз ($/тиж)": money, "Потрібно ($/тиж)": money,
        "Прогноз / ціль (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
    })


# ==============================================================================
# 📈 РОЗДІЛ 3: ДИНАМІКА ПРОДАЖІВ (гнучкі фільтри)
# ==============================================================================
FILTER_MODES = ["⚡ Останній тиждень", "↔️ Останні N тижнів", "🎯 Квартал / рік / місяць", "🗓️ Довільні дати", "📅 Весь період"]


def sales_filter_panel(all_dates):
    """Повертає (wk, start, end, label). wk — тижні, що потрапили у фільтр."""
    has_weekly = not weekly_df.empty
    modes = FILTER_MODES if has_weekly else FILTER_MODES[2:]
    c_mode, c_ctrl = st.columns([1.3, 2.7])
    mode = c_mode.radio("Формат вибору періоду:", modes, key="dyn_mode", **persisted("dyn_mode", modes))

    with c_ctrl:
        if mode == "⚡ Останній тиждень":
            wk = weekly_df.tail(1)
            start = wk["Parsed_Date"].iloc[0].date()
            end = start + timedelta(days=6)
            label = f"тиждень {wk['Week'].iloc[0]}"
        elif mode == "↔️ Останні N тижнів":
            total_w = len(weekly_df)
            n = st.slider("Кількість останніх тижнів:", 2, min(52, total_w), min(8, total_w), key="dyn_n") if total_w > 2 else total_w
            wk = weekly_df.tail(n)
            start, end = wk["Parsed_Date"].iloc[0].date(), wk["Parsed_Date"].iloc[-1].date() + timedelta(days=6)
            label = f"останні {len(wk)} тиж."
        elif mode == "🎯 Квартал / рік / місяць":
            label = period_picker(all_dates, key="dyn_period", label="Квартал, рік або місяць:", include_months=True)
            start, end = period_bounds(label)
            wk = weekly_between(start, end)
        elif mode == "🗓️ Довільні дати":
            ds = sorted(d for d in (to_date(x) for x in all_dates) if d)
            lo, hi = ds[0], max(ds[-1], TODAY)
            rng = st.date_input("Діапазон дат:", value=(max(lo, TODAY - timedelta(days=90)), hi), min_value=lo, max_value=hi + timedelta(days=365), key="dyn_dates")
            start, end = (rng[0], rng[1]) if isinstance(rng, (tuple, list)) and len(rng) == 2 else (lo, hi)
            wk = weekly_between(start, end)
            label = f"{start.strftime('%d.%m.%Y')} — {end.strftime('%d.%m.%Y')}"
        else:
            start = end = None
            wk = weekly_df
            label = "весь період"

        f1, f2, f3 = st.columns([1.8, 1.4, 1.4])
        plats = f1.multiselect("Платформи:", PLATFORMS, format_func=lambda p: PLATFORM_LABEL[p], key="dyn_plats", **persisted("dyn_plats", PLATFORMS, default=PLATFORMS)) or PLATFORMS
        group = f2.radio("Групування графіків:", ["Тижні", "Місяці", "Квартали"], horizontal=True, key="dyn_group", **persisted("dyn_group", ["Тижні", "Місяці", "Квартали"]))
        compare = f3.checkbox("Порівняти з попер. періодом", value=start is not None, disabled=start is None, key="dyn_compare")
    return wk, start, end, label, plats, group, compare and start is not None


def group_weekly(wk, group):
    """Агрегує тижні до місяців/кварталів (сумою); соцмережі не агрегуються — це накопичувальні значення."""
    if group == "Тижні" or wk.empty:
        return wk.assign(Період=wk["Week"])
    key = wk["Parsed_Date"].apply(lambda d: month_label(d) if group == "Місяці" else f"Q{quarter_of(d)} {d.year}")
    num_cols = [c for c in wk.columns if c not in ("From", "To", "Week", "Parsed_Date") + tuple(SOCIAL_COLS) and pd.api.types.is_numeric_dtype(wk[c])]
    out = wk.assign(Період=key).groupby("Період", sort=False)[num_cols].sum().reset_index()
    return out


def render_dynamics():
    st.title("📈 Динаміка продажів")
    st.caption("Тижнева звітність, BizDev воронка, соцмережі та помісячні звіти сторів • гнучкий вибір періоду, платформ і групування")

    n_matrix, n_months = parse_nintendo_monthly_data(load_sheet(NINTENDO_MONTHLY_SHEET_URL))
    x_matrix, x_months = parse_xbox_monthly_data(load_sheet(XBOX_MONTHLY_SHEET_URL))
    c_matrix, c_months = combine_monthly_matrices(n_matrix, x_matrix, n_months, x_months)

    all_dates = (list(weekly_df["Parsed_Date"]) if not weekly_df.empty else []) + [month_label_to_date(m) for m in c_months]
    if not all_dates:
        st.warning("⚠️ Немає ні тижневих, ні помісячних даних. Перевір `WEEKLY_SHEET_URL` та посилання на звіти сторів.")
        return

    try:
        box = st.container(border=True)
    except TypeError:  # старі версії Streamlit без border
        box = st.container()
    with box:
        wk, start, end, label, plats, group, compare = sales_filter_panel(all_dates)

    # ---- KPI з порівнянням з попереднім періодом такої ж довжини ----
    prev = pd.DataFrame()
    if compare and not weekly_df.empty:
        span = (end - start).days + 1
        prev = weekly_between(start - timedelta(days=span), start - timedelta(days=1))
    rev_cols = [f"{WEEKLY_PREFIX[p]}_Revenue" for p in plats]
    sales_cols = [f"{WEEKLY_PREFIX[p]}_Sales" for p in plats]

    def delta(cur, cols):
        if prev.empty:
            return None
        before = float(prev[cols].sum().sum())
        pct = safe_pct(cur - before, before)
        return f"{pct:+.1f}% vs попер. період" if pct is not None else None

    st.caption(f"Обрано: **{label}** • тижневих звітів: **{len(wk)}**" + (f" • попередній період для порівняння: {len(prev)} тиж." if compare else ""))
    if not wk.empty:
        k = st.columns(2 + len(plats))
        rev_total = float(wk[rev_cols].sum().sum())
        units_total = float(wk[sales_cols].sum().sum())
        k[0].metric("💰 Виторг", fmt_usd(rev_total, True), delta(rev_total, rev_cols))
        k[1].metric("📦 Продано копій", f"{int(units_total):,}", delta(units_total, sales_cols))
        for i, p in enumerate(plats, start=2):
            col = f"{WEEKLY_PREFIX[p]}_Revenue"
            k[i].metric(PLATFORM_LABEL[p], fmt_usd(float(wk[col].sum()), True), delta(float(wk[col].sum()), [col]))

    st.markdown("<br>", unsafe_allow_html=True)
    t_rev, t_funnel, t_month, t_social, t_table = st.tabs([
        "💰 Виторг і продажі", "🤝 BizDev воронка", "🗓️ Помісячно (звіти сторів)", "📱 Соцмережі", "📑 Таблиця",
    ])

    with t_rev:
        if wk.empty:
            st.info("Немає тижневих даних за обраний період.")
        else:
            g = group_weekly(wk, group)
            long_rev = g.melt(id_vars="Період", value_vars=rev_cols, var_name="Platform", value_name="Revenue")
            long_rev["Platform"] = long_rev["Platform"].map({f"{WEEKLY_PREFIX[p]}_Revenue": PLATFORM_LABEL[p] for p in PLATFORMS})
            st.subheader(f"Виторг ($) • {group.lower()}")
            fig = px.bar(long_rev, x="Період", y="Revenue", color="Platform", color_discrete_map=PLATFORM_COLORS)
            totals = g[rev_cols].sum(axis=1)
            fig.add_trace(go.Scatter(x=g["Період"], y=totals, mode="text", text=[f"${v:,.0f}" for v in totals],
                                     textposition="top center", showlegend=False, textfont=dict(color="#e2e8f0", size=11)))
            show_fig(fig, height=400, yaxis_title="Виторг ($)", xaxis_title="", xaxis=dict(type="category"))

            long_sales = g.melt(id_vars="Період", value_vars=sales_cols, var_name="Platform", value_name="Sales")
            long_sales["Platform"] = long_sales["Platform"].map({f"{WEEKLY_PREFIX[p]}_Sales": PLATFORM_LABEL[p] for p in PLATFORMS})
            st.subheader(f"Продажі в копіях • {group.lower()}")
            show_fig(px.line(long_sales, x="Період", y="Sales", color="Platform", markers=True, color_discrete_map=PLATFORM_COLORS),
                     height=360, yaxis_title="Копій (шт)", xaxis_title="", xaxis=dict(type="category"))

            wl_cols = [f"{WEEKLY_PREFIX[p]}_Wishlists" for p in plats if f"{WEEKLY_PREFIX[p]}_Wishlists" in g.columns]
            if wl_cols and g[wl_cols].sum().sum() > 0:
                long_wl = g.melt(id_vars="Період", value_vars=wl_cols, var_name="Platform", value_name="Wishlists")
                long_wl["Platform"] = long_wl["Platform"].map({f"{WEEKLY_PREFIX[p]}_Wishlists": PLATFORM_LABEL[p] for p in PLATFORMS})
                st.subheader(f"Вішлісти • {group.lower()}")
                show_fig(px.bar(long_wl, x="Період", y="Wishlists", color="Platform", barmode="group", color_discrete_map=PLATFORM_COLORS),
                         height=320, xaxis_title="", yaxis_title="", xaxis=dict(type="category"))

    with t_funnel:
        render_funnel(wk, group)

    with t_month:
        render_monthly(start, end, {"🔴 Nintendo eShop": (n_matrix, n_months, "#e60012"),
                                    "🟢 Xbox Store": (x_matrix, x_months, "#107c10"),
                                    "🌐 Всі консолі (Switch + Xbox)": (c_matrix, c_months, "#d946ef")})

    with t_social:
        cols = [c for c in SOCIAL_COLS if c in wk.columns and wk[c].sum() > 0]
        if wk.empty or not cols:
            st.info("Немає даних соцмереж за обраний період.")
        else:
            st.subheader("📱 Ріст аудиторії та соцмереж (по тижнях)")
            sel_social = st.multiselect("Мережі:", cols, default=cols, key="dyn_social") or cols
            show_fig(px.line(wk, x="Week", y=sel_social, markers=True), height=380, xaxis_title="", yaxis_title="",
                     xaxis=dict(type="category"))
            first, last = wk.iloc[0], wk.iloc[-1]
            s = st.columns(len(sel_social))
            for i, c in enumerate(sel_social):
                s[i].metric(c, f"{int(last[c]):,}", f"{int(last[c] - first[c]):+,} за період")

    with t_table:
        if wk.empty:
            st.info("Немає тижневих даних за обраний період.")
        else:
            table = wk.drop(columns=["Parsed_Date"])
            st.dataframe(table, use_container_width=True, height=450, hide_index=True)
            csv_button(table, "📥 Експортувати тижневий звіт (.CSV)", "upscale_weekly_reporting.csv")


def render_funnel(wk, group="Тижні"):
    st.subheader("🎯 Воронка залучення проєктів (Leads ➔ Deals)")
    present = [s for s in FUNNEL_STAGES if s[0] in wk.columns]
    if wk.empty or not present:
        st.info("Немає даних воронки за обраний період.")
        return
    totals = {s[0]: float(wk[s[0]].sum()) for s in present}
    cols = st.columns(len(present))
    prev = None
    for i, (key, lbl, _) in enumerate(present):
        conv = safe_pct(totals[key], totals[prev]) if prev else None
        cols[i].metric(lbl, f"{int(totals[key]):,}", f"{conv:.1f}% від попер. етапу" if conv is not None else None, delta_color="off")
        prev = key
    st.caption("Конверсія рахується лише з реальних даних; якщо на попередньому етапі 0 — показується без %.")

    fig = go.Figure(go.Funnel(
        y=[f"{lbl} ({desc})" for _, lbl, desc in present], x=[totals[k] for k, _, _ in present],
        textinfo="value+percent initial+percent previous",
        marker=dict(color=["#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#f59e0b", "#10b981"][:len(present)]),
        connector={"line": {"color": "#475569", "width": 1.5}},
    ))
    show_fig(fig, height=380)

    st.subheader(f"📊 Динаміка воронки • {group.lower()}")
    g = group_weekly(wk, group)
    show_fig(px.bar(g, x="Період", y=[k for k, _, _ in present], barmode="group",
                    color_discrete_sequence=["#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#f59e0b", "#10b981"]),
             height=380, xaxis_title="", yaxis_title="", xaxis=dict(type="category"))


def month_overlaps(label, start, end):
    m_start = month_label_to_date(label)
    if m_start is None:
        return False
    m_end = date(m_start.year, m_start.month, calendar.monthrange(m_start.year, m_start.month)[1])
    return (start is None or m_end >= start) and (end is None or m_start <= end)


def render_revenue_heatmap(matrix, months):
    h1, h2 = st.columns([1.6, 1.4])
    h1.subheader("🔥 Теплова карта виторгу (топ-20)")
    mode = h2.radio("Шкала:", ["💵 Абсолютні $", "📐 Сезонність (% від піку гри)"], horizontal=True,
                    key="heat_mode", label_visibility="collapsed", **persisted("heat_mode", ["💵 Абсолютні $", "📐 Сезонність (% від піку гри)"]))
    heat = matrix.set_index("Назва гри / DLC")[months]
    heat = heat.loc[heat.sum(axis=1).sort_values(ascending=False).index[:20]]
    if heat.empty:
        return

    normalized = mode.startswith("📐")
    if normalized:
        z = heat.div(heat.max(axis=1).replace(0, float("nan")), axis=0).fillna(0.0) * 100
        hover = "<b>%{y}</b><br>%{x}: $%{customdata:,.0f}<br>%{z:.0f}% від найкращого місяця гри<extra></extra>"
        colorbar = dict(title="% піку", ticksuffix="%")
        st.caption("Кожен рядок масштабовано до найкращого місяця цієї гри (= 100%) — видно сезонність і згасання кожного тайтлу, "
                   "незалежно від його розміру. Абсолютні суми — у підказці.")
    else:
        z = heat
        hover = "<b>%{y}</b><br>%{x}: $%{customdata:,.0f}<extra></extra>"
        colorbar = dict(title="$")
    fig = go.Figure(go.Heatmap(z=z.values, x=list(heat.columns), y=list(heat.index), customdata=heat.values,
                               colorscale="Purples", hovertemplate=hover, xgap=1, ygap=1, colorbar=colorbar))
    show_fig(fig, height=max(320, 26 * len(heat) + 80), yaxis=dict(autorange="reversed"), xaxis=dict(type="category"))


def render_monthly(start, end, sources):
    c1, c2 = st.columns([2, 1.2])
    plat_choice = c1.radio("Платформа:", list(sources.keys()), horizontal=True, key="monthly_platform", **persisted("monthly_platform", list(sources.keys())))
    matrix, months, accent = sources[plat_choice]
    if matrix.empty or not months:
        st.info("Немає даних помісячного звіту для цієї платформи. Перевір посилання на звіт.")
        return

    # Місяці з основного фільтра, але їх можна підправити вручну
    default_months = [m for m in months if month_overlaps(m, start, end)] or [months[-1]]
    sel_months = c2.multiselect("Місяці (з фільтра періоду, можна змінити):", months, default=default_months, key=f"monthly_sel_{start}_{end}") or default_months
    sel_months = [m for m in months if m in sel_months]
    if not any(month_overlaps(m, start, end) for m in months):
        st.caption(f"ℹ️ За обраним періодом у звіті місяців немає — показано останній. Доступно: {months[0]} — {months[-1]}.")
    period_lbl = sel_months[0] if len(sel_months) == 1 else f"{sel_months[0]} ➔ {sel_months[-1]}"

    view = matrix[["Назва гри / DLC"] + sel_months].copy()
    view["Виторг за період ($)"] = view[sel_months].sum(axis=1)
    view["All-Time ($)"] = matrix["Всього ($)"]
    view = view[view["Виторг за період ($)"] > 0].sort_values("Виторг за період ($)", ascending=False).reset_index(drop=True)
    total = float(view["Виторг за період ($)"].sum())
    view["Частка (%)"] = view["Виторг за період ($)"] / total * 100 if total else 0.0

    k = st.columns(4)
    kpi_card(k[0], f"Виторг ({period_lbl})", fmt_usd(total, True), f"{len(sel_months)} міс.")
    kpi_card(k[1], "Активних тайтлів", len(view), "З продажами", "badge-ps")
    kpi_card(k[2], "Лідер періоду", view.iloc[0]["Назва гри / DLC"] if not view.empty else "—",
             fmt_usd(view.iloc[0]["Виторг за період ($)"], True) if not view.empty else "", "badge-xbox", "#38bdf8")
    kpi_card(k[3], "Каса платформи All-Time", fmt_usd(matrix["Всього ($)"].sum(), True), "Повна база", "badge-switch")

    if not view.empty:
        st.subheader(f"🏆 Топ-10 за період ({period_lbl})")
        fig = px.bar(view.head(10), x="Виторг за період ($)", y="Назва гри / DLC", orientation="h", text="Виторг за період ($)",
                     color_discrete_sequence=[accent])
        fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", cliponaxis=False)
        show_fig(fig, height=380, yaxis=dict(autorange="reversed", title=""))

    money = {c: st.column_config.NumberColumn(c, format="$%.2f") for c in sel_months + ["Виторг за період ($)", "All-Time ($)"]}
    money["Частка (%)"] = st.column_config.NumberColumn(format="%.1f%%")
    st.dataframe(view, column_config=money, use_container_width=True, height=400, hide_index=True)
    slug = "nintendo" if "Nintendo" in plat_choice else "xbox" if "Xbox" in plat_choice else "all"
    csv_button(view, "📥 Звіт за період (.CSV)", f"{slug}_revenue_{period_lbl.replace(' ➔ ', '_')}.csv")

    render_revenue_heatmap(matrix, sel_months if len(sel_months) >= 2 else months)

    st.subheader("📈 Тренд окремої гри")
    game = st.selectbox("Гра:", matrix["Назва гри / DLC"].tolist(), key="monthly_trend_game")
    row = matrix[matrix["Назва гри / DLC"] == game].iloc[0]
    trend = pd.DataFrame({"Місяць": months, "Виторг ($)": [row[m] for m in months]})
    fig = px.bar(trend, x="Місяць", y="Виторг ($)", text="Виторг ($)", color_discrete_sequence=[accent])
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", cliponaxis=False)
    show_fig(fig, height=350, xaxis_title="")

    with st.expander("📑 Повна помісячна матриця за всі місяці"):
        st.dataframe(matrix, use_container_width=True, height=420, hide_index=True,
                     column_config={c: st.column_config.NumberColumn(c, format="$%.2f") for c in months + ["Всього ($)"]})
        csv_button(matrix, "📥 Повна матриця (.CSV)", f"{slug}_monthly_usd_matrix.csv", key="full_matrix_csv")

# ==============================================================================
# 📅 РОЗДІЛ 3: КАЛЕНДАР І СЕЙЛИ
# ==============================================================================
EVENT_STYLE = {
    "release": ("pill-release", "#a855f7"), "nintendo": ("pill-nintendo", "#e60012"),
    "xbox": ("pill-xbox", "#107c10"), "deadline": ("pill-deadline", "#f59e0b"),
}
EVENT_TYPE_LABEL = {"release": "🎮 Реліз", "nintendo": "🔴 Nintendo сейл", "xbox": "🟢 Xbox сейл", "deadline": "⏰ Дедлайн подачі"}
CAL_MAX_LANES = 4  # скільки смуг подій влазить у тиждень; решта — «+ ще N»


def build_calendar_events():
    """Кожна подія має start/end — сейл зберігається одним записом, а не окремо на кожен день."""
    events, seen = [], set()
    for _, r in raw_df.iterrows():
        d = game_release(r)
        if d:
            name = r["Game_Name_Clean"]
            seen.add((name.lower(), d))
            events.append({"start": d, "end": d, "type": "release", "title": f"🎮 Реліз: {name}", "desc": f"Вихід гри {name} на консолях"})
    if not pipe_df.empty:
        for _, pr in pipe_df.iterrows():
            d = to_date(pr["_d_release"])
            if d and (pr["Гра"].lower(), d) not in seen:
                events.append({"start": d, "end": d, "type": "release", "title": f"🚀 Реліз NSW: {pr['Гра']}",
                               "desc": f"Плановий вихід порту (розробник: {pr['Розробник']})"})
    for s in NINTENDO_SCHEDULE:
        a, b = sale_dates(s)
        events.append({"start": a, "end": b, "type": "nintendo", "title": f"🔴 NSW: {s['name']}", "desc": f"Розпродаж Nintendo eShop ({s['region']})"})
    for s in XBOX_SCHEDULE:
        a, b = sale_dates(s)
        events.append({"start": a, "end": b, "type": "xbox", "title": f"🟢 XB: {s['name']}", "desc": f"Xbox Sale: {s['note']}"})
        dl = datetime.strptime(s["deadline"], "%Y-%m-%d").date()
        events.append({"start": dl, "end": dl, "type": "deadline", "title": f"⏰ ДЕДЛАЙН: {s['name']}",
                       "desc": f"Крайній строк подачі в Microsoft. {s['note']}"})
    return events


def event_dates_str(e):
    return e["start"].strftime("%d.%m.%Y") if e["start"] == e["end"] else f"{e['start'].strftime('%d.%m')} – {e['end'].strftime('%d.%m.%Y')}"


def render_calendar_section():
    st.title("📅 Календар релізів і розпродажів")
    st.caption("Релізи портфоліо й пайплайну, сейли Nintendo/Xbox і дедлайни подачі — плюс інструменти підготовки сейлів")
    t_cal, t_ns, t_xb = st.tabs(["📅 Календар", "🔴 Сейл Nintendo (bookmarklet)", "🟢 Сейл Xbox (подача)"])
    with t_cal:
        render_calendar(build_calendar_events())
    with t_ns:
        render_nintendo_sale()
    with t_xb:
        render_xbox_sale()


def calendar_week_html(week, sel_m, events):
    """Один тиждень місячної сітки: фон днів + смуги подій, розкладені по доріжках (lanes)."""
    ws, we = week[0], week[-1]
    segs = []
    for e in events:
        if e["end"] < ws or e["start"] > we:
            continue
        s, en = max(e["start"], ws), min(e["end"], we)
        segs.append({"e": e, "c0": (s - ws).days, "c1": (en - ws).days, "cl": e["start"] < ws, "cr": e["end"] > we})
    # довші події та сейли — у верхні доріжки, щоб смуги не «стрибали» між рядками
    segs.sort(key=lambda g: (g["c0"], -(g["c1"] - g["c0"]), g["e"]["type"] == "release"))

    lane_end = []
    for g in segs:
        for i, last in enumerate(lane_end):
            if last < g["c0"]:
                lane_end[i], g["lane"] = g["c1"], i
                break
        else:
            lane_end.append(g["c1"])
            g["lane"] = len(lane_end) - 1

    n_lanes = min(len(lane_end), CAL_MAX_LANES)
    hidden = [0] * 7
    for g in segs:
        if g["lane"] >= CAL_MAX_LANES:
            for c in range(g["c0"], g["c1"] + 1):
                hidden[c] += 1
    rows_tpl = f"24px repeat({n_lanes}, 21px) minmax(16px, 1fr)" if n_lanes else "24px minmax(16px, 1fr)"
    more_row = n_lanes + 2

    cells = []
    for i, day in enumerate(week):
        cls = ("other-month" if day.month != sel_m.month else "") + (" today" if day == TODAY else "")
        cells.append(f'<div class="cal-bg {cls}" style="grid-column:{i + 1}; grid-row:1 / -1;"></div>')
    for i, day in enumerate(week):
        cls = ("other-month" if day.month != sel_m.month else "") + (" today" if day == TODAY else "")
        cells.append(f'<div class="cal-num {cls}" style="grid-column:{i + 1}; grid-row:1;">{day.day}</div>')
        if hidden[i]:
            cells.append(f'<div class="cal-more" style="grid-column:{i + 1}; grid-row:{more_row};">+ ще {hidden[i]}</div>')
    for g in segs:
        if g["lane"] >= CAL_MAX_LANES:
            continue
        e = g["e"]
        cls = f'cal-bar {EVENT_STYLE[e["type"]][0]}' + (" cont-left" if g["cl"] else "") + (" cont-right" if g["cr"] else "")
        tip = html.escape(f'{e["title"]} • {event_dates_str(e)} • {e["desc"]}', quote=True)
        label = ("◂ " if g["cl"] else "") + html.escape(e["title"]) + (" ▸" if g["cr"] else "")
        cells.append(f'<div class="{cls}" title="{tip}" style="grid-column:{g["c0"] + 1} / {g["c1"] + 2}; grid-row:{g["lane"] + 2};">{label}</div>')
    return f'<div class="cal-week" style="grid-template-rows:{rows_tpl};">' + "".join(cells) + "</div>"


def render_calendar_timeline(events):
    lo, hi = TODAY - timedelta(days=7), TODAY + timedelta(days=90)
    rows = sorted([e for e in events if e["end"] >= lo and e["start"] <= hi], key=lambda e: (e["start"], e["end"]))
    if not rows:
        st.info("💡 Найближчі 90 днів подій немає.")
        return
    df = pd.DataFrame([{
        "Подія": e["title"], "Start": pd.Timestamp(e["start"]), "End": pd.Timestamp(e["end"] + timedelta(days=1)),
        "Тип": EVENT_TYPE_LABEL[e["type"]], "Дати": event_dates_str(e), "Опис": e["desc"],
    } for e in rows])
    fig = px.timeline(df, x_start="Start", x_end="End", y="Подія", color="Тип",
                      color_discrete_map={EVENT_TYPE_LABEL[t]: EVENT_STYLE[t][1] for t in EVENT_STYLE},
                      hover_data={"Дати": True, "Опис": True, "Start": False, "End": False, "Тип": False, "Подія": False})
    fig.update_yaxes(autorange="reversed", title="", tickfont=dict(size=11))
    today_vline(fig, line_dash="dash")
    show_fig(fig, height=max(320, 26 * len(df) + 110), xaxis=dict(type="date", range=[lo, hi]))


def render_calendar(events):
    # Місяці генеруються від реальних подій (± поточний місяць), а не жорстким списком
    first = min([e["start"] for e in events] + [TODAY]).replace(day=1)
    last = max([e["end"] for e in events] + [TODAY]).replace(day=1)
    months = []
    cur = first
    while cur <= last:
        months.append(cur)
        cur = date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1)
    cur_m = TODAY.replace(day=1)

    c1, c2, c3 = st.columns([1.5, 1.7, 2.3])
    sel_m = c1.selectbox("🗓️ Місяць:", months, index=months.index(cur_m), format_func=month_label, key="cal_month")
    flt = c2.radio("Фільтр:", ["Всі події", "🎮 Релізи", "🏷️ Сейли й дедлайни"], horizontal=True, key="cal_filter", **persisted("cal_filter", ["Всі події", "🎮 Релізи", "🏷️ Сейли й дедлайни"]))
    view = c3.radio("Вигляд:", ["📅 Місяць", "📊 Таймлайн 90 днів", "📋 Список (Agenda)"], horizontal=True, key="cal_view", **persisted("cal_view", ["📅 Місяць", "📊 Таймлайн 90 днів", "📋 Список (Agenda)"]))

    if flt == "🎮 Релізи":
        events = [e for e in events if e["type"] == "release"]
    elif flt == "🏷️ Сейли й дедлайни":
        events = [e for e in events if e["type"] != "release"]

    m_start = sel_m
    m_end = date(sel_m.year, sel_m.month, calendar.monthrange(sel_m.year, sel_m.month)[1])

    if view == "📅 Місяць":
        legend = "".join(f'<span><span style="color:{c};">●</span> {t}</span>' for t, c in
                         [("Релізи", "#a855f7"), ("Nintendo сейли", "#ff4d4f"), ("Xbox сейли", "#52c41a"), ("Дедлайни подачі", "#faad14")])
        parts = ['<div class="cal-container">',
                 f'<div style="padding:14px 20px; background:#1a1a27; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #28283c;">'
                 f'<h3 style="margin:0; color:#fff; font-size:18px; font-weight:800;">{month_label(sel_m)}</h3>'
                 f'<div style="font-size:12px; color:#94a3b8; display:flex; gap:14px;">{legend}</div></div>',
                 '<div class="cal-header">' + "".join(
                     '<div class="cal-header-cell"' + (' style="color:#ff6b6b;"' if i >= 5 else "") + f">{d}</div>"
                     for i, d in enumerate(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"])) + "</div>"]
        for week in calendar.Calendar(firstweekday=0).monthdatescalendar(sel_m.year, sel_m.month):
            parts.append(calendar_week_html(week, sel_m, events))
        parts.append("</div>")
        st.markdown("".join(parts), unsafe_allow_html=True)
        st.caption("Наведи на смугу, щоб побачити дати й опис • ◂ ▸ — подія триває з попереднього / на наступний тиждень")
    elif view == "📊 Таймлайн 90 днів":
        st.caption("Від тижня тому до +90 днів від сьогодні • вибір місяця тут не діє")
        render_calendar_timeline(events)
    else:
        agenda = sorted([e for e in events if e["start"] <= m_end and e["end"] >= m_start], key=lambda e: e["start"])
        if not agenda:
            st.info("💡 У цьому місяці немає подій.")
        for e in agenda:
            diff = (e["start"] - TODAY).days
            if e["start"] <= TODAY <= e["end"]:
                countdown, cd_color = ("🔥 СЬОГОДНІ" if e["start"] == e["end"] else "🔥 Йде зараз"), "#34d399"
            elif diff > 0:
                countdown, cd_color = f"⏳ Через {diff} дн.", "#34d399"
            else:
                countdown, cd_color = f"Минуло {(TODAY - e['end']).days} дн. тому", "#64748b"
            st.markdown(
                f'<div style="background:#171724; border:1px solid #28283c; border-left:5px solid {EVENT_STYLE[e["type"]][1]}; border-radius:8px; '
                f'padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">'
                f'<div><b style="color:#fff; font-size:15px;">{e["title"]}</b><p style="margin:2px 0 0 0; font-size:12px; color:#94a3b8;">{e["desc"]}</p></div>'
                f'<div style="text-align:right;"><span style="font-size:14px; font-weight:700; color:#fff;">{event_dates_str(e)}</span><br>'
                f'<span style="font-size:11px; font-weight:bold; color:{cd_color};">{countdown}</span></div></div>',
                unsafe_allow_html=True,
            )


def sales_timeline(schedule, color_key=None, color_map=None, height=240):
    df = pd.DataFrame([{"Сейл": s["name"], "Початок": s["start"], "Кінець": s["end"], "Статус": sale_status(s),
                        "Тип": s.get("type", "")} for s in schedule])
    fig = px.timeline(df, x_start="Початок", x_end="Кінець", y="Сейл", color=color_key or "Статус", color_discrete_map=color_map)
    fig.update_yaxes(autorange="reversed", title="")
    today_vline(fig, line_dash="dash")
    show_fig(fig, height=height)


# Країни, де eShop приймає лише ціни, кратні 0.25. Рядок країни в таблиці Nintendo шукається за цим виразом
# (код валюти або назва країни). Ціна округлюється ВНИЗ, щоб знижка не стала меншою за задану.
QUARTER_PRICE_RE = r"\b(DKK|ZAR)\b|Denmark|Danmark|Dänemark|South Africa|Südafrika|Sydafrika"

# Мінімальна ціна зі знижкою, яку приймає Nintendo (з повідомлень порталу). Якщо розрахована ціна нижча —
# ставимо мінімум; якщо мінімум не нижчий за звичайну ціну — знижку в цій країні не робимо.
# Нові обмеження додавай сюди: "КОД_ВАЛЮТИ": мінімальна_ціна.
MIN_SALE_PRICES = {"USD": 1.99, "CAD": 2.79, "MXN": 42.99, "BRL": 11.99, "ARS": 2799.99,
                   "CLP": 1990, "COP": 8600, "PEN": 7.49}
# Валюти без копійок: ціни в них — цілі числа, а крапка чи кома — це роздільник тисяч (1.908 CLP = 1908).
ZERO_DECIMAL_CURRENCIES = ["CLP", "COP", "JPY", "KRW", "TWD", "IDR", "VND"]

BOOKMARKLET_TEMPLATE = r"""javascript:(function(){
const discounts = __DISCOUNTS__;
const quarterRe = new RegExp(__QUARTER_RE__, "i");
const minPrices = __MIN_PRICES__;
const zeroDec = __ZERO_DEC__;
const known = new Set(Object.keys(minPrices).concat(zeroDec, ["EUR","GBP","AUD","NZD","CHF","SEK","NOK","DKK","PLN","CZK","ZAR","HKD","SGD","THB","MYR","PHP","RUB","HUF"]));
function rowCurrency(row){const m=((row&&row.innerText)||"").match(/\b[A-Z]{3}\b/g)||[];for(const c of m){if(known.has(c))return c;}return null;}
function parsePrice(text,cur){let s=text.trim().replace(/[^0-9.,]/g,'');if(!s)return null;
 if(zeroDec.includes(cur))return parseInt(s.replace(/[.,]/g,''),10);
 if(s.includes('.')&&s.includes(',')){if(s.lastIndexOf('.')<s.lastIndexOf(',')){s=s.replace(/\./g,'').replace(',','.');}else{s=s.replace(/,/g,'');}}
 else{const sep=s.includes(',')?',':(s.includes('.')?'.':null);if(sep){const parts=s.split(sep);if(parts.length>2||parts[parts.length-1].length===3){s=parts.join('');}else{s=parts.join('.');}}}
 return parseFloat(s);}
function getGameTitle(el){let current=el;while(current&&current!==document.body){let prev=current.previousElementSibling;while(prev){let text=prev.innerText||"";if(text.includes('HAC-')&&text.includes(':')){let rawTitle=text.substring(text.indexOf(':')+1).trim();rawTitle=rawTitle.replace(/\s*\(\d+\/\d+\)\s*$/,'').trim();return rawTitle;}prev=prev.previousElementSibling;}current=current.parentElement;}return null;}
const sortedKeys=Object.keys(discounts).sort((a,b)=>b.length-a.length);
const inputs=Array.from(document.querySelectorAll('input[type="text"]')).filter(inp=>{const td=inp.closest('td');if(!td)return false;const prevTd=td.previousElementSibling;return prevTd&&/[\d]/.test(prevTd.innerText);});
let updatedCount=0,quarterCount=0;const raised=[],skipped=[];
inputs.forEach(priceInput=>{
 const td=priceInput.closest('td');const regularPriceTd=td.previousElementSibling;if(!regularPriceTd)return;
 const row=priceInput.closest('tr');const cur=rowCurrency(row);
 const country=(row&&row.cells&&row.cells[0])?row.cells[0].innerText.trim():(cur||"?");
 const regularPrice=parsePrice(regularPriceTd.innerText,cur);if(regularPrice===null||isNaN(regularPrice)||regularPrice<=0)return;
 let gameTitle=getGameTitle(priceInput)||"Default";let cleanTitle=gameTitle.toLowerCase().replace(/\s+/g,' ').trim();
 let discountPercent=70;let matched=false;for(let k of sortedKeys){if(cleanTitle===k){discountPercent=discounts[k];matched=true;break;}}
 if(!matched){for(let k of sortedKeys){if(cleanTitle.includes(k)||k.includes(cleanTitle)){discountPercent=discounts[k];break;}}}
 const minP=(cur&&minPrices[cur]!=null)?minPrices[cur]:null;
 if(minP!==null&&minP>=regularPrice){skipped.push(country+" ("+gameTitle+")");return;}
 const raw=regularPrice*(1-(discountPercent/100));let v,mode;
 if(zeroDec.includes(cur)){v=Math.floor(raw+1e-9);mode="int";}
 else if(row&&quarterRe.test(row.innerText)){v=Math.floor(raw*4+1e-9)/4;mode="2dp";quarterCount++;}
 else if(cur||regularPriceTd.innerText.includes(',')||regularPriceTd.innerText.includes('.')){v=Math.floor(raw*100+1e-6)/100;mode="2dp";}
 else{v=Math.floor(raw+1e-9);mode="int";}
 if(minP!==null&&v<minP){v=minP;raised.push(country);}
 const finalPriceStr=mode==="int"?String(Math.round(v)):v.toFixed(2);
 priceInput.value=finalPriceStr;priceInput.dispatchEvent(new Event('input',{bubbles:true}));priceInput.dispatchEvent(new Event('change',{bubbles:true}));
 if(row){const checkbox=row.querySelector('input[type="checkbox"]');if(checkbox&&!checkbox.checked){checkbox.click();}}
 updatedCount++;});
let msg="🎉 Заповнено цін: "+updatedCount;
if(quarterCount)msg+="\nОкруглено до кратних 0.25 (Данія, ПАР): "+quarterCount;
if(raised.length)msg+="\nПідняли до мінімальної ціни Nintendo (знижка менша за задану): "+raised.join(", ");
if(skipped.length)msg+="\nПропущено — звичайна ціна вже не вища за мінімальну, знижка неможлива: "+skipped.join(", ");
alert(msg);
})();"""


def sheet_discount(r, minimum=0):
    v = clean_num_val(r.get(COL["discount"])) if COL["discount"] else 0.0
    v = int(round(v)) if v > 0 else 70
    return max(v, minimum)


def render_nintendo_sale():
    st.subheader("🔴 Підготовка розпродажу Nintendo eShop")
    sales_timeline(NINTENDO_SCHEDULE)

    idx = default_sale_index(NINTENDO_SCHEDULE, key_date="end")
    names = [f"{s['name']} — {sale_status(s)}" for s in NINTENDO_SCHEDULE]
    choice = st.selectbox("Сейл:", range(len(names)), index=idx, format_func=lambda i: names[i], key="ns_sale")
    sale_start = sale_dates(NINTENDO_SCHEDULE[choice])[0]

    rows = []
    for _, r in raw_df.iterrows():
        rel = game_release(r)
        if rel is None:
            ready, status = False, "⚪ Немає дати релізу"
        elif rel > sale_start:
            ready, status = False, "⏳ Вийде після старту сейлу"
        else:
            since = (sale_start - rel).days
            ready = since >= NINTENDO_COOLDOWN_DAYS
            status = "🟢 Готова" if ready else f"🟡 Кулдаун (ще {NINTENDO_COOLDOWN_DAYS - since} дн.)"
        rows.append({"Включити": ready, "Гра": r["Game_Name_Clean"], "Знижка (%)": sheet_discount(r),
                     "Дата релізу": rel.strftime("%d.%m.%Y") if rel else "—", "Статус": status})

    edited = st.data_editor(
        pd.DataFrame(rows), hide_index=True, use_container_width=True, height=360, key="ns_editor",
        column_config={"Включити": st.column_config.CheckboxColumn("Включити в сейл"),
                       "Знижка (%)": st.column_config.NumberColumn(min_value=10, max_value=90, step=5)},
        disabled=["Гра", "Дата релізу", "Статус"],
    )
    picked = edited[edited["Включити"]]
    st.caption(f"Обрано ігор: **{len(picked)}**")

    if st.button("⚡ Згенерувати Bookmarklet для Nintendo", use_container_width=True):
        if picked.empty:
            st.warning("Оберіть хоча б одну гру галочкою!")
        else:
            payload = {row["Гра"].strip().lower(): int(row["Знижка (%)"]) for _, row in picked.iterrows()}
            code = (BOOKMARKLET_TEMPLATE.replace("__DISCOUNTS__", json.dumps(payload, ensure_ascii=False))
                    .replace("__QUARTER_RE__", json.dumps(QUARTER_PRICE_RE)).replace("__MIN_PRICES__", json.dumps(MIN_SALE_PRICES))
                    .replace("__ZERO_DEC__", json.dumps(ZERO_DECIMAL_CURRENCIES)))
            st.success(f"🎉 Bookmarklet згенеровано для {len(picked)} ігор!")
            st.caption("Букмарклет враховує правила eShop: для Данії та ПАР ціни кратні 0.25, ціни в песо Чилі й Колумбії — цілі числа, а в країнах Америки ціна не опускається нижче мінімуму Nintendo (тоді знижка буде меншою за задану).")
            b1, b2 = st.columns(2)
            with b1:
                st.markdown("##### 📌 Код закладки:")
                st.code(code, language="javascript")
            with b2:
                st.markdown("##### 📋 Список назв:")
                st.text_area("Назви ігор:", "\n".join(picked["Гра"].str.strip()), height=160)


def render_xbox_sale():
    st.subheader("🟢 Подача на розпродажі Xbox")
    sales_timeline(XBOX_SCHEDULE, color_key="Тип", color_map={"ID Sale (Глибокі знижки)": "#10b981", "Tentpole Sale": "#d946ef"}, height=220)

    idx = default_sale_index(XBOX_SCHEDULE, key_date="deadline")
    names = [f"{s['name']} — дедлайн {s['deadline']} ({deadline_badge(s['deadline'])})" for s in XBOX_SCHEDULE]
    choice = st.selectbox("Сейл:", range(len(names)), index=idx, format_func=lambda i: names[i], key="xb_sale")
    sale = XBOX_SCHEDULE[choice]

    x = st.columns(4)
    x[0].metric("🎯 Розпродаж", sale["name"], sale_status(sale), delta_color="off")
    x[1].metric("⏰ Дедлайн подачі", sale["deadline"], deadline_badge(sale["deadline"]), delta_color="off")
    x[2].metric("🔒 Ліміт тайтлів", f"до {sale['limit']} ігор")
    x[3].metric("📩 Approval Feedback", sale["feedback"])
    st.info(f"💡 **Вимоги Microsoft:** {sale['note']}")

    rows = []
    for _, r in raw_df.iterrows():
        price = game_price(r) or 9.99
        disc = sheet_discount(r, minimum=sale["min_discount"])
        fails = [f"ціна ${price:.2f} < ${sale['min_price']}"] if sale["min_price"] and price < sale["min_price"] else []
        rows.append({"Подати": not fails, "Гра": r["Game_Name_Clean"], "Базова ціна ($)": price, "Знижка (%)": disc,
                     "Ціна на сейлі ($)": round(price * (1 - disc / 100), 2),
                     "Вимоги": "🟢 Проходить" if not fails else f"🔴 Не підходить ({', '.join(fails)})"})

    edited = st.data_editor(
        pd.DataFrame(rows), hide_index=True, use_container_width=True, height=360, key="xb_editor",
        column_config={"Подати": st.column_config.CheckboxColumn("Подати в Microsoft"),
                       "Знижка (%)": st.column_config.NumberColumn(min_value=sale["min_discount"], max_value=90, step=5),
                       "Базова ціна ($)": st.column_config.NumberColumn(format="$%.2f"),
                       "Ціна на сейлі ($)": st.column_config.NumberColumn(format="$%.2f")},
        disabled=["Гра", "Базова ціна ($)", "Ціна на сейлі ($)", "Вимоги"],
    )
    picked = edited[edited["Подати"]]
    if len(picked) > sale["limit"]:
        st.warning(f"⚠️ Обрано {len(picked)} ігор, а ліміт сейлу — {sale['limit']}. Зніми зайві галочки.")
    else:
        st.caption(f"Обрано {len(picked)} з {sale['limit']} можливих.")
    csv_button(picked.drop(columns=["Подати"]), "📥 Список для подачі (.CSV)", f"xbox_{sale['name'].replace(' ', '_')}.csv")

# ==============================================================================
# 🚀 РОЗДІЛ 4: РЕЛІЗИ (сертифікація + команда + roadmap + маркетинг)
# ==============================================================================
def build_activity_table():
    """Маркетинговий чек-лист. Без фолбеку на каталог — якщо листа немає, так і кажемо."""
    src = load_sheet(ACTIVITY_SHEET_URL)
    if src.empty:
        return pd.DataFrame()
    t_col = find_col(src.columns, "title", "гра", "game", "назва") or src.columns[0]
    d_col = find_col(src.columns, "release date", "release", "date", "дата")
    s_col = find_col(src.columns, "status", "статус")
    rows = []
    for _, r in src.iterrows():
        name = safe_str(r.get(t_col))
        if not name:
            continue
        rel = to_date(r.get(d_col)) if d_col else None
        raw_stat = safe_str(r.get(s_col)).lower() if s_col else ""
        done = sum(is_truthy(r.get(t)) for t in ACTIVITY_CHECKBOX_COLS)
        row = {"Гра": name, "Дата релізу": rel, "Статус": "🟢 Done" if ("released" in raw_stat or "done" in raw_stat) else "🟡 In Progress",
               "Готовність (%)": int(round(done / len(ACTIVITY_CHECKBOX_COLS) * 100))}
        row.update({t: is_truthy(r.get(t)) for t in ACTIVITY_CHECKBOX_COLS})
        rows.append(row)
    return pd.DataFrame(rows)


def render_releases():
    st.title("🚀 Релізи: сертифікація, команда та маркетинг")
    st.caption(f"Лист **'{CERTIFICATION_SHEET_NAME}'** + маркетинговий чек-лист • Контроль швидкості портування та готовності до релізу")

    act_df = build_activity_table()
    has_pipe = not pipe_df.empty
    if not has_pipe:
        st.warning(f"⚠️ Не вдалося завантажити лист **'{CERTIFICATION_SHEET_NAME}'**. Перевір назву листа в Google Таблиці.")

    if has_pipe:
        deltas = pd.to_numeric(pipe_df["_delta"], errors="coerce").dropna()
        on_time = float((deltas <= 0).mean() * 100) if not deltas.empty else 0.0
        k = st.columns(5)
        kpi_card(k[0], "Всього тайтлів", len(pipe_df), "Лист Certification")
        kpi_card(k[1], "Білдів завантажено", int((pipe_df["Етап"] == STAGE_DONE).sum()), "Готові до сабміту", "badge-xbox", "#4ade80")
        kpi_card(k[2], "Зараз у роботі", int(pipe_df["Етап"].isin([STAGE_WIP, STAGE_OVERDUE]).sum()), "Включно з простроченими", "badge-ps", "#38bdf8")
        kpi_card(k[3], "Зриви дедлайнів", int(pipe_df["Вердикт"].str.contains("Прострочено|Затримка").sum()), "Затримка / Прострочено", "badge-switch", "#ef4444")
        kpi_card(k[4], "Вчасність здачі", f"{on_time:.0f}%", "On-Time Rate", "badge-total", "#10b981" if on_time >= 70 else "#f59e0b")

        overdue = pipe_df[pipe_df["Етап"] == STAGE_OVERDUE]
        if not overdue.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander(f"🚨 Критичні зриви: {len(overdue)} білд(ів) прострочено й досі не завантажено", expanded=True):
                for _, cr in overdue.iterrows():
                    st.markdown(
                        f'<div class="alert-card-red"><b style="color:#fff; font-size:15px;">{cr["Гра"]} (Розробник: {cr["Розробник"]})</b> ➔ '
                        f'<span style="color:#fca5a5; font-weight:bold;">План фінішу був {cr["План здачі білда"]}</span>'
                        f'<p style="margin:3px 0 0 0; font-size:12px; color:#cbd5e1;">Старт: {cr["Дата старту"]} • Вердикт: {cr["Вердикт"]}</p></div>',
                        unsafe_allow_html=True,
                    )

    st.markdown("<br>", unsafe_allow_html=True)
    t_tracker, t_team, t_roadmap, t_marketing = st.tabs(["📋 Трекер і дедлайни", "👨‍💻 Команда: KPI", "📅 Roadmap", "📣 Маркетинг-готовність"])
    with t_tracker:
        if has_pipe:
            render_cert_tracker(act_df)
        else:
            st.info("Немає даних сертифікації.")
    with t_team:
        if has_pipe:
            render_team_kpi()
        else:
            st.info("Немає даних сертифікації.")
    with t_roadmap:
        if has_pipe:
            render_roadmap()
        else:
            st.info("Немає даних сертифікації.")
    with t_marketing:
        render_marketing(act_df)


def render_cert_tracker(act_df):
    all_devs = sorted(d for d in pipe_df["Розробник"].unique() if d != "Не призначено")
    c1, c2 = st.columns([1.5, 2.5])
    sel_dev = c1.selectbox("Розробник:", ["Всі розробники"] + all_devs + ["Не призначено"], key="pipe_dev")
    sel_stage = c2.radio("Етап:", ["Всі", "🟢 Завантажені", "⏳ В роботі", "🚨 Затримка / прострочка", "⚪ В черзі"], horizontal=True, key="pipe_stage", **persisted("pipe_stage", ["Всі", "🟢 Завантажені", "⏳ В роботі", "🚨 Затримка / прострочка", "⚪ В черзі"]))

    view = pipe_df.copy()
    if sel_dev != "Всі розробники":
        view = view[view["Розробник"] == sel_dev]
    stage_filters = {
        "🟢 Завантажені": view["Етап"] == STAGE_DONE,
        "⏳ В роботі": view["Етап"].isin([STAGE_WIP, STAGE_OVERDUE]),
        "🚨 Затримка / прострочка": view["Вердикт"].str.contains("Затримка|Прострочено"),
        "⚪ В черзі": view["Етап"] == STAGE_BACKLOG,
    }
    if sel_stage in stage_filters:
        view = view[stage_filters[sel_stage]]

    # Підтягуємо маркетингову готовність з чек-листа — сертифікація і маркетинг в одному рядку
    if not act_df.empty:
        ready_map = {n.lower(): v for n, v in zip(act_df["Гра"], act_df["Готовність (%)"])}
        view["Маркетинг (%)"] = view["Гра"].str.lower().map(ready_map)

    cols = ["Гра", "Розробник", "Вердикт", "Дата старту", "План здачі білда", "Дата завантаження білда",
            "Реліз Nintendo", "План (дн)", "Факт (дн)", "Відхилення (дн)"] + (["Маркетинг (%)"] if "Маркетинг (%)" in view.columns else [])
    st.dataframe(view[cols], hide_index=True, use_container_width=True, height=420, column_config={
        "Маркетинг (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%"),
        "Відхилення (дн)": st.column_config.NumberColumn(format="%+d"),
    })
    csv_button(view[cols], "📥 Експортувати реєстр (.CSV)", "nintendo_certification_pipeline.csv")

    st.markdown("---")
    st.subheader("⏳ План vs Факт по здачі білдів")
    st.caption("Ті самі фільтри, що й у таблиці • Червоне = затримка, зелене = вчасно або раніше")
    dv = view[pd.to_numeric(view["_delta"], errors="coerce").notna()].copy()
    if dv.empty:
        st.info("Для обраного фільтра ще немає зданих білдів із планом і фактом.")
        return
    dv["_delta"] = dv["_delta"].astype(float)
    fig = px.bar(dv.sort_values("_delta", ascending=False), x="Гра", y="_delta", color="_delta", text="_delta",
                 color_continuous_scale=["#10b981", "#eab308", "#ef4444"], labels={"_delta": "Відхилення (днів)"}, hover_data={"Розробник": True})
    fig.update_traces(texttemplate="%{text:+.0f} дн", textposition="outside", cliponaxis=False)
    show_fig(fig, height=360, xaxis_title="")


def render_team_kpi():
    all_devs = sorted(d for d in pipe_df["Розробник"].unique() if d != "Не призначено")
    dated = pipe_df.assign(_pdate=pipe_df.apply(project_date, axis=1))
    c_p, _ = st.columns([1.2, 3])
    with c_p:
        sel = period_picker(dated["_pdate"], key="team_period")
    start, end = period_bounds(sel)
    period_df = dated if sel == "Весь період" else dated[dated["_pdate"].apply(lambda d: in_bounds(d, start, end))]
    st.caption(f"Проєкт потрапляє в період за датою плану здачі (або завантаження / старту) • У вибірці: **{len(period_df)}** ігор")

    kpi = build_dev_kpi(period_df, all_devs)
    active = kpi[kpi["Всього ігор"] > 0] if not kpi.empty else kpi
    if active.empty:
        st.info("За цей період немає проєктів із призначеним розробником.")
        return

    st.markdown(f"##### 📊 Завантаження команди ({sel})")
    fig = go.Figure()
    for col, name, color in [("Здано білдів", "Здано", "#10b981"), ("В роботі", "В роботі", "#38bdf8"),
                             ("Прострочено", "Прострочено", "#ef4444"), ("В черзі", "В черзі", "#64748b")]:
        fig.add_trace(go.Bar(x=active["Розробник"], y=active[col], name=name, marker_color=color))
    show_fig(fig, height=330, barmode="stack", yaxis=dict(dtick=1))

    st.markdown(f"##### 📋 KPI розробників ({sel})")
    st.dataframe(kpi, hide_index=True, use_container_width=True, column_config={
        "Сер. план (дн)": st.column_config.NumberColumn(format="%.1f"),
        "Сер. факт (дн)": st.column_config.NumberColumn(format="%.1f"),
        "Сер. відхилення (дн)": st.column_config.NumberColumn(format="%+.1f дн"),
        "% вчасно": st.column_config.NumberColumn(format="%d%%"),
        "KPI (0-100)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
    })
    with st.expander("ℹ️ Як рахується KPI"):
        st.markdown("- **45 балів** — частка зданих білдів від усіх ігор розробника за період\n"
                    "- **35 балів** — % здач вчасно (якщо зданих ще немає — нейтральні 25)\n"
                    "- **+20** базових балів\n"
                    "- **−2** за кожен день середньої затримки, **−5** за кожну гру, прострочену зараз\n\n"
                    "🟢 ≥ 80 • 🟡 65–79 • 🔴 < 65")


def render_roadmap():
    st.subheader("📅 Графік зайнятості та план здачі ігор")
    st.caption("Жовта лінія — сьогодні • Повзунок унизу — масштабування")
    recs = []
    for _, r in pipe_df.iterrows():
        dev = r["Розробник"]
        d_s, d_p, d_u = r["_d_start"], r["_d_plan"], r["_d_upload"]
        if dev == "Не призначено" or (pd.isna(d_s) and pd.isna(d_p)):
            continue
        start_d = d_s if pd.notna(d_s) else d_p - timedelta(days=14)
        end_d = d_p if pd.notna(d_p) else d_s + timedelta(days=14)
        if start_d > end_d:
            start_d, end_d = end_d, start_d
        if pd.notna(d_u):
            status = "🟢 Здано вчасно" if pd.notna(d_p) and d_u.date() <= d_p.date() else "🔴 Здано з затримкою"
        elif pd.notna(d_s):
            status = "🚨 Прострочено" if pd.notna(d_p) and TODAY > d_p.date() else "🔵 В роботі"
        else:
            status = "🟣 Заплановано"
        recs.append({"Гра": r["Гра"], "Розробник": f"👨‍💻 {dev}", "Start": start_d, "End": end_d, "Статус": status,
                     "Старт": r["Дата старту"], "План": r["План здачі білда"], "Факт": r["Дата завантаження білда"],
                     "Тривалість": f"{(end_d - start_d).days} дн."})
    if not recs:
        st.info("Немає даних із датами для побудови графіка.")
        return
    fig = px.timeline(
        pd.DataFrame(recs), x_start="Start", x_end="End", y="Розробник", color="Статус", text="Гра",
        color_discrete_map={"🟢 Здано вчасно": "#10b981", "🔴 Здано з затримкою": "#ef4444", "🚨 Прострочено": "#f43f5e",
                            "🔵 В роботі": "#38bdf8", "🟣 Заплановано": "#a855f7"},
        hover_data={"Гра": True, "Статус": True, "Старт": True, "План": True, "Факт": True, "Тривалість": True,
                    "Start": False, "End": False, "Розробник": False},
    )
    fig.update_yaxes(autorange="reversed", showgrid=True, gridcolor="rgba(255,255,255,0.12)", tickfont=dict(size=14, color="#ffffff"), title="")
    fig.add_vline(x=datetime.combine(TODAY, datetime.min.time()).timestamp() * 1000, line_width=2.5, line_dash="dash", line_color="#fbbf24",
                  annotation_text=f"СЬОГОДНІ ({TODAY.strftime('%d.%m')})", annotation_position="top left",
                  annotation_font_color="#fbbf24", annotation_font_size=11)
    fig.update_traces(textposition="inside", insidetextanchor="middle", textfont=dict(color="#ffffff", size=11.5))
    show_fig(fig, height=580, xaxis=dict(type="date", range=[TODAY - timedelta(days=10), TODAY + timedelta(days=100)],
                                         rangeslider=dict(visible=True, thickness=0.07, bgcolor="#161622", bordercolor="#28283c")))


MARKETING_URGENT_DAYS = 14  # реліз ближче за N днів → незакриті пункти підсвічуються червоним


def render_marketing_matrix(act_df):
    c1, c2 = st.columns([1.6, 2.4])
    scope = c1.radio("Показати:", ["🟡 Тільки в роботі", "Всі ігри"], horizontal=True, key="mkt_scope", **persisted("mkt_scope", ["🟡 Тільки в роботі", "Всі ігри"]))
    df = act_df if scope == "Всі ігри" else act_df[act_df["Статус"].str.startswith("🟡")]
    if df.empty:
        st.info("Немає ігор для відображення.")
        return
    df = df.assign(_sort=df["Дата релізу"].apply(lambda d: d or date(2100, 1, 1))).sort_values(["_sort", "Гра"])

    labels, z, text, hover = [], [], [], []
    for _, r in df.iterrows():
        d = r["Дата релізу"]
        days_left = (d - TODAY).days if d else None
        urgent = r["Статус"].startswith("🟡") and days_left is not None and days_left <= MARKETING_URGENT_DAYS
        labels.append(f"{r['Гра']} · {d.strftime('%d.%m') if d else 'без дати'} · {r['Готовність (%)']}%")
        row_z, row_t, row_h = [], [], []
        for t in ACTIVITY_CHECKBOX_COLS:
            if r[t]:
                row_z.append(1); row_t.append("✓"); row_h.append("✅ Зроблено")
            elif urgent:
                when = f"через {days_left} дн." if days_left >= 0 else f"{-days_left} дн. тому"
                row_z.append(-1); row_t.append("!"); row_h.append(f"🚨 Не зроблено — реліз {when}")
            else:
                row_z.append(0); row_t.append(""); row_h.append("⬜ Не зроблено")
        z.append(row_z); text.append(row_t); hover.append(row_h)

    fig = go.Figure(go.Heatmap(
        z=z, x=ACTIVITY_CHECKBOX_COLS, y=labels, text=text, customdata=hover, texttemplate="%{text}",
        textfont=dict(color="#ffffff", size=12), zmin=-1, zmax=1, showscale=False, xgap=3, ygap=3,
        colorscale=[[0.0, "#b91c1c"], [0.5, "#2a2a3d"], [1.0, "#10b981"]],
        hovertemplate="<b>%{y}</b><br>%{x}: %{customdata}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=12))
    fig.update_xaxes(side="top", tickangle=-30, tickfont=dict(size=11))
    show_fig(fig, height=max(240, 30 * len(labels) + 120), margin=dict(t=80, b=10, l=10, r=10))
    c2.caption(f"🟩 зроблено • ⬛ не зроблено • 🟥 не зроблено, а реліз ближче ніж {MARKETING_URGENT_DAYS} дн. (або вже вийшла) • "
               "рядки відсортовано за датою релізу")

    missing = {t: int((~df[t].astype(bool)).sum()) for t in ACTIVITY_CHECKBOX_COLS}
    worst = sorted(missing.items(), key=lambda kv: kv[1], reverse=True)[:3]
    if worst and worst[0][1] > 0:
        st.caption("Найчастіше не закрито: " + " • ".join(f"**{t}** ({n} ігор)" for t, n in worst if n > 0))


def render_marketing(act_df):
    st.subheader("📣 Маркетингова готовність до релізів")
    if act_df.empty:
        st.warning("⚠️ Не вдалося завантажити маркетинговий чек-лист. Перевір `ACTIVITY_SHEET_URL`.")
        return

    k = st.columns(4)
    kpi_card(k[0], "🎮 Ігор у трекері", len(act_df))
    kpi_card(k[1], "🛠️ В роботі", int(act_df["Статус"].str.contains("Progress").sum()), "Підготовка", "badge-switch", "#f59e0b")
    kpi_card(k[2], "🟢 Випущено", int(act_df["Статус"].str.contains("Done").sum()), "Done", "badge-xbox", "#4ade80")
    kpi_card(k[3], "📊 Середня готовність", f"{act_df['Готовність (%)'].mean():.0f}%", "По всій базі", "badge-ps", "#38bdf8")

    for _, r in act_df.iterrows():
        if r["Дата релізу"] and r["Статус"].startswith("🟡"):
            days_left = (r["Дата релізу"] - TODAY).days
            if 0 <= days_left <= 14 and r["Готовність (%)"] < 70:
                missing = [t for t in ACTIVITY_CHECKBOX_COLS if not r[t]]
                st.markdown(
                    f'<div class="alert-card-yellow"><b style="color:#fff; font-size:15px;">⏳ {r["Гра"]}</b> ➔ '
                    f'<span style="color:#fde047; font-weight:bold;">реліз через {days_left} дн., маркетинг готовий на {r["Готовність (%)"]}%</span>'
                    f'<p style="margin:2px 0 0 0; font-size:12px; color:#cbd5e1;">Не закрито: {", ".join(missing)}</p></div>',
                    unsafe_allow_html=True,
                )

    st.markdown("##### 🧩 Матриця «гра × активність»")
    render_marketing_matrix(act_df)

    with st.expander("📑 Таблиця чек-листа"):
        cfg = {"Дата релізу": st.column_config.DateColumn(format="DD.MM.YYYY"),
               "Готовність (%)": st.column_config.ProgressColumn("Готовність", format="%d%%", min_value=0, max_value=100)}
        cfg.update({t: st.column_config.CheckboxColumn(t, width="small", disabled=True) for t in ACTIVITY_CHECKBOX_COLS})
        order = ["Гра", "Дата релізу", "Статус", "Готовність (%)"] + ACTIVITY_CHECKBOX_COLS
        st.dataframe(act_df[order], column_config=cfg, hide_index=True, use_container_width=True, height=520)
        csv_button(act_df[order], "📥 Експортувати звіт активностей (.CSV)", "release_activities_report.csv")

# ==============================================================================
# 🧮 РОЗДІЛ 5: ПРОГНОЗИ ТА ЛІДИ
# ==============================================================================
SOURCE_INPUTS = {
    "Steam": ("Steam All-Time Revenue ($):", 6000, 1000),
    "Google Play": ("Завантаження Google Play (Installs):", 500000, 50000),
    "CrazyGames / Web": ("Кількість відгуків / оцінок:", 3500, 500),
    "itch.io": ("Оцінки itch.io:", 40, 5),
}
LEAD_COLUMNS_REQUIRED = {"Назва гри", "Total M1 ($)"}


def render_forecasts():
    st.title("🧮 Прогнози та ліди")
    st.caption("Оцінка нових лідів за 30 піджанрами, пайплайн лідів і перевірка точності моделі на випущених іграх")
    t_calc, t_leads, t_acc = st.tabs(["🧮 Калькулятор ліда", "📋 Пайплайн лідів", "🎯 Точність моделі (план vs факт M1)"])
    with t_calc:
        render_calculator()
    with t_leads:
        render_leads()
    with t_acc:
        render_accuracy()


def render_calculator():
    left, right = st.columns([1, 1.25])
    with left:
        st.markdown('<div class="sandbox-box">', unsafe_allow_html=True)
        st.markdown("#### 1. Вхідні дані ліда")
        name = st.text_input("Назва гри / ліда:", "Project Prototype")
        link = st.text_input("🔗 Посилання на гру (Steam / GP / itch / Web):", "https://store.steampowered.com/app/...")
        source = st.selectbox("Джерело аналізу:", list(SOURCE_INPUTS.keys()))
        lbl, default, step = SOURCE_INPUTS[source]
        value = st.number_input(lbl, min_value=0, value=default, step=step)
        base = base_metric_from_source(source, value)
        st.markdown("---")
        st.markdown("#### 2. Жанр і ціна")
        genre = st.selectbox("Точний піджанр гри:", list(GENRE_DATABASE.keys()))
        price = st.selectbox("Планова ціна на консолях ($):", list(PRICE_MODIFIERS.keys()), index=4)
        st.markdown("</div>", unsafe_allow_html=True)

    cfg = GENRE_DATABASE[genre]
    est = forecast_m1(base, genre, price)
    tot_m1 = sum(est.values())
    share = studio_share()
    ltv = {p: tot_m1 * LTV_MULT[p] for p in ["M3", "M6", "1Y"]}

    with right:
        st.markdown('<div class="sandbox-box">', unsafe_allow_html=True)
        st.markdown(f"### 📈 Розрахунок: **{name}**")
        st.caption(f"💡 *{cfg['Desc']}*")
        st.caption(f"Органічна база: **${base:,.1f}** • Ціновий множник: **{PRICE_MODIFIERS.get(price, 1.0)}x** • "
                   f"Частка студії: **{share * 100:.1f}%** (з налаштувань P&L)")
        if tot_m1 >= 6500:
            st.success("🟢 **ТОП ЛІД:** рекомендовано надсилати пітч (M1 > $6.5k)")
            rec = "✅ ТОП ЛІД"
        elif tot_m1 >= 3000:
            st.info("🟡 **СТАНДАРТНИЙ ТАЙТЛ:** стабільний кандидат ($3k–$6.5k)")
            rec = "⚠️ СТАНДАРТ"
        else:
            st.warning("🔴 **ВИСОКИЙ РИЗИК:** низька прогнозована каса (M1 < $3k)")
            rec = "❌ РИЗИК"

        m = st.columns(3)
        for i, p in enumerate(["PS", "Switch", "Xbox"]):
            m[i].metric(f"{PLATFORM_LABEL[p]} (M1)", fmt_usd(est[p]), f"{cfg[p]}x", delta_color="off")
        t = st.columns(3)
        t[0].metric("🔥 Gross M1", fmt_usd(tot_m1), f"Студії: {fmt_usd(tot_m1 * share)}", delta_color="off")
        t[1].metric(f"📈 Gross M6 ({LTV_MULT['M6']}x)", fmt_usd(ltv["M6"]), f"Студії: {fmt_usd(ltv['M6'] * share)}", delta_color="off")
        t[2].metric(f"📅 Gross 1Y ({LTV_MULT['1Y']}x)", fmt_usd(ltv["1Y"]), f"Студії: {fmt_usd(ltv['1Y'] * share)}", delta_color="off")

        if st.button("➕ Зберегти лід (у таблицю та Google Sheets)", use_container_width=True):
            lead = {
                "Дата": datetime.now().strftime("%Y-%m-%d %H:%M"), "Назва гри": name, "Посилання": link, "Джерело": source,
                "Жанр": genre, "Ціна ($)": price, "Base Metric": round(base, 1),
                "PS M1 ($)": round(est["PS"], 1), "Switch M1 ($)": round(est["Switch"], 1), "Xbox M1 ($)": round(est["Xbox"], 1),
                "Total M1 ($)": round(tot_m1, 1), "Studio Margin M1 ($)": round(tot_m1 * share, 1),
                "1Y LTV ($)": round(ltv["1Y"], 1), "Рекомендація": rec,
            }
            st.session_state.setdefault("scouted_leads", []).append(lead)
            if GOOGLE_WEBHOOK_URL:
                try:
                    res = requests.post(GOOGLE_WEBHOOK_URL, json=lead, timeout=5)
                    st.toast("🚀 Записано в Google Таблицю (лист Leads)!" if res.status_code == 200 else f"⚠️ Webhook відповів {res.status_code}, лід збережено локально")
                except Exception as e:
                    st.warning(f"Збережено локально. Помилка webhook: {e}")
            else:
                st.toast(f"✅ Лід '{name}' збережено!")
        st.markdown("</div>", unsafe_allow_html=True)


def render_leads():
    st.subheader("📋 Пайплайн нових лідів")
    sheet = load_sheet(GOOGLE_SHEET_URL, LEADS_SHEET_NAME)
    # gviz повертає перший лист, якщо листа з такою назвою немає — тому перевіряємо колонки
    sheet = sheet if LEAD_COLUMNS_REQUIRED.issubset(set(sheet.columns)) else pd.DataFrame()
    session = pd.DataFrame(st.session_state.get("scouted_leads", []))
    leads = pd.concat([sheet, session], ignore_index=True) if not session.empty else sheet
    if not leads.empty and {"Назва гри", "Дата"}.issubset(leads.columns):
        leads = leads.drop_duplicates(subset=["Назва гри", "Дата"], keep="first")

    if leads.empty:
        st.info("💡 Лідів поки немає. Розрахуй гру в калькуляторі та натисни «➕ Зберегти лід».")
        return
    st.caption(f"З Google Sheets: **{len(sheet)}** • Додано в цій сесії: **{len(session)}** (ще не підтягнулись із таблиці)")

    total = pd.to_numeric(leads.get("Total M1 ($)"), errors="coerce").fillna(0.0) if "Total M1 ($)" in leads.columns else pd.Series(dtype=float)
    k = st.columns(3)
    k[0].metric("Зібрано лідів", len(leads))
    k[1].metric("Потенціал Gross M1", fmt_usd(float(total.sum()), True))
    k[2].metric(f"Очікуваний дохід студії ({studio_share() * 100:.1f}%)", fmt_usd(float(total.sum()) * studio_share(), True))

    cfg = {"Посилання": st.column_config.LinkColumn("Посилання", display_text="Відкрити ↗")} if "Посилання" in leads.columns else {}
    st.dataframe(leads, column_config=cfg, use_container_width=True, height=400, hide_index=True)
    c1, c2 = st.columns([1, 4])
    with c1:
        csv_button(leads, "📥 Експортувати ліди (.CSV)", "upscale_scouted_leads.csv")
    with c2:
        if st.button("🗑️ Очистити ліди цієї сесії"):
            st.session_state["scouted_leads"] = []
            st.rerun()


def row_base_metric(r):
    base = clean_num_val(r.get(find_col(r.index, "base metric"))) if find_col(r.index, "base metric") else 0.0
    if base > 0:
        return base
    source = safe_str(r.get(COL["source"])).lower() if COL["source"] else ""
    steam = clean_num_val(r.get(find_col(r.index, "steam revenue"))) if find_col(r.index, "steam revenue") else 0.0
    installs_col = find_col(r.index, "installs", "reviews")
    installs = clean_num_val(r.get(installs_col)) if installs_col else 0.0
    if "steam" in source or steam > 0:
        return base_metric_from_source("steam", steam) or 500.0
    if "play" in source or "google" in source or installs >= 10000:
        return base_metric_from_source("google play", installs)
    if "crazy" in source or "web" in source:
        return base_metric_from_source("web", installs)
    if "itch" in source:
        return base_metric_from_source("itch", installs)
    return 0.0


def render_accuracy():
    st.subheader("🎯 Точність прогнозу M1 на випущених іграх")
    st.caption("Та сама формула, що й у калькуляторі: база з джерела × жанровий коефіцієнт × ціновий множник")
    rows = []
    for _, r in raw_df.iterrows():
        m1_plat = {p: row_period_fact(r, "M1", p) or 0.0 for p in PLATFORMS}
        platforms = [p for p in PLATFORMS if m1_plat[p] > 0]
        fact = sum(m1_plat.values())
        base = row_base_metric(r)
        genre_key = match_genre(r.get(COL["genre"]) if COL["genre"] else "")
        price = game_price(r) or 9.99
        pred = sum(forecast_m1(base, genre_key, price, platforms or ["Switch"]).values()) if base > 0 else None

        if pred and fact > 0:
            acc = max(0.0, (1 - abs(fact - pred) / max(fact, pred)) * 100)
            status = "🟢 Перевищила план" if fact > pred * 1.25 else ("🔴 Нижче плану" if fact < pred * 0.70 else "🟡 У плані (±25%)")
        else:
            acc, status = None, ("⚪ Немає вхідних метрик" if fact > 0 else "⚪ Немає факту M1")
        rows.append({"Гра": r["Game_Name_Clean"], "Жанр (модель)": genre_key, "Ціна ($)": price,
                     "Платформи": " + ".join(platforms) if platforms else "—", "Base Metric": round(base, 1) if base else None,
                     "Факт M1 ($)": round(fact, 2) if fact else None, "Прогноз M1 ($)": round(pred, 2) if pred else None,
                     "Різниця ($)": round(fact - pred, 2) if acc is not None else None,
                     "Точність (%)": round(acc, 1) if acc is not None else None, "Статус": status})
    comp = pd.DataFrame(rows)
    valid = comp.dropna(subset=["Точність (%)"])

    a = st.columns(4)
    a[0].metric("Середня точність моделі", f"{valid['Точність (%)'].mean():.1f}%" if not valid.empty else "—")
    a[1].metric("🟢 Перевищили план", f"{comp['Статус'].str.contains('Перевищила').sum()} ігор")
    a[2].metric("🟡 У межах (±25%)", f"{comp['Статус'].str.contains('У плані').sum()} ігор")
    a[3].metric("🔴 Нижче прогнозу", f"{comp['Статус'].str.contains('Нижче').sum()} ігор")

    if not valid.empty:
        top = valid.nlargest(15, "Факт M1 ($)")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=top["Гра"], y=top["Факт M1 ($)"], name="Факт M1", marker_color="#10b981"))
        fig.add_trace(go.Bar(x=top["Гра"], y=top["Прогноз M1 ($)"], name="Прогноз M1", marker_color="#d946ef"))
        show_fig(fig, height=360, barmode="group", xaxis_title="", yaxis_title="$")
    st.dataframe(comp, use_container_width=True, height=450, hide_index=True, column_config={
        "Точність (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
        "Факт M1 ($)": st.column_config.NumberColumn(format="$%.0f"), "Прогноз M1 ($)": st.column_config.NumberColumn(format="$%.0f"),
        "Різниця ($)": st.column_config.NumberColumn(format="$%+.0f"),
    })


# ==============================================================================
# 🧭 9. РОУТИНГ
# ==============================================================================
PAGES = {
    SECTIONS[0]: render_portfolio,
    SECTIONS[1]: render_goals_page,
    SECTIONS[2]: render_dynamics,
    SECTIONS[3]: render_calendar_section,
    SECTIONS[4]: render_releases,
    SECTIONS[5]: render_forecasts,
}
PAGES[app_mode]()
save_prefs()
