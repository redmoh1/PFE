# Intelligent Sales Analytics & Forecasting System

##  نظرة عامة

نظام متكامل لتحليل المبيعات والتنبؤ الذكي يجمع بين:
- **Python Backend**: معالجة البيانات، التنبؤ بالمبيعات، تحليل المشاعر، التوصيات
- **React Frontend**: لوحة تحكم تفاعلية حديثة مع تصور بيانات احترافي
- **Machine Learning**: نموذج Linear Regression مع دورة حياة كاملة (train/eval/predict/retrain)

---

##  المتطلبات

### Python 3.8+
```bash
# تثبيت مكتبات Python (Python environment)
pip install -r requirements.txt
```

### Node.js 18+
```bash
# تثبيت مكتبات JavaScript (مجلد frontend)
cd frontend
npm install
```

---

## هيكل المشروع

```
Sales_Intelligence_Project/
├── backend/                    # FastAPI Backend
│   ├── main.py                # API endpoints
│   └── requirements.txt        # مكتبات Python
├── frontend/                   # React + TypeScript + Vite
│   ├── src/
│   ├── package.json
│   └── ...
├── src/
│   ├── 01_eda.py              # تحليل استكشافي
│   ├── 02_cleaning_features.py # تنظيف البيانات
│   ├── 03_forecasting.py       # التنبؤ الأساسي
│   ├── 04_rfm.py               # تحليل RFM
│   ├── 05_recommendation.py    # توصيات المنتجات
│   ├── 06_sentiment.py         # تحليل المشاعر
│   ├── 07_dashboard.py         # لوحة التحكم
│   └── ml_lifecycle/
│       ├── train_forecast.py   # تدريب النموذج
│       ├── evaluate_forecast.py # تقييم النموذج
│       ├── predict_forecast.py # توليد التنبؤات
│       ├── retrain_forecast.py # إعادة تدريب
│       └── model_registry/
├── data/                       # بيانات المشروع
├── logs/                       # ملفات السجل
├── ML_LIFECYCLE.md             # توثيق دورة حياة ML
└── README.md                   # هذا الملف
```

---

##  التشغيل السريع

### 1️ تشغيل Backend API

```bash
# من مجلد المشروع الرئيسي
python -m pip install -r backend/requirements.txt

# تشغيل API
python -m uvicorn backend.main:app --reload --port 8000
```

API سيكون متاح على: **http://localhost:8000**

Documentation: **http://localhost:8000/docs** (Swagger)

### 2️ تشغيل Frontend Dashboard

```bash
# من مجلد frontend
cd frontend
npm install  # إذا لم تقم بذلك بعد
npm run dev
```

Dashboard سيكون متاح على: **http://localhost:5173**

### 3️ تشغيل كلا الجزأين معاً (اختياري)

**Terminal 1 - Backend:**
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend && npm run dev
```

---

## 📊 API Endpoints

| Endpoint | الوصف | الأسلوب |
|----------|-------|--------|
| `/api/health` | فحص الصحة | GET |
| `/api/kpis` | مؤشرات الأداء الرئيسية | GET |
| `/api/monthly-sales` | المبيعات الشهرية + التنبؤات | GET |
| `/api/top-products` | أفضل المنتجات | GET |
| `/api/top-cities` | أفضل المدن | GET |
| `/api/sentiment` | ملخص تحليل المشاعر | GET |
| `/api/recommendations` | قواعد التوصيات | GET |
| `/api/raw-data` | البيانات الخام | GET |
| `/api/summary` | ملخص شامل | GET |

---

## 🤖 ML Lifecycle Scripts

### تدريب نموذج جديد
```bash
python src/ml_lifecycle/train_forecast.py
```

### تقييم النموذج
```bash
python src/ml_lifecycle/evaluate_forecast.py
```

### توليد التنبؤات
```bash
# التنبؤ للشهور الـ 6 القادمة (افتراضي)
python src/ml_lifecycle/predict_forecast.py

# التنبؤ للشهور الـ 12 القادمة
python src/ml_lifecycle/predict_forecast.py 12
```

### إعادة تدريب النموذج
```bash
python src/ml_lifecycle/retrain_forecast.py
```

---

##  مراحل تحليل البيانات

### Phase 1: تحليل استكشافي (EDA)
```bash
python src/01_eda.py
```

### Phase 2: تنظيف وهندسة الميزات
```bash
python src/02_cleaning_features.py
```

### Phase 3: التنبؤ بالمبيعات
```bash
python src/03_forecasting.py
```

### Phase 4: تحليل RFM
```bash
python src/04_rfm.py
```

### Phase 5: توصيات المنتجات
```bash
python src/05_recommendation.py
```

### Phase 6: تحليل المشاعر
```bash
python src/06_sentiment.py
```

### Phase 7: لوحة التحكم
```bash
python src/07_dashboard.py
```

---

## ملفات الإخراج الرئيسية

| الملف | الوصف |
|------|-------|
| `data/cleaned_dataset.csv` | البيانات المنظفة والمجهزة |
| `data/sales_forecast_future.csv` | التنبؤات المستقبلية |
| `data/sentiment_results.csv` | نتائج تحليل المشاعر |
| `data/product_recommendations.csv` | قواعد التوصيات |
| `logs/forecast_lifecycle.log` | سجلات دورة حياة ML |

---

##  التكوين والإعدادات

### متغيرات البيئة (اختياري)

أنشئ ملف `.env` في المجلد الرئيسي:

```env
FLASK_ENV=development
LOG_LEVEL=INFO
API_PORT=8000
FORECAST_HORIZON=6
```

---

##  الاختبار

### اختبار Backend API

```bash
# استخدم curl أو Postman
curl http://localhost:8000/api/health
curl http://localhost:8000/api/kpis
curl http://localhost:8000/api/monthly-sales
```

### اختبار Frontend

تأكد من أن الـ React app يتصل بـ API على:
```
http://localhost:8000
```

---

## المراجع والتوثيق

- **ML Lifecycle**: اطلع على [ML_LIFECYCLE.md](ML_LIFECYCLE.md)
- **FastAPI Docs**: http://localhost:8000/docs (Swagger UI)
- **React Best Practices**: [Frontend README](frontend/README.md)

---

##  الميزات الرئيسية

**تحليل المبيعات**: مؤشرات أداء رئيسية، اتجاهات شهرية، أفضل المنتجات  
**التنبؤ الذكي**: Linear Regression مع دورة حياة كاملة  
**تحليل المشاعر**: تصنيف آراء العملاء (إيجابي/محايد/سلبي)  
**التوصيات**: قواعس association (الشراء X → التوصية بـ Y)  
**التقسيم**: تحليل RFM للعملاء  
**لوحة تحكم تفاعلية**: واجهة حديثة مع React + TypeScript  

 
**آخر تحديث**: يناير 2026  
**الحالة**: ✅ جاهز للإنتاج
