# StockPilot

**Intelligent Inventory Management System**

StockPilot is a modern, full-featured inventory management API built with FastAPI and Python. It provides real-time stock tracking, smart alerts, and comprehensive reporting to help businesses manage their inventory efficiently.

---

## Features

- **User Authentication & Authorization** — JWT-based auth with role-based access control (admin, manager, staff)
- **Inventory Management** — Full CRUD operations for products, categories, and stock levels
- **Stock Tracking** — Real-time stock level monitoring with automatic low-stock alerts
- **Supplier Management** — Track suppliers, purchase orders, and delivery schedules
- **Reporting & Analytics** — Generate inventory reports, stock movement history, and valuation summaries
- **Search & Filtering** — Advanced search with pagination, sorting, and metadata filtering
- **Audit Trail** — Complete history of all inventory changes with timestamps and user attribution
- **Bulk Operations** — Batch import/export of inventory data via CSV
- **RESTful API** — Clean, well-documented API with OpenAPI/Swagger UI

---

## Tech Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| **Runtime**    | Python 3.12                         |
| **Framework**  | FastAPI                             |
| **Database**   | PostgreSQL + SQLAlchemy 2.0 (async) |
| **Auth**       | JWT (python-jose) + bcrypt          |
| **Validation** | Pydantic v2                         |
| **Server**     | Uvicorn                             |
| **Migrations** | Alembic                             |
| **Testing**    | pytest + httpx + pytest-asyncio     |

---

## Project Structure

```
stockpilot/
├── alembic/                    # Database migrations
│   ├── versions/
│   └── env.py
├── alembic.ini
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Pydantic Settings configuration
│   ├── database.py             # Async SQLAlchemy engine & session
│   ├── dependencies.py         # Shared dependencies (auth, db, pagination)
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── category.py
│   │   ├── item.py
│   │   ├── supplier.py
│   │   └── stock_movement.py
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── category.py
│   │   ├── item.py
│   │   ├── supplier.py
│   │   └── stock_movement.py
│   ├── routes/                 # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── categories.py
│   │   ├── items.py
│   │   ├── suppliers.py
│   │   ├── stock_movements.py
│   │   └── reports.py
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── inventory.py
│   │   └── report.py
│   └── utils/                  # Shared utilities
│       ├── __init__.py
│       ├── security.py
│       └── pagination.py
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_items.py
│   └── test_categories.py
├── .env.example                # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- pip or a virtual environment manager (venv, poetry, etc.)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/stockpilot.git
cd stockpilot
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration (see [Environment Variables](#environment-variables) below).

### 5. Set Up the Database

Create the PostgreSQL database:

```bash
createdb stockpilot
```

Run migrations:

```bash
alembic upgrade head
```

### 6. Seed Default Data (Optional)

```bash
python -m app.seeds
```

### 7. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

- **API Base URL:** `http://localhost:8000`
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## Environment Variables

| Variable                | Description                              | Default               | Required |
|-------------------------|------------------------------------------|-----------------------|----------|
| `DATABASE_URL`          | PostgreSQL async connection string       | —                     | ✅        |
| `SECRET_KEY`            | JWT signing secret (min 32 chars)        | —                     | ✅        |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime (minutes) | `30`                  | ❌        |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | JWT refresh token lifetime (days)  | `7`                   | ❌        |
| `ALGORITHM`             | JWT signing algorithm                    | `HS256`               | ❌        |
| `CORS_ORIGINS`          | Comma-separated allowed origins          | `http://localhost:3000` | ❌      |
| `LOG_LEVEL`             | Logging level                            | `INFO`                | ❌        |
| `ENVIRONMENT`           | Runtime environment                      | `development`         | ❌        |
| `DEFAULT_ADMIN_EMAIL`   | Seed admin email                         | `admin@stockpilot.io` | ❌        |
| `DEFAULT_ADMIN_PASSWORD`| Seed admin password                      | `changeme123`         | ❌        |

### Example `.env`

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/stockpilot
SECRET_KEY=your-super-secret-key-at-least-32-characters-long
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
LOG_LEVEL=INFO
ENVIRONMENT=development
```

---

## ⚠️ Default Credentials Warning

When the application is seeded, a default admin account is created:

| Field    | Value                 |
|----------|-----------------------|
| Email    | `admin@stockpilot.io` |
| Password | `changeme123`         |

> **🔴 IMPORTANT:** Change the default admin password immediately after first login. Never use default credentials in production. Set `DEFAULT_ADMIN_EMAIL` and `DEFAULT_ADMIN_PASSWORD` environment variables to override the defaults during seeding.

---

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_auth.py

# Run with coverage report
pytest --cov=app --cov-report=term-missing
```

---

## Deployment

### Deploy to Vercel

StockPilot can be deployed to Vercel as a serverless function.

#### 1. Install the Vercel CLI

```bash
npm install -g vercel
```

#### 2. Add a `vercel.json` Configuration

Create `vercel.json` in the project root:

```json
{
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

#### 3. Set Environment Variables

Configure all required environment variables in the Vercel dashboard:

- Go to **Project Settings → Environment Variables**
- Add `DATABASE_URL`, `SECRET_KEY`, and all other required variables
- Use a managed PostgreSQL service (e.g., Vercel Postgres, Neon, Supabase) for the database URL

#### 4. Deploy

```bash
vercel --prod
```

### Deploy with Docker (Alternative)

```bash
# Build the image
docker build -t stockpilot .

# Run the container
docker run -d \
  --name stockpilot \
  -p 8000:8000 \
  --env-file .env \
  stockpilot
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Use a strong, unique `SECRET_KEY` (generate with `openssl rand -hex 32`)
- [ ] Change default admin credentials
- [ ] Configure `CORS_ORIGINS` to only allow your frontend domain(s)
- [ ] Enable HTTPS / TLS termination
- [ ] Set up database backups
- [ ] Configure log aggregation
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR` for production

---

## API Usage Guide

### Authentication

#### Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "Jane Doe"
  }'
```

#### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

#### Use the Token

Include the access token in the `Authorization` header for all protected endpoints:

```bash
curl -X GET http://localhost:8000/api/v1/items \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### Inventory Operations

#### Create a Category

```bash
curl -X POST http://localhost:8000/api/v1/categories \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Electronics",
    "description": "Electronic devices and components"
  }'
```

#### Add an Inventory Item

```bash
curl -X POST http://localhost:8000/api/v1/items \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Arduino Uno R4",
    "sku": "ELEC-ARD-001",
    "category_id": 1,
    "quantity": 150,
    "unit_price": 27.50,
    "reorder_level": 20,
    "supplier_id": 1
  }'
```

#### List Items with Pagination & Filtering

```bash
curl -X GET "http://localhost:8000/api/v1/items?page=1&per_page=20&category_id=1&search=arduino" \
  -H "Authorization: Bearer <token>"
```

#### Record a Stock Movement

```bash
curl -X POST http://localhost:8000/api/v1/stock-movements \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": 1,
    "movement_type": "OUT",
    "quantity": 5,
    "reference": "ORDER-2024-0042",
    "notes": "Shipped to customer"
  }'
```

#### Generate an Inventory Report

```bash
curl -X GET "http://localhost:8000/api/v1/reports/inventory-summary" \
  -H "Authorization: Bearer <token>"
```

---

## License

**Private** — All rights reserved. This software is proprietary and confidential. Unauthorized copying, distribution, or modification is strictly prohibited.