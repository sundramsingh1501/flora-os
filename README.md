---
title: Flora OS
emoji: 🌿
colorFrom: purple
colorTo: blue
sdk: streamlit
sdk_version: 1.41.0
app_file: app/main.py
pinned: false
python_version: 3.11
license: mit
---

<div align="center">

<img src="https://img.shields.io/badge/Flora%20OS-Personal%20AI%20Assistant-7c6af7?style=for-the-badge&logo=leaf&logoColor=white" />

# 🌿 Flora OS

### Your Personal AI Executive Assistant

*Start every day informed, organised, and ahead of the curve.*

[![Live Demo](https://img.shields.io/badge/Live%20Demo-HuggingFace%20Spaces-ff9d00?style=for-the-badge&logo=huggingface&logoColor=white)](https://sundram1501-flora-os.hf.space)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.41-ff4b4b?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Gemini](https://img.shields.io/badge/Gemini%202.5%20Flash-AI%20Engine-4285f4?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## What is Flora OS?

Flora OS is a full-stack **personal productivity dashboard** that acts as your AI-powered executive assistant. Every morning it delivers a curated briefing straight to your inbox — top news ranked by relevance to your interests, live weather, market snapshot, and job openings matched to your profile. Throughout the day, the same dashboard is available as a rich web app giving you everything in one place.

Built with a dark glassmorphism UI inspired by Linear, Notion, and Apple — Flora OS is designed to feel premium, fast, and personal.

---

## Features

### 🗞 Morning Brief
- AI-curated top stories from the last 24 hours across your chosen topics
- Each article ranked by importance score (1–10) using Gemini 2.5 Flash
- One-line summaries you can skim in seconds
- Categories: Technology, AI/ML, Indian News, Markets, Sports, Finance, and more
- Refreshes daily — no stale content

### 📧 Daily Email Delivery
- Automated morning brief delivered to your inbox at your chosen time
- Fully personalised HTML email — your name, your topics, your market watchlist
- Includes weather, market snapshot, and fresher job openings
- One-click **"Open Full Brief →"** button linking back to your live dashboard
- Configure delivery time and timezone from Settings

### 📬 Email Hub (Gmail Integration)
- Connects to your Gmail via OAuth2
- Automatically filters **job-related emails only** — interviews, assessments, coding tests, rejections, offer letters
- Powered by Gmail API search query — no manual sorting needed
- Inline preview of each email with sender, subject, and date

### 💼 Job Board
- Live job listings pulled from multiple sources: **Adzuna**, **RemoteOK**, and more
- Each job scored 1–10 for fit against your profile (role, tech stack, location)
- Filters by source, location, fit score, and keyword search
- Clean job cards with company, location, salary range, and tags
- Direct "Apply →" link for each listing

### 📈 Market Watchlist
- Live stock prices for your personal watchlist (Apple, Google, MSFT, or any ticker)
- Crypto prices (Bitcoin, Ethereum, etc.) via CoinGecko
- Price change % with green/red indicators
- AI-generated 3-sentence market briefing summarising the day's moves
- Mini Plotly chart for each asset

### ☀️ Dashboard
- At-a-glance daily overview: weather, date, top stories, market pulse
- Gmail connection status
- Quick navigation to all sections
- User profile display

### ⚙️ Settings & Personalisation
- **News Topics** — choose your interest categories
- **Job Preferences** — target roles, preferred locations, tech stack
- **Stock & Crypto Watchlist** — add/remove tickers
- **Morning Email** — toggle on/off, set delivery time, set timezone
- **Gmail Connect** — OAuth2 Gmail integration
- **Account** — update name, password

### 🔐 Authentication
- Email + password signup/login with bcrypt hashing
- **Continue with Google** — one-click OAuth2 sign-in
- Persistent sessions via encrypted localStorage tokens
- Secure token management — no plaintext credentials stored

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit 1.41, custom CSS (glassmorphism dark theme) |
| **AI Engine** | Google Gemini 2.5 Flash |
| **Auth** | Google OAuth2, bcrypt, JWT via `python-jose` |
| **Database** | SQLite (via SQLAlchemy ORM) |
| **Email** | Gmail API (OAuth2), SMTP with Gmail App Password |
| **News** | NewsAPI, RSS feeds via feedparser |
| **Jobs** | Adzuna API, RemoteOK API |
| **Market Data** | yfinance (stocks), CoinGecko (crypto), Alpha Vantage |
| **Weather** | OpenWeatherMap API |
| **Scheduler** | APScheduler (BackgroundScheduler, runs inside Streamlit) |
| **Deployment** | HuggingFace Spaces (CPU Basic) |

---

## Project Structure

```
flora-os/
├── app/
│   ├── main.py                  # Entry point, OAuth callbacks, scheduler bootstrap
│   ├── config.py                # Pydantic-settings config (reads env vars)
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models.py                # ORM models: User, UserPreferences, DailyBrief, etc.
│   │
│   ├── agents/
│   │   ├── orchestrator.py      # Coordinates all agents to build daily brief
│   │   ├── news_agent.py        # Fetches + ranks news with Gemini
│   │   ├── brief_generator.py   # Generates AI morning message
│   │   ├── gmail_agent.py       # Gmail job-email filter
│   │   ├── job_agent.py         # Fetches + scores job listings
│   │   ├── market_agent.py      # Market data + AI briefing
│   │   └── research_agent.py    # Deep-dive article research
│   │
│   ├── auth/
│   │   ├── session.py           # Session persistence (localStorage + Streamlit state)
│   │   ├── email_auth.py        # Register/login with email + bcrypt
│   │   ├── google_oauth.py      # Google OAuth2 flow
│   │   └── token_manager.py     # OAuth token storage
│   │
│   ├── pages/
│   │   ├── login.py             # Login / sign-up page
│   │   ├── onboarding.py        # First-run personalisation wizard
│   │   ├── dashboard.py         # Home dashboard
│   │   ├── morning_brief.py     # Full news brief page
│   │   ├── email_hub.py         # Gmail job email viewer
│   │   ├── job_board.py         # Job listings with filters
│   │   ├── market.py            # Market watchlist + charts
│   │   └── settings.py          # User settings
│   │
│   ├── services/
│   │   ├── ai_service.py        # Gemini API wrapper (generate, summarize, score)
│   │   ├── email_sender.py      # HTML email builder + SMTP sender
│   │   ├── news_service.py      # NewsAPI + RSS fetcher
│   │   ├── job_service.py       # Adzuna + RemoteOK fetcher
│   │   ├── market_service.py    # yfinance + CoinGecko fetcher
│   │   └── weather_service.py   # OpenWeatherMap fetcher
│   │
│   ├── scheduler/
│   │   └── morning_brief.py     # APScheduler jobs: email delivery + brief generation
│   │
│   └── ui/
│       ├── theme.py             # Global CSS design system
│       ├── navbar.py            # Sidebar navigation
│       └── components.py        # Reusable UI components
│
├── scheduler_worker.py          # Standalone scheduler (for local use)
├── requirements.txt
├── .env.example
└── .streamlit/
    ├── config.toml              # Streamlit server + theme config
    └── pages.toml               # Page routing
```

---

## Setup

### Prerequisites
- Python 3.11+
- A Google Cloud project (for OAuth + Gmail)
- API keys for NewsAPI, OpenWeatherMap, Adzuna, Gemini

### 1. Clone the repository

```bash
git clone https://github.com/sundramsingh1501/flora-os.git
cd flora-os
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
# App
APP_SECRET_KEY=your-random-secret-key-min-32-chars
APP_BASE_URL=http://localhost:8501

# Google OAuth (console.cloud.google.com → APIs & Services → Credentials)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8501/

# Gemini AI (aistudio.google.com/app/apikey)
GEMINI_API_KEY=AIzaSy...

# NewsAPI (newsapi.org)
NEWS_API_KEY=your-key

# OpenWeatherMap (openweathermap.org/api)
OPENWEATHER_API_KEY=your-key

# SMTP — use a Gmail App Password (not your real password)
# myaccount.google.com → Security → 2-Step Verification → App Passwords
SMTP_EMAIL=you@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx

# Adzuna Jobs API (developer.adzuna.com)
ADZUNA_APP_ID=your-app-id
ADZUNA_APP_KEY=your-app-key

# Alpha Vantage — optional, extended market data (alphavantage.co)
ALPHA_VANTAGE_KEY=your-key

# Encryption key — generate once with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-fernet-key
```

### 5. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → **APIs & Services → Enable APIs**
   - Google People API
   - Gmail API
3. **Credentials → Create OAuth 2.0 Client ID** (Web application)
4. Add Authorized Redirect URIs:
   - `http://localhost:8501/` (local dev)
   - Your deployed URL (e.g. `https://your-space.hf.space/`)
5. Copy Client ID and Client Secret into `.env`

### 6. Run the app

```bash
streamlit run app/main.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### 7. First run — onboarding

After signing up, Flora OS walks you through a personalisation wizard:
- Choose your news topics
- Set your target job roles and tech stack
- Add stocks/crypto to your watchlist
- Configure your daily email time and timezone

---

## Deployment — HuggingFace Spaces

The live app is deployed at **https://sundram1501-flora-os.hf.space**

To deploy your own instance:

1. Fork this repo
2. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space) with **Streamlit** SDK
3. Connect your forked repo
4. Add all environment variables under **Settings → Variables and Secrets**
5. Set `APP_BASE_URL` to your Space URL (e.g. `https://your-username-flora-os.hf.space`)
6. Update your Google OAuth redirect URIs to include the Space URL

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `APP_SECRET_KEY` | ✅ | Random secret for session signing |
| `APP_BASE_URL` | ✅ | Base URL of the deployed app |
| `ENCRYPTION_KEY` | ✅ | Fernet key for encrypting OAuth tokens |
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | ✅ | OAuth callback URL |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `NEWS_API_KEY` | ✅ | NewsAPI key |
| `OPENWEATHER_API_KEY` | ✅ | OpenWeatherMap key |
| `SMTP_EMAIL` | ✅ | Gmail address for sending emails |
| `SMTP_PASSWORD` | ✅ | Gmail App Password |
| `ADZUNA_APP_ID` | ✅ | Adzuna Jobs API app ID |
| `ADZUNA_APP_KEY` | ✅ | Adzuna Jobs API key |
| `ALPHA_VANTAGE_KEY` | ⬜ | Alpha Vantage key (extended market data) |
| `DATABASE_URL` | ⬜ | SQLite path (default: `sqlite:///./flora_os.db`) |

---

## License

MIT — free to use, modify, and distribute.

---

<div align="center">

Built with 🌿 by [Kumar Sundram](https://github.com/sundramsingh1501)

</div>
