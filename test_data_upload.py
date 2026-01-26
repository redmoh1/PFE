#!/usr/bin/env python
"""
Test script to validate data upload functionality
تم إنشاؤه بواسطة: GitHub Copilot
"""

import pandas as pd
from pathlib import Path

def validate_csv_columns(csv_path):
    """
    تحقق من أن ملف CSV يحتوي على الأعمدة المطلوبة
    """
    try:
        df = pd.read_csv(csv_path)
        headers = [h.strip().lower() for h in df.columns]
        
        # Column name aliases
        column_mappings = {
            'id': ['id', 'orderid', 'transactionid', 'order_id'],
            'date': ['date', 'orderdate', 'order_date', 'transactiondate'],
            'amount': ['amount', 'totalprice', 'total_price', 'price', 'ordervalue'],
            'product': ['product', 'productname', 'product_name', 'item'],
            'city': ['city', 'location', 'region']
        }
        
        required_cols = {}
        missing = []
        
        for required, aliases in column_mappings.items():
            found = False
            for header in headers:
                if header in aliases:
                    required_cols[required] = header
                    found = True
                    break
            if not found:
                missing.append(required)
        
        if missing:
            print(f"❌ FAILED: Missing required columns: {missing}")
            print(f"   Available columns: {list(df.columns)}")
            return False
        
        print(f"✅ SUCCESS: CSV file is valid!")
        print(f"   File: {csv_path.name}")
        print(f"   Records: {len(df)}")
        print(f"   Columns found:")
        for req, actual in required_cols.items():
            print(f"     - {req}: '{actual}'")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Test all CSV files"""
    project_root = Path(__file__).parent
    data_dir = project_root / "data"
    
    test_files = [
        data_dir / "sales.csv",
        data_dir / "sample_sales.csv",
        data_dir / "cleaned_dataset.csv",
        data_dir / "minimal_example.csv",
    ]
    
    print("=" * 60)
    print("📋 CSV Validation Test")
    print("=" * 60)
    
    for test_file in test_files:
        if test_file.exists():
            print(f"\nTesting: {test_file.relative_to(project_root)}")
            print("-" * 60)
            validate_csv_columns(test_file)
        else:
            print(f"\n⚠️  File not found: {test_file.relative_to(project_root)}")

if __name__ == "__main__":
    main()
