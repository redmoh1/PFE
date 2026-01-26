# 🚀 دليل التشغيل السريع - Sales Intelligence Project

## تم إصلاح مشكلة رفع الملفات! ✅

### المشكلة القديمة:
```
❌ Validation Failed
Missing required columns: [id, date, amount, product, city]
```

### الحل:
✅ نظام التحميل الآن يدعم **أسماء أعمدة مختلفة** تلقائياً!

---

## 📋 المتطلبات

- **Python 3.8+** (مثبت)
- **Node.js 18+** (مثبت)
- **pip** (مثبت)
- **npm** (مثبت)

---

## 🔧 خطوات التثبيت والتشغيل

### الخطوة 1️⃣: تثبيت المكتبات (Backend)

```powershell
cd "c:\Users\DELL\Desktop\New folder\Sales_Intelligence_Project"
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### الخطوة 2️⃣: تثبيت المكتبات (Frontend)

```powershell
cd frontend
npm install
```

### الخطوة 3️⃣: تشغيل Backend API

**افتح Terminal جديد:**
```powershell
cd "c:\Users\DELL\Desktop\New folder\Sales_Intelligence_Project"
python -m uvicorn backend.main:app --reload --port 8000
```

✅ API متاح على: **http://localhost:8000**
📚 Documentation: **http://localhost:8000/docs**

### الخطوة 4️⃣: تشغيل Frontend Dashboard

**افتح Terminal ثاني:**
```powershell
cd "c:\Users\DELL\Desktop\New folder\Sales_Intelligence_Project\frontend"
npm run dev
```

✅ Dashboard متاح على: **http://localhost:5173**

---

## 📊 اختبار رفع البيانات

### ✅ الأعمدة المدعومة الآن:

| المتطلب | الأسماء البديلة |
|--------|------------------|
| **id** | `orderid`, `transactionid`, `order_id` |
| **date** | `orderdate`, `order_date`, `transactiondate` |
| **amount** | `totalprice`, `total_price`, `price`, `ordervalue` |
| **product** | `productname`, `product_name`, `item` |
| **city** | `location`, `region` |

### 📁 نماذج ملفات للاختبار:

1. **ملف نموذجي جاهز:**
   ```
   data/sample_sales.csv
   ```

2. **ملفك الحالي (إذا كان صحيحاً):**
   ```
   data/sales.csv
   ```

3. **البيانات المنظفة:**
   ```
   data/cleaned_dataset.csv
   ```

### 🧪 طريقة الاختبار:

1. اذهب إلى **Data Upload** في الـ Dashboard
2. اختر ملف CSV (أي من النماذج أعلاه)
3. اضغط **Select CSV File**
4. انتظر الرسالة ✅ **Pipeline Complete!**

---

## 🐛 استكشاف الأخطاء

### ❌ خطأ: "Missing required columns"

**السبب:** الملف لا يحتوي على الأعمدة المطلوبة

**الحل:**
- تأكد من وجود 5 أعمدة على الأقل (id, date, amount, product, city)
- استخدم أسماء الأعمدة من الجدول أعلاه
- اطلع على [DATA_FORMAT.md](./DATA_FORMAT.md)

---

### ❌ خطأ: Backend لا يستجيب

```powershell
# تأكد من تشغيل الـ Backend
python -m uvicorn backend.main:app --reload --port 8000

# إذا كان هناك خطأ، جرب:
pip install fastapi uvicorn
```

---

### ❌ خطأ: npm packages missing

```powershell
cd frontend
npm install
npm run dev
```

---

## 🎯 هيكل المشروع

```
Sales_Intelligence_Project/
├── backend/                    # ✅ FastAPI Server
│   ├── main.py                # API endpoints
│   └── requirements.txt        
├── frontend/                   # ✅ React Dashboard
│   ├── pages/
│   │   └── DataUpload.tsx      # ✅ محدث - يدعم أسماء أعمدة متعددة
│   └── package.json
├── src/                        # Python ML Scripts
│   ├── 01_eda.py
│   ├── 02_cleaning_features.py
│   ├── 03_forecasting.py
│   ├── 04_rfm.py
│   ├── 05_recommendation.py
│   ├── 06_sentiment.py
│   ├── 07_dashboard.py
│   └── ml_lifecycle/           # Model Training Pipeline
│       ├── train_forecast.py
│       ├── evaluate_forecast.py
│       ├── predict_forecast.py
│       └── retrain_forecast.py
├── data/                       # 📊 البيانات
│   ├── sales.csv              # بيانات المبيعات الأصلية
│   ├── sample_sales.csv       # ✅ ملف نموذجي للاختبار
│   ├── cleaned_dataset.csv    # بيانات منظفة
│   └── ...
├── DATA_FORMAT.md             # ✅ جديد - دليل تنسيق البيانات
└── README.md
```

---

## 🚀 الخطوات التالية

1. **تشغيل البيانات الأساسية:**
   ```powershell
   python src/01_eda.py
   python src/02_cleaning_features.py
   ```

2. **تدريب نموذج التنبؤ:**
   ```powershell
   python src/ml_lifecycle/train_forecast.py
   ```

3. **تقييم النموذج:**
   ```powershell
   python src/ml_lifecycle/evaluate_forecast.py
   ```

4. **توليد التنبؤات:**
   ```powershell
   python src/ml_lifecycle/predict_forecast.py
   ```

---

## 🆘 الدعم

- **مشكلة في البيانات?** اطلع على [DATA_FORMAT.md](./DATA_FORMAT.md)
- **مشكلة في التكامل?** اطلع على [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
- **مشكلة في ML?** اطلع على [ML_LIFECYCLE.md](./ML_LIFECYCLE.md)

---

## 📝 الملفات المحدثة

✅ `frontend/pages/DataUpload.tsx` - دعم أسماء أعمدة متعددة
✅ `DATA_FORMAT.md` - دليل جديد لتنسيق البيانات
✅ `data/sample_sales.csv` - ملف نموذجي جاهز للاختبار

---

**آخر تحديث:** 23 يناير 2026
