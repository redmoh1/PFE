# 📊 نظام ذكي لتحليل وتنبؤ المبيعات
**Intelligent Sales Analytics and Forecasting System**

---

## 📋 نظرة عامة على المشروع

### ما هو المشروع؟

هذا مشروع متكامل يجمع بين **تحليل البيانات** و**التعلم الآلي** و**تطبيقات الويب الحديثة** لمساعدة الشركات على:

✅ فهم أنماط المبيعات والعملاء  
✅ التنبؤ بالمبيعات المستقبلية  
✅ تقسيم العملاء وتحليلهم  
✅ تقديم توصيات منتجات ذكية  
✅ تحليل مشاعر العملاء من التقييمات  

---

## 🏗️ معمارية النظام

### الهيكل العام (Three-Tier Architecture)

```
┌─────────────────────────────────────────────────────────┐
│           React Frontend (TypeScript + Vite)            │
│        لوحة تحكم تفاعلية لعرض البيانات والنتائج        │
└────────────────────────┬────────────────────────────────┘
                         │ (HTTP/REST API)
                         ↓
┌─────────────────────────────────────────────────────────┐
│          FastAPI Backend (Python)                       │
│    خادم الويب ومدير نقاط نهاية البيانات               │
└────────────────────────┬────────────────────────────────┘
                         │ (يستدعي)
                         ↓
┌─────────────────────────────────────────────────────────┐
│       ML Pipeline (Python Scripts)                      │
│   خط أنابيب التعلم الآلي ومعالجة البيانات             │
│  - تحليل استكشافي (EDA)                               │
│  - تنظيف البيانات (Cleaning)                           │
│  - التنبؤ بالمبيعات (Forecasting)                     │
│  - تحليل RFM (Customer Segmentation)                  │
│  - التوصيات (Market Basket Analysis)                  │
│  - تحليل المشاعر (Sentiment Analysis)                 │
└─────────────────────────────────────────────────────────┘
        ↑
        │ (قراءة/كتابة)
        ↓
┌─────────────────────────────────────────────────────────┐
│           نظام إدارة البيانات                          │
│  - قاعدة بيانات SQLite (metadata)                      │
│  - ملفات CSV (البيانات الأولية والمعالجة)           │
│  - نماذج ML المحفوظة (joblib)                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 هيكل المشروع

```
Sales_Intelligence_Project/
│
├── backend/
│   ├── main.py                 # خادم FastAPI الرئيسي
│   └── requirements.txt         # متطلبات Python للخادم
│
├── frontend/                    # تطبيق React
│   ├── components/              # مكونات UI
│   ├── pages/                   # صفحات التطبيق
│   ├── store/                   # إدارة الحالة (Context API)
│   ├── package.json
│   └── vite.config.ts
│
├── src/                         # خط أنابيب ML
│   ├── 01_eda.py               # المرحلة 1: تحليل استكشافي
│   ├── 02_cleaning_features.py  # المرحلة 2: تنظيف البيانات
│   ├── 03_forecasting.py        # المرحلة 3: التنبؤ بالمبيعات
│   ├── 04_rfm.py                # المرحلة 4: تقسيم العملاء
│   ├── 05_recommendation.py     # المرحلة 5: التوصيات
│   ├── 06_sentiment.py          # المرحلة 6: تحليل المشاعر
│   ├── pipeline_controller.py   # منسق خط الأنابيب (Single Source of Truth)
│   └── ml_lifecycle/             # دورة حياة النماذج
│       ├── train_forecast.py    # تدريب النموذج
│       ├── evaluate_forecast.py  # تقييم الأداء
│       ├── predict_forecast.py   # التنبؤ المستقبلي
│       ├── retrain_forecast.py   # إعادة تدريب
│       └── model_registry/       # مستودع النماذج المحفوظة
│
├── data/                        # البيانات
│   └── {Company_ID}/
│       ├── sales/               # بيانات المبيعات (CSV)
│       ├── customers/           # بيانات العملاء (CSV)
│       └── reviews/             # تقييمات العملاء (CSV)
│
├── output/                      # المخرجات والنتائج
│   ├── plots/                   # الرسوم البيانية
│   ├── *.csv                    # ملفات النتائج
│   └── *.json                   # تقارير JSON
│
├── logs/                        # ملفات السجلات
│
├── tests/                       # اختبارات الوحدة
│
├── config.py                    # ملف الإعدادات الرئيسي
└── README.md                    # التوثيق

```

---

## 🔄 كيفية عمل النظام بالتفصيل

### المسار الكامل لمعالجة البيانات

```
┌─────────────────────────────────────────────────────────────┐
│ 1️⃣ رفع البيانات عبر الواجهة الأمامية                      │
│    (sales.csv, customers.csv, customer_reviews.csv)       │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 2️⃣ تخزين البيانات في قاعدة البيانات SQLite               │
│    + نسخ في مجلد البيانات                                   │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 3️⃣ استدعاء Pipeline Controller                             │
│    (يحقق من حالة البيانات والملفات المشتقة)              │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 4️⃣ تنفيذ خط الأنابيب بالترتيب:                            │
│    01 → 02 → 03 → 04 → 05 → 06                            │
│                                                             │
│ كل مرحلة تقرأ من المرحلة السابقة وتكتب النتائج           │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 5️⃣ حفظ النتائج والنماذج                                    │
│    - ملفات CSV للنتائج                                     │
│    - نموذج pickle لإعادة الاستخدام                       │
│    - رسوم بيانية وتقارير                                   │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 6️⃣ عرض النتائج عبر لوحة التحكم                            │
│    (الرسوم البيانية والجداول والإحصائيات)               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧮 الخوارزميات الرئيسية

### 1️⃣ التحليل الاستكشافي (EDA - Exploratory Data Analysis)

**الغرض:** فهم البيانات وتحديد الأنماط الأساسية

**الخطوات:**
```
├─ تحميل البيانات (sales.csv, customers.csv, reviews.csv)
├─ التحقق من جودة البيانات (null values, duplicates)
├─ توحيد أسماء الأعمدة (normalization)
├─ حساب الإحصائيات الأساسية (min, max, mean, std)
├─ دمج البيانات بناءً على Customer/Order IDs
├─ حفظ البيانات الموحدة (merged_data.csv)
└─ إنشاء رسوم بيانية استكشافية
```

**المخرجات:**
- `merged_data.csv` - البيانات الموحدة من جميع المصادر
- `eda_report.json` - تقرير الإحصائيات الأساسية

---

### 2️⃣ تنظيف البيانات (Data Cleaning & Feature Engineering)

**الغرض:** تحضير البيانات للتحليل والتعلم الآلي

**الخطوات:**
```
├─ إزالة القيم المفقودة (NULL handling)
├─ إزالة القيم المكررة (duplicates)
├─ معالجة القيم الشاذة (outliers)
├─ تنسيق التواريخ (date parsing)
├─ تحويل الأنواع (type conversion)
├─ إنشاء ميزات جديدة:
│  ├─ YearMonth من OrderDate
│  ├─ Year, Month, Quarter
│  ├─ DayOfWeek من التاريخ
│  ├─ TotalPrice من Price * Quantity
│  └─ إضافة معرف العميل والمدينة
├─ معايرة البيانات العددية (normalization)
└─ حفظ البيانات النظيفة (cleaned_dataset.csv)
```

**المخرجات:**
- `cleaned_dataset.csv` - البيانات الجاهزة للمعالجة

---

### 3️⃣ التنبؤ بالمبيعات (Sales Forecasting)

**الخوارزمية:** Linear Regression مع Time Series

**الخطوات:**
```
1️⃣ تجميع البيانات شهرياً (Monthly Aggregation)
   ├─ حساب إجمالي المبيعات لكل شهر
   ├─ إنشاء مؤشر زمني (MonthIndex = 0, 1, 2, ...)
   └─ تصفية الأشهر بدون مبيعات

2️⃣ تقسيم البيانات (Temporal Split)
   ├─ البيانات التدريبية: 80% (التواريخ الأقدم)
   ├─ بيانات الاختبار: 20% (التواريخ الأحدث)
   └─ ✅ لا يتم خلط البيانات (no shuffling) - مهم للسلاسل الزمنية

3️⃣ بناء النموذج (Model Training)
   ├─ استخدام LinearRegression
   ├─ X = MonthIndex (مؤشر زمني)
   ├─ y = TotalPrice (المبيعات)
   └─ Equation: Sales = a * Month + b

4️⃣ تقييم الأداء (Model Evaluation)
   ├─ R² Score: نسبة التباين المشروحة (0-1)
   ├─ MAE (Mean Absolute Error): الخطأ المتوسط المطلق
   └─ RMSE: جذر مربع الخطأ المتوسط

5️⃣ التنبؤ المستقبلي (Future Prediction)
   ├─ إنشاء مؤشرات زمنية للأشهر القادمة
   ├─ استخدام النموذج للتنبؤ
   └─ حفظ النتائج (sales_forecast_future.csv)
```

**المعادلة الرياضية:**
$$\text{Sales}_{future} = m \times t + b$$

حيث:
- $m$ = ميل الخط (معدل التغير)
- $t$ = المؤشر الزمني (شهر)
- $b$ = التقاطع (القيمة الأولية)

**المخرجات:**
- `sales_forecast.csv` - التنبؤات التاريخية
- `sales_forecast_future.csv` - التنبؤات المستقبلية (60 شهر)

---

### 4️⃣ تقسيم العملاء (RFM Analysis)

**الغرض:** تصنيف العملاء بناءً على قيمتهم

**الخوارزمية: RFM Segmentation**

```
RFM يرمز إلى:
R = Recency    (قرب آخر عملية شراء)
F = Frequency  (عدد مرات الشراء)
M = Monetary   (إجمالي المبلغ المنفق)
```

**الخطوات:**

```
1️⃣ حساب مقاييس RFM لكل عميل
   ├─ Recency: عدد الأيام منذ آخر طلب
   │  = اليوم الحالي - أحدث تاريخ طلب
   │
   ├─ Frequency: إجمالي عدد الطلبات
   │  = COUNT(OrderID) لكل CustomerID
   │
   └─ Monetary: إجمالي المبالغ المنفقة
      = SUM(TotalPrice) لكل CustomerID

2️⃣ تقسيم القيم إلى فترات (Binning)
   ├─ تقسيم R إلى 5 فترات
   │  (الأقل حداثة إلى الأكثر حداثة)
   │
   ├─ تقسيم F إلى 5 فترات
   │  (الأقل تكراراً إلى الأكثر تكراراً)
   │
   └─ تقسيم M إلى 5 فترات
      (الأقل إنفاقاً إلى الأكثر إنفاقاً)

3️⃣ إنشاء درجات RFM
   ├─ RFM_Score = R_Score + F_Score + M_Score
   ├─ يتراوح من 3 إلى 15
   └─ الدرجات الأعلى = عملاء أكثر قيمة

4️⃣ تصنيف العملاء
   ├─ VIP Customers      (12-15): عملاء نجمة
   ├─ Loyal Customers    (9-11):  عملاء وفيون
   ├─ Potential          (6-8):   عملاء بإمكانيات
   └─ At Risk            (3-5):   عملاء قد يتركون
```

**مثال:**
```
CustomerID | Recency | Frequency | Monetary | R_bin | F_bin | M_bin | Segment
-----------|---------|-----------|----------|-------|-------|-------|----------
C001       | 5       | 15        | 5000     | 5     | 5     | 5     | VIP
C002       | 60      | 3         | 500      | 2     | 2     | 2     | At Risk
C003       | 20      | 8         | 2000     | 4     | 4     | 4     | Loyal
```

**المخرجات:**
- `rfm_table.csv` - جدول RFM كامل لكل عميل

---

### 5️⃣ توصيات المنتجات (Market Basket Analysis)

**الغرض:** اكتشاف أنماط الشراء المشتركة وتقديم توصيات

**الخوارزمية: Apriori Algorithm**

```
الفكرة الأساسية:
- العملاء الذين يشترون المنتج A غالباً يشترون أيضاً المنتج B
- هذه الأنماط يمكن استخدامها لتوصيات شخصية
```

**الخطوات:**

```
1️⃣ بناء مصفوفة التعاملات (Transaction Matrix)
   ├─ كل صف = عميل
   ├─ كل عمود = منتج
   └─ القيمة = 1 إذا اشترى العميل المنتج، 0 وإلا
   
   مثال:
   Customer | Product_A | Product_B | Product_C
   ---------|-----------|-----------|----------
   C001     | 1         | 1         | 0
   C002     | 1         | 0         | 1
   C003     | 1         | 1         | 1

2️⃣ تطبيق Apriori Algorithm
   ├─ min_support = 1% (المنتجات المشتراة معاً في 1% من الحالات على الأقل)
   ├─ min_confidence = 10% (إذا اشترى A، احتمال شراء B = 10% على الأقل)
   └─ min_lift = 1.0 (نسبة الارتباط)

3️⃣ استخراج القواعس (Association Rules)
   ├─ {A} → {B}: إذا اشترى A فاشترى B
   ├─ Support: في كم نسبة من الحالات يحدث كليهما
   ├─ Confidence: احتمال شراء B عند شراء A
   └─ Lift: كم مرة أقوى من الصدفة العشوائية

4️⃣ توليد التوصيات
   ├─ ترتيب القواعس حسب Lift (الأقوى أولاً)
   └─ للعميل الذي يشتري A، توصي بـ B
```

**مثال رياضي:**

```
إذا كان لدينا:
- 1000 عملية شراء إجمالية
- 50 عملية تضمنت {Laptop, Mouse}
- 100 عملية تضمنت Laptop
- 200 عملية تضمنت Mouse

التحليل:
- Support({Laptop, Mouse}) = 50/1000 = 5%
- Confidence({Laptop}→{Mouse}) = 50/100 = 50%
- Lift = (50/1000) / (100/1000 * 200/1000) = 2.5

الدلالة:
✅ الذين يشترون Laptop لديهم احتمال 50% أن يشتروا Mouse
✅ هذا احتمال أقوى بـ 2.5 مرة من الصدفة!
```

**المخرجات:**
- `product_recommendations.csv` - قواعس التوصيات

---

### 6️⃣ تحليل المشاعر (Sentiment Analysis)

**الغرض:** فهم رأي العملاء من خلال تقييماتهم

**الخوارزمية: TextBlob Sentiment Analysis**

```
TextBlob تحلل النصوص عبر:
1. Polarity (القطبية):    من -1 (سلبي) إلى +1 (إيجابي)
2. Subjectivity (الذاتية): من 0 (موضوعي) إلى 1 (ذاتي)
```

**الخطوات:**

```
1️⃣ استخراج النصوص من البيانات
   ├─ البحث عن عمود النصوص (ReviewText, Review, Comment إلخ)
   └─ تنظيف النصوص (إزالة مسافات زائدة)

2️⃣ تحليل المشاعر لكل نص
   ├─ حساب Polarity:
   │  └─ النص = "المنتج رائع جداً"
   │     Polarity = +0.8 (إيجابي جداً)
   │
   ├─ حساب Subjectivity:
   │  └─ النص = "المنتج جميل" vs "المنتج يزن 500 غرام"
   │     النص الأول أكثر ذاتية
   │
   └─ تصنيف المشاعر:
      ├─ Positive   (Polarity > 0.1)
      ├─ Neutral    (-0.1 ≤ Polarity ≤ 0.1)
      └─ Negative   (Polarity < -0.1)

3️⃣ إحصائيات تجميعية
   ├─ نسبة المشاعر الإيجابية/السلبية/المحايدة
   ├─ متوسط Polarity
   ├─ المنتجات ذات أعلى تقييمات
   └─ اتجاهات المشاعر عبر الزمن

4️⃣ حفظ النتائج
   └─ sentiment_results.csv بجميع المقاييس
```

**مثال:**

```
Review Text                           | Polarity | Subjectivity | Sentiment
--------------------------------------|----------|--------------|----------
"رائع جداً أنصح الجميع"              | +0.85    | 0.9          | Positive
"جودة عادية وثمن غالي"              | -0.40    | 0.6          | Negative
"المنتج يزن 500غ كما المواصفات"      | +0.10    | 0.3          | Neutral
```

**المخرجات:**
- `sentiment_results.csv` - نتائج تحليل المشاعر

---

## 🔌 API Endpoints (واجهة برمجية)

### نقاط النهاية الرئيسية في FastAPI:

```
POST /upload/
├─ الغرض: رفع ملفات البيانات
└─ المدخلات: 
   ├─ files: (sales.csv, customers.csv, customer_reviews.csv)
   └─ company_id: معرف الشركة

GET /data/dashboard/
├─ الغرض: الحصول على بيانات لوحة التحكم الرئيسية
└─ المخرجات: ملخص البيانات والرسوم البيانية

POST /analyze/
├─ الغرض: تشغيل خط الأنابيب
└─ المدخلات: company_id

GET /results/{result_type}/
├─ الغرض: الحصول على نتائج معينة
├─ result_type: forecast, rfm, recommendations, sentiment
└─ المخرجات: JSON مع النتائج

GET /metrics/
├─ الغرض: إحصائيات الأداء
└─ المخرجات: KPIs والمقاييس المهمة
```

---

## 🛠️ تدفق العمل الكامل

### 1. المستخدم ينقر على "رفع البيانات" 📤

```
المستخدم رفع (sales.csv, customers.csv, reviews.csv)
         ↓
FastAPI Backend
- حفظ الملفات في مجلد data/{company_id}
- إنشاء سجل في قاعدة البيانات SQLite
- التحقق من صحة الملفات
         ↓
الواجهة تعرض: "تم رفع البيانات بنجاح ✅"
```

### 2. المستخدم ينقر على "تحليل البيانات" 🔍

```
المستخدم ينقر على زر التحليل
         ↓
FastAPI → Pipeline Controller
         ↓
التحقق من حالة البيانات:
- هل توجد بيانات جديدة؟
- هل توجد ملفات مشتقة قديمة؟
         ↓
حذف الملفات القديمة (Clean Slate)
         ↓
تنفيذ خط الأنابيب:

  [01_eda.py]
  قراءة: sales.csv, customers.csv, reviews.csv
  كتابة: merged_data.csv
         ↓
  [02_cleaning_features.py]
  قراءة: merged_data.csv
  كتابة: cleaned_dataset.csv
         ↓
  [03_forecasting.py]
  قراءة: cleaned_dataset.csv
  كتابة: sales_forecast.csv, sales_forecast_future.csv
  (يدرب نموذج LinearRegression)
         ↓
  [04_rfm.py]
  قراءة: cleaned_dataset.csv
  كتابة: rfm_table.csv
         ↓
  [05_recommendation.py]
  قراءة: cleaned_dataset.csv
  كتابة: product_recommendations.csv
         ↓
  [06_sentiment.py]
  قراءة: cleaned_dataset.csv
  كتابة: sentiment_results.csv
         ↓
FastAPI يعود بـ: "اكتمل التحليل ✅"
```

### 3. المستخدم يعرض النتائج 📊

```
React Dashboard يطلب البيانات من FastAPI
         ↓
FastAPI يقرأ الملفات:
- sales_forecast.csv → رسم بياني خط المبيعات
- rfm_table.csv → رسم بياني RFM
- sentiment_results.csv → مخطط فطيرة المشاعر
- product_recommendations.csv → جدول التوصيات
         ↓
React يعرض:
├─ مؤشرات KPI (إجمالي المبيعات، عدد العملاء، إلخ)
├─ رسوم بيانية تفاعلية
├─ جداول البيانات
└─ توصيات المنتجات
```

---

## 💾 إدارة حالة البيانات (State Management)

### Pipeline Controller - مدير الحالة

**المسؤولية الرئيسية:**
تحقيق حالة نظيفة قبل كل تشغيل

```python
def orchestrate_pipeline(company_id: str):
    """تنفيذ خط الأنابيب بشكل آمن"""
    
    # 1. كشف البيانات المحذوفة
    detect_data_deletion(company_id)
    
    # 2. حذف الملفات المشتقة القديمة
    hard_reset_derived_outputs(company_id)
    
    # 3. تنفيذ كل مرحلة بالترتيب
    for script in PIPELINE_SCRIPTS:
        run_python_script(script)
    
    # 4. تحديث حالة البيانات
    update_pipeline_state()
```

---

## 📊 ملفات المدخلات والمخرجات

### البيانات المدخلة (Inputs):

| الملف | الأعمدة المطلوبة | المثال |
|------|----------------|--------|
| `sales.csv` | OrderID, CustomerID, OrderDate, TotalPrice, Product | ✅ إلزامي |
| `customers.csv` | CustomerID, City | ❓ اختياري |
| `customer_reviews.csv` | ReviewText, Rating | ❓ اختياري |

### البيانات المخرجة (Outputs):

| الملف | الغرض | الاستخدام |
|------|------|----------|
| `merged_data.csv` | دمج جميع البيانات | المشهد الكامل للبيانات |
| `cleaned_dataset.csv` | البيانات بعد التنظيف | المصدر الثاني لـ ML |
| `sales_forecast.csv` | التنبؤات التاريخية | رسم بياني المقارنة |
| `sales_forecast_future.csv` | التنبؤات المستقبلية | التخطيط المالي |
| `rfm_table.csv` | تقسيم العملاء | تحديد العملاء المهمين |
| `product_recommendations.csv` | قواعس التوصيات | Cross-selling |
| `sentiment_results.csv` | تحليل المشاعر | رضا العملاء |

---

## 🎯 الميزات الرئيسية

### ✨ نقاط القوة:

✅ **نظام تلقائي كامل**
- من رفع البيانات إلى النتائج، كل شيء آلي

✅ **معايرة عالية الجودة**
- التحقق من البيانات، التنظيف، معالجة الأخطاء

✅ **قابل للتوسع**
- دعم شركات متعددة
- إمكانية إضافة خوارزميات جديدة

✅ **تقارير شاملة**
- جداول، رسوم بيانية، إحصائيات

✅ **سهل الاستخدام**
- واجهة رسومية حديثة بـ React
- API موثقة بـ Swagger

---

## 🚀 كيفية التشغيل

### الخطوة 1: تثبيت المتطلبات

```bash
# Python الخادم
pip install -r backend/requirements.txt
pip install -r requirements.txt

# Node.js الواجهة
cd frontend
npm install
```

### الخطوة 2: بدء الخادم

```bash
# طرفية 1 - FastAPI
python -m uvicorn backend.main:app --reload --port 8000

# الخادم سيكون متاحاً في: http://localhost:8000
# التوثيق التفاعلية: http://localhost:8000/docs
```

### الخطوة 3: بدء الواجهة الأمامية

```bash
# طرفية 2 - React
cd frontend
npm run dev

# الواجهة ستكون متاحة في: http://localhost:5173
```

### الخطوة 4: استخدام النظام

1. افتح المتصفح: `http://localhost:5173`
2. ارفع ملفات البيانات (CSV)
3. انقر على "تحليل البيانات"
4. شاهد النتائج والرسوم البيانية

---

## 📈 مثال عملي كامل

### السيناريو: شركة Acme Corp

**البيانات المرفوعة:**
```
sales.csv:
OrderID | CustomerID | OrderDate  | TotalPrice | Product
1       | C001       | 2024-01-15 | 1000      | Laptop
2       | C002       | 2024-01-20 | 500       | Mouse
3       | C001       | 2024-02-10 | 1500      | Monitor
...

customers.csv:
CustomerID | City
C001       | Cairo
C002       | Alexandria
...

reviews.csv:
CustomerID | ReviewText              | Rating
C001       | المنتج ممتاز جداً       | 5
C002       | جودة عادية             | 3
...
```

**نتائج التحليل:**

```
1. EDA:
   - عدد العملاء: 100
   - إجمالي المبيعات: $50,000
   - متوسط الطلب: $500

2. التنبؤ:
   - توقع المبيعات للشهر القادم: $6,200
   - اتجاه النمو: +5% شهرياً

3. RFM:
   - عملاء VIP: 10 (عملاء بقيمة عالية)
   - عملاء في خطر: 15 (يحتاجون عناية)

4. التوصيات:
   - من يشتري Laptop → ينبغي أن يشتري Monitor (Confidence: 75%)

5. المشاعر:
   - 80% تقييمات إيجابية
   - متوسط الرضا: 4.2 من 5
```

---

## 🔧 التكنولوجيا المستخدمة

### Backend (الخادم):
- **FastAPI**: إطار عمل ويب حديث وسريع
- **Pandas & NumPy**: معالجة البيانات
- **Scikit-learn**: التعلم الآلي
- **TextBlob**: تحليل المشاعر
- **MLXtend**: تحليل السلة السوقية
- **SQLite**: قاعدة البيانات

### Frontend (الواجهة):
- **React**: مكتبة بناء الواجهات
- **TypeScript**: لغة محسنة للنوع الآمن
- **Vite**: بناء سريع والتطوير
- **Tailwind CSS**: أنماط حديثة

### DevOps:
- **Docker**: حاويات لسهولة النشر
- **Logging**: تسجيل الأحداث والأخطاء

---

## 🧪 الاختبارات

```bash
# تشغيل اختبارات الوحدة
pytest tests/

# الاختبارات تغطي:
├─ اختبار API endpoints
├─ اختبار خوارزميات ML
├─ اختبار معالجة الأخطاء
└─ اختبار أداء البيانات الضخمة
```

---

## 📝 الخلاصة

هذا المشروع هو **نظام ذكي متكامل** يجمع بين:
- 📊 تحليل متقدم للبيانات
- 🤖 خوارزميات تعلم آلي متعددة
- 🎨 واجهة مستخدم حديثة وسهلة
- 🔄 تلقيم تلقائي كامل

**الفائدة الرئيسية:** تمكين الشركات من فهم مبيعاتهم والتنبؤ بالمستقبل والعثور على فرص نمو جديدة!

---

**آخر تحديث:** 27 يناير 2026  
**النسخة:** 1.0.0  
**الحالة:** ✅ جاهز للإنتاج

---

# 📚 شرح تدريسي تفصيلي جدًا جدًا (نسخة طالب إعلام آلي)

## منهجية التوثيق والشرح

يعتمد هذا التوثيق على شرح المشروع بشكل تدريجي ومنهجي، مع الالتزام بالتفصيل العميق وعدم تجاوز أي جزئية مهما كانت بسيطة.

يتبع الشرح الترتيب التالي:

1️⃣ **فكرة المشروع (Project Idea)**  
شرح الدافع وراء المشروع، المشكلة التي يعالجها، وأهميته العملية، مع توضيح السياق الواقعي لاستخدامه.

2️⃣ **معمارية المشروع (Architecture)**  
شرح البنية العامة للمشروع، وتفصيل أدوار كل جزء (Backend / Frontend / Database / ML إن وُجد)، وكيفية تواصل هذه الأجزاء مع بعضها، ولماذا تم اختيار هذه المعمارية بالذات.

3️⃣ **هيكلة المشروع (Project Structure)**  
شرح جميع المجلدات والملفات، سبب وجود كل عنصر، ووظيفته داخل النظام، مع توضيح تأثير حذفه أو تغييره.

4️⃣ **شرح الكود بالتفصيل المُمل (Code Deep Dive)**  
البدء بشرح الملفات الأساسية المرتبطة بمشكلة المشروع (مثل: Alerts / Proxy / OUTPUT_DIR)، مع تحليل الكود سطرًا بسطر:
- شرح كل import
- شرح كل دالة ولماذا كُتبت بهذه الطريقة
- شرح كل سطر كود وماذا يحدث لو تم تغييره

5️⃣ **المفاهيم النظرية (Theoretical Concepts)**  
شرح جميع المفاهيم التقنية المستخدمة في المشروع (مثل: API, REST, JWT, Async, Pipelines, ML Models...) مع:
- تعريف نظري مبسط
- مثال مستقل خارج المشروع
- ربط مباشر بالمشروع

6️⃣ **التحسينات والملاحظات الخاصة بمشروع التخرج (PFE Notes & Improvements)**  
تقديم ملاحظات تقنية، تحسينات محتملة، Code Smells إن وُجدت، ونقاط قوة يمكن التركيز عليها أثناء مناقشة المشروع.

📌 في حال الرغبة في إكمال الشرح **سطرًا بسطر حرفيًا** لجميع الملفات، يتم ذلك حسب أولوية يحددها القارئ (Backend أولًا أو Frontend أو ML Scripts)، حيث سيتم إضافة **ملاحق (Appendices)** مخصصة، مثل:
- ملحق 2: شرح ملف backend/main.py سطرًا بسطر.

---

## 1️⃣ الفكرة العامة للمشروع

### 1. ما المشكلة التي يحلها المشروع؟

تخيّل أنك شركة تبيع منتجات (Retail / E-commerce / متجر)، وعندك بيانات مثل:

- مبيعات (Sales) لكل عملية شراء: تاريخ، منتج، كمية، سعر…
- عملاء (Customers): من هو العميل، مدينته…
- تقييمات/مراجعات (Reviews): نصوص يكتبها العملاء حول تجربتهم (قد تكون بالعربية)

في الحالة التقليدية، الشركة غالبًا:

- تملك البيانات كملفات CSV متفرقة.
- تفتحها في Excel أو أداة BI.
- تعمل رسوم بيانية بسيطة.
- ثم تعتمد على “الخبرة الشخصية” لاتخاذ القرار.

المشكلة: هذا لا يكفي عندما تريد:

1) **فهم المبيعات بشكل عميق**: أين ترتفع؟ أين تنخفض؟ من أفضل المدن؟ ما المنتجات الأقوى؟
2) **التنبؤ بالمستقبل (Forecasting)**: ماذا سيحدث في الشهر القادم؟ هل سننخفض؟ هل نحتاج حملة تسويق؟
3) **تقسيم العملاء (Segmentation)**: من هم العملاء الأهم؟ من على وشك المغادرة؟
4) **توصيات منتجات (Recommendations)**: ما المنتجات التي تُشترى معًا؟ كيف نعمل Cross-sell؟
5) **تحليل مشاعر (Sentiment Analysis)**: هل العملاء راضون أم غاضبون؟ على ماذا يشتكون؟
6) **تنبيهات استباقية (Proactive Alerts)**: بدل أن تراقب أنت لوحة التحكم كل يوم، النظام يخبرك: “انتبه! هناك هبوط في الإيرادات” أو “التوقعات أقل من الهدف”.

إذن، المشروع يحل مشكلة “تحويل البيانات الخام إلى قرارات”.

### 2. لماذا هذا النوع من المشاريع مهم؟

لأن الشركات الحديثة تعتمد على:

- **Data-driven decision making**: قرار مبني على بيانات بدل شعور.
- **Automation**: توفير وقت الموظفين.
- **Scalability**: لما تكبر البيانات، Excel يصبح محدود.
- **Competitive advantage**: من يفهم زبائنه ومبيعاته أسرع، يربح.

### 3. كيف يُستعمل في الواقع؟ (سيناريو واقعي خطوة بخطوة)

1) موظف أو Analyst يرفع ملفات CSV عبر صفحة “Data Ingestion”.
2) الـ Backend يستقبل الملفات ويخزنها في مجلد البيانات لكل شركة (Multi-tenant).
3) الـ Backend يشغّل Pipeline (سلسلة سكربتات Python) لتوليد نتائج:
   - KPIs
   - Forecast
   - Segments
   - Recommendations
   - Sentiment
   - Alerts
4) الـ Frontend يستدعي API endpoints ويعرض النتائج كـ dashboards ورسوم.
5) المستخدم يرى: 
   - Revenue, Orders, AOV, Top City
   - Chart للتوقعات
   - Segmentation bars
   - Alerts Panel يخبره ما الذي يحتاج انتباه

---

## 2️⃣ Architecture المشروع (معمارية النظام)

### 1) ما معنى Architecture أصلًا؟

Architecture = “كيف قُسِّم النظام إلى أجزاء، وما دور كل جزء، وكيف يتواصلون”.

هذا المشروع يتبع فكرة: 

- Frontend (واجهة)
- Backend (خادم API)
- Storage/Data (ملفات + SQLite)
- ML Pipeline (سكربتات تحليل وتعلّم آلي)

### 2) Frontend (React + TypeScript + Vite)

**دوره:**

- عرض الواجهة للمستخدم.
- إرسال طلبات HTTP للـ Backend.
- عرض البيانات (Charts) باستخدام Recharts.
- إدارة الحالة (State) مثل: هل المستخدم logged in؟ هل البيانات محملة؟ هل يوجد error؟

**لماذا React؟**

- React ممتاز لـ Single Page Applications (SPA).
- Component-based: تقسيم الواجهة إلى مكونات صغيرة.
- مجتمع ضخم.

**لماذا TypeScript؟**

- يضيف “أنواع” (Types) على JavaScript.
- يقلل أخطاء runtime.
- يجعل الـ IDE يساعدك أكثر.

**لماذا Vite؟**

- dev server سريع.
- build سريع.
- إعدادات بسيطة.

### 3) Backend (FastAPI - Python)

**دوره:**

- توفير API endpoints مثل `/api/kpis`, `/api/alerts`.
- قراءة البيانات من الملفات/SQLite.
- تشغيل pipeline scripts عند الحاجة.
- تطبيق auth (JWT أو fallback demo token).
- توحيد الاستجابات (JSON) للـ frontend.

**لماذا FastAPI؟**

- سريع.
- يكتب API بسهولة.
- يوفر Swagger UI تلقائيًا (`/docs`).
- يعتمد على type hints ما يجعل الكود أوضح.

### 4) Database / Storage

في هذا المشروع يوجد نوعان من التخزين:

1) **SQLite**: غالبًا للـ metadata/مستخدمين/تتبع ملفات (بحسب أجزاء من الكود).
2) **File-based storage**: ملفات CSV/JSON داخل `data/` و `output/`.

**لماذا File-based outputs؟ (Design Choice)**

- بسيط جدًا للتعلم ولمشاريع PFE.
- يسمح بقراءة النتائج دون تعقيد.
- مناسب للـ offline processing.

**عيوبه:**

- في الإنتاج الحقيقي، الأفضل غالبًا قاعدة بيانات/Storage أقوى.
- إدارة التزامن (concurrency) أصعب.

### 5) ML Pipeline (Python scripts)

**دوره:**

- تحويل البيانات الخام إلى نتائج قابلة للعرض.
- تدريب/تقييم نماذج.
- إنتاج ملفات output.

**لماذا فصل الـ ML كـ scripts؟**

- يجعل pipeline واضحًا: كل مرحلة ملف.
- يسهل اختبار كل خطوة بشكل مستقل.
- مناسب كـ مشروع تخرج لأن كل مرحلة يمكن شرحها.

### 6) كيف تتواصل الأجزاء مع بعضها؟ (Data Flow)

1) Frontend يرسل HTTP request إلى Backend.
2) Backend يعالج الطلب:
   - يقرأ من output أو يشغّل pipeline.
   - يرجع JSON.
3) Frontend يستقبل JSON ويعرضه.

**ملاحظة مهمة جدًا:**

الواجهة لا يجب أن تعتمد على ملفات مباشرة. دائمًا تتعامل مع API.

---

## 3️⃣ Structure المشروع (لماذا كل Folder موجود؟ وما دور كل ملف؟ وماذا لو حذفناه؟)

### جذر المشروع: `Sales_Intelligence_Project/`

هذا المجلد هو “المنتج الكامل” الذي يربط كل شيء.

- `backend/`: كود FastAPI.
  - إذا حذفناه: لن يوجد API، والواجهة لن تحصل على بيانات.

- `frontend/`: تطبيق React.
  - إذا حذفناه: لا يوجد واجهة، لكن يمكن اختبار API مباشرة عبر Swagger.

- `src/`: سكربتات التحليل والـ ML.
  - إذا حذفناه: API قد يعمل جزئيًا لكن أغلب النتائج لن تتولد (forecast/segmentation/alerts...).

- `data/`: بيانات الإدخال (CSV) لكل شركة.
  - إذا حذفناه: لا يوجد “مصدر بيانات”، أغلب endpoints ستعيد 204 أو فارغ.

- `output/`: نتائج المعالجة (CSV/JSON/plots).
  - إذا حذفناه: النتائج تختفي وسيضطر النظام لإعادة التوليد.

- `logs/`: سجلات التشغيل.
  - إذا حذفناه: لن تفقد وظائف النظام، لكن تفقد debug وtrace.

- `tests/`: اختبارات.
  - إذا حذفناه: النظام قد يعمل، لكن ستفقد أمان التحقق من السلوك.

- `requirements.txt` و `backend/requirements.txt`:
  - إذا حذفناهما: تثبيت dependencies يصبح أصعب/غير منظم.

> ملاحظة: يوجد أيضًا مجلد آخر في workspace اسمه `dashboard/` يشبه Frontend مستقل. هذا قد يكون نسخة/تجربة. التركيز الأساسي عادة هو `Sales_Intelligence_Project/frontend/` لأنه مرتبط بالـ backend والـ data.

---

## 4️⃣ شرح الكود بالتفصيل الممل (Core Files أولًا)

سأبدأ بالملفات التي أثّرت مباشرة على المشكلة التي رأيتها في الواجهة (Failed to load alerts) ثم نتوسع.

### (A) ملف Frontend: `frontend/vite.config.ts`

**فكرة الملف:**

هذا ملف إعدادات Vite. عندما تشغل `npm run dev`، Vite يقرأ هذا الملف ليعرف:

- على أي port يشغل dev server.
- هل يوجد plugins.
- هل يوجد proxy لإعادة توجيه طلبات API.

**لماذا مهم؟**

لأن المشكلة التي ظهرت عندك كانت:

- الواجهة طلبت `/api/alerts`.
- بدون proxy، Vite يعاملها كطلب إلى نفس dev server.
- وإذا لم يجد endpoint، يرجّع HTML (`index.html`).
- ثم الكود يحاول `response.json()` فيفشل لأن HTML ليس JSON.

**Imports واحدًا واحدًا:**

1) `import path from 'path';`
   - مكتبة Node.js لمعالجة المسارات.
   - نحتاجها لعمل alias مثل `@`.

2) `import { defineConfig, loadEnv } from 'vite';`
   - `defineConfig`: لتساعد TypeScript على فهم شكل الإعدادات.
   - `loadEnv`: لقراءة متغيرات البيئة (Environment Variables).

3) `import react from '@vitejs/plugin-react';`
   - plugin يجعل Vite يفهم JSX/TSX.

**أهم جزء: server.proxy**

- `proxy: { '/api': { target: 'http://localhost:8000' ... } }`
  - معناها: أي طلب يبدأ بـ `/api`، أرسله للـ backend.

**Design Choice: لماذا proxy بدل كتابة URL كامل في كل fetch؟**

- الـ proxy يجعل الكود أبسط (`/api/alerts` بدل `http://localhost:8000/api/alerts`).
- يقلل مشاكل CORS في التطوير.
- يجعل الانتقال إلى بيئة الإنتاج أسهل (يمكن تغييره حسب النشر).

**بدائل ممكنة:**

1) وضع `VITE_API_BASE=http://localhost:8000` واستخدامه في كل fetch.
2) عمل Nginx reverse proxy في الإنتاج.
3) تشغيل frontend والbackend على نفس domain.

---

### (B) ملف Frontend: `frontend/components/AlertsPanel.tsx`

**فكرة الملف:**

يعرض لوحة تنبيهات الأعمال. هذه اللوحة تعتمد على endpoint: `/api/alerts`.

#### Imports واحدًا واحدًا (بتفسير مبسط):

1) `import React, { useState, useEffect } from 'react';`
   - `React`: ضروري لكتابة Components.
   - `useState`: Hook لتخزين حالة داخل component.
   - `useEffect`: Hook لتشغيل شيء عند mounting أو تغير dependencies.

2) `lucide-react` icons:
   - مجرد أيقونات UI.
   - لا تؤثر على المنطق.

#### Interfaces (BusinessAlert / AlertsData)

في TypeScript، `interface` يحدد شكل البيانات.

- `BusinessAlert`: يمثل alert واحد (id, category, severity...).
- `AlertsData`: يمثل الرد الكامل من API (company, total_alerts, alerts...).

**لماذا نكتب Interfaces؟**

- حتى TypeScript يضمن أن `alertsData.alerts` هو array من `BusinessAlert`.
- حتى الـ IDE يعطي autocomplete ويمنع أخطاء.

#### State variables

داخل component:

- `alertsData`: البيانات القادمة من API.
- `isLoading`: هل نحن في حالة تحميل؟
- `error`: رسالة خطأ إن حدثت.
- `isExpanded`: هل اللوحة مفتوحة أم مطوية.

#### useEffect

`useEffect(() => { fetchAlerts(); }, []);`

- `[]` تعني: شغّل هذا مرة واحدة فقط عند أول render.
- السبب: نريد تحميل alerts مباشرة عند فتح Dashboard.

#### الدالة fetchAlerts (تفصيل ممل)

سأشرحها خطوة خطوة بشكل “قراءة كود بصوت مرتفع”:

1) `setIsLoading(true);`
   - قبل البدء بالطلب، نعلن أننا نحمّل.
   - الهدف: UI يعرض spinner أو placeholder.

2) `setError(null);`
   - إذا كان هناك error قديم من محاولة سابقة، نمسحه.

3) `const response = await fetch('/api/alerts', { headers: { 'X-Company-ID': ... } });`
   - `fetch` = function في المتصفح ترسل HTTP request.
   - المسار `/api/alerts` (بدون domain):
     - في التطوير، Vite proxy سيحوّله إلى `http://localhost:8000/api/alerts`.
   - `headers`:
     - `X-Company-ID` يُستخدم لتحديد الشركة (Multi-tenant).
     - `localStorage.getItem('company') || 'Acme Corp'`:
       - إذا وجدنا company في localStorage نستعملها.
       - وإلا نستعمل 'Acme Corp' كقيمة افتراضية.

4) `if (!response.ok) { throw new Error('Failed to fetch alerts'); }`
   - `response.ok` يعني status code بين 200 و 299.
   - إذا كان 404/500... نرمي error.
   - لماذا نرمي error؟ لأننا نريد الدخول إلى `catch` لتحديث UI.

5) `const data = await response.json();`
   - هنا نحن نقول: “توقعنا أن body هو JSON”.
   - إذا كان body HTML أو نص عادي، هذا السطر سيرمي Exception.
   - وهذا بالضبط سبب رسالة: `Unexpected token '<'` عندما كان proxy غير موجود.

6) `setAlertsData(data);`
   - نخزّن البيانات في state.
   - React سيعمل re-render، والUI سيعرض alerts.

7) `catch (err) { setError(...) }`
   - إذا أي خطأ حدث (شبكة/500/JSON parse)، نخزنه لنظهره للمستخدم.

8) `finally { setIsLoading(false); }`
   - في النهاية، سواء نجح أو فشل، نوقف loading.

**بدائل ممكنة لتنفيذ fetchAlerts:**

1) استخدام `axios` بدل `fetch`.
2) عمل `AbortController` لإلغاء الطلب عند unmount.
3) دمج مع Auth token (هنا alerts endpoint لا يستخدم JWT في الواجهة الحالية).

---

### (C) ملف Backend: `backend/main.py` (الجزء المتعلق بـ alerts + الإعدادات)

**فكرة الملف:**

`main.py` يحتوي تطبيق FastAPI الأساسي، وتعريف endpoints كثيرة.

#### Imports (لماذا يوجد الكثير منها؟)

في backend كبير، ملف main غالبًا يحمل:

- مكتبات Python قياسية (sys, os, logging...)
- مكتبات Data science (pandas/numpy)
- FastAPI components (FastAPI, Request, HTTPException...)
- Auth related modules (HTTPBearer...)

أنا سأركز هنا على ما يؤثر على alerts لأن هذه هي المشكلة التي ظهرت لديك.

#### تعريف المسارات الأساسية (BASE_DIR, DATA_DIR, OUTPUT_DIR)

في بداية الملف يوجد:

- `BASE_DIR = Path(__file__).resolve().parent.parent`
  - `__file__` هو مسار هذا الملف.
  - `parent.parent` يعني: اطلع مجلدين للأعلى.
  - الهدف: الحصول على root الخاص بـ Sales_Intelligence_Project.

- `DATA_DIR = BASE_DIR / "data"`
  - مكان بيانات الإدخال.

- `OUTPUT_DIR = BASE_DIR / "output"`
  - مكان النتائج.
  - هذه المتغير كان ناقصًا سابقًا، وهذا سبب 500 عند endpoint `/api/alerts`.

**لماذا `OUTPUT_DIR` مهم؟**

لأن endpoint `/api/alerts` يبني مسار ملف cache:

`alerts_path = OUTPUT_DIR / f"{company_id}_alerts.json"`

إذا `OUTPUT_DIR` غير معرف، Python سيعطي NameError وبالتالي يرجع 500.

#### Endpoint: GET `/api/alerts`

الفكرة: 

1) اقرأ company id من header `X-Company-ID`.
2) ابحث هل يوجد ملف cache جاهز في output؟
3) إذا موجود ولم يُطلب refresh، أعده.
4) إذا غير موجود أو refresh=true، شغّل alert engine لتوليد جديد.

**لماذا cache؟ (Design Choice)**

- توليد alerts قد يقرأ ملفات كثيرة ويحسب أشياء.
- caching يقلل وقت الاستجابة.

**بدائل cache:**

1) حفظ alerts في SQLite.
2) حفظها في Redis.
3) توليدها في background job.

---

### (D) ملف Pipeline: `src/schema_resolver.py` (فكرة “Semantic Fields”)

**المشكلة التي يحلها هذا الملف:**

غالبًا CSV تأتي بأسماء أعمدة مختلفة.

مثال:

- شركة A تسمي عمود التاريخ: `OrderDate`
- شركة B تسميه: `Date`
- شركة C تسميه: `sale_date`

لو كتبنا pipeline بفرض “OrderDate” فقط، سيكسر مع الشركات الأخرى.

الحل: نعرّف “المعنى” كـ SemanticField:

- ORDER_DATE
- CUSTOMER_ID
- TOTAL_PRICE

ثم نكتب قائمة alias لكل واحد.

**Design Choice:**

- هذا يجعل النظام “أكثر SaaS-ready” لأنك لا تتحكم في مخطط العميل.

---

### (E) ملف Pipeline: `src/pipeline_controller.py` (Single Source of Truth)

هذا الملف يتحكم في:

- ما هي الملفات الأساسية (canonical inputs)
- ما هي النتائج المشتقة (derived outputs)
- ترتيب التنفيذ
- تنظيف outputs القديمة
- تنفيذ pipeline بشكل “deterministic”

**لماذا Single Source of Truth؟**

لأن المشاريع الكبيرة إذا عرّفت أسماء الملفات في 5 أماكن مختلفة، ستقع في:

- تناقضات (مثلاً: ملف اسمه `alerts.json` في مكان و `*_alerts.json` في مكان آخر)
- صعوبة debug

إذن تُعرّفها في مكان واحد.

---

## 5️⃣ شرح المفاهيم النظرية (تعريف + مثال خارج المشروع + ربط بالمشروع)

سأعرّف مجموعة مفاهيم رئيسية مرتبطة مباشرة بما رأيناه.

### 1) API (Application Programming Interface)

**التعريف:**

API هو “واجهة” بين برنامجين.

**مثال خارج المشروع:**

تخيل آلة بيع (Vending machine):

- أنت تضغط زر رقم 5.
- الآلة تعطيك منتج.

الزر هنا هو API.

**ربط بالمشروع:**

- Frontend لا يقرأ الملفات.
- Frontend يضغط “زر” اسمه `/api/alerts`.
- Backend يرجع JSON.

### 2) REST

**التعريف:**

REST هو أسلوب تصميم APIs عبر HTTP، يعتمد غالبًا على:

- GET لجلب بيانات
- POST لإرسال/إنشاء
- PUT/PATCH للتعديل
- DELETE للحذف

**ربط بالمشروع:**

- `/api/alerts` يستخدم GET.
- `/api/alerts/generate` يستخدم POST.

### 3) JWT (JSON Web Token)

**التعريف:**

JWT هو token يحتوي معلومات (claims) موقّعة.
الهدف: المصادقة (Authentication) بدون جلسات server-side.

**مثال خارج المشروع:**

بدل أن يحتفظ الأستاذ بورقة لكل طالب (session)، يعطي الطالب بطاقة موقعة.
كل مرة يدخل، يري البطاقة.

**ربط بالمشروع:**

- `AuthContext.tsx` يخزّن `auth_token` في localStorage.
- `DataContext.tsx` يرسل `Authorization: Bearer <token>`.

### 4) Hook (React Hook)

**التعريف:**

Hook هي دالة في React تبدأ بـ `use...` تسمح لك باستخدام features داخل functional components.

**مثال:**

- `useState` لتخزين متغير داخل component.
- `useEffect` لتشغيل كود عند mounting.

**ربط بالمشروع:**

- `AlertsPanel` يستخدم `useEffect` لجلب alerts.
- `DataContext` يستخدم `useEffect` لجلب كل البيانات عند login.

### 5) Async / Await

**التعريف:**

عندما تستدعي network request، لا تريد تجميد الواجهة.
Async يسمح بانتظار نتيجة بدون إيقاف الـ UI.

**مثال خارج المشروع:**

أنت تطلب بيتزا. لا تقف بلا حركة حتى تصل، بل تكمل عملك.

**ربط بالمشروع:**

- `fetchAlerts` هي async.
- `fetchData` في DataContext هي async.

---

## 6️⃣ التحسينات والملاحظات (Code Smells + أداء + تنظيم + PFE)

### A) ملاحظة عن المشكلة التي ظهرت عندك (Failed to load alerts)

**السبب الفعلي (كما حدث عندك):**

1) في البداية لم يكن هناك proxy في Vite.
2) إذن `/api/alerts` يرجع HTML.
3) `response.json()` يفشل.
4) ظهر error: `Unexpected token '<'`.

ثم بعد إضافة proxy:

1) صار الطلب يصل للـ backend.
2) لكن endpoint كان يسبب 500 بسبب `OUTPUT_DIR` غير معرف.
3) بعد تعريف `OUTPUT_DIR` صار endpoint يرجع JSON صحيح.

### B) Code Smells محتملة

1) ملف `backend/main.py` كبير جدًا.
   - الرائحة (smell): God file.
   - تحسين: تقسيمه إلى routers/modules.

2) تنبيهات alerts في الواجهة لا تستخدم JWT.
   - قد يكون مقصودًا، لكن في SaaS حقيقي الأفضل حماية endpoint أو ربطه بالمستخدم.

3) اعتماد كبير على file outputs.
   - ممتاز للتعلم، لكن في الإنتاج: DB أو object storage أفضل.

### C) تحسينات أداء

- cache للـ heavy computations.
- background tasks لتوليد outputs.
- pagination للـ raw data.

### D) ملاحظات مهمة لمشروع تخرج (PFE)

1) اعرض “قصة المشكلة والحل” (business problem → technical solution).
2) أظهر architecture diagram واضح.
3) اشرح ما الذي يجعل مشروعك مختلفًا (Arabic-first NLP + Proactive Alerts).
4) ضع قسم Limitations صريح (مثلاً: file-based storage).
5) ضع قسم Future Work (تحويل التخزين إلى DB، تحسين auth، تحسين ML evaluation).

---

# الملاحق (Appendices)

هذه الملاحق هدفها تنفيذ مطلب “شرح سطرًا بسطر حرفيًا” لكن بطريقة منظمة: سنأخذ ملفًا واحدًا في كل ملحق، ونشرحه على أجزاء (Part 1, Part 2, …) حتى لا يضيع القارئ.

> تنبيه تربوي (بدون اختصار):
>
> ملف مثل `backend/main.py` طويل جدًا (آلاف الأسطر). شرح كل سطر حرفيًا يعني أننا سنكتب “كتابًا صغيرًا” داخل هذا الملف.
>
> لهذا سنقسم الشرح إلى أجزاء متسلسلة، وكل جزء يشرح نطاقًا محددًا من الأسطر. لا يوجد قفز أو تجاهل، فقط تقسيم حتى يكون قابلاً للقراءة.

---

## ملحق 2: شرح ملف `backend/main.py` سطرًا بسطر (Part 1)

### 0) قبل أن نقرأ أي سطر: ما وظيفة `backend/main.py`؟

هذا الملف هو **نقطة التشغيل الأساسية (Entry Point)** لتطبيق الـ Backend.

عندما تكتب في الطرفية (Terminal):

`python -m uvicorn main:app --reload --port 8000`

فهذا يعني:

1) شغّل برنامج `uvicorn` (وهو ASGI server).
2) اطلب منه أن يفتح الملف `main.py`.
3) وابحث داخله عن متغير اسمه `app`.
4) واعتبر هذا المتغير هو تطبيق FastAPI.
5) ثم ابدأ الاستماع على `http://localhost:8000`.

**لماذا نحتاج Entry Point؟ (Design Choice)**

- لأن الـ server يحتاج “عنوانًا واضحًا” ليعرف من أين يبدأ.
- هذا يجعل تشغيل النظام واضحًا: ملف واحد مسؤول عن إنشاء `app` وتعريف routes.

---

### 1) نص الكود الذي سنشرحه في هذا الجزء

في Part 1 سنشرح بالضبط الأسطر الأولى من الملف (من البداية حتى بداية نماذج المصادقة). هذا الجزء مهم لأنه يحدد:

- التعريف العام للملف.
- imports.
- إعدادات JWT.
- تحديد المسارات (BASE_DIR / DATA_DIR / OUTPUT_DIR …).
- إعداد logging.

نص الأسطر التي سنشرحها (كما هي):

```python
"""FastAPI backend for Intelligent Sales Analytics Dashboard.

Exposes data endpoints for the React frontend to consume.
Run with: uvicorn backend.main:app --reload
"""

import sys
import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import shutil
import subprocess
import hashlib

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File, Form, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

# JWT Authentication
try:
   from jose import JWTError, jwt
   JWT_ENABLED = True
except ImportError:
   JWT_ENABLED = False
   logging.warning("python-jose not installed. JWT authentication disabled.")

# Password hashing
try:
   from passlib.context import CryptContext
   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
   PASSLIB_ENABLED = True
except ImportError:
   PASSLIB_ENABLED = False
   logging.warning("passlib not installed. Using simple password verification.")

# Import Pipeline Controller - SINGLE SOURCE OF TRUTH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
try:
   from pipeline_controller import (
      orchestrate_pipeline,
      hard_reset_derived_outputs,
      detect_data_deletion,
      get_pipeline_state,
      DERIVED_OUTPUT_FILES,
      CANONICAL_INPUT_FILES,
   )
   PIPELINE_CONTROLLER_AVAILABLE = True
   logging.info("Pipeline Controller imported successfully")
except ImportError as e:
   PIPELINE_CONTROLLER_AVAILABLE = False
   logging.warning(f"Pipeline Controller not available: {e}. Using fallback implementation.")

# Rate Limiting
try:
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address
   from slowapi.errors import RateLimitExceeded
   RATE_LIMITING_ENABLED = True
except ImportError:
   RATE_LIMITING_ENABLED = False
   logging.warning("slowapi not installed. Rate limiting disabled. Install with: pip install slowapi")

# Environment Variables
try:
   from dotenv import load_dotenv
   load_dotenv()
except ImportError:
   logging.warning("python-dotenv not installed. Using default settings.")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
MODEL_PATH = BASE_DIR / "src" / "ml_lifecycle" / "model_registry" / "sales_forecast_model.pkl"
DB_PATH = DATA_DIR / "datasets.db"
PIPELINE_LOCK_PATH = DATA_DIR / ".pipeline.lock"

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
   level=logging.INFO,
   format="%(asctime)s - %(levelname)s - %(message)s",
   handlers=[
      logging.FileHandler(LOGS_DIR / "api.log", encoding="utf-8"),
      logging.StreamHandler(sys.stdout),
   ],
)
logger = logging.getLogger(__name__)

ALLOWED_DATASET_TYPES = {"sales", "customers", "reviews"}
MAX_PREVIEW_ROWS = 50

DATE_CANDIDATES = ["OrderDate", "Sale_Date", "Order_Date", "Date", "order_date"]
# IMPORTANT: Include "Price" for datasets that use Price instead of TotalPrice
REVENUE_CANDIDATES = ["TotalPrice", "Price", "Sales_Amount", "SalesAmount", "Revenue", "Sales", "Amount", "amount", "price"]
PRODUCT_CANDIDATES = ["ProductID", "Product_ID", "Product", "SKU"]
CITY_CANDIDATES = ["City", "city", "Region", "region", "Market"]

# =============================================================================
# JWT Configuration
# =============================================================================
# SECURITY: In production, JWT_SECRET_KEY MUST be set as an environment variable
# Never use the default in production - it's for development only
_default_secret = "sales-intelligence-secret-key-change-in-production-2024"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _default_secret)
if SECRET_KEY == _default_secret and os.getenv("ENVIRONMENT", "development") == "production":
   logger.critical("SECURITY ERROR: JWT_SECRET_KEY must be set in production!")
   raise RuntimeError("JWT_SECRET_KEY environment variable required in production")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security = HTTPBearer(auto_error=False)

# Demo users for testing (in production, use database)
DEMO_USERS = {
   "admin@acme.com": {
      "id": "1",
      "email": "admin@acme.com",
      "name": "Admin User",
      "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.OQbWIEPOZyAe9O",  # admin123
      "company": "Acme Corp",
      "company_id": 1,
      "role": "admin"
   },
   "analyst@acme.com": {
      "id": "2", 
      "email": "analyst@acme.com",
      "name": "Analyst User",
      "password_hash": "$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi",  # analyst123
      "company": "Acme Corp",
      "company_id": 1,
      "role": "analyst"
   }
}

# Simple password for demo (when passlib is not available)
DEMO_PASSWORDS = {
   "admin@acme.com": "admin123",
   "analyst@acme.com": "analyst123"
}
```

> مهم جدًا: لاحظ أنني وضعت الكود داخل Code Block لكي نرجع إليه سطرًا سطرًا.

---

### 2) شرح Docstring في بداية الملف (الأسطر الأولى)

السطر:

`"""FastAPI backend for Intelligent Sales Analytics Dashboard.`

**ماذا يعني؟**

- هذا يسمى **Docstring** في Python.
- Docstring هي نص يوضع في بداية ملف أو دالة أو class.
- هدفه: توثيق ما الذي يفعله الملف.

**لماذا استُعملت ثلاث علامات اقتباس؟**

- لأن Python تسمح بكتابة نص متعدد الأسطر باستخدام `""" ... """`.
- لو استخدمنا `"` فقط، سيكون النص سطر واحد فقط أو نحتاج `\n`.

السطر الثاني:

`Exposes data endpoints for the React frontend to consume.`

**المعنى:**

- “هذا الـ backend يوفر endpoints (روابط API) لكي يستهلكها الـ frontend.”
- كلمة consume هنا معناها: frontend “يستهلك” JSON الذي يرجعه backend.

السطر الثالث:

`Run with: uvicorn backend.main:app --reload`

**المعنى:**

- يخبرك كيف تشغل التطبيق.
- `uvicorn` هو خادم (server) لتطبيقات Python التي تتبع معيار ASGI.
- `backend.main:app` تعني: اذهب إلى package `backend` ثم module `main` ثم خذ المتغير `app`.
- `--reload` يعني: عندما تغيّر الكود، server يعيد التحميل تلقائيًا.

**ماذا يحدث لو حذفنا Docstring؟**

- لا يتعطل البرنامج.
- لكن تفقد التوثيق، ويصير فهم الملف أصعب.

---

### 3) شرح Imports سطرًا سطرًا (بدون تجاوز)

> قاعدة عامة مهمّة جدًا:
>
> `import` يعني: “أريد استعمال شيء ليس معرفًا في هذا الملف.”
>
> إذا لم نستورد (import) شيئًا ثم حاولنا استخدامه، سنحصل على خطأ اسمه `NameError` أو `ModuleNotFoundError`.

#### 3.1) `import sys`

**ما هو sys؟**

- مكتبة قياسية (Standard Library) تأتي مع Python.
- تعطينا وصولًا لأشياء مرتبطة بالـ interpreter نفسه.

**لماذا نحتاجه في هذا الملف؟**

- استُعمل لاحقًا في `logging.StreamHandler(sys.stdout)` حتى يكتب الـ logs إلى شاشة الطرفية.
- كما يمكن استعماله لإضافة paths مثل `sys.path.insert(...)` حتى Python يعرف أين يجد modules.

**ماذا يحدث لو حذفناه؟**

- عندما يصل الكود إلى `sys.stdout` سيعطي `NameError: name 'sys' is not defined`.

#### 3.2) `import logging`

**ما هو logging؟**

- نظام تسجيل (Logging) رسمي في Python.

**لماذا نحتاجه؟**

- بدل `print`، نستخدم logging لأن:
  - يمكن تحديد مستوى (INFO/WARNING/ERROR).
  - يمكن الكتابة إلى ملف log.
  - مفيد جدًا في debug والإنتاج.

**ماذا يحدث لو حذفناه؟**

- `logging.basicConfig(...)` سيعطي `NameError`.

#### 3.3) `import os`

**ما هو os؟**

- مكتبة قياسية للتعامل مع نظام التشغيل.

**أين استُعمل هنا؟**

- لاحقًا: `os.getenv(...)` لقراءة Environment Variables مثل `JWT_SECRET_KEY`.

**ماذا يحدث لو حذفناه؟**

- `os.getenv` سيعطي `NameError`.

#### 3.4) `import sqlite3`

**ما هو sqlite3؟**

- مكتبة قياسية للتعامل مع SQLite database.

**لماذا موجود؟**

- لأن المشروع يستخدم ملف قاعدة بيانات SQLite غالبًا لتخزين metadata.

**ماذا يحدث لو حذفناه؟**

- أي كود في `main.py` يتعامل مع SQLite سيتعطل.

#### 3.5) `from pathlib import Path`

**ما هي Path؟**

- `Path` كائن (object) يمثل مسار ملف/مجلد بطريقة نظيفة.
- بديل حديث عن التعامل مع المسارات كنصوص (strings).

**لماذا Path أفضل من string؟ (Design Choice)**

- تعطيك عمليات جاهزة: `exists()`, `mkdir()`, `parent`, `resolve()`.
- تعمل بشكل أكثر أمانًا عبر Windows/Linux.

**ماذا يحدث لو استبدلنا Path بـ strings؟**

- يمكن، لكن ستكتب كود أطول وأكثر أخطاء (مثل مشاكل \ و /).

#### 3.6) `from typing import Optional, List, Dict, Any`

**ما هو typing؟**

- هذا جزء من نظام Type Hints في Python.
- يساعد على توثيق الأنواع وتسهيل القراءة والتحليل.

**شرح كل اسم:**

- `Optional[T]`: يعني القيمة يمكن أن تكون `T` أو `None`.
- `List[T]`: قائمة عناصر من النوع `T`.
- `Dict[K, V]`: قاموس mapping من `K` إلى `V`.
- `Any`: يعني “أي نوع” (escape hatch عندما لا تعرف النوع).

**ماذا يحدث لو حذفنا typing؟**

- غالبًا البرنامج لا يتعطل مباشرة لأن Type Hints ليست مطلوبة runtime.
- لكن قد تتعطل أدوات تحليل/IDE، ويصير الكود أقل وضوحًا.


#### 3.7) `from datetime import datetime, timedelta, timezone`

**ما هي datetime؟**

- `datetime` هي مكتبة قياسية للتعامل مع الوقت والتاريخ.
- لكن لاحظ: الاسم `datetime` هنا هو **اسم class** داخل module `datetime`.

**ماذا يعني هذا الاستيراد؟**

- نحن لم نكتب `import datetime`.
- بل كتبنا: `from datetime import datetime, timedelta, timezone`.
- هذا يعني:
   - خذ `datetime` (class) وضعه مباشرة في مساحة أسماء الملف.
   - خذ `timedelta` (نوع يمثل مدة زمنية) وضعه كذلك.
   - خذ `timezone` (يمثل timezone) وضعه كذلك.

**لماذا استُعملت هذه الأشياء؟**

- `timedelta` استُعملت في JWT: لحساب مدة صلاحية token.
- `timezone` استُعملت لتحديد أن الوقت UTC.

**ماذا يحدث لو حذفناه؟**

- عند سطر مثل: `datetime.now(timezone.utc)` سيحدث `NameError` لأن `timezone` غير معرف.

**بدائل ممكنة:**

- بدل `from datetime import ...` يمكن كتابة `import datetime` ثم `datetime.datetime.now(...)`.
- هذا أكثر طولًا لكنه أحيانًا يقلل الالتباس بين اسم module واسم class.

#### 3.8) `from functools import lru_cache`

**ما هو lru_cache؟**

- هذا Decorator في Python يعمل **Caching** لنتائج دالة.
- LRU = Least Recently Used (آخر استخدام)

**لماذا قد يكون موجودًا هنا؟**

- غالبًا يوجد في هذا الملف دوال قراءة/تهيئة يمكن cache لها.
- لكن يجب الانتباه: في مشروع يتعامل مع بيانات تتغير باستمرار، الـ caching قد يسبب بيانات قديمة (stale data).

**ماذا يحدث لو حذفناه؟**

- فقط الدوال التي تستخدم `@lru_cache` ستتعطل.
- إن لم يوجد استعمال، فلن يحدث شيء.

#### 3.9) `import shutil`

**ما هو shutil؟**

- مكتبة قياسية لعمليات الملفات مثل copy, move, rmtree.

**أين يُستعمل غالبًا؟**

- عند حذف مجلدات outputs أو نسخ ملفات dataset.

#### 3.10) `import subprocess`

**ما هو subprocess؟**

- تشغيل أوامر نظام التشغيل من داخل Python.

**لماذا قد نحتاجه؟**

- لتشغيل scripts pipeline كعمليات منفصلة.

**بدائل ممكنة:**

- استدعاء الدوال مباشرة بدل تشغيل process جديد.
- لكن تشغيل process مستقل قد يكون أسهل للـ isolation.

#### 3.11) `import hashlib`

**ما هو hashlib؟**

- مكتبة قياسية لحساب hashes (مثل SHA-256).

**لماذا نحتاج hash؟**

- عادةً لتتبع تغيّر الملفات، أو إعطاء IDs ثابتة مبنية على المحتوى.

#### 3.12) `import joblib`

**ما هو joblib؟**

- مكتبة شائعة لحفظ/تحميل نماذج ML أو أشياء Python بسرعة.

**ربط بالمشروع:**

- يوجد مسار `MODEL_PATH` يشير إلى ملف `.pkl` لنموذج forecasting.

#### 3.13) `import numpy as np`

**ما هو numpy؟**

- مكتبة أساسية للحسابات العددية (arrays, matrices).

**لماذا نعمل alias `np`؟ (Design Choice)**

- هذه عادة متفق عليها في مجتمع Python.
- تقلل طول كتابة `numpy` كل مرة.

#### 3.14) `import pandas as pd`

**ما هو pandas؟**

- مكتبة لمعالجة البيانات الجدولية (DataFrame).

**لماذا alias `pd`؟**

- نفس فكرة `np`: اختصار متعارف عليه.

#### 3.15) `from fastapi import ...`

هذا الاستيراد طويل لأنه يجلب كل ما يحتاجه backend:

- `FastAPI`: class لإنشاء التطبيق.
- `HTTPException`: لرمي خطأ HTTP مثل 401/404/500.
- `Query`: لقراءة query parameters (مثل `?refresh=true`).
- `Request`: للحصول على headers وغيرها.
- `UploadFile, File, Form`: لرفع ملفات وإرسال form data.
- `Response`: للتحكم في response.
- `Depends`: نظام Dependency Injection في FastAPI.

**ماذا يحدث لو حذفنا Depends؟**

- دوال مثل `current_user: Dict = Depends(get_current_user)` ستفشل.

#### 3.16) `from fastapi.middleware.cors import CORSMiddleware`

**ما هو CORS؟**

- سياسة في المتصفح تمنع صفحة من domain/port أن تطلب من domain/port آخر بدون سماح.
- مثال: frontend على `localhost:3000` والbackend على `localhost:8000`.
- المتصفح يعتبرهما “Origins” مختلفة.

**لماذا نحتاج CORSMiddleware؟**

- حتى يسمح backend للfrontend أن يطلب منه أثناء التطوير.

#### 3.17) `from fastapi.responses import JSONResponse`

**لماذا JSONResponse؟**

- أحيانًا تريد تحديد response بشكل صريح (status + json body).

#### 3.18) `from fastapi.encoders import jsonable_encoder`

**ما وظيفة jsonable_encoder؟**

- يحوّل أشياء مثل pandas/numpy أو datetime إلى أشياء يمكن تحويلها إلى JSON.

#### 3.19) `from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials`

**الفكرة:**

- `HTTPBearer`: extractor يقرأ `Authorization: Bearer <token>`.
- `HTTPAuthorizationCredentials`: نوع يمثل القيمة المستخرجة.

#### 3.20) `from pydantic import BaseModel, EmailStr`

**ما هو Pydantic؟**

- مكتبة للتحقق من البيانات (Validation) وبناء نماذج.

**لماذا BaseModel؟**

- في FastAPI، request/response models غالبًا تكون Pydantic.

**EmailStr؟**

- نوع يفرض أن النص هو email صحيح.
- لاحظ: في جزء من هذا الملف تم استعمال `EmailStr`، لكنه قد لا يظهر في الجزء الذي شرحناه.

---

### 4) Imports داخل الملف في منتصفه (threading/time/contextmanager)

في هذا الملف يوجد `import threading` و `import time` و `from contextlib import contextmanager` لكن ليس في أعلى الملف، بل جاء بعد `init_db()`.

**هل هذا خطأ؟**

- ليس خطأ في Python.
- لكنه Design Choice: كثير من المشاريع تضع كل imports بالأعلى.

**لماذا قد يضعها المطور في الوسط؟**

- أحيانًا للفصل بين “جزء التهيئة” و “جزء أدوات التزامن”.
- أو لأنه أُضيف لاحقًا أثناء تطوير المشروع.

**ملاحظة PFE:**

- من الأفضل توحيد imports في الأعلى لتسهيل القراءة.

---

## ملحق 2: شرح `backend/main.py` سطرًا بسطر (Part 2)

في Part 2 سنشرح:

1) نماذج المصادقة (Authentication Models)
2) دوال المصادقة (verify_password/create_access_token/get_current_user)
3) قاعدة بيانات SQLite للـ datasets metadata
4) قفل التزامن (pipeline_lock)

### 1) Authentication Models (نماذج Pydantic)

في `main.py` يوجد:

```python
class LoginRequest(BaseModel):
      email: str
      password: str


class TokenResponse(BaseModel):
      access_token: str
      token_type: str = "bearer"
      user: Dict[str, Any]


class UserResponse(BaseModel):
      id: str
      email: str
      name: str
      company: str
      role: str
```

سطرًا بسطر:

#### 1.1) `class LoginRequest(BaseModel):`

- كلمة `class` تعني: تعريف نوع جديد.
- `LoginRequest` هو نموذج يمثل بيانات الدخول.
- `(BaseModel)` يعني: هذا class يرث من Pydantic BaseModel.

**لماذا BaseModel مهم؟**

- لأنه يجعل FastAPI:
   - يقرأ JSON request body.
   - يتحقق أن الحقول موجودة.
   - يعطي خطأ 422 تلقائيًا إذا data غير صحيحة.

#### 1.2) `email: str` و `password: str`

- هذه ليست “تعيين قيم” بل Type Annotations.
- معناها: نتوقع نص.

**ماذا يحدث لو أرسل المستخدم رقم بدل نص؟**

- Pydantic قد يحاول تحويله إلى نص.
- أو يرفض حسب الإعدادات.

#### 1.3) `class TokenResponse(BaseModel)`

هذا النموذج يحدد ماذا يرجع endpoint login.

- `access_token`: token نفسه.
- `token_type`: غالبًا ثابت `bearer`.

**لماذا token_type موجود؟**

- معيارًا (Convention) في OAuth2/HTTP Bearer.
- كثير من clients تتوقع هذا الشكل.

- `user: Dict[str, Any]`:
   - هذا يعني: user object بدون تحديد دقيق لحقوله.

**Design Choice:**

- استخدام `Dict[str, Any]` سريع، لكن أقل صرامة.
- بديل أفضل: `user: UserResponse`.

#### 1.4) `class UserResponse(BaseModel)`

هذا يمثل شكل بيانات المستخدم الذي نرسله للواجهة.

- لاحظ أنه لا يحتوي password.
- هذا جيد أمنيًا.

---

### 2) Authentication Helpers (دوال المساعدة)

#### 2.1) الدالة `verify_password`

النص:

```python
def verify_password(plain_password: str, hashed_password: str, email: str = None) -> bool:
      """Verify password - uses simple check for demo, bcrypt for production."""
      # Always check simple demo passwords first for reliability
      if email and email in DEMO_PASSWORDS:
            if plain_password == DEMO_PASSWORDS[email]:
                  return True
    
      # Try bcrypt verification if passlib is available
      if PASSLIB_ENABLED:
            try:
                  return pwd_context.verify(plain_password, hashed_password)
            except Exception as e:
                  logger.warning(f"Password verification failed: {e}")
    
      return False
```

سطرًا بسطر:

- `def verify_password(...)-> bool:`
   - `def` تعريف دالة.
   - `plain_password` كلمة مرور نصية.
   - `hashed_password` كلمة مرور مخزنة بشكل hash.
   - `email: str = None` يعني parameter اختياري.
   - `-> bool` يعني الدالة ترجع True أو False.

- docstring: تقول أن هناك وضع demo ووضع production.

- `if email and email in DEMO_PASSWORDS:`
   - هنا يفحص: هل email تم تمريره؟ وهل هو ضمن قائمة demo passwords؟

- `if plain_password == DEMO_PASSWORDS[email]: return True`
   - إذا تطابق، نعتبره صحيح.

**لماذا هذا موجود؟ (Design Choice)**

- لأن passlib قد لا يكون مثبتًا.
- ولأن المشروع يريد أن يعمل حتى بدون تعقيد إعداد bcrypt.

**ماذا يحدث لو حذفنا هذا الجزء؟**

- عند غياب passlib، لن تستطيع تسجيل الدخول لأن لا يوجد تحقق.

- `if PASSLIB_ENABLED:`
   - إذا passlib مثبت، نستخدم bcrypt verification.

- `try/except`:
   - لأنه قد يحدث خطأ (hash غير صالح، أو إعدادات bcrypt...).

- `return False` في النهاية:
   - إذا لم يتحقق أي شرط، password غير صحيح.

**بدائل ممكنة:**

1) إلزام passlib دائمًا (أفضل للإنتاج).
2) استخدام مكتبة أخرى (argon2).
3) تخزين المستخدمين في DB بدل dict.

#### 2.2) الدالة `create_access_token`

النص:

```python
def create_access_token(data: dict) -> str:
      """Create JWT access token."""
      if not JWT_ENABLED:
            # Simple fallback token
            return f"demo-token-{data.get('sub', 'unknown')}"
    
      to_encode = data.copy()
      expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
      to_encode.update({"exp": expire})
      return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

سطرًا بسطر:

- `if not JWT_ENABLED:`
   - إذا `python-jose` غير مثبت، لا يوجد JWT حقيقي.
   - إذن يرجع token بسيط نصي يبدأ بـ `demo-token-`.

**Design Choice:**

- هذا يجعل المشروع يعمل بسهولة في بيئة تعليمية.
- لكنه ليس آمنًا للإنتاج.

- `to_encode = data.copy()`
   - ننسخ dict حتى لا نعدل الأصل.

- `expire = datetime.now(timezone.utc) + timedelta(...)`
   - احسب وقت انتهاء الصلاحية.
   - `timezone.utc` يعني توقيت عالمي.

- `to_encode.update({"exp": expire})`
   - إضافة claim `exp`.
   - JWT libraries تعرف هذا الحقل.

- `jwt.encode(...)`
   - توقيع البيانات باستخدام `SECRET_KEY`.
   - والـ algorithm هو HS256.

#### 2.3) الدالة `get_current_user`

النص:

```python
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict]:
      """Extract current user from JWT token."""
      if not credentials:
            return None
    
      token = credentials.credentials
    
      # Handle demo token
      if token.startswith("demo-token-"):
            email = token.replace("demo-token-", "")
            if email in DEMO_USERS:
                  user = DEMO_USERS[email].copy()
                  user.pop("password_hash", None)
                  return user
            return None
    
      if not JWT_ENABLED:
            return None
    
      try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email and email in DEMO_USERS:
                  user = DEMO_USERS[email].copy()
                  user.pop("password_hash", None)
                  return user
      except JWTError:
            pass
    
      return None
```

شرح مفصل:

- `credentials: HTTPAuthorizationCredentials = Depends(security)`
   - هذا سطر “مهم جدًا” لأنه يشرح Dependency Injection.
   - `security = HTTPBearer(auto_error=False)`.
   - `Depends(security)` يعني: FastAPI سيشغل extractor `security` قبل استدعاء هذه الدالة.
   - وإذا وجد header `Authorization`, سيملأ `credentials`.

- `if not credentials: return None`
   - إذا لا يوجد Authorization header، لا يوجد مستخدم.

- `token = credentials.credentials`
   - هذا يسحب النص الفعلي للـ token.

- `if token.startswith("demo-token-"):`
   - دعم demo token.
   - يستخرج email.

- `user.pop("password_hash", None)`
   - إزالة password_hash قبل إرجاع user.
   - لماذا؟ لأننا لا نريد تسريب hash حتى لو كان demo.

- `if not JWT_ENABLED: return None`
   - إذا JWT library غير موجودة ولا token demo، لا نستطيع decode token.

- `payload = jwt.decode(...)`
   - فك التوقيع والتحقق من صحة token.
   - إذا فشل، سيرمي JWTError.

- `email = payload.get("sub")`
   - claim `sub` عادة يمثل subject (هوية المستخدم).

- ثم نفس المنطق: إذا email موجود ضمن DEMO_USERS نعيد user.

**ماذا يحدث لو تغيّرنا وصرنا نخزن المستخدمين في DB؟**

- هذه الدالة يجب أن تبحث في DB بدل dict.
- هذا تطوير منطقي للـ PFE.

---

### 3) SQLite metadata: `get_db_connection`, `init_db`, `init_db()`

هنا الهدف هو إنشاء جدول `datasets` إذا لم يكن موجودًا.

#### 3.1) `def get_db_connection():`

- تفتح اتصال SQLite بملف `DB_PATH`.
- `row_factory = sqlite3.Row` يجعل النتائج تُقرأ كصفوف يمكن الوصول لها بالأسماء.

#### 3.2) `def init_db():`

- تنفذ SQL لإنشاء جدول.

**لماذا `CREATE TABLE IF NOT EXISTS`؟**

- حتى لا ينهار البرنامج إذا الجدول موجود.

#### 3.3) `init_db()` مباشرة

- هذا يعني: عند import للملف، سيتم إنشاء الجدول.

**Design Choice:**

- سهل، لكنه يجعل import يقوم بعمل side-effect.
- بديل: تشغيل init عند startup event في FastAPI.

---

### 4) قفل التزامن pipeline_lock (Concurrency)

هذا جزء مهم جدًا لأن المشروع يتعامل مع ملفات.
وعندما تتعامل مع ملفات، قد يحدث:

- مستخدم يرفع ملف جديد بينما pipeline يعمل.
- ملف outputs يتم حذفه بينما endpoint يحاول قراءته.

لهذا تم استخدام lock:

- `_pipeline_lock = threading.Lock()`
- `pipeline_lock_timeout = 120`

ثم دالة contextmanager:

`@contextmanager def pipeline_lock(operation: str = "pipeline"):`

**ما معنى contextmanager؟**

- يسمح لك بكتابة:
   - `with pipeline_lock("upload"):`
   - ثم كل ما داخل with يكون محمي.

**لماذا هذا Design Choice جيد؟**

- يمنع race conditions في نفس process.

**ماذا لا يحل؟**

- إذا شغّلت عدة processes للـ uvicorn (مثلاً workers متعددة)، threading.Lock لا يكفي.

**البدائل التي ذكرها الكود:**

- Redis distributed lock
- PostgreSQL advisory locks
- File-based locking

> ممتاز كـ PFE: هذا يبين أنك تفكر في concurrency.

---

## ملحق 2: شرح `backend/main.py` سطرًا بسطر (Part 3)

في Part 3 سنشرح:

1) إنشاء تطبيق FastAPI (`app = FastAPI(...)`)
2) Rate limiting (slowapi)
3) CORS Middleware
4) Authentication Endpoints (`/api/auth/login`, `/api/auth/me`, `/api/auth/verify`)

### 1) إنشاء التطبيق: `app = FastAPI(...)`

النص:

```python
app = FastAPI(
      title="Sales Analytics API",
      description="Backend API for Intelligent Sales Analytics Dashboard",
      version="1.0.0",
)
```

شرح:

- `FastAPI(...)` ينشئ التطبيق.
- `title/description/version` تستخدم في Swagger docs.

**ماذا يحدث لو حذفنا هذه الحقول؟**

- التطبيق يعمل.
- لكن صفحة `/docs` ستكون أقل وصفًا.

### 2) Rate Limiting (slowapi)

النص:

```python
if RATE_LIMITING_ENABLED:
      limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])
      app.state.limiter = limiter
      app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
      logger.info("Rate limiting enabled: 100 requests/hour default")
else:
      limiter = None
      logger.warning("Rate limiting is DISABLED - not recommended for production")
```

سطرًا بسطر:

- `if RATE_LIMITING_ENABLED:`
   - هذا المتغير يتحدد إذا slowapi موجود أو لا.

- `Limiter(key_func=get_remote_address, default_limits=["100/hour"])`
   - Limiter يحتاج key لتمييز المستخدم.
   - هنا key هو IP address.
   - والحد الافتراضي 100 طلب بالساعة.

- `app.state.limiter = limiter`
   - نخزن limiter داخل `state`.

- `add_exception_handler`:
   - عندما يتجاوز المستخدم الحد، سيحدث RateLimitExceeded.
   - نحدد handler يعيد response مناسب.

**Design Choice:**

- حماية بسيطة ضد spam.
- في PFE: نقطة قوة لأنها Security/Resilience.

### 3) CORS Middleware

النص:

```python
ALLOWED_ORIGINS = os.getenv(
      "CORS_ORIGINS",
      (
            "http://localhost:5173,http://localhost:3000,http://localhost:3001,http://localhost:3002," \
            "http://127.0.0.1:5173,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002"
      ),
).split(",")
ALLOWED_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX", r"http://(localhost|127\.0\.0\.1):\d{2,5}")

app.add_middleware(
      CORSMiddleware,
      allow_origins=ALLOWED_ORIGINS,
      allow_origin_regex=ALLOWED_ORIGIN_REGEX,
      allow_credentials=True,
      allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
      allow_headers=["*"],
      max_age=3600,
)
```

شرح:

- `os.getenv("CORS_ORIGINS", default).split(",")`
   - اقرأ env var.
   - إذا غير موجود، استعمل default (قائمة ports محلية).
   - ثم split لتحويلها إلى list.

**لماذا default يحتوي 5173 و3000؟**

- لأن Vite غالبًا يستخدم 5173.
- لكن هذا المشروع شغل Vite على 3000.
- فتم السماح بالاثنين.

- `allow_origin_regex`:
   - يسمح لأي port محلي ضمن regex.
   - هذا يقلل مشاكل “CORS flakiness” أثناء التطوير.

**ماذا يحدث لو لم نضف CORS؟**

- المتصفح سيمنع طلبات frontend إلى backend.
- وسترى خطأ CORS في console.

### 4) Authentication Endpoints

#### 4.1) POST `/api/auth/login`

النص:

```python
@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
      email = request.email.lower().strip()
      password = request.password
      if email not in DEMO_USERS:
            raise HTTPException(status_code=401, detail="Invalid email or password")
      user_data = DEMO_USERS[email]
      if not verify_password(password, user_data["password_hash"], email):
            raise HTTPException(status_code=401, detail="Invalid email or password")
      access_token = create_access_token(data={"sub": email})
      user_response = {
            "id": user_data["id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "company": user_data["company"],
            "role": user_data["role"]
      }
      return TokenResponse(access_token=access_token, token_type="bearer", user=user_response)
```

شرح سطرًا بسطر:

- `@app.post(...)`
   - decorator يربط الدالة بـ route.
   - method POST لأننا نرسل بيانات حساسة (email/password) في body.

- `response_model=TokenResponse`
   - FastAPI سيجبر شكل الرد أن يطابق TokenResponse.

- `async def login(...):`
   - async لأن الدالة قد تنتظر عمليات IO.

- `email = request.email.lower().strip()`
   - lower: لتجنب اختلاف الحالة.
   - strip: لإزالة مسافات.

- `if email not in DEMO_USERS: raise HTTPException(401, ...)`
   - إذا المستخدم غير موجود، نرفض.

- `verify_password(...)`
   - تحقق من كلمة المرور.

- `create_access_token(data={"sub": email})`
   - create token.

- `user_response = {...}`
   - جهّز كائن المستخدم بدون password.

**لماذا نعيد نفس رسالة الخطأ لكل حالة؟**

- “Invalid email or password” سواء email خطأ أو password خطأ.
- هذا Design Choice أمني: لا نريد كشف هل email موجود أم لا.

#### 4.2) GET `/api/auth/me`

- يعتمد على `Depends(get_current_user)`.
- إذا لم يوجد مستخدم، يرجع 401.

#### 4.3) GET `/api/auth/verify`

- يفحص صلاحية token.
- يعيد `{valid: true, user: ...}` إذا ok.

> في Part 4 سنكمل شرح نماذج البيانات (Pydantic Models لباقي endpoints) ثم Data Loading Helpers ثم endpoints الأساسية مثل datasets/kpis/segmentation، ثم سنصل إلى intelligence endpoints مثل `/api/alerts`.




---

## ملحق 2: شرح `backend/main.py` سطرًا بسطر (Part 4)

في Part 4 سننتقل من “طبقة الـ API العامة (Auth/CORS/RateLimit)” إلى “طبقة تشغيل البيانات” التي تجعل الـ API فعليًا قادرًا على:

1) تعريف شكل الداتا التي يرجعها الـ API (Pydantic Models) لبعض التحليلات والـ datasets.
2) تحميل البيانات من القرص (CSV/ملفات outputs) إلى الذاكرة عند الحاجة.
3) منع “stale data” (بيانات قديمة) عبر دوال reset + reload.
4) تجهيز Hooks تساعد في تشغيل pipelines بعد upload/replace.

> ملاحظة تربوية مهمة: هذا الملف فيه فلسفتان متداخلتان:
>
> - فلسفة “in-memory globals” (df/forecast_df/…) لتحسين الأداء.
> - وفلسفة “always read fresh from disk” في بعض endpoints الحساسة (مثل segmentation/sentiment/recommendations) حتى لا تتأثر بالحذف/التحديث.
>
> لذلك ستجد أحيانًا الكود يقول: “NEVER CACHED” لكنه مازال يستعمل globals. الفكرة المقصودة: “لا نعتمد على cache كمرجع وحيد” بل نعطي أولوية للقرص أو نُعيد التحميل باستمرار.

---

### 1) نماذج البيانات (Pydantic Models) — لماذا مهمة؟

أمثلة من النص:

```python
class SentimentDetail(BaseModel):
   label: str
   count: int
   percentage: float

class SentimentAnalysisResponse(BaseModel):
   total_reviews: int
   sentiment_breakdown: List[SentimentDetail]
   top_keywords: List[str]
   last_analyzed: Optional[str] = None
   data_source: str = "sentiment_results.csv"

class DatasetMeta(BaseModel):
   id: int
   company_id: str
   dataset_type: str
   file_name: str
   row_count: int
   uploaded_at: str
   is_active: bool

class DatasetPreview(BaseModel):
   id: int
   file_name: str
   dataset_type: str
   uploaded_at: str
   row_count: int
   columns: List[str]
   rows: List[Dict[str, Any]]
```

شرح الفكرة “سطرًا بسطر” على شكل مبادئ:

- `BaseModel`:
   - هذا من Pydantic.
   - الهدف: يفرض شكل JSON الذي يخرج من API أو يدخل له.

- لماذا هذا مهم جدًا؟
   - لأن React (الـ frontend) يبني UI على أساس شكل ثابت.
   - إذا تغيّر الشكل بلا قصد (مثل إضافة field أو تغيير الاسم)، تحصل مشاكل.

- `SentimentDetail`:
   - نموذج صغير يمثل عنصر واحد: label/count/percentage.
   - لاحظ: `percentage` float، يعني لازم نُرجع رقمًا جاهزًا للعرض.

- `SentimentAnalysisResponse`:
   - هذا هو wrapper للنتيجة الكاملة.
   - `sentiment_breakdown: List[SentimentDetail]` يعني مصفوفة من تفاصيل.
   - `last_analyzed: Optional[str]` قد تكون None إذا ما عندنا ملف.

- `data_source: str = "sentiment_results.csv"`:
   - Default يوضح مصدر الداتا.
   - هذا مفيد جدًا للتصحيح debugging: “من أين جاءت النتائج؟”.

- `DatasetMeta`:
   - هذا نموذج metadata لسجلات جدول SQLite “datasets”.
   - مهم لأنه يتيح multi-tenant: `company_id` جزء من الهوية.

- `DatasetPreview`:
   - هذا نموذج خاص بميزة preview.
   - `columns` + `rows` يعني الواجهة تقدر ترسم table مباشرة.

**بدائل Pydantic Models:**

- يمكنك الاستغناء عنها وإرجاع dict عادي.
- لكن تخسر validation + docs + typing.

---

### 2) Global DataFrames — لماذا موجودة أصلًا؟

النص:

```python
df = None
forecast_df = None
sentiment_df = None
recommendation_df = None
model = None
data_last_modified = None
```

شرح:

- هذه متغيرات global (على مستوى الملف).
- استخدامها يعطي ميزتين:
   1) أداء أسرع: بدل قراءة CSV كل طلب.
   2) نقطة مركزية لمعرفة “هل البيانات موجودة؟”.

لكن لماذا هذا قد يكون خطير؟

- لأن أي upload/delete يغير الملفات على القرص.
- إذا نسيت تُحدّث globals، سيبقى الـ API يرجع data قديمة.

ولهذا تم بناء دالتين أساسيتين:

- `clear_all_caches_and_reset()`
- `reload_all_data_from_disk()`

---

### 3) دالة `clear_all_caches_and_reset()` — “زر Reset شامل”

النص:

```python
def clear_all_caches_and_reset():
   global df, forecast_df, sentiment_df, recommendation_df, model, data_last_modified
   ...
   df = None
   forecast_df = None
   sentiment_df = None
   recommendation_df = None
   model = None
   data_last_modified = None
```

شرح سطرًا بسطر:

- `def clear_all_caches_and_reset():`
   - دالة بدون arguments.
   - معناها: القرار “شامل” وليس متعلقًا بـ company واحدة.

- `global df, forecast_df, ...`:
   - بدون global، أي assignment داخل الدالة سينشئ متغيرات محلية.
   - وهذا خطأ شائع جدًا في Python.

- `df = None` وغيرها:
   - نحن نعلن رسميًا: “لا يوجد أي بيانات في الذاكرة الآن”.

**لماذا None وليس DataFrame فارغ؟**

- None يوضح “لم يتم تحميل شيء”.
- DataFrame فارغ قد يعني “تم تحميل شيء لكنه بلا نتائج” وهذا معنى مختلف.

**متى يجب استخدام هذه الدالة؟**

كما يقول الـ docstring:

- بعد delete
- قبل upload pipeline
- بعد pipeline

هذه فلسفة “No stale data”.

---

### 4) دالة `reload_all_data_from_disk()` — “اجلب كل شيء من CSV إلى الذاكرة”

هذه الدالة كبيرة لكنها منطقية جدًا إذا قرأتها كخطوات.

#### 4.1) status dict

النص:

```python
status = {
   "cleaned_dataset": False,
   "forecast": False,
   "sentiment": False,
   "recommendations": False,
   "model": False
}
```

الفكرة:

- بدل أن ترجع True/False فقط، ترجع تفاصيل.
- هذا مفيد جدًا للواجهة أو للـ logs.

#### 4.2) data_last_modified

النص:

```python
data_last_modified = datetime.now(timezone.utc)
```

شرح:

- هذا timestamp “متى آخر مرة عملنا reload”.
- الواجهة قد تعرض “آخر تحديث”.

#### 4.3) تحميل sales data من أكثر من ملف ممكن

النص:

```python
possible_data_files = [
   DATA_DIR / "cleaned_dataset.csv",
   DATA_DIR / "sales.csv",
   DATA_DIR / "merged_data.csv",
]
```

شرح:

- هذا design choice عملي: لأن الـ pipeline قد ينتج ملفات مختلفة حسب المرحلة.
- في بعض المشاريع يكون اسم واحد “canonical”، لكن هنا يوجد legacy paths.

ثم:

```python
for data_path in possible_data_files:
   if data_path.exists():
      df = pd.read_csv(data_path)
      ...
```

- يبحث أول ملف موجود.
- يقرأه.
- ثم يحاول “تطبيع” اسم عمود التاريخ إلى `OrderDate`.

#### 4.4) Auto-detect date column

النص:

```python
date_cols = ["OrderDate", "Sale_Date", "Order_Date", "Date", "order_date"]
date_col = next((c for c in date_cols if c in df.columns), None)
if date_col:
   df = df.rename(columns={date_col: "OrderDate"})
   df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
```

شرح:

- `next((...), None)`:
   - يعطي أول عمود موجود من القائمة.
   - إذا لا يوجد، يرجع None.

- `pd.to_datetime(..., errors="coerce")`:
   - أي قيمة لا يمكن تحويلها تصبح NaT بدل أن يرمي Exception.

**لماذا هذا مهم؟**

- لأن ملفات العملاء تختلف في naming.
- نحن نريد endpoint ثابت لا يتعطل بسبب اسم عمود مختلف.

#### 4.5) تحميل forecast

نفس الفكرة: يبحث عن ملف من عدة احتمالات.

#### 4.6) تحميل sentiment + recommendations

- يقرأ `sentiment_results.csv` و`product_recommendations.csv` إن وُجدت.
- وإذا فشل القراءة يضع None ويكمل.

#### 4.7) تحميل model

النص:

```python
if MODEL_PATH.exists():
   model = joblib.load(MODEL_PATH)
```

شرح:

- هذا يعني يوجد نموذج محفوظ على القرص.
- `joblib` شائع جدًا لحفظ موديلات scikit-learn.

---

### 5) Startup event — لماذا نعمل reload عند تشغيل السيرفر؟

النص:

```python
@app.on_event("startup")
def load_data():
   reload_all_data_from_disk()
```

شرح:

- عندما يعمل Uvicorn ويبدأ FastAPI، يتم استدعاء هذا event.
- الهدف: السيرفر يبدأ وهو “جاهز” بدل أن ينتظر أول طلب.

**ماذا لو حذفنا هذا؟**

- التطبيق يعمل.
- لكن أول طلب قد يواجه df = None ويعطي degraded أو 503.

---

### 6) `require_company_id()` — حجر أساس الـ multi-tenant

النص:

```python
def require_company_id(request: Request) -> str:
   company_id = request.headers.get("X-Company-ID")
   if not company_id:
      raise HTTPException(status_code=400, detail="Missing X-Company-ID header")
   return company_id
```

شرح:

- المشروع يميز الشركة من header.
- إذا لم ترسل header، لا يمكن تحديد أي dataset نشغل عليه التحليلات.

**لماذا 400 وليس 401؟**

- 401 معناها “غير مصرح” (auth).
- هنا المشكلة ليست auth بل “missing required input”.

**بدائل تصميمية:**

- تعتمد company_id من token نفسه (أفضل أمنيًا).
- أو من subdomain (company1.example.com).
- أو من path (`/api/{company_id}/kpis`).

---

### 7) Trigger helpers — تشغيل pipeline بشكل متحكم

هنا لدينا دالتان:

- `trigger_recommendation_pipeline(sales_file_path)`
- `trigger_sentiment_pipeline(reviews_file_path)`

#### 7.1) `trigger_recommendation_pipeline`

أهم أفكاره:

- يقرأ sales CSV.
- يتحقق من وجود `OrderID`.
- يفتش عن عمود المنتج من عدة احتمالات (`ProductID`, `SKU`, …).
- يفحص إذا عندنا orders تحتوي أكثر من منتج.

**لماذا شرط multi-product مهم؟**

- Apriori يحتاج “سلة مشتريات” فيها أكثر من عنصر.
- إذا كل Order فيه منتج واحد، لا توجد Association Rules.

ثم يعمل:

```python
result = subprocess.run(
   [sys.executable, str(BASE_DIR / "src" / "05_recommendation.py")],
   ...
)
```

شرح:

- يطلق سكربت ML كعملية مستقلة.
- `sys.executable` يضمن استعمال نفس Python environment.
- `timeout=120` حتى لا يعلق السيرفر بلا نهاية.

بعد النجاح:

- يعيد تحميل `recommendation_df` global من الملف الناتج.

#### 7.2) `trigger_sentiment_pipeline`

فكرته مشابهة:

- يفتش عن عمود النص (`ReviewText`, `comment`, …).
- يمنع تشغيل pipeline إذا كل النصوص فارغة.
- ثم يشغّل `06_sentiment.py` عبر subprocess.

> في Part 5 سنشرح “المحرك الأساسي” الذي يستدعي هذه triggers: وهو trigger_pipeline + endpoints الخاصة بالرفع والاستبدال.


---

## ملحق 2: شرح `backend/main.py` سطرًا بسطر (Part 5)

في Part 5 سندخل في “قلب الـ backend الإنتاجي” لهذا المشروع:

1) trigger_pipeline (Single Source of Truth مع pipeline_controller)
2) تحميل active datasets per company
3) Dataset endpoints: upload/replace/preview/delete
4) لماذا نحتاج SQLite metadata أصلًا

---

### 1) `trigger_pipeline(...)` — نقطة مركزية للأتمتة

النص يبدأ بـ docstring واضح:

- “Hook for automation workflows”
- “SINGLE SOURCE OF TRUTH: Uses pipeline_controller.orchestrate_pipeline()”

ثم:

```python
if PIPELINE_CONTROLLER_AVAILABLE:
   result = orchestrate_pipeline(dataset_type, action, file_path)
   ...
   reload_all_data_from_disk()
   return
```

شرح:

- إذا ملف `src/pipeline_controller.py` موجود وقابل للاستيراد، نستخدمه.
- هذا أفضل من تنفيذ logic داخل main.py.
- وبعد التنفيذ نعمل reload حتى globals تتحدث.

إذا فشل الاستيراد أو التنفيذ:

- يوجد FALLBACK.

**لماذا وجود FALLBACK فكرة جيدة؟**

- أثناء التطوير/العرض قد لا تكون كل dependencies جاهزة.
- FALLBACK يجعل النظام “يشتغل” ولو بقدرات أقل.

---

### 2) `load_active_sales_df(company_id)` — كيف نقرر أي ملف نقرأ؟

النص:

```python
if company_id:
   active = get_active_dataset(company_id, "sales")
else:
   active = get_latest_active_dataset("sales")
```

شرح:

- إذا عندنا company_id: نقرأ آخر sales dataset active لهذه الشركة.
- إذا لا: نأخذ آخر active dataset لأي شركة (سلوك demo/legacy).

ثم:

```python
if active and Path(active["file_path"]).exists():
   return pd.read_csv(Path(active["file_path"]))
```

- هذه هي “الحقيقة” في النظام multi-tenant: الملف الذي في DB.

ثم fallback:

- إذا df global موجودة، يرجعها.
- إذا لا، يبحث في `data/sales.csv` أو `cleaned_dataset.csv`.

**لماذا يوجد هذا التعقيد؟**

- لأن المشروع مر بمراحل (legacy → multi-tenant).
- فتم الحفاظ على توافق backward compatibility.

---

### 3) Dataset metadata helpers (SQLite) — لماذا لا نكتفي بالملفات؟

الدوال:

- `list_datasets(company_id)`
- `archive_existing(company_id, dataset_type)`
- `insert_dataset(...)`
- `get_dataset(...)`
- `get_active_dataset(...)`
- `get_latest_active_dataset(dataset_type)`
- `delete_dataset(...)`

شرح الفكرة:

- الملفات على القرص وحدها لا تعطيك:
   - تاريخ الرفع
   - أي ملف active
   - multi-tenant clean separation
   - soft delete

لذلك يوجد جدول SQLite `datasets`.

مثال:

```python
UPDATE datasets
SET is_active = 0
WHERE company_id = ? AND dataset_type = ? AND is_deleted = 0
```

هذه هي `archive_existing`:

- قبل إدخال dataset جديد، نعطل القديم.
- وبهذا يصبح “واحد فقط active” لكل (company_id, dataset_type).

---

### 4) Endpoint: GET `/api/datasets`

النص:

```python
@app.get("/api/datasets", response_model=List[DatasetMeta], tags=["Datasets"])
def list_company_datasets(request: Request):
   company_id = require_company_id(request)
   return list_datasets(company_id)
```

شرح سطرًا بسطر:

- `response_model=List[DatasetMeta]`:
   - يرجع قائمة datasets.

- `require_company_id(request)`:
   - يمنع أن أي شخص يرى datasets شركة أخرى.

---

### 5) Endpoint: POST `/api/datasets/upload`

هذا endpoint هو “الأكثر أهمية” لأن منه تبدأ كل التحليلات.

النص (أجزاء):

```python
dataset_type: str = Form(...)
file: UploadFile = File(...)
```

شرح:

- هذا upload من نوع multipart/form-data.
- `python-multipart` ضروري.

ثم:

```python
with pipeline_lock(f"upload-{dataset_type}-{company_id}"):
```

شرح:

- يمنع تزامن Uploadين لنفس الشركة في نفس اللحظة.
- هذا يحمي من race conditions.

ثم يقوم بـ:

- `ensure_company_dir(company_id, dataset_type)` لإنشاء مجلد الشركة.
- بناء اسم آمن `safe_name`.
- إضافة timestamp لتجنب overwrite.
- حفظ الملف.

#### 5.1) Normalization للـ sales

إذا dataset_type == "sales"، الكود يحاول:

- قراءة CSV
- استدعاء `normalize_sales_dataframe(raw_df)`
- بناء DataFrame canonical بأعمدة ثابتة:
   - `OrderID`, `OrderDate`, `TotalPrice`, `ProductID`, `City`

هذه نقطة “احترافية جدًا” لأن downstream scripts عادة تتوقع أعمدة ثابتة.

ثم:

- `archive_existing(...)`
- `insert_dataset(...)`
- `trigger_pipeline(...)`

يعني: upload → تسجيل → تشغيل pipeline.

---

### 6) Endpoint: POST `/api/datasets/{dataset_id}/replace`

يشبه upload لكن مع:

- `dataset_id` يجب أن يكون موجودًا.
- يستخرج dataset_type من record الحالي.
- يرفع ملف جديد ويجعله active.

مهم هنا أنه يستخدم normalization أيضًا.

---

### 7) Endpoint: DELETE `/api/datasets/{dataset_id}`

هذا endpoint يطبق “Enterprise behavior”: حذف dataset ليس حذف ملف فقط.

النص يشرح ذلك مباشرة:

- “Deletes ALL derived ML outputs”
- “Resets in-memory DataFrames”
- “APIs will return 204 until new data is uploaded”

التنفيذ:

1) soft delete في SQLite: `delete_dataset(dataset_id, company_id)`
2) حذف الملف الخام `Path(current["file_path"]).unlink(...)`
3) تشغيل cascade deletion: `cascade_delete_derived_files(dataset_type)`

> في Part 6 سنشرح cascade_delete_derived_files بالتفصيل لأنه مرتبط مباشرة بمفهوم “no stale analytics”.

---

### 8) Endpoint: GET `/api/datasets/{dataset_id}/preview`

فكرة preview:

- قراءة أول rows + columns
- إرجاعها وفق `DatasetPreview`

ويوجد error handling واضح:

- إذا الملف ناقص: 404
- إذا preview فشل: 500


---

## ملحق 2: شرح `backend/main.py` سطرًا بسطر (Part 6)

في Part 6 سنغطي ثلاثة محاور مترابطة:

1) Cascading deletion (حذف النتائج المشتقة بالكامل)
2) Analytics endpoints (segmentation/kpis/monthly-sales/top-products/top-cities/sentiment/recommendations)
3) Intelligence endpoints وعلى رأسها `/api/alerts` وربطها بالمشكلة التي حصلت سابقًا (HTML بدل JSON + خطأ OUTPUT_DIR)

---

### 1) Cascading deletion — لماذا هذا ضروري؟

الفكرة الأساسية:

- إذا حذفنا sales.csv مثلًا، لا معنى أن يبقى `rfm_table.csv` أو `product_recommendations.csv`.
- بقاء هذه الملفات يعني dashboard قد يعرض نتائج غير مرتبطة بالبيانات الحالية.

لهذا الكود يفرض “hard reset”.

#### 1.1) Single Source of Truth (المفضل)

النص:

```python
if PIPELINE_CONTROLLER_AVAILABLE:
   result = detect_data_deletion(dataset_type)
   clear_all_caches_and_reset()
   return {...}
```

شرح:

- `detect_data_deletion` موجودة في `pipeline_controller`.
- هي المكان الصحيح لتعريف “ماذا نحذف؟” بدل تكرار القائمة في أكثر من ملف.

#### 1.2) FALLBACK inline implementation

إذا لم يتوفر pipeline_controller، ينفّذ خطوات واضحة:

**Step 1:**

- `clear_all_caches_and_reset()`

**Step 2:**

- حلقة على `DERIVED_ML_FILES` وحذفها من `DATA_DIR`.

**Step 3:**

- حذف الملف canonical المرتبط بـ dataset_type:
   - sales → `sales.csv`
   - reviews → `customer_reviews.csv`
   - customers → `customers.csv`

**Step 4/5:**

- تنظيف `output/` و `output/plots/` (خاصة صور png).

**Step 6:**

- تنظيف `src/ml_lifecycle/model_registry/` (إذا موجود).

في النهاية يرجع dict يحتوي:

- `deleted_files`
- `errors`
- `total_deleted`
- `memory_cleared`

هذا الرد مفيد جدًا للواجهة في صفحة Settings أو Admin.

---

### 2) Analytics endpoints — نمط “اقرأ من القرص مباشرة”

لاحظ أنك ستجد تكرار جملة:

- “CRITICAL: Always reads FRESH from disk, NEVER from cached globals.”

#### 2.1) Segmentation/RFM

يوجد دالة داخلية `_get_rfm_segmentation_data(request)`.

الفكرة:

- تبحث عن `data/rfm_table.csv`.
- إذا غير موجود: ترجع `Response(status_code=204)`.
- إذا موجود: تقرأه وتحسب counts لكل Segment.

**لماذا 204؟**

- 204 معناها “لا يوجد محتوى”.
- أفضل من 404 أحيانًا لأن endpoint نفسه موجود، لكن البيانات غير جاهزة.

#### 2.2) KPIs

endpoint `/api/kpis` يعمل:

- `sales_df = normalize_sales_dataframe(load_active_sales_df(company_id))`
- يبني فترة current/previous.
- يحسب revenue/orders/aov.
- يحسب percentage changes.

ملاحظة تربوية:

- `calc_pct_change` ترجع None إذا previous = 0.
- هذا يمنع division by zero.

#### 2.3) Monthly sales + Forecast

endpoint `/api/monthly-sales`:

- يحسب actual شهريًا via `groupby(Grouper(freq="MS"))`.
- ثم يحمل forecast من disk عبر `load_forecast_data()`.
- ثم يدمج الاثنين في dict ثم يحوله لـ response.

لاحظ design choice:

- forecast يتم إضافته فقط إذا قيمة forecast > 0 لتجنب قيم سلبية شاذة.

#### 2.4) Top products / Top cities

يستخدم نفس نمط:

- groupby على `__product` أو `__city`
- sum revenue + count orders
- sort desc + head(limit)

#### 2.5) Sentiment + Recommendations

يقرآن من:

- `data/sentiment_results.csv`
- `data/product_recommendations.csv`

ويرجعان 204 إذا الملفات ناقصة/فارغة.

هذا مهم جدًا بعد cascade deletion: كل هذه endpoints ستصبح 204 بدل أن تعطي بيانات قديمة.

---

### 3) Intelligence endpoints — `/api/alerts` كمثال حي

هنا نعود مباشرة للمشكلة التي بدأت منها القصة في الواجهة:

- الواجهة كانت تتوقع JSON.
- لكنها كانت تستقبل HTML (غالبًا من dev server أو مسار غير صحيح).
- وبعدها اكتشفنا أن backend كان يرجع 500 بسبب مشكلة مسار output (OUTPUT_DIR).

الآن نقرأ endpoint نفسه.

#### 3.1) GET `/api/alerts`

النص:

```python
@app.get("/api/alerts", tags=["Intelligence"])
def get_business_alerts(request: Request, refresh: bool = Query(False, description="Force regeneration of alerts")):
   company_id = request.headers.get("X-Company-ID", "Acme Corp")
   alerts_path = OUTPUT_DIR / f"{company_id}_alerts.json"
   ...
```

شرح سطرًا بسطر:

- `refresh: bool = Query(False, ...)`:
   - query parameter.
   - إذا `refresh=true` نولد alerts من جديد حتى لو cache موجود.

- `company_id = request.headers.get("X-Company-ID", "Acme Corp")`:
   - هنا يوجد Default.
   - هذا سلوك demo-friendly لكنه ليس صارم مثل `require_company_id`.

- `alerts_path = OUTPUT_DIR / f"{company_id}_alerts.json"`:
   - هذا كاش file-based.
   - الهدف: تسريع الاستجابة، لأن توليد alerts قد يكون مكلفًا.

ثم:

```python
if alerts_path.exists() and not refresh:
   alerts_data = json.load(...)
   return alerts_data
```

هذا الجزء هو سبب أن endpoint كان يفترض أن يرجع JSON دائمًا.

ثم إذا لا يوجد cache أو refresh:

- يضيف `src` إلى `sys.path`.
- يستورد `run_alert_engine`.
- ينفذه ويعيد الناتج.

**لماذا حصلت مشكلة 500 سابقًا؟**

- لأن `OUTPUT_DIR` كان مستخدمًا هنا.
- إذا لم يكن معرفًا (أو المجلد غير موجود)، سيحصل Exception.
- وهذا يترجم إلى HTTP 500.

وهذا يوضح نقطة هندسية:

- ملفات الكاش paths يجب أن تكون معرفة بوضوح وفي مكان واحد.

#### 3.2) POST `/api/alerts/generate`

هذا endpoint “يجبر” regenerate.

- مفيد للاختبار.
- أو لو عندك زر في Settings: “Rebuild alerts”.

#### 3.3) Advanced sentiment / CLV / Intelligence summary

هذه endpoints كلها تتبع نفس الفلسفة:

- اقرأ من cache داخل `output/` إن وُجد.
- وإلا شغّل سكربت داخل `src/` يولد النتائج.

والـ endpoint `intelligence-summary` يجمع “أفضل 5 alerts + highlights + recommendations” ليعطي dashboard تجربة “Proactive”.

> بهذا نكون أكملنا أهم أجزاء `backend/main.py` من ناحية: data lifecycle + deletion + analytics + alerts.




---

## ملحق 3: شرح ملف `src/pipeline_controller.py` سطرًا بسطر (Part 1)

هذا الملحق هو استكمال مباشر لما رأيناه داخل `backend/main.py` عندما تكرر المصطلح:

- **SINGLE SOURCE OF TRUTH**

في `backend/main.py` رأينا أكثر من مكان يقول:

- إذا `PIPELINE_CONTROLLER_AVAILABLE` استخدم `orchestrate_pipeline(...)` أو `detect_data_deletion(...)`.

الآن سنشرح الملف الذي يُفترض أن يكون “المصدر الوحيد” (Canonical Authority) لتشغيل الـ ML pipelines وتنظيف النتائج.

> نقطة مهمة: هذا الملف هو السبب الذي يجعل سلوك المشروع “منظم” بدل أن يكون كل endpoint يشغّل سكربتات بطريقة مختلفة.

---

### 0) ماذا يفعل هذا الملف عمليًا؟

لو أردت تبسيطه جدًا لطالب مبتدئ:

- هذا الملف هو **المُنسّق (Orchestrator)**.
- يستقبل “حدث” مثل: upload/replace/delete.
- يقرر ما الذي يجب تشغيله (أي سكربت) وبأي ترتيب.
- ويضمن قاعدة ذهبية: **لا توجد نتائج قديمة** بعد التحديث/الحذف.

---

### 1) Docstring في أعلى الملف — لماذا مكتوب بهذه الطريقة؟

النص يبدأ بـ:

```python
"""
Pipeline Controller - SINGLE SOURCE OF TRUTH for ML Pipeline Orchestration.
...
CRITICAL RULES:
- NO caching of DataFrames - always read fresh from disk
- DELETE old outputs before generating new ones
- If a module produces NO results, it MUST delete any old output files
- All state must be deterministic and reproducible
"""
```

شرح سطرًا بسطر منطقياً (ليس فقط ترجمة):

- `SINGLE SOURCE OF TRUTH`:
   - يعني: أي منطق “ماذا نحذف؟ ماذا نشغّل؟” يجب أن يكون هنا.
   - الهدف: منع تناقضات بين main.py وبين السكربتات.

- “Deterministic order”:
   - ترتيب ثابت (EDA → …).
   - لماذا مهم؟ لأن نفس البيانات يجب أن تنتج نفس outputs كل مرة (Reproducibility).

- “Pipeline Rigidity”:
   - هذا يعترف بمشكلة شائعة: بعض التحليلات تتطلب أعمدة غير موجودة.
   - الحل هنا: **Conditional execution** بدل الفشل.

- “NO caching of DataFrames”:
   - المقصود هنا: هذا المنسّق لا يعتمد على df global.
   - يقرأ من القرص حتى لا يستخدم بيانات قديمة.

> ملاحظة: داخل `backend/main.py` توجد globals، لكن هنا يحاول صاحب التصميم أن يجعل pipeline نفسه “قرص-أولًا”.

---

### 2) Imports — لماذا كل هذه المكتبات؟

جزء من imports:

```python
import sys
import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
```

شرح:

- `subprocess`:
   - لأن pipeline سيشغّل سكربتات بايثون كعمليات مستقلة.
   - هذا أفضل من import السكربت وتنفيذ main() لأن السكربتات غالبًا مكتوبة للتنفيذ المباشر.

- `shutil`:
   - لنسخ الملفات المرفوعة إلى “canonical file names” مثل `data/sales.csv`.

- `Path`:
   - إدارة المسارات بشكل portable بدل string paths.

- `typing`:
   - لتوضيح شكل الدوال (خاصة لأن الدوال ترجع dicts كبيرة).

---

### 3) Path Setup — لاحظ وجود OUTPUT_DIR هنا أيضًا

النص:

```python
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
LOGS_DIR = BASE_DIR / "logs"
SRC_DIR = BASE_DIR / "src"
```

شرح:

- `BASE_DIR`:
   - يعني: “جذر المشروع” (Sales_Intelligence_Project).
   - يتم بناء كل المسارات منه.

- `OUTPUT_DIR`:
   - نفس الفكرة التي تسببّت سابقًا في مشكلة `/api/alerts` عندما كان `OUTPUT_DIR` غير معرف في main.py.
   - هنا نلاحظ أن الملف يعرّفه صراحة.

ثم:

```python
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
```

لماذا هذه خطوة قوية؟

- لأنها تجعل المشروع “self-healing” جزئيًا.
- حتى لو حُذف مجلد `output/` بالخطأ، التشغيل يعيده.

---

### 4) Logging Configuration — لماذا ملف log مستقل؟

النص:

```python
log_file = LOGS_DIR / "pipeline_controller.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PipelineController")
```

شرح:

- `FileHandler`:
   - مهم جدًا لأن pipeline قد يُشغّل عبر API ثم ينتهي.
   - وجود log file يسمح بتشخيص أي فشل بعد انتهاء الطلب.

- `StreamHandler(sys.stdout)`:
   - يجعل نفس الرسائل تظهر في التيرمينال.

**بدائل logging في production:**

- structured logging (JSON logs)
- ربط مع ELK / Grafana Loki

---

### 5) Schema Resolver — لماذا موجود وما فائدته؟

النص:

```python
try:
    from schema_resolver import (
        SchemaResolver,
        SemanticField,
        ANALYSIS_REQUIREMENTS,
        can_perform_analysis
    )
    SCHEMA_RESOLVER_AVAILABLE = True
except ImportError as e:
    SCHEMA_RESOLVER_AVAILABLE = False
```

الفكرة:

- `schema_resolver.py` يحل مشكلة “اختلاف أسماء الأعمدة بين ملفات العملاء”.
- بدل أن تقول: “لازم يكون OrderDate” حرفيًا، تستطيع اكتشاف عمود تاريخ بأي اسم ضمن candidates.

لماذا try/except؟

- لو الملف غير موجود أو فشل import، المشروع لا يتوقف.
- ينتقل إلى fallback logic.

هذه فلسفة “robust demo”:

- المشروع يعرض قيمة حتى إذا بعض الأجزاء ناقصة.

---

### 6) File Definitions — قائمة رسمية لما يُحذف ويُنتج

هذا القسم مهم جدًا لأنه يحوّل موضوع الحذف من “تخمين” إلى “قائمة رسمية”.

#### 6.1) Canonical input files

```python
CANONICAL_INPUT_FILES = {
    "sales": "sales.csv",
    "customers": "customers.csv",
    "reviews": "customer_reviews.csv",
}
```

معنى canonical:

- مهما كان اسم الملف المرفوع من المستخدم، النظام ينسخه إلى اسم ثابت.
- هذا يجعل سكربتات ML أبسط لأنها تقرأ من مسار ثابت.

#### 6.2) Derived outputs

```python
DERIVED_OUTPUT_FILES = [
    "merged_data.csv",
    "cleaned_dataset.csv",
    "rfm_table.csv",
    ...
    "alerts.json",
    "clv_analysis.csv",
    "clv_insights.json",
]
```

هنا نرى “مخرجات intelligence” أيضًا.

ملاحظة مهمة جدًا تربويًا:

- في `backend/main.py` ملفات intelligence كانت بصيغة `f"{company_id}_alerts.json"`.
- هنا القائمة تذكر أسماء عامة مثل `alerts.json`.

هذا يدل أن المشروع يحتوي **مسارين للتخزين**:

- مسار legacy/عام (ملف واحد).
- ومسار multi-tenant per company (ملف لكل شركة).

سنرجع لهذه النقطة لاحقًا لأنها نقطة تصميم تحتاج توحيد.

---

### 7) الفكرة الأساسية: Conditional Pipeline Execution

الدالة المحورية هنا:

```python
def determine_available_analyses(data_path: Path = None) -> Dict[str, Dict[str, Any]]:
```

ماذا ترجع؟

- ترجع dict مثل:
   - `forecasting`: available؟ ولماذا.
   - `rfm`: available؟ ولماذا.
   - `recommendation`: available؟ ولماذا.
   - `sentiment`: available؟ ولماذا.

#### 7.1) لماذا هذه الدالة “تصلح مشروع PFE”؟

لأنها تُظهر تفكير هندسي:

- بدل “تشغيل كل شيء بأي ثمن”، يتم تقييم صلاحية التحليل قبل تشغيله.
- هذا يقلل الأخطاء، ويجعل نتائج الـ dashboard منطقية.

#### 7.2) من أين تقرأ الداتا؟

```python
if data_path is None:
    data_path = DATA_DIR / "cleaned_dataset.csv"
    if not data_path.exists():
        data_path = DATA_DIR / "sales.csv"
```

شرح:

- يفضّل cleaned_dataset (لأنه المفترض “أنظف” ومهيأ).
- إذا غير موجود، يرجع لـ sales.csv.

#### 7.3) استخدام Schema Resolver إذا توفر

```python
if SCHEMA_RESOLVER_AVAILABLE:
    resolver = SchemaResolver()
    resolution = resolver.resolve(df, "sales")
    for analysis_name in ["forecasting", "rfm", "recommendation"]:
        can_do, reason = can_perform_analysis(df, analysis_name)
        result[analysis_name] = {"available": can_do, "reason": reason}
```

الفكرة:

- بدل “if column in df.columns” اليدوي، توجد دالة معيارية تحدد المتطلبات.

ملاحظة:

- `resolution` هنا لا يتم استخدامه لاحقًا في المقطع المعروض، لكنه قد يكون مقصودًا لأغراض logs أو التوسع.

#### 7.4) Fallback logic — عندما لا يوجد Schema Resolver

الكود يبني lists للأعمدة المرشحة:

- date columns
- value columns
- customer columns
- product columns

ثم يحدد الشروط مثل:

- forecasting: date + value + حد أدنى للصفوف
- rfm: date + customer + value
- recommendation: product + rows

هذا مثال ممتاز على “Resilient design”.

#### 7.5) Sentiment منفصل

لاحظ أن sentiment لا يعتمد على sales.csv بل على ملف reviews:

- `data/customer_reviews.csv`

وهذا منطقي لأن sentiment تحليل نصوص وليس مبيعات.

---

### 8) PipelineState — لماذا نحتاج State إذا قلنا “لا caching”؟

النص:

```python
class PipelineState:
    def __init__(self):
        self.last_execution_time: Optional[datetime] = None
        self.last_execution_status: Dict[str, Any] = {}
        self.is_running: bool = False
        self.available_analyses: Dict[str, Dict[str, Any]] = {}
```

شرح:

- هذا ليس caching للبيانات.
- هذا caching لـ “حالة التنفيذ”: هل pipeline يعمل الآن؟ ما آخر نتيجة؟

لماذا مهم؟

- يمنع تشغيل pipeline مرتين بالتزامن.
- يعطيك إمكانية عرض “آخر تشغيل” في dashboard أو logs.

ثم:

```python
_pipeline_state = PipelineState()
def get_pipeline_state() -> PipelineState:
    return _pipeline_state
```

هذا Singleton بسيط.

**ملاحظة هندسية:**

- هذا singleton يعمل داخل process واحد فقط.
- إذا شغّلت uvicorn بعدة workers، كل worker سيكون له state منفصل.
- في production الحقيقي، state يجب أن يكون في Redis/DB.

---

### 9) File deletion functions — لماذا مكتوبة بهذه الدقة؟

الدالة:

```python
def delete_file_if_exists(file_path: Path, context: str = "") -> bool:
```

فكرة الدالة:

- بدل أن تكرر try/exists/unlink في كل مكان، تجعله helper.
- ترجع True إذا حذف فعلاً.
- وترجع False إذا لم يوجد (وهذا ليس خطأ).

ثم الدالة النووية:

```python
def hard_reset_derived_outputs() -> Dict[str, Any]:
```

شرح:

- تحذف كل outputs المشتقة (Data + Output + plots + model registry).
- ترجع تقريرًا: عدد المحذوفات + errors.

> لاحظ التطابق مع مفهوم cascade deletion في `backend/main.py` — نفس الفكرة لكن هنا كمرجع رسمي.

---

### 10) أين وصلنا؟ وما الذي سيأتي في Part 2؟

في Part 1 فهمنا:

- فلسفة الـ pipeline controller.
- لماذا paths + output dirs مهمة.
- لماذا conditional execution يقلل فشل التحليلات.
- لماذا hard reset هو ضمانة ضد “stale analytics”.

في Part 2 سنشرح بالتفصيل:

1) `detect_data_upload` و `detect_data_deletion`.
2) `run_script` ولماذا subprocess مع timeouts.
3) `run_full_sales_pipeline` وكيف يعمل خطوة بخطوة (EDA ثم conditional stages).
4) `orchestrate_pipeline` كنقطة الدخول الوحيدة التي يستدعيها `backend/main.py`.




---

## ملحق 3: شرح ملف `src/pipeline_controller.py` سطرًا بسطر (Part 2)

في Part 2 سندخل في “المعنى التنفيذي” للملف: كيف يقرر أن الـ data upload صالح؟ كيف يحذف كل النتائج القديمة؟ وكيف يشغّل السكربتات بالترتيب الصحيح بدون أن يعلّق السيرفر؟

---

### 1) `detect_data_upload(dataset_type, file_path)` — التحقق قبل التشغيل

هذه الدالة هدفها:

- فحص الملف المرفوع بسرعة (CSV parsing + columns + row_count).
- إرجاع تقرير واضح: valid؟ errors؟ warnings؟
- بدون أن تشغّل pipeline مباشرة.

النص (أجزاء):

```python
result = {
   "valid": False,
   "dataset_type": dataset_type,
   "file_path": str(file_path),
   "row_count": 0,
   "columns": [],
   "errors": [],
   "warnings": []
}
```

شرح سطرًا بسطر:

- `valid: False`:
   - default: نفترض أنه غير صالح حتى يثبت العكس.
   - هذا أسلوب آمن (secure-by-default).

- `errors` و`warnings` منفصلين:
   - **errors** = يمنع التشغيل.
   - **warnings** = “تحذير” يعني الملف سيشتغل لكن التحليلات قد تكون ناقصة.

ثم:

```python
if not file_path.exists():
   result["errors"].append("File not found")
   return result
```

معنى هذا:

- لا تدخل حتى في pandas إذا المسار غير موجود.
- وهذا يوفر وقت ويعطي رسالة واضحة.

ثم:

```python
df = pd.read_csv(file_path)
result["row_count"] = len(df)
result["columns"] = list(df.columns)
```

هنا الدالة تجمع metadata.

ثم:

```python
if len(df) == 0:
   result["errors"].append("File is empty (0 rows)")
   return result
```

يعني:

- ملف فارغ = لا pipeline.

#### 1.1) Validation حسب نوع dataset

**حالة sales:**

```python
required = ["OrderDate", "TotalPrice"]
optional = ["OrderID", "ProductID", "CustomerID", "City"]
missing = [c for c in required if c not in df.columns]
if missing:
   result["warnings"].append(f"Missing recommended columns: {missing}")
```

ملاحظة مهمة جدًا:

- هنا الكود يسميها `required` لكنه يتعامل معها كـ warning وليس error.
- هذا يعكس فلسفة “النظام لا يتوقف” حتى لو البيانات ناقصة.

عمليًا ماذا يعني ذلك؟

- إذا غاب OrderDate أو TotalPrice:
   - كثير من التحليلات (forecasting/kpis) قد لا تعمل لاحقًا.
   - لكن يمكن أن يعمل EDA أو أجزاء بسيطة.

**حالة reviews:**

```python
text_cols = ["ReviewText", "review_text", "Review", "text", "Text", "comment"]
has_text = any(c in df.columns for c in text_cols)
if not has_text:
   result["errors"].append(f"Missing review text column...")
   return result
```

هنا صارمة أكثر:

- بدون عمود نص = sentiment لا معنى له.
- لذلك تعتبره error.

في النهاية:

```python
result["valid"] = True
```

> الخلاصة: `detect_data_upload` هو “فلتر أولي” (preflight check) يمنع الملفات السيئة جدًا، ويسمح للملفات الناقصة بالمرور مع تحذير.

---

### 2) `detect_data_deletion(dataset_type)` — حدث الحذف = Hard Reset

هذه الدالة تعالج حدث deletion بطريقة صارمة:

- حذف ملف canonical input الخاص بالنوع.
- ثم تنفيذ HARD RESET لكل المخرجات المشتقة.

النص (أجزاء):

```python
canonical_file = CANONICAL_INPUT_FILES.get(dataset_type)
if canonical_file:
   delete_file_if_exists(DATA_DIR / canonical_file, context="(canonical input)")

reset_result = hard_reset_derived_outputs()
```

شرح:

- لماذا نحذف canonical input أولاً؟
   - لأن وجوده قد يجعل pipeline يعتقد أن البيانات مازالت موجودة.

- لماذا HARD RESET لكل شيء وليس فقط ملفات مرتبطة بالنوع؟
   - لأن ملفات الـ outputs مشتقة غالبًا من دمج عدة مصادر (sales + customers + reviews).
   - حذف جزء من المدخلات يجعل كل النتائج “مشكوكة”.
   - لذلك هذا قرار Design قوي: **clean slate**.

ثم تعيد:

```python
return {
   "dataset_type": dataset_type,
   "canonical_deleted": canonical_file,
   "hard_reset": reset_result,
   "timestamp": ...
}
```

هذه الاستجابة ممتازة للتوثيق ولـ UI: تقدر تعرض للمستخدم “كم ملف تم حذفه”.

---

### 3) `run_script(script_name, timeout)` — تشغيل سكربت ML بشكل آمن

هذه الدالة هي “مشغل موحد” لكل سكربتات `src/*.py`.

#### 3.1) التحقق من وجود السكربت

```python
script_path = SRC_DIR / script_name
if not script_path.exists():
   return {"success": False, "error": f"Script not found: {script_path}", ...}
```

لماذا هذا ممتاز؟

- بدل أن يسقط البرنامج باستثناء غير واضح، يعطيك dict منظم.

#### 3.2) subprocess.run

```python
result = subprocess.run(
   [sys.executable, str(script_path)],
   cwd=str(BASE_DIR),
   capture_output=True,
   text=True,
   timeout=timeout
)
```

شرح سطرًا بسطر:

- `sys.executable`:
   - يضمن استخدام نفس بيئة بايثون (نفس venv) التي يعمل بها السيرفر.

- `cwd=str(BASE_DIR)`:
   - مهم لأن السكربتات غالبًا تعتمد على paths نسبية مثل `data/...`.

- `capture_output=True`:
   - يجمع stdout/stderr داخل result.
   - هذا مفيد جدًا لو تريد إظهار جزء من الخطأ في logs.

- `timeout`:
   - يمنع السكربت من تعليق السيرفر إلى ما لا نهاية.

#### 3.3) ما الذي ترجعها الدالة؟

- ترجع dict فيه:
   - `success`
   - `return_code`
   - `stdout`
   - `stderr`

وهذا يجعل “تشغيل pipeline” قابل للتسجيل والتتبع.

---

### 4) `run_full_sales_pipeline(source_file)` — السيناريو الكامل للمبيعات

هذه هي أهم دالة في الملف لأنها تنفّذ التسلسل: EDA ثم تحليلات مشروطة.

#### 4.1) منع التزامن (concurrency guard)

```python
state = get_pipeline_state()
if state.is_running:
   return {"success": False, "error": "Pipeline already running"}
state.is_running = True
state.reset()
```

شرح:

- إذا pipeline يعمل الآن، نرفض تشغيل آخر.
- `state.reset()` يضمن أن الحالة القديمة لا تؤثر على الجديدة.

#### 4.2) Step 1: HARD RESET

```python
reset_result = hard_reset_derived_outputs()
results["steps"]["hard_reset"] = reset_result
```

هذا يطبّق القاعدة الذهبية:

- “DELETE old outputs before generating new ones”.

#### 4.3) Step 2: Copy file إلى canonical (اختياري)

```python
if source_file and source_file.exists():
   shutil.copy2(source_file, DATA_DIR / "sales.csv")
else:
   if not (DATA_DIR / "sales.csv").exists():
      return {"success": False, "error": "No sales data available"}
```

شرح:

- إذا تم رفع ملف جديد، انسخه إلى `data/sales.csv`.
- إذا لم يأتِ ملف (مثلاً تشغيل يدوي)، استعمل الموجود.

#### 4.4) Step 3: تشغيل EDA (إجباري)

```python
eda_result = run_script("01_eda.py", timeout=120)
if not eda_result["success"]:
   results["success"] = False
   return results
```

EDA هو الأساس لأنه:

- ينتج `merged_data.csv`
- وينتج `cleaned_dataset.csv`

وإذا فشل EDA لا معنى لإكمال باقي التحليلات.

#### 4.5) Step 4: التحقق من cleaned_dataset.csv

```python
cleaned_path = DATA_DIR / "cleaned_dataset.csv"
if not cleaned_path.exists():
   results["success"] = False
   return results
```

هذه نقطة مهمة جدًا:

- بدل أن نفترض أن السكربت نجح في توليد الملف، نتحقق.
- هذا يمنع “نجاح ظاهري” مع outputs ناقصة.

#### 4.6) Step 5: determine_available_analyses

```python
availability = determine_available_analyses(cleaned_path)
```

ثم:

- يضيف المتاح إلى `available_analyses`.
- ويضيف غير المتاح إلى `skipped_analyses` مع reason.

وهذا بالضبط “حل مشكلة pipeline rigidity” التي ذكرها docstring.

#### 4.7) Steps 6/7/8: تشغيل تحليلات مشروطة

المنطق نفسه يتكرر:

- إذا `forecasting` متاح → شغّل `03_forecasting.py`.
- إذا `rfm` متاح → شغّل `04_rfm.py`.
- إذا `recommendation` متاح → شغّل `05_recommendation.py`.

ملاحظة مهمة:

- إذا فشل forecasting/rfm/recommendations، يعتبر “non-critical” ويكمل.
- هذا قرار تصميم: الهدف أن dashboard يظل يعمل حتى لو جزء فشل.

#### 4.8) finally: تحديث state

```python
finally:
   state.is_running = False
   state.last_execution_time = datetime.utcnow()
   state.last_execution_status = results
```

معنى ذلك:

- حتى لو حصل exception، سيتم فك القفل `is_running=False`.
- وسيتم تسجيل آخر نتيجة.

---

### 5) `run_sentiment_pipeline` و`run_customers_pipeline` — خطوط فرعية

هذه الدوال أقل تعقيدًا لكنها مهمة لفهم الشمول:

- `run_sentiment_pipeline`:
   - يحذف ملف sentiment القديم.
   - ينسخ reviews إلى `data/customer_reviews.csv`.
   - يشغّل `06_sentiment.py`.

- `run_customers_pipeline`:
   - ينسخ customers إلى `data/customers.csv`.
   - إذا `data/sales.csv` موجود، يعيد تشغيل `run_full_sales_pipeline()` حتى يتم دمج customer info في التحليلات.

هذه نقطة تصميم قوية:

- العملاء (customers) وحدهم لا ينتجون dashboard.
- لكنهم “يحسنون” تحليلات sales (مثل RFM) إذا تم الدمج.

---

### 6) `orchestrate_pipeline(dataset_type, action, file_path)` — نقطة الدخول الوحيدة

هذه هي الدالة التي يستدعيها `backend/main.py` عندما يقول:

- “SINGLE SOURCE OF TRUTH: Uses pipeline_controller.orchestrate_pipeline()”.

النص (مختصر):

```python
if action == "delete":
   result["execution"] = detect_data_deletion(dataset_type)
   return result

if action in ["upload", "replace"]:
   if dataset_type == "sales":
      result["execution"] = run_full_sales_pipeline(file_path)
   elif dataset_type == "reviews":
      result["execution"] = run_sentiment_pipeline(file_path)
   elif dataset_type == "customers":
      result["execution"] = run_customers_pipeline(file_path)
```

شرح:

- action = delete → تنظيف شامل.
- upload/replace → تشغيل pipeline المناسب حسب dataset_type.

وهكذا `backend/main.py` لا يحتاج أن يعرف تفاصيل “كيف” يعمل كل pipeline.

---

### 7) Standalone execution — لماذا موجود؟

في نهاية الملف:

- يسمح لك تشغيل orchestrator من CLI.
- هذا مفيد جدًا للتجارب بدون frontend.

مثال (كما يكتب في docstring):

- `python pipeline_controller.py sales upload path/to/sales.csv`
- `python pipeline_controller.py sales delete`

هذا يعطيك JSON منظم لنتيجة التنفيذ.

---

### 8) ربط Part 2 بالمشكلة الأصلية (alerts + OUTPUT_DIR) — فكرة هندسية واحدة

في بداية المشروع ظهر عندك:

- “Unexpected token '<'” عندما الواجهة انتظرت JSON لكنها أخذت HTML.

ثم لاحقًا ظهر:

- 500 بسبب `OUTPUT_DIR`.

الدرس الهندسي المشترك بين `backend/main.py` و`pipeline_controller.py` هو:

1) **المسارات (Paths) لازم تكون معرفة بوضوح وموجودة فعليًا** (mkdir).
2) **الحياة الكاملة للبيانات (Data Lifecycle)** أهم من endpoint واحد:
   - upload → تشغيل → outputs → cache → delete → hard reset.
3) **Single Source of Truth** يقلل bugs: بدل أن كل endpoint يقرر الحذف والتشغيل بنفسه.

> في Part 3 من هذا الملحق (إذا أكملنا) سننتقل لشرح `schema_resolver.py` لأن conditional execution يعتمد عليه ويعتبر “عقل” فهم الأعمدة.




---

## ملحق 4: شرح ملف `src/schema_resolver.py` سطرًا بسطر (Part 1)

هذا الملف هو “طبقة المعنى” (Semantic Layer) في المشروع.

إذا قلت لك إن `pipeline_controller.py` هو “العقل الذي يقرر ماذا نشغّل”، فـ `schema_resolver.py` هو “العقل الذي يفهم **ماذا تعني الأعمدة**”.

بدون هذا الملف، أي اختلاف بسيط في أسماء الأعمدة سيكسر التحليلات.

---

### 1) Docstring — لماذا طويل جدًا؟

بداية الملف تشرح مشكلتين أساسيتين:

#### PROBLEM #1: Hard-Coded Column Assumptions

كان النظام سابقًا يفترض أعمدة ثابتة مثل:

- `OrderDate`
- `CustomerID`
- `TotalPrice`
- `Product`

لكن في الواقع، أي شركة قد ترفع ملف بأسماء مختلفة:

- `Sale_Date` بدل `OrderDate`
- `cust_id` بدل `CustomerID`
- `Revenue` بدل `TotalPrice`

الحل المفاهيمي الذي يضعه الملف:

- نفصل بين:
  - **Business Meaning (Semantics)**
  - و **Column Names (Syntax)**

يعني: نحن لا نهتم بالاسم الحقيقي للعمود، بل نهتم بمعناه.

#### PROBLEM #2: “نحلل أي بيانات” وهم

الملف يضع حدودًا واضحة:

- هذا النظام صُمم لـ **Transactional Sales Data**.
- يدعم أسئلة محددة (Forecasting, RFM, Recommendations, Sentiment).
- لا يدعم أنواع أخرى (صور/فيديو/Streaming/بيانات بلا تاريخ...).

لماذا هذا مهم كـ PFE؟

- لأن توثيق “نطاق التحليل” (Scope) هو جزء أساسي في أي منتج تحليلي.
- بدون scope سيصبح المشروع مليئًا بحالات فشل غير مبررة.

---

### 2) Imports — لماذا dataclass وEnum وpandas؟

النص:

```python
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
```

شرح:

- `Enum`:
   - حتى نعرّف قائمة “أنواع المعاني” بشكل ثابت.
   - بدل strings عشوائية (أخطاء إملائية سهلة).

- `dataclass`:
   - لبناء كائنات نتائج منظمة بدل dicts غير منضبطة.
   - مثل `SchemaResolutionResult`.

- `pandas`:
   - لأننا نتعامل مع DataFrame وdf.columns والقراءة من CSV غالبًا.

---

### 3) SemanticField(Enum) — قائمة المعاني التي يفهمها النظام

النص:

```python
class SemanticField(Enum):
   ORDER_DATE = "order_date"
   CUSTOMER_ID = "customer_id"
   ORDER_ID = "order_id"
   PRODUCT = "product"
   QUANTITY = "quantity"
   UNIT_PRICE = "unit_price"
   TOTAL_PRICE = "total_price"
   ...
   REVIEW_TEXT = "review_text"
   RATING = "rating"
   REVIEW_DATE = "review_date"
```

شرح تربوي:

- هنا تم وضع “قاموس مفاهيمي” (Domain Vocabulary).
- أي تحليل لاحقًا سيقول: “أحتاج ORDER_DATE” بدل أن يقول “أحتاج OrderDate”.

هذا يحقق هدف كبير:

- **توحد لغة المشروع** بين pipeline/scripts/backend.

---

### 4) COLUMN_ALIASES — المصدر الوحيد لاكتشاف الأعمدة

النص:

```python
COLUMN_ALIASES: Dict[SemanticField, List[str]] = {
   SemanticField.ORDER_DATE: ["OrderDate", "order_date", "Sale_Date", ...],
   SemanticField.CUSTOMER_ID: ["CustomerID", "cust_id", ...],
   ...
}
```

شرح:

- هذا هو “Registry” للأسماء المحتملة.
- لكل معنى، توجد قائمة أسماء قد تظهر في ملفات مختلفة.

**لماذا يسميه الملف SINGLE SOURCE OF TRUTH؟**

- لأن أي مكان آخر في المشروع يحتاج اكتشاف عمود تاريخ يجب أن يعتمد على هذه القائمة.
- لو عملت قائمة ثانية في ملف آخر، ستدخل في تناقضات.

**نقطة هندسية مهمة:**

- هذه القوائم يجب أن تُدار بعناية:
  - إضافة aliases جديدة عندما تواجه ملفات عملاء جديدة.
  - لكن بدون “توسيع عشوائي” يجعل الكشف خاطئًا.

---

### 5) AnalysisRequirement — تعريف متطلبات كل تحليل

النص:

```python
@dataclass
class AnalysisRequirement:
   name: str
   description: str
   required_fields: List[SemanticField]
   optional_fields: List[SemanticField] = field(default_factory=list)
   min_rows: int = 10
```

شرح:

- هذا يعرّف “عقد” (Contract) لكل تحليل:
  - ما الذي يجب توفره؟
  - ما الذي يُفضل توفره؟
  - ما أقل عدد صفوف لكي يكون التحليل ذا معنى؟

ثم يتم بناء قاموس:

```python
ANALYSIS_REQUIREMENTS = {
   "forecasting": AnalysisRequirement(... min_rows=30),
   "rfm": AnalysisRequirement(... min_rows=10),
   "recommendation": AnalysisRequirement(... min_rows=50),
   "sentiment": AnalysisRequirement(... min_rows=5),
}
```

شرح:

- لاحظ أن `recommendation` يحتاج min_rows أعلى لأن pattern mining يحتاج حجم.
- forecasting يحتاج 30 نقطة على الأقل (قيمة عملية جدًا).

> في Part 2 سنشرح كيف يستخدم `SchemaResolver.resolve()` هذه المتطلبات ليقرر:
>
> - available_analyses
> - unavailable_analyses مع أسباب واضحة


---

## ملحق 4: شرح ملف `src/schema_resolver.py` سطرًا بسطر (Part 2)

في Part 2 سنشرح الجزء التنفيذي: كيف يتم “حل” الأعمدة فعليًا من DataFrame؟ وكيف يتم إنتاج تقرير مفهوم للبشر؟

---

### 1) SchemaResolutionResult — لماذا نحتاج Result object؟

النص:

```python
@dataclass
class SchemaResolutionResult:
   resolved_columns: Dict[SemanticField, str]
   missing_required: List[SemanticField]
   missing_optional: List[SemanticField]
   unmapped_columns: List[str]
   is_valid: bool
   validation_errors: List[str]
   validation_warnings: List[str]
   available_analyses: List[str]
   unavailable_analyses: Dict[str, str]
```

شرح:

- `resolved_columns`:
   - أهم حقل: يربط “المعنى” بالعمود الحقيقي.
   - مثال: ORDER_DATE → "Sale_Date".

- `unmapped_columns`:
   - أعمدة موجودة في الملف لكن النظام لا يعرف معناها.
   - وجودها ليس خطأ، فقط “لن تُستخدم”.

- `available_analyses` و`unavailable_analyses`:
   - هذه النقطة تجعل pipeline controller “شرطيًا” بطريقة منظمة.
   - بدل: “جرّب وشوف يفشل”، يصبح: “قرر قبل التشغيل”.

ثم يوجد helper methods:

- `get_column(field)`
- `has_field(field)`

وهذه تساعد باقي الكود أن يكون نظيفًا.

---

### 2) SchemaResolver.__init__ — قابلية التخصيص

النص:

```python
def __init__(self, custom_aliases: Dict[SemanticField, List[str]] = None):
   self.aliases = COLUMN_ALIASES.copy()
   if custom_aliases:
      ... merge ...
```

شرح:

- يسمح لك أن تضيف aliases خاصة بعميل معين بدون تعديل القائمة العامة.
- هذا مفيد إذا عميل يستخدم naming غريب جدًا.

> هندسيًا: في production قد تحفظ custom_aliases في DB لكل شركة.

---

### 3) SchemaResolver.resolve(df, dataset_type, required_analyses)

هذه هي الدالة التي تعطي معنى للمشروع كله.

#### 3.1) تجهيز الحاويات

النص:

```python
resolved = {}
unmapped = list(df.columns)
errors = []
warnings = []
used_columns = set()
```

شرح:

- `unmapped` يبدأ بكل الأعمدة، ثم ننقص منه الأعمدة التي تم التعرف عليها.
- `used_columns` يمنع أن عمود واحد يُنسب لأكثر من معنى.

#### 3.2) حل الأعمدة (Resolution loop)

النص:

```python
for semantic_field, possible_names in self.aliases.items():
   for name in possible_names:
      if name in df.columns and name not in used_columns:
         resolved[semantic_field] = name
         used_columns.add(name)
         unmapped.remove(name)
         break
```

شرح سطرًا بسطر:

- يمر على كل SemanticField.
- يمر على كل alias محتمل.
- أول alias موجود في df.columns يتم اعتماده.

**ملاحظة هندسية:**

- ترتيب aliases داخل القائمة مهم جدًا.
- لأن “أول match” هو الذي يُختار.

#### 3.3) تحديد التحليلات المتاحة

النص:

```python
for analysis_name, requirement in ANALYSIS_REQUIREMENTS.items():
   missing_for_analysis = [field for field in requirement.required_fields if field not in resolved]
   if missing_for_analysis:
      unavailable_analyses[analysis_name] = "Missing required fields ..."
   elif len(df) < requirement.min_rows:
      unavailable_analyses[analysis_name] = "Insufficient data ..."
   else:
      available_analyses.append(analysis_name)
```

شرح:

- هذا يطبق “العقد” الذي عرّفناه في Part 1.
- يعطي أسباب واضحة: missing fields أو rows قليلة.

هذه الأسباب تظهر في:

- logs
- pipeline_controller
- ويمكن عرضها في UI لاحقًا.

#### 3.4) Validation حسب dataset_type

**حالة sales:**

```python
if SemanticField.ORDER_DATE not in resolved:
   errors.append("Sales data requires a date column...")

if SemanticField.TOTAL_PRICE not in resolved:
   if UNIT_PRICE and QUANTITY موجودين:
      warnings.append("Will compute from UnitPrice × Quantity")
   else:
      errors.append("Sales data requires a value column...")
```

شرح:

- إذا total_price غير موجود لكن يمكن حسابه من unit_price × quantity → warning وليس error.
- هذا تصميم ذكي لأنه يسمح بتنوع الملفات.

**حالة reviews:**

- إذا لا يوجد REVIEW_TEXT → error.

#### 3.5) required_analyses (إلزام تحليلات معينة)

النص:

```python
if required_analyses:
   for analysis in required_analyses:
      if analysis in unavailable_analyses:
         errors.append(f"Required analysis '{analysis}' not available: ...")
```

شرح:

- أحيانًا تريد أن تقول: “لا أقبل هذا الملف إلا إذا كان forecasting ممكن”.
- هذه feature مهمة لو أردت وضع Quality Gate.

#### 3.6) Unmapped columns warning

- إذا بقيت أعمدة غير معروفة، يضع warning “سيتم تجاهلها”.

ثم يرجع `SchemaResolutionResult` مع:

- `is_valid = len(errors) == 0`.

---

### 4) get_canonical_dataframe — توحيد أسماء الأعمدة

النص:

```python
canonical_name = f"__{semantic_field.value}"
result[canonical_name] = result[actual_col]
```

شرح:

- هذا ينتج أعمدة مثل:
  - `__order_date`
  - `__total_price`
  - `__product`

لماذا prefix `__`؟

- لتجنب الاصطدام بأعمدة موجودة أصلًا.
- ولتمييز أنها “أعمدة معيارية مشتقة”.

هذه الفكرة نفس التي رأيناها في `backend/main.py` داخل `normalize_sales_dataframe` حيث تم إنشاء:

- `__order_date`
- `__total_price`
- `__product`

يعني يوجد “تلاقي” Design بين الملفات.

---

### 5) validate_and_report — تقرير مفهوم للبشر

هذه الدالة ترجع:

- `resolution`
- و`report` (string)

والـ report يحتوي:

- resolved fields
- missing required
- unmapped columns
- available/unavailable analyses
- errors/warnings

هذه ميزة قوية جدًا للتوثيق وواجهة admin.

---

### 6) Convenience functions — استخدام سريع

الدوال:

- `resolve_schema(df, dataset_type)`
- `validate_sales_data(df)`
- `get_column_for(df, semantic_field)`
- `can_perform_analysis(df, analysis_name)`

مهم خصوصًا `can_perform_analysis` لأنه يُستخدم داخل `pipeline_controller.py`.

لاحظ أنه يعمل:

- `result = resolver.resolve(df)`
- ثم يقرر based on `available_analyses`.

---

### 7) Main demo — لماذا موجود؟

آخر الملف يبني `sample_data` بأعمدة مختلفة مثل `Sale_Date` و`cust_id` و`Qty` و`Price`.

ثم:

- يستدعي `validate_and_report`.
- ويطبع report.

هذه طريقة ممتازة للتأكد أن resolver يعمل حتى بدون تشغيل الـ backend.

> بهذا نكون فهمنا “العقل” الذي يجعل المشروع يتحمل اختلاف schemas. الخطوة التالية الطبيعية: شرح `src/data_validator.py` ثم ربطه بـ upload endpoints لضمان جودة البيانات قبل تشغيل pipelines.


---

## ملحق 5: شرح ملف `src/data_validator.py` سطرًا بسطر (Part 1)

هذا الملف هو “حارس البوابة” (Gatekeeper) في لحظة الرفع Upload.

إذا كان `schema_resolver.py` يجاوب: “ما معنى الأعمدة؟”

فـ `data_validator.py` يجاوب: “هل هذه البيانات **صالحة فعليًا** للتحليل؟ وما المشاكل التي فيها؟”

الفرق مهم جدًا:

- Schema Resolver = فهم أسماء الأعمدة.
- Data Validator = جودة البيانات (تواريخ صحيحة؟ قيم سالبة؟ تكرار كبير؟ نقص في completeness؟).

---

### 1) Docstring — لماذا نحتاج validation عند upload؟

الملف يعرّف المشكلة:

- سابقًا يمكن إدخال بيانات خاطئة وتكسر التحليل “بصمت”.

والحل:

- Validate **قبل** تشغيل أي pipeline.

هذه نقطة هندسية قوية لأن تشغيل pipeline على بيانات سيئة ينتج:

- نتائج مضللة
- أخطاء عشوائية
- صعوبة debug

---

### 2) Imports — لماذا numpy وpandas؟

```python
import pandas as pd
import numpy as np
```

السبب:

- pandas للتعامل مع df.
- numpy لاكتشاف الأعمدة الرقمية عبر `select_dtypes` ونطاقات min/max.

ثم:

```python
from schema_resolver import (SchemaResolver, SchemaResolutionResult, SemanticField, ANALYSIS_REQUIREMENTS)
```

شرح:

- validator يعتمد على resolver.
- لأن أول خطوة في validation هي “حل الأعمدة” (resolve) لكي نعرف أي عمود هو التاريخ وأي عمود هو السعر.

---

### 3) DataQualityMetrics — مقاييس الجودة

النص:

```python
@dataclass
class DataQualityMetrics:
   total_rows: int
   total_columns: int
   missing_values: Dict[str, int]
   duplicate_rows: int
   numeric_columns: List[str]
   date_columns: List[str]
   text_columns: List[str]
   date_range: Optional[Tuple[str, str]] = None
   numeric_ranges: Dict[str, Tuple[float, float]] = None
```

شرح:

- هذا لا يحكم “valid/invalid” مباشرة.
- هذا يجمع حقائق تساعدنا نقرر.

أهم دالة هنا:

```python
def get_completeness_score(self) -> float:
```

فكرتها:

- تحسب نسبة الخلايا غير الناقصة من مجموع الخلايا.
- تُرجع رقم من 0 إلى 100.

لماذا completeness مهم؟

- لأن التحليل على بيانات فيها 40% نقص غالبًا يعطي قرارات سيئة.

---

### 4) ValidationResult — النتيجة الكاملة للـ validation

النص:

```python
@dataclass
class ValidationResult:
   dataset_type: str
   file_name: str
   schema_result: SchemaResolutionResult
   quality_metrics: DataQualityMetrics
   is_valid: bool
   errors: List[str]
   warnings: List[str]
   suggestions: List[str]
   available_analyses: List[str]
```

لماذا هذا التصميم جميل؟

- لأنه يجمع كل شيء في مكان واحد.
- الواجهة تستطيع عرض:
  - أخطاء تمنع الرفع
  - تحذيرات
  - اقتراحات لتحسين الملف
  - “أي تحليلات ستعمل؟”

ثم `to_dict()`:

- يحول النتيجة لJSON.
- وهذا يُسهّل إرجاعها عبر API.

---

### 5) DataValidator.validate_upload(df, dataset_type, file_name)

هذه هي الدالة الأساسية.

#### 5.1) Step 1: Basic validation

```python
if df is None or df.empty:
   errors.append("Dataset is empty or could not be loaded")
   return ValidationResult(...)
```

هنا نرى تصميم “fail fast”:

- لا تكمل إذا لا يوجد بيانات.
- ترجع نتيجة منظمة حتى في الفشل.

لاحظ أنه يبني `SchemaResolutionResult` فارغ و`DataQualityMetrics` فارغة.

هذه طريقة احترافية:

- بدل `return None` (الذي يكسر كل شيء لاحقًا).

#### 5.2) Step 2: Compute data quality

- يستدعي `_compute_quality_metrics(df)`.

#### 5.3) Step 3: Resolve schema

```python
schema_result = self.schema_resolver.resolve(df, dataset_type)
errors.extend(schema_result.validation_errors)
warnings.extend(schema_result.validation_warnings)
```

شرح:

- إذا schema_resolver قال “missing date column” هذه تتحول إلى error.
- إذا قال “unmapped columns” تتحول إلى warning.

#### 5.4) Step 4: Type-specific validation

- إذا sales → `_validate_sales_data`
- إذا customers → `_validate_customers_data`
- إذا reviews → `_validate_reviews_data`

هذه مهمة لأن “جودة” sales تختلف عن “جودة” reviews.

#### 5.5) Step 5: Duplicates warning

```python
if quality_metrics.duplicate_rows > 0:
   pct = ...
   if pct > 10:
      warnings.append("High duplicate rate ...")
```

شرح:

- التكرار العالي يفسد التحليلات.
- لكنه ليس دائمًا “خطأ قاتل” لذلك جعله warning.

#### 5.6) Step 5 (تكملة): completeness

```python
if completeness < 80:
   warnings.append(f"Low data completeness: {completeness}%")
   suggestions.append("Consider cleaning missing values before analysis")
```

شرح:

- 80% threshold قرار عملي.
- يمكن تغييره لاحقًا كـ config.

#### 5.7) Step 6: suggestions إذا schema invalid

- `_generate_column_suggestions` يعطي اقتراحات بسيطة للمستخدم.

في النهاية:

- `is_valid = len(errors) == 0`.

> في Part 2 سنشرح تفاصيل حساب metrics والتحقق النوعي لكل dataset.


---

## ملحق 5: شرح ملف `src/data_validator.py` سطرًا بسطر (Part 2)

في Part 2 سنفكك الدوال الداخلية التي تجعل validation “ذكي” وليس مجرد check للأعمدة.

---

### 1) `_compute_quality_metrics(df)` — كيف نعرف نوع الأعمدة؟

النص يبدأ بـ:

```python
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
text_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
```

شرح:

- هذه طريقة معيارية لتصنيف الأعمدة.
- مهمة لأننا نريد:
  - نطاقات للأرقام
  - وطول/جودة للنص

ثم يكتشف date columns بطريقتين:

1) إذا dtype أصلاً datetime
2) أو يحاول `pd.to_datetime(sample)` على عينة

هذا design choice ذكي لأنه:

- لا يعتمد على اسم العمود
- يعتمد على قابلية تحويل القيم لتاريخ

ثم:

```python
missing = {col: int(df[col].isna().sum()) for col in df.columns}
duplicates = int(df.duplicated().sum())
```

هذه مقاييس مباشرة.

ثم date_range:

- يحاول إيجاد min/max تاريخ.
- وهذا مفيد جدًا في dashboard (مثلاً “البيانات تغطي 2021-2024”).

ثم numeric_ranges:

- min/max لكل عمود رقمي.
- مفيد لاكتشاف anomalies (مثلاً سعر = 1,000,000).

---

### 2) `_validate_sales_data` — منطق جودة المبيعات

#### 2.1) فحص التاريخ

```python
dates = pd.to_datetime(df[date_col], errors='coerce')
invalid_dates = dates.isna().sum()
```

شرح:

- `errors='coerce'` يحول القيم الخاطئة إلى NaT.
- ثم نحسب كم عددها.

ثم threshold:

- إذا invalid_dates أكثر من 20% → error.
- أقل → warning.

لماذا؟

- لأن نسبة كبيرة من تواريخ خاطئة تعني forecasting وkpis غير موثوقة.

ثم فحص “تواريخ مستقبلية”:

- غالبًا خطأ إدخال.
- تحذير وليس خطأ.

#### 2.2) فحص السعر

```python
prices = pd.to_numeric(df[price_col], errors='coerce')
negative_prices = (prices < 0).sum()
```

سعر سلبي عادة غير منطقي (إلا إذا dataset فيه refunds).

الكود اعتبره warning.

ثم “عدد كبير من الصفر”:

- إذا أكثر من 50% معاملات قيمتها 0 → warning.
- هذا يدل أن عمود السعر ربما خطأ أو مفقود.

---

### 3) `_validate_customers_data`

يفحص duplicate في `CustomerID`.

- تكرار معرف العميل يعني دمج سيء أو ملفات مكررة.

---

### 4) `_validate_reviews_data`

يفحص:

- short reviews (أقل من 10 حروف)
- ratings خارج 0-5

لماذا short reviews؟

- NLP على نص قصير جدًا يعطي دقة أقل.

---

### 5) Convenience functions

الدالة `quick_validate(file_path, dataset_type)` مفيدة جدًا:

- تقرأ CSV
- ترجع (is_valid, errors)

هذه تصلح لربطها مباشرة في API upload قبل حفظ الملف النهائي.

---

### 6) Demo في نهاية الملف

يبني مثال valid sales ثم مثال invalid sales.

- الهدف: اختبار سريع بدون backend.

> بهذا نكون صنعنا “Quality Gate” منطقي. الخطوة التالية: شرح كيف يمكن دمج هذا validator داخل endpoints `/api/datasets/upload` و`replace` (أو داخل pipeline_controller قبل copy).


---

## ملحق 6: شرح ملف `src/explainability.py` سطرًا بسطر (Part 1)

هذا الملف يقدم “طبقة شرح” (Explainability) فوق النتائج.

لماذا هذا مهم؟

- لأن الـ dashboard ليس هدفه إعطاء رقم فقط.
- هدفه أن يفهم المدير “لماذا” الرقم هكذا وما الذي يجب فعله.

الملف يشرح 3 أشياء:

1) Forecast (اتجاه/ثقة/موسمية)
2) RFM Segments (لماذا العميل Champion أو At Risk)
3) Recommendations (support/confidence/lift بلغة بشرية)

---

### 1) explain_forecast(forecast_df, components, model_type)

النص يبدأ ببناء dict اسمه `explanations` يحتوي أقسام:

- forecast_summary
- trend_analysis
- seasonality_insights
- confidence
- recommendations

#### 1.1) Summary statistics

```python
avg_forecast = forecast_df["yhat"].mean()
min_forecast = forecast_df["yhat"].min()
max_forecast = forecast_df["yhat"].max()
total_forecast = forecast_df["yhat"].sum()
```

ثم يحوّلها إلى نص قابل للعرض مثل `$15,000.00`.

هذه نقطة UI مهمة:

- الواجهة لا تريد raw float فقط.

#### 1.2) Trend analysis

يقارن أول شهر بآخر شهر ويحسب نسبة النمو.

- إذا أكبر من 5% → upward
- أقل من -5% → downward
- غير ذلك → stable

ثم يعطي توصيات:

- نمو قوي → زد المخزون/التسويق.
- هبوط قوي → راجع التسعير والاحتفاظ.

#### 1.3) Confidence intervals

إذا توجد `yhat_lower` و`yhat_upper`:

- يحسب متوسط عدم اليقين.
- يصنف الثقة high/medium/low.

هذه “لغة بشرية” بدل أرقام فقط.

#### 1.4) Seasonality

- إذا model_type Prophet وأعطيت `components` وفيها yearly.
- يضيف تفسير أن هناك موسمية.

> في Part 2 سنشرح RFM explainability + recommendation explainability + ExplainabilityEngine كواجهة موحدة.


---

## ملحق 6: شرح ملف `src/explainability.py` سطرًا بسطر (Part 2)

Part 2 يكمّل طبقة الشرح لباقي الـ outputs: RFM وRecommendations، ثم يعطي “واجهة موحدة” عبر class.

---

### 2) score_to_rating(score, max_score=5)

هذه دالة صغيرة لكنها ذكية:

- تحوّل رقم score إلى label بشري.
- مثل: 1 → Low، 3 → Medium، 5 → High.

المغزى:

- بدل ما تقول للمستخدم “R=4” تقول “Recency: High”.

---

### 3) explain_rfm_segment(rfm_row)

المدخل المتوقع:

- صف واحد (Series أو dict) يحتوي:
   - RecencyScore
   - FrequencyScore
   - MonetaryScore
   - Segment

المخرجات:

- dict فيه:
   - segment_summary
   - score_breakdown
   - interpretation
   - action_recommendations

الفكرة:

#### 3.1) Score breakdown

- يستخدم `score_to_rating` لإنتاج labels.
- ينتج نص بسيط “Recency: High” إلخ.

#### 3.2) Interpretation حسب segment

الملف عادة يعالج حالات شائعة مثل:

- Champions
- Loyal Customers
- At Risk
- Hibernating

ويعطي توصيات:

- Champions → عروض VIP / upsell
- At Risk → حملات استرجاع / خصومات
- Hibernating → إعادة تفعيل برسائل/تذكير

لماذا هذا مهم للمشروع؟

- لأن segmentation بدون action ليست مفيدة.
- explainability يحوّل segment إلى “قرار”.

---

### 4) lift_interpretation(lift)

في association rules:

- lift > 1 يعني علاقة إيجابية (وجود A يزيد احتمال B)
- lift ≈ 1 يعني لا علاقة
- lift < 1 يعني علاقة سلبية

هذه الدالة تلخص ذلك بجمل قصيرة.

هدفها:

- تحويل مفهوم إحصائي إلى وصف تجاري.

---

### 5) recommendation_strength(confidence, lift)

هذه دالة “تصنيف قوة التوصية”:

- confidence عالي + lift عالي → Strong
- متوسط → Medium
- ضعيف → Weak

الفائدة:

- الواجهة يمكنها أن تلوّن البطاقة (Strong/Medium/Weak)
- أو تعمل sort بناءً على القوة

---

### 6) explain_recommendation(rule_row)

المدخل المتوقع غالبًا صف يحتوي:

- antecedents
- consequents
- support
- confidence
- lift

المخرجات:

- description: “Customers who buy X also buy Y”
- metrics_summary: نص يشرح support/confidence/lift
- interpretation: ناتج lift_interpretation
- strength: ناتج recommendation_strength
- action_items: اقتراحات مثل bundling / cross-sell

أهم نقطة تربطها بالمشروع:

- المشروع لديه `05_recommendation.py` أو مخرجات `product_recommendations.csv`.
- هذا الملف يضع layer شرح فوق تلك النتائج.

---

### 7) ExplainabilityEngine — واجهة موحدة

الـ class عادة يعمل wrappers:

- `explain_forecast(...)`
- `explain_rfm(...)`
- `explain_recommendation(...)`

لماذا class وليس functions فقط؟

- لأنك لاحقًا قد تضيف configuration (لغة، thresholds، formatting)
- أو caching
- أو logging

وبالتالي وجود Engine يحميك من إعادة كتابة الاستدعاءات في كل مكان.

---

### 8) Demo في `__main__`

الملف ينفذ سيناريوهات بسيطة:

- يبني forecast_df sample
- يبني rfm row
- يبني recommendation rule

ثم يطبع النتائج.

هذه الطريقة ممتازة لسببين:

- اختبار سريع أثناء التطوير بدون تشغيل backend.
- توثيق عملي “بالكود” عن شكل المدخلات والمخرجات.

> بهذا اكتمل توثيق `explainability.py`. الخطوة التالية في المنهجية: الانتقال إلى ملفات intelligence/alerts (مثل `src/alert_engine.py` و`src/08_alert_engine.py`) وربطها مباشرة بـ endpoint `/api/alerts` الذي أصلحناه سابقًا.


---

## ملحق 7: شرح نظام التنبيهات Alerts — (`src/alert_engine.py` + `src/08_alert_engine.py`) وربطه بـ `/api/alerts` (Part 1)

هذا الملحق هو أهم “حلقة ربط” بين:

- نتائج التحليلات (forecast, RFM, sentiment…)
- وتجربة المستخدم داخل الـ Dashboard

لأن الـ Dashboard لوحده “سلبي” (Passive). المستخدم لازم يدخل ويتفقد.

أما Alerts فهو “نشط/استباقي” (Proactive):

- النظام يقول للمستخدم: **هذا يحتاج انتباه الآن**.

وهنا تحديدًا نفهم لماذا هذا المشروع يُسوق كـ “Business Assistant” وليس مجرد charts.

---

### 0) خريطة الملفات (من الخارج للداخل)

عندنا ملفان:

1) `src/alert_engine.py`  (Wrapper)
2) `src/08_alert_engine.py` (Core Engine)

السبب:

- اسم الملف الأساسي يبدأ برقم (`08_...`) وهذا قد يسبب صعوبة في الاستيراد المعتاد.
- لذلك يوجد wrapper يصدّر (re-export) الدوال/classes بأسماء “طبيعية” ليسترقها backend بسهولة.

---

### 1) شرح `src/alert_engine.py` (Wrapper)

بداية الملف تقول:

> Provides clean import path for the backend API.

أي أن الهدف ليس ذكاء… الهدف “نظافة الاستيراد”.

#### 1.1) تعديل sys.path

```python
sys.path.insert(0, str(Path(__file__).parent))
```

هذا يجعل Python يرى `src/` كمسار بحث.

#### 1.2) import_module

```python
_module = import_module("08_alert_engine")
run_alert_engine = _module.run_alert_engine
AlertEngine = _module.AlertEngine
BusinessAlert = _module.BusinessAlert
```

هنا “إعادة تصدير” (re-export):

- أي ملف يستورد `from alert_engine import run_alert_engine` سيحصل على الدالة الفعلية داخل `08_alert_engine.py`.

#### 1.3) Fallback stub

إذا فشل import لأي سبب (مفقود dependencies مثل pandas):

- يرجّع structure ثابتة فيها `total_alerts=0` + رسالة error.

هذه فلسفة مهمة:

- لا تكسر الـ API بالكامل.
- لكن لاحظ: backend نفسه في `main.py` لديه أيضًا fallback عند ImportError.

> يعني لدينا طبقتين حماية: wrapper fallback + endpoint fallback.

---

### 2) شرح `src/08_alert_engine.py` — الفكرة العامة

الملف يشرح نفسه في أعلى docstring:

- Alerts مدفوعة بقواعد rule-based.
- تدعم فئات:
   - Sales
   - Customer (RFM)
   - Sentiment (aspect complaints)
   - Forecast

هذا يعني:

- لا يوجد model واحد “يتنبأ بالتنبيه”.
- بل “قواعد” مبنية على thresholds وheuristics.

لماذا rule-based هنا مناسب؟

- سهل الفهم
- سهل التعديل
- ممتاز لبيئة PFE/مشروع تخرج
- يقلل الحاجة لبيانات تدريب labelled alerts

---

### 3) Paths & Logging — لماذا OUTPUT_DIR مهم جدًا؟

```python
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
```

هذه هي نفس الفكرة التي أصلحناها سابقًا في backend:

- أي endpoint يعتمد على ملفات output يجب أن يضمن وجود المجلد.

السبب العملي:

- Alerts تُحفظ كـ JSON في `output/{company}_alerts.json`.
- إذا `output/` غير موجود → 500.

---

### 4) Data Structures: AlertSeverity / AlertCategory / BusinessAlert

#### 4.1) Enums

- `AlertSeverity`: info/warning/critical
- `AlertCategory`: sales/customer/sentiment/forecast/inventory

وجود Enums هنا يساعد:

- ثبات القيم (لا يوجد typo مثل “critcal”).
- سهولة الفرز في UI.

#### 4.2) BusinessAlert dataclass

```python
@dataclass
class BusinessAlert:
      id: str
      category: str
      severity: str
      title: str
      message: str
      recommendation: str
      metric_value: Optional[float] = None
      threshold: Optional[float] = None
      created_at: str = ""
      icon: str = "⚠️"
```

الفكرة هنا: التنبيه ليس مجرد رسالة.

هو object “قابل للعرض والتنفيذ”:

- title/message للعرض
- recommendation للقرار
- metric_value/threshold لشرح لماذا ظهر التنبيه

ثم:

```python
def __post_init__(self):
      if not self.created_at:
            self.created_at = datetime.now().isoformat()
```

أي تنبيه بدون وقت → يُعطى وقت تلقائي.

---

### 5) AlertEngine — قلب النظام

`AlertEngine` لديه:

- `self.alerts`: قائمة التنبيهات
- `self.alert_counter`: لترقيم IDs

والـ ID:

```python
return f"ALT-{self.company_name[:3].upper()}-{self.alert_counter:04d}"
```

يعني:

- ALT-ACM-0001 …

هذا مفيد للـ UI والـ logging.

---

### 6) قواعد Sales Alerts (أمثلة تعليمية)

#### 6.1) check_revenue_decline

- يقارن current vs previous
- إذا الهبوط أكثر من 15% → alert
- إذا أكثر من 30% → critical

هذه “قاعدة” (Rule):

- بسيطة لكنها قوية.

#### 6.2) check_goal_progress

- يحسب expected progress بناءً على الأيام
- إذا متأخر أكثر من 20% عن المتوقع → warning

هذه مهمة لأن:

- الإدارة تفكر في progress نحو الهدف وليس فقط revenue النهائي.

#### 6.3) check_sales_anomaly

- يستخدم z-score مقابل آخر 30 يوم
- إذا اليوم أقل من المتوسط بأكثر من 2 std → warning

هذه “anomaly detection” بسيط.

> في Part 2 سنربط كل هذا بـ `run_alert_engine` وبـ endpoint `/api/alerts` (الكاش، refresh، X-Company-ID، وأنماط الفشل).


---

## ملحق 7: نظام التنبيهات Alerts وربطه بالـ API (Part 2)

Part 2 هو أهم جزء عملي: كيف تتحول القواعد إلى JSON يصل للواجهة.

---

### 1) قواعد Customer Alerts

#### 1.1) check_churning_customers

يدخل `rfm_df`، ثم يبحث عن عمود segment:

- أي عمود اسمه يحتوي “segment”.

ثم يحسب نسبة “At Risk”:

- إذا أكثر من 15% من العملاء → warning.

الفكرة:

- ليس مهم فقط وجود عملاء at risk، المهم أن النسبة “كبيرة”.

#### 1.2) check_vip_customer_inactive

- يبحث عن recency/segment/customer columns.
- لو العميل VIP/Champion/Loyal وrecency أكبر من 60 يوم → info.

ثم يضع limit (حتى 5، وبعدها backend يحدها أكثر).

لماذا limit؟

- لأن UI لو عرضت 200 VIP inactive تصبح noisy.

---

### 2) قواعد Sentiment Alerts

#### 2.1) check_aspect_complaints

يدخل `aspect_data` (من advanced sentiment).

- يتجاهل aspects قليلة الذكر (أقل من 3 mentions).
- إذا negative_pct > 40% → warning
- إذا > 60% → critical

ثم يعطي recommendation حسب aspect via `_get_aspect_action`.

هذه نقطة “ذكاء عملي”:

- نفس التنبيه “شكاوى عالية” لكن recommendation تختلف:
   - delivery → logistics
   - service → تدريب خدمة العملاء
   - packaging → تحسين التغليف

---

### 3) Forecast Alerts

`check_forecast_shortfall`:

- يجمع قيم yhat/forecast
- إذا أقل من 90% من target → warning

لاحظ:

- يستخدم `value_col` عبر البحث عن أسماء تحتوي yhat/forecast.

هذا يكرر فلسفة المشروع:

- تعامل مرن مع اختلاف أسماء الأعمدة.

---

### 4) run_all_checks(data) — كيف يتقرر ماذا يُفحص؟

الدالة تعتمد على “توفر البيانات”:

- إذا موجود current/previous revenue → revenue decline
- إذا موجود daily_sales → anomaly
- إذا موجود rfm_df → churn + VIP inactive
- إذا موجود sentiment_data.aspect_analysis → aspect complaints
- إذا موجود forecast_df + revenue_goal → shortfall

ثم:

- يرتب alerts حسب severity.
- ويرجع list of dicts عبر `asdict`.

هذه خطوة مهمة للـ JSON.

---

### 5) run_alert_engine(company_name) — من أين تأتي البيانات؟

هذه هي نقطة التجميع (Data Loading).

#### 5.1) تحميل RFM

```python
rfm_path = OUTPUT_DIR / f"{company_name}_rfm_segments.csv"
if not rfm_path.exists():
      rfm_path = OUTPUT_DIR / "rfm_segments.csv"
```

يعني:

- إذا لديك outputs per-company استخدمها.
- إذا لا، استخدم output عام.

#### 5.2) تحميل advanced sentiment

- من `output/{company}_advanced_sentiment.json`.

#### 5.3) تحميل sales data

يبحث في عدة أماكن:

- `data/{company}/sales/*.csv`
- أو `data/cleaned_dataset.csv`
- أو `output/merged_data.csv`

هذا “fallback chain”.

ميزة: ما يتعطل بسرعة.
عيب: ممكن يستخدم ملف غير الذي تتوقعه إذا عندك أكثر من مصدر.

> لاحقًا يمكن جعل هذا موحّد عبر pipeline_controller (Canonical inputs).

#### 5.4) حساب current/previous/goal (محاكاة)

هنا يوجد قرار “للتجربة”:

- previous_revenue = current * 1.05
- goal = current * 1.2

هذا ليس production logic.

فكرته:

- يعطي alerts “تعمل” حتى لو ما عندك تقسيم زمني دقيق.

في نسخة Production:

- previous يجب أن يُحسب من date ranges.
- والهدف يجب أن يأتي من Settings أو DB.

#### 5.5) daily sales

إذا وجد عمود تاريخ:

- يحوله datetime
- يجمع daily revenue

وهذا يغذي anomaly detection.

#### 5.6) forecast

- يحاول `output/{company}_forecast_prophet.csv`
- أو `output/forecast.csv`

ثم ينفذ `engine.run_all_checks(data)`.

---

### 6) حفظ Alerts في ملف JSON (الكاش)

```python
output_path = OUTPUT_DIR / f"{company_name}_alerts.json"
json.dump(output, f, ensure_ascii=False, indent=2)
```

هذا هو “الكاش” الذي يستخدمه backend.

النتيجة:

- أول مرة تولّد alerts وتكتب الملف.
- لاحقًا الـ API يعيد نفس الملف بسرعة (بدون إعادة حساب) إلا إذا طلبت refresh.

---

### 7) الربط مع backend: `/api/alerts` في `backend/main.py`

الـ endpoint يعمل كالتالي:

1) يقرأ `X-Company-ID` (افتراضي `Acme Corp`).
2) يبني مسار الكاش:

```python
alerts_path = OUTPUT_DIR / f"{company_id}_alerts.json"
```

3) إذا الملف موجود وrefresh=False → يرجعه مباشرة.
4) إذا لا → يستورد `run_alert_engine` ويولّد جديد.

وهذا يفسر مشكلة “Unexpected token '<'” التي كانت عندنا سابقًا:

- الواجهة كانت تتوقع JSON.
- لكن بدون proxy كانت تضرب سيرفر Vite وترجع HTML.

ثم لما حلينا proxy:

- وصلنا backend.
- لكن backend كان يرجع 500 عندما `OUTPUT_DIR` غير معرّف/غير موجود.

اليوم بعد الإصلاح:

- endpoint يرجع JSON صحيح.

---

### 8) كيف تختبر Alerts عمليًا؟

من PowerShell:

- GET cached/generate:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/alerts" -Headers @{"X-Company-ID"="Acme Corp"}
```

- Force regenerate:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/alerts?refresh=true" -Headers @{"X-Company-ID"="Acme Corp"}
```

أو:

- POST generate:

```powershell
Invoke-WebRequest -Method POST -Uri "http://localhost:8000/api/alerts/generate" -Headers @{"X-Company-ID"="Acme Corp"}
```

---

### 9) ملاحظات هندسية (مهم كطالب)

1) **الكاش file-based** سريع وبسيط، لكنه يحتاج إدارة:
    - متى يتم invalidation؟ (refresh أو حذف output)

2) **company_name داخل اسم الملف**:
    - إذا company فيه مسافات أو رموز، ممكن يظهر اختلاف في filenames.
    - الأفضل لاحقًا normalize company_id.

3) **محاكاة previous/goal**:
    - جميلة للعرض، لكنها ليست Business Accurate.
    - يجب ربطها بـ Settings/DB.

> بهذا نكون وثقنا Alerts end-to-end: من القواعد → إلى JSON → إلى cache → إلى `/api/alerts` → إلى الواجهة.


---

## ملحق 8: التحليل العاطفي المتقدم Advanced Sentiment (Arabic‑First) — (`src/advanced_sentiment.py` + `src/07_advanced_sentiment.py`) وربطه بـ `/api/advanced-sentiment` (Part 1)

هذا الملحق يشرح “ميزة قاتلة” في المشروع: بدل ما نقول للمستخدم:

- “المراجعة إيجابية/سلبية”

نقول:

- “العميل يحب **الجودة** لكنه يشتكي من **التوصيل**”

وهذا يعطي إدارة العمليات/Product team شيئًا قابلًا للتنفيذ.

---

### 0) لماذا لدينا ملف Wrapper أيضًا؟

مثل Alerts، يوجد ملفان:

1) `src/advanced_sentiment.py` (Wrapper)
2) `src/07_advanced_sentiment.py` (Core)

السبب:

- الملف الأساسي يبدأ برقم (`07_...`) فالوصول له عبر import “قد يكون مزعج”.
- الـ backend يريد استيراد اسم بسيط: `from advanced_sentiment import run_advanced_sentiment_analysis`.

---

### 1) شرح `src/advanced_sentiment.py` (Wrapper)

الملف يعمل 3 أشياء فقط:

1) يضيف `src/` إلى `sys.path`.
2) يستورد `07_advanced_sentiment` عبر `import_module`.
3) يعيد تصدير:
   - `run_advanced_sentiment_analysis`
   - `analyze_review`
   - `generate_aspect_insights`
   - `ASPECT_KEYWORDS`

وعند ImportError:

- يرجع stub JSON منظم (total_reviews=0 …) بدل crash.

> نفس فلسفة “API لا ينكسر بالكامل”.

---

### 2) نظرة عامة على `src/07_advanced_sentiment.py`

الملف يعلن هدفه بوضوح:

- Arabic‑First Aspect‑Based Sentiment.

هذا يعني:

- دعم عربي “فعلي” عبر كلمات عربية وإشارات Unicode.
- استخراج Aspects محددة (quality/price/delivery/service/packaging).
- بناء Alerts/Recommendations بناء على النسب.

مهم جدًا: هذا implementation rule‑based/keyword‑based.

ميزة:

- سريع، مفهوم، مناسب للمشروع.

قيود:

- يعتمد على الكلمات المفتاحية وقد يفشل مع sarcasm أو لهجات.

---

### 3) Paths & Logging

نفس النمط:

- `OUTPUT_DIR` لحفظ النتائج كـ JSON.
- `LOGS_DIR` لملف `advanced_sentiment.log`.

وهذا يربط مباشرة بـ endpoint:

- `/api/advanced-sentiment` يبحث عن `output/{company}_advanced_sentiment.json`.

---

### 4) تعريف الجوانب ASPECT_KEYWORDS

هذا أهم قاموس في الملف:

- لكل aspect (مثل quality) توجد:
  - كلمات عربية `ar`
  - كلمات إنجليزية `en`
  - icon للـ UI

فكرة التصميم:

- أنت لا “تكتشف موضوعات” عشوائيًا.
- أنت تقول مسبقًا: “هذه أهم 5 جوانب في التجارة الإلكترونية”.

وهذا عملي جدًا للـ dashboard.

---

### 5) ARABIC_POSITIVE / ARABIC_NEGATIVE

هذه قوائم مشاعر عربية بسيطة:

- إيجابي: ممتاز، رائع، أنصح…
- سلبي: سيء، غش، تأخير…

ملاحظة تعليمية:

- هذا ليس NLP عميق.
- لكنه baseline ممتاز.

---

### 6) detect_language(text)

الفكرة:

- يستخدم regex يلتقط حروف عربية (`\u0600-\u06FF`).
- يحسب ratio مقارنة بعدد الحروف.
- إذا ratio > 0.3 → Arabic.

لماذا 0.3؟

- لأنه يوجد reviews قد تحتوي emojis/أرقام/إنجليزي مع كلمات عربية.
- threshold بسيط لإعطاء قرار.

> في Part 2 سنشرح: extract_aspects + analyze_review + generate_aspect_insights + run_advanced_sentiment_analysis ثم الربط مع API والكاش والـ refresh.


---

## ملحق 8: Advanced Sentiment وربطه بالـ API (Part 2)

Part 2 هو “المسار الكامل” من reviews.csv إلى JSON جاهز للواجهة.

---

### 1) extract_aspects(text, language)

المنطق:

- يمر على كل aspect
- يأخذ keywords حسب اللغة
- إذا وجد أي keyword داخل النص → يضيف aspect

ملاحظة:

- هذا extraction “وجود/عدم وجود”.
- لا يحسب كثافة أو position.

ميزة:

- بسيط وسريع.

تطوير محتمل:

- stemming/normalization للهجات العربية.

---

### 2) get_aspect_sentiment(text, aspect, language)

المنطق:

- لو عربي: يعد كلمات إيجابية وسلبية من القوائم.
- لو إنجليزي: يستخدم قائمة صغيرة أيضًا.

ثم:

- pos > neg → positive
- neg > pos → negative
- else → neutral

لاحظ:

- الدالة لا تستخدم aspect فعليًا في الحساب إلا كـ parameter.
- أي أنها تحسب sentiment على النص كامل، وليس “حول aspect فقط”.

هذا قيد معروف.

لكن في مشروع تخرج، هذا مقبول ويعطي نتائج مفيدة عمليًا.

---

### 3) analyze_review(text)

هذه أهم دالة للوحدة:

#### 3.1) Guard clauses

- لو النص قصير جدًا أو غير صالح → neutral بثقة 0.

#### 3.2) language + aspects

- يحدد اللغة
- يستخرج aspects

#### 3.3) aspect_sentiments

- لكل aspect موجود في النص → يحسب sentiment.

#### 3.4) overall sentiment + confidence

- يعيد حساب pos/neg للنص.
- يقرر overall.
- يبني confidence (0.5 baseline، وتزيد حسب الفرق).

هذا ممتاز للواجهة:

- يمكنك إظهار “ثقة تقريبية” بدل قرار قطعي.

---

### 4) generate_aspect_insights(results_df)

هنا “القيمة التجارية” الحقيقية.

المدخل:

- DataFrame ناتج من analyze_review لكل مراجعة.

المخرجات:

- summary: لكل aspect
  - total_mentions
  - positive_pct
  - negative_pct
  - icon
- alerts: عندما negative_ratio > 0.4 وmentions >= 3
- recommendations: عندما positive_ratio > 0.7 وmentions >= 3

لاحظ تطابق thresholds مع alert_engine:

- في alert_engine (Part 7) كانت aspect complaints > 40% ترفع alert.
- هنا module sentiment نفسه يولد alerts أيضًا.

هذا قرار تصميم:

- sentiment module ينتج “alerts محلية” (داخل نتائج sentiment).
- alert_engine ينتج “alerts عامة” عبر كل الأنظمة.

---

### 5) get_aspect_recommendation(aspect, sentiment_type)

قاموس توصيات جاهز:

- delivery negative → audit logistics + SLAs
- service negative → تدريب + response time
- price negative → competitor pricing + bundles

هذه توصيات “business‑oriented” وليست تقنية.

---

### 6) run_advanced_sentiment_analysis(company_name)

هذه هي entry point التي يستدعيها الـ backend.

#### 6.1) البحث عن ملف المراجعات

- يبحث في `data/{company}/reviews/*.csv`.
- إذا لم يجد، fallback إلى `output/sentiment_analysis.csv`.

هذا fallback chain مثل alert_engine.

#### 6.2) اكتشاف عمود النص

يبحث ضمن أسماء محتملة مثل:

- ReviewText / review_text / comment / feedback …

إذا لم يجد → error.

#### 6.3) تحليل كل review

- يمر على الصفوف
- يبني result لكل review
- يحفظ original_text

ثم يبني results_df.

#### 6.4) إحصائيات عامة

- language_distribution
- sentiment_distribution (+ positive_rate)
- average_confidence

#### 6.5) aspect_analysis + alerts + recommendations

- يأخذ `insights["summary"]` إلى `aspect_analysis`.
- يأخذ alerts/recommendations الناتجة.

#### 6.6) حفظ JSON في output

- `output/{company}_advanced_sentiment.json`

وهذا بالضبط ما يستخدمه endpoint كـ cache.

---

### 7) الربط مع backend: `/api/advanced-sentiment`

الـ endpoint يعمل هكذا:

1) يقرأ `X-Company-ID` (افتراضي Acme Corp).
2) يبحث عن cache:

- `output/{company}_advanced_sentiment.json`

3) إذا موجود وrefresh=False → يرجعه مباشرة.
4) إذا refresh=True أو الملف غير موجود → يشغّل:

- `run_advanced_sentiment_analysis(company_id)`

وبالتالي أنت فهمت الآن:

- من أين يأتي `aspect_analysis` الذي يستخدمه alert_engine داخل `check_aspect_complaints`.

---

### 8) كيف تختبر endpoint عمليًا؟

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/advanced-sentiment" -Headers @{"X-Company-ID"="Acme Corp"}
```

وإجبار إعادة التحليل:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/advanced-sentiment?refresh=true" -Headers @{"X-Company-ID"="Acme Corp"}
```

---

### 9) ملاحظات تحسين (مهمة في التقرير)

1) **Aspect sentiment ليس aspect‑scoped فعليًا**:
   - الآن يحسب sentiment على النص ككل.
   - تطوير: window around aspect keyword أو dependency parsing.

2) **الكلمات العربية تحتاج normalization**:
   - (تاء مربوطة/هاء، همزات، مد…)
   - إضافة preprocessing ستزيد الدقة.

3) **threshholds**:
   - 0.4 و0.7 قرارات عملية.
   - يمكن جعلها Settings per-company.

> بهذا اكتمل توثيق advanced sentiment end‑to‑end، وهو مصدر رئيسي لـ Alerts/Intelligence Summary.


---

## ملحق 9: CLV (Customer Lifetime Value) — (`src/clv_calculation.py` + `src/09_clv_calculation.py`) وربطه بـ `/api/clv` (Part 1)

هذا الملحق يشرح “تقييم قيمة العميل على مدى عمر العلاقة” وليس فقط آخر شراء.

**CLV يجاوب سؤال إداري حساس جدًا:**

- كم يستاهل أن أدفع لاكتساب عميل؟
- من هم العملاء الذين يجب الحفاظ عليهم بأي ثمن؟

---

### 0) نفس فلسفة wrapper/core

يوجد ملفان:

1) `src/clv_calculation.py` (Wrapper)
2) `src/09_clv_calculation.py` (Core)

السبب:

- core اسمه يبدأ برقم.
- backend يستورد اسم نظيف: `from clv_calculation import run_clv_analysis`.

الـ wrapper يعيد تصدير:

- `run_clv_analysis`
- `calculate_historical_clv`
- `calculate_average_clv`
- `calculate_predictive_clv`
- `assign_clv_segments`
- `generate_clv_insights`

وعند فشل الاستيراد:

- يرجع stub فيه insights فارغة بدل crash.

---

### 1) لماذا هذا الملف (Business Value)

المقدمة داخل `09_clv_calculation.py` واضحة جدًا:

1) Marketing budget (CAC)
2) Segmentation حقيقي بالقيمة
3) Prioritization (VIP)
4) Forecasting لقيمة قاعدة العملاء

---

### 2) Paths & Logging

```python
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
```

ثم إنشاء المجلدات.

هذه نقطة ربط مباشرة بالـ API:

- ناتج CLV يُحفظ كملفين:
   - `output/{company}_clv_analysis.csv`
   - `output/{company}_clv_insights.json`

والـ backend يعامل `*_clv_insights.json` كـ cache.

---

### 3) calculate_historical_clv — أبسط شكل

الفكرة:

- CLV = مجموع الإيرادات التي دفعها العميل تاريخيًا.

الكود:

- groupby customer
- sum revenue
- ينتج عمود `historical_clv`.

ميزة:

- واقعي 100%.

عيب:

- لا يتنبأ بالمستقبل.

---

### 4) calculate_average_clv — معادلة مفهومة إداريًا

المعادلة:

> CLV = AOV × Purchase Frequency × Average Lifespan

الخطوات داخل الكود:

1) حساب per-customer:
    - total revenue
    - average order value
    - purchase count
    - first/last purchase

2) حساب tenure:
    - tenure_days = (last-first)+1
    - tenure_years = tenure_days / 365.25

3) purchase_frequency:

- purchases per year
- مع `clip(lower=0.1)` لتجنب division by zero.

4) average_clv:

- `avg_order_value * purchase_frequency * avg_lifespan_years`

لاحظ:

- `avg_lifespan_years` افتراضي 2.0.
- هذا قرار business/industry وليس “قانون رياضي”.

> في Part 2 سنشرح predictive CLV، التقسيم إلى segments، توليد insights، ثم `run_clv_analysis` وربطه بـ `/api/clv` و`/api/clv/segments`.


---

## ملحق 9: CLV وربطه بالـ API (Part 2)

Part 2 هو الطريق الكامل: من sales.csv → إلى CLV segments → إلى JSON للواجهة.

---

### 1) calculate_predictive_clv — نموذج احتمالي مبسط

الفكرة:

- نتوقع الإيراد السنوي:
   - `avg_order_value * purchase_frequency`

ثم نحسب القيمة الحالية (NPV) لسنوات مستقبلية عبر:

- retention_rate = 1 - churn_rate
- discount_factor = 1 / (1+discount_rate)^year

ثم مجموع:

- expected_revenue × survival_prob × discount

ملاحظة تعليمية:

- هذا ليس BG/NBD الحقيقي، لكنه approximation ممتاز للمشروع.
- parameters (churn_rate/discount_rate/projection_years) قابلة للضبط.

---

### 2) assign_clv_segments — تقسيم العملاء بالقيمة

المنطق:

- يحسب quartiles/percentiles:
   - p40, p70, p90

ثم:

- >= p90 → Platinum
- >= p70 → Gold
- >= p40 → Silver
- else → Bronze

لماذا هذا تقسيم قوي؟

- لأنه relative للبيانات (لا يعتمد على رقم ثابت).
- يتكيف مع الشركات الصغيرة والكبيرة.

---

### 3) generate_clv_insights — تحويل أرقام إلى قرارات

ينتج 3 أقسام:

1) summary
2) segments breakdown
3) recommendations

#### 3.1) Summary

- total_customers
- total_clv
- average/median/std

#### 3.2) Segments

- count/total_clv/avg_clv لكل segment
- pct_of_total: كم نسبة قيمة الشركة تأتي من هذا segment

#### 3.3) Recommendations

- إذا Platinum موجود:
   - “VIP loyalty program”
- إذا Bronze كبير:
   - “upgrade path”
- CAC recommendation:
   - قاعدة: CAC < 30% من CLV

هذه قاعدة عملية وليست ثابتة (تختلف حسب الصناعة).

---

### 4) run_clv_analysis(company_name) — من أين تأتي البيانات؟

الملف يبحث عن sales عبر chain:

- `data/{company}/sales/*.csv`
- `output/{company}_merged_data.csv`
- `output/merged_data.csv`
- `data/cleaned_dataset.csv`

ثم يحاول resolve الأعمدة عبر candidates:

- customer_col (CustomerID…)
- revenue_col (TotalPrice/Price/Revenue…)
- date_col (OrderDate/Date…)

إذا لا يوجد customer_id أو revenue → يرجع error.

ثم cleaning:

- dropna customer/revenue
- revenue > 0

ثم الحساب:

- إذا يوجد date_col:
   - average_clv + predictive_clv
- إذا لا:
   - historical فقط، ويجعل `average_clv = historical_clv`

ثم:

- assign segments
- generate insights

#### 4.1) دمج RFM (ميزة إضافية)

إذا وجد `output/{company}_rfm_segments.csv` (أو fallback):

- يدمج RFM مع CLV لتكوين صورة أغنى.

> هنا تظهر فكرة “Intelligence layer”: ليس كل تحليل منفصل، بل يمكن دمج outputs.

#### 4.2) حفظ النتائج

- CSV: `output/{company}_clv_analysis.csv`
- JSON: `output/{company}_clv_insights.json`

ويضيف `top_customers` (أعلى 10 حسب average_clv).

---

### 5) الربط مع backend: `/api/clv`

في `backend/main.py`:

1) يقرأ `X-Company-ID`.
2) يفحص الكاش:

- `output/{company}_clv_insights.json`

3) إذا موجود وrefresh=False → يرجعه.
4) إذا refresh=True أو الملف غير موجود → يستدعي:

- `run_clv_analysis(company_id)`

---

### 6) Endpoint إضافي: `/api/clv/segments`

هذا endpoint يعتمد على CSV:

- `output/{company}_clv_analysis.csv`

إذا الملف غير موجود:

- يستدعي `get_customer_clv(refresh=True)` لتوليده.

ثم يقرأ CSV ويجمع:

- count/sum/mean حسب segment.

---

### 7) اختبار سريع

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/clv" -Headers @{"X-Company-ID"="Acme Corp"}
```

إعادة حساب:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/clv?refresh=true" -Headers @{"X-Company-ID"="Acme Corp"}
```

Segments:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/clv/segments" -Headers @{"X-Company-ID"="Acme Corp"}
```

> بهذا اكتمل توثيق CLV end‑to‑end: من sales data → إلى CLV metrics → إلى segments → إلى insights JSON → إلى API.




---

## ملحق 10: Forecasting (تنبؤ المبيعات) — (`src/03_forecasting.py` + `src/03_forecasting_prophet.py`) وربطه بـ `/api/monthly-sales`

في هذا الملحق سنفهم “كيف المشروع يتنبأ بالمبيعات المستقبلية” بطريقتين:

1) **Baseline بسيط (Linear Regression)** داخل `src/03_forecasting.py`.
2) **نسخة أقوى علميًا (Prophet)** داخل `src/03_forecasting_prophet.py`.

والأهم: سنربط النتيجة بالـ backend endpoint:

- `/api/monthly-sales`

الذي يعرض للواجهة “Actual + Forecast” معًا.

---

### Part 1 — فهم `src/03_forecasting.py` خطوة بخطوة (Baseline)

#### 0) لماذا يوجد Forecasting أصلاً؟ (Business)

التنبؤ يجاوب أسئلة عملية:

- هل المبيعات تصعد أم تنخفض؟
- كم نتوقع الشهر القادم؟
- هل نحتاج Stock / Budget / حملة تسويق؟

وبالواجهة: chart monthly sales يحتاج “جزء مستقبل” حتى يظهر خط التوقع.

---

#### 1) Paths & Logging (علاقة مباشرة بالمجلدات)

الملف يعرّف مسارات ثابتة:

```python
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
```

ثم ينشئ المجلدات إذا لم تكن موجودة.

هذه النقطة مهمة لأن الـ backend لاحقًا يقرأ ملفات التنبؤ “من disk” (ليس من memory).

---

#### 2) Schema Resolver Integration (لماذا؟)

المشكلة التي يحلها هنا:

- datasets تأتي بأسماء أعمدة مختلفة.

إذًا الملف يحاول استيراد:

```python
from schema_resolver import SchemaResolver, SemanticField, can_perform_analysis
```

إذا نجح الاستيراد → يستخدم resolver لتحديد:

- عمود التاريخ (ORDER_DATE)
- عمود القيمة/الإيراد (TOTAL_PRICE)

وإذا لم يتوفر resolver → يستخدم fallback list:

- date_cols مثل `OrderDate`, `Date`, `ds`...
- value_cols مثل `TotalPrice`, `Revenue`, `Sales`...

**النتيجة التعليمية:**

بدل ما نقول “لازم اسم العمود OrderDate”، نحن نقول “لازم معنى العمود يكون تاريخ مبيعات” حتى لو اسمه مختلف.

---

#### 3) `find_data_file()` — من أين يقرأ البيانات؟

هذه الدالة تبحث بالترتيب:

1) `data/cleaned_dataset.csv`
2) `data/sales.csv`
3) `data/merged_data.csv`

هذا يعني:

- لو Phase 1 (EDA) أنتج `cleaned_dataset.csv` → هذا هو المصدر المفضل.
- لو لم يوجد → يرجع لـ `sales.csv` (النسخة الخام).

---

#### 4) `load_and_prepare_data()` — تجهيز البيانات للتنبؤ

هنا أهم خطوة: تحويل بيانات المبيعات “إلى مستوى شهري” لأن التنبؤ هنا شهري.

الخطوات المفاهيمية:

1) قراءة CSV إلى DataFrame.
2) تحديد أعمدة (date/value) عبر resolver أو fallback.
3) إعادة تسمية الأعمدة إلى أسماء معيارية:
   - `OrderDate`
   - `TotalPrice`
4) تحويل `OrderDate` إلى datetime.
5) جعل `OrderDate` index.
6) **resample شهري:**

```python
monthly_sales = (
   df.resample("MS")["TotalPrice"].sum().reset_index()
)
```

`MS` معناها Month Start (أول يوم بالشهر) وهذا ممتاز لتوحيد الأشهر.

7) تنظيف:
   - حذف الأشهر ذات `TotalPrice <= 0`.
8) إضافة `TimeIndex` = 0..n-1 حتى نقدر نطبق regression بسهولة.

**النتيجة:** جدول صغير (عدد نقاطه = عدد الأشهر).

---

#### 5) استراتيجية التنبؤ داخل `main()`

داخل `main()`:

- `periods = 6` (يتوقع 6 أشهر أمام)
- يحسب `n_months = len(monthly_sales)`

ثم يقرر:

1) إذا `n_months >= 3` → يستخدم Regression.
2) إذا `n_months == 2` → Regression أيضًا لكن يطبع تحذير.
3) إذا أقل من ذلك → Naive forecast (تكرار آخر قيمة).

**ليش هذا مهم؟**

لأن forecast “لازم يطلع” حتى لو البيانات قليلة، لكن مع تحذير واضح أن الجودة ضعيفة.

---

#### 6) `regression_forecast()` — ما الذي يفعله بالضبط؟

الفكرة هنا:

- نجعل الزمن “رقم” (TimeIndex)
- ونجعل المبيعات “هدف” (y)
- ثم linear regression:

$$y = a \cdot t + b$$

الميزة الأساسية في هذا الملف: لو البيانات كافية (>=6 أشهر) يعمل split زمني:

- 80% train
- 20% validation

ويحسب metrics على validation (Out-of-sample) ثم يعيد تدريب على كل البيانات لإنتاج forecast النهائي.

إذا البيانات قليلة → يحسب metrics in-sample فقط ويعطي warning أنها غير موثوقة.

**هذا سلوك “تعليمي + واقعي”:** يفرق بين metrics حقيقية وmetrics “على نفس التدريب”.

---

#### 7) `plot_forecast()` — الرسم الذي تظهر صورته في output

يولد رسمًا بسيطًا:

- خط actual
- خط forecast

ويحفظه هنا:

- `output/plots/sales_forecast.png`

---

#### 8) Output CSV الأساسي لهذا الملف

في النهاية:

```python
forecast_df = pd.DataFrame({
   "OrderDate": future_dates,
   "ForecastedSales": future_sales
})
forecast_df.to_csv(DATA_DIR / "sales_forecast.csv", index=False)
```

إذًا الملف يكتب:

- `data/sales_forecast.csv`

وهذا مهم جدًا لأن الـ backend endpoint `/api/monthly-sales` يبحث ضمن مصادر forecast.

---

### Part 2 — فهم `src/03_forecasting_prophet.py` (Production‑grade)

هذا الملف يقدم نسخة أقوى من التنبؤ:

- Prophet يتعامل مع seasonality + trend + uncertainty.

#### 1) Prophet Import with Fallback

```python
try:
   from prophet import Prophet
   PROPHET_AVAILABLE = True
except ImportError:
   PROPHET_AVAILABLE = False
```

معنى ذلك:

- لو Prophet غير مثبت → المشروع لا ينهار، لكنه سيستخدم baseline فقط.

---

#### 2) `find_sales_file(company_name)` — بحث multi‑tenant

هنا الملف يدعم multi-company directories:

1) `data/{company}/sales/cleaned_sales.csv`
2) `data/{company}/sales/*.csv`
3) fallback:
   - `data/cleaned_dataset.csv`
   - `data/sales.csv`
   - `data/merged_data.csv`

هذا يتوافق مع فلسفة النظام: كل شركة لها مجلدها.

---

#### 3) `load_and_prepare_data()` — aggregation شهري + auto-detect

الملف يعمل auto-detect للأعمدة (date/revenue) بدون SchemaResolver هنا:

- `date_candidates`
- `revenue_candidates`

ثم يحول الأعمدة إلى أسماء معيارية (`OrderDate`, `TotalPrice`)، وبعدها:

```python
monthly_sales = (
   df.groupby(pd.Grouper(key="OrderDate", freq="MS"))["TotalPrice"].sum()
)
```

لاحظ الفرق:

- في baseline استخدم `resample` بعد set_index.
- هنا استخدم `groupby(Grouper)`.

النتيجة نفسها: monthly time-series.

---

#### 4) baseline_linear_regression() موجود للمقارنة

يحسب R2/MAE/RMSE على التاريخ (in-sample) ثم يولد forecast مع interval ±10% (تقريبي).

الغرض هنا:

- مقارنة بسيطة: baseline vs prophet.

---

#### 5) prophet_forecast() — ماذا ينتج؟

Prophet يتطلب dataframe بشكل:

- `ds` = التاريخ
- `y` = القيمة

ثم ينشئ model:

- `seasonality_mode='multiplicative'`
- `interval_width=0.95`
- `changepoint_prior_scale=0.05`

ويعيد:

1) `metrics`: MAE/RMSE/MAPE
2) `forecast`: future predictions (`ds`, `yhat`, `yhat_lower`, `yhat_upper`)
3) `components`: trend/yearly decomposition

---

#### 6) Outputs التي يكتبها Prophet

داخل `run_forecasting(company_name)`:

- baseline:
  - `output/{company}_forecast_baseline.csv`

- prophet (إذا متوفر):
  - `output/{company}_forecast_prophet.csv`
  - plots:
   - `output/plots/{company}_forecast_comparison.png`
   - `output/plots/{company}_forecast_components.png`

---

### Part 3 — الربط مع backend: `/api/monthly-sales`

داخل `backend/main.py` توجد وظيفة مهمة: `load_forecast_data()`.

هي تبحث عن forecast من أكثر من مصدر (لأن عندنا ملفين Forecasting):

1) `data/sales_forecast.csv` (من `03_forecasting.py`)
2) `data/sales_forecast_future.csv`
3) `output/Acme Corp_forecast_prophet.csv` (من `03_forecasting_prophet.py`)
4) `data/forecast.csv`

ثم تعمل normalization للأعمدة:

- date: ممكن يكون `MonthStart` أو `ds` أو `OrderDate`...
- forecast: ممكن يكون `ForecastedSales` أو `yhat`...

ثم endpoint `/api/monthly-sales`:

1) يحسب actual شهريًا من sales (بعد normalize).
2) يضيف forecast من `load_forecast_data()`.
3) يدمج actual + forecast في قائمة واحدة مرتبة.

**ملاحظة مهمة (طلاب كثير يغلطون فيها):**

الـ API هنا لا يشغل forecasting تلقائيًا؛ هو “يقرأ forecast الموجود على disk”.

يعني لازم أحد هذه الأشياء يحدث:

- تشغل `src/03_forecasting.py` أو `src/03_forecasting_prophet.py` يدويًا.
- أو تتأكد أن pipeline يضيف هذه المرحلة (لو رغبت مستقبلًا).

---

## ملحق 11: RFM Segmentation — (`src/04_rfm.py`) وربطه بـ `/api/segmentation` و`/api/rfm`

RFM = Recency / Frequency / Monetary.

هو تقسيم عملاء بناءً على:

- **Recency:** آخر مرة اشترى فيها العميل (بالأيام)
- **Frequency:** عدد الطلبات
- **Monetary:** إجمالي الإنفاق

الهدف: نخرج Segments مفهومة إداريًا مثل Champions / At Risk / Lost...

---

### 1) Paths & Logging

نفس منطق الملفات السابقة:

- Logs: `logs/rfm.log`
- Plots: `output/plots/`
- Output CSV: `data/rfm_table.csv`

---

### 2) حل مشكلة “اختلاف أسماء الأعمدة” (Schema Resolver)

`resolve_rfm_columns(df)` يرجع 3 أعمدة أساسية:

- date
- customer
- value

إذا Schema Resolver متوفر → يستخدم `SemanticField`.
إذا لا → fallback lists.

---

### 3) أهم قرار تصميم هنا: RFM يتطلب CustomerID

داخل `load_and_validate_data()`:

- إذا `CustomerID` غير موجود → لا يعتبر هذا “خطأ قاتل”.
- بل يعتبره “analysis غير ممكن” ويعمل:

1) يطبع warning واضح.
2) يرجع `None`.

ثم داخل `main()`:

```python
df = load_and_validate_data()
if df is None:
   sys.exit(0)
```

**معنى ذلك:**

- الـ pipeline لا ينهار بسبب غياب CustomerID.
- لكن لن يوجد `data/rfm_table.csv` وبالتالي الـ API سيرجع 204.

---

### 4) `calculate_rfm()` — الحساب الفعلي

Reference date = أكبر تاريخ في البيانات.

ثم groupby على CustomerID:

- Recency: الأيام منذ آخر شراء
- Frequency: count of orders
- Monetary: sum of TotalPrice

الناتج: جدول (صف لكل عميل).

---

### 5) `score_metric()` — تحويل أرقام إلى Scores 1..5

الفكرة التعليمية:

- لا نريد Recency بالأيام فقط.
- نريد “درجة” حتى نبني segmentation بسهولة.

يستخدم `pd.qcut(q=5)` لعمل quantile binning.

الحالة الخاصة المهمة:

- Recency: **الأقل أفضل** (العميل الذي اشترى أمس أفضل من الذي اشترى قبل 200 يوم).
- لذلك يضع labels معكوسة: `[5,4,3,2,1]`.

ولو qcut فشل (قيم قليلة) → fallback ranking.

---

### 6) `add_rfm_scores()` — تجميع R/F/M

ينتج:

- `R_Score`, `F_Score`, `M_Score`
- `RFM_Score` كـ string مثل "545".

هذا الرقم يسهّل لاحقًا قواعد التقسيم.

---

### 7) `classify_customers()` — تحويل Scores إلى Segments

الدالة `get_segment(r,f,m)` تعطي segment حسب قواعد بسيطة:

- Champions: r>=4 & f>=4 & m>=4
- Loyal Customers: r>=4 & f>=3 & m>=3
- At Risk: r<=2 & f>=3
- Lost: r<=2 & f<=2
...

هذه القواعد ليست “قانون عالمي”، لكنها نموذج ممتاز للمشروع.

**ملحوظة مهمّة للطالب:**

هنا segmentation مبني على scores وليس على القيم الخام.

---

### 8) Plots (output/plots)

`plot_rfm_distribution()` يولّد 3 رسومات:

1) `rfm_heatmap.png` (Recency vs Frequency)
2) `rfm_segments.png` (توزيع العملاء حسب segment)
3) `rfm_metrics_distribution.png` (Histograms)

---

### 9) Output CSV

يحفظ:

- `data/rfm_table.csv`

وبداخله أعمدة مثل:

- CustomerID
- Recency/Frequency/Monetary
- R_Score/F_Score/M_Score
- Segment

---

### 10) الربط مع Pipeline في backend

داخل `backend/main.py` في `run_full_sales_pipeline()`:

- Step 4 يشغل `src/04_rfm.py`.

ومهم جدًا: backend يعتبر خروج RFM غير قاتل:

- إذا `returncode != 0` يطبع warning.
- وحتى لو `CustomerID` غير موجود فالسكربت يخرج 0.

---

### 11) الربط مع API: `/api/segmentation` و`/api/rfm`

في backend:

- يوجد `_get_rfm_segmentation_data(request)`

خصائصه:

1) يقرأ دائمًا من disk (FRESH) من `data/rfm_table.csv`.
2) إذا الملف غير موجود أو فارغ → يرجع `204 No Content`.
3) إذا عمود `Segment` غير موجود → يرجع 204.
4) يبني `RFMSegmentResponse` لكل segment:
   - customer_count
   - avg_recency/avg_frequency/avg_monetary
   - color (مع dictionary)

ثم endpointين:

- `/api/segmentation` → يرجع نفس الدالة
- `/api/rfm` → alias

---

## ملحق 12: Product Recommendations (Market Basket) — (`src/05_recommendation.py`) وربطه بـ `/api/recommendations`

هذا الملحق يشرح كيف النظام يعمل “توصيات منتجات” بناءً على سلوك الشراء المشترك.

فكرة Market Basket:

- إذا كثير من الناس يشترون A مع B
- إذًا عندما يشتري العميل A، اقترح عليه B

هذه ليست “AI تخمين”، بل قواعد Association Rules.

---

### 1) Inputs المتوقعة (بدون ما نكون متشددين بالأسماء)

الملف يستخدم Schema Resolver لو توفر، أو fallback.

يحتاج عادة أعمدة مثل:

- معرف الطلب (OrderID) أو شيء يعبر عن “سلة الشراء”
- المنتج (ProductID / SKU / Product)

وفي كثير من datasets يكون عندنا صف لكل item داخل order.

---

### 2) Pipeline العام داخل `main()`

الملف منظم جدًا على شكل خطوات واضحة:

1) Load & validate
2) Analyze basket composition
3) Encode baskets
4) Mine association rules
5) Format for display
6) Plot + Save

وهذه نقطة ممتازة تعليميًا: كل مرحلة لها هدف واضح.

---

### 3) `analyze_basket_composition()` — فحص جودة البيانات قبل التعدين

هذا الجزء يسأل سؤالًا مهمًا:

هل عندنا “طلبات تحتوي أكثر من منتج”؟

لأن rules لا تظهر إذا كل order فيها منتج واحد فقط.

إذا نسبة multi_product قليلة جدًا (<1%) يطبع warning:

- rules ستكون sparse أو غير موثوقة.

---

### 4) `encode_baskets()` — تحويل السلال إلى مصفوفة Boolean

هنا جوهر Apriori:

- كل row = order
- كل column = product
- القيمة = True/False هل المنتج موجود داخل هذا order

عمليًا يستخدم `MultiLabelBinarizer` أو منطق مشابه لتكوين matrix.

هذه هي البيانات التي يفهمها Apriori.

---

### 5) `mine_association_rules()` — Apriori + association_rules

الملف يعتمد على `mlxtend`:

- `apriori`
- `association_rules`

ويضع thresholds:

- `min_support=0.01`
- `min_confidence=0.1`

ثم يفلتر غالبًا:

- `lift > 1.0`

**تفسير lift ببساطة:**

- lift > 1 يعني وجود B مع A أكثر من المتوقع “عشوائيًا” → قاعدة مفيدة.

---

### 6) نقطة سلوك مهمة جدًا: حذف ملف توصيات قديم إذا فشل التعدين

في `main()` لو `mine_association_rules` فشل (ValueError) بسبب dataset صغير:

1) يطبع تحذير.
2) يحاول حذف:
   - `data/product_recommendations.csv`

والسبب:

- منع “stale recommendations” من الظهور في الـ API.

هذه حركة ذكية جدًا في نظام analytics.

---

### 7) `format_rules_for_display()` — تجهيز النتائج للواجهة والقراءة

حتى لو rules داخل dataframe تحتوي antecedents/consequents كـ sets، هذا ليس مناسبًا للعرض.

التنسيق ينتج أعمدة مفهومة مثل:

- `RuleID`
- `IF (Buy)`
- `THEN (Recommend)`
- `Support`
- `Confidence`
- `Lift`

ثم يطبع top 5 في logs.

---

### 8) Visualizations (3 رسومات)

الدالة `plot_association_rules(rules, PLOTS_DIR)` تنتج 3 صور:

1) `rules_scatter.png` (Support vs Confidence مع لون/حجم للـ lift عادة)
2) `top_rules_by_lift.png` (أقوى قواعد حسب lift)
3) `rules_metrics_distribution.png` (توزيعات support/confidence/lift)

هذه الصور تحفظ في:

- `output/plots/`

---

### 9) Output CSV الأساسي

يحفظ النتائج هنا:

- `data/product_recommendations.csv`

بـ encoding utf-8.

---

### 10) الربط مع Pipeline في backend

داخل `backend/main.py` في `run_full_sales_pipeline()`:

- Step 5 يشغل `src/05_recommendation.py`.

ولو فشل لا يوقف النظام بالكامل (warning)، لأن recommendation “تحسين” وليس شرطًا لعمل بقية النظام.

---

### 11) الربط مع API: `/api/recommendations`

endpoint في backend يقرأ دائمًا FRESH من disk:

- `data/product_recommendations.csv`

سلوكاته:

1) إذا الملف غير موجود → `204 No Content`.
2) إذا الملف فارغ → 204.
3) يفلتر `Confidence > 0`.
4) يرتّب حسب `Lift` تنازليًا.
5) يطبق `limit` (افتراضي 10).

ثم يبني response مرن لأنه يدعم أسماء أعمدة مختلفة (IF/THEN/Antecedent/Consequent...).

---

### 12) اختبار endpoint عمليًا

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/recommendations" -Headers @{"X-Company-ID"="Acme Corp"}
```

وعدد أقل:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/recommendations?limit=5" -Headers @{"X-Company-ID"="Acme Corp"}
```

> بهذا اكتمل توثيق: Forecasting + RFM + Recommendations، وربطها بالـ outputs والـ API والـ pipeline.


---

## ملحق 13: Sentiment Analysis (تحليل مشاعر العملاء) — (`src/06_sentiment.py` + `src/06_sentiment_arabic.py`) وربطه بـ `/api/sentiment`

هذا الملحق يشرح كيف النظام يحول “نصوص تقييمات العملاء” إلى:

- Positive / Neutral / Negative
- مؤشرات مثل Polarity/Subjectivity
- (اختياريًا) كلمات مفتاحية

ثم كيف يقرأ الـ backend النتائج من ملف:

- `data/sentiment_results.csv`

ويعرضها عبر:

- `/api/sentiment-analysis`
- `/api/sentiment` (Alias)

---

### Part 1 — الملف الأساسي المستخدم في الـ Pipeline: `src/06_sentiment.py`

#### 0) لماذا Sentiment مهم؟ (Business)

تحليل المشاعر يجاوب أسئلة بسيطة لكنها قوية:

- هل العملاء راضين؟
- هل توجد موجة شكاوى؟
- هل حصلت مشكلة بعد تحديث/منتج جديد؟

وفي نظامنا تحديدًا:

- هو أحد مصادر intelligence التي تُغذي “الرؤية العامة” في اللوحة.

---

#### 1) Paths & Logging

الملف يعمل مثل بقية المراحل:

```python
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
LOGS_DIR = BASE_DIR / "logs"
```

ويكتب log هنا:

- `logs/sentiment_analysis.log`

ويحفظ الرسم هنا:

- `output/plots/sentiment_analysis.png`

وأهم ملف output للـ API:

- `data/sentiment_results.csv`

---

#### 2) Schema Resolver Integration (لماذا؟)

بسبب اختلاف أسماء الأعمدة في ملفات reviews.

`resolve_sentiment_columns(df)` يحاول إيجاد:

- عمود النص `REVIEW_TEXT`
- عمود التقييم `RATING` (اختياري)

إذا resolver غير متوفر → يستخدم fallback lists:

- `ReviewText`, `comment`, `feedback`, ...

ثم الدوال:

- `find_text_column(df)`
- `find_rating_column(df)`

ترجع اسم العمود المناسب.

**الدرس:** تحليل المشاعر يعتمد على وجود “نص”؛ بدون نص لا معنى له.

---

#### 3) Detect Language (Arabic vs English) بشكل مبسط

الملف يملك منطق اكتشاف العربية عبر Unicode ranges.

الفكرة:

- إذا أكثر من ~30% من الأحرف عربية → اعتبر النص عربي.

هذا حل عملي “baseline” وليس NLP متقدم.

---

#### 4) `analyze_sentiment(text)` — قرار التحليل حسب اللغة

إذا النص عربي → يستخدم `analyze_arabic_sentiment()`:

- Keyword-based lexicon بسيط (كلمات إيجابية وسلبية)
- يحسب polarity تقريبًا:

$$polarity = \frac{pos - neg}{pos + neg}$$

ثم يصنف:

- Positive إذا polarity > 0.1
- Negative إذا polarity < -0.1
- Neutral غير ذلك

إذا النص غير عربي → يستخدم TextBlob:

- polarity وsubjectivity من TextBlob
- ثم نفس thresholds (0.1 و -0.1)

ويحاول استخراج keywords (أسماء nouns) كقائمة قصيرة.

**ملاحظة تعليمية مهمة:**

- TextBlob ممتاز كبداية للإنجليزي.
- العربية هنا ليست “تحليل لغوي حقيقي”، بل baseline بسيط.

---

#### 5) `process_reviews(df, text_col)` — تطبيق التحليل على كل صف

يمر على كل review ويضيف أعمدة:

- `Polarity`
- `Subjectivity`
- `Sentiment`
- `Keywords`

لاحظ: الملف لا يضمن وجود عمود واحد باسم معين للنص داخل output؛ بل يترك الأعمدة الأصلية كما هي ويضيف أعمدة جديدة.

---

#### 6) `generate_visualizations()` — الرسم المستخدم في dashboard

ينتج رسمًا مركبًا (subplots):

1) Pie Chart لتوزيع Positive/Neutral/Negative
2) Histogram لتوزيع Polarity

ويحفظه في:

- `output/plots/sentiment_analysis.png`

---

#### 7) `main()` — نقطة التشغيل

الـ input الأساسي الذي يتوقعه هذا الملف (داخل pipeline) هو:

- `data/customer_reviews.csv`

ثم:

1) يقرأ الملف
2) يجد عمود النص
3) يحلل كل صف
4) يولد summary في logs
5) يحفظ النتائج:

- `data/sentiment_results.csv`

هذا هو “العقد” بين ML scripts والـ API.

---

### Part 2 — الربط مع الـ Backend (Pipeline + API)

#### 1) كيف يتم توليد `data/sentiment_results.csv` تلقائيًا عند رفع reviews؟

داخل `backend/main.py` يوجد trigger:

- إذا dataset_type == "reviews" وعملية upload/replace → يشغل `run_sentiment_pipeline(uploaded_file)`.

و`run_sentiment_pipeline()` يعمل عمليًا:

1) يحذف أي نتائج قديمة (reset in-memory + حذف `sentiment_results.csv` إن وجد).
2) ينسخ الملف المرفوع إلى مكان قياسي:
   - `data/customer_reviews.csv`
3) يشغّل سكربت:
   - `src/06_sentiment.py`
4) بعد النجاح: يعيد تحميل `sentiment_results.csv` إلى الذاكرة (لكن الـ API لاحقًا لا يعتمد عليها دائمًا).

**فائدة هذا التصميم:**

- البيانات تُحفظ في مكان واحد معروف.
- كل مرة ترفع reviews → النتائج تتجدد.

---

#### 2) API: `/api/sentiment-analysis` و`/api/sentiment`

الـ backend يتعامل مع sentiment كـ “ملف على disk”:

- يقرأ `data/sentiment_results.csv` دائمًا (FRESH).

السلوك:

1) إذا الملف غير موجود → يرجع `204 No Content`.
2) إذا الملف فارغ → 204.
3) يبحث عن عمود التصنيف ضمن:
   - `SentimentLabel` أو `Sentiment` أو `Label`...
4) يحسب counts والنسب.
5) (اختياري) يحاول استخراج keywords من نصوص الإيجابي:
   - يفضّل `CleanedText` ثم `ReviewText`.

**نقطة مهمة جدًا:**

إذا ملف `sentiment_results.csv` لا يحتوي `ReviewText` ولا `CleanedText` (مثلاً كان عمود النص اسمه `comment`) فالـ API سيعطي breakdown صحيح، لكن `top_keywords` قد تخرج فارغة.

هذا ليس bug قاتل، لكنه فرق بين “analytics موجودة” و“keywords موجودة”.

---

#### 3) اختبار endpoint عمليًا

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/sentiment" -Headers @{"X-Company-ID"="Acme Corp"}
```

أو:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/sentiment-analysis" -Headers @{"X-Company-ID"="Acme Corp"}
```

---

### Part 3 — ملف ترقية العربية (اختياري): `src/06_sentiment_arabic.py`

هذا الملف ليس هو المسار الافتراضي للـ backend الحالي، لكنه “نسخة محسنة” للعربية.

#### 1) الفكرة

بدل keyword-based العربية، يستخدم Transformers + نموذج عربي جاهز.

يحاول الاستيراد:

- `transformers` و`torch`

إذا غير موجودة → يقع على TextBlob فقط.

#### 2) ArabicSentimentAnalyzer

ينشئ HuggingFace pipeline:

- `sentiment-analysis`

ويعيد:

- sentiment
- confidence
- polarity (موجب للإيجابي وسالب للسلبي)
- method (arabic_bert)

#### 3) UnifiedSentimentAnalyzer

يقرر:

- إذا النص عربي + الموديل جاهز → Arabic BERT
- غير ذلك → TextBlob

#### 4) Output لهذا الملف

هذا الملف يكتب نتيجة مختلفة عن المسار الافتراضي:

- `output/{company}_sentiment_analysis.csv`

ويقرأ input من:

- `data/{company}/reviews/*reviews*.csv`

**ملاحظة مهمة:** لكي تربطه بالـ API الحالي، ستحتاج توحيد مسارات الإدخال/الإخراج أو تعديل الـ backend ليقرأ هذا الملف.

---

> بهذا اكتمل توثيق Phase 6 (Sentiment) end‑to‑end: من reviews.csv → إلى sentiment_results.csv → إلى `/api/sentiment`.


---

## ملحق 14: Phase 1 — Data Collection & EDA — (`src/01_eda.py`) ودوره كمصدر الحقيقة لباقي المراحل

هذا الملحق يشرح أهم ملف في خط المبيعات:

- `src/01_eda.py`

لأنه يقوم بوظيفتين معًا:

1) **EDA (تحليل استكشافي)** + رسومات.
2) **توحيد وتجهيز البيانات** وإنتاج ملفات “قياسية” تعتمد عليها بقية المراحل.

وأهم output عمليًا (الذي يفتح الباب لبقية السكربتات):

- `data/merged_data.csv`
- `data/cleaned_dataset.csv`

---

### Part 1 — الفكرة العامة (لماذا Phase 1 أساس كل شيء؟)

تذكر قاعدة مهمة جدًا في أي مشروع ML:

- إذا البيانات غير موحدة/غير نظيفة → كل النتائج اللاحقة ستكون مضللة.

Phase 1 هنا يقوم بعمل “توحيد الأعمدة” (Normalization) قبل أي تحليل:

- يجعل الأعمدة الأساسية بأسماء معيارية:
  - `OrderDate`
  - `TotalPrice`
  - `CustomerID` (إن توفر)
  - `OrderID` (حتى لو سنّعه صناعيًا)
  - `Product` (إن توفر)
  - `Quantity` و`Price` (إن توفر)

وبالتالي:

- Forecasting يعتمد على `OrderDate + TotalPrice`.
- RFM يعتمد على `CustomerID + OrderDate + TotalPrice`.
- Recommendations تعتمد على `OrderID + Product` (وأحيانًا Quantity).

إذًا Phase 1 هو الذي يجعل تلك الأشياء ممكنة.

---

### Part 2 — شرح `src/01_eda.py` سطرًا بسطر (المنطق الفعلي)

#### 0) Paths & Logging

مثل بقية المشروع:

```python
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
LOGS_DIR = BASE_DIR / "logs"
```

ويكتب log هنا:

- `logs/eda.log`

ويحفظ الرسومات في:

- `output/plots/`

---

#### 1) Schema Resolver Integration (حل مشكلة اختلاف أسماء الأعمدة)

الملف يحاول استيراد:

- `SchemaResolver`
- `SemanticField`

إذا متوفر → يستخدمه كـ “مترجم معنى الأعمدة” بدل ما يفترض أسماء ثابتة.

**الدالة المحورية:** `resolve_columns(df, dataset_type)`

لو resolver متوفر:

1) ينفذ `resolver.resolve(df, dataset_type)`.
2) يطبع mapping في logs:
   - `ORDER_DATE -> '...'`
   - `TOTAL_PRICE -> '...'`
   - وهكذا.
3) يرجع قاموس مبسط للمفاتيح التالية:
   - order_date
   - customer_id
   - order_id
   - product
   - quantity
   - unit_price
   - total_price
   - city

لو resolver غير متوفر → يشتغل fallback `_fallback_resolve_columns()`.

---

#### 2) `normalize_sales_df()` — أهم دالة في Phase 1

هذه الدالة تحول ملف sales “كما هو” إلى شكل قياسي.

##### 2.1) OrderDate (إجباري)

- يحاول تحديد عمود التاريخ.
- إذا غير موجود → يرفع ValueError ويوقف Phase 1.

هذا منطقي لأن:

- بدون تاريخ لا يوجد تحليل مبيعات زمني.

##### 2.2) CustomerID (اختياري)

- إذا موجود → يطبّعه إلى `CustomerID`.
- إذا غير موجود → warning:
  - “RFM analysis will be unavailable”.

##### 2.3) OrderID (اختياري)

- إذا موجود → يستخدمه.
- إذا غير موجود → يولّد `OrderID` صناعيًا:

```python
sales["OrderID"] = range(1, len(sales) + 1)
```

هذه خطوة ذكية لأنها تمنع فشل مراحل تعتمد على OrderID.

##### 2.4) Product (اختياري)

- إذا موجود → يطبّعه إلى `Product`.
- إذا غير موجود → warning:
  - “Recommendations will be unavailable”.

##### 2.5) Quantity/Price (اختياري)

- إذا quantity موجود → يحوله رقم.
- لو غير موجود → يجعل Quantity = 1.

##### 2.6) TotalPrice (إجباري أو مشتق)

الحالات:

1) لو يوجد عمود value (TotalPrice/Revenue/...) → يحوله رقم.
2) لو لا، لكن يوجد Price وQuantity → يحسب:
   - `TotalPrice = Price * Quantity`
3) إذا لا يوجد أي شيء → ValueError.

وهذا مهم لأنه “العمود الوحيد الذي كل التحليلات تحتاجه”.

---

#### 3) `normalize_customers_df()` — إثراء اختياري

إذا customers.csv موجود:

- يحاول تطبيع City إلى `City` (ويملأ Unknown).
- يحاول تطبيع CustomerID.

ثم لاحقًا يتم merge مع sales لإضافة خصائص العميل.

---

#### 4) `load_data()` — ما الذي يعتبر Mandatory وما الذي يعتبر Optional؟

داخل Phase 1:

- `data/sales.csv` **إجباري**.
- `data/customers.csv` اختياري.
- `data/customer_reviews.csv` أو `data/reviews.csv` اختياري (ويقرأه فقط كمعلومة/استعداد، لكنه لا يدخل بعمق في merge هنا).

هذه الفلسفة تجعل pipeline مرن:

- يمكنك تشغيل المبيعات وحدها.
- ثم لاحقًا تضيف customers لتحسين RFM.

---

#### 5) `clean_data(customers, sales)` — تنظيف بسيط لكنه مهم

الخطوات:

1) إزالة duplicates في customers بناء على CustomerID (لو موجود).
2) حذف صفوف sales التي OrderDate فيها NaN.
3) حذف TotalPrice السالب.

ثم يطبع عدد السجلات المحذوفة.

**ملحوظة:** هذا تنظيف baseline فقط. ليس تنظيفًا إحصائيًا متقدمًا، لكنه كافٍ للمشروع.

---

#### 6) `merge_data(sales, customers)` — enrichment (إن توفر)

إذا customers موجود وCustomerID موجود في الملفين:

- يعمل merge left على CustomerID.

إذا لا → يتجاوز merge ويستخدم sales كما هو.

---

#### 7) `compute_kpis(df)` — KPIs أولية

يحسب مؤشرات مثل:

- Total Sales Revenue
- Total Orders
- Total Customers (إن توفر CustomerID)
- Average/Median Order Value
- Total Products Sold (إن توفر Product)

هذه KPIs تُطبع في logs وتُستخدم كملخص سريع.

---

#### 8) `perform_eda(df)` — استخراج جداول EDA

يضيف عمود Month:

- `df["Month"] = df["OrderDate"].dt.to_period("M")...`

ثم يحسب:

1) monthly_sales = sum(TotalPrice) per month
2) top_products = أعلى 5 منتجات حسب revenue
3) sales_by_city (لو يوجد City)

---

#### 9) `plot_results()` — الصور التي يراها المستخدم

ينتج 3 رسومات:

- `output/plots/monthly_sales.png`
- `output/plots/top_products.png`
- `output/plots/sales_by_city.png` (لو city موجود)

---

#### 10) أهم نقطة: Outputs التي “تفتح الطريق” لباقي المراحل

داخل `main()` بعد merge:

```python
df.to_csv(DATA_DIR / "merged_data.csv", index=False)
df.to_csv(DATA_DIR / "cleaned_dataset.csv", index=False)
```

وهذا قرار تصميم مهم جدًا مذكور داخل backend أيضًا:

- backend يعتبر أن Phase 1 الآن يغطي ما كان يسمى Phase 2، لأنه ينتج `cleaned_dataset.csv` مباشرة.

بالتالي:

- `src/04_rfm.py` و`src/05_recommendation.py` و`src/03_forecasting.py` غالبًا يقرؤون `data/cleaned_dataset.csv` أولًا.

---

### Part 3 — الربط مع Pipeline في backend

داخل `backend/main.py` في `run_full_sales_pipeline()`:

1) ينسخ الملف المرفوع إلى:
   - `data/sales.csv`
2) يشغّل:
   - `src/01_eda.py`
3) يتأكد أن `data/cleaned_dataset.csv` تم إنشاؤه.
4) ينتقل إلى:
   - `src/04_rfm.py`
   - `src/05_recommendation.py`

**النتيجة:**

رفع sales واحد → يولد تلقائيًا:

- `data/merged_data.csv`
- `data/cleaned_dataset.csv`
- `data/rfm_table.csv` (إن توفر CustomerID)
- `data/product_recommendations.csv` (إن توفر Product / multi-baskets)

---

### Part 4 — ملاحظة مهمة عن “النتائج” و“الحذف” (Stale Data)

في backend توجد آلية Cascade Delete تحذف مشتقات التحليل عند حذف dataset.

حتى لو رأيت في الكود أسماء مثل `eda_report.json` أو `kpis.csv`... فهذا يعكس “مخرجات مشتقة” محتملة يتم تنظيفها عند reset.

أهم شيء كطالب:

- النظام يحاول دائمًا منع ظهور بيانات قديمة بعد حذف/استبدال البيانات.

---

> بهذا اكتمل توثيق Phase 1 (EDA): من `data/sales.csv` → إلى normalization/merge → إلى `merged_data.csv` و`cleaned_dataset.csv` + plots، وهو الأساس الذي يعتمد عليه باقي المشروع.


---

## ملحق 15: ML Lifecycle (تدريب/تقييم/تنبؤ/إعادة تدريب + Monitoring) — (`src/ml_lifecycle/*`) وربطه بالـ Backend عبر `MODEL_PATH`

في هذا المشروع لدينا **مسارين للتنبؤ**:

1) مسار “سكربتات التحليل” مثل `src/03_forecasting.py` و`src/03_forecasting_prophet.py`.
2) مسار “دورة حياة نموذج” داخل `src/ml_lifecycle/`.

الفرق الجوهري:

- سكربت Phase 3 ينتج **CSV forecast** مباشرة.
- ML Lifecycle يبني **ملف نموذج محفوظ** (Model Artifact) داخل registry ثم يستخدمه للتنبؤ لاحقًا.

المشروع يستخدم الاثنين:

- الـ backend يقرأ forecast CSV من أكثر من مصدر.
- والـ backend يستطيع تحميل نموذج محفوظ عبر:
  - `MODEL_PATH = src/ml_lifecycle/model_registry/sales_forecast_model.pkl`

---

### Part 1 — ما هو “Model Registry” داخل هذا المشروع؟

داخل `src/ml_lifecycle/` يوجد مجلد:

- `src/ml_lifecycle/model_registry/`

فكرته بسيطة جدًا:

- مكان ثابت لحفظ النماذج والإصدارات والـ metadata.

في النسخة الأساسية (Linear Regression lifecycle):

- الملف الثابت للنموذج الحالي:
  - `sales_forecast_model.pkl`

في نسخة Prophet مع versioning:

- ملفات متعددة:
  - `sales_forecast_baseline_v{version}.pkl`
  - `sales_forecast_prophet_v{version}.pkl`
  - `model_metadata.json`
  - ثم يتم تحديث `sales_forecast_model.pkl` ليصبح “النموذج الحالي” المختار.

**الدرس المهم:**

الـ registry هنا يعمل كأنه:

- "current production model" + "history of versions".

---

### Part 2 — الربط مع backend: لماذا `MODEL_PATH` موجود؟

في `backend/main.py` يوجد:

- `MODEL_PATH = .../sales_forecast_model.pkl`

وعند startup (داخل `reload_all_data_from_disk`) يحاول:

- `joblib.load(MODEL_PATH)`

إذا نجح:

- `status["model"] = True`

إذا فشل أو الملف غير موجود:

- `model = None`

**مهم كطالب:** وجود هذا التحميل يعني:

- الـ backend “جاهز” للتنبؤ بنموذج محفوظ (حتى لو لم تُستخدم هذه القدرة في كل endpoints).

ومهم أيضًا أن backend عند حذف dataset يعمل Cascade Delete ويقوم بمسح:

- `src/ml_lifecycle/model_registry/*`

حتى لا يبقى model قديم يعمل على بيانات جديدة.

---

### Part 3 — `train_forecast.py` (تدريب baseline وحفظه)

هذا السكربت هو أبسط lifecycle مكتمل (Train → Evaluate → Persist).

#### 1) Inputs (ما الذي يتطلبه التدريب؟)

يقرأ:

- `data/cleaned_dataset.csv`

ويشترط وجود عمودين بالاسم القياسي:

- `OrderDate`
- `TotalPrice`

وهنا يظهر دور Phase 1:

- `01_eda.py` يضمن أن `cleaned_dataset.csv` يحمل هذه الأعمدة القياسية.

#### 2) `load_monthly_sales()`

يحوله إلى monthly series بنفس منطق بقية المشروع:

- group by month-start (MS)
- sum TotalPrice
- يضيف feature:
  - `MonthIndex = 0..n-1`

ويشترط على الأقل 3 أشهر.

#### 3) `split_time_series()` (Temporal Split بدون شفل)

هذه نقطة تعليمية قوية:

- time series لا نعمل لها shuffle.

يحسب test size 20% افتراضيًا، ويضمن:

- train فيه على الأقل شهرين.

#### 4) `train_model()`

Linear Regression بسيط:

$$y = a \cdot MonthIndex + b$$

مفيد لأنه:

- baseline واضح وسهل التفسير.

#### 5) `evaluate_model()`

يقيس:

- MAE
- RMSE
- R2 (مع guard إذا عدد العينات قليل)

ويطبع train/test metrics.

#### 6) `save_model()` (الربط مع model_registry)

يحفظ هنا:

- `src/ml_lifecycle/model_registry/sales_forecast_model.pkl`

باستخدام `joblib`.

**النتيجة:** بعد تشغيل هذا السكربت، الـ backend عند startup سيستطيع تحميل model.

---

### Part 4 — `evaluate_forecast.py` (تقييم النموذج المحفوظ)

هذا السكربت يكرر نفس data-prep وsplit، ثم:

1) يحمّل النموذج من:
   - `model_registry/sales_forecast_model.pkl`
2) يقيمه على train/test.

ميزة تربوية:

- يفصل “evaluation” عن “training” لكي يصبح لدينا مراحل واضحة.

إذا لم تجد model:

- يعرض رسالة واضحة: شغّل `train_forecast.py` أولًا.

---

### Part 5 — `predict_forecast.py` (توليد forecast CSV من model)

هذا السكربت هو الجسر الأهم بين “model artifact” و“forecast CSV”.

#### 1) لماذا هذا السكربت مهم في النظام كله؟

لأنه يكتب output file بالاسم الذي يبحث عنه الـ backend ضمن `load_forecast_data()`:

- `data/sales_forecast_future.csv`

والـ backend يعتبره مصدر forecast محتمل (قبل/بعد غيره حسب ترتيب البحث).

#### 2) حمايات مهمة داخل السكربت

- horizon الافتراضي = 6 أشهر.
- يوجد حد أقصى:
  - `MAX_PERIODS = 60`

حتى لا يطلب أحد 5000 شهر ويفشل النظام أو يستهلك ذاكرة بلا معنى.

#### 3) `build_future_features()`

يبني:

- future MonthIndex values
- future calendar months (`MonthStart`) بعد آخر شهر موجود

ثم model.predict → يكتب:

- `MonthStart`
- `ForecastedSales`

في:

- `data/sales_forecast_future.csv`

#### 4) الربط مع `/api/monthly-sales`

بعد تشغيل `predict_forecast.py`:

- endpoint `/api/monthly-sales` سيقرأ `sales_forecast_future.csv` (لأنه ضمن قائمة `load_forecast_data()`)
- ثم يدمجه مع actuals ويعرض للواجهة.

**هذه نقطة مهمة جدًا:**

هذا يعني أن مشروعك يستطيع أن ينتج forecast بطريقتين:

- (A) من Phase 3 script مباشرة (sales_forecast.csv)
- (B) من model registry lifecycle (sales_forecast_future.csv)

---

### Part 6 — `retrain_forecast.py` (إعادة تدريب مع “محاكاة بيانات جديدة”)

هذا الملف يشرح فكرة retraining بشكل تعليمي.

ماذا يفعل؟

1) يدرّب baseline model على البيانات الحالية.
2) يستخدمه لمحاكاة 3 أشهر مستقبلية (Forecast) ثم يضيف noise بسيط (5%) حتى لا تكون البيانات مثالية.
3) يدمج هذه الأشهر مع التاريخ → ينتج dataset أطول.
4) يعيد حساب MonthIndex.
5) يعمل temporal split.
6) يدرب نموذج جديد.
7) **يكتب فوق نفس الملف**:
   - `sales_forecast_model.pkl`

إذًا retraining هنا “update inplace”.

**الدرس المهم:**

- في الواقع البيانات الجديدة تأتي من السوق.
- هنا نحاكيها فقط حتى نفهم دورة retraining.

---

### Part 7 — `train_forecast_prophet.py` (نسخة production أقوى مع versioning + model selection)

هذا الملف مختلف عن baseline lifecycle لأنه:

1) يدرب **نموذجين**:
   - LinearRegression baseline
   - Prophet (إذا متوفر)
2) يقارنهم بمقياس واضح:
   - MAPE
3) يختار الأفضل.
4) يسجل versioning داخل:
   - `model_metadata.json`
5) يحدث “current model”:
   - يكتب أفضل نموذج إلى `sales_forecast_model.pkl`

#### 1) مصدر البيانات هنا (Multi‑tenant)

هذا السكربت يقرأ من:

- `data/{company}/sales/cleaned_sales.csv`

لاحظ أنه مختلف عن baseline lifecycle الذي يقرأ `data/cleaned_dataset.csv`.

هذه نقطة مهمة:

- هذا السكربت مبني على “بيانات شركة محددة” داخل مجلد الشركة.

#### 2) metadata

يحفظ تاريخ التدريب، أحجام train/test، metrics لكل نموذج، ثم:

- `selected_model` = baseline أو prophet

وهذا يسهّل monitoring والإدارة.

---

### Part 8 — `monitor_model.py` (Monitoring + Drift Detection + Retrain Decision) — متقدم

هذا الملف يشرح فكرة MLOps مبسطة:

- ليس كافيًا أن ندرب model مرة واحدة.
- يجب مراقبة الأداء + الانحراف (drift).

#### 1) ماذا يحتاج هذا السكربت؟

هو متصل بقاعدة البيانات عبر:

- `backend.database.connection.SessionLocal`
- `backend.database.models.ModelPerformanceLog`

ويعتمد أيضًا على:

- `scipy.stats` (اختبار KS)

إذًا هو سكربت “تشغيلي” أكثر من كونه جزءًا من pipeline الأساسي.

#### 2) Performance Logs

`log_model_performance(...)` يسجل metrics مثل:

- MAE / RMSE / MAPE

ثم يقارنها بآخر سجلات ليكتشف:

- performance degradation

#### 3) Drift Detection

`detect_data_drift(company_name)` يقسم البيانات إلى:

- reference window (مثلاً 90 يوم)
- current window (مثلاً 30 يوم)

ثم يستخدم KS test ليقيس هل التوزيع تغير.

إذا p-value < 0.05 → drift detected.

#### 4) قرار retrain

`should_retrain_model()` يقرر retraining بناء على:

- degradation
- drift
- الزمن منذ آخر تدريب
- force flag

**ملاحظة:** هذا السكربت ليس endpoint في backend حاليًا، لكنه جاهز ليكون جزءًا من scheduled job أو admin tool.

---

### Part 9 — كيف تشغل lifecycle عمليًا (مسارات وأوامر)

هذه أوامر تشغيل عامة (من داخل مشروع Sales_Intelligence_Project):

1) تدريب baseline وحفظ model:

```powershell
& "$env:VIRTUAL_ENV\Scripts\python.exe" src/ml_lifecycle/train_forecast.py
```

2) تقييم model المحفوظ:

```powershell
& "$env:VIRTUAL_ENV\Scripts\python.exe" src/ml_lifecycle/evaluate_forecast.py
```

3) إنتاج forecast CSV مستقبلي من model (مثلاً 6 أشهر):

```powershell
& "$env:VIRTUAL_ENV\Scripts\python.exe" src/ml_lifecycle/predict_forecast.py 6
```

بعدها `/api/monthly-sales` يستطيع دمج actual + forecast.

---

> بهذا اكتمل توثيق `src/ml_lifecycle/`: من فكرة registry → تدريب baseline → تقييم → تنبؤ مستقبل → retraining → training prophet versioned → monitoring/drift، وربط ذلك بالـ backend عبر `MODEL_PATH` وملفات forecast التي يقرأها `/api/monthly-sales`.


---

## ملحق 16: Backend v2 (Authentication + SQLAlchemy DB + Background Tasks + Standard Responses) — (`backend/main_enhanced.py` وما حوله)

هذا الملحق يشرح “النسخة الثانية” من الـ backend الموجودة في المشروع.

> مهم: مشروعك يحتوي على Backend أساسي في `backend/main.py` (الذي استعملته الواجهة في التجارب)، ويوجد Backend “محسّن” في `backend/main_enhanced.py` يضيف Authentication + DB + Background Tasks + Monitoring.

هدف هذا الملحق كطالب:

- تفهم كيف صُمّم نظام “مؤسسي” أكثر (Users/Companies/Roles + تخزين نتائج ML في DB).
- تفهم كيف يتم تشغيل عمليات ML الثقيلة في الخلفية بدون ما تعطل الـ API.
- تفهم كيف يمكن أن تنتقل من “قراءة CSV مباشرة” إلى “Caching داخل DB”.

---

### Part 1 — خريطة الملفات (ما الذي يشكل Backend v2؟)

الملفات الأساسية في v2:

1) `backend/main_enhanced.py`
    - تطبيق FastAPI v2.0
    - حماية endpoints بالـ JWT
    - تشغيل Forecast/Sentiment كـ Background Tasks
    - Explainability + Monitoring endpoints

2) `backend/database/connection.py`
    - إعداد SQLite engine + SessionLocal
    - `get_db()` Dependency لـ FastAPI
    - `init_db()` لإنشاء الجداول
    - `reset_db()` (للتطوير فقط)

3) `backend/database/models.py`
    - SQLAlchemy models: `User`, `Company`, ونتائج ML مثل `ForecastResult`, `SentimentResult`, `RFMResult`
    - `UserRole` (RBAC)

4) `backend/auth.py`
    - إنشاء/فك JWT
    - Hashing والتحقق من كلمة المرور
    - Dependencies مثل: `get_current_user` و`require_role`
    - عزل الشركات عبر `check_company_access`

5) `backend/routes/auth_routes.py`
    - endpoints تسجيل/تسجيل دخول/من أنا/تحقق من التوكن

6) `backend/background_tasks.py`
    - تنفيذ Forecast/Sentiment في الخلفية
    - سجل مهام in-memory بسيط (TASK_REGISTRY)
    - حفظ نتائج forecast/sentiment في DB

7) `backend/responses.py`
    - نماذج Pydantic لتوحيد شكل الردود (APIResponse / ErrorResponse / PaginatedResponse)

8) `backend/init_db.py`
    - إنشاء seed data (شركات ومستخدمين) للتجربة

---

### Part 2 — قاعدة البيانات في v2 (SQLAlchemy + SQLite)

#### 1) أين ملف قاعدة البيانات؟

داخل `backend/database/connection.py` يتم تحديد:

- `BASE_DIR = Sales_Intelligence_Project/`
- `DB_DIR = BASE_DIR / "data"`
- افتراضيًا SQLite:
   - `data/sales_intelligence.db`

إذًا قاعدة البيانات جزء من “طبقة التخزين” في المشروع.

#### 2) لماذا SessionLocal مهم؟

في FastAPI، كل request يحتاج session مستقلة:

- `SessionLocal()` → تفتح اتصال.
- `yield db` → يمررها للـ endpoint.
- `finally: db.close()` → يغلقها بشكل آمن.

هذا يجعل الـ endpoints:

- تعمل بشكل متكرر بدون memory leaks.
- معزولة بين requests.

#### 3) init_db vs migrations

`init_db()` يستعمل:

- `Base.metadata.create_all(bind=engine)`

وهذا مناسب للتجارب.
أما production غالبًا تستخدم Alembic migrations (مذكور في التعليقات).

---

### Part 3 — Models: كيف تم تمثيل النظام في DB؟

#### 1) UserRole (RBAC)

`UserRole` يحدد أدوار:

- `admin`: صلاحيات كاملة
- `analyst`: تشغيل التحليلات + مشاهدة النتائج
- `viewer`: قراءة فقط

#### 2) User و Company

الفكرة التعليمية هنا:

- كل User مرتبط بشركة واحدة (`company_id`).
- كل Company لها:
   - `data_directory` → هذا يربط DB بالعالم الفعلي للملفات داخل `data/{Company}/...`

بالتالي عند تنفيذ analysis:

- الـ API يعرف أي شركة تتعامل معها.
- يمكن عزل البيانات Multi‑tenant.

#### 3) ForecastResult / SentimentResult / RFMResult

هنا تظهر فلسفة caching:

- بدلاً من إعادة تشغيل ML كل مرة، نخزن الناتج:
   - forecast → JSON داخل `forecast_data`
   - sentiment → صفوف results لكل review
   - rfm → صفوف segments لكل customer

هذا يجعل dashboard:

- أسرع
- أقل اعتمادًا على ملفات CSV عند كل request

---

### Part 4 — Authentication في v2: JWT + Dependencies

#### 1) JWT payload

عند `create_access_token` يتم وضع payload عادة مثل:

- `sub`: email
- `role`: دور المستخدم
- `company_id`: شركة المستخدم
- `exp`: انتهاء الصلاحية

الهدف:

- أي endpoint محمي يستطيع معرفة من المستخدم وما هي صلاحياته بدون سؤال DB في كل خطوة (لكن لا يزال يراجع وجود user).

#### 2) get_current_user

هذا Dependency هو حجر الأساس:

1) يأخذ التوكن من `Authorization: Bearer ...`
2) يفك JWT
3) يقرأ email من `sub`
4) يحمّل User من DB
5) يرفض المستخدم غير النشط

#### 3) require_role + require_admin / require_analyst / require_viewer

`require_role([...])` يرجع dependency جديد.

مثال عملي:

- `require_admin` يسمح فقط لـ admin
- `require_analyst` يسمح لـ admin + analyst

هذه هي الطريقة الصحيحة لبناء RBAC في FastAPI.

#### 4) check_company_access

هذه نقطة Multi‑tenant:

- analyst/viewer لا يرى إلا شركته.
- admin يمكنه الوصول لكل الشركات.

---

### Part 5 — Auth Routes: `/api/auth/*`

هذا الجزء موجود في `backend/routes/auth_routes.py`.

#### 1) POST `/api/auth/register`

يدخل:

- email + password + full_name + company_id + role

ويطبق قواعد:

- password على الأقل 8 أحرف
- email غير مكرر
- company_id يجب أن يكون موجودًا

ويعيد User بدون كلمة مرور.

#### 2) POST `/api/auth/login`

يدخل:

- email + password

ثم:

- `authenticate_user` يتحقق من الحساب وكلمة المرور
- إذا نجح يرجع JWT + user profile

#### 3) POST `/api/auth/login/form`

هذا endpoint موجود فقط للتوافق مع Swagger UI (OAuth2PasswordRequestForm).

#### 4) GET `/api/auth/me`

يعيد بيانات المستخدم الحالي بناء على التوكن.

#### 5) GET `/api/auth/verify`

يرجع JSON بسيط يثبت أن التوكن صالح.

---

### Part 6 — Standard Responses: لماذا `backend/responses.py` مهم؟

في v1 قد ترى endpoints ترجع dict مباشرة.
في v2 يوجد فكرة “قالب رد موحد”:

- `APIResponse[T]`:
   - `success`
   - `data`
   - `message`
   - `errors`
   - `metadata`
   - `timestamp`

وهذا مفيد لأن الواجهة:

- لا تحتاج تخمين شكل الاستجابة لكل endpoint.
- أخطاء النظام ترجع بشكل متوقع.

الملف أيضًا يوفر builders:

- `success_response(data, message, metadata)`
- `error_response(error, detail, error_code)`
- `paginated_response(...)`

---

### Part 7 — Background Tasks: تشغيل ML بدون ما نحبس الـ API

`backend/background_tasks.py` مصمم لتشغيل عمليتين ثقيلتين:

1) Forecasting
2) Sentiment Analysis

#### 1) Task Registry

يوجد:

- `TASK_REGISTRY: Dict[str, Dict]`

وهو in-memory.
هذا يعني:

- مناسب للتجربة.
- عند restart للسيرفر… ستضيع حالة المهام.

في production عادة تستخدم Redis/Celery.

#### 2) TaskStatus

حالات المهمة:

- pending
- running
- completed
- failed

#### 3) run_forecast_async

التدفق:

1) يكتب المهمة running + progress
2) ينفذ forecasting (قد يكون baseline أو prophet حسب `use_prophet`)
3) يكتب النتائج داخل DB (ForecastResult)
4) يضع status completed مع result مختصر

تعليميًا:

- forecast_data يخزن JSON rows
- metrics (MAE/RMSE/MAPE/R2) تساعد في monitoring لاحقًا

#### 4) run_sentiment_async

التدفق:

1) ينفذ `analyze_reviews`
2) يحذف نتائج sentiment القديمة للشركة
3) يكتب نتائج جديدة على دفعات (batch insert)
4) يرجع distribution (Positive/Neutral/Negative)

#### 5) cleanup_old_tasks

هذا مجرد housekeeping:

- يحذف المهام المكتملة/الفاشلة بعد مدة (افتراضي 24 ساعة)

---

### Part 8 — main_enhanced: endpoints الأساسية (كيف يشتغل النظام؟)

#### 1) Startup

عند startup:

- `init_sqlalchemy_db()` ينشئ الجداول

#### 2) Companies

- GET `/api/companies`
   - analyst/viewer: يرجع شركته فقط
   - admin: يرجع كل الشركات

#### 3) Forecast (Background)

- POST `/api/companies/{company_id}/forecast`
   - ينشئ `task_id`
   - يضيف `run_forecast_async` إلى `BackgroundTasks`
   - يرجع task_id فورًا

- GET `/api/tasks/{task_id}`
   - تتابع progress/status

- GET `/api/companies/{company_id}/forecast/latest`
   - يقرأ آخر ForecastResult من DB
   - يحاول توليد explainability عبر `explain_forecast` (إذا نجح)

#### 4) Sentiment (Background)

- POST `/api/companies/{company_id}/sentiment`
   - يطلق task

- GET `/api/companies/{company_id}/sentiment/summary`
   - يقرأ نتائج DB ويحسب summary

#### 5) Explainability

- POST `/api/explain/rfm`
   - يشرح سبب segment لعميل بناء على قيم RFM

- POST `/api/explain/recommendation`
   - يشرح توصية (حاليًا يستخدم أرقام placeholder)

#### 6) Monitoring (Admin Only)

- GET `/api/admin/model-health/{company_id}`
- POST `/api/admin/check-drift/{company_id}`
- POST `/api/admin/retrain/{company_id}`

هذه تربط backend v2 مباشرة مع وحدات MLOps داخل `src/ml_lifecycle/`.

---

### Part 9 — `init_db.py`: seed data لتجربة الـ Auth بسرعة

هذا السكربت يبني بيانات جاهزة:

- شركات demo (مثل Acme Corp)
- مستخدمين بأدوار مختلفة

ويطبع credentials واضحة للتجربة.

**ملاحظة مهمة:** إذا كان DB موجود، السكربت يسأل هل تريد reset.

---

> بهذا اكتمل توثيق Backend v2: طبقة DB + Users/Companies/Roles + JWT + Routes + Background Tasks + Explainability/Monitoring.


---

## ملحق 17: Frontend (React + TypeScript + Vite + Tailwind) — (`Sales_Intelligence_Project/frontend/*`) وربطه بالـ API

هذا الملحق يشرح واجهة المشروع الموجودة داخل:

- `Sales_Intelligence_Project/frontend/`

> ملاحظة: يوجد مجلد آخر اسمه `dashboard/` في أعلى الـ workspace. لكنه عمليًا نسخة/واجهة ثانية. الواجهة “الأساسية” المتصلة بهذا المشروع هي الموجودة داخل `Sales_Intelligence_Project/frontend/`.

هدف الملحق:

- تفهم كيف تُبنى صفحات الـ Dashboard.
- تفهم طبقة Authentication من جهة الواجهة.
- تفهم طبقة “جلب البيانات” (Data Context) وكيف ترتبط بـ endpoints في الـ backend.
- تفهم لماذا ظهر خطأ JSON/HTML سابقًا، وكيف حله proxy.

---

### Part 1 — الصورة الكبيرة: كيف تشتغل الواجهة؟

الواجهة مبنية بـ:

- React + TypeScript
- Vite (dev server)
- TailwindCSS (styles)
- Recharts (charts)

فكرة العمل كطالب:

1) المستخدم يسجل الدخول (JWT).
2) بعد النجاح، التطبيق يفتح Layout فيه Sidebar + Header.
3) DataContext يجلب البيانات من الـ backend عبر endpoints متعددة.
4) كل صفحة تعرض جزءًا من هذه البيانات (Forecasting / Segmentation / Recommendations / Sentiment / Sales).

---

### Part 2 — Vite Proxy: لماذا كان يظهر “Unexpected token '<'”؟

عندما الواجهة تعمل على Vite (مثلاً `http://localhost:3000`) وتطلب:

- `fetch('/api/alerts')`

بدون proxy، فإن الطلب يذهب إلى نفس سيرفر Vite وليس إلى FastAPI.
وسيرفر Vite غالبًا يرد HTML (صفحة index) → فيظهر الخطأ:

- JSON.parse يتوقع JSON لكنه يستقبل HTML يبدأ بـ `<`.

حل ذلك موجود في:

- `frontend/vite.config.ts`

حيث يوجد:

- proxy لمسار `/api` → `http://localhost:8000`

وبالتالي أي request يبدأ بـ `/api/...` سيذهب إلى FastAPI.

**الدرس المهم:**

- في التطوير: إمّا تستخدم proxy وتكتب `/api/...`.
- أو تستخدم base URL صريح مثل `http://localhost:8000/api/...`.

وفي مشروعك… ستجد الطريقتين مستخدمتين.

---

### Part 3 — نقطة الدخول: App + Layout + التنقل بين الصفحات

في `frontend/App.tsx` يوجد:

- `AuthProvider` (يوفر حالة login)
- `DataProvider` (يوفر البيانات التحليلية)

ثم `AppContent`:

- إذا لم يكن المستخدم authenticated → يعرض صفحة `Auth.tsx`.
- إذا authenticated → يعرض `Layout.tsx` ويغيّر `currentPage` بين:
  - Dashboard
  - Sales Analytics
  - Forecasting
  - Segmentation
  - Recommendations
  - Sentiment
  - DataUpload
  - Settings

الـ Layout نفسه:

- Sidebar buttons تغير `currentPage`.
- Header يظهر المستخدم والشركة + theme toggle.

**الدرس المهم:** هذا تطبيق “single-page navigation” داخلي (ليس React Router). بسيط للتعلم.

---

### Part 4 — Authentication في الواجهة (`store/AuthContext.tsx`)

هذا الملف هو “العقل” الخاص بتسجيل الدخول على الواجهة.

#### 1) أين يحتفظ الواجهة بالجلسة؟

في `localStorage`:

- `auth_token` ← JWT token
- `auth_user` ← user profile (company/role/email…)
- `company` ← اسم الشركة (لتوحيد سلوك بعض المكونات)

عند فتح الصفحة لاحقًا:

- `loadSavedAuth()` يقرأ token + user من localStorage
- ثم يطلب:
  - `GET /api/auth/verify`
- إذا OK → يثبت الجلسة
- إذا لا → يمسح localStorage

#### 2) login

`login(email, password)` يرسل:

- POST `/api/auth/login`

ثم يحول الـ payload إلى نوع `User` في `types.ts`.

#### 3) register

`register(...)` يرسل:

- POST `/api/auth/register`

ثم مباشرة يعمل login.

#### 4) useAuthFetch

هذه أداة مهمة:

- تغلف `fetch`
- تضيف `Authorization: Bearer <token>` تلقائيًا
- إذا جاء `401` → تعمل logout وتطلب من المستخدم تسجيل الدخول مجددًا

**الدرس المهم:** هذه طريقة عملية لتوحيد الطلبات المحمية.

---

### Part 5 — DataContext: “المكان الوحيد” الذي يجمع بيانات التحليلات (`store/DataContext.tsx`)

هذا الملف يجلب بيانات متعددة ويخزنها في state واحد:

- `sales`
- `forecast`
- `segments`
- `recommendations`
- `sentiment` (فيه state لكنه ليس محمّل بالكامل في النسخة الحالية من fetchData)
- `kpis`

والأهم: عند تغيير المستخدم (tenant) أو بعد رفع البيانات… يتم:

- مسح state القديم
- جلب جديد من السيرفر

فيه فلسفة واضحة مكتوبة في التعليقات:

- “لا تعرض بيانات قديمة (stale).”
- “تعامل مع 204 كـ no-content واظهر empty state.”

#### endpoints التي يطلبها DataContext (أمثلة)

1) KPIs:
- GET `/api/kpis`

2) Raw data:
- GET `/api/raw-data?limit=100`

3) Forecast (لـ dashboard والـ charts):
- GET `/api/monthly-sales`

4) Recommendations:
- GET `/api/recommendations?limit=10`

5) Segmentation:
- GET `/api/segmentation`

> مهم: DataContext يتعامل أحيانًا مع شكلين للرد:
> - رد موحّد `{ success, data, ... }`
> - أو رد مباشر Array/Dict
> لذا سترى: `const x = response.data || response`.

---

### Part 6 — DataUpload: رفع/استبدال/حذف datasets وربطها بالـ pipeline

صفحة `pages/DataUpload.tsx` هي “بوابة البيانات”.

ماذا تفعل؟

1) تعرض أنواع datasets:
   - sales (مطلوب)
   - customers (اختياري)
   - reviews (اختياري)

2) عند upload:
   - POST `/api/datasets/upload` (multipart)
   - يرسل `dataset_type` + `file`
   - يضيف header مهم:
     - `X-Company-ID: <user.company>`

3) بعد النجاح:
   - يعيد تحميل قائمة datasets: GET `/api/datasets`
   - ثم يعمل `refreshData()` من DataContext لإحضار النتائج الجديدة

4) عند replace:
   - POST `/api/datasets/{id}/replace`
   - ثم refreshData

5) عند delete:
   - DELETE `/api/datasets/{id}`
   - ثم:
     - `resetAllAnalytics()` لمسح أي state قديم فورًا
     - ثم refreshData (لترى 204/empty states)

**الدرس المهم:** هذه الصفحة توضح “علاقة البيانات الخام” بالـ pipeline والنتائج.

---

### Part 7 — Dashboard: دمج KPIs + Charts + Intelligence Components

في `pages/Dashboard.tsx` ترى 3 طبقات:

1) KPIs (Total Revenue/Orders/AOV/Top City)
   - تعتمد على `/api/kpis`

2) Charts (Revenue actual + forecast)
   - تعتمد على `/api/monthly-sales`

3) Intelligence (مميزات “المساعد الذكي”)
   - `components/AlertsPanel.tsx`
   - `components/SentimentInsights.tsx`

وهنا نقطة مهمة:

- هذه المكونات تستخدم `fetch('/api/...')` (أي تعتمد على Vite proxy)
- وتضيف header `X-Company-ID` من localStorage (مع fallback)

إذًا لكي تعمل بشكل صحيح:

- يجب وجود proxy في Vite
- ويجب أن يكون `localStorage.company` مضبوطًا

---

### Part 8 — AlertsPanel: `/api/alerts` كـ “Proactive Intelligence”

`AlertsPanel` يعرض:

- total_alerts
- توزيع حسب severity (critical/warning/info)
- قائمة alerts مع:
  - title
  - message
  - recommendation

ومهم جدًا:

- هذا هو الجزء الذي يحول dashboard من “reporting” إلى “assistant”
- لأنه لا يعرض أرقام فقط… بل “يوصي” بإجراء عملي.

---

### Part 9 — SentimentInsights: `/api/advanced-sentiment` كميزة Arabic-first

`SentimentInsights` يطلب:

- GET `/api/advanced-sentiment`

ثم يعرض:

- اللغة: نسبة Arabic/English
- Positive rate
- Aspect analysis (quality/price/delivery/service/packaging…)
- Alerts بالعربي والإنجليزي
- Strengths/Recommendations

**الدرس المهم:** هذه طبقة أعلى من `/api/sentiment` لأنها:

- ليست مجرد Positive/Negative
- بل تحليل محاور (aspects) + تنبيهات

---

### Part 10 — الصفحات الأخرى وربطها بالـ endpoints

1) `SalesAnalytics.tsx`
   - GET `/api/top-products?limit=10`
   - GET `/api/top-cities?limit=10`
   - جدول transactions من DataContext (`/api/raw-data`)

2) `Segmentation.tsx`
   - GET `/api/segmentation` (metadata + segments)

3) `Recommendations.tsx`
   - GET `/api/recommendations?limit=10`

4) `Sentiment.tsx`
   - GET `/api/sentiment`
   - POST `/api/sentiment/analyze` (تشغيل تحليل جديد)
   - يستخدم `useAuthFetch` (JWT)

5) `Forecasting.tsx`
   - يعتمد أساسًا على بيانات DataContext القادمة من `/api/monthly-sales`

---

### Part 11 — ملخص تربوي (كيف تفكر بالواجهة كنظام؟)

إذا أردت أن تفهم المشروع بسرعة، فكر هكذا:

- AuthContext = من أنت؟ (JWT + role + company)
- DataUpload = ماذا رفعت؟ (datasets)
- Pipeline في backend = ماذا اشتُقّ من البيانات؟ (EDA/RFM/Forecast/Recs/Sentiment)
- DataContext = ما هي آخر حالة من النتائج على السيرفر؟
- Pages/Components = كيف نعرض هذه الحالة بشكل مفهوم؟

وبهذا تكون الواجهة “واجهة نظام ذكاء مبيعات” وليست مجرد رسوم.

---

> بهذا اكتمل توثيق الواجهة `Sales_Intelligence_Project/frontend/*`: بنية التطبيق + proxy + auth + data fetching + upload workflow + صفحات التحليلات + طبقة Intelligence.


---

## ملحق 18: واجهة ثانية (Prototype) داخل `dashboard/` — ولماذا هي موجودة؟ وكيف تختلف عن `Sales_Intelligence_Project/frontend/`؟

داخل الـ workspace يوجد مشروع واجهة ثاني مستقل تمامًا اسمه:

- `dashboard/`

هذه الواجهة تشبه كثيرًا واجهة `Sales_Intelligence_Project/frontend/` من حيث:

- نفس اسم المنتج (InsightPro)
- نفس الصفحات (Dashboard / Forecasting / Segmentation / Recommendations / Sentiment / DataUpload / Settings)
- نفس المكتبات تقريبًا (lucide-react + recharts)
- نفس فكرة proxy إلى backend

لكنها تختلف في نقطة جوهرية:

- `dashboard/` = Prototype/Demo أبسط (Auth محلي بدون JWT)
- `Sales_Intelligence_Project/frontend/` = واجهة “متصلة” بنظام JWT الحقيقي (تسجيل دخول عبر `/api/auth/*`)

هذا الملحق يشرح `dashboard/` كطالب، ويجعلك تعرف متى تستخدمه ومتى تتجاهله.

---

### Part 1 — تشغيل `dashboard/` (Dev Server + Proxy)

في `dashboard/vite.config.ts`:

- المنفذ الافتراضي: `5173`
- يوجد proxy:
   - `/api` → `http://localhost:8000`

النتيجة:

- أي `fetch('/api/...')` من داخل `dashboard/` يذهب إلى FastAPI.

وهذا يمنع خطأ HTML بدل JSON الذي حصل سابقًا.

---

### Part 2 — App.tsx: نفس طريقة التنقل (بدون React Router)

ملف `dashboard/App.tsx` مطابق تقريبًا لنسخة `frontend/App.tsx`:

- إذا غير authenticated → `pages/Auth.tsx`
- إذا authenticated → `components/Layout.tsx` + صفحات حسب `currentPage`

التنقل يتم بـ state:

- `currentPage` يتغير عند الضغط من الـ sidebar.

---

### Part 3 — AuthContext في `dashboard/`: تسجيل دخول “محلي” للتجربة

الفرق الأكبر هنا في:

- `dashboard/store/AuthContext.tsx`

سلوكه:

- لا يتصل بالـ backend إطلاقًا.
- `login(email, company)` ينشئ User وهمي ويخزنه في localStorage باسم:
   - `insight_pro_user`
- الدور ثابت تقريبًا (ADMIN) داخل هذا البروتوتايب.

يعني كطالب:

- هذه الواجهة تعمل حتى لو لم تشغل `/api/auth/login`.
- لكنها ليست “أمنية” ولا تمثل JWT الحقيقي.

متى تكون مفيدة؟

- عند عرض UI/UX بسرعة.
- عند تجربة الصفحات بدون إعداد قاعدة بيانات users.

متى لا تعتمد عليها؟

- عندما تريد اختبار flow الحقيقي (JWT + roles + verify).

---

### Part 4 — DataContext في `dashboard/`: نفس فكرة “اجلب كل شيء من السيرفر”

`dashboard/store/DataContext.tsx` يجلب البيانات من endpoints نفسها تقريبًا:

- `/api/kpis`
- `/api/raw-data`
- `/api/monthly-sales`
- `/api/recommendations`
- `/api/segmentation`
- `/api/sentiment`

وهو يرسل header مهم لعزل الشركات:

- `X-Company-ID: user.company`

هذه نفس فكرة multi-tenant في backend.

**فرق صغير مهم:**

- في `dashboard/` لا يوجد JWT ولا `Authorization`.
- في `frontend/` يوجد `useAuthFetch` ويضيف `Authorization: Bearer ...` للـ endpoints المحمية.

---

### Part 5 — الصفحات في `dashboard/`: عرض بيانات بدون طبقة Intelligence

عند قراءة `dashboard/pages/Dashboard.tsx` ستجد:

- KPI cards + charts (forecast/segments)
- لا يوجد `AlertsPanel` ولا `SentimentInsights` هنا (مقارنة بـ `frontend/pages/Dashboard.tsx`).

إذًا هذه الواجهة تركز على “التحليلات الكلاسيكية” أكثر من طبقة intelligence.

---

### Part 6 — DataUpload في `dashboard/`: نفس Workflow رفع/استبدال/حذف

`dashboard/pages/DataUpload.tsx` مطابق تقريبًا لنسخة `frontend/pages/DataUpload.tsx`:

- GET `/api/datasets`
- POST `/api/datasets/upload`
- POST `/api/datasets/{id}/replace`
- DELETE `/api/datasets/{id}`
- GET `/api/datasets/{id}/preview`

ومهم جدًا:

- بعد كل عملية ناجحة يعمل `refreshData()` لإعادة جلب نتائج التحليلات.
- وعند الحذف يعمل `resetAllAnalytics()` ثم refresh.

هذا هو السلوك الصحيح لمنع stale data.

---

### Part 7 — لماذا يوجد مشروعان واجهة؟ (خلاصة تربوية)

فكر فيها كالتالي:

- `dashboard/` = واجهة Demo/Prototype سريعة، بدون تعقيد JWT
- `Sales_Intelligence_Project/frontend/` = الواجهة “الحقيقية” التي تحاول تمثيل منتج SaaS (JWT + verify + roles) + مكونات Intelligence

إذا هدفك هو تشغيل المشروع end-to-end كما صُمم في توثيقنا:

- ركّز على `Sales_Intelligence_Project/frontend/`.

إذا هدفك هو عرض تصميم الواجهة فقط بسرعة:

- استخدم `dashboard/`.

---

> بهذا اكتمل توثيق `dashboard/` كواجهة ثانية، مع توضيح الفروقات ولماذا من الأفضل الاعتماد على `Sales_Intelligence_Project/frontend/` عند اختبار الـ backend الحقيقي.


---

## ملحق 19: تشغيل المشروع End‑to‑End على Windows (Backend + Frontend + Upload + Verification + Troubleshooting)

هذا الملحق هو “دليل تشغيل عملي” خطوة بخطوة.

الهدف كطالب:

- تشغل الـ backend والواجهة بدون ارتباك في المسارات.
- ترفع datasets وتلاحظ كيف تتغير النتائج في الصفحات.
- تعرف كيف تختبر endpoints يدويًا.
- تعرف أكثر الأخطاء شيوعًا وكيف تحلها بسرعة.

---

### Part 1 — قبل التشغيل: ما الذي تحتاجه؟

1) Python (يفضل داخل Virtual Environment)
2) Node.js + npm

المجلد الأساسي للمشروع هنا:

- `Sales_Intelligence_Project/`

وفي داخله:

- `backend/` (FastAPI)
- `frontend/` (React)
- `src/` (ML pipeline scripts)
- `data/` و`output/` (مخرجات وملفات)

---

### Part 2 — تشغيل الـ Backend (النسخة الأساسية v1: `backend/main.py`)

#### الطريقة الموصى بها (من جذر المشروع)

افتح PowerShell في:

- `Sales_Intelligence_Project/`

ثم:

1) تثبيت الاعتمادات:

```powershell
python -m pip install -r backend/requirements.txt
```

2) تشغيل API:

```powershell
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

بعدها:

- Swagger: `http://localhost:8000/docs`

إذا ظهر لك `WinError 10048` (المنفذ 8000 مشغول/محجوز على Windows):

- شغّل على 8001 بدل 8000:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

- أو استخدم الملف الجاهز (تشغيل بنقرة مزدوجة):
   - `Sales_Intelligence_Project/run_backend_8001.bat`

#### طريقة بديلة (من داخل مجلد backend)

لو أنت داخل:

- `Sales_Intelligence_Project/backend/`

شغّل:

```powershell
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**ملاحظة مهمة:** الطريقتان صحيحتان… لكن لا تخلط بين المسارين في نفس الأمر.

---

### Part 3 — تشغيل الـ Backend v2 (المحسن: `backend/main_enhanced.py`) + تهيئة DB + Users

هذه النسخة تضيف JWT + SQLAlchemy + Background Tasks.

1) تثبيت الاعتمادات (قد تحتاج إضافيًا: `python-jose`, `passlib[bcrypt]`, `sqlalchemy` … حسب إعدادك):

```powershell
python -m pip install -r backend/requirements.txt
python -m pip install python-jose[cryptography] passlib[bcrypt] sqlalchemy
```

2) إنشاء/تهيئة قاعدة البيانات + seed data:

```powershell
python backend/init_db.py
```

3) تشغيل v2:

```powershell
python -m uvicorn backend.main_enhanced:app --reload --host 0.0.0.0 --port 8000
```

بديل Windows سريع على منفذ مختلف:

- `Sales_Intelligence_Project/run_backend_v2_8002.bat`

بعدها يمكنك تسجيل الدخول من الواجهة عبر `/api/auth/login`.

---

### Part 4 — تشغيل الواجهة الأساسية (React) — `Sales_Intelligence_Project/frontend/`

افتح Terminal جديد في:

- `Sales_Intelligence_Project/frontend/`

ثم:

```powershell
npm install
npm run dev
```

مهم:

- ملف `frontend/vite.config.ts` فيه proxy لـ `/api`.
- افتراضيًا تم ضبطه على `http://localhost:8001` لأن بعض أجهزة Windows قد يكون عندها المنفذ 8000 محجوز/مشغول.
- يمكنك تغيير الهدف بسهولة عبر متغير بيئة: `VITE_API_TARGET`.
- هذا يعني أن أي request مثل `fetch('/api/alerts')` يذهب تلقائيًا للـ backend.

إذا أردت استخدام base url صريح بدل proxy:

- يمكنك ضبط `VITE_API_BASE` (اختياري) لكن المشروع يعمل حتى بدونها بسبب proxy.

مثال سريع (Windows PowerShell) لتغيير هدف الـ proxy مؤقتًا عند تشغيل الواجهة:

```powershell
$env:VITE_API_TARGET = "http://localhost:8001"
npm run dev
```

---

### Part 5 — تشغيل الواجهة الثانية (Prototype) — `dashboard/` (اختياري)

هذه واجهة demo (بدون JWT).

افتح Terminal في:

- `dashboard/`

ثم:

```powershell
npm install
npm run dev
```

هي أيضًا تحتوي proxy لـ `/api`.

---

### Part 6 — أول اختبار سريع: هل الـ API شغال؟

اختبر من المتصفح:

- `http://localhost:8000/` (يعيد status)
- `http://localhost:8000/docs`

ومن PowerShell (اختبار endpoints):

```powershell
(Invoke-WebRequest -Uri "http://localhost:8000/api/health" -Method GET).Content
```

إذا endpoint يتطلب tenant header، جرّب:

```powershell
(Invoke-WebRequest -Uri "http://localhost:8000/api/alerts" -Headers @{'X-Company-ID'='Acme Corp'} -Method GET).Content
```

---

### Part 7 — سيناريو عملي: رفع datasets ثم مشاهدة النتائج في الصفحات

#### 1) افتح صفحة Data Ingestion

في الواجهة:

- Data Ingestion (DataUpload)

#### 2) ارفع Sales dataset أولًا (مهم)

اختر النوع `sales` وارفع CSV.

بعد الرفع:

- النظام يحفظ dataset
- ثم الـ pipeline ينتج مشتقات مثل:
   - `data/merged_data.csv`
   - `data/cleaned_dataset.csv`
   - `data/sales_forecast.csv` أو `output/*prophet*.csv`
   - `data/rfm_table.csv`
   - `data/product_recommendations.csv`

#### 3) ارفع Reviews (اختياري لكن مهم للـ Sentiment)

اختر النوع `reviews` وارفع CSV.

بعدها تظهر:

- `Sentiment` (ملخص)
- `Customer Feedback Intelligence` (advanced sentiment)

#### 4) افتح الصفحات واحدة واحدة ولاحظ “مصدر البيانات”

- Dashboard: KPIs + Forecast chart + Alerts + SentimentInsights
- Forecasting: يعتمد غالبًا على `/api/monthly-sales`
- Segmentation: يعتمد على `/api/segmentation`
- Recommendations: يعتمد على `/api/recommendations`
- Sales Analytics: يعتمد على `/api/top-products` و`/api/top-cities`

---

### Part 8 — مفهوم مهم: 204 (No Content) ليس خطأ

في مشروعك كثير من endpoints ترجع:

- HTTP 204

وهذا معناه:

- لا توجد بيانات (مثلاً لم ترفع reviews بعد)

والواجهة مصممة لتتعامل مع ذلك بإظهار empty state بدل crash.

---

### Part 9 — Troubleshooting سريع لأشهر المشاكل

#### (A) خطأ: `Unexpected token '<' ... not valid JSON`

السبب:

- الواجهة طلبت `/api/...` لكن الرد كان HTML (غالبًا من Vite server).

الحل:

- تأكد proxy موجود في `vite.config.ts`
- أو استخدم `VITE_API_BASE` مع URL صريح

#### (B) خطأ: `401 Unauthorized`

السبب:

- endpoint محمي بـ JWT ولم ترسل `Authorization`.

الحل:

- سجّل الدخول من الواجهة
- أو تأكد أن الواجهة تستعمل `useAuthFetch`

#### (C) خطأ: `Failed to fetch` أو `ECONNREFUSED`

السبب:

- backend غير شغال أو المنفذ غلط.

الحل:

- تأكد `uvicorn` شغال على 8000
- افتح `http://localhost:8000/docs`

#### (D) لا تظهر بيانات بعد رفع ملف

الأسباب الأكثر شيوعًا:

- نوع dataset غير صحيح (رفعت sales كـ reviews مثلًا)
- ملف CSV ناقص أعمدة أساسية
- الشركة (tenant) غير متطابقة مع header `X-Company-ID`

الحل:

- راجع صفحة DataUpload (النوع + رسالة الخطأ)
- راجع أن `X-Company-ID` يساوي اسم الشركة الصحيح
- جرّب endpoint مباشرة عبر PowerShell

#### (E) `uvicorn` يبدأ ثم يطفئ فورًا (ويظهر Exit Code 1)

هذا السلوك معناه غالبًا أن عملية السيرفر استلمت إشارة إيقاف (SIGINT/SIGTERM) أو حدث خطأ خارج “مسار الطباعة” المعتاد.

خطوات تشخيص عملية (بالترتيب):

1) جرّب منفذ مختلف لتستبعد تعارض المنفذ:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --log-level debug
```

2) جرّب بدون `--reload` (reloader أحيانًا يسبب إغلاق مبكر على بيئات معينة):

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --log-level debug
```

3) تأكد أن المنفذ غير مستخدم (Windows):

```powershell
netstat -ano | findstr ":8000"
```

لو وجدت PID يشغل المنفذ، يمكنك إغلاقه:

```powershell
taskkill /PID <PID> /F
```

4) لو كنت تعمل على Python نسخة “تجريبية/حديثة جدًا”، جرّب Python 3.11 أو 3.12 للمشروع.
أدوات مثل `uvicorn`, `watchfiles`, `pydantic` قد تتصرف بشكل غير متوقع على نسخ Python غير مستقرة.

#### (F) الطرفية تسبق كل أمر بحرف غريب مثل `ؤ` (في VS Code)

هذا ليس خطأ في المشروع؛ هو مشكلة إدخال/لغة/IME أو لصق نص يحتوي علامة RTL/حرف إضافي.

حلول سريعة:

- افتح Terminal جديدة داخل VS Code (زر سلة المهملات لإغلاق القديمة ثم `Terminal: New Terminal`).
- بدّل لغة الإدخال إلى English (Win+Space) قبل كتابة أي أمر.
- جرّب تشغيل الأوامر من Windows Terminal أو PowerShell خارجي (خارج VS Code) لعزل المشكلة.
- إن استمرت: أعد تشغيل VS Code.

---

### Part 10 — شرح تعليمي (مهم جدًا): لماذا يظهر Exit Code 1؟ ولماذا `uvicorn` “يشتغل ثم يطفئ”؟

هذا الجزء ليس خطوات فقط… هذا “فهم”.

#### 10.1 ما معنى Exit Code 1؟

عندما تشغّل برنامج من الطرفية، ينتهي البرنامج برقم اسمه **Exit Code**:

- `0` يعني: انتهى طبيعيًا (Success).
- `1` (أو أي رقم غير 0) يعني: حصل خطأ أو تم الإنهاء بشكل غير طبيعي.

في حالتنا: `uvicorn` يطبع أحيانًا:

- `Application startup complete.`

ثم بعدها مباشرة:

- `Shutting down`
- وينهي بـ Exit Code 1

وهذا غالبًا يحدث لأحد سببين:

1) **فشل binding للمنفذ** (أشهر سبب على Windows)
2) **استلم إشارة إيقاف/تم إيقافه من بيئة التشغيل** (أحيانًا من terminal runner أو reloader)

#### 10.2 خطأ `WinError 10048` (أهم سبب عندك)

الرسالة:

> `OSError: [WinError 10048] Only one usage of each socket address ... is normally permitted`

ترجمتها التعليمية:

- “أنا (السيرفر) حاولت أحجز المنفذ (مثلاً 8000)، لكن المنفذ **محجوز** أو **مشغول** بالفعل”.

متى يحصل هذا؟

- يوجد برنامج آخر شغال على نفس المنفذ (مثلاً Uvicorn قديم، أو برنامج ثاني).
- أو يوجد listener مخفي/معلق (أحيانًا بعد crash).

إذن: حتى لو كانت كل ملفات المشروع صحيحة 100%… **لن يعمل** السيرفر على 8000 إذا كان المنفذ غير متاح.

#### 10.3 كيف تشخّص المنفذ على Windows (فهم + أوامر)

الفكرة: نحن نريد جواب سؤال واحد:

> “من هو البرنامج الذي ماسك المنفذ 8000؟”

أداة 1: `netstat` (قديمة لكنها مفيدة)

```powershell
netstat -ano | findstr ":8000"
```

أداة 2: `Get-NetTCPConnection` (أوضح على PowerShell)

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess
```

بعد أن تحصل على `OwningProcess` (PID):

```powershell
tasklist /FI "PID eq <PID>"
```

لو تريد إيقافه:

```powershell
taskkill /PID <PID> /F
```

ملاحظة تعليمية مهمة:

- أحيانًا قد ترى “PID” في مخرجات الشبكة لكنه يختفي سريعًا (عملية انتهت للتو)، لذلك كرر الأمر مرة أو مرتين.

#### 10.4 لماذا “يشتغل ثم يطفئ” بدون أن ترى خطأ واضح؟

هنا نميّز بين حالتين:

**الحالة (A): يطفئ لأنه لا يستطيع حجز المنفذ**

- غالبًا سترى `WinError 10048` (ولو مرة واحدة).
- الحل: استخدم منفذ آخر مثل 8001.

**الحالة (B): يطفئ لأن بيئة التشغيل أوقفته**

- بعض أدوات التشغيل (أو طريقة تشغيل داخل VS Code Tasks/Runner) قد تُرسل إشارة إيقاف عند انتهاء “الأمر” أو عند حصول خطأ في جزء آخر.
- أيضًا خيار `--reload` قد يسبب سلوك غريب إذا كان file watcher غير متوافق.

تعليميًا: لذلك نجرّب دائمًا:

- بدون `--reload`
- وعلى `127.0.0.1`
- وعلى منفذ “فاضي”

#### 10.5 مشكلة الطرفية التي تضع حرفًا مثل `ؤ` قبل الأوامر

هذا النوع من المشاكل ليس من FastAPI ولا من المشروع.

التفسير التعليمي:

- الطرفية تقرأ أحرف غير مرئية/غير متوقعة بسبب لغة الإدخال (IME) أو لصق نص يحتوي علامات RTL.
- عندما يصبح الأمر مثل `ؤSet-Location` فهو اسم جديد غير معروف، لذلك PowerShell يقول: “الأمر غير موجود”.

أبسط حل عملي:

- افتح Terminal جديدة.
- غيّر لغة الإدخال إلى EN.
- جرّب تشغيل نفس الأمر من Windows Terminal خارج VS Code.

الفكرة هنا: **أنت تعالج أداة الإدخال** وليس الكود.

---

> بهذا اكتمل دليل التشغيل End‑to‑End: تشغيل backend/واجهة + رفع بيانات + اختبار endpoints + حلول سريعة لأكثر المشاكل شيوعًا.


---

## ملحق 20: شرح تعليمي للـ API (Headers + JWT + Multi‑Tenant) + كيف تختبر Endpoints عمليًا

هذا الملحق هدفه “تفهم” كيف تتعامل الواجهة مع الـ API، وكيف تختبر أنت بنفسك بدون الاعتماد على الواجهة.

سنعالج 3 أفكار كبيرة:

1) ما هو الـ Header؟ ولماذا نحتاجه؟
2) ما هو JWT؟ ولماذا `Authorization: Bearer ...`؟
3) ما معنى `X-Company-ID`؟ ولماذا هو مهم في هذا المشروع؟

---

### Part 1 — ما هو الـ Header؟ (فكرة بسيطة)

عندما ترسل Request للـ API، أنت ترسل:

- **Method** مثل GET/POST
- **URL** مثل `/api/alerts`
- **Headers** (معلومات إضافية)
- **Body** (محتوى الطلب) إذا كان POST/PUT

الـ Headers مثل “بطاقة تعريف” مرفقة مع الطلب.

في مشروعنا أهم Headerين هما:

1) `Authorization`
2) `X-Company-ID`

---

### Part 2 — JWT Authentication (تعليميًا: ما المشكلة التي يحلها؟)

لو لم يكن لدينا JWT:

- أي شخص يستطيع فتح `/api/...` ويأخذ البيانات.

مع JWT:

- السيرفر يقول لك: “أثبت أنك مستخدم مسجل دخول”.

كيف يعمل ذلك عمليًا؟

1) أنت ترسل email/password إلى endpoint تسجيل الدخول.
2) السيرفر يرجع لك `access_token`.
3) أنت ترسل هذا التوكن في كل request بعد ذلك داخل header:

```
Authorization: Bearer <token>
```

فكرة كلمة Bearer:

- معناها: “أنا أحمل التوكن معي”.

---

### Part 3 — الفرق بين Backend v1 و v2 بخصوص JWT

#### Backend v1 (النسخة الأساسية)

- يدعم JWT “إذا كانت مكتبة `python-jose` مثبتة”.
- وإذا لم تكن مثبتة، قد يعمل بنمط demo token (حسب الكود).
- بعض endpoints قد تكون متاحة بدون JWT (حسب الاعتماد في الواجهة).

تعليميًا: v1 ممتاز للتعلم واختبار الـ ML pipeline بسرعة.

#### Backend v2 (main_enhanced)

- يعتمد على JWT بشكل أوضح + Roles (admin/analyst/viewer).
- يعني هناك endpoints “لن تعمل” إلا إذا كان `Authorization` صحيح.

تعليميًا: v2 أقرب لبيئة Production.

---

### Part 4 — Multi‑Tenant: ما معنى `X-Company-ID`؟

هذا المشروع يدعم أكثر من شركة (Multi‑Tenant).

بدل ما يكون عندك API لكل شركة، أنت تستخدم نفس الـ endpoint… لكن تقول للسيرفر “أنا أقصد أي شركة؟” عبر:

```
X-Company-ID: Acme Corp
```

متى تحتاجه؟

- عندما endpoint يعتمد على ملفات/مخرجات تخص شركة معينة (مثل alerts, outputs, uploads)

تعليميًا:

- JWT يقول: “من أنت؟”
- `X-Company-ID` يقول: “أنت تعمل على بيانات أي شركة؟”

---

### Part 5 — اختبار سريع عبر Swagger UI (أسهل طريقة كطالب)

افتح:

- `http://localhost:8001/docs` (أو 8000 إذا تستخدمه)

ماذا تستفيد من Swagger؟

- ترى كل endpoints
- تستطيع تجربة request مباشرة
- ترى Body/Response بشكل مرتب

إذا endpoint يحتاج JWT:

- في Swagger غالبًا يوجد زر Authorize
- تضع التوكن هناك ثم يجرب لك

---

### Part 6 — اختبار عملي عبر PowerShell (مهم جدًا)

#### 6.1 طلب GET بسيط بدون headers

```powershell
(Invoke-WebRequest -Uri "http://127.0.0.1:8001/" -Method GET).Content
```

#### 6.2 GET مع `X-Company-ID`

```powershell
(Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/alerts" -Headers @{'X-Company-ID'='Acme Corp'} -Method GET).Content
```

#### 6.3 تسجيل الدخول للحصول على Token (فكرة عامة)

الطريقة تختلف حسب الـ endpoint في نسخة الـ backend التي تعمل بها.

مثال تعليمي (قد تحتاج تعديل مسار endpoint حسب النسخة):

```powershell
$body = @{ email = "admin@acme.com"; password = "admin123" } | ConvertTo-Json
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/auth/login" -Method POST -ContentType "application/json" -Body $body
$token = $resp.access_token
```

ثم تستخدمه:

```powershell
$headers = @{ Authorization = "Bearer $token"; "X-Company-ID" = "Acme Corp" }
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/alerts" -Headers $headers -Method GET
```

تعليميًا: إذا رجع لك 401 معناها أن `Authorization` ناقص أو التوكن غير صحيح أو endpoint يتطلب دور (role) أعلى.

---

### Part 7 — كيف تفهم 401 و 403؟

#### 401 Unauthorized

يعني:

- “أنت لم تثبت هويتك”

أشهر الأسباب:

- لم ترسل `Authorization`
- التوكن منتهي أو خاطئ

#### 403 Forbidden

يعني:

- “أنا أعرف من أنت… لكن ليس مسموح لك”

مثال:

- أنت viewer وتحاول تعمل endpoint خاص بـ admin.

---

### Part 8 — كيف تفهم 400 و 422؟

#### 400 Bad Request

يعني:

- أنت أرسلت طلب ناقص أو header مطلوب غير موجود.

مثال شائع في مشروعنا:

- `Missing X-Company-ID header`

#### 422 Unprocessable Entity

يعني:

- شكل JSON الذي أرسلته لا يطابق Model الذي يتوقعه FastAPI.

تعليميًا: هذا خطأ “صياغة” أكثر منه خطأ “منطق”.

---

### Part 9 — ربط هذا الكلام بالواجهة (كيف يفكر الـ Frontend؟)

الواجهة عادة تعمل التالي:

1) المستخدم يسجل دخول → تخزين token
2) أي API call بعد ذلك يتم عبر helper يضيف `Authorization`
3) إذا المشروع multi-tenant، يتم إضافة `X-Company-ID` أيضًا

لهذا إذا ظهرت مشاكل “بيانات شركة غير صحيحة”:

- غالبًا header `X-Company-ID` غير مضبوط
- أو localStorage/company state غير متزامن

---

> بهذا اكتمل الشرح التعليمي للـ API: headers + JWT + multi‑tenant + اختبار عملي عبر Swagger وPowerShell.


---

## ملحق 21: شرح تعليمي لتدفّق البيانات (Upload → Pipeline → Outputs → API → Pages) ولماذا تظهر 204

هذا الملحق هو “قلب المشروع” من ناحية الفهم.

سأشرحه كقصة واضحة:

1) أنت ترفع ملف CSV
2) السيرفر يحفظه
3) الـ pipeline يعالج ويولّد ملفات مشتقة
4) الـ API يقرأ الملفات المشتقة ويرجع JSON
5) الواجهة ترسم Charts وجداول

إذا فهمت هذا الملحق… ستستطيع حل 80% من مشاكل “لا توجد بيانات” بنفسك.

---

### Part 1 — ما المقصود بـ “Data Flow” هنا؟

في مشاريع الداشبورد عادة يوجد مساران:

- مسار “البيانات الخام” (Raw): CSV كما هو.
- مسار “البيانات المشتقة” (Derived): نواتج التحليل مثل التوقعات، RFM، توصيات، Sentiment…

مشروعك يعتمد بقوة على المسار الثاني.

يعني: ليس كافيًا أن ترفع ملف… يجب أن يولّد الـ pipeline مخرجات قابلة للاستهلاك.

---

### Part 2 — أين تذهب الملفات بعد Upload؟ (تعليميًا)

عند رفع dataset عبر الواجهة (DataUpload):

- الـ backend يستقبل `UploadFile`
- يحدد نوع الملف (`sales`, `customers`, `reviews`)
- يحفظه على القرص داخل مجلدات المشروع

بعد ذلك يبدأ توليد ملفات مشتقة في:

- `Sales_Intelligence_Project/data/`
- `Sales_Intelligence_Project/output/`

فكرة مهمة:

- الواجهة لا “تحسب” التحليلات.
- الواجهة فقط “تعرض” ما أنتجه الـ backend.

---

### Part 3 — ما هو الـ Pipeline؟ (فهم عملي)

كلمة Pipeline تعني سلسلة خطوات متتابعة، مثل:

1) تنظيف/دمج بيانات المبيعات
2) تجميع شهري (Monthly aggregation)
3) Forecasting (Linear أو Prophet)
4) RFM Segmentation
5) Recommendations (Market Basket / Apriori)
6) Sentiment (على reviews)
7) Alerts/Insights (تقرأ المخرجات وتولّد تنبيهات)

تعليميًا:

- بعض الخطوات تعتمد على sales فقط.
- بعض الخطوات تحتاج reviews.
- لذلك من الطبيعي أن ترى صفحات تعمل وصفحات فارغة حتى ترفع النوع الصحيح.

---

### Part 4 — ما الذي يقرأه الـ API فعلًا؟

هذه نقطة “ترفع مستواك”:

الـ API غالبًا لا يحسب من الصفر في كل request.

بدل ذلك:

- يقرأ ملفات جاهزة من `data/` أو `output/`.

مثال ذهني:

- صفحة Forecasting في الواجهة → تنادي endpoint → endpoint يقرأ `sales_forecast.csv` أو ملف prophet → يرجع JSON → الواجهة ترسم chart.

بمعنى:

إذا الملف غير موجود… لن توجد بيانات.

---

### Part 5 — لماذا 204 (No Content) تظهر كثيرًا؟

هذا سلوك “صحيح” وتعليميًا ممتاز.

فكرة 204:

- السيرفر يقول: “أنا فهمت طلبك، لكن لا يوجد محتوى لأرجعه الآن”.

متى يحدث هذا في مشروعك؟

- لم ترفع dataset المطلوب.
- رفعت dataset لكن الـ pipeline لم ينتج الملف المشتق (إما فشل أو الشروط لم تتحقق).
- أنت تستهدف شركة (tenant) لا يوجد لها مخرجات بعد.

لماذا لا يرجع 500 بدل 204؟

- لأن 500 يعني “السيرفر انكسر”.
- أما 204 يعني “لا توجد بيانات” وهذا شيء طبيعي في الأنظمة التحليلية.

تعليميًا: 204 = “المعادلة لم تكتمل بعد” وليس “البرنامج خرب”.

---

### Part 6 — Checklist تعليمي: كيف أتأكد أن كل شيء جاهز؟

فكر فيها كقائمة فحص (Inspection):

#### 6.1 هل عندي ملفات Raw؟

- هل يوجد `sales.csv` أو ملف مبيعات محفوظ؟
- هل يوجد `customer_reviews.csv` أو ملف reviews محفوظ؟

#### 6.2 هل عندي ملفات Derived؟

اذهب لمجلد:

- `Sales_Intelligence_Project/data/`

وابحث عن (أمثلة شائعة):

- `cleaned_dataset.csv`
- `merged_data.csv`
- `rfm_table.csv`
- `product_recommendations.csv`
- `sentiment_results.csv`

ثم اذهب إلى:

- `Sales_Intelligence_Project/output/`

وابحث عن (حسب الشركة):

- `<Company>_alerts.json`
- `<Company>_advanced_sentiment.json`
- `<Company>_forecast_*.csv`

تعليميًا:

- وجود الملفات = 70% من الطريق.
- محتوى الملفات (غير فارغ) = 100% جاهزية.

---

### Part 7 — خطأ شائع جدًا: رفعت sales لكن لا توجد Recommendations

هذا طبيعي أحيانًا.

لأن Market Basket يحتاج “طلبات متعددة المنتجات” (multi‑product orders).

إذا كانت بياناتك كل OrderID فيها منتج واحد فقط:

- لن يستطيع Apriori استخراج قواعد IF/THEN قوية.
- قد ينتج ملف توصيات فارغ.

تعليميًا: هذا ليس bug… هذا “قيود رياضية” على الخوارزمية.

---

### Part 8 — خطأ شائع جدًا: Sentiment فارغ رغم وجود Reviews

أسباب تعليمية محتملة:

- عمود النص ليس بالاسم المتوقع (مثل `review_text`/`text`/`comment`).
- Encoding في CSV جعل القراءة تفشل أو تُنتج نصوصًا فارغة.
- يوجد تنظيف قوي حذف أغلب الصفوف.

كيف تعرف؟

- افتح ملف `sentiment_results.csv` وانظر هل عدد الصفوف يساوي تقريبًا عدد reviews.

---

### Part 9 — كيف تربط “كل صفحة” بما تعتمد عليه؟ (طريقة تفكير)

بدل ما تحفظ أسماء endpoints، احفظ المنهج:

1) اسم الصفحة → ما الذي تعرضه؟
2) ما هو مصدره؟ (sales/reviews/customers)
3) ما هو الملف المشتق المتوقع؟
4) ما هو endpoint الذي يرجعه؟

مثال:

- Forecasting Page
   - تعرض: خط توقع + قيم مستقبلية
   - المصدر: sales
   - المتوقع: forecast CSV
   - الـ API يرجعه كـ JSON

هكذا تصبح قادرًا على التشخيص:

إذا الصفحة فارغة → ارجع خطوة للخلف: هل الملف موجود؟ هل الـ endpoint يعيد 204؟

---

### Part 10 — لماذا نستخدم “القراءة من القرص” بدل caching قوي؟

تعليميًا يوجد توازن:

- caching يعطي سرعة
- لكن في مشاريع الداشبورد التعليمية/التجريبية، أهم شيء هو “عدم عرض بيانات قديمة” بعد upload/delete.

لذلك ستلاحظ في المشروع تركيز على:

- إعادة تحميل البيانات من القرص عند startup
- أو بعد pipeline

وهذا يجعل سلوك النظام “واضح” عند التعلم.

---

> بهذا اكتمل شرح تدفّق البيانات: أنت الآن تستطيع ربط أي صفحة بالملفات التي تقف خلفها، وتفهم لماذا 204 ليست خطأ.



---

## ملحق 22: Phase 7 — Advanced Sentiment (Aspect-Based) — (`src/07_advanced_sentiment.py` + `src/advanced_sentiment.py`) وربطه بـ `/api/advanced-sentiment`

هذا الملحق يشرح “ذكاء المشاعر المتقدم” الذي لا يكتفي بأن يقول: “المراجعة إيجابية/سلبية”، بل يحاول استخراج **الجوانب (Aspects)** التي يتحدث عنها العميل مثل:

- الجودة (quality)
- السعر (price)
- التوصيل (delivery)
- الخدمة (service)
- التغليف (packaging)

والهدف النهائي: تحويل النصوص إلى **قرارات** (Actionable Insights).

---

### 22.1 ما الفرق بين Sentiment العادي و Advanced Sentiment؟

1) Sentiment العادي (مثل `src/06_sentiment.py` و`src/06_sentiment_arabic.py`):

- يخرج “Polarity/Label” لكل Review.
- مناسب لتلخيص عام: نسبة الإيجابي/السلبي.

2) Advanced Sentiment (`src/07_advanced_sentiment.py`):

- يركز على سؤال أقوى: “ما الذي يعجبهم وما الذي يزعجهم؟”
- لذلك يقسم النص إلى “جوانب” ثم يحكم على كل جانب (إيجابي/سلبي/محايد).

**تعليميًا:**

- Sentiment العادي = “درجة حرارة الجسم”.
- Advanced Sentiment = “تقرير طبي: أين المشكلة تحديدًا؟”.

---

### 22.2 هيكل الكلمات المفتاحية للجوانب ASPECT_KEYWORDS

داخل `src/07_advanced_sentiment.py` ستجد قاموسًا اسمه `ASPECT_KEYWORDS`:

- لكل aspect يوجد:
  - قائمة كلمات عربية `ar`
  - قائمة كلمات إنجليزية `en`
  - `icon` للاستخدام في الواجهة

مثلاً: جانب delivery لديه كلمات مثل “توصيل/شحن/تأخير/مندوب…”، وهذا يجعل الاستخراج بسيطًا.

**ملاحظة مهمة:**

هذا أسلوب Rule-Based بسيط (قائم على كلمات).
ميزته: سريع وسهل ويفيد كمشروع تدريبي.
عيبه: لا يفهم سياق الجملة ولا السخرية ولا التراكيب.

---

### 22.3 كشف اللغة detect_language()

الدالة `detect_language(text)` تحسب نسبة الحروف العربية في النص:

- إذا كانت > 30% تعتبر Arabic
- وإلا تعتبر English

**تعليميًا:** هذا نموذج مبسط لتحديد اللغة (Language Identification).

---

### 22.4 استخراج الجوانب extract_aspects()

الدالة `extract_aspects(text, language)`:

1) تختار قائمة الكلمات حسب اللغة.
2) تفحص وجود أي كلمة من كلمات الجانب داخل النص.
3) إذا وجدت كلمة واحدة على الأقل → تسجل أن هذا الجانب “مذكور”.

**نتيجة هذا الجزء:** قائمة مثل:

- `["quality", "delivery"]`

أي: العميل تحدث عن الجودة والتوصيل.

---

### 22.5 حكم المشاعر لكل جانب get_aspect_sentiment()

الدالة `get_aspect_sentiment(text, aspect, language)` لا تستخدم نموذج عميق، بل:

- للعربية: تعد كلمات إيجابية (`ARABIC_POSITIVE`) وسلبية (`ARABIC_NEGATIVE`).
- للإنجليزية: تستخدم قائمة بسيطة (good/great… مقابل bad/terrible…)

ثم:

- إذا positives > negatives → positive
- إذا negatives > positives → negative
- وإلا → neutral

**تعليميًا:** هذه قاعدة Decision بسيطة، لكنها توضح منطق “مقارنة إشارات” داخل النص.

---

### 22.6 تحليل مراجعة واحدة analyze_review()

الدالة `analyze_review(text)` تُخرج كائنًا يحتوي:

- `language`
- `overall_sentiment`
- `aspects`
- `aspect_sentiments` مثل:
  - `{"delivery": "negative", "quality": "positive"}`
- `confidence` (ثقة مبسطة)

**ما معنى confidence هنا؟**

ليست probability حقيقية من نموذج ML؛ هي تقريب (heuristic) يعتمد على الفرق بين عدد الكلمات الإيجابية والسلبية.

---

### 22.7 توليد “Insights” قابلة للتنفيذ generate_aspect_insights()

هذه هي نقطة التحول من “تحليل” إلى “قرار”.

المنطق:

1) يحسب إحصائيات لكل aspect:
   - عدد مرات ذكره
   - عدد الإيجابي/السلبي/المحايد
2) يصنع Summary لكل aspect:
   - `positive_pct` و`negative_pct` و`total_mentions`
3) يصنع Alerts:
   - إذا السلبي مرتفع جدًا (مثلاً > 40%) وكان total_mentions كافي
4) يصنع Recommendations:
   - إذا الإيجابي مرتفع جدًا (مثلاً > 70%) → “هذا جانب قوة”

**تعليميًا:** هذه خطوة “Business Rules”.

---

### 22.8 نقطة الدخول run_advanced_sentiment_analysis()

الدالة `run_advanced_sentiment_analysis(company_name)`:

1) تبحث عن ملف reviews الخاص بالشركة (داخل `data/<company>/reviews/` أو fallback).
2) تحدد عمود النص (مثل ReviewText).
3) تطبق `analyze_review` على كل صف.
4) تنتج Output JSON شامل.
5) تحفظ الملف عادة باسم:

- `output/<Company>_advanced_sentiment.json`

---

### 22.9 ملف wrapper: `src/advanced_sentiment.py`

هذا الملف ليس “تحليل” بحد ذاته، بل حل هندسي لسبب شائع:

- لا تريد أن تعتمد الـ API على اسم ملف يبدأ برقم مثل `07_advanced_sentiment.py`.

لذلك wrapper يقوم بـ:

- `import_module("07_advanced_sentiment")`
- ثم يعيد تصدير `run_advanced_sentiment_analysis` وغيره.

إذا فشل الاستيراد:

- يعطي stub يرجع error داخل JSON.

**تعليميًا:** هذا أسلوب “واجهة ثابتة Stable API for imports”.



---

## ملحق 23: Phase 8 — Alert Engine — (`src/08_alert_engine.py` + `src/alert_engine.py`) وربطه بـ `/api/alerts`

هذا هو الجزء الذي يجعل النظام **استباقيًا**: بدل أن المستخدم يفتح داشبورد ليبحث، النظام يقول له: “هناك شيء يحتاج انتباه”.

---

### 23.1 الفكرة العامة: Rules Engine

`AlertEngine` هو محرك قواعد (Rules Engine):

- كل قاعدة = دالة `check_*`
- إذا تحقق الشرط → يرجع alert
- إذا لم يتحقق → يرجع None

هذا نمط تصميم مهم:

- سهل الإضافة: تضيف قاعدة جديدة كدالة.
- سهل الاختبار: تختبر كل قاعدة وحدها.

---

### 23.2 نماذج البيانات: AlertSeverity / AlertCategory / BusinessAlert

داخل `src/08_alert_engine.py`:

- `AlertSeverity`: info/warning/critical
- `AlertCategory`: sales/customer/sentiment/forecast/…

ثم `BusinessAlert` dataclass يحتوي:

- id
- category + severity
- title + message
- recommendation (المهم: ماذا أفعل؟)
- metric_value/threshold (لشرح “لماذا ظهر التنبيه؟”)
- created_at تلقائي

**تعليميًا:** وجود threshold يجعل alert “قابل للتفسير” وليس مجرد رسالة.

---

### 23.3 Sales Alerts

أمثلة قواعد:

1) `check_revenue_decline(current_revenue, previous_revenue, threshold_pct)`
   - تحسب نسبة التغير
   - إذا الانخفاض أكبر من حد معين → warning/critical

2) `check_goal_progress(current_revenue, goal, days_elapsed, days_total)`
   - يقارن التقدم المتوقع مقابل الفعلي
   - يصنع فجوة gap

3) `check_sales_anomaly(daily_sales, std_threshold)`
   - يستخدم z-score على آخر قيمة
   - إذا كانت أقل من المتوسط بـ X انحراف معياري → alert

**تعليميًا:** z-score هنا هو:

$$ z = \frac{x - \mu}{\sigma} $$

حيث $x$ مبيعات اليوم، و$\mu$ المتوسط، و$\sigma$ الانحراف المعياري.

---

### 23.4 Customer Alerts (RFM)

قواعد مثل:

- `check_churning_customers(rfm_df, churn_segment="At Risk")`
  - تبحث عن عمود segment
  - تحسب نسبة “At Risk”
  - إذا النسبة كبيرة → alert

- `check_vip_customer_inactive(rfm_df, days_inactive=60)`
  - تبحث عن VIP segments مثل Champion/Loyal/VIP
  - إذا recency كبير → تنبيه معلوماتي

**تعليميًا:** هذه قواعد تربط التحليلات (RFM) بالقرار (حملة win-back).

---

### 23.5 Sentiment Alerts

قواعد مثل:

- `check_aspect_complaints(aspect_data)`
  - إذا جانب معين negative_pct > 40% وكان له mentions كافية → alert
  - ويستخدم `_get_aspect_action(aspect)` ليقترح action خاص.

---

### 23.6 Forecast Alerts

- `check_forecast_shortfall(forecast_df, target)`
  - يجمع forecast values
  - إذا أقل من الهدف بأكثر من 10% → alert

---

### 23.7 تجميع كل القواعد: run_all_checks()

`run_all_checks(data)` يستقبل dict فيه:

- sales metrics
- rfm_df
- sentiment_data
- forecast_df
- targets

ثم:

1) ينفذ قواعد متعددة.
2) يجمع alerts.
3) يرتبهم حسب severity (critical أولًا).
4) يرجع قائمة alerts كـ dicts عبر `asdict`.

---

### 23.8 نقطة الدخول run_alert_engine(company_name)

هذه الدالة تعمل “load then rules”:

1) تحاول تحميل RFM من `output/<Company>_rfm_segments.csv` (أو fallback).
2) تحاول تحميل advanced sentiment من `output/<Company>_advanced_sentiment.json`.
3) تحاول تحميل sales من مسارات محتملة.
4) تحاول تحميل forecast من `output/<Company>_forecast_prophet.csv` (أو fallback).
5) تنفذ `engine.run_all_checks(data)`.
6) تحفظ الناتج في:

- `output/<Company>_alerts.json`

**ملاحظة تعليمية:** ستجد أحيانًا “محاكاة” لقيم previous_revenue/goal داخل الملف لو لم يوجد مصدر تاريخي جاهز؛ هذه نقطة تدريبية وليست بنية إنتاجية كاملة.

---

### 23.9 ملف wrapper: `src/alert_engine.py`

تمامًا مثل advanced sentiment wrapper:

- يثبت اسم importable
- يصدر `run_alert_engine` و`AlertEngine` و`BusinessAlert`
- إن فشل الاستيراد → يرجع stub



---

## ملحق 24: Phase 9 — CLV (Customer Lifetime Value) — (`src/09_clv_calculation.py` + `src/clv_calculation.py`) وكيف يخرج Insights استراتيجية

CLV هو “قيمة العميل على مدى الحياة”.

فكر فيها: إذا لديك عميل قيمته المتوقعة 5000$، هل تتعامل معه مثل عميل قيمته 50$؟

---

### 24.1 ثلاث طرق لحساب CLV داخل الملف

#### (A) Historical CLV

`calculate_historical_clv(customer_transactions, customer_col, revenue_col)`:

- يجمع إجمالي الإيرادات لكل عميل.
- هذا ماضٍ (Backwards-looking).

#### (B) Average CLV

`calculate_average_clv(..., avg_lifespan_years=2.0)`:

يبني مؤشرات لكل عميل:

- total_revenue
- avg_order_value
- purchase_count
- first_purchase / last_purchase
- tenure_days/tenure_years
- purchase_frequency (مشتريات لكل سنة)

ثم:

$$ CLV = AOV \times Purchase\ Frequency \times Lifespan $$

#### (C) Predictive CLV (مبسطة)

`calculate_predictive_clv(customer_metrics, churn_rate=0.2, discount_rate=0.1, projection_years=3)`:

1) يحسب retention_rate = 1 - churn_rate
2) يحسب expected_annual_revenue
3) يجمع NPV لسنوات مستقبلية:

$$ CLV = \sum_{t=1}^{T} Revenue_t \times Retention^t \times \frac{1}{(1+discount)^t} $$

**تعليميًا:** هذا تبسيط لفكرة الخصم (Discounting) والبقاء (Survival).

---

### 24.2 التقسيم إلى شرائح CLV Segments

`assign_clv_segments(customer_metrics, clv_column='average_clv')` يستخدم quantiles:

- Platinum: أعلى 10%
- Gold: 70–90%
- Silver: 40–70%
- Bronze: أقل 40%

الفكرة: ليس كل العملاء متساوين في القيمة.

---

### 24.3 توليد Insights: generate_clv_insights()

يخرج:

- summary: إجمالي العملاء/إجمالي CLV/متوسط/وسيط…
- segments: كم عميل في كل شريحة وكم تمثل من القيمة
- recommendations:
  - مثال: “Platinum customers generate X% of CLV → VIP loyalty program”
  - مثال: “CAC يجب ألا يتجاوز 30% من CLV”

**تعليميًا:** هنا يتحول رقم CLV إلى سياسة تسويق وRetention.

---

### 24.4 run_clv_analysis(company_name)

هذه نقطة الدخول:

1) تحاول إيجاد ملف مبيعات من مسارات متعددة.
2) تحاول حل أسماء الأعمدة عبر candidates بسيطة (CustomerID/Revenue/Date).
3) إذا لا يوجد customer id → ترجع error لأن CLV لا يعمل بدون عميل.
4) تحسب CLV.
5) تدمج مع RFM إن وجد (`output/*rfm_segments.csv`) لتوسيع التحليل.
6) تحفظ:

- CSV: `output/<Company>_clv_analysis.csv`
- JSON: `output/<Company>_clv_insights.json`

---

### 24.5 ملف wrapper: `src/clv_calculation.py`

نفس الفكرة:

- واجهة import ثابتة للـ API
- إعادة تصدير دوال المرحلة 9
- stub عند الفشل



---

## ملحق 25: Backend v2 (تفكيك الملفات الداعمة) — (`backend/auth.py`, `backend/routes/auth_routes.py`, `backend/database/*`, `backend/responses.py`, `backend/background_tasks.py`, `backend/init_db.py`)

ملحق 16 أعطى نظرة عامة عن Backend v2. هذا الملحق يكمل بتفكيك الملفات الداعمة “واحدة واحدة” بشكل تعليمي.

---

### 25.1 `backend/responses.py` — لماذا Standard Response؟

الفكرة: بدل أن كل endpoint يرجع شكل مختلف، نثبت هيكلًا موحدًا:

- `APIResponse`:
  - `success: bool`
  - `data`
  - `message`
  - `errors`
  - `metadata`
  - `timestamp`

وهناك `PaginatedResponse` للـ lists.

ثم دوال builder:

- `success_response(data, message, metadata)`
- `error_response(error, detail, error_code, status_code)`

**تعليميًا:** هذا يقلل فوضى الـ frontend: يعلم أن هناك دومًا `data` أو `error`.

---

### 25.2 `backend/database/connection.py` — Engine + Session + Dependency

المسؤوليات:

1) تحديد DB path داخل `data/sales_intelligence.db`.
2) إنشاء SQLAlchemy engine.
3) إنشاء `SessionLocal`.
4) توفير Dependency `get_db()` للاستخدام داخل FastAPI.

**لماذا StaticPool في SQLite؟**

لتبسيط سلوك SQLite في بيئة متعددة threads أثناء التطوير.

---

### 25.3 `backend/database/models.py` — Models و RBAC

الملف يعرف:

- `UserRole`: admin/analyst/viewer
- `User`:
  - hash password
  - verify password
  - مرتبط بـ Company
- `Company`:
  - multi-tenant isolation
  - `data_directory` لتحديد مجلد الشركة في data
- جداول نتائج ML:
  - `ForecastResult`
  - `RFMResult`
  - `SentimentResult`
- `ModelPerformanceLog` لمراقبة الأداء.

**تعليميًا:** هنا ترى الفرق بين “ML outputs على ملفات” و “ML outputs داخل DB” كـ cache تاريخي.

---

### 25.4 `backend/auth.py` — JWT + Dependencies

المفاهيم:

1) `create_access_token()` ينشئ JWT ويضع claim مثل:
   - `sub` (عادة الإيميل)
   - `role`
   - `company_id`
   - `exp` وقت انتهاء

2) `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/form")`:
   - هذا يجعل Swagger UI يعرف كيف يطلب token.

3) `get_current_user()`:
   - يقرأ Authorization header
   - يفك token
   - يجلب user من DB

4) `require_role([...])`:
   - Factory يرجع Dependency يفحص الدور.

5) `check_company_access(user, company_id)`:
   - يمنع الوصول لبيانات شركة مختلفة إلا للأدمن.

**تعليميًا:** هذا قلب الـ RBAC + Multi-tenant.

---

### 25.5 `backend/routes/auth_routes.py` — Endpoints Authentication

Endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/login/form` (للـ Swagger)
- `GET /api/auth/me`
- `GET /api/auth/verify`

ويستخدم models Pydantic مثل `UserRegister`, `UserResponse`, `TokenResponse`.

**تعليميًا:** وجود `login/form` يشرح لماذا tokenUrl في OAuth2PasswordBearer مهم.

---

### 25.6 `backend/init_db.py` — Seed Data

هذا سكربت تعليمي لإنشاء:

- شركات demo
- Users demo بأدوار مختلفة

ويطبع credentials للتجربة.

**تعليميًا:** هذا ليس جزءًا من تشغيل الإنتاج، لكنه مفيد للتعلم.

---

### 25.7 `backend/background_tasks.py` — لماذا Background Tasks؟

الفكرة: بعض عمليات ML قد تأخذ 10–60 ثانية.

لو نفذتها داخل request مباشرة:

- سيظل المستخدم ينتظر
- وقد يحصل timeout

الحل: background task.

داخل الملف:

1) `_load_module_from_path()`:
   - يستورد سكربت من `src/` مباشرة عبر path.
   - هذا يسمح باستعمال ملفات مثل `03_forecasting_prophet.py` بدون تحويلها لحزمة.

2) `TASK_REGISTRY`:
   - سجل in-memory لتتبع status/progress.
   - (تعليميًا: في الإنتاج تستخدم Redis/DB.)

3) `run_forecast_async()`:
   - يشغل forecasting
   - ثم يحفظ النتائج في جدول `ForecastResult`.

4) `run_sentiment_async()`:
   - يشغل `06_sentiment_arabic.py`
   - ثم يحفظ النتائج في جدول `SentimentResult`.

5) دوال مساعدة:
   - `create_task_id()`
   - `get_task_status()`
   - `cleanup_old_tasks()`

**تعليميًا:** هذا يشرح تصميم “Async job + status polling”.



---

## ملحق 26: الاختبارات Tests — (`tests/*`) وما الذي تثبته؟

الهدف من tests هنا ليس الوصول إلى تغطية كاملة، بل:

- التأكد أن الـ API لا يرجع 404/500 بشكل مفاجئ.
- التأكد أن منطق ML الأساسي (بشكل مبسط) يعمل.

---

### 26.1 `tests/conftest.py`

هذا الملف يفعل شيئين مهمين:

1) يضيف مسارات المشروع إلى `sys.path` حتى imports تعمل أثناء الاختبارات.
2) يعرف fixtures جاهزة:

- `sample_sales_data`: DataFrame صغير للاختبار
- `sample_review_data`: DataFrame صغير لمراجعات

**تعليميًا:** fixture = بيانات اختبار جاهزة تُحقن في tests.

---

### 26.2 `tests/test_api.py`

يستخدم `TestClient` من FastAPI لتجربة endpoints من غير تشغيل سيرفر حقيقي.

نقاط تعليمية واضحة:

- بعض endpoints قد ترجع 503 إذا البيانات لم تُحمَّل (والاختبار يسمح بذلك).
- التحقق من validation:
  - مثال: تاريخ غير صحيح → 422.

وهناك test parametrized يمر على endpoints للتأكد أنها ليست 404 ولا 500.

---

### 26.3 `tests/test_ml_scripts.py`

هذه اختبارات “منطقية” وليست تدريب نماذج كاملة:

- date parsing
- monthly grouping
- توليد future periods
- RFM recency/frequency
- sentiment polarity عبر TextBlob
- cleaning (duplicates + missing values)

**تعليميًا:** الهدف تقليل احتمالية كسر المنطق الأساسي عند تعديل ملفات ML.

---

### 26.4 `tests/README.md`

يوضح أوامر التشغيل:

- `pytest tests/ -v`
- `pytest tests/test_api.py -v`
- `pytest tests/ --cov=backend --cov=src --cov-report=html`



---

## ملحق 27: Frontend (تفكيك المسارات الحرجة) — (`frontend/store/*` + `frontend/components/AlertsPanel.tsx` + `frontend/components/SentimentInsights.tsx` + `frontend/pages/Dashboard.tsx`)

ملحق 17 شرح الواجهة عمومًا. هذا الملحق يركز على “الأسلاك الأساسية” التي تربط الواجهة بالـ API وبفكرة multi-tenant.

---

### 27.1 `frontend/App.tsx` — منطق الصفحات

التطبيق بسيط جدًا تعليميًا:

- إذا غير authenticated → يعرض `AuthPage`.
- إذا authenticated → يعرض `Layout` وفي داخله صفحة حسب `currentPage`.

هذا ليس React Router؛ هو state-based navigation.

---

### 27.2 `frontend/store/AuthContext.tsx` — JWT + حفظ الشركة

المسؤوليات:

1) `login()`:
   - يرسل `POST /api/auth/login` إلى `API_BASE_URL`.
   - إذا نجح، يخزن:
     - `auth_token`
     - `auth_user`
     - وأيضًا `company` (مهم لأن بعض components تستخدمه في header `X-Company-ID`).

2) `loadSavedAuth()`:
   - عند بداية التطبيق، يقرأ token/user من localStorage.
   - يختبر token عبر `GET /api/auth/verify`.

3) `useAuthFetch()`:
   - helper يضيف `Authorization: Bearer <token>` تلقائيًا.

**تعليميًا:** هذا هو “Client-side session management” باستخدام localStorage.

---

### 27.3 `frontend/store/DataContext.tsx` — تحميل البيانات من endpoints

`fetchData()` يوضح أسلوب مهم:

- لا يعتمد على cache محلي لبيانات التحليلات.
- يتعامل مع 204: إذا لا توجد بيانات → يضع state فارغ بدل أن يرمي error.

ويستدعي endpoints مثل:

- `/api/kpis`
- `/api/raw-data`
- `/api/monthly-sales`
- `/api/recommendations`
- `/api/segmentation`

ويضيف Authorization header من token.

**ملاحظة تعليمية مهمة:**

ستلاحظ أن بعض components تستخدم `API_BASE_URL` (absolute) وبعضها يستخدم `fetch('/api/...')` (relative).
هذا يربط بفكرة Vite proxy أثناء التطوير.

---

### 27.4 `frontend/components/AlertsPanel.tsx` — لماذا ظهر خطأ “Unexpected token '<'”؟

هذا component يطلب:

- `GET /api/alerts`

ويضيف header:

- `X-Company-ID: localStorage.company`

إذا لم يكن هناك proxy مضبوط، الطلب قد يذهب لسيرفر الواجهة ويرجع HTML (صفحة Vite)، فيحاول `response.json()` تفسير HTML كـ JSON، فتظهر رسالة:

- `Unexpected token '<'`

وهذا بالضبط ما شرحناه في بداية المحادثة.

---

### 27.5 `frontend/components/SentimentInsights.tsx` — ربط advanced sentiment

هذا component يطلب:

- `GET /api/advanced-sentiment`

ويعرض:

- نسبة الإيجابي
- نسبة المراجعات العربية
- breakdown لكل aspect مع progress bars
- Alerts حول الجوانب السيئة

**تعليميًا:** هذا هو “عرض Insights” وليس مجرد charts.

---

### 27.6 `frontend/pages/Dashboard.tsx` — دمج الذكاء داخل صفحة واحدة

تلاحظ في Dashboard:

- يعرض `AlertsPanel` (ذكاء استباقي)
- ثم KPI cards
- ثم charts
- ثم `SentimentInsights` (ذكاء نصي عربي)

هذا يلخص فلسفة المشروع:

1) بيانات رقمية (KPIs/Forecast)
2) بيانات سلوكية (Segments/Recommendations)
3) بيانات نصية (Sentiment)
4) قرارات (Alerts)



---

## ملحق 28: شرح ملف `backend/main_enhanced.py` سطرًا بسطر (Backend v2 Main) — (Part 1)

هذا الملحق هو “تفكيك تدريسي” لملف Backend v2 الأساسي.

الفكرة: بدل ما نقول “فيه Auth و DB و Background Tasks”، سنمشي على الملف خطوة خطوة لتفهم:

- لماذا وضعوا `sys.path`؟
- كيف جهزوا FastAPI + CORS؟
- كيف صمموا request/response models؟
- كيف تُحمى endpoints؟
- كيف يتم إطلاق مهام ML في الخلفية؟

> ملاحظة: هذا شرح تعليمي داخل الملف فقط. لا نغيّر كود.

---

### Part 1 — رأس الملف + Imports + إعداد التطبيق

#### 1) Docstring في الأعلى

الأسطر الأولى تشرح أن هذا:

- FastAPI backend v2.0
- فيه تحسينات: JWT + SQLAlchemy + Background Tasks + Explainability + Monitoring

وجود هذا الملخص مهم لأن:

- أي مطور جديد يفهم “وظيفة الملف” من أول دقيقة.

#### 2) Imports القياسية

سترى imports مثل:

- `sys`, `logging`, `os`, `Path`
- `typing` (Optional/List/Dict/Any)
- `datetime`

هذه لدعم:

- تسجيل logs
- قراءة env vars
- التعامل مع paths بشكل آمن
- نمذجة أنواع البيانات

#### 3) Imports من مكتبات المشروع

سترى:

- `pandas as pd` لأن بعض endpoints تحول JSON↔DataFrame لتوليد explainability.
- `fastapi` و `CORSMiddleware`.
- `sqlalchemy.orm.Session` لاستخدام DB session داخل endpoints.

#### 4) حركة مهمة: sys.path.insert

في الكود:

- `BASE_DIR = Path(__file__).resolve().parent.parent`
- ثم: `sys.path.insert(0, str(BASE_DIR / "src"))`

**لماذا؟**

لأن ملف `explainability.py` وملفات أخرى موجودة في مجلد `src/` (وهو ليس package رسمي).
في بايثون، الاستيراد يعتمد على `sys.path`.
فهم يحلونها بسرعة لتعمل imports مثل:

- `from explainability import explain_forecast`

**تعليميًا:**

- هذا حل عملي للتجارب.
- في مشاريع كبيرة، الأفضل تحويل `src/` إلى package أو تثبيت المشروع كـ module.

#### 5) Imports من داخل backend v2

لاحظ وجود imports أساسية:

- `get_db` + `init_db` من `backend.database.connection`
- Models مثل `User`, `Company`, `ForecastResult`…
- Auth deps مثل `require_admin`, `require_analyst`, `check_company_access`
- `auth_router` (Routes للـ auth)
- `responses` (قالب رد موحّد)
- `background_tasks` (تشغيل forecasting/sentiment)

**فكرة مهمة جدًا:**

`main_enhanced.py` هنا ليس فيه ML logic نفسه.
هو “Orchestrator” يجمع:

- Security
- DB
- API endpoints
- تشغيل ML كوحدات مستقلة

#### 6) Logging setup

يحدد:

- `LOGS_DIR = BASE_DIR / "logs"`
- ثم `logging.basicConfig(...)` بحيث:
   - يكتب إلى ملف `logs/api_enhanced.log`
   - ويطبع أيضًا على console

**تعليميًا:** وجود log file يجعل debugging أسهل لأنك ترى ما حدث حتى لو terminal ضاع.

#### 7) إنشاء app = FastAPI(...)

في:

- `title`, `description`, `version`
- `docs_url` و `redoc_url`

**تعليميًا:** هذه metadata تظهر في Swagger UI.

#### 8) CORS Configuration

`ALLOWED_ORIGINS` تُقرأ من env var `CORS_ORIGINS` أو default.

ثم `app.add_middleware(CORSMiddleware, ...)` يسمح:

- origins محددة
- ويسمح أيضًا عبر `allow_origin_regex` لأي localhost port.

**لماذا هذا مهم؟**

لأن الواجهة تعمل على ports مختلفة (Vite).
بدون CORS ستواجه خطأ في المتصفح يمنع request.

#### 9) include_router(auth_router)

هذا يعني أن endpoints داخل `backend/routes/auth_routes.py` تم تركيبها داخل التطبيق.

ميزة router:

- يجعل المشروع modular
- لا تكتب كل endpoints في ملف واحد عملاق

#### 10) Startup event

`@app.on_event("startup")` يقوم بـ:

- `init_sqlalchemy_db()`

أي: إنشاء الجداول إن لم تكن موجودة.

**تعليميًا:** هذا “تهيئة” قبل استقبال requests.

> انتهى Part 1: الآن التطبيق جاهز (FastAPI + CORS + Router + DB init).



---

## ملحق 28: شرح `backend/main_enhanced.py` سطرًا بسطر — (Part 2)

هذا الجزء يشرح نماذج الطلب/الرد (Pydantic) ثم أهم endpoints الخاصة بالتحليلات.

---

### Part 2 — Request/Response Models + Forecast/Sentiment Endpoints

#### 1) لماذا توجد Models مثل ForecastRequest/SentimentRequest؟

في FastAPI، عندما تعرف model بـ Pydantic:

- يحصل Validation تلقائي
- ويتولد Documentation تلقائي في Swagger
- وتضمن أن client يرسل JSON بشكل صحيح

مثال:

- `ForecastRequest` فيه `periods` و `use_prophet`.
- `SentimentRequest` فيه `use_arabic_model`.

#### 2) TaskStatusResponse: نموذج مهم لأسلوب “Poll status”

لأن forecast/sentiment تعمل في الخلفية، تحتاج endpoint يعيد:

- status
- progress
- result
- error

وهذا بالضبط ما يمثله `TaskStatusResponse`.

#### 3) Public endpoints: `/` و `/health`

- `/` يعيد معلومات عامة وإصدار v2.
- `/health` يعيد health check مع timestamp.

**تعليميًا:** وجود health endpoint مفيد للـ monitoring.

#### 4) GET `/api/companies`

هذا endpoint محمي بـ:

- `current_user: User = Depends(require_analyst)`

يعني: لا يمكن الوصول إلا لمستخدم role مناسب.

ثم:

- إذا ADMIN → يرجع كل الشركات
- غير ذلك → يرجع فقط شركة المستخدم

هذه Multi-tenant فكرة “الحد الأدنى من البيانات”.

#### 5) POST `/api/companies/{company_id}/forecast`

هنا أهم pattern في v2:

1) يتحقق من وجود الشركة
2) `check_company_access` يمنع الوصول لشركة غير شركتك
3) ينشئ `task_id`
4) يضيف مهمة إلى `background_tasks.add_task(run_forecast_async, ...)`
5) يرجع فورًا `ForecastResponse` فيه task_id

**تعليميًا:**

هذا يجعل API سريع: لا ينتظر ML ينتهي.

#### 6) GET `/api/companies/{company_id}/forecast/latest`

هذا endpoint لا يشغل ML؛ بل يقرأ آخر نتيجة محفوظة في DB:

- `ForecastResult` بأحدث `created_at`.

ثم يحاول توليد explainability:

- يستورد `explain_forecast`
- يحول `forecast.forecast_data` إلى DataFrame
- يمرر trend/seasonality إن وجدت

لو فشل الشرح:

- لا يكسر endpoint؛ فقط يجعل `explanation = None`.

**تعليميًا:** هذا يسمى graceful degradation.

#### 7) POST `/api/companies/{company_id}/sentiment`

نفس فكرة forecast:

- يتحقق من company
- check_company_access
- ينشئ task_id
- يشغل `run_sentiment_async` في الخلفية
- يرجع رسالة “تحليل المشاعر بدأ”

#### 8) GET `/api/companies/{company_id}/sentiment/summary`

بدل قراءة ملف CSV، هنا يقرأ من DB:

- يجلب كل `SentimentResult` للشركة
- يحسب:
   - total
   - counts (Positive/Neutral/Negative)
   - average confidence
   - percentages

**تعليميًا:** هذا يوضح كيف تحول “تحليل” إلى “ملخص” يصلح للداشبورد.

> انتهى Part 2: فهمت كيف يطلق backend مهام ML ويرجع status/summary.



---

## ملحق 28: شرح `backend/main_enhanced.py` سطرًا بسطر — (Part 3)

هذا الجزء يغطي explainability endpoints + tasks status + admin monitoring + error handlers.

---

### Part 3 — Explainability + Admin Monitoring + Error Handling

#### 1) Explainability endpoint: POST `/api/explain/rfm`

هذا endpoint:

- يأخذ `customer_id` داخل body (Pydantic model).
- يأخذ `company_id` كـ query parameter.
- محمي بـ `require_analyst`.

ثم:

1) يبحث عن `RFMResult` للعميل داخل DB.
2) إذا لم يجد → 404.
3) إذا وجد → يستدعي `explainability.explain_rfm_segment(...)`.

**تعليميًا:**

الـ explainability هنا ليست “نموذج ML جديد”، بل “تفسير” للنتيجة الموجودة.

#### 2) Explainability endpoint: POST `/api/explain/recommendation`

هذا endpoint يقدم شرح لتوصية (IF/THEN) لكنه يستخدم placeholder metrics:

- support/confidence/lift قيم ثابتة للتجربة.

**تعليميًا:** هذا endpoint يوضح الشكل النهائي، لكن في نظام إنتاجي يجب أن يقرأ rule metrics من DB أو ملف توصيات.

#### 3) Task status endpoint: GET `/api/tasks/{task_id}`

هذا هو endpoint الذي يجعل background tasks قابلة للاستخدام من الواجهة:

- يبحث عن `task_info = get_task_status(task_id)` من registry.
- إذا لم يجد → 404.
- إذا وجد → يرجع TaskStatusResponse.

**تعليميًا:** هذا هو “Polling” (الواجهة تسأل كل فترة: هل انتهيت؟).

#### 4) Admin-only monitoring endpoints

1) GET `/api/admin/model-health/{company_id}`
    - محمي بـ `require_admin`.
    - يستدعي `ml_lifecycle.monitor_model.get_model_health_summary`.

2) POST `/api/admin/check-drift/{company_id}`
    - يستدعي `detect_data_drift(company.data_directory)`.
    - ويعيد النتائج.

3) POST `/api/admin/retrain/{company_id}`
    - يستدعي `should_retrain_model(...)`.
    - إذا `should_retrain=True` يرجع “triggered” مع task_id.

**تعليميًا مهم:**

هنا نرى كيف ينتقل المشروع من “ML scripts” إلى “MLOps decisions” داخل API.

#### 5) Error Handlers

يوجد:

- handler لـ `HTTPException` يرجع شكل موحّد فيه:
   - success: False
   - error: detail
   - status_code
   - timestamp

- handler عام لأي `Exception`:
   - يكتب log بـ `exc_info=True`
   - ويرجع 500 برسالة عامة

**تعليميًا:**

إخفاء تفاصيل exception عن client أفضل أمنيًا.
وتسجيل التفاصيل في logs أفضل للمطور.

#### 6) تشغيل مباشر إذا كان الملف main

في النهاية:

- `uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)`

لكن في التشغيل الحقيقي غالبًا تستخدم الأمر:

- `uvicorn backend.main_enhanced:app --reload`

> انتهى ملحق 28: الآن تقدر تقرأ ملف `backend/main_enhanced.py` وتفهم “لماذا كل سطر موجود”.









