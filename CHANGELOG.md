# Changelog

## V2.0.0

- Refactored monolithic `app.py` into Flask blueprints and services layer
- Security: env-based `SECRET_KEY`, Flask-Login, CSRF, rate limiting
- Data model: date-keyed check-ins; chat messages in separate collection
- Real daily check-in flow with mood, energy, and journal notes
- Dashboard: week view, Chart.js, progress rings, AI focus tip
- AI chat: richer context, suggested prompts, voice input, streaming endpoint
- Notifications: APScheduler email reminders + web push subscriptions
- Profile page: edit settings, export data, delete account
- Onboarding wizard for new users
- PWA manifest and service worker
- REST API at `/api/v1/`
- Docker, pytest, and GitHub Actions CI
