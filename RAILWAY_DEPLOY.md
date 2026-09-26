# HealthSetu Railway Deployment Guide

This guide enables any contributor or team member to deploy the HealthSetu backend to **Railway** in 2 minutes.

---

## Prerequisites
- A [Railway account](https://railway.com) (free or pro)
- GitHub access to [kamanasis/HealthSetu](https://github.com/kamanasis/HealthSetu)

---

## Method 1: Web Dashboard (Recommended & Easiest)

1. **Log in to Railway**: Go to [railway.com](https://railway.com).
2. **Create New Project**:
   - Click **+ New Project** (or **Deploy from GitHub repo**).
   - Select the repository: `kamanasis/HealthSetu`.
   - Branch: `main`.
3. **Automatic Build**:
   - Railway will automatically detect `railway.json` and `Dockerfile`.
   - It will build the Python 3.12 Docker image and run uvicorn on the dynamic `$PORT`.
4. **Generate Public Domain**:
   - In your Railway project, click on the **HealthSetu service**.
   - Go to **Settings** → **Networking** (or **Public Networking**).
   - Click **Generate Domain** (e.g. `healthsetu-production.up.railway.app`).
5. **Verify Backend Health**:
   - Visit `https://<your-railway-domain>/api/v1/health` in your browser.
   - You should see:
     ```json
     {"status":"ok","service":"healthsetu-backend","version":"0.1.0"}
     ```
   - Swagger API Docs are available at `https://<your-railway-domain>/docs`.

---

## Method 2: Railway CLI (From Terminal)

```bash
# 1. Clone the repository (if not already cloned)
git clone https://github.com/kamanasis/HealthSetu.git
cd HealthSetu

# 2. Login to Railway
npx @railway/cli login

# 3. Initialize and deploy
npx @railway/cli init
npx @railway/cli up

# 4. Generate public domain
npx @railway/cli domain
```

---

## Optional Environment Variables

The backend runs out-of-the-box in demo mode with in-memory stores. If you want persistent PostgreSQL database or production settings, set these in Railway under **Variables**:

| Variable | Recommended Value | Notes |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Enables production mode |
| `PORT` | `8000` | Injected automatically by Railway |
| `DATABASE_URL` | *Railway Postgres URL* | Optional: Add a PostgreSQL service on Railway |
| `JWT_SECRET_KEY` | *(Random 32-byte string)* | e.g. `openssl rand -hex 32` |
| `CORS_ALLOWED_ORIGINS` | `https://health-setu-giaa.vercel.app` | Already pre-configured in code with regex for `*.vercel.app` |

---

## Connecting Railway Backend to the Vercel Frontend

Once you have your Railway public domain (e.g. `https://healthsetu-production.up.railway.app`):
1. Open the [Vercel Project Settings](https://vercel.com).
2. Go to **Settings** → **Environment Variables**.
3. Add / update:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: `https://<your-railway-domain>`
4. Trigger a **Redeploy** on Vercel.
5. The live frontend at `https://health-setu-giaa.vercel.app` is now completely connected to the Railway backend!
