# Hospitality AI Platform

An AI-powered restaurant management platform that unifies KPI analytics, Menu Engineering, Beverage Management, HR Optimization, Recipe Intelligence, and Strategic Planning behind a single agent API and a modern Next.js dashboard.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Repository Structure](#repository-structure)
5. [Getting Started](#getting-started)
6. [Environment Variables](#environment-variables)
7. [Backend — API Reference](#backend--api-reference)
8. [Frontend — Dashboard Modules](#frontend--dashboard-modules)
9. [Business Analysis Domains](#business-analysis-domains)
10. [CSV Upload Specifications](#csv-upload-specifications)
11. [Deployment](#deployment)
12. [Documentation](#documentation)
13. [License](#license)

---

## Overview

Hospitality AI is a full-stack consulting platform built for restaurant operators. It turns raw operational data — sales, labor, inventory, recipes, and beverage records — into actionable HTML business reports, structured metrics, and AI-driven recommendations.

**Core capabilities:**
- Unified REST API that accepts both JSON payloads and CSV file uploads
- AI-generated HTML business reports with performance badges, benchmarks, and recommendations
- Nine dashboard modules covering every major area of restaurant operations
- Conversational chat assistant for on-demand business insights
- Role-based entitlement gating for premium KPI features

---

## Architecture

```
┌─────────────────────────────────┐     ┌──────────────────────────────────┐
│         Frontend (Next.js)      │     │        Backend (Django)           │
│                                 │     │                                   │
│  /dashboard/*  →  services/     │────▶│  /api/agent/  (unified endpoint)  │
│  React 19 + Tailwind + Recharts │     │  /api/agent/safe/  (card tasks)   │
│  shadcn/ui components           │     │  /chat/api/   (conversational AI) │
└─────────────────────────────────┘     └──────────────┬────────────────────┘
                                                        │
                                        ┌───────────────▼──────────────────┐
                                        │      Business Logic Layer         │
                                        │  backend/consulting_services/     │
                                        │  ├── beverage/  (3 features)      │
                                        │  ├── hr/        (4 features)      │
                                        │  ├── kpi/       (4 features)      │
                                        │  ├── menu/      (5 features)      │
                                        │  ├── recipe/    (3 features)      │
                                        │  └── strategy/  (6 features)      │
                                        └──────────────────────────────────┘
```

**Architecture pattern:** Polymonolith — organized like microservices, deployed as a monolith. The Django app layer handles HTTP routing; all business logic lives in `backend/consulting_services/` and is fully decoupled from Django.

---

## Tech Stack

### Backend
| Component | Technology |
|---|---|
| Framework | Django 4.2 + Django REST Framework |
| Language | Python 3.10+ |
| AI / LLM | OpenAI API |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Validation | Pydantic v2 |
| Config | django-environ |
| CORS | django-cors-headers |
| Tunneling (dev) | ngrok |

### Frontend
| Component | Technology |
|---|---|
| Framework | Next.js 16 (App Router) |
| Language | TypeScript / React 19 |
| Styling | Tailwind CSS + shadcn/ui (Radix UI) |
| Charts | Recharts |
| Animation | Motion (Framer Motion) |
| Forms | React Hook Form + Zod |
| Theming | next-themes (dark / light) |
| Sanitization | DOMPurify |

---

## Repository Structure

```
Hospitality_AI_Restaurant_Website/
├── Backend/
│   ├── apps/
│   │   ├── agent_core/          # Unified API gateway — routes tasks, validates schemas
│   │   ├── chat_assistant/      # Conversational AI endpoint
│   │   ├── dashboard/           # Django-rendered dashboard views
│   │   ├── beverage_api/        # Beverage domain REST endpoints
│   │   ├── hr_api/              # HR domain REST endpoints
│   │   ├── kpi_api/             # KPI domain REST endpoints
│   │   ├── menu_api/            # Menu domain REST endpoints
│   │   ├── recipe_api/          # Recipe domain REST endpoints
│   │   └── strategic_api/       # Strategic domain REST endpoints
│   ├── backend/
│   │   ├── consulting_services/ # All business logic (27 features across 7 domains)
│   │   │   ├── beverage/        # Liquor cost, bar inventory, beverage pricing
│   │   │   ├── hr/              # Retention, scheduling, performance, analysis
│   │   │   ├── kpi/             # KPI summary, labor, food, sales, prime cost
│   │   │   ├── menu/            # Product mix, pricing, design matrix, optimization
│   │   │   ├── recipe/          # Recipe costing, scaling, management
│   │   │   └── strategy/        # Strategic planning and business insights
│   │   └── shared/              # AI utilities, report formatters, common helpers
│   ├── config/                  # Django settings, URLs, ASGI/WSGI
│   ├── docs/                    # Full documentation suite
│   ├── infrastructure/          # Deployment, monitoring, network config
│   └── requirements.txt
│
└── Frontend/
    ├── app/
    │   ├── auth/                # Authentication pages
    │   └── dashboard/           # Nine analytics dashboard pages
    ├── components/              # Reusable UI components (shadcn/ui + custom)
    ├── services/                # API client layer (one file per domain)
    ├── hooks/                   # Custom React hooks
    ├── lib/                     # Utility functions
    └── providers/               # React context providers
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key

### 1 — Clone

```bash
git clone https://github.com/<your-org>/Hospitality_AI_Restaurant_Website.git
cd Hospitality_AI_Restaurant_Website
```

### 2 — Backend

```bash
cd Backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Backend runs at `http://localhost:8000`.

### 3 — Frontend

```bash
cd Frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## Environment Variables

Create a `.env` file in the `Backend/` directory (or one level above, depending on your setup):

```env
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# OpenAI
OPENAI_API_KEY=sk-...

# Database (production)
DATABASE_URL=postgres://user:password@host:5432/dbname

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

Create a `.env.local` file in the `Frontend/` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

See [`Backend/docs/ENVIRONMENT_VARIABLES.md`](Backend/docs/ENVIRONMENT_VARIABLES.md) for the full reference.

---

## Backend — API Reference

### Unified Agent Endpoint

```
POST /api/agent/
```

Accepts JSON payloads or multipart CSV file uploads.

**JSON format:**
```json
{
  "task": "<task_name>",
  "payload": { ... }
}
```

**CSV format:**
```
FormData: task=<task_name>, file=<csv_file>
```

**Response fields:**

| Field | Description |
|---|---|
| `status` | `success` or `error` |
| `analysis_type` | Human-readable analysis name |
| `business_report_html` | Full HTML report (use this for rendering) |
| `business_report` | Plain text fallback |
| `metrics` / `summary` / `recommendations` | Structured data objects |
| `industry_benchmarks` | Benchmark comparisons |

**Entitlement header** (required for KPI tasks):
```
X-KPI-Analysis-Entitled: true
```

### Safe Card Endpoint

```
POST /api/agent/safe/
```

```json
{
  "service": "<service_name>",
  "subtask": "<subtask_name>",
  "params": { ... }
}
```

### Chat Endpoint

```
POST /chat/api/
```

```json
{
  "message": "What is my prime cost?",
  "context": "beverage"
}
```

### Task Catalog

| Domain | Task Name |
|---|---|
| **Beverage** | `liquor_cost_analysis`, `bar_inventory_analysis`, `beverage_pricing_analysis` |
| **KPI** | `kpi_summary`, `labor_cost_analysis`, `prime_cost_analysis`, `sales_performance_analysis`, `food_cost_analysis` |
| **Menu** | `product_mix_analysis`, `menu_pricing_strategy`, `item_optimization` |
| **HR** | `hr_retention`, `hr_scheduling`, `hr_performance`, `hr_analysis` |
| **Recipe** | `recipe_management` |
| **Cost** | `labor_cost`, `food_cost`, `prime_cost`, `liquor_cost`, `cost_analysis` |

---

## Frontend — Dashboard Modules

| Module | Route | Description |
|---|---|---|
| KPI Analysis | `/dashboard/kpi-analysis` | Prime cost, labor, food cost & sales performance |
| CSV KPI Dashboard | `/dashboard/csv-kpi-dashboard` | Upload CSV for batch KPI reporting |
| Beverage Insights | `/dashboard/beverage-insights` | Liquor cost, bar inventory & beverage pricing |
| Menu Engineering | `/dashboard/menu-engineering` | Product mix, pricing strategy & item optimization |
| HR Optimization | `/dashboard/hr-optimization` | Labor scheduling & HR cost analysis |
| Recipe Intelligence | `/dashboard/recipe-intelligence` | Recipe costing & ingredient optimization |
| Strategic Planning | `/dashboard/strategic-planning` | High-level business strategy insights |
| History | `/dashboard/history` | Log of past analyses |
| Profile | `/dashboard/profile` | User account settings |

---

## Business Analysis Domains

### Beverage Management
- **Liquor Cost Analysis** — theoretical vs actual pour cost, waste %, cost percentage vs target
- **Bar Inventory Analysis** — reorder triggers, turnover rate, inventory valuation
- **Beverage Pricing Analysis** — margin calculation, competitive gap, elasticity-adjusted revenue

### KPI Analytics
- **KPI Summary** — daily KPI aggregation with trend comparisons and AI insights
- **Labor Cost Analysis** — labor % of sales, scheduling efficiency
- **Prime Cost Analysis** — combined labor + food cost vs industry benchmarks
- **Sales Performance Analysis** — revenue trends, cover counts, average check
- **Food Cost Analysis** — food cost %, waste, variance from target

### Menu Engineering
- **Product Mix Analysis** — menu item popularity and profitability classification
- **Menu Pricing Strategy** — competitive pricing gap, food cost % alignment
- **Menu Design Matrix** — Stars / Plowhorses / Puzzles / Dogs classification
- **Item Optimization** — waste detection, high-cost low-sales flagging

### HR Optimization
- **Retention Analysis** — turnover rate, risk segmentation
- **Scheduling Optimization** — labor hour efficiency, shift recommendations
- **Performance Analysis** — productivity metrics, goal attainment
- **HR Analysis** — composite HR health scoring

### Recipe Intelligence
- **Recipe Costing** — ingredient-level cost breakdown, portion analysis
- **Recipe Scaling** — batch scaling with cost recalculation

### Strategic Planning
- Six strategy features covering market positioning, revenue diversification, and growth planning

---

## CSV Upload Specifications

### KPI Analysis
| Column | Required |
|---|---|
| `date`, `sales`, `labor_cost`, `food_cost`, `labor_hours` | ✅ |
| Variants: `revenue`, `wages`, `cogs` | Auto-mapped |

### Product Mix
| Column | Required |
|---|---|
| `item_name`, `quantity_sold`, `price` | ✅ |
| `cost`, `food_cost_pct`, `category` | Optional |

### Bar Inventory
| Column | Required |
|---|---|
| `current_stock`, `reorder_point`, `monthly_usage`, `inventory_value` | ✅ |
| `lead_time_days`, `safety_stock`, `item_cost`, `target_turnover` | Optional |

### Liquor Cost
| Column | Required |
|---|---|
| `expected_oz`, `actual_oz`, `liquor_cost`, `total_sales` | ✅ |
| `bottle_cost`, `bottle_size_oz`, `target_cost_percentage` | Optional |

### Beverage Pricing
| Column | Required |
|---|---|
| `drink_price`, `cost_per_drink`, `sales_volume`, `competitor_price` | ✅ |
| `target_margin`, `market_position`, `elasticity_factor` | Optional |

### Recipe Management
| Column | Required |
|---|---|
| `recipe_name`, `ingredient_cost`, `portion_cost`, `recipe_price`, `servings`, `labor_cost` | ✅ |

---

## Deployment

### Backend — AWS / Self-hosted

See [`Backend/docs/AWS_DEPLOYMENT.md`](Backend/docs/AWS_DEPLOYMENT.md) and [`Backend/docs/PRODUCTION_CHECKLIST.md`](Backend/docs/PRODUCTION_CHECKLIST.md).

```bash
# Production settings
export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY=<strong-secret>
python manage.py collectstatic
gunicorn config.wsgi:application
```

### Frontend — Vercel (recommended)

Connect the repository to [vercel.com](https://vercel.com) and set `NEXT_PUBLIC_API_URL` to your production backend URL.

```bash
npm run build
npm start
```

### ngrok (local tunneling for dev)

See [`Backend/infrastructure/ngrok/`](Backend/infrastructure/ngrok/) for the ngrok config used to expose the local backend during development.

---

## Documentation

| Document | Description |
|---|---|
| [`ARCHITECTURE_STRUCTURE.md`](Backend/docs/ARCHITECTURE_STRUCTURE.md) | Full system architecture and feature inventory |
| [`ENVIRONMENT_VARIABLES.md`](Backend/docs/ENVIRONMENT_VARIABLES.md) | All required and optional env vars |
| [`AWS_DEPLOYMENT.md`](Backend/docs/AWS_DEPLOYMENT.md) | AWS deployment guide |
| [`PRODUCTION_CHECKLIST.md`](Backend/docs/PRODUCTION_CHECKLIST.md) | Pre-launch checklist |
| [`PRODUCTION_READINESS_REPORT.md`](Backend/docs/PRODUCTION_READINESS_REPORT.md) | System readiness assessment |
| [`MENU_ENGINEERING_IMPLEMENTATION.md`](Backend/docs/MENU_ENGINEERING_IMPLEMENTATION.md) | Menu engineering deep dive |
| [`CONVERSATIONAL_AI_PLAN.md`](Backend/docs/CONVERSATIONAL_AI_PLAN.md) | Chat assistant architecture |
| [`BUSINESS_LOGIC_WORKFLOW.md`](Backend/docs/BUSINESS_LOGIC_WORKFLOW.md) | End-to-end request flow |
| [`DATA_SOURCE_GUIDE.md`](Backend/docs/DATA_SOURCE_GUIDE.md) | Data ingestion and CSV specs |
| [Postman Collection — API](Backend/docs/Hospitality_AI_API.postman_collection.json) | API test collection |
| [Postman Collection — Dashboard](Backend/docs/Hospitality_AI_Dashboard.postman_collection.json) | Dashboard flow tests |

---

## License

MIT. See [LICENSE](Backend/LICENSE).
