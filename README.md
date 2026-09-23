# Twin-Mate V2

AI-powered habit tracker and life coaching web app.

**Local app URL (after starting):** [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Easiest way to run (Windows)

1. Double-click **`run.bat`** in the project folder  
   — or in Command Prompt:
   ```cmd
   run.bat
   ```
2. Your browser should open automatically to [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Run from Cursor / VS Code

1. Open this project folder in Cursor
2. Press **F5** (or Run → **Run Twin-Mate**)
3. Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Manual setup (Command Prompt)

```cmd
cd C:\Users\parma\OneDrive\Desktop\TWIN_MATE_V1
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Then open: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Environment variables

Copy `.env.example` to `.env` and set:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask session secret (required) |
| `MONGO_URI` | MongoDB connection string |
| `DB_NAME` | Database name |
| `OPENAI_API_KEY` | OpenAI API key for AI chat |

**MongoDB options:**
- Local: `mongodb://localhost:27017/`
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (free cloud): use your Atlas connection string

## Docker

```cmd
docker compose up
```

App: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## App pages (after login)

| Page | URL |
|---|---|
| Login | [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login) |
| Sign up | [http://127.0.0.1:5000/signup](http://127.0.0.1:5000/signup) |
| Home | [http://127.0.0.1:5000/home](http://127.0.0.1:5000/home) |
| Check-in | [http://127.0.0.1:5000/checkin](http://127.0.0.1:5000/checkin) |
| Tracker | [http://127.0.0.1:5000/dashboard](http://127.0.0.1:5000/dashboard) |
| AI Chat | [http://127.0.0.1:5000/chat](http://127.0.0.1:5000/chat) |
| Profile | [http://127.0.0.1:5000/profile](http://127.0.0.1:5000/profile) |

## API endpoints

| Method | URL |
|---|---|
| GET | [http://127.0.0.1:5000/api/v1/dashboard](http://127.0.0.1:5000/api/v1/dashboard) |
| GET | [http://127.0.0.1:5000/api/v1/goals](http://127.0.0.1:5000/api/v1/goals) |
| GET/POST | [http://127.0.0.1:5000/api/v1/checkin](http://127.0.0.1:5000/api/v1/checkin) |
| POST | [http://127.0.0.1:5000/api/v1/chat](http://127.0.0.1:5000/api/v1/chat) |

## Tests

```cmd
set FLASK_ENV=testing
python -m pytest -q
```

## Features

- User auth with Flask-Login, CSRF protection, and rate limiting
- Multi-step onboarding wizard
- Date-keyed daily check-ins (mood, energy, goals, journal note)
- Dashboard with week view, Chart.js trends, goal progress rings, heatmap, and calendar
- AI chat coach (GPT-4o-mini) with suggested prompts and voice input
- Email and web push reminders (SendGrid/Resend + pywebpush)
- Profile settings, data export, account deletion
- REST API at `/api/v1/` for future mobile apps
- PWA support (manifest + service worker)
