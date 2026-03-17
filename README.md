# cicd-demo

A CI/CD pipeline portfolio project demonstrating GitHub Actions, automated testing, code quality gates, and continuous deployment to Render.

![CI](https://github.com/ss-bae/cicd-demo/actions/workflows/ci.yml/badge.svg)
![CD](https://github.com/ss-bae/cicd-demo/actions/workflows/cd.yml/badge.svg)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Developer                            │
│                    git push / PR                            │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CI Workflow (every push + PR to main)               │   │
│  │  1. Checkout code                                    │   │
│  │  2. Set up Python 3.12                               │   │
│  │  3. Install dev dependencies                         │   │
│  │  4. flake8 lint check          ──► FAIL → blocked    │   │
│  │  5. black format check         ──► FAIL → blocked    │   │
│  │  6. pytest + coverage          ──► FAIL → blocked    │   │
│  │  7. Upload coverage artifact                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CD Workflow (push to main only)                     │   │
│  │  1. Trigger Render deploy webhook                    │   │
│  │  2. Wait 30s for deploy to complete                  │   │
│  │  3. Health check /health endpoint                    │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Render (Free Hosting)                      │
│                                                             │
│  Build: pip install -r requirements.txt                     │
│  Start: gunicorn app.main:app                               │
│                                                             │
│  GET  /         → { message, status }                       │
│  GET  /health   → { status: "healthy" }                     │
│  GET  /items    → { items: [...] }                          │
│  POST /items    → { id, name }                              │
└─────────────────────────────────────────────────────────────┘
```

---

## What This Demonstrates

| Skill | How |
|---|---|
| GitHub Actions CI | Runs flake8, black, pytest on every push and PR |
| GitHub Actions CD | Auto-deploys to Render on merge to main |
| Python testing | pytest with coverage reporting |
| Code quality gates | flake8 (lint) + black (formatting) block merges |
| Docker | Containerized with a production-ready Dockerfile |
| Gated deploys | CD only runs after CI passes (branch protection) |
| REST API | Flask app with GET/POST endpoints |

---

## Local Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run the app
python -m app.main

# Run tests
pytest --cov=app tests/

# Lint
flake8 app/ tests/

# Format check
black --check app/ tests/

# Auto-format
black app/ tests/
```

---

## Render Deployment Setup

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New Web Service** → connect repo
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app.main:app`
5. Copy the **Deploy Hook URL** from the service settings
6. Add it to GitHub repo secrets as `RENDER_DEPLOY_HOOK`
7. Update the health check URL in `.github/workflows/cd.yml` with your Render URL

---

## API Reference

### `GET /`
```json
{ "message": "Hello, World!", "status": "ok" }
```

### `GET /health`
```json
{ "status": "healthy" }
```

### `GET /items`
```json
{ "items": [{ "id": 1, "name": "widget" }] }
```

### `POST /items`
Request: `{ "name": "widget" }`
Response (201): `{ "id": 1, "name": "widget" }`
