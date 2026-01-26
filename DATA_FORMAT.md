# Data Format Guide | دليل تنسيق البيانات

## Required File Columns | الأعمدة المطلوبة

### Sales Data (sales.csv) | بيانات المبيعات

يجب أن يحتوي ملف CSV على الأعمدة التالية (يمكن استخدام أسماء بديلة):

| Column Name | Aliases | Type | Example | Description |
|---|---|---|---|---|
| **id** | `OrderID`, `TransactionID`, `Order_ID` | String/Integer | 1001 | معرف الطلب الفريد |
| **date** | `OrderDate`, `Order_Date`, `TransactionDate` | Date (YYYY-MM-DD) | 2024-01-05 | تاريخ الطلب |
| **amount** | `TotalPrice`, `Total_Price`, `Price`, `OrderValue` | Float/Decimal | 1200.00 | المبلغ الإجمالي |
| **product** | `ProductName`, `Product_Name`, `Item` | String | Laptop | اسم المنتج |
| **city** | `Location`, `Region`, `City` | String | Algiers | المدينة |

### Optional Columns | أعمدة اختيارية

```
CustomerID, CustomerName, Quantity, UnitPrice, Month, Year, etc.
```

---

## CSV Format Example | مثال على التنسيق

```csv
OrderID,OrderDate,TotalPrice,Product,City,Quantity,UnitPrice
1001,2024-01-05,1200,Laptop,Algiers,1,1200
1002,2024-01-07,40,Mouse,Oran,2,20
1003,2024-02-10,50,Keyboard,Constantine,1,50
1004,2024-02-15,300,Monitor,Algiers,1,300
1005,2024-03-01,1200,Laptop,Setif,1,1200
1006,2024-03-05,160,Headphones,Blida,2,80
```

---

## Common Issues & Solutions | المشاكل الشائعة والحلول

### ❌ Issue: "Missing required columns"
**Solution**: تأكد من أن ملفك يحتوي على جميع الأعمدة المطلوبة الخمسة (id, date, amount, product, city)

### ❌ Issue: "Invalid date format"
**Solution**: استخدم صيغة التاريخ: `YYYY-MM-DD` (2024-01-05)

### ❌ Issue: "Empty file or no records"
**Solution**: تأكد من أن الملف يحتوي على رأس الأعمدة + بيانات واحد على الأقل

### ✅ Column name flexibility
النظام يدعم أسماء أعمدة مختلفة تلقائياً:
- `id` = `orderid` = `order_id` = `transactionid`
- `date` = `orderdate` = `order_date`
- `amount` = `totalprice` = `total_price` = `price`
- `product` = `productname` = `item`
- `city` = `location` = `region`

---

## ✅ Valid File Examples

### Example 1: Minimal (Required columns only)
```csv
id,date,amount,product,city
1,2024-01-05,1200,Laptop,Algiers
2,2024-01-07,40,Mouse,Oran
3,2024-02-10,50,Keyboard,Constantine
```

### Example 2: With additional details
```csv
OrderID,CustomerID,Product,OrderDate,TotalPrice,City,Quantity
1001,1,Laptop,2024-01-05,1200,Algiers,1
1002,2,Mouse,2024-01-07,40,Oran,2
1003,3,Keyboard,2024-02-10,50,Constantine,1
```

### Example 3: Using different aliases
```csv
TransactionID,Date,OrderValue,Item,Location
T001,2024-01-05,1200,Laptop,Algiers
T002,2024-01-07,40,Mouse,Oran
T003,2024-02-10,50,Keyboard,Constantine
```

---

## 📥 How to Use

1. Prepare your CSV file with required columns
2. Upload via the Data Upload page
3. System will automatically validate and process
4. Dashboard updates with new insights

---

**Last Updated**: January 23, 2026
