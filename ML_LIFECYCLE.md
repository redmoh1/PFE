# ML Lifecycle Documentation

## Intelligent Sales Analytics & Forecasting System

---

## 1. Introduction

This document describes the end-to-end ML lifecycle for the "Intelligent Sales Analytics & Forecasting System," covering data ingestion, preparation, training, evaluation, deployment, monitoring, and retraining of a Linear Regression time-series model for monthly sales forecasting.

---

## 2. Data Ingestion

- **Sources**: Sales transactions and customer data in `data/sales.csv`, `data/customers.csv`, and consolidated training-ready `data/cleaned_dataset.csv`.
- **Storage**: Local project workspace under `data/`.
- **Access patterns**: Scripts read from `cleaned_dataset.csv` (primary source for forecasting).
- **Reliability**: Validate file presence and required columns (`OrderDate`, `TotalPrice`) before processing.

---

## 3. Data Preparation & Feature Engineering

- **Temporal parsing**: `OrderDate` is parsed to datetime with coercion and null-drop for invalid dates.
- **Aggregation**: Monthly sales totals via `pd.Grouper(freq="MS")` producing a stable calendar index.
- **Time index**: `MonthIndex` = sequential integer per month to feed the regression.
- **Quality checks**: Require ≥3 monthly periods; drop rows with missing `OrderDate` or `TotalPrice`.
- **Output**: Prepared monthly dataframe with columns `[OrderDate, TotalPrice, MonthIndex]`.

---

## 4. Model Training

- **Script**: `src/ml_lifecycle/train_forecast.py`
- **Algorithm**: Linear Regression (interpretable baseline for monthly trend)
- **Split**: Time-aware train/test split (no shuffling), default `test_size=0.2`, minimum 2 training periods
- **Metrics during training**: MAE, RMSE, R2 (R2 guarded when sample size < 2)
- **Persistence**: Model saved with joblib to `src/ml_lifecycle/model_registry/sales_forecast_model.pkl`
- **Logging**: `logs/forecast_lifecycle.log` records stages, splits, and metrics

### Training Command
```bash
python src/ml_lifecycle/train_forecast.py
```

---

## 5. Model Evaluation

- **Script**: `src/ml_lifecycle/evaluate_forecast.py`
- **Process**: Reload persisted model, rebuild monthly features, repeat temporal split identical to training
- **Metrics**: MAE, RMSE, R2 with explicit warning when test size is too small for R2
- **Output**: Metrics logged to `logs/forecast_lifecycle.log` for auditability

### Evaluation Command
```bash
python src/ml_lifecycle/evaluate_forecast.py
```

---

## 6. Model Deployment (Local)

- **Script**: `src/ml_lifecycle/predict_forecast.py`
- **Inputs**: Persisted model, latest `cleaned_dataset.csv`; CLI argument for horizon (default 6, capped at 60)
- **Features**: Extends `MonthIndex` beyond last observed month; future calendar months generated via `MonthBegin`
- **Outputs**: `data/sales_forecast_future.csv` with columns `[MonthStart, ForecastedSales]`
- **Safeguards**: Validates positive horizon, caps maximum months, summarizes forecast window and min/max values in logs

### Prediction Command
```bash
# Predict next 6 months (default)
python src/ml_lifecycle/predict_forecast.py

# Predict next 12 months
python src/ml_lifecycle/predict_forecast.py 12
```

---

## 7. Model Monitoring

- **Operational logs**: `logs/forecast_lifecycle.log` captures train/eval/predict events and metrics
- **Data drift signals** (manual checks in this baseline):
  - Monthly volume stability (count of orders per month)
  - Revenue distribution shifts (mean/variance of `TotalPrice`)
- **Performance tracking**: Re-run `evaluate_forecast.py` on a holdout or most recent window to compare MAE/RMSE over time
- **Anomaly indicators**: Sudden spikes in MAE/RMSE or sustained drop in R2 → trigger investigation/retraining

---

## 8. Retraining Strategy

- **Script**: `src/ml_lifecycle/retrain_forecast.py`
- **Simulation**: Generates small synthetic future periods using current model + controlled noise; caps horizon (default 3, max 36) to avoid runaway
- **Refresh**: Concatenate simulated months, reindex `MonthIndex`, perform temporal split, retrain Linear Regression, and overwrite registry artifact
- **Validation**: Metrics logged with small-sample warnings for R2; timestamps recorded in UTC for traceability
- **Triggering policy** (recommendation):
  - **Schedule**: periodic (e.g., monthly)
  - **Performance**: if MAE/RMSE degrades beyond threshold vs. last baseline
  - **Data freshness**: when ≥1 new month of real sales data is available

### Retraining Command
```bash
python src/ml_lifecycle/retrain_forecast.py
```

---

## 9. ML Lifecycle Diagram (text-based)

```
┌─────────────────────┐
│  Data Ingestion     │
│  - sales.csv        │
│  - customers.csv    │
│  - cleaned_dataset  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Data Preparation    │
│ - Parse OrderDate   │
│ - Drop nulls        │
│ - Aggregate monthly │
│ - Add MonthIndex    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Model Training    │
│ - Temporal split    │
│ - Fit LinearReg     │
│ - Log MAE/RMSE/R2   │
│ - Persist model     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Model Evaluation   │
│ - Reload model      │
│ - Repeat split      │
│ - Report metrics    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Model Prediction   │
│ - Reload model      │
│ - Build future X    │
│ - Save forecasts    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Monitoring       │
│ - Track logs        │
│ - MAE/RMSE trends   │
│ - Data drift checks │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Retraining       │
│ - Simulate new data │
│ - Temporal split    │
│ - Fit, evaluate     │
│ - Overwrite model   │
└─────────────────────┘
           │
           └──────────► [Cycle repeats]
```

---

## 10. File Structure

```
Sales_Intelligence_Project/
├── data/
│   ├── sales.csv
│   ├── customers.csv
│   ├── cleaned_dataset.csv
│   ├── sales_forecast_future.csv  # Output from predict
│   └── sales_forecast.csv
├── logs/
│   └── forecast_lifecycle.log     # ML lifecycle logs
├── src/
│   └── ml_lifecycle/
│       ├── train_forecast.py      # Training pipeline
│       ├── evaluate_forecast.py   # Evaluation pipeline
│       ├── predict_forecast.py    # Prediction pipeline
│       ├── retrain_forecast.py    # Retraining pipeline
│       └── model_registry/
│           └── sales_forecast_model.pkl  # Persisted model
└── ML_LIFECYCLE.md                # This document
```

---

## 11. Quick Start Guide

### Initial Setup
```bash
# 1. Train the model
python src/ml_lifecycle/train_forecast.py

# 2. Evaluate the model
python src/ml_lifecycle/evaluate_forecast.py

# 3. Generate predictions
python src/ml_lifecycle/predict_forecast.py 6
```

### Regular Operations
```bash
# Monthly: Retrain with simulated new data
python src/ml_lifecycle/retrain_forecast.py

# Weekly: Generate updated forecasts
python src/ml_lifecycle/predict_forecast.py 12

# On-demand: Check model performance
python src/ml_lifecycle/evaluate_forecast.py
```

---

## 12. Metrics Glossary

- **MAE (Mean Absolute Error)**: Average absolute difference between predicted and actual sales. Lower is better.
- **RMSE (Root Mean Squared Error)**: Square root of mean squared errors. Penalizes larger errors more than MAE. Lower is better.
- **R² (Coefficient of Determination)**: Proportion of variance explained by the model. Range [0, 1]. Higher is better. Note: undefined (nan) when sample size < 2.

---

## 13. Future Enhancements

- **Model versioning**: Implement semantic versioning for model artifacts
- **A/B testing**: Compare Linear Regression vs. ARIMA/Prophet
- **Automated retraining**: Trigger based on performance degradation thresholds
- **Feature expansion**: Add seasonal indicators, promotional events, external factors
- **Cloud deployment**: Migrate to cloud-based model serving (AWS SageMaker, Azure ML)
- **API endpoint**: Expose predictions via REST API
- **Dashboard integration**: Real-time forecast visualization in Phase 7 dashboard

---

*Document Version: 1.0*  
*Last Updated: January 23, 2026*
