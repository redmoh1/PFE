# 🎬 دليل عملي - كيفية رفع ملف CSV

## الخطوة الأولى: تحضير ملف CSV

### ✅ الأعمدة المطلوبة (5 أعمدة)

يجب أن يحتوي ملفك على **واحد من هذه الأسماء** لكل عمود:

```
[id]              [date]              [amount]           [product]         [city]
├─ id             ├─ date             ├─ amount          ├─ product        ├─ city
├─ orderid        ├─ orderdate        ├─ totalprice      ├─ productname    ├─ location
├─ transactionid  ├─ order_date       ├─ total_price     ├─ product_name   ├─ region
└─ order_id       ├─ transactiondate  ├─ price           └─ item           
                  └─ order_date       └─ ordervalue
```

---

## مثال 1: الطريقة الأساسية

### ملف `my_sales.csv`

```csv
id,date,amount,product,city
1,2024-01-05,1200,Laptop,Algiers
2,2024-01-07,40,Mouse,Oran
3,2024-02-10,50,Keyboard,Constantine
4,2024-02-15,300,Monitor,Algiers
```

### 📤 كيفية الرفع
1. اذهب إلى Dashboard (http://localhost:5173)
2. اختر **Data Upload** من القائمة الجانبية
3. اضغط **Select CSV File**
4. اختر ملفك `my_sales.csv`
5. اضغط **Upload & Process**
6. ✅ انتظر: **Pipeline Complete!**

---

## مثال 2: أسماء أعمدة مختلفة

### ملف `sales_data.csv`

```csv
OrderID,CustomerID,Product,OrderDate,TotalPrice,Location,Quantity
1001,C001,Laptop,2024-01-05,1200,Algiers,1
1002,C002,Mouse,2024-01-07,40,Oran,2
1003,C003,Keyboard,2024-02-10,50,Constantine,1
```

### 🔍 الخريطة التلقائية
```
OrderID        → id
OrderDate      → date
TotalPrice     → amount
Product        → product
Location       → city
```

### 📤 النتيجة
✅ يعمل بدون مشاكل! النظام يتعرف على الأعمدة تلقائياً

---

## مثال 3: ملف من Excel محفوظ كـ CSV

### الخطوات:
1. افتح ملفك في Excel
2. **File → Save As**
3. اختر نوع الملف: **CSV UTF-8 (.csv)**
4. احفظ الملف
5. رفعه عبر Data Upload ✅

### ⚠️ انتبه:
- الأعمدة يجب أن تحتوي على البيانات الصحيحة
- لا تترك خلايا فارغة في رؤوس الأعمدة
- تأكد من أن التواريخ بصيغة `YYYY-MM-DD`

---

## مثال 4: استخدام البيانات الموجودة بالفعل

### ملفات جاهزة في المشروع:

```powershell
# كل هذه الملفات جاهزة للرفع مباشرة ✅

data/sales.csv              # 8 records
data/sample_sales.csv       # 20 record (موصى به)
data/cleaned_dataset.csv    # 8 records
data/minimal_example.csv    # 10 record (الأبسط)
```

### كيفية الاستخدام:
1. اذهب إلى **Data Upload**
2. اختر أي من الملفات أعلاه
3. انتظر ✅ **Pipeline Complete!**

---

## 🔧 إنشاء ملف CSV من الصفر

### باستخدام Notepad/VS Code:

```csv
id,date,amount,product,city
1,2024-01-01,100,Item A,City A
2,2024-01-02,200,Item B,City B
3,2024-01-03,300,Item C,City C
```

1. انسخ النص أعلاه
2. افتح Notepad
3. الصق النص
4. **File → Save As → Save as type: All Files**
5. اكتب اسم الملف: `my_data.csv`
6. احفظ على سطح المكتب
7. رفع عبر Dashboard ✅

---

## 🛠️ استكشاف الأخطاء

### ❌ خطأ: "Missing required columns"

**الأسباب الممكنة:**

1. **أعمدة غير صحيحة**
   ```csv
   ❌ wrong: name, date, total, goods, town
   ✅ right: product, date, amount, product, city
   ```

2. **أعمدة ناقصة**
   ```csv
   ❌ wrong: id, date, amount, product (بدون city)
   ✅ right: id, date, amount, product, city (5 أعمدة)
   ```

3. **مسافات في الأسماء**
   ```csv
   ❌ wrong: " id ", "date ", "amount"
   ✅ right: id, date, amount
   ```

### الحل:
```powershell
# اختبر ملفك
python test_data_upload.py

# إذا أظهر FAILED، عدل الأعمدة
```

---

## ✅ قائمة التحقق قبل الرفع

قبل رفع ملفك، تأكد من:

```
☑️ هل الملف بصيغة CSV؟
☑️ هل يحتوي على 5 أعمدة (id, date, amount, product, city)؟
☑️ هل أسماء الأعمدة صحيحة (من القائمة المدعومة)؟
☑️ هل التواريخ بصيغة YYYY-MM-DD؟
☑️ هل المبالغ أرقام (مثل 100 أو 100.50)؟
☑️ هل يحتوي على بيانات (أكثر من مجرد رؤوس الأعمدة)؟
☑️ هل لا توجد أسطر فارغة في المنتصف؟
```

---

## 📊 نموذج CSV جاهز للنسخ

### النسخة الأساسية (الحد الأدنى):
```csv
id,date,amount,product,city
1,2024-01-05,1200,Laptop,Algiers
2,2024-01-07,40,Mouse,Oran
3,2024-02-10,50,Keyboard,Constantine
4,2024-02-15,300,Monitor,Algiers
5,2024-03-01,1200,Laptop,Setif
```

### النسخة الموسعة (مع معلومات إضافية):
```csv
OrderID,CustomerID,ProductID,Product,Quantity,UnitPrice,TotalPrice,OrderDate,City
1001,C001,P001,Laptop,1,1200,1200,2024-01-05,Algiers
1002,C002,P002,Mouse,2,20,40,2024-01-07,Oran
1003,C003,P003,Keyboard,1,50,50,2024-02-10,Constantine
1004,C001,P004,Monitor,1,300,300,2024-02-15,Algiers
```

---

## 🚀 الخطوات الكاملة

### 1. تشغيل المشروع
```powershell
# Terminal 1
python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

### 2. افتح Dashboard
```
http://localhost:5173
```

### 3. اذهب إلى Data Upload
```
القائمة اليسرى → Data Upload
```

### 4. اختر ملف CSV
```
اختر ملفك أو استخدم أحد النماذج الجاهزة
```

### 5. اضغط Upload & Process
```
انتظر الرسالة: ✅ Pipeline Complete!
```

### 6. شاهد النتائج
```
عد إلى Dashboard لرؤية الرسوم البيانية والمقاييس
```

---

## 💡 نصائح

✅ **استخدم البيانات النموذجية أولاً**
```
data/sample_sales.csv - الأفضل للاختبار
```

✅ **اختبر ملفك قبل الرفع**
```powershell
python test_data_upload.py
```

✅ **استخدم أسماء أعمدة واضحة**
```
✅ جيد: OrderID, OrderDate, TotalPrice, Product, City
❌ سيء: O, D, T, P, C
```

✅ **احفظ نسخة احتياطية**
```
احتفظ بنسخة من ملفك الأصلي
```

---

## 📞 الدعم

| المشكلة | الحل |
|--------|------|
| لا أعرف الأعمدة | اقرأ [DATA_FORMAT.md](./DATA_FORMAT.md) |
| ملفي تم رفضه | اختبر: `python test_data_upload.py` |
| أريد أمثلة | استخدم: `data/sample_sales.csv` |
| مشاكل تقنية | اقرأ [QUICK_START.md](./QUICK_START.md) |

---

**الآن أنت جاهز! ارفع ملفك! 🚀**

---

**التاريخ:** 23 يناير 2026
