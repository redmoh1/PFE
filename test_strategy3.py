import pandas as pd
from pathlib import Path

# Create test data for Strategy 3 with OrderDate but NO CustomerID
test_data = {
    'OrderDate': ['2024-01-15', '2024-01-15', '2024-01-20', '2024-01-20'],
    'Product': ['P101', 'P102', 'P101', 'P103'],
    'TotalPrice': [150.00, 200.00, 120.00, 180.00],
    'City': ['NYC', 'NYC', 'LA', 'LA']
}

df = pd.DataFrame(test_data)
data_dir = Path('data')
df.to_csv(data_dir / 'sales.csv', index=False)

print('Created test data for Strategy 3 (Fallback):')
print('- OrderDate present')
print('- CustomerID MISSING')
print('- Should generate incremental OrderIDs (ORD_000001, etc.)')
print(f'\nTest Data ({len(df)} rows):')
print(df.to_string())
