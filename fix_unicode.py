"""Quick fix script: Remove Unicode symbols and recreate test data"""
import pandas as pd
from pathlib import Path
import re

# Fix Unicode symbols in src/01_eda.py
eda_file = Path('src/01_eda.py')
content = eda_file.read_text(encoding='utf-8')

# Replace all Unicode symbols with ASCII
replacements = {
    '\u2713': '[OK]',      # ✓
    '\u26a0': '[WARN]',    # ⚠
    '\u2298': '[SKIP]',    # ⊘
    '\u2717': '[FAIL]',    # ✗
}

for unicode_char, ascii_replacement in replacements.items():
    content = content.replace(unicode_char, ascii_replacement)

eda_file.write_text(content, encoding='utf-8')
print('Fixed Unicode symbols in src/01_eda.py')

# Recreate test sales data with CustomerID and OrderDate
data_dir = Path('data')
test_data = {
    'CustomerID': ['C001', 'C001', 'C002', 'C002', 'C003', 'C001', 'C003', 'C002'],
    'OrderDate': ['2024-01-15', '2024-01-15', '2024-01-20', '2024-01-20', 
                  '2024-02-01', '2024-02-01', '2024-02-05', '2024-02-10'],
    'Product': ['P101', 'P102', 'P101', 'P103', 'P102', 'P104', 'P101', 'P105'],
    'TotalPrice': [150.00, 200.00, 120.00, 180.00, 250.00, 175.00, 200.00, 95.00],
    'City': ['NYC', 'NYC', 'LA', 'LA', 'Chicago', 'NYC', 'Chicago', 'LA']
}

df = pd.DataFrame(test_data)
df.to_csv(data_dir / 'sales.csv', index=False)

print(f'Recreated test sales.csv with {len(df)} rows')
print('Strategy: CustomerID + OrderDate (Strategy 2)')
print('\nTest Data:')
print(df)
