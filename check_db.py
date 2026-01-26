import sqlite3
from pathlib import Path

db_path = Path('data/datasets.db')
conn = sqlite3.connect(db_path)

# Get active sales dataset
cursor = conn.execute("""
    SELECT * FROM datasets 
    WHERE is_active=1 AND dataset_type='sales' 
    ORDER BY uploaded_at DESC LIMIT 1
""")
row = cursor.fetchone()
print('Active sales dataset:', row)

if row:
    file_path = row[4]  # file_path column
    print(f'\nFile path: {file_path}')
    print(f'File exists: {Path(file_path).exists()}')
    
    # Check file content
    if Path(file_path).exists():
        import pandas as pd
        df = pd.read_csv(file_path)
        print(f'Columns: {df.columns.tolist()}')
        print(f'Rows: {len(df)}')
        if 'Price' in df.columns:
            print(f'Price sum: {df["Price"].sum()}')
        if 'TotalPrice' in df.columns:
            print(f'TotalPrice sum: {df["TotalPrice"].sum()}')

conn.close()
