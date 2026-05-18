"""
Pipeline Controller - SINGLE SOURCE OF TRUTH for ML Pipeline Orchestration.

This module is the CANONICAL AUTHORITY for:
1. Detecting data upload events
2. Detecting data deletion events
3. Enforcing a CLEAN STATE before pipeline execution
4. Orchestrating pipeline execution in DETERMINISTIC ORDER:
   EDA -> Cleaning -> Forecasting -> RFM -> Recommendations -> Sentiment

=============================================================================
PROBLEM #4: Pipeline Rigidity
=============================================================================
Previously, the pipeline assumed all datasets support all analyses
(forecasting, RFM, recommendations, sentiment).

CONCEPTUAL CORRECTION:
Each analysis module is now CONDITIONAL - enabled/disabled based on:
1. Available data columns (semantic field resolution)
2. Minimum data requirements (row counts)
3. Dataset type compatibility

The pipeline gracefully SKIPS incompatible analyses instead of failing.

=============================================================================

CRITICAL RULES:
- NO caching of DataFrames - always read fresh from disk
- DELETE old outputs before generating new ones
- If a module produces NO results, it MUST delete any old output files
- All state must be deterministic and reproducible

Author: AI Assistant
Version: 2.0.0 - Added conditional pipeline execution
"""

import sys
import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.tenant_paths import derived_output_paths, ensure_tenant_directories, tenant_outputs_dir, tenant_uploads_dir

# ============================================================================
# Path Setup
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
LOGS_DIR = BASE_DIR / "logs"
SRC_DIR = BASE_DIR / "src"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# Logging Configuration
# ============================================================================

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


def _tenant_dir_key(company_id: str, branch_id: Optional[str] = None) -> str:
    company = str(company_id or "Acme Corp").strip().replace("/", "_")
    branch = str(branch_id or "GLOBAL").strip().replace("/", "_")
    return f"{company}__{branch}"


def _tenant_data_dir(company_id: str, branch_id: Optional[str] = None) -> Path:
    return tenant_uploads_dir(DATA_DIR, company_id or "unknown", branch_id)


def _tenant_output_dir(company_id: str, branch_id: Optional[str] = None) -> Path:
    return tenant_outputs_dir(DATA_DIR, company_id or "unknown", branch_id)


def _build_tenant_env(company_id: str, branch_id: Optional[str] = None) -> Dict[str, str]:
    tenant_dirs = ensure_tenant_directories(DATA_DIR, company_id or "unknown", branch_id)
    scope_dir = tenant_dirs["scope"]
    data_dir = tenant_dirs["uploads"]
    output_dir = tenant_dirs["outputs"]
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "SI_COMPANY_ID": str(company_id),
            "SI_BRANCH_ID": str(branch_id or "GLOBAL"),
            "SI_TENANT_KEY": _tenant_dir_key(company_id, branch_id),
            "SI_TENANT_ROOT": str(scope_dir),
            "SI_DATA_DIR": str(data_dir),
            "SI_OUTPUT_DIR": str(output_dir),
            "SI_PLOTS_DIR": str(plots_dir),
            "SI_FORECASTS_DIR": str(tenant_dirs["forecasts"]),
            "SI_SEGMENTATION_DIR": str(tenant_dirs["segmentation"]),
            "SI_SENTIMENT_DIR": str(tenant_dirs["sentiment"]),
            "SI_RECOMMENDATIONS_DIR": str(tenant_dirs["recommendations"]),
            "SI_NOTIFICATIONS_DIR": str(tenant_dirs["notifications"]),
        }
    )
    return env


def _current_tenant_dirs() -> tuple[Path, Path]:
    """Resolve the active tenant data/output directories from the environment."""
    company_id = os.getenv("SI_COMPANY_ID", "").strip()
    branch_id = os.getenv("SI_BRANCH_ID", "").strip()
    data_dir_value = os.getenv("SI_DATA_DIR", "").strip()
    output_dir_value = os.getenv("SI_OUTPUT_DIR", "").strip()

    if data_dir_value and output_dir_value:
        return Path(data_dir_value).expanduser(), Path(output_dir_value).expanduser()

    if company_id:
        if branch_id and branch_id.upper() != "GLOBAL":
            return _tenant_data_dir(company_id, branch_id), _tenant_output_dir(company_id, branch_id)
        return _tenant_data_dir(company_id, None), _tenant_output_dir(company_id, None)

    return DATA_DIR, OUTPUT_DIR


def _tenant_file_map(company_id: Optional[str], branch_id: Optional[str]) -> dict[str, Path]:
    if company_id:
        return derived_output_paths(DATA_DIR, company_id, branch_id)

    return {
        "merged_data.csv": DATA_DIR / "merged_data.csv",
        "cleaned_dataset.csv": DATA_DIR / "cleaned_dataset.csv",
        "rfm_table.csv": DATA_DIR / "rfm_table.csv",
        "product_recommendations.csv": DATA_DIR / "product_recommendations.csv",
        "sentiment_results.csv": DATA_DIR / "sentiment_results.csv",
        "sales_forecast.csv": DATA_DIR / "sales_forecast.csv",
        "sales_forecast_future.csv": DATA_DIR / "sales_forecast_future.csv",
        "eda_report.json": OUTPUT_DIR / "eda_report.json",
        "kpis.csv": OUTPUT_DIR / "kpis.csv",
        "monthly_sales.csv": OUTPUT_DIR / "monthly_sales.csv",
        "sales_by_city.csv": OUTPUT_DIR / "sales_by_city.csv",
        "top_products.csv": OUTPUT_DIR / "top_products.csv",
        "clv_analysis.csv": OUTPUT_DIR / "clv_analysis.csv",
        "clv_insights.json": OUTPUT_DIR / "clv_insights.json",
    }


# ============================================================================
# Import Schema Resolver for Conditional Execution
# ============================================================================

try:
    from .schema_resolver import (
        SchemaResolver, 
        SemanticField, 
        ANALYSIS_REQUIREMENTS,
        can_perform_analysis
    )
    SCHEMA_RESOLVER_AVAILABLE = True
    logger.info("Schema Resolver imported successfully")
except ImportError as e:
    SCHEMA_RESOLVER_AVAILABLE = False
    logger.warning(f"Schema Resolver not available: {e}. Using fallback logic.")


# ============================================================================
# File Definitions - SINGLE SOURCE OF TRUTH
# ============================================================================

# Canonical input files (copied from uploaded files)
CANONICAL_INPUT_FILES = {
    "sales": "sales.csv",
    "customers": "customers.csv",
    "reviews": "customer_reviews.csv",
}

# Derived output files (generated by ML pipeline)
DERIVED_OUTPUT_FILES = [
    "merged_data.csv",
    "cleaned_dataset.csv",
    "rfm_table.csv",
    "product_recommendations.csv",
    "sentiment_results.csv",
    "sales_forecast.csv",
    "sales_forecast_future.csv",
    # New intelligence modules outputs
    "clv_analysis.csv",
    "clv_insights.json",
]

# Directories to clean on hard reset
DERIVED_DIRECTORIES = [
    "output/plots",
    "src/ml_lifecycle/model_registry",
]

# Additional output files in the output directory
ADDITIONAL_OUTPUT_FILES = [
    "eda_report.json",
    "kpis.csv",
    "monthly_sales.csv",
    "sales_by_city.csv",
    "top_products.csv",
]

# Pipeline script execution order (DETERMINISTIC)
# NOTE: 02_cleaning is now integrated into 01_eda.py which creates both
# merged_data.csv and cleaned_dataset.csv directly
PIPELINE_SCRIPTS = {
    "01_eda": "01_eda.py",
    # "02_cleaning": "02_cleaning_features.py",  # Integrated into 01_eda
    "03_forecasting": "03_forecasting.py",
    "04_rfm": "04_rfm.py",
    "05_recommendation": "05_recommendation.py",
    "06_sentiment": "06_sentiment.py",
    "09_clv_calculation": "09_clv_calculation.py",        # Customer Lifetime Value
}


# ============================================================================
# Conditional Pipeline Execution - Data Availability Check
# ============================================================================

def determine_available_analyses(data_path: Path = None) -> Dict[str, Dict[str, Any]]:
    """
    Determine which analyses can be performed on the current data.
    
    This is the KEY FUNCTION for making pipeline execution conditional.
    It checks data availability and returns a dict of available analyses.
    
    Args:
        data_path: Path to the data file to check (defaults to cleaned_dataset.csv)
        
    Returns:
        Dict mapping analysis_name -> {available: bool, reason: str}
    """
    import pandas as pd
    
    result = {
        "eda": {"available": True, "reason": "Always required"},
        "forecasting": {"available": False, "reason": "Not checked yet"},
        "rfm": {"available": False, "reason": "Not checked yet"},
        "recommendation": {"available": False, "reason": "Not checked yet"},
        "sentiment": {"available": False, "reason": "Not checked yet"}
    }
    
    # Check for sales data
    if data_path is None:
        tenant_data_dir, _ = _current_tenant_dirs()
        data_path = tenant_data_dir / "cleaned_dataset.csv"
        if not data_path.exists():
            data_path = tenant_data_dir / "sales.csv"
    
    if not data_path.exists():
        for key in result:
            if key != "eda":
                result[key] = {"available": False, "reason": "No sales data found"}
        return result
    
    try:
        df = pd.read_csv(data_path)
        row_count = len(df)
        columns = set(df.columns)
        
        # Use Schema Resolver if available
        if SCHEMA_RESOLVER_AVAILABLE:
            resolver = SchemaResolver()
            resolution = resolver.resolve(df, "sales")
            
            # Check each analysis type
            for analysis_name in ["forecasting", "rfm", "recommendation"]:
                can_do, reason = can_perform_analysis(df, analysis_name)
                result[analysis_name] = {"available": can_do, "reason": reason}
        else:
            # Fallback: Manual column detection
            logger.info("[AVAILABILITY] Using fallback column detection")
            
            # Forecasting: needs date + value
            date_cols = ["OrderDate", "order_date", "Date", "Sale_Date"]
            value_cols = ["TotalPrice", "Revenue", "Sales", "Amount", "total_price"]
            has_date = any(c in columns for c in date_cols)
            has_value = any(c in columns for c in value_cols)
            
            if has_date and has_value and row_count >= 3:
                result["forecasting"] = {"available": True, "reason": "Date and value columns found"}
            else:
                missing = []
                if not has_date: missing.append("date column")
                if not has_value: missing.append("value column")
                if row_count < 3: missing.append(f"min rows (have {row_count}, need 3)")
                result["forecasting"] = {"available": False, "reason": f"Missing: {', '.join(missing)}"}
            
            # RFM: needs date + customer_id + value
            customer_cols = ["CustomerID", "customer_id", "Customer_ID", "cust_id"]
            has_customer = any(c in columns for c in customer_cols)
            
            if has_date and has_customer and has_value and row_count >= 10:
                result["rfm"] = {"available": True, "reason": "All required columns found"}
            else:
                missing = []
                if not has_date: missing.append("date column")
                if not has_customer: missing.append("customer_id column")
                if not has_value: missing.append("value column")
                result["rfm"] = {"available": False, "reason": f"Missing: {', '.join(missing)}"}
            
            # Recommendation: needs product column
            product_cols = ["Product", "product", "ProductName", "Item", "Description"]
            has_product = any(c in columns for c in product_cols)
            
            if has_product and row_count >= 50:
                result["recommendation"] = {"available": True, "reason": "Product column found"}
            else:
                missing = []
                if not has_product: missing.append("product column")
                if row_count < 50: missing.append(f"min rows (have {row_count}, need 50)")
                result["recommendation"] = {"available": False, "reason": f"Missing: {', '.join(missing)}"}
        
        # Sentiment: check for reviews file separately
        tenant_data_dir, _ = _current_tenant_dirs()
        reviews_path = tenant_data_dir / "customer_reviews.csv"
        if reviews_path.exists():
            try:
                reviews_df = pd.read_csv(reviews_path)
                text_cols = ["Review", "review", "Comment", "Feedback", "Text"]
                has_text = any(c in reviews_df.columns for c in text_cols)
                if has_text and len(reviews_df) >= 5:
                    result["sentiment"] = {"available": True, "reason": "Reviews file with text column found"}
                else:
                    result["sentiment"] = {"available": False, "reason": "Reviews file missing text column"}
            except Exception as e:
                result["sentiment"] = {"available": False, "reason": f"Error reading reviews: {e}"}
        else:
            result["sentiment"] = {"available": False, "reason": "No customer_reviews.csv found"}
        
        logger.info(f"[AVAILABILITY] Analysis availability determined: "
                   f"{[k for k, v in result.items() if v['available']]}")
        
    except Exception as e:
        logger.error(f"[AVAILABILITY] Error checking data: {e}")
        for key in result:
            if key != "eda":
                result[key] = {"available": False, "reason": f"Error: {str(e)}"}
    
    return result


# ============================================================================
# State Management
# ============================================================================

class PipelineState:
    """
    Manages pipeline execution state.
    CRITICAL: This class never caches data - it only tracks execution status.
    """
    
    def __init__(self):
        self.last_execution_time: Optional[datetime] = None
        self.last_execution_status: Dict[str, Any] = {}
        self.is_running: bool = False
        self.available_analyses: Dict[str, Dict[str, Any]] = {}
    
    def reset(self):
        """Reset all state - called before new pipeline execution."""
        self.last_execution_time = None
        self.last_execution_status = {}
        self.is_running = False
        self.available_analyses = {}
    
    def update_availability(self, data_path: Path = None):
        """Update which analyses are available based on current data."""
        self.available_analyses = determine_available_analyses(data_path)


# Global singleton instance
_pipeline_state = PipelineState()


def get_pipeline_state() -> PipelineState:
    """Get the singleton pipeline state instance."""
    return _pipeline_state


# ============================================================================
# File Deletion Functions
# ============================================================================

def delete_file_if_exists(file_path: Path, context: str = "") -> bool:
    """
    Delete a file if it exists.
    
    Args:
        file_path: Path to the file to delete
        context: Optional context for logging
        
    Returns:
        True if file was deleted, False if file didn't exist
    """
    try:
        if file_path.exists():
            file_path.unlink()
            logger.info(f"[DELETE] ✓ Deleted: {file_path.name} {context}")
            return True
        else:
            logger.debug(f"[DELETE] File not found (already clean): {file_path.name}")
            return False
    except Exception as e:
        logger.error(f"[DELETE] ✗ Failed to delete {file_path.name}: {e}")
        return False


def hard_reset_derived_outputs(company_id: Optional[str] = None, branch_id: Optional[str] = None) -> Dict[str, Any]:
    """
    HARD RESET: Delete ALL derived ML output files.
    
    This is the NUCLEAR option - used when:
    1. ANY dataset is deleted
    2. A critical error occurs in the pipeline
    3. User explicitly requests a clean slate
    
    Returns:
        Dict with deleted files count and any errors
    """
    logger.info("=" * 70)
    logger.info("[HARD RESET] Deleting ALL derived output files")
    logger.info("=" * 70)
    
    deleted_count = 0
    errors = []
    deleted_files = []
    
    data_root = _tenant_data_dir(company_id, branch_id) if company_id else DATA_DIR
    output_root = _tenant_output_dir(company_id, branch_id) if company_id else OUTPUT_DIR
    file_map = _tenant_file_map(company_id, branch_id)
    plots_root = output_root / "plots"

    # Delete derived files in data directory
    for filename in DERIVED_OUTPUT_FILES:
        file_path = file_map.get(filename, data_root / filename)
        if delete_file_if_exists(file_path, context="(data dir)"):
            deleted_count += 1
            deleted_files.append(filename)
    
    # Delete additional output files
    for filename in ADDITIONAL_OUTPUT_FILES:
        file_path = file_map.get(filename, output_root / filename)
        if delete_file_if_exists(file_path, context="(output dir)"):
            deleted_count += 1
            deleted_files.append(f"output/{filename}")
    
    # Clear plots directory
    if plots_root.exists():
        try:
            for plot_file in plots_root.glob("*.png"):
                plot_file.unlink()
                deleted_count += 1
                deleted_files.append(f"plots/{plot_file.name}")
            logger.info(f"[HARD RESET] ✓ Cleared plots directory")
        except Exception as e:
            errors.append(f"Failed to clear plots: {e}")
            logger.error(f"[HARD RESET] ✗ Failed to clear plots: {e}")
    
    # model_registry currently stores shared artifacts, so only clear it for a full global reset.
    if company_id is None:
        model_registry_dir = BASE_DIR / "src" / "ml_lifecycle" / "model_registry"
        if model_registry_dir.exists():
            try:
                for model_file in model_registry_dir.glob("*"):
                    if model_file.is_file():
                        model_file.unlink()
                        deleted_count += 1
                        deleted_files.append(f"model_registry/{model_file.name}")
                logger.info(f"[HARD RESET] ✓ Cleared model_registry directory")
            except Exception as e:
                errors.append(f"Failed to clear model_registry: {e}")
                logger.error(f"[HARD RESET] ✗ Failed to clear model_registry: {e}")
    else:
        logger.info("[HARD RESET] Skipping shared model_registry cleanup for tenant-scoped reset")
    
    logger.info("=" * 70)
    logger.info(f"[HARD RESET] COMPLETE: {deleted_count} files deleted")
    logger.info("=" * 70)
    
    return {
        "deleted_count": deleted_count,
        "deleted_files": deleted_files,
        "errors": errors,
        "timestamp": datetime.utcnow().isoformat()
    }


def delete_single_output(output_type: str, company_id: Optional[str] = None, branch_id: Optional[str] = None) -> bool:
    """
    Delete a specific output file.
    
    Args:
        output_type: One of 'rfm', 'recommendations', 'sentiment', 'forecast'
        
    Returns:
        True if file was deleted or didn't exist, False on error
    """
    file_map = _tenant_file_map(company_id, branch_id)
    output_map = {
        "rfm": file_map["rfm_table.csv"],
        "recommendations": file_map["product_recommendations.csv"],
        "sentiment": file_map["sentiment_results.csv"],
        "forecast": file_map["sales_forecast_future.csv"],
        "cleaned": file_map["cleaned_dataset.csv"],
        "merged": file_map["merged_data.csv"],
    }
    
    file_path = output_map.get(output_type)
    if file_path:
        return delete_file_if_exists(file_path, context=f"(type: {output_type})")
    else:
        logger.warning(f"[DELETE] Unknown output type: {output_type}")
        return False


# ============================================================================
# Data Detection Functions
# ============================================================================

def detect_canonical_files() -> Dict[str, bool]:
    """
    Detect which canonical input files exist.
    
    Returns:
        Dict mapping dataset_type to existence status
    """
    status = {}
    tenant_data_dir, _ = _current_tenant_dirs()
    for dataset_type, filename in CANONICAL_INPUT_FILES.items():
        file_path = tenant_data_dir / filename
        exists = file_path.exists() and file_path.stat().st_size > 0
        status[dataset_type] = exists
        logger.debug(f"[DETECT] {dataset_type}: {'EXISTS' if exists else 'MISSING'}")
    return status


def detect_derived_outputs() -> Dict[str, bool]:
    """
    Detect which derived output files exist.
    
    Returns:
        Dict mapping filename to existence status
    """
    status = {}
    company_id = os.getenv("SI_COMPANY_ID", "").strip() or None
    branch_id = os.getenv("SI_BRANCH_ID", "").strip() or None
    file_map = _tenant_file_map(company_id, None if branch_id in {None, "", "GLOBAL"} else branch_id)
    tenant_data_dir, tenant_output_dir = _current_tenant_dirs()
    for filename in DERIVED_OUTPUT_FILES:
        file_path = file_map.get(filename, tenant_data_dir / filename)
        if not file_path.exists():
            file_path = tenant_output_dir / filename
        exists = file_path.exists() and file_path.stat().st_size > 0
        status[filename] = exists
    return status


def detect_data_upload(dataset_type: str, file_path: Path) -> Dict[str, Any]:
    """
    Detect and validate a data upload event.
    
    CRITICAL: This function should be called BEFORE copying the file to canonical location.
    
    Args:
        dataset_type: One of 'sales', 'customers', 'reviews'
        file_path: Path to the uploaded file
        
    Returns:
        Dict with validation status and metadata
    """
    logger.info(f"[UPLOAD DETECT] Dataset type: {dataset_type}, File: {file_path}")
    
    result = {
        "valid": False,
        "dataset_type": dataset_type,
        "file_path": str(file_path),
        "row_count": 0,
        "columns": [],
        "errors": [],
        "warnings": []
    }
    
    if not file_path.exists():
        result["errors"].append("File not found")
        return result
    
    try:
        import pandas as pd
        df = pd.read_csv(file_path)
        result["row_count"] = len(df)
        result["columns"] = list(df.columns)
        
        if len(df) == 0:
            result["errors"].append("File is empty (0 rows)")
            return result
        
        # Validate required columns based on dataset type
        if dataset_type == "sales":
            required = ["OrderDate", "TotalPrice"]
            optional = ["OrderID", "ProductID", "CustomerID", "City"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                result["warnings"].append(f"Missing recommended columns: {missing}")
        
        elif dataset_type == "reviews":
            text_cols = ["ReviewText", "review_text", "Review", "text", "Text", "comment"]
            has_text = any(c in df.columns for c in text_cols)
            if not has_text:
                result["errors"].append(f"Missing review text column. Expected one of: {text_cols}")
                return result
        
        result["valid"] = True
        logger.info(f"[UPLOAD DETECT] Valid upload: {result['row_count']} rows, {len(result['columns'])} columns")
        
    except Exception as e:
        result["errors"].append(f"Failed to parse CSV: {str(e)}")
        logger.error(f"[UPLOAD DETECT] Parse error: {e}")
    
    return result


def detect_data_deletion(dataset_type: str) -> Dict[str, Any]:
    """
    Handle data deletion event.
    
    CRITICAL: This triggers a HARD RESET of all derived outputs.
    
    Args:
        dataset_type: One of 'sales', 'customers', 'reviews'
        
    Returns:
        Dict with deletion results
    """
    logger.info("=" * 70)
    logger.info(f"[DELETION DETECT] Dataset type: {dataset_type}")
    logger.info("[DELETION DETECT] Triggering HARD RESET of all derived outputs")
    logger.info("=" * 70)
    
    # Delete the canonical input file
    canonical_file = CANONICAL_INPUT_FILES.get(dataset_type)
    if canonical_file:
        delete_file_if_exists(_tenant_data_dir(os.getenv("SI_COMPANY_ID", "unknown"), os.getenv("SI_BRANCH_ID") or None) / canonical_file, context="(canonical input)")
    
    # HARD RESET all derived outputs
    reset_result = hard_reset_derived_outputs()
    
    return {
        "dataset_type": dataset_type,
        "canonical_deleted": canonical_file,
        "hard_reset": reset_result,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# Pipeline Execution Functions
# ============================================================================

def run_script(script_name: str, timeout: int = 180, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Run a single ML pipeline script.
    
    Args:
        script_name: Name of the script (e.g., "01_eda.py")
        timeout: Maximum execution time in seconds
        
    Returns:
        Dict with execution status, stdout, stderr
    """
    script_path = SRC_DIR / script_name
    
    if not script_path.exists():
        return {
            "success": False,
            "script": script_name,
            "error": f"Script not found: {script_path}",
            "stdout": "",
            "stderr": ""
        }
    
    logger.info(f"[RUN SCRIPT] Executing: {script_name}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        
        success = result.returncode == 0
        
        if success:
            logger.info(f"[RUN SCRIPT] ✓ {script_name} completed successfully")
        else:
            logger.warning(f"[RUN SCRIPT] ⚠ {script_name} exited with code {result.returncode}")
            if result.stderr:
                logger.warning(f"[RUN SCRIPT] stderr: {result.stderr[:500]}")
        
        return {
            "success": success,
            "script": script_name,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"[RUN SCRIPT] ✗ {script_name} timed out after {timeout}s")
        return {
            "success": False,
            "script": script_name,
            "error": f"Timeout after {timeout} seconds",
            "stdout": "",
            "stderr": ""
        }
    except Exception as e:
        logger.error(f"[RUN SCRIPT] ✗ {script_name} failed with exception: {e}")
        return {
            "success": False,
            "script": script_name,
            "error": str(e),
            "stdout": "",
            "stderr": ""
        }


def run_full_sales_pipeline(source_file: Optional[Path] = None, company_id: str = "Acme Corp", branch_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the COMPLETE sales pipeline in DETERMINISTIC order:
    1. Clear all derived outputs (HARD RESET)
    2. Copy source file to canonical location (if provided)
    3. Run EDA (01_eda.py) - creates merged_data.csv, cleaned_dataset.csv
    4. CONDITIONAL: Determine which analyses are available
    5. Run Forecasting (03_forecasting.py) - IF data supports it
    6. Run RFM (04_rfm.py) - IF CustomerID available
    7. Run Recommendations (05_recommendation.py) - IF Product available
    
    =========================================================================
    PROBLEM #4 FIX: Pipeline Rigidity
    =========================================================================
    Previously, all stages ran unconditionally and could fail silently.
    Now, each stage is CONDITIONAL based on data availability.
    Incompatible analyses are SKIPPED with clear logging.
    
    Args:
        source_file: Optional path to uploaded sales file
        
    Returns:
        Dict with execution status for each step
    """
    state = get_pipeline_state()
    
    if state.is_running:
        logger.warning("[SALES PIPELINE] Pipeline already running - aborting")
        return {"success": False, "error": "Pipeline already running"}
    
    state.is_running = True
    state.reset()
    
    logger.info("=" * 70)
    logger.info("[SALES PIPELINE] STARTING FULL SALES PIPELINE (Conditional Execution)")
    logger.info("=" * 70)
    
    results = {
        "success": True,
        "steps": {},
        "skipped_analyses": [],
        "available_analyses": [],
        "timestamp_start": datetime.utcnow().isoformat()
    }
    
    try:
        # Step 1: HARD RESET - Clear all derived outputs first
        logger.info("[SALES PIPELINE] Step 1: HARD RESET derived outputs")
        reset_result = hard_reset_derived_outputs(company_id=company_id, branch_id=branch_id)
        results["steps"]["hard_reset"] = reset_result

        tenant_env = _build_tenant_env(company_id, branch_id)
        
        # Step 2: Copy source file to canonical location (if provided)
        if source_file and source_file.exists():
            logger.info(f"[SALES PIPELINE] Step 2: Copying {source_file.name} -> sales.csv")
            canonical_path = _tenant_data_dir(company_id, branch_id) / "sales.csv"
            shutil.copy2(source_file, canonical_path)
            results["steps"]["copy_file"] = {"success": True, "source": str(source_file)}
        else:
            canonical_path = _tenant_data_dir(company_id, branch_id) / "sales.csv"
            if not canonical_path.exists():
                logger.error("[SALES PIPELINE] No sales.csv found - aborting")
                results["success"] = False
                results["error"] = "No sales data available"
                return results
            results["steps"]["copy_file"] = {"success": True, "source": "existing sales.csv"}
        
        # Step 3: Run EDA (always required)
        logger.info("[SALES PIPELINE] Step 3: Running EDA (01_eda.py)")
        eda_result = run_script("01_eda.py", timeout=120, env=tenant_env)
        results["steps"]["eda"] = eda_result
        if not eda_result["success"]:
            logger.error("[SALES PIPELINE] EDA failed - cannot continue")
            results["success"] = False
            return results
        
        # Step 4: Verify cleaned_dataset.csv was created
        logger.info("[SALES PIPELINE] Step 4: Verifying cleaned_dataset.csv exists")
        cleaned_path = _tenant_data_dir(company_id, branch_id) / "cleaned_dataset.csv"
        if not cleaned_path.exists():
            logger.error("[SALES PIPELINE] cleaned_dataset.csv not created by EDA - aborting")
            results["success"] = False
            results["steps"]["verify_cleaned"] = {"success": False, "error": "cleaned_dataset.csv not found"}
            return results
        results["steps"]["verify_cleaned"] = {"success": True, "file": str(cleaned_path)}
        logger.info("[SALES PIPELINE] ✓ cleaned_dataset.csv verified")
        
        # Step 5: CONDITIONAL ANALYSIS - Determine what's available
        logger.info("[SALES PIPELINE] Step 5: Determining available analyses")
        availability = determine_available_analyses(cleaned_path)
        results["steps"]["availability_check"] = availability
        state.available_analyses = availability
        
        for name, info in availability.items():
            if info["available"]:
                results["available_analyses"].append(name)
                logger.info(f"[AVAILABILITY] ✓ {name}: AVAILABLE")
            else:
                if name not in ["eda"]:  # eda is always run
                    results["skipped_analyses"].append({"name": name, "reason": info["reason"]})
                logger.info(f"[AVAILABILITY] ✗ {name}: SKIPPED - {info['reason']}")
        
        # Step 6: Run Forecasting (CONDITIONAL)
        if availability.get("forecasting", {}).get("available", False):
            logger.info("[SALES PIPELINE] Step 6: Running Forecasting (03_forecasting.py)")
            forecast_result = run_script("03_forecasting.py", timeout=180, env=tenant_env)
            results["steps"]["forecasting"] = forecast_result
            if forecast_result["success"]:
                logger.info("[SALES PIPELINE] ✓ Forecasting completed")
            else:
                logger.warning("[SALES PIPELINE] ⚠ Forecasting failed (non-critical)")
        else:
            reason = availability.get("forecasting", {}).get("reason", "Unknown")
            logger.info(f"[SALES PIPELINE] Step 6: SKIPPING Forecasting - {reason}")
            results["steps"]["forecasting"] = {"skipped": True, "reason": reason}
        
        # Step 7: Run RFM Segmentation (CONDITIONAL - requires CustomerID)
        if availability.get("rfm", {}).get("available", False):
            logger.info("[SALES PIPELINE] Step 7: Running RFM (04_rfm.py)")
            rfm_result = run_script("04_rfm.py", timeout=120, env=tenant_env)
            results["steps"]["rfm"] = rfm_result
            if rfm_result["success"]:
                logger.info("[SALES PIPELINE] ✓ RFM segmentation completed")
            else:
                logger.warning("[SALES PIPELINE] ⚠ RFM failed (non-critical)")
        else:
            reason = availability.get("rfm", {}).get("reason", "Unknown")
            logger.info(f"[SALES PIPELINE] Step 7: SKIPPING RFM - {reason}")
            results["steps"]["rfm"] = {"skipped": True, "reason": reason}
        
        # Step 8: Run Recommendations (CONDITIONAL - requires Product column)
        if availability.get("recommendation", {}).get("available", False):
            logger.info("[SALES PIPELINE] Step 8: Running Recommendations (05_recommendation.py)")
            rec_result = run_script("05_recommendation.py", timeout=180, env=tenant_env)
            results["steps"]["recommendations"] = rec_result
            if rec_result["success"]:
                logger.info("[SALES PIPELINE] ✓ Recommendations completed")
            else:
                logger.warning("[SALES PIPELINE] ⚠ Recommendations failed (non-critical)")
        else:
            reason = availability.get("recommendation", {}).get("reason", "Unknown")
            logger.info(f"[SALES PIPELINE] Step 8: SKIPPING Recommendations - {reason}")
            results["steps"]["recommendations"] = {"skipped": True, "reason": reason}
        
        logger.info("=" * 70)
        logger.info("[SALES PIPELINE] COMPLETED")
        logger.info(f"[SALES PIPELINE] Available: {results['available_analyses']}")
        logger.info(f"[SALES PIPELINE] Skipped: {[s['name'] for s in results['skipped_analyses']]}")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"[SALES PIPELINE] Failed with exception: {e}")
        results["success"] = False
        results["error"] = str(e)
    finally:
        state.is_running = False
        state.last_execution_time = datetime.utcnow()
        state.last_execution_status = results
        results["timestamp_end"] = datetime.utcnow().isoformat()
    
    return results


def run_sentiment_pipeline(source_file: Optional[Path] = None, company_id: str = "Acme Corp", branch_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the Customer Feedback pipeline:
    1. Delete old sentiment_results.csv first
    2. Copy source file to canonical location (if provided)
    3. Run Customer Feedback (06_sentiment.py)
    
    Args:
        source_file: Optional path to uploaded reviews file
        
    Returns:
        Dict with execution status
    """
    logger.info("=" * 70)
    logger.info("[SENTIMENT PIPELINE] STARTING SENTIMENT PIPELINE")
    logger.info("=" * 70)
    
    results = {
        "success": True,
        "steps": {},
        "timestamp_start": datetime.utcnow().isoformat()
    }
    
    try:
        # Step 1: Delete old sentiment results
        logger.info("[SENTIMENT PIPELINE] Step 1: Deleting old sentiment_results.csv")
        tenant_env = _build_tenant_env(company_id, branch_id)
        delete_single_output("sentiment", company_id=company_id, branch_id=branch_id)
        results["steps"]["delete_old"] = {"success": True}
        
        # Step 2: Copy source file to canonical location (if provided)
        if source_file and source_file.exists():
            logger.info(f"[SENTIMENT PIPELINE] Step 2: Copying {source_file.name} -> customer_reviews.csv")
            canonical_path = _tenant_data_dir(company_id, branch_id) / "customer_reviews.csv"
            shutil.copy2(source_file, canonical_path)
            results["steps"]["copy_file"] = {"success": True, "source": str(source_file)}
        else:
            canonical_path = _tenant_data_dir(company_id, branch_id) / "customer_reviews.csv"
            if not canonical_path.exists():
                logger.error("[SENTIMENT PIPELINE] No customer_reviews.csv found - aborting")
                results["success"] = False
                results["error"] = "No reviews data available"
                return results
            results["steps"]["copy_file"] = {"success": True, "source": "existing customer_reviews.csv"}
        
        # Step 3: Run Customer Feedback
        logger.info("[SENTIMENT PIPELINE] Step 3: Running Sentiment (06_sentiment.py)")
        sentiment_result = run_script("06_sentiment.py", timeout=300, env=tenant_env)
        results["steps"]["sentiment"] = sentiment_result
        
        if not sentiment_result["success"]:
            logger.warning("[SENTIMENT PIPELINE] Customer Feedback failed")
            results["success"] = False
        
        logger.info("=" * 70)
        logger.info("[SENTIMENT PIPELINE] COMPLETED")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"[SENTIMENT PIPELINE] Failed with exception: {e}")
        results["success"] = False
        results["error"] = str(e)
    finally:
        results["timestamp_end"] = datetime.utcnow().isoformat()
    
    return results


def run_customers_pipeline(source_file: Optional[Path] = None, company_id: str = "Acme Corp", branch_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle customers upload:
    1. Copy source file to canonical location
    2. If sales.csv exists, re-run full sales pipeline to merge customer data
    
    Args:
        source_file: Optional path to uploaded customers file
        
    Returns:
        Dict with execution status
    """
    logger.info("=" * 70)
    logger.info("[CUSTOMERS PIPELINE] STARTING CUSTOMERS PIPELINE")
    logger.info("=" * 70)
    
    results = {
        "success": True,
        "steps": {},
        "timestamp_start": datetime.utcnow().isoformat()
    }
    
    try:
        # Step 1: Copy source file to canonical location
        if source_file and source_file.exists():
            logger.info(f"[CUSTOMERS PIPELINE] Step 1: Copying {source_file.name} -> customers.csv")
            canonical_path = _tenant_data_dir(company_id, branch_id) / "customers.csv"
            shutil.copy2(source_file, canonical_path)
            results["steps"]["copy_file"] = {"success": True, "source": str(source_file)}
        else:
            logger.error("[CUSTOMERS PIPELINE] No source file provided - aborting")
            results["success"] = False
            results["error"] = "No customers file provided"
            return results
        
        # Step 2: Check if sales.csv exists and re-run pipeline
        sales_path = _tenant_data_dir(company_id, branch_id) / "sales.csv"
        if sales_path.exists():
            logger.info("[CUSTOMERS PIPELINE] Step 2: Sales data exists - re-running full pipeline")
            pipeline_result = run_full_sales_pipeline(company_id=company_id, branch_id=branch_id)
            results["steps"]["rerun_pipeline"] = pipeline_result
        else:
            logger.info("[CUSTOMERS PIPELINE] Step 2: No sales data yet - customers stored, waiting for sales upload")
            results["steps"]["rerun_pipeline"] = {"skipped": True, "reason": "No sales data"}
        
        logger.info("=" * 70)
        logger.info("[CUSTOMERS PIPELINE] COMPLETED")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"[CUSTOMERS PIPELINE] Failed with exception: {e}")
        results["success"] = False
        results["error"] = str(e)
    finally:
        results["timestamp_end"] = datetime.utcnow().isoformat()
    
    return results


# ============================================================================
# Main Entry Point
# ============================================================================

def orchestrate_pipeline(
    dataset_type: str,
    action: str,
    file_path: Optional[Path] = None,
    company_id: str = "Acme Corp",
    branch_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    MAIN ENTRY POINT - Orchestrate pipeline execution based on event.
    
    This is the SINGLE SOURCE OF TRUTH for all pipeline operations.
    
    Args:
        dataset_type: One of 'sales', 'customers', 'reviews'
        action: One of 'upload', 'replace', 'delete'
        file_path: Optional path to the data file
        
    Returns:
        Dict with complete execution results
    """
    logger.info("=" * 70)
    logger.info("[ORCHESTRATE] Pipeline Orchestration Request")
    logger.info(f"[ORCHESTRATE] Dataset: {dataset_type}")
    logger.info(f"[ORCHESTRATE] Action: {action}")
    logger.info(f"[ORCHESTRATE] File: {file_path}")
    logger.info(f"[ORCHESTRATE] Tenant: {company_id} / {branch_id or 'GLOBAL'}")
    logger.info("=" * 70)
    
    result = {
        "dataset_type": dataset_type,
        "action": action,
        "file_path": str(file_path) if file_path else None,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Handle DELETE action
    if action == "delete":
        result["execution"] = detect_data_deletion(dataset_type)
        return result
    
    # Handle UPLOAD/REPLACE actions
    if action in ["upload", "replace"]:
        if dataset_type == "sales":
            result["execution"] = run_full_sales_pipeline(file_path, company_id=company_id, branch_id=branch_id)
        elif dataset_type == "reviews":
            result["execution"] = run_sentiment_pipeline(file_path, company_id=company_id, branch_id=branch_id)
        elif dataset_type == "customers":
            result["execution"] = run_customers_pipeline(file_path, company_id=company_id, branch_id=branch_id)
        else:
            result["execution"] = {"error": f"Unknown dataset type: {dataset_type}"}
    else:
        result["execution"] = {"error": f"Unknown action: {action}"}
    
    return result


# ============================================================================
# Standalone Execution
# ============================================================================

if __name__ == "__main__":
    """
    Standalone execution for testing.
    
    Usage:
        python pipeline_controller.py sales upload /path/to/sales.csv
        python pipeline_controller.py reviews upload /path/to/reviews.csv
        python pipeline_controller.py sales delete
    """
    import json
    
    if len(sys.argv) < 3:
        print("Usage: python pipeline_controller.py <dataset_type> <action> [file_path]")
        print("  dataset_type: sales, customers, reviews")
        print("  action: upload, replace, delete")
        print("  file_path: (optional) path to data file")
        sys.exit(1)
    
    dataset_type = sys.argv[1]
    action = sys.argv[2]
    file_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    
    result = orchestrate_pipeline(dataset_type, action, file_path)
    print(json.dumps(result, indent=2, default=str))
