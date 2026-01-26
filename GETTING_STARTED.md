# 📚 دليل شامل للمشروع - Sales Intelligence Project

## 🎯 ملخص المشروع

مشروع متكامل لتحليل المبيعات والتنبؤ الذكي يجمع بين:
- ✅ **Python Backend**: FastAPI مع معالجة بيانات متقدمة
- ✅ **React Frontend**: لوحة تحكم تفاعلية حديثة
- ✅ **Machine Learning**: نموذج Linear Regression مع دورة حياة كاملة

---

## ⚡ البدء السريع (5 دقائق)

### 1️⃣ تثبيت المتطلبات
```powershell
cd "c:\Users\DELL\Desktop\New folder\Sales_Intelligence_Project"

# Backend
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 2️⃣ تشغيل الخوادم

**Terminal 1 - Backend:**
```powershell
python -m uvicorn backend.main:app --reload --port 8000
```
✅ متاح على: http://localhost:8000
📚 Documentation: http://localhost:8000/docs

**Terminal 2 - Frontend:**
```powershell
cd frontend && npm run dev
```
✅ متاح على: http://localhost:5173

### 3️⃣ رفع البيانات
1. اذهب إلى **Data Upload** في الـ Dashboard
2. اختر ملف CSV (مثل `data/sample_sales.csv`)
3. انتظر رسالة ✅ **Pipeline Complete!**

---

## 📋 متطلبات الملفات

### الأعمدة المطلوبة (5 أعمدة):

| متطلب | الأسماء البديلة | مثال |
|-------|-----------------|------|
| **id** | `orderid`, `transactionid` | 1001 |
| **date** | `orderdate`, `order_date` | 2024-01-05 |
| **amount** | `totalprice`, `price` | 1200.00 |
| **product** | `productname`, `item` | Laptop |
| **city** | `location`, `region` | Algiers |

### ملفات نموذجية متاحة:
- ✅ `data/sales.csv` - البيانات الأساسية
- ✅ `data/sample_sales.csv` - مثال كامل (20 record)
- ✅ `data/minimal_example.csv` - مثال بسيط (10 record)
- ✅ `data/cleaned_dataset.csv` - بيانات منظفة

---

## 🏗️ هيكل المشروع

```
Sales_Intelligence_Project/
│
├── backend/
│   ├── main.py                    # FastAPI endpoints
│   └── requirements.txt
│
├── frontend/
│   ├── pages/
│   │   ├── DataUpload.tsx        # ✅ محدث
│   │   ├── Dashboard.tsx
│   │   ├── Forecasting.tsx
│   │   ├── SalesAnalytics.tsx
│   │   ├── Sentiment.tsx
│   │   └── ...
│   └── package.json
│
├── src/
│   ├── 01_eda.py                 # تحليل استكشافي
│   ├── 02_cleaning_features.py   # تنظيف البيانات
│   ├── 03_forecasting.py         # التنبؤ الأساسي
│   ├── 04_rfm.py                 # تحليل RFM
│   ├── 05_recommendation.py      # توصيات
│   ├── 06_sentiment.py           # تحليل المشاعر
│   ├── 07_dashboard.py           # تصدير البيانات
│   └── ml_lifecycle/
│       ├── train_forecast.py
│       ├── evaluate_forecast.py
│       ├── predict_forecast.py
│       └── retrain_forecast.py
│
├── data/
│   ├── sales.csv                 # ✅ محدث
│   ├── sample_sales.csv          # ✅ جديد
│   ├── minimal_example.csv       # ✅ جديد
│   ├── cleaned_dataset.csv
│   ├── customers.csv
│   ├── customer_reviews.csv
│   └── ...
│
├── tests/
│   ├── test_api.py
│   ├── test_ml_scripts.py
│   └── conftest.py
│
├── DATA_FORMAT.md                # ✅ جديد - دليل البيانات
├── QUICK_START.md                # ✅ جديد - دليل سريع
├── SOLUTION_SUMMARY.md           # ✅ جديد - ملخص الحل
└── README.md
```

---

## 🔧 تشغيل البرامج النصية

### تحليل استكشافي (EDA)
```powershell
python src/01_eda.py
```
📊 ينتج: إحصائيات وتحليلات أساسية

### تنظيف البيانات
```powershell
python src/02_cleaning_features.py
```
📊 ينتج: `data/cleaned_dataset.csv`

### تدريب نموذج التنبؤ
```powershell
python src/ml_lifecycle/train_forecast.py
```
🤖 ينتج: `src/ml_lifecycle/model_registry/sales_forecast_model.pkl`

### تقييم النموذج
```powershell
python src/ml_lifecycle/evaluate_forecast.py
```
📈 ينتج: تقرير الأداء (MAE, RMSE, R²)

### توليد التنبؤات
```powershell
python src/ml_lifecycle/predict_forecast.py
```
🔮 ينتج: `data/sales_forecast_future.csv` (6 شهور)

### إعادة تدريب النموذج
```powershell
python src/ml_lifecycle/retrain_forecast.py
```
🔄 ينتج: تحديث النموذج بالبيانات الجديدة

---

## 📊 API Endpoints

### KPIs
```
GET /api/kpis
```
Response:
```json
{
  "total_revenue": 45000.00,
  "total_orders": 150,
  "average_order_value": 300.00,
  "top_product": "Laptop",
  "top_city": "Algiers"
}
```

### المبيعات الشهرية (مع التنبؤات)
```
GET /api/monthly-sales
```

### أفضل المنتجات
```
GET /api/top-products
```

### أفضل المدن
```
GET /api/top-cities
```

### تحليل المشاعر
```
GET /api/sentiment
```

### التوصيات
```
GET /api/recommendations
```

---

## 🧪 تشغيل الاختبارات

### اختبار صحة البيانات
```powershell
python test_data_upload.py
```

### اختبار API
```powershell
pytest tests/test_api.py -v
```

### اختبار ML Scripts
```powershell
pytest tests/test_ml_scripts.py -v
```

---

## 🐛 استكشاف الأخطاء

### ❌ "Missing required columns"
**الحل:** تأكد من وجود الأعمدة الخمس المطلوبة
```powershell
python test_data_upload.py  # للتحقق
```

### ❌ Backend لا يستجيب
```powershell
pip install fastapi uvicorn
python -m uvicorn backend.main:app --reload --port 8000
```

### ❌ Frontend packages missing
```powershell
cd frontend
npm install
npm run dev
```

### ❌ Python version issue
```powershell
python --version  # يجب أن يكون 3.8+
```

---

## 📖 الملفات الإضافية

| الملف | الوصف |
|------|--------|
| [DATA_FORMAT.md](./DATA_FORMAT.md) | دليل تنسيق البيانات بالتفصيل |
| [QUICK_START.md](./QUICK_START.md) | دليل التشغيل السريع |
| [SOLUTION_SUMMARY.md](./SOLUTION_SUMMARY.md) | ملخص حل المشكلة |
| [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) | دليل التكامل (Backend + Frontend) |
| [ML_LIFECYCLE.md](./ML_LIFECYCLE.md) | توثيق دورة حياة ML |
| [SECURITY_REVIEW.md](./SECURITY_REVIEW.md) | مراجعة الأمان |
| [PROJECT_EVALUATION.md](./PROJECT_EVALUATION.md) | تقييم المشروع |
| [APPLIED_IMPROVEMENTS.md](./APPLIED_IMPROVEMENTS.md) | التحسينات المطبقة |

---

## ✨ المميزات الرئيسية

✅ **Data Upload**: رفع ملفات CSV بمرونة  
✅ **Validation**: التحقق الذكي من الأعمدة  
✅ **ML Pipeline**: تدريب وتقييم وتنبؤ تلقائي  
✅ **Dashboard**: لوحة تحكم تفاعلية  
✅ **Forecasting**: التنبؤ بالمبيعات للـ 6 شهور القادمة  
✅ **RFM Analysis**: تقسيم العملاء  
✅ **Sentiment**: تحليل مشاعر العملاء  
✅ **Recommendations**: توصيات المنتجات  

---

## 🚀 النقطة التالية

بعد التشغيل الناجح، يمكنك:
1. رفع بيانات حقيقية عبر Data Upload
2. مراقبة المقاييس في Dashboard
3. عرض التنبؤات المستقبلية
4. استكشاف التوصيات

---

## 📞 الدعم

- 📚 اقرأ [DATA_FORMAT.md](./DATA_FORMAT.md) للبيانات
- ⚡ اقرأ [QUICK_START.md](./QUICK_START.md) للتشغيل السريع
- 🔧 اقرأ [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) للتكامل

---

**آخر تحديث:** 23 يناير 2026  
**الحالة:** ✅ جاهز للتشغيل
