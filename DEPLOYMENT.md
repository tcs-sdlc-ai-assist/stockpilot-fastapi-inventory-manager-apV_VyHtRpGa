# StockPilot Deployment Guide — Vercel

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure Overview](#project-structure-overview)
- [vercel.json Configuration](#verceljson-configuration)
- [Environment Variables](#environment-variables)
- [Deployment Steps](#deployment-steps)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)
- [SQLite Persistence Caveats on Serverless](#sqlite-persistence-caveats-on-serverless)
- [Production Recommendations](#production-recommendations)

---

## Prerequisites

Before deploying StockPilot to Vercel, ensure you have the following:

1. **Vercel Account** — Sign up at [vercel.com](https://vercel.com) if you don't have one.
2. **Git Repository** — Your StockPilot codebase must be hosted on GitHub, GitLab, or Bitbucket.
3. **Vercel CLI (optional)** — Install globally for local testing and manual deployments:
   ```bash
   npm install -g vercel
   ```
4. **Python 3.12** — Vercel's Python runtime supports 3.12. Ensure your `runtime.txt` or Vercel project settings specify this version.
5. **requirements.txt** — All Python dependencies must be listed and pinned in `requirements.txt` at the project root.

---

## Project Structure Overview

```
stockpilot/
├── main.py                  # FastAPI application entry point
├── requirements.txt         # Python dependencies
├── vercel.json              # Vercel deployment configuration
├── .env.example             # Example environment variables
├── config.py                # Pydantic Settings configuration
├── database.py              # SQLAlchemy async engine & session
├── models/                  # SQLAlchemy ORM models
│   └── __init__.py
├── routes/                  # FastAPI route modules
│   └── __init__.py
├── schemas/                 # Pydantic request/response schemas
│   └── __init__.py
├── services/                # Business logic layer
│   └── __init__.py
├── static/                  # Static assets (CSS, JS, images)
├── templates/               # Jinja2 HTML templates
└── tests/                   # Test suite
```

---

## vercel.json Configuration

Create a `vercel.json` file in the project root. This tells Vercel how to build and route requests to your FastAPI application.

```json
{
  "version": 2,
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    },
    {
      "src": "static/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "main.py"
    }
  ]
}
```

### Explanation

| Key | Purpose |
|-----|---------|
| `builds[0]` | Tells Vercel to use the Python runtime to build and serve `main.py`. The `@vercel/python` builder expects an ASGI-compatible `app` object exported from this file. |
| `builds[1]` | Serves everything under `static/` as static files without going through the Python runtime. |
| `routes[0]` | Routes any request matching `/static/*` directly to the static file builder — bypasses the Python function entirely. |
| `routes[1]` | Catch-all route that sends every other request to `main.py` (your FastAPI app). |

> **Important:** Vercel's Python builder looks for a variable named `app` in your entry-point file. Ensure `main.py` exports the FastAPI instance as `app`:
> ```python
> from fastapi import FastAPI
> app = FastAPI(title="StockPilot")
> ```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./stockpilot.db` or `postgresql+asyncpg://user:pass@host/db` |
| `SECRET_KEY` | JWT signing key — must be a strong random string (min 32 chars) | `a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5` |
| `ENVIRONMENT` | Deployment environment | `production` |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins | `https://yourdomain.com,https://www.yourdomain.com` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token lifetime in minutes | `30` |

### Setting Variables on Vercel Dashboard

1. Go to your project on [vercel.com](https://vercel.com).
2. Navigate to **Settings** → **Environment Variables**.
3. Add each variable:
   - Enter the **Name** (e.g., `SECRET_KEY`).
   - Enter the **Value**.
   - Select the target environments: **Production**, **Preview**, and/or **Development**.
   - Click **Save**.
4. Repeat for all required variables.

> **Security Note:** Never commit `.env` files to your repository. Use `.env.example` as a template with placeholder values only.

### Using Vercel CLI

You can also set environment variables via the CLI:

```bash
vercel env add SECRET_KEY production
# You will be prompted to enter the value
```

To pull environment variables for local development:

```bash
vercel env pull .env.local
```

---

## Deployment Steps

### Option A: Deploy via Vercel Dashboard (Recommended)

1. **Connect Repository**
   - Log in to [vercel.com](https://vercel.com).
   - Click **"Add New…"** → **"Project"**.
   - Select your Git provider (GitHub, GitLab, Bitbucket).
   - Find and select the `stockpilot` repository.

2. **Configure Project**
   - **Framework Preset:** Select **"Other"** (Vercel does not auto-detect FastAPI).
   - **Root Directory:** Leave as `/` unless your code is in a subdirectory.
   - **Build Command:** Leave empty — the `@vercel/python` builder handles this via `vercel.json`.
   - **Output Directory:** Leave empty.
   - **Install Command:** Leave empty — dependencies are installed from `requirements.txt` automatically.

3. **Set Environment Variables**
   - Add all required environment variables as described in the [Environment Variables](#environment-variables) section.

4. **Deploy**
   - Click **"Deploy"**.
   - Vercel will build and deploy your application. The first deployment typically takes 1–3 minutes.
   - Once complete, you'll receive a deployment URL (e.g., `https://stockpilot-xxxx.vercel.app`).

5. **Verify**
   - Visit `https://your-deployment-url.vercel.app/docs` to confirm the FastAPI Swagger UI loads.
   - Test a health-check endpoint if available (e.g., `GET /health`).

### Option B: Deploy via Vercel CLI

```bash
# Navigate to your project root
cd stockpilot

# Login to Vercel (first time only)
vercel login

# Deploy to preview environment
vercel

# Deploy to production
vercel --prod
```

### Option C: Deploy via Git Push (Auto-Deploy)

Once your repository is connected to Vercel:

- **Push to `main` branch** → triggers a **production** deployment.
- **Push to any other branch** → triggers a **preview** deployment.
- **Open a Pull Request** → Vercel creates a unique preview URL for that PR.

---

## CI/CD Integration

### Automatic Deployments

By default, Vercel deploys automatically on every push to your connected repository. No additional CI/CD configuration is needed for basic deployments.

### Running Tests Before Deployment

To ensure tests pass before deploying, you can use GitHub Actions (or your CI provider) alongside Vercel:

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        run: |
          pytest tests/ -v --tb=short
        env:
          DATABASE_URL: "sqlite+aiosqlite:///./test.db"
          SECRET_KEY: "test-secret-key-not-for-production"
          ENVIRONMENT: "testing"
```

### Skipping Deployments

Add `[skip ci]` or `[vercel skip]` to your commit message to prevent a Vercel deployment:

```bash
git commit -m "Update README [skip ci]"
```

### Ignored Build Step

You can configure Vercel to skip builds for certain paths. In your project settings or `vercel.json`:

```json
{
  "git": {
    "deploymentEnabled": {
      "main": true,
      "develop": true
    }
  },
  "ignoreCommand": "git diff HEAD^ HEAD --quiet -- . ':!docs' ':!*.md'"
}
```

This skips deployment if only documentation or markdown files changed.

---

## Troubleshooting

### 404 Errors on API Routes

**Symptom:** All API routes return 404, but the deployment succeeded.

**Causes & Fixes:**

1. **Missing catch-all route in `vercel.json`:**
   Ensure the last route entry catches all paths and forwards to `main.py`:
   ```json
   { "src": "/(.*)", "dest": "main.py" }
   ```

2. **`app` variable not found:**
   Vercel's Python builder looks for a variable named `app` in your entry-point file. Verify `main.py` has:
   ```python
   app = FastAPI(...)
   ```
   Do NOT wrap it in `if __name__ == "__main__"`.

3. **Router not included:**
   Ensure all routers are registered with `app.include_router(...)` in `main.py` at module level — not inside a function that only runs conditionally.

### Static Files Not Loading (CSS, JS, Images)

**Symptom:** Pages load but styles/scripts are missing; browser console shows 404 for `/static/*` files.

**Causes & Fixes:**

1. **Missing static build entry in `vercel.json`:**
   Ensure you have the static builder configured:
   ```json
   { "src": "static/**", "use": "@vercel/static" }
   ```

2. **Route ordering matters:**
   The `/static/(.*)` route MUST appear BEFORE the catch-all `/(.*)` route. Vercel evaluates routes top-to-bottom; if the catch-all is first, static requests go to Python.

3. **File paths are case-sensitive:**
   Vercel runs on Linux. `Static/style.css` ≠ `static/style.css`. Ensure your HTML references match the exact file paths.

4. **FastAPI StaticFiles mount conflicts:**
   If you also mount static files in FastAPI (`app.mount("/static", StaticFiles(...))`), this can conflict with Vercel's static builder. On Vercel, let the `@vercel/static` builder handle static files and remove or conditionally disable the FastAPI mount:
   ```python
   import os
   if os.getenv("ENVIRONMENT") != "production":
       app.mount("/static", StaticFiles(directory="static"), name="static")
   ```

### 500 Internal Server Error

**Symptom:** Deployment succeeds but requests return 500.

**Debugging Steps:**

1. Check **Vercel Function Logs:**
   - Go to your project → **Deployments** → select the deployment → **Functions** tab → click on the function → view **Logs**.

2. **Missing environment variables:**
   The most common cause. Verify all required variables are set in the Vercel dashboard for the correct environment (Production vs. Preview).

3. **Import errors:**
   A missing dependency in `requirements.txt` causes an `ImportError` at cold start. Check logs for the specific module name and add it to `requirements.txt`.

4. **Database connection failures:**
   If using an external database (PostgreSQL, MySQL), ensure the connection string is correct and the database server allows connections from Vercel's IP ranges. Consider using connection pooling (e.g., PgBouncer, Supabase pooler).

### Cold Start Timeouts

**Symptom:** First request after inactivity takes 10+ seconds or times out.

**Explanation:** Vercel Serverless Functions have cold starts. The Python runtime needs to initialize, install dependencies, and import your application on each cold start.

**Mitigations:**

- Minimize dependencies in `requirements.txt` — remove unused packages.
- Use lazy imports for heavy libraries (load them inside functions, not at module level).
- Consider Vercel's **Edge Functions** for latency-sensitive endpoints (note: Edge Functions use JavaScript/WASM, not Python).
- Upgrade to Vercel Pro/Enterprise for longer function timeouts and more memory.

### Build Failures

**Symptom:** Deployment fails during the build step.

**Common Causes:**

1. **Incompatible Python version:** Ensure your code is compatible with the Python version Vercel uses. Add a `runtime.txt` with:
   ```
   python-3.12
   ```

2. **Native dependencies:** Some Python packages (e.g., `psycopg2`) require system libraries that aren't available in Vercel's build environment. Use pure-Python alternatives:
   - `psycopg2` → `psycopg2-binary` or `asyncpg`
   - `bcrypt` → ensure version `4.0.1` if using with `passlib`

3. **requirements.txt syntax errors:** Ensure no trailing whitespace, no Windows line endings (use LF), and valid version specifiers.

---

## SQLite Persistence Caveats on Serverless

> **⚠️ Critical Warning:** SQLite is NOT suitable for production deployments on Vercel (or any serverless platform).

### Why SQLite Doesn't Work on Vercel

1. **Ephemeral Filesystem:** Vercel Serverless Functions run in ephemeral containers. The filesystem is read-only except for `/tmp`, and `/tmp` is wiped between invocations. Any SQLite database file written during a request is **lost** when the function instance is recycled.

2. **No Shared State:** Each function invocation may run in a different container. There is no shared filesystem between invocations, so concurrent requests may each see a different (or empty) database.

3. **Write Conflicts:** Even if you write to `/tmp`, concurrent function instances cannot share a SQLite file — SQLite uses file-level locking, which doesn't work across separate containers.

### What This Means for StockPilot

- **Development/Testing:** SQLite with `aiosqlite` works perfectly for local development and CI testing.
- **Vercel Deployment:** You MUST use an external database service.

### Recommended Database Options for Vercel

| Service | Protocol | Connection String Example |
|---------|----------|--------------------------|
| **Vercel Postgres** (powered by Neon) | PostgreSQL | `postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require` |
| **Supabase** | PostgreSQL | `postgresql+asyncpg://postgres:pass@db.xxx.supabase.co:5432/postgres` |
| **Neon** | PostgreSQL | `postgresql+asyncpg://user:pass@ep-xxx.neon.tech/dbname` |
| **PlanetScale** | MySQL | `mysql+aiomysql://user:pass@aws.connect.psdb.cloud/dbname?ssl=true` |
| **Railway** | PostgreSQL | `postgresql+asyncpg://postgres:pass@xxx.railway.app:5432/railway` |
| **Turso** (libSQL) | SQLite-compatible | Requires `libsql-client` — not a drop-in replacement for `aiosqlite` |

### Migration Steps (SQLite → PostgreSQL)

1. **Update `requirements.txt`:**
   ```
   asyncpg>=0.29.0
   ```
   Remove `aiosqlite` from production dependencies (keep for testing if desired).

2. **Update `DATABASE_URL` environment variable** on Vercel to your PostgreSQL connection string.

3. **Update `database.py`** to handle both SQLite (local) and PostgreSQL (production):
   ```python
   from config import settings

   if settings.DATABASE_URL.startswith("sqlite"):
       engine = create_async_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
   else:
       engine = create_async_engine(settings.DATABASE_URL, pool_size=5, max_overflow=10)
   ```

4. **Run migrations** against your production database using Alembic:
   ```bash
   DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head
   ```

---

## Production Recommendations

### Security Checklist

- [ ] `SECRET_KEY` is a cryptographically random string (min 32 characters).
- [ ] `DEBUG` is set to `false` in production.
- [ ] `ALLOWED_ORIGINS` is set to your specific domain(s) — never `*`.
- [ ] All sensitive environment variables are set via Vercel dashboard, not committed to code.
- [ ] HTTPS is enforced (Vercel handles this automatically).
- [ ] Database credentials use a dedicated production user with minimal privileges.

### Performance Tips

- **Connection Pooling:** Use connection pooling for your database. Serverless functions open/close connections frequently; a pooler (e.g., Neon's built-in pooler, PgBouncer) prevents exhausting database connections.
- **Response Caching:** Add `Cache-Control` headers to read-heavy endpoints.
- **Minimize Cold Starts:** Keep `requirements.txt` lean. Every unused package adds to cold start time.

### Monitoring

- **Vercel Analytics:** Enable in project settings for request-level performance data.
- **Vercel Logs:** Available in the dashboard under Deployments → Logs. For persistent logging, integrate with a service like Datadog, Sentry, or Logflare.
- **Error Tracking:** Add Sentry integration for Python exception tracking:
  ```bash
  # Add to requirements.txt
  sentry-sdk[fastapi]>=1.40.0
  ```

### Custom Domain

1. Go to your Vercel project → **Settings** → **Domains**.
2. Add your custom domain (e.g., `stockpilot.yourdomain.com`).
3. Configure DNS as instructed (CNAME or A record).
4. Vercel automatically provisions and renews SSL certificates.

---

## Quick Reference Commands

```bash
# Local development
uvicorn main:app --reload --port 8000

# Run tests
pytest tests/ -v

# Deploy preview
vercel

# Deploy production
vercel --prod

# View logs
vercel logs https://your-deployment-url.vercel.app

# List environment variables
vercel env ls

# Pull env vars for local dev
vercel env pull .env.local
```