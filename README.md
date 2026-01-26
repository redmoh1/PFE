# Intelligent Sales Analytics and Forecasting System

## Overview

This is a complete sales intelligence platform that brings together data analytics, machine learning, and modern web technologies. The system is designed to help businesses understand their sales patterns, predict future trends, and make data-driven decisions.

The project consists of three main components:

- **Python Backend**: Handles data processing, sales forecasting, sentiment analysis, and product recommendations using FastAPI
- **React Frontend**: A modern interactive dashboard built with TypeScript and Vite for data visualization
- **Machine Learning Pipeline**: Linear Regression model with a full lifecycle including training, evaluation, prediction, and retraining capabilities

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
│   ├── 06_sentiment.py         # Sentiment analysis
│   ├── pipeline_controller.py  # Pipeline orchestration
│   └── ml_lifecycle/           # ML model management
├── data/                       # Uploaded datasets
├── output/                     # Generated reports
├── tests/                      # Unit tests
└── README.md                   # This file
```

---

## Getting Started

### Step 1: Start the Backend API

Open a terminal in the project root directory and run:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Once running, the API will be available at: **http://localhost:8000**

You can explore the API documentation at: **http://localhost:8000/docs** (Swagger UI)

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
python -m uvicorn backend.main:app --reload --port 8000
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
| `/api/sentiment` | Sentiment analysis summary | GET |
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

### Phase 6: Sentiment Analysis

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
| `data/sentiment_results.csv` | Sentiment analysis results |
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
curl http://localhost:8000/api/health
curl http://localhost:8000/api/kpis
curl http://localhost:8000/api/monthly-sales
```

### Testing the Frontend

Make sure the React app is configured to connect to the API at:
```
http://localhost:8000
```

---

## Documentation

For more detailed information, check these resources:

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Frontend Guide**: [Frontend README](frontend/README.md)

---

## Key Features

Here is what this system offers:

- **Sales Analytics**: Key performance indicators, monthly trends, and top product analysis
- **Intelligent Forecasting**: Linear Regression model with complete lifecycle management
- **Sentiment Analysis**: Customer review classification (positive, neutral, negative)
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

- API Documentation at http://localhost:8000/docs
- System logs in `logs/` folder
- Backend code in `backend/main.py`

---

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Status**: Production Ready
