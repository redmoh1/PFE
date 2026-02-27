"""
Data Validator - Schema Validation at Upload Time

=============================================================================
PROBLEM #3: Data Validation & Schema Awareness
=============================================================================
Previously, no strong validation of incoming datasets existed.
Invalid or incomplete data could silently break analysis.

CONCEPTUAL CORRECTION:
This module validates data AT UPLOAD TIME before any processing begins.
It provides:
- Clear error messages for missing/invalid data
- Explicit checks for required semantic fields
- Data quality metrics and warnings
- Type checking and coercion

=============================================================================
Author: AI Assistant
Version: 1.0.0
=============================================================================
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np

from schema_resolver import (
    SchemaResolver,
    SchemaResolutionResult,
    SemanticField,
    ANALYSIS_REQUIREMENTS,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATA QUALITY METRICS
# ============================================================================

@dataclass
class DataQualityMetrics:
    """Quality metrics for a dataset."""
    total_rows: int
    total_columns: int
    missing_values: Dict[str, int]  # column -> count of missing
    duplicate_rows: int
    numeric_columns: List[str]
    date_columns: List[str]
    text_columns: List[str]
    
    # Data range info
    date_range: Optional[Tuple[str, str]] = None
    numeric_ranges: Dict[str, Tuple[float, float]] = None
    
    def get_completeness_score(self) -> float:
        """Calculate data completeness score (0-100%)."""
        if self.total_rows == 0:
            return 0.0
        
        total_cells = self.total_rows * self.total_columns
        total_missing = sum(self.missing_values.values())
        
        if total_cells == 0:
            return 100.0
        
        return round((1 - total_missing / total_cells) * 100, 2)


# ============================================================================
# VALIDATION RESULT
# ============================================================================

@dataclass
class ValidationResult:
    """Complete validation result for a dataset."""
    # Basic info
    dataset_type: str
    file_name: str
    
    # Schema resolution
    schema_result: SchemaResolutionResult
    
    # Data quality
    quality_metrics: DataQualityMetrics
    
    # Validation outcome
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    
    # What can be done with this data
    available_analyses: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "dataset_type": self.dataset_type,
            "file_name": self.file_name,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "available_analyses": self.available_analyses,
            "quality": {
                "total_rows": self.quality_metrics.total_rows,
                "total_columns": self.quality_metrics.total_columns,
                "completeness_score": self.quality_metrics.get_completeness_score(),
                "duplicate_rows": self.quality_metrics.duplicate_rows,
            },
            "resolved_columns": {
                field.value: col 
                for field, col in self.schema_result.resolved_columns.items()
            },
        }


# ============================================================================
# DATA VALIDATOR CLASS
# ============================================================================

class DataValidator:
    """
    Validates incoming datasets before processing.
    
    USAGE:
        validator = DataValidator()
        result = validator.validate_upload(df, "sales", "sales.csv")
        
        if result.is_valid:
            # Proceed with processing
        else:
            # Show errors to user
            for error in result.errors:
                print(error)
    """
    
    def __init__(self):
        self.schema_resolver = SchemaResolver()
    
    def validate_upload(
        self,
        df: pd.DataFrame,
        dataset_type: str,
        file_name: str = "unknown"
    ) -> ValidationResult:
        """
        Validate an uploaded dataset.
        
        Args:
            df: The uploaded dataframe
            dataset_type: Expected type ("sales", "customers", "reviews")
            file_name: Original file name for error messages
            
        Returns:
            ValidationResult with complete validation info
        """
        errors: List[str] = []
        warnings: List[str] = []
        suggestions: List[str] = []
        
        # Step 1: Basic validation
        if df is None or df.empty:
            errors.append("Dataset is empty or could not be loaded")
            return ValidationResult(
                dataset_type=dataset_type,
                file_name=file_name,
                schema_result=SchemaResolutionResult(
                    resolved_columns={},
                    missing_required=[],
                    missing_optional=[],
                    unmapped_columns=[],
                    is_valid=False,
                    validation_errors=errors,
                    validation_warnings=[],
                    available_analyses=[],
                    unavailable_analyses={}
                ),
                quality_metrics=DataQualityMetrics(
                    total_rows=0,
                    total_columns=0,
                    missing_values={},
                    duplicate_rows=0,
                    numeric_columns=[],
                    date_columns=[],
                    text_columns=[]
                ),
                is_valid=False,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions,
                available_analyses=[]
            )
        
        # Step 2: Compute data quality metrics
        quality_metrics = self._compute_quality_metrics(df)
        
        # Step 3: Resolve schema
        schema_result = self.schema_resolver.resolve(df, dataset_type)
        errors.extend(schema_result.validation_errors)
        warnings.extend(schema_result.validation_warnings)
        
        # Step 4: Type-specific validation
        if dataset_type == "sales":
            self._validate_sales_data(df, schema_result, errors, warnings, suggestions)
        elif dataset_type == "customers":
            self._validate_customers_data(df, schema_result, errors, warnings, suggestions)
        elif dataset_type == "reviews":
            self._validate_reviews_data(df, schema_result, errors, warnings, suggestions)
        
        # Step 5: Data quality warnings
        if quality_metrics.duplicate_rows > 0:
            pct = round(quality_metrics.duplicate_rows / quality_metrics.total_rows * 100, 1)
            if pct > 10:
                warnings.append(
                    f"High duplicate rate: {quality_metrics.duplicate_rows} rows ({pct}%)"
                )
            else:
                warnings.append(
                    f"Found {quality_metrics.duplicate_rows} duplicate rows ({pct}%)"
                )
        
        completeness = quality_metrics.get_completeness_score()
        if completeness < 80:
            warnings.append(f"Low data completeness: {completeness}%")
            suggestions.append("Consider cleaning missing values before analysis")
        
        # Step 6: Generate suggestions
        if not schema_result.is_valid:
            suggestions.extend(self._generate_column_suggestions(df, schema_result))
        
        return ValidationResult(
            dataset_type=dataset_type,
            file_name=file_name,
            schema_result=schema_result,
            quality_metrics=quality_metrics,
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            available_analyses=schema_result.available_analyses
        )
    
    def _compute_quality_metrics(self, df: pd.DataFrame) -> DataQualityMetrics:
        """Compute data quality metrics for a dataframe."""
        # Identify column types
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        text_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
        
        # Try to identify date columns
        date_cols = []
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]':
                date_cols.append(col)
            elif col not in numeric_cols and col not in date_cols:
                # Try to parse as date
                try:
                    sample = df[col].dropna().head(10)
                    if len(sample) > 0:
                        pd.to_datetime(sample)
                        date_cols.append(col)
                        if col in text_cols:
                            text_cols.remove(col)
                except:
                    pass
        
        # Calculate missing values
        missing = {col: int(df[col].isna().sum()) for col in df.columns}
        
        # Calculate duplicates
        duplicates = int(df.duplicated().sum())
        
        # Calculate date range
        date_range = None
        for col in date_cols:
            try:
                dates = pd.to_datetime(df[col], errors='coerce').dropna()
                if len(dates) > 0:
                    date_range = (str(dates.min().date()), str(dates.max().date()))
                    break
            except:
                pass
        
        # Calculate numeric ranges
        numeric_ranges = {}
        for col in numeric_cols:
            try:
                numeric_ranges[col] = (float(df[col].min()), float(df[col].max()))
            except:
                pass
        
        return DataQualityMetrics(
            total_rows=len(df),
            total_columns=len(df.columns),
            missing_values=missing,
            duplicate_rows=duplicates,
            numeric_columns=numeric_cols,
            date_columns=date_cols,
            text_columns=text_cols,
            date_range=date_range,
            numeric_ranges=numeric_ranges
        )
    
    def _validate_sales_data(
        self,
        df: pd.DataFrame,
        schema_result: SchemaResolutionResult,
        errors: List[str],
        warnings: List[str],
        suggestions: List[str]
    ):
        """Validate sales-specific data requirements."""
        # Check date values
        date_col = schema_result.get_column(SemanticField.ORDER_DATE)
        if date_col:
            dates = pd.to_datetime(df[date_col], errors='coerce')
            invalid_dates = dates.isna().sum()
            if invalid_dates > 0:
                pct = round(invalid_dates / len(df) * 100, 1)
                if pct > 20:
                    errors.append(f"Too many invalid dates: {invalid_dates} rows ({pct}%)")
                else:
                    warnings.append(f"Found {invalid_dates} invalid dates ({pct}%)")
            
            # Check for future dates
            future_dates = (dates > pd.Timestamp.now()).sum()
            if future_dates > 0:
                warnings.append(f"Found {future_dates} future dates (may be data entry errors)")
        
        # Check price values
        price_col = schema_result.get_column(SemanticField.TOTAL_PRICE)
        if price_col:
            prices = pd.to_numeric(df[price_col], errors='coerce')
            negative_prices = (prices < 0).sum()
            if negative_prices > 0:
                warnings.append(f"Found {negative_prices} negative price values")
            
            zero_prices = (prices == 0).sum()
            if zero_prices > len(df) * 0.5:
                warnings.append(f"Warning: {zero_prices} zero-value transactions (>50%)")
    
    def _validate_customers_data(
        self,
        df: pd.DataFrame,
        schema_result: SchemaResolutionResult,
        errors: List[str],
        warnings: List[str],
        suggestions: List[str]
    ):
        """Validate customers-specific data requirements."""
        customer_col = schema_result.get_column(SemanticField.CUSTOMER_ID)
        if customer_col:
            duplicates = df[customer_col].duplicated().sum()
            if duplicates > 0:
                warnings.append(f"Found {duplicates} duplicate customer IDs")
    
    def _validate_reviews_data(
        self,
        df: pd.DataFrame,
        schema_result: SchemaResolutionResult,
        errors: List[str],
        warnings: List[str],
        suggestions: List[str]
    ):
        """Validate reviews-specific data requirements."""
        text_col = schema_result.get_column(SemanticField.REVIEW_TEXT)
        if text_col:
            # Check for very short reviews
            short_reviews = (df[text_col].str.len() < 10).sum()
            if short_reviews > len(df) * 0.3:
                warnings.append(
                    f"Many short reviews ({short_reviews}). "
                    "Customer Feedback may be less accurate."
                )
        
        rating_col = schema_result.get_column(SemanticField.RATING)
        if rating_col:
            ratings = pd.to_numeric(df[rating_col], errors='coerce')
            if ratings.min() < 0 or ratings.max() > 5:
                warnings.append("Rating values outside expected range (0-5)")
    
    def _generate_column_suggestions(
        self,
        df: pd.DataFrame,
        schema_result: SchemaResolutionResult
    ) -> List[str]:
        """Generate suggestions for fixing column issues."""
        suggestions = []
        
        for field in schema_result.missing_required:
            suggestions.append(
                f"Column '{field.value}' is required. "
                f"Your data might have it under a different name. "
                f"Available columns: {list(df.columns)}"
            )
        
        return suggestions


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def validate_upload(
    df: pd.DataFrame,
    dataset_type: str,
    file_name: str = "unknown"
) -> ValidationResult:
    """
    Convenience function to validate an uploaded dataset.
    
    Args:
        df: The uploaded dataframe
        dataset_type: Expected type ("sales", "customers", "reviews")
        file_name: Original file name for error messages
        
    Returns:
        ValidationResult
    """
    validator = DataValidator()
    return validator.validate_upload(df, dataset_type, file_name)


def quick_validate(
    file_path: Path,
    dataset_type: str = "sales"
) -> Tuple[bool, List[str]]:
    """
    Quick validation check for a file.
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    try:
        df = pd.read_csv(file_path)
        result = validate_upload(df, dataset_type, file_path.name)
        return result.is_valid, result.errors
    except Exception as e:
        return False, [f"Failed to read file: {str(e)}"]


# ============================================================================
# MAIN - Demo/Test
# ============================================================================

if __name__ == "__main__":
    print("Data Validator - Demo")
    print("=" * 60)
    
    # Create sample valid sales data
    valid_sales = pd.DataFrame({
        "OrderDate": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "CustomerID": [1, 2, 1],
        "Product": ["Widget A", "Widget B", "Widget A"],
        "TotalPrice": [100.0, 150.0, 200.0]
    })
    
    validator = DataValidator()
    result = validator.validate_upload(valid_sales, "sales", "test_sales.csv")
    
    print(f"Valid: {result.is_valid}")
    print(f"Available analyses: {result.available_analyses}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
    
    print()
    
    # Create sample invalid sales data
    invalid_sales = pd.DataFrame({
        "SomeDate": ["2024-01-01"],  # Wrong name
        "Value": [100.0]             # Wrong name
    })
    
    result2 = validator.validate_upload(invalid_sales, "sales", "bad_sales.csv")
    
    print("Invalid data test:")
    print(f"Valid: {result2.is_valid}")
    print(f"Errors: {result2.errors}")
    print(f"Suggestions: {result2.suggestions}")
