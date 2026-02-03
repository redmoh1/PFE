"""
Schema Resolver - Semantic Data Abstraction Layer

=============================================================================
PROBLEM #1: Hard-Coded Column Assumptions
=============================================================================
The pipeline previously assumed fixed column names (OrderDate, CustomerID, 
TotalPrice, Product). Any schema variation would break the system.

CONCEPTUAL CORRECTION:
We now decouple BUSINESS MEANING (semantics) from COLUMN NAMES (syntax).
The system defines what it NEEDS semantically, then RESOLVES actual column
names from the incoming data.

=============================================================================
PROBLEM #2: Conceptual & Logical Issues
=============================================================================
The project implicitly assumed it could analyze "any data", which is incorrect.

CONCEPTUAL CORRECTION:
This module explicitly defines:
- What TYPE of data the system is designed for (transactional sales data)
- What BUSINESS QUESTIONS it can answer
- What it CANNOT analyze
- REQUIRED vs OPTIONAL semantic fields

=============================================================================
ANALYTICAL SCOPE DEFINITION
=============================================================================
This system is designed for: TRANSACTIONAL SALES DATA ANALYSIS

Supported Business Questions:
1. Forecasting: "What will our sales be in the next N months?"
   - REQUIRES: date field + revenue/amount field
   
2. RFM Segmentation: "How do we categorize customers by value?"
   - REQUIRES: date + customer_id + revenue
   
3. Product Recommendations: "What products are frequently bought together?"
   - REQUIRES: customer_id or order_id + product field
   
4. Sentiment Analysis: "What is customer sentiment from reviews?"
   - REQUIRES: text/review field (from separate reviews dataset)

NOT Supported:
- Image/video analysis
- Real-time streaming data
- Non-transactional data (surveys, logs without transactions)
- Data without date context

=============================================================================
Author: AI Assistant
Version: 1.0.0
=============================================================================
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# SEMANTIC FIELD DEFINITIONS
# ============================================================================

class SemanticField(Enum):
    """
    Business-meaningful field types that the system can work with.
    Each semantic field can map to multiple possible column names.
    """
    # Core transaction fields
    ORDER_DATE = "order_date"          # When the transaction occurred
    CUSTOMER_ID = "customer_id"        # Who made the purchase
    ORDER_ID = "order_id"              # Transaction identifier
    PRODUCT = "product"                # What was purchased
    QUANTITY = "quantity"              # How many units
    UNIT_PRICE = "unit_price"          # Price per unit
    TOTAL_PRICE = "total_price"        # Total transaction value
    
    # Customer fields (from customers dataset)
    CITY = "city"                      # Customer location
    CUSTOMER_NAME = "customer_name"    # Customer name
    
    # Review/Sentiment fields (from reviews dataset)
    REVIEW_TEXT = "review_text"        # Customer review content
    RATING = "rating"                  # Numeric rating (1-5)
    REVIEW_DATE = "review_date"        # When review was written


# ============================================================================
# COLUMN ALIAS REGISTRY
# ============================================================================

# Maps each semantic field to possible column name variations
# This is the SINGLE SOURCE OF TRUTH for column name detection
COLUMN_ALIASES: Dict[SemanticField, List[str]] = {
    SemanticField.ORDER_DATE: [
        "OrderDate", "order_date", "Order_Date", "Sale_Date", "sale_date",
        "Date", "date", "TransactionDate", "transaction_date", "InvoiceDate",
        "invoice_date", "PurchaseDate", "purchase_date", "ds"
    ],
    SemanticField.CUSTOMER_ID: [
        "CustomerID", "customer_id", "Customer_ID", "CustomerId", "cust_id",
        "client_id", "ClientID", "buyer_id", "BuyerID", "user_id", "UserID"
    ],
    SemanticField.ORDER_ID: [
        "OrderID", "order_id", "Order_ID", "OrderId", "InvoiceNo", "invoice_no",
        "TransactionID", "transaction_id", "Receipt", "receipt_id"
    ],
    SemanticField.PRODUCT: [
        "Product", "product", "ProductName", "product_name", "Item", "item",
        "Description", "description", "ProductDescription", "SKU", "sku",
        "ItemName", "item_name", "StockCode", "stock_code"
    ],
    SemanticField.QUANTITY: [
        "Quantity", "quantity", "Qty", "qty", "Units", "units", "Amount",
        "Count", "count", "NumItems", "num_items"
    ],
    SemanticField.UNIT_PRICE: [
        "UnitPrice", "unit_price", "Price", "price", "ItemPrice", "item_price",
        "PricePerUnit", "Cost", "cost"
    ],
    SemanticField.TOTAL_PRICE: [
        "TotalPrice", "total_price", "Total", "total", "Revenue", "revenue",
        "Sales", "sales", "Amount", "amount", "Sales_Amount", "sales_amount",
        "OrderTotal", "order_total", "LineTotal", "line_total"
    ],
    SemanticField.CITY: [
        "City", "city", "Location", "location", "CustomerCity", "customer_city",
        "Region", "region", "State", "state", "Country", "country"
    ],
    SemanticField.CUSTOMER_NAME: [
        "CustomerName", "customer_name", "Name", "name", "FullName", "full_name",
        "ClientName", "client_name"
    ],
    SemanticField.REVIEW_TEXT: [
        "Review", "review", "ReviewText", "review_text", "Comment", "comment",
        "Feedback", "feedback", "Text", "text", "ReviewContent", "review_content"
    ],
    SemanticField.RATING: [
        "Rating", "rating", "Score", "score", "Stars", "stars", "Rate", "rate"
    ],
    SemanticField.REVIEW_DATE: [
        "ReviewDate", "review_date", "Review_Date", "Date", "date"
    ],
}


# ============================================================================
# ANALYSIS REQUIREMENTS
# ============================================================================

@dataclass
class AnalysisRequirement:
    """Defines what semantic fields are needed for each analysis type."""
    name: str
    description: str
    required_fields: List[SemanticField]
    optional_fields: List[SemanticField] = field(default_factory=list)
    min_rows: int = 10  # Minimum data points for meaningful analysis


# Define requirements for each analysis module
ANALYSIS_REQUIREMENTS: Dict[str, AnalysisRequirement] = {
    "forecasting": AnalysisRequirement(
        name="Sales Forecasting",
        description="Predict future sales based on historical trends",
        required_fields=[SemanticField.ORDER_DATE, SemanticField.TOTAL_PRICE],
        optional_fields=[SemanticField.PRODUCT, SemanticField.CUSTOMER_ID],
        min_rows=3  # Script can operate on small datasets; more rows improves reliability
    ),
    "rfm": AnalysisRequirement(
        name="RFM Customer Segmentation",
        description="Segment customers by Recency, Frequency, Monetary value",
        required_fields=[
            SemanticField.CUSTOMER_ID,
            SemanticField.ORDER_DATE,
            SemanticField.TOTAL_PRICE
        ],
        optional_fields=[SemanticField.ORDER_ID],
        min_rows=10
    ),
    "recommendation": AnalysisRequirement(
        name="Product Recommendations",
        description="Find products frequently purchased together",
        required_fields=[SemanticField.PRODUCT],
        optional_fields=[SemanticField.ORDER_ID, SemanticField.CUSTOMER_ID],
        min_rows=50  # Need sufficient transactions for pattern mining
    ),
    "sentiment": AnalysisRequirement(
        name="Sentiment Analysis",
        description="Analyze customer sentiment from reviews",
        required_fields=[SemanticField.REVIEW_TEXT],
        optional_fields=[SemanticField.RATING, SemanticField.REVIEW_DATE],
        min_rows=5
    ),
}


# ============================================================================
# SCHEMA RESOLUTION RESULT
# ============================================================================

@dataclass
class SchemaResolutionResult:
    """
    Result of schema resolution for a dataset.
    Contains the mapping from semantic fields to actual column names.
    """
    # Mapping: semantic field -> actual column name in the data
    resolved_columns: Dict[SemanticField, str]
    
    # Fields that could not be resolved
    missing_required: List[SemanticField]
    missing_optional: List[SemanticField]
    
    # Original columns that were not mapped
    unmapped_columns: List[str]
    
    # Validation status
    is_valid: bool
    validation_errors: List[str]
    validation_warnings: List[str]
    
    # Which analyses can be performed
    available_analyses: List[str]
    unavailable_analyses: Dict[str, str]  # analysis -> reason
    
    def get_column(self, semantic_field: SemanticField) -> Optional[str]:
        """Get the actual column name for a semantic field."""
        return self.resolved_columns.get(semantic_field)
    
    def has_field(self, semantic_field: SemanticField) -> bool:
        """Check if a semantic field was resolved."""
        return semantic_field in self.resolved_columns


# ============================================================================
# SCHEMA RESOLVER CLASS
# ============================================================================

class SchemaResolver:
    """
    Resolves semantic field names to actual column names in a dataset.
    
    USAGE:
        resolver = SchemaResolver()
        result = resolver.resolve(df)
        
        if result.is_valid:
            date_col = result.get_column(SemanticField.ORDER_DATE)
            # Use date_col to access the data
    """
    
    def __init__(self, custom_aliases: Dict[SemanticField, List[str]] = None):
        """
        Initialize resolver with optional custom aliases.
        
        Args:
            custom_aliases: Additional column aliases to merge with defaults
        """
        self.aliases = COLUMN_ALIASES.copy()
        if custom_aliases:
            for field, aliases in custom_aliases.items():
                if field in self.aliases:
                    self.aliases[field] = list(set(self.aliases[field] + aliases))
                else:
                    self.aliases[field] = aliases
    
    def resolve(
        self,
        df: pd.DataFrame,
        dataset_type: str = "sales",
        required_analyses: List[str] = None
    ) -> SchemaResolutionResult:
        """
        Resolve semantic fields to actual column names in the dataframe.
        
        Args:
            df: The dataframe to analyze
            dataset_type: Type of dataset ("sales", "customers", "reviews")
            required_analyses: List of analyses that must be supported
            
        Returns:
            SchemaResolutionResult with mapping and validation info
        """
        resolved: Dict[SemanticField, str] = {}
        missing_required: List[SemanticField] = []
        missing_optional: List[SemanticField] = []
        unmapped: List[str] = list(df.columns)
        errors: List[str] = []
        warnings: List[str] = []
        
        # Track which columns have been mapped
        used_columns = set()
        
        # Resolve each semantic field
        for semantic_field, possible_names in self.aliases.items():
            for name in possible_names:
                if name in df.columns and name not in used_columns:
                    resolved[semantic_field] = name
                    used_columns.add(name)
                    if name in unmapped:
                        unmapped.remove(name)
                    break
        
        # Determine which analyses are available
        available_analyses: List[str] = []
        unavailable_analyses: Dict[str, str] = {}
        
        for analysis_name, requirement in ANALYSIS_REQUIREMENTS.items():
            # Check required fields
            missing_for_analysis = []
            for field in requirement.required_fields:
                if field not in resolved:
                    missing_for_analysis.append(field)
            
            if missing_for_analysis:
                unavailable_analyses[analysis_name] = (
                    f"Missing required fields: {[f.value for f in missing_for_analysis]}"
                )
            elif len(df) < requirement.min_rows:
                unavailable_analyses[analysis_name] = (
                    f"Insufficient data: {len(df)} rows, need {requirement.min_rows}"
                )
            else:
                available_analyses.append(analysis_name)
        
        # Validate based on dataset type
        if dataset_type == "sales":
            # Sales data MUST have date and some form of value
            if SemanticField.ORDER_DATE not in resolved:
                errors.append("Sales data requires a date column (e.g., OrderDate)")
                missing_required.append(SemanticField.ORDER_DATE)
            
            if SemanticField.TOTAL_PRICE not in resolved:
                # Check if we can compute it
                if (SemanticField.UNIT_PRICE in resolved and 
                    SemanticField.QUANTITY in resolved):
                    warnings.append(
                        "No TotalPrice column found. Will compute from UnitPrice × Quantity"
                    )
                else:
                    errors.append(
                        "Sales data requires a value column (e.g., TotalPrice, Revenue)"
                    )
                    missing_required.append(SemanticField.TOTAL_PRICE)
        
        elif dataset_type == "reviews":
            if SemanticField.REVIEW_TEXT not in resolved:
                errors.append("Reviews data requires a text column (e.g., Review, Comment)")
                missing_required.append(SemanticField.REVIEW_TEXT)
        
        # Check if required analyses are supported
        if required_analyses:
            for analysis in required_analyses:
                if analysis in unavailable_analyses:
                    errors.append(f"Required analysis '{analysis}' not available: "
                                f"{unavailable_analyses[analysis]}")
        
        # Add warnings for unmapped columns
        if unmapped:
            warnings.append(f"Unmapped columns will be ignored: {unmapped}")
        
        return SchemaResolutionResult(
            resolved_columns=resolved,
            missing_required=missing_required,
            missing_optional=missing_optional,
            unmapped_columns=unmapped,
            is_valid=len(errors) == 0,
            validation_errors=errors,
            validation_warnings=warnings,
            available_analyses=available_analyses,
            unavailable_analyses=unavailable_analyses
        )
    
    def get_canonical_dataframe(
        self,
        df: pd.DataFrame,
        resolution: SchemaResolutionResult
    ) -> pd.DataFrame:
        """
        Create a dataframe with canonical (standardized) column names.
        
        This allows pipeline modules to always use the same column names
        regardless of the original data schema.
        
        Args:
            df: Original dataframe
            resolution: Schema resolution result
            
        Returns:
            DataFrame with canonical column names prefixed with "__"
        """
        result = df.copy()
        
        # Add canonical columns with __ prefix to avoid conflicts
        for semantic_field, actual_col in resolution.resolved_columns.items():
            canonical_name = f"__{semantic_field.value}"
            result[canonical_name] = result[actual_col]
        
        return result
    
    def validate_and_report(
        self,
        df: pd.DataFrame,
        dataset_type: str = "sales"
    ) -> Tuple[SchemaResolutionResult, str]:
        """
        Validate a dataset and generate a human-readable report.
        
        Args:
            df: DataFrame to validate
            dataset_type: Type of dataset
            
        Returns:
            Tuple of (resolution result, formatted report string)
        """
        resolution = self.resolve(df, dataset_type)
        
        lines = [
            "=" * 60,
            "SCHEMA RESOLUTION REPORT",
            "=" * 60,
            "",
            f"Dataset Type: {dataset_type}",
            f"Total Rows: {len(df)}",
            f"Total Columns: {len(df.columns)}",
            "",
            "RESOLVED FIELDS:",
        ]
        
        for field, col in resolution.resolved_columns.items():
            lines.append(f"  ✓ {field.value} -> '{col}'")
        
        if resolution.missing_required:
            lines.append("")
            lines.append("MISSING REQUIRED FIELDS:")
            for field in resolution.missing_required:
                lines.append(f"  ✗ {field.value}")
        
        if resolution.unmapped_columns:
            lines.append("")
            lines.append("UNMAPPED COLUMNS (ignored):")
            for col in resolution.unmapped_columns:
                lines.append(f"  - {col}")
        
        lines.append("")
        lines.append("AVAILABLE ANALYSES:")
        for analysis in resolution.available_analyses:
            req = ANALYSIS_REQUIREMENTS[analysis]
            lines.append(f"  ✓ {req.name}")
        
        if resolution.unavailable_analyses:
            lines.append("")
            lines.append("UNAVAILABLE ANALYSES:")
            for analysis, reason in resolution.unavailable_analyses.items():
                req = ANALYSIS_REQUIREMENTS[analysis]
                lines.append(f"  ✗ {req.name}: {reason}")
        
        if resolution.validation_errors:
            lines.append("")
            lines.append("ERRORS:")
            for error in resolution.validation_errors:
                lines.append(f"  ❌ {error}")
        
        if resolution.validation_warnings:
            lines.append("")
            lines.append("WARNINGS:")
            for warning in resolution.validation_warnings:
                lines.append(f"  ⚠️ {warning}")
        
        lines.append("")
        lines.append(f"VALIDATION STATUS: {'PASSED ✓' if resolution.is_valid else 'FAILED ✗'}")
        lines.append("=" * 60)
        
        return resolution, "\n".join(lines)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def resolve_schema(
    df: pd.DataFrame,
    dataset_type: str = "sales"
) -> SchemaResolutionResult:
    """
    Convenience function to resolve schema for a dataframe.
    
    Args:
        df: DataFrame to analyze
        dataset_type: Type of dataset ("sales", "customers", "reviews")
        
    Returns:
        SchemaResolutionResult
    """
    resolver = SchemaResolver()
    return resolver.resolve(df, dataset_type)


def validate_sales_data(df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
    """
    Validate that a dataframe contains valid sales data.
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    resolver = SchemaResolver()
    result = resolver.resolve(df, "sales")
    return result.is_valid, result.validation_errors, result.validation_warnings


def get_column_for(
    df: pd.DataFrame,
    semantic_field: SemanticField
) -> Optional[str]:
    """
    Quick lookup: get the actual column name for a semantic field.
    
    Returns None if the field is not found.
    """
    for alias in COLUMN_ALIASES.get(semantic_field, []):
        if alias in df.columns:
            return alias
    return None


def can_perform_analysis(
    df: pd.DataFrame,
    analysis_name: str
) -> Tuple[bool, str]:
    """
    Check if a specific analysis can be performed on the data.
    
    Args:
        df: DataFrame to check
        analysis_name: One of "forecasting", "rfm", "recommendation", "sentiment"
        
    Returns:
        Tuple of (can_perform, reason_if_not)
    """
    if analysis_name not in ANALYSIS_REQUIREMENTS:
        return False, f"Unknown analysis type: {analysis_name}"
    
    resolver = SchemaResolver()
    result = resolver.resolve(df)
    
    if analysis_name in result.available_analyses:
        return True, "All requirements met"
    else:
        return False, result.unavailable_analyses.get(analysis_name, "Unknown reason")


# ============================================================================
# MAIN - Demo/Test
# ============================================================================

if __name__ == "__main__":
    # Demo with sample data
    print("Schema Resolver - Demo")
    print("=" * 60)
    
    # Create sample data with various column naming conventions
    sample_data = pd.DataFrame({
        "Sale_Date": ["2024-01-01", "2024-01-02"],
        "cust_id": [1, 2],
        "ProductName": ["Widget A", "Widget B"],
        "Qty": [5, 3],
        "Price": [10.0, 15.0],
        "ExtraColumn": ["x", "y"]
    })
    
    resolver = SchemaResolver()
    result, report = resolver.validate_and_report(sample_data, "sales")
    print(report)
