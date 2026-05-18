# Graduation Project - Complete Information File
# ملف معلومات مشروع التخرج الكامل

---

## SECTION 1: GENERAL INFORMATION / معلومات عامة

| Field | Details |
|-------|---------|
| **Project Title (EN)** | Intelligent Sales Overview and Forecasting System |
| **Project Title (AR)** | نظام ذكي لتحليل وتنبؤ المبيعات |
| **University** | University of M'sila (جامعة المسيلة) |
| **Faculty** | Faculty of Mathematics and Computer Science (كلية الرياضيات والإعلام الآلي) |
| **Department** | Computer Science (قسم الإعلام الآلي) |
| **Level** | Licence (L3) - ليسانس |
| **Academic Year** | 2025/2026 |
| **Supervisor** | Cherait Hanan |
| **Team Members** | Sailaa Mohammed Radhwen |
| **Thesis Language** | English |
| **Development Duration** | 6 months |
| **Application Type** | Web-based SaaS Platform (Multi-Tenant) |
| **Target Market** | Small and Medium Enterprises (SMEs) in Algeria |

---

## SECTION 2: PROBLEM & SOLUTION / المشكلة والحل

### 2.1 Problem Statement (Problématique)

Small and medium-sized enterprises (SMEs) in Algeria face significant challenges in data-driven decision making:

1. **Lack of Advanced Analytics Tools**: Most SMEs cannot afford enterprise solutions like Power BI, Tableau, or Salesforce Analytics (high licensing costs, complex setup).
2. **Manual Decision Making**: Sales decisions are based on intuition rather than data analysis, leading to missed opportunities and inefficient resource allocation.
3. **No Sales Forecasting**: Businesses cannot predict future demand, resulting in inventory problems (overstocking or stockouts).
4. **Poor Customer Understanding**: No systematic approach to customer segmentation, lifetime value analysis, or sentiment tracking.
5. **Fragmented Data**: Sales data, customer data, and reviews are scattered across spreadsheets with no unified view.

### 2.2 Proposed Solution

An integrated, affordable, cloud-based Sales Intelligence Platform that provides:

- **Automated Sales Forecasting** using Prophet time-series algorithm
- **Customer Segmentation** via RFM (Recency, Frequency, Monetary) analysis
- **Customer Lifetime Value (CLV)** calculation for strategic decision making
- **Product Recommendations** using Market Basket Analysis (Apriori algorithm)
- **Sentiment Analysis** supporting both English (TextBlob) and Arabic (AraBERT)
- **Multi-tenant SaaS Architecture** enabling multiple companies to use the system with data isolation
- **Interactive Dashboard** for real-time visualization and monitoring

### 2.3 Why This Project is Important

| Aspect | Justification |
|--------|---------------|
| **Economic** | Reduces cost of analytics for SMEs (no expensive licenses) |
| **Technical** | Combines multiple ML techniques in one integrated platform |
| **Local Relevance** | Designed for MENA/Algeria market with Arabic language support |
| **Academic** | Demonstrates full-stack development + Machine Learning integration |
| **Scalability** | Multi-tenant architecture allows serving multiple businesses |

### 2.4 Differentiation from Existing Solutions

| Feature | Power BI / Tableau | Zoho Analytics | **Our System** |
|---------|-------------------|----------------|----------------|
| Price | Expensive licenses | Monthly fees | Affordable SaaS |
| ML Forecasting | Limited/Manual | Basic | Prophet + Auto pipeline |
| Customer Segmentation | Manual | Basic | Automated RFM + CLV |
| Arabic Sentiment | ❌ | ❌ | ✅ AraBERT |
| Multi-tenant | ❌ | ✅ | ✅ Full isolation |
| Product Recommendations | ❌ | ❌ | ✅ Apriori |
| All-in-One | ❌ | Partial | ✅ Complete pipeline |
| Open Source Core | ❌ | ❌ | ✅ |

---

## SECTION 3: TECHNICAL ASPECTS / الجوانب التقنية

### 3.1 Technology Stack

#### Backend
| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11 | Core programming language |
| FastAPI | 0.109.x | Web framework (REST API) |
| SQLAlchemy | 2.0.x | ORM (Object-Relational Mapping) |
| SQLite | Built-in | Database engine |
| Uvicorn | 0.27.x | ASGI server |
| Pydantic | 2.5.x | Data validation |

#### Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 19.x | UI framework |
| TypeScript | 5.8.x | Type-safe JavaScript |
| Vite | 6.2.x | Build tool & dev server |
| Tailwind CSS | 3.4.x | Utility-first CSS framework |
| Recharts | 3.7.x | Data visualization charts |
| Lucide React | 0.563.x | Icon library |

#### Machine Learning
| Technology | Version | Purpose |
|-----------|---------|---------|
| Prophet | 1.1.x | Time-series forecasting |
| scikit-learn | 1.3.x | ML utilities (Linear Regression, metrics) |
| TextBlob | 0.17.x | English sentiment analysis |
| Transformers (HuggingFace) | 4.36.x | Arabic NLP (AraBERT) |
| PyTorch | 2.1.x | Deep learning backend for Transformers |
| mlxtend | 0.23.x | Apriori algorithm (Market Basket) |
| pandas | 2.0.x | Data manipulation |
| NumPy | 1.23.x | Numerical computing |
| Matplotlib/Seaborn | 3.8.x / 0.13.x | Visualization |

#### Security & Infrastructure
| Technology | Purpose |
|-----------|---------|
| JWT (python-jose) | Token-based authentication |
| bcrypt (passlib) | Password hashing |
| SlowAPI | Rate limiting |
| Docker + Docker Compose | Containerization & deployment |
| Nginx | Reverse proxy (production) |

### 3.2 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│              React + TypeScript + Tailwind CSS               │
│          (SPA with interactive charts & dashboards)          │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/REST API (JSON)
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│                  FastAPI Backend (Python)                    │
│    ┌─────────────┐  ┌──────────┐  ┌───────────────────┐    │
│    │ Auth (JWT)  │  │  Routes  │  │ Pipeline Control  │    │
│    │ RBAC System │  │  (REST)  │  │   (Orchestrator)  │    │
│    └─────────────┘  └──────────┘  └───────────────────┘    │
└────────────────────────────┬────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
┌──────────────────┐ ┌─────────────┐ ┌──────────────────────┐
│   ML PIPELINE    │ │  DATABASE   │ │  TENANT FILE SYSTEM  │
│                  │ │  (SQLite)   │ │                      │
│ • EDA            │ │             │ │ data/company_X/      │
│ • Cleaning       │ │ • Users     │ │   branch_Y/          │
│ • Forecasting    │ │ • Companies │ │     uploads/         │
│ • RFM Segment.   │ │ • Forecasts │ │     outputs/         │
│ • Recommendations│ │ • RFM Cache │ │     forecasts/       │
│ • Sentiment      │ │ • Sentiment │ │     segmentation/    │
│ • CLV            │ │ • Logs      │ │     sentiment/       │
└──────────────────┘ └─────────────┘ └──────────────────────┘
```

### 3.3 Architecture Pattern

- **Three-Tier Architecture** (Presentation → Application → Data)
- **Multi-Tenant SaaS** with company-level data isolation
- **Branch Isolation** within each company
- **Pipeline Pattern** for ML orchestration (sequential processing)
- **RESTful API Design** for frontend-backend communication
- **JWT-based Stateless Authentication**

### 3.4 API Endpoints (Main)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | User authentication |
| POST | `/api/auth/register` | User registration |
| GET | `/api/kpis` | Key Performance Indicators |
| GET | `/api/sales` | Sales data |
| GET | `/api/forecasting` | Sales predictions |
| GET | `/api/rfm` | Customer segmentation |
| GET | `/api/recommendations` | Product recommendations |
| GET | `/api/sentiment` | Sentiment analysis results |
| POST | `/api/upload` | Data file upload |
| GET | `/api/alerts` | System alerts |
| GET | `/api/notifications` | User notifications |
| GET | `/api/inventory` | Inventory management |

---

## SECTION 4: SYSTEM ANALYSIS / تحليل النظام

### 4.1 Actors (Diagram Scope)

| Actor | Type | Responsibilities |
|-------|------|------------------|
| Admin | Human actor | Manages users, branches, settings, uploads, and analytics access |
| BranchManager | Human actor | Uploads branch data and monitors branch-level analytics |
| System | Automated actor | Validates data, runs analytics pipelines, and generates alerts/notifications |

### 4.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | User authentication (login/register) with JWT | High |
| FR-02 | Role-based access control (RBAC) | High |
| FR-03 | Upload sales/customer/review CSV data | High |
| FR-04 | Automated ML pipeline execution on data upload | High |
| FR-05 | Sales forecasting with Prophet (60 months ahead) | High |
| FR-06 | Customer segmentation via RFM analysis | High |
| FR-07 | Product recommendations via Market Basket Analysis | Medium |
| FR-08 | Sentiment analysis (English + Arabic) | Medium |
| FR-09 | Customer Lifetime Value (CLV) calculation | Medium |
| FR-10 | Interactive dashboard with KPI visualization | High |
| FR-11 | Multi-company (tenant) data isolation | High |
| FR-12 | Branch-level data separation | Medium |
| FR-13 | Alert generation for inventory/performance anomalies | Medium |
| FR-14 | Notification system for users | Low |
| FR-15 | Data export (CSV/JSON) | Low |

### 4.3 Non-Functional Requirements

| ID | Requirement | Metric |
|----|-------------|--------|
| NFR-01 | **Performance**: API response time | < 2 seconds for dashboard |
| NFR-02 | **Scalability**: Support multiple tenants | Multi-tenant architecture |
| NFR-03 | **Security**: Password hashing | bcrypt with salt |
| NFR-04 | **Security**: Token expiration | 24-hour JWT tokens |
| NFR-05 | **Security**: Rate limiting | SlowAPI protection |
| NFR-06 | **Availability**: Containerized deployment | Docker Compose |
| NFR-07 | **Maintainability**: Modular code | Separated modules/layers |
| NFR-08 | **Portability**: Database agnostic | SQLAlchemy ORM |
| NFR-09 | **Usability**: Responsive design | Tailwind CSS |
| NFR-10 | **Reliability**: Graceful error handling | Try/catch + logging |

### 4.4 Use Cases (Summary)

#### UC-01: User Authentication
- **Actor**: Admin, BranchManager
- **Precondition**: Actor has a registered account
- **Flow**: Enter credentials → Validate → Issue JWT → Redirect to dashboard
- **Postcondition**: User has valid session token

#### UC-02: Upload Data
- **Actor**: Admin, BranchManager
- **Precondition**: Authenticated, has write permissions
- **Flow**: Select CSV file → Upload → Validate schema → Store → Trigger pipeline
- **Postcondition**: Data processed, analytics generated

#### UC-03: View Sales Forecast
- **Actor**: Admin, BranchManager
- **Precondition**: Sales data uploaded and pipeline completed
- **Flow**: Navigate to Forecasting page → View chart → Select forecast period
- **Postcondition**: Forecast displayed with confidence intervals

#### UC-04: View Customer Segmentation
- **Actor**: Admin, BranchManager
- **Precondition**: Customer data uploaded
- **Flow**: Navigate to Segmentation → View RFM table → Filter by segment
- **Postcondition**: Customer segments displayed

#### UC-05: View Product Recommendations
- **Actor**: Admin, BranchManager
- **Precondition**: Sales data with product info uploaded
- **Flow**: Navigate to Recommendations → View association rules → Sort by Lift
- **Postcondition**: Product pairs displayed with support/confidence/lift

#### UC-06: View Sentiment Analysis
- **Actor**: Admin, BranchManager
- **Precondition**: Customer reviews uploaded
- **Flow**: Navigate to Sentiment → View positive/negative/neutral distribution
- **Postcondition**: Sentiment results displayed

#### UC-07: Manage Users (Admin)
- **Actor**: Admin
- **Precondition**: Admin privileges
- **Flow**: Create/Edit/Delete users → Assign roles → Assign branches
- **Postcondition**: User accounts managed

#### UC-08: Automated Analytics Processing
- **Actor**: System
- **Precondition**: A valid upload has been stored
- **Flow**: Validate schema → Trigger pipeline → Refresh analytics outputs → Generate alerts/notifications
- **Postcondition**: Updated analytics are available for Admin and BranchManager

---

## SECTION 5: DATABASE DESIGN / تصميم قاعدة البيانات

### 5.1 Database Technology
- **Engine**: SQLite (development) / PostgreSQL (production-ready via SQLAlchemy)
- **ORM**: SQLAlchemy 2.0
- **Migration Tool**: Alembic

### 5.2 Tables (Entities)

#### Table: `users`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, Auto-increment | User ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Login email |
| full_name | VARCHAR(255) | NOT NULL | Display name |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt hash |
| role | ENUM | NOT NULL | UserRole value |
| company_id | INTEGER | FK → companies.id | Tenant association |
| branch_id | INTEGER | FK → branches.id, NULLABLE | Branch assignment |
| is_active | BOOLEAN | DEFAULT TRUE | Account status |
| created_at | DATETIME | NOT NULL | Registration date |
| last_login | DATETIME | NULLABLE | Last login timestamp |

#### Table: `companies`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Company ID |
| name | VARCHAR(255) | UNIQUE, NOT NULL | Company name |
| slug | VARCHAR(255) | UNIQUE, NOT NULL | URL-safe identifier |
| description | TEXT | NULLABLE | Company description |
| data_directory | VARCHAR(512) | NOT NULL | Data folder path |
| is_active | BOOLEAN | DEFAULT TRUE | Active status |
| created_at | DATETIME | NOT NULL | Creation date |

#### Table: `branches`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Branch ID |
| company_id | INTEGER | FK → companies.id | Parent company |
| name | VARCHAR(255) | NOT NULL | Branch name |
| city | VARCHAR(255) | NOT NULL | Branch city |
| phone | VARCHAR(50) | NULLABLE | Contact phone |
| manager_id | INTEGER | FK → users.id | Branch manager |
| is_active | BOOLEAN | DEFAULT TRUE | Active status |
| created_at | DATETIME | NOT NULL | Creation date |

#### Table: `forecast_results`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Result ID |
| company_id | INTEGER | FK → companies.id | Tenant |
| branch_id | INTEGER | FK, NULLABLE | Branch scope |
| model_type | VARCHAR(50) | NOT NULL | "Prophet" or "LinearRegression" |
| model_version | INTEGER | NOT NULL | Version number |
| forecast_periods | INTEGER | NOT NULL | Months forecasted |
| mae | FLOAT | NULLABLE | Mean Absolute Error |
| rmse | FLOAT | NULLABLE | Root Mean Square Error |
| mape | FLOAT | NULLABLE | Mean Absolute % Error |
| r2 | FLOAT | NULLABLE | R-squared score |
| forecast_data | JSON | NOT NULL | Predictions array |
| trend_data | JSON | NULLABLE | Trend component |
| seasonality_data | JSON | NULLABLE | Seasonal component |
| created_at | DATETIME | NOT NULL | Generation date |

#### Table: `rfm_results`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Result ID |
| company_id | INTEGER | FK → companies.id | Tenant |
| branch_id | INTEGER | FK, NULLABLE | Branch scope |
| customer_id | VARCHAR(255) | NOT NULL | Customer identifier |
| customer_name | VARCHAR(255) | NULLABLE | Customer name |
| recency | INTEGER | NOT NULL | Days since last purchase |
| frequency | INTEGER | NOT NULL | Total purchases |
| monetary | FLOAT | NOT NULL | Total spending |
| r_score | INTEGER | NOT NULL | Recency score (1-5) |
| f_score | INTEGER | NOT NULL | Frequency score (1-5) |
| m_score | INTEGER | NOT NULL | Monetary score (1-5) |
| rfm_segment | VARCHAR(50) | NOT NULL | Segment label |
| created_at | DATETIME | NOT NULL | Calculation date |

#### Table: `sentiment_results`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Result ID |
| company_id | INTEGER | FK → companies.id | Tenant |
| branch_id | INTEGER | FK, NULLABLE | Branch scope |
| review_id | VARCHAR(255) | NULLABLE | Review identifier |
| review_text | TEXT | NOT NULL | Original review text |
| review_date | DATETIME | NULLABLE | Review date |
| sentiment | VARCHAR(20) | NOT NULL | Positive/Negative/Neutral |
| confidence | FLOAT | NOT NULL | Prediction confidence |
| polarity | FLOAT | NOT NULL | -1 to +1 |
| analysis_method | VARCHAR(50) | NOT NULL | "arabic_bert" or "textblob" |
| product_id | VARCHAR(255) | NULLABLE | Associated product |
| rating | INTEGER | NULLABLE | Star rating |
| created_at | DATETIME | NOT NULL | Analysis date |

#### Table: `model_performance_logs`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Log ID |
| company_id | INTEGER | FK → companies.id | Tenant |
| branch_id | INTEGER | FK, NULLABLE | Branch scope |
| model_type | VARCHAR(50) | NOT NULL | Model name |
| model_version | INTEGER | NOT NULL | Version |
| mae | FLOAT | NOT NULL | MAE metric |
| rmse | FLOAT | NOT NULL | RMSE metric |
| mape | FLOAT | NULLABLE | MAPE metric |
| training_samples | INTEGER | NOT NULL | Training set size |
| test_samples | INTEGER | NOT NULL | Test set size |
| feature_stats | JSON | NULLABLE | Feature statistics |
| performance_degraded | BOOLEAN | DEFAULT FALSE | Degradation flag |
| retrain_recommended | BOOLEAN | DEFAULT FALSE | Retrain flag |
| logged_at | DATETIME | NOT NULL | Log timestamp |

#### Table: `notifications`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Notification ID |
| company_id | INTEGER | FK, NULLABLE | Tenant |
| branch_id | INTEGER | FK, NULLABLE | Branch scope |
| product_name | VARCHAR(255) | NULLABLE | Related product |
| message | TEXT | NOT NULL | Notification text |
| type | ENUM | NOT NULL | ALERT/WARNING/INFO |
| is_read | BOOLEAN | DEFAULT FALSE | Read status |
| created_at | DATETIME | NOT NULL | Creation time |

### 5.3 Relationships

```
Companies (1) ────── (N) Users
Companies (1) ────── (N) Branches
Companies (1) ────── (N) ForecastResults
Companies (1) ────── (N) RFMResults
Companies (1) ────── (N) SentimentResults
Companies (1) ────── (N) ModelPerformanceLogs
Branches  (1) ────── (N) Users
Branches  (1) ────── (0..N) ForecastResults
Users     (1) ────── (0..1) Branch (as manager)
```

---

## SECTION 6: DEVELOPMENT / التطوير

### 6.1 System Pages (Frontend)

| Page | Route | Description |
|------|-------|-------------|
| Authentication | `/auth` | Login/Register forms |
| Dashboard | `/` | Main KPI overview with charts |
| Sales Analytics | `/sales` | Detailed sales data visualization |
| Forecasting | `/forecasting` | Prophet forecast chart + metrics |
| Segmentation | `/segmentation` | RFM customer segments |
| Recommendations | `/recommendations` | Product association rules |
| Sentiment | `/sentiment` | Review sentiment distribution |
| Inventory | `/inventory` | Stock level management |
| Data Upload | `/upload` | CSV file upload interface |
| Settings | `/settings` | User/company configuration |

### 6.2 Key Features

1. **Automated ML Pipeline**: Upload data → Pipeline auto-executes all analyses
2. **Schema Resolution**: Smart column name detection (works with any CSV headers)
3. **Branch Selector**: Switch between branches in the UI (Admin feature)
4. **Real-time Alerts**: Automatic notifications for anomalies
5. **Model Lifecycle**: Train → Evaluate → Predict → Retrain cycle
6. **Data Quality Checks**: Validation before processing

### 6.3 ML Pipeline Workflow

```
User uploads CSV files (sales.csv, customers.csv, reviews.csv)
         │
         ↓
┌─── Pipeline Controller (Orchestrator) ───┐
│                                          │
│  Step 1: EDA (Exploratory Data Analysis) │
│          ↓                               │
│  Step 2: Data Cleaning & Features        │
│          ↓                               │
│  Step 3: Sales Forecasting (Prophet)     │
│          ↓                               │
│  Step 4: RFM Customer Segmentation      │
│          ↓                               │
│  Step 5: Product Recommendations         │
│          ↓                               │
│  Step 6: Sentiment Analysis              │
│          ↓                               │
│  Step 7: CLV Calculation                 │
│                                          │
└──────────────────────────────────────────┘
         │
         ↓
Results stored in DB + displayed on Dashboard
```

### 6.4 Algorithms Detail

#### A. Sales Forecasting (Prophet)
- **Algorithm**: Facebook Prophet (Additive Decomposition)
- **Formula**: $y(t) = g(t) + s(t) + h(t) + \epsilon_t$
  - $g(t)$ = trend (growth over time)
  - $s(t)$ = seasonality (weekly, yearly patterns)
  - $h(t)$ = holiday effects
  - $\epsilon_t$ = error term
- **Input**: Monthly aggregated sales (OrderDate, TotalPrice)
- **Output**: 60-month forecast with confidence intervals
- **Metrics**: MAE, RMSE, MAPE, R²
- **Advantage over Linear Regression**: Handles seasonality and missing data

#### B. Customer Segmentation (RFM)
- **Method**: Quintile-based scoring
- **Metrics per customer**:
  - Recency = days since last purchase
  - Frequency = total number of orders
  - Monetary = total amount spent
- **Scoring**: Each metric scored 1-5 (quintiles)
- **Segments**: VIP (12-15), Loyal (9-11), Potential (6-8), At Risk (3-5)

#### C. Product Recommendations (Apriori)
- **Algorithm**: Apriori Association Rule Mining
- **Parameters**: min_support=1%, min_confidence=10%, min_lift=1.0
- **Output**: Rules like {Product A} → {Product B} with support, confidence, lift
- **Library**: mlxtend

#### D. Sentiment Analysis
- **English**: TextBlob (polarity: -1 to +1, subjectivity: 0 to 1)
- **Arabic**: AraBERT via HuggingFace Transformers (`aubmindlab/bert-base-arabertv02-twitter`)
- **Output**: Positive / Negative / Neutral + confidence score

#### E. Customer Lifetime Value (CLV)
- **Methods implemented**:
  1. Historical CLV = Sum of all past revenue
  2. Average CLV = Avg Order Value × Frequency × Lifespan
  3. Predictive CLV (BG/NBD model)
- **Segmentation**: Platinum / Gold / Silver / Bronze tiers

---

## SECTION 7: TESTING / الاختبارات

### 7.1 Types of Tests Implemented

| Type | Tool | File | Coverage |
|------|------|------|----------|
| Unit Tests (API) | pytest + FastAPI TestClient | `tests/test_api.py` | API endpoints |
| Unit Tests (ML) | pytest | `tests/test_ml_scripts.py` | ML pipeline scripts |
| Integration Tests | PowerShell script | `tests/smoke_branch_runtime.ps1` | Branch isolation |
| Configuration Tests | conftest.py | `tests/conftest.py` | Test fixtures |

### 7.2 Test Scenarios

| Scenario | Expected Result |
|----------|----------------|
| Root endpoint returns API info | Status 200, contains version |
| Health check works | Status 200, status = healthy |
| KPIs endpoint responds | Status 200 or 503 (no data) |
| Authentication with valid credentials | JWT token returned |
| Authentication with invalid credentials | Status 401 |
| File upload with valid CSV | Status 200, pipeline triggered |
| Access restricted endpoint without token | Status 401 |
| Branch admin cannot access other branches | Status 403 |

### 7.3 Model Evaluation Metrics

| Model | Metric | Description |
|-------|--------|-------------|
| Prophet Forecast | MAE | Mean Absolute Error |
| Prophet Forecast | RMSE | Root Mean Square Error |
| Prophet Forecast | MAPE | Mean Absolute Percentage Error |
| Prophet Forecast | R² | Coefficient of Determination |
| Sentiment (AraBERT) | Confidence | Prediction probability |
| RFM | Segment Distribution | % per segment |

---

## SECTION 8: DEPLOYMENT / النشر

### 8.1 Deployment Architecture

```
┌─────────────────────────────────────────┐
│            Docker Compose               │
│                                         │
│  ┌─────────────┐    ┌───────────────┐  │
│  │  Frontend   │    │    Backend    │  │
│  │  (Nginx)    │    │  (Uvicorn)   │  │
│  │  Port 3000  │───▶│  Port 8001   │  │
│  └─────────────┘    └───────────────┘  │
│         │                    │          │
│         └──────┬─────────────┘          │
│                ↓                        │
│  ┌─────────────────────────────┐       │
│  │  Persistent Volumes         │       │
│  │  ./data  ./logs  ./output   │       │
│  └─────────────────────────────┘       │
└─────────────────────────────────────────┘
```

### 8.2 How to Run

```bash
# Development
cd Sales_Intelligence_Project
docker compose up --build

# Access:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8001
# API Docs (Swagger): http://localhost:8001/docs
```

---

## SECTION 9: CONCLUSION / الخاتمة

### 9.1 Achieved Results

1. ✅ Complete SaaS platform with multi-tenant architecture
2. ✅ Automated ML pipeline (6 analysis modules)
3. ✅ Prophet-based sales forecasting with confidence intervals
4. ✅ Arabic sentiment analysis using AraBERT
5. ✅ Customer segmentation (RFM) and CLV calculation
6. ✅ Product recommendation engine (Apriori)
7. ✅ JWT-based authentication with RBAC (5 roles)
8. ✅ Dockerized deployment ready for production
9. ✅ Interactive React dashboard with real-time charts
10. ✅ Branch-level data isolation

### 9.2 Difficulties Encountered

| Difficulty | Solution Applied |
|-----------|-----------------|
| Finding suitable test data for Algerian market | Generated synthetic data mimicking real patterns |
| Prophet installation issues on Windows | Used cmdstanpy with proper configuration |
| Arabic NLP model size and performance | Implemented fallback to TextBlob when model unavailable |
| Multi-tenant data isolation complexity | Designed tenant_paths system with strict folder separation |
| Schema variation across different CSV formats | Built dynamic schema_resolver.py |

### 9.3 Future Improvements (Perspectives)

1. **Deep Learning Forecasting**: LSTM/Transformer models for better accuracy
2. **Mobile Application**: React Native companion app
3. **Real-time Analytics**: WebSocket-based live updates
4. **AI Chatbot**: Natural language queries for analytics
5. **PostgreSQL Migration**: For production scalability
6. **Payment Integration**: Subscription management for SaaS
7. **Advanced Anomaly Detection**: Automated outlier identification
8. **Multi-language Dashboard**: Arabic/French UI translations
9. **API Marketplace**: Third-party integrations (ERP, CRM)
10. **Horizontal Scaling**: Kubernetes deployment for high availability

---

## SECTION 10: UML DIAGRAMS NEEDED / المخططات المطلوبة

### 10.1 Use Case Diagram (Elements)

**Actors**: Admin, BranchManager, System

**Use Cases**:
- Authenticate (Login/Register)
- Upload Data (CSV)
- View Dashboard (KPIs)
- View Sales Forecast
- View Customer Segmentation (RFM)
- View Product Recommendations
- View Sentiment Analysis
- Manage Users
- Manage Branches
- Manage Company Settings
- Export Reports
- View Notifications/Alerts
- Validate Uploaded Data
- Trigger Analytics Pipeline
- Generate Notifications/Alerts

**Relationships**:
- Admin, BranchManager → Authenticate
- Admin, BranchManager → Upload Data
- Admin, BranchManager → View Dashboard, View Sales Forecast, View Customer Segmentation, View Product Recommendations, View Sentiment Analysis, View Notifications/Alerts
- Admin → Manage Users, Manage Branches, Manage Company Settings, Export Reports
- System → Validate Uploaded Data, Trigger Analytics Pipeline, Generate Notifications/Alerts
- «include»: Upload Data includes Validate Uploaded Data
- «include»: Validate Uploaded Data includes Trigger Analytics Pipeline
- «extend»: View Sales Forecast extends Export Reports

### 10.2 Class Diagram (Main Classes)

```
User
├── id: int
├── email: string
├── full_name: string
├── hashed_password: string
├── role: UserRole
├── company_id: int
├── branch_id: int?
├── is_active: bool
├── verify_password(): bool
└── hash_password(): string

Company
├── id: int
├── name: string
├── slug: string
├── data_directory: string
├── is_active: bool
├── users: List[User]
├── branches: List[Branch]
└── forecasts: List[ForecastResult]

Branch
├── id: int
├── company_id: int
├── name: string
├── city: string
├── manager_id: int?
└── users: List[User]

ForecastResult
├── id: int
├── company_id: int
├── model_type: string
├── forecast_periods: int
├── mae, rmse, mape, r2: float
├── forecast_data: JSON
└── trend_data: JSON

RFMResult
├── id: int
├── customer_id: string
├── recency, frequency: int
├── monetary: float
├── r_score, f_score, m_score: int
└── rfm_segment: string

SentimentResult
├── id: int
├── review_text: string
├── sentiment: string
├── confidence: float
├── polarity: float
└── analysis_method: string
```

### 10.3 Sequence Diagram (Key Flows)

#### Flow 1: Data Upload & Pipeline Execution
```
User → Frontend: Upload CSV file
Frontend → Backend API: POST /api/upload (multipart/form-data)
Backend API → Auth Middleware: Validate JWT token
Auth Middleware → Backend API: User authenticated
Backend API → File System: Store file in tenant directory
Backend API → Pipeline Controller: Trigger pipeline
Pipeline Controller → EDA Module: Execute analysis
Pipeline Controller → Cleaning Module: Clean data
Pipeline Controller → Forecasting Module: Run Prophet
Pipeline Controller → RFM Module: Segment customers
Pipeline Controller → Recommendations: Generate rules
Pipeline Controller → Sentiment Module: Analyze reviews
Pipeline Controller → Backend API: Pipeline complete
Backend API → Database: Store results
Backend API → Frontend: Return success + results summary
Frontend → User: Display updated dashboard
```

#### Flow 2: User Authentication
```
User → Frontend: Enter email + password
Frontend → Backend API: POST /api/auth/login
Backend API → Database: Find user by email
Database → Backend API: User record
Backend API → bcrypt: Verify password hash
Backend API → JWT: Generate access token (24h)
Backend API → Frontend: Return {token, user_info}
Frontend → LocalStorage: Store JWT token
Frontend → User: Redirect to Dashboard
```

---

## SECTION 11: REFERENCES / المراجع المقترحة

### Academic References
1. Taylor, S.J. & Letham, B. (2018). "Forecasting at Scale." *The American Statistician*, 72(1), 37-45. [Prophet paper]
2. Agrawal, R. & Srikant, R. (1994). "Fast Algorithms for Mining Association Rules." *VLDB Conference*. [Apriori]
3. Hughes, A.M. (1994). "Strategic Database Marketing." [RFM Analysis]
4. Antoun, W. et al. (2020). "AraBERT: Transformer-based Model for Arabic Language Understanding." *WANLP Workshop*. [Arabic NLP]

### Technical References
5. FastAPI Documentation - https://fastapi.tiangolo.com/
6. React Documentation - https://react.dev/
7. Prophet Documentation - https://facebook.github.io/prophet/
8. SQLAlchemy Documentation - https://docs.sqlalchemy.org/
9. Docker Documentation - https://docs.docker.com/

---

## APPENDIX: PROJECT METRICS

| Metric | Value |
|--------|-------|
| Total Python files | ~25+ |
| Total TypeScript/React files | ~15+ |
| Lines of Code (Backend) | ~3000+ |
| Lines of Code (Frontend) | ~2000+ |
| Lines of Code (ML Pipeline) | ~2000+ |
| Database Tables | 7 |
| API Endpoints | 15+ |
| ML Algorithms | 5 (Prophet, RFM, Apriori, TextBlob, AraBERT) |
| User Roles | 5 |
| Frontend Pages | 10 |
| Development Duration | 6 months |
| Team Size | 1 |

---

*Document generated: May 2026*
*This file contains all information needed to write the graduation thesis (mémoire de fin d'études).*
