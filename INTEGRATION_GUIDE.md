# Integration Guide: Frontend + Backend + Python Analytics

## نموذج التكامل المعماري

```
┌─────────────────────────────────────────────────────────┐
│           React Dashboard (Frontend)                     │
│        (http://localhost:5173)                          │
│  - Interactive Charts (Recharts)                        │
│  - KPI Cards, Tables, Filters                           │
│  - Authentication & Navigation                          │
└────────────────────┬────────────────────────────────────┘
                     │ REST API Calls (CORS enabled)
                     │ Fetch data from backend
                     ▼
┌─────────────────────────────────────────────────────────┐
│        FastAPI Backend (main.py)                        │
│        (http://localhost:8000)                          │
│  - /api/kpis → Revenue, Orders, AOV                     │
│  - /api/monthly-sales → Actuals + Forecasts            │
│  - /api/top-products, /api/top-cities                   │
│  - /api/sentiment → Positive/Neutral/Negative counts    │
│  - /api/recommendations → Association rules             │
└────────────────────┬────────────────────────────────────┘
                     │ Reads from data directory
                     │ Uses trained ML models
                     ▼
┌─────────────────────────────────────────────────────────┐
│          Python ML Lifecycle (src/ml_lifecycle/)         │
│  - train_forecast.py → Trains Linear Regression         │
│  - evaluate_forecast.py → Evaluates model               │
│  - predict_forecast.py → Generates 6-month forecast     │
│  - retrain_forecast.py → Retrains with new data         │
└────────────────────┬────────────────────────────────────┘
                     │ Outputs:
                     ├─ sales_forecast_model.pkl
                     ├─ sales_forecast_future.csv
                     ├─ sentiment_results.csv
                     └─ product_recommendations.csv
```

---

## 🔧 خطوات التثبيت والتكامل

### Step 1: نسخ مجلد frontend

انسخ داشبورد React إلى مجلد `frontend/`:

```bash
# من الجذر
cp -r ../dashboard/* ./frontend/
```

أو يدوياً:
1. انسخ جميع ملفات React إلى `frontend/`
2. تأكد من وجود `package.json` و`tsconfig.json`

### Step 2: تثبيت مكتبات Backend

```bash
# قم بتثبيت جميع متطلبات API
pip install -r backend/requirements.txt
```

### Step 3: تثبيت مكتبات Frontend

```bash
cd frontend
npm install
```

### Step 4: التحقق من البيانات

تأكد من وجود:
- `data/cleaned_dataset.csv`
- `data/sales_forecast_future.csv` (من predict_forecast.py)
- `data/sentiment_results.csv` (من 06_sentiment.py)
- `data/product_recommendations.csv` (من 05_recommendation.py)

إذا لم تكن موجودة، قم بتشغيل سكريبتات التحليل:

```bash
python src/06_sentiment.py
python src/ml_lifecycle/predict_forecast.py
```

### Step 5: تدريب النموذج (اختياري)

```bash
python src/ml_lifecycle/train_forecast.py
```

---

## 🚀 التشغيل

### تشغيل Backend و Frontend معاً

**Terminal 1 - Backend:**
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**النتيجة:**
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

---

## 🔌 التحقق من الاتصال

### اختبار API من Terminal

```bash
# فحص الصحة
curl http://localhost:8000/api/health

# الحصول على KPIs
curl http://localhost:8000/api/kpis

# الحصول على المبيعات الشهرية
curl http://localhost:8000/api/monthly-sales

# الحصول على أفضل المنتجات
curl http://localhost:8000/api/top-products?limit=5
```

### اختبار من React

تأكد من أن React dashboard:
1. يتصل بـ `http://localhost:8000`
2. يعرض البيانات بنجاح في الجداول والرسوم البيانية
3. يتعامل مع الأخطاء بشكل صحيح

---

## 📝 ملفات التكوين الرئيسية

### `backend/main.py`
- FastAPI app مع CORS تفعيل
- 9 endpoints لتقديم البيانات
- تحميل البيانات عند بدء التطبيق

### `frontend/App.tsx`
- React Router تنقل بين الصفحات
- Authentication Context
- Data Context للحالة العام

### `frontend/package.json`
- Vite للتطوير السريع
- React 19 + TypeScript
- Recharts للرسوم البيانية
- Lucide React للأيقونات

---

## 🎯 الإجراءات التالية

### في Backend (main.py)

اختياري: أضف endpoints إضافية:

```python
@app.get("/api/custom-metric")
def get_custom_metric():
    # منطق مخصص
    return {...}
```

### في Frontend

اختياري: أضف صفحات جديدة:

```tsx
// pages/NewPage.tsx
export const NewPage = () => {
  const [data, setData] = useState([]);
  
  useEffect(() => {
    fetch('http://localhost:8000/api/custom-metric')
      .then(r => r.json())
      .then(setData);
  }, []);
  
  return <div>{/* عرض البيانات */}</div>;
};
```

---

## 🔄 Workflow متكامل

1. **جمع البيانات**: `01_eda.py`
2. **تنظيف البيانات**: `02_cleaning_features.py`
3. **تدريب النموذج**: `src/ml_lifecycle/train_forecast.py`
4. **توليد التنبؤات**: `src/ml_lifecycle/predict_forecast.py`
5. **تحليل المشاعر**: `06_sentiment.py`
6. **التوصيات**: `05_recommendation.py`
7. **عرض في Dashboard**: Backend API ← Frontend React

---

## 🐛 استكشاف الأخطاء

### API لا يستجيب

```bash
# تحقق من البوابة
lsof -i :8000

# إعادة بدء
python -m uvicorn backend.main:app --reload --port 8000
```

### React لا يتصل بـ API

- تحقق من CORS في `backend/main.py`
- تأكد من `allow_origins=["http://localhost:5173", ...]`
- افتح console في المتصفح (F12) وابحث عن CORS errors

### بيانات ناقصة

- تحقق من `logs/api.log`
- تأكد من أن CSV files موجودة في `data/`

---

## 📚 إعادة المراجع

- [ML_LIFECYCLE.md](../ML_LIFECYCLE.md) - دورة حياة النموذج
- [README.md](../README.md) - نظرة عامة المشروع
- [FastAPI Docs](http://localhost:8000/docs) - توثيق API
- [Recharts Docs](https://recharts.org) - مكتبة الرسوم البيانية

---

**Version**: 1.0  
**Last Updated**: January 23, 2026
