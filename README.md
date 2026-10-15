# Intelligent Sales Overview and Forecasting System

## Overview

This is a complete sales intelligence platform that brings together data analytics, machine learning, and modern web technologies. The system is designed to help businesses understand their sales patterns, predict future trends, and make data-driven decisions.

** Target Market:** MENA SME Retail Analytics  
** Killer Feature:** End-to-end Sales Overview + forecasting

The project consists of three main components:

- **Python Backend**: Handles data processing, sales forecasting, Customer Feedback, and product recommendations using FastAPI
- **React Frontend**: A modern interactive dashboard built with TypeScript and Vite for data visualization
- **Machine Learning Pipeline**: Prophet-based forecasting with full lifecycle including training, evaluation, prediction, and retraining capabilities

---

## Key Differentiators

| Feature | Description |
|---------|-------------|
| **Customer Lifetime Value** | CLV-based segmentation (Platinum/Gold/Silver/Bronze) |
| **Multi-Tenant** | Company-based data isolation for SaaS deployment |
| **Schema Resolver** | Works with any CSV column names |
| **Branch Isolation** | Tenant-scoped storage and analytics per company/branch |
| **RBAC** | JWT-backed roles for SUPER_ADMIN, COMPANY_ADMIN, BRANCH_ADMIN, EMPLOYEE, VIEWER |

---

##  Intelligence Modules

### New in v2.0

1. **Customer Lifetime Value** (`09_clv_calculation.py`)
   - Historical, Average, and Predictive CLV
   - Segment customers by value tier
   - Acquisition cost recommendations

---

## Requirements

Before getting started, make sure you have the following installed on your system:

### Python 3.8 or higher

Install the Python dependencies by running:

```bash
pip install -r requirements.txt
```

### Node.js 18 or higher

Navigate to the frontend folder and install the JavaScript dependencies:

```bash
cd frontend
npm install
```

---

## Project Structure

Here is how the project is organized:

```
Sales_Intelligence_Project/
├── backend/                    # FastAPI Backend
│   ├── main.py                 # API endpoints
│   └── requirements.txt        # Python dependencies
├── frontend/                   # React + TypeScript + Vite
│   ├── pages/                  # Page components
│   ├── components/             # UI components
│   ├── store/                  # State management
│   └── package.json
├── src/
│   ├── 01_eda.py               # Exploratory data analysis
│   ├── 03_forecasting.py       # Sales forecasting
│   ├── 04_rfm.py               # RFM customer segmentation
│   ├── 05_recommendation.py    # Product recommendations
│   ├── 06_sentiment.py         # Customer Feedback
│   ├── pipeline_controller.py  # Pipeline orchestration
│   └── ml_lifecycle/           # ML model management
├── data/                       # Uploaded datasets
├── output/                     # Generated reports
├── tests/                      # Unit tests
└── README.md                   # This file
```

### Tenant storage layout

Analytics and uploads are stored under tenant folders instead of shared CSV outputs:

```
data/
   company_<id>/
      branch_<id>/
         uploads/
         outputs/
         forecasts/
         segmentation/
         sentiment/
         recommendations/
```

Company admins can switch branches in the UI. Branch admins are locked to their assigned branch, and the backend validates access from JWT claims only.

---

## Getting Started

##  Hosting (Docker) — Recommended

This repo includes a ready-to-run Docker setup that:

- Runs the **FastAPI backend** on port **8001**
- Serves the **frontend** on port **3000**
- Proxies frontend requests from **`/api` → backend** (so you can host behind one domain)

### Prerequisites

- Docker Desktop (Windows/macOS) or Docker Engine (Linux)

### Run (local or VPS)

From the project root:

```bash
cd Sales_Intelligence_Project
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Backend: http://localhost:8001
- API Docs: http://localhost:8001/docs

### Data persistence

`docker-compose.yml` mounts:

- `./data` → `/app/data`
- `./logs` → `/app/logs`
- `./output` → `/app/output`

So your uploads and generated outputs persist on the host.

### Full ML/NLP dependencies (optional)

By default the backend image is **lite** (faster build). To build with the full dependency set, edit `docker-compose.yml` and set:

```yaml
args:
   INSTALL_FULL: "true"
```

Note: full mode can be very large (NLP/ML libs).

### Production notes

- If you set `ENVIRONMENT=production` on the backend, you must set `JWT_SECRET_KEY` (required by the backend).
- Docker Compose now forwards the backend email settings from the host environment or `.env`, including `EMAIL_DELIVERY_MODE`, `SMTP_*`, `RESEND_*`, and `FRONTEND_BASE_URL`.
- To enable real email delivery in production with SMTP, set `ENVIRONMENT=production`, `EMAIL_DELIVERY_MODE=smtp`, valid `SMTP_*` values, and a public `FRONTEND_BASE_URL` before rebuilding the backend.
- To enable Resend instead, set `ENVIRONMENT=production`, `EMAIL_DELIVERY_MODE=resend`, `RESEND_API_KEY`, optionally `RESEND_API_BASE_URL`, and a verified sender in `SMTP_FROM_EMAIL` plus a public `FRONTEND_BASE_URL`.
- If you host the frontend separately (different domain), set backend `CORS_ORIGINS` to your frontend URL.
- The frontend container now proxies API calls through `API_UPSTREAM`. In local Docker Compose it defaults to `http://backend:8001`, but in hosted environments you should override it to the real backend URL or internal service address exposed by your platform.
- If you deploy the frontend as static files without the bundled nginx reverse proxy, set `VITE_API_BASE` at build time to your public backend URL so the app does not fall back to same-origin `/api` requests.

---

### Step 1: Start the Backend API

Open a terminal in the project root directory and run:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8001
```

Once running, the API will be available at: **http://localhost:8001**

You can explore the API documentation at: **http://localhost:8001/docs** (Swagger UI)

Do not run `uvicorn main:app` from the `frontend/` folder. The backend app lives at `backend.main:app` and should be started from the project root.

### Step 2: Start the Frontend Dashboard

Open another terminal, navigate to the frontend folder, and run:

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at: **http://localhost:5173**

### Step 3: Running Both Together (Optional)

If you want to run both the backend and frontend simultaneously, you will need two terminal windows:

**Terminal 1 - Backend:**
```bash
python -m uvicorn backend.main:app --reload --port 8001
```

**Terminal 2 - Frontend:**
```bash
cd frontend && npm run dev
```

---

## API Endpoints

Here are the available API endpoints:

| Endpoint | Description | Method |
|----------|-------------|--------|
| `/api/health` | Health check | GET |
| `/api/kpis` | Key performance indicators | GET |
| `/api/monthly-sales` | Monthly sales with forecasts | GET |
| `/api/top-products` | Best selling products | GET |
| `/api/top-cities` | Top performing cities | GET |
| `/api/sentiment` | Customer Feedback summary | GET |
| `/api/recommendations` | Product recommendation rules | GET |
| `/api/raw-data` | Raw data access | GET |
| `/api/summary` | Comprehensive summary | GET |

---

## Machine Learning Lifecycle

The project includes a complete ML lifecycle for the forecasting model. Here is how to use each script:

### Train a New Model

```bash
python src/ml_lifecycle/train_forecast.py
```

### Evaluate the Model

```bash
python src/ml_lifecycle/evaluate_forecast.py
```

### Generate Predictions

```bash
# Predict the next 6 months (default)
python src/ml_lifecycle/predict_forecast.py

# Predict the next 12 months
python src/ml_lifecycle/predict_forecast.py 12
```

### Retrain the Model

```bash
python src/ml_lifecycle/retrain_forecast.py
```

---

## Data Analysis Pipeline

The data analysis is organized into sequential phases. You can run each phase independently:

### Phase 1: Data Analysis

```bash
python src/01_eda.py
```

### Phase 2: Sales Forecasting

```bash
python src/03_forecasting.py
```

### Phase 4: RFM Customer Analysis

```bash
python src/04_rfm.py
```

### Phase 5: Product Recommendations

```bash
python src/05_recommendation.py
```

### Phase 6: Customer Feedback

```bash
python src/06_sentiment.py
```

---

## Output Files

The system generates several output files during processing:

| File | Description |
|------|-------------|
| `data/cleaned_dataset.csv` | Cleaned and processed data |
| `data/sales_forecast_future.csv` | Future sales predictions |
| `data/sentiment_results.csv` | Customer Feedback results |
| `data/product_recommendations.csv` | Product recommendation rules |
| `logs/forecast_lifecycle.log` | ML lifecycle logs |

---

## Configuration

### Environment Variables (Optional)

You can create a `.env` file in the project root to customize settings:

```env
FLASK_ENV=development
LOG_LEVEL=INFO
API_PORT=8000
FORECAST_HORIZON=6
```

---

## Testing

### Testing the Backend API

You can test the API endpoints using curl or Postman:

```bash
curl http://localhost:8001/api/health
curl http://localhost:8001/api/kpis
curl http://localhost:8001/api/monthly-sales
```

### Testing the Frontend

Make sure the React app is configured to connect to the API at:
```
http://localhost:8001
```

---

## Documentation

For more detailed information, check these resources:

- **API Documentation**: http://localhost:8001/docs (Swagger UI)
- **Frontend Guide**: [Frontend README](frontend/README.md)

---

## Key Features

Here is what this system offers:

- **Sales Overview**: Key performance indicators, monthly trends, and top product analysis
- **Intelligent Forecasting**: Linear Regression model with complete lifecycle management
- **Customer Feedback**: Customer review classification (positive, neutral, negative)
- **Product Recommendations**: Association rules (customers who buy X often buy Y)
- **Customer Segmentation**: RFM analysis for customer categorization
- **Interactive Dashboard**: Modern interface built with React and TypeScript

---

## Contributing

If you would like to contribute to this project:

1. Create a new branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Add clear comments explaining your modifications
4. Submit a pull request

---

## Support

If you run into issues or have questions, check these resources:

- API Documentation at http://localhost:8001/docs
- System logs in `logs/` folder
- Backend code in `backend/main.py`

---

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Status**: Production Ready
tst
