"""
Phase 6: Sentiment Analysis - NLP-Based Customer Review Analysis

Purpose:
    Analyze customer sentiment from reviews to support business decision-making.
    
Why TextBlob/VADER for Sentiment Analysis:
    1. Lightweight & Interpretable: No deep learning complexity
    2. Domain-Agnostic: Works well for general review text
    3. Fast Processing: Ideal for real-time dashboards
    4. Explainable: Clear polarity/subjectivity scores
    5. Production-Ready: Battle-tested in production systems
    
Business Value:
    - Monitor customer satisfaction trends over time
    - Identify problem areas (negative feedback clusters)
    - Segment customers by sentiment for targeted marketing
    - Track impact of product/service changes on sentiment
    - Early warning system for customer churn risk
    
Technical Approach:
    - TextBlob for polarity analysis (sentiment classification)
    - VADER for social media/informal text (more robust)
    - Text preprocessing: normalization, tokenization, stop words
    - Sentiment aggregation: per-customer, temporal, global
"""

import sys
import logging
import re
from pathlib import Path
from typing import Tuple, Dict, List, Any

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from textblob import TextBlob

# Import VADER for comparison
try:
    from nltk.sentiment import SentimentIntensityAnalyzer
    vader_available = True
except ImportError:
    vader_available = False
    import warnings
    warnings.warn("VADER not available; using TextBlob only")

# -------------------------------------------------
# Paths & Logging Setup
# -------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"

LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'sentiment_analysis.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# -------------------------------------------------
# Text Preprocessing Functions
# -------------------------------------------------
def clean_text(text: str) -> str:
    """
    Clean and normalize text for sentiment analysis.
    
    Steps:
    1. Convert to lowercase
    2. Remove URLs
    3. Remove special characters (keep letters, numbers, spaces)
    4. Remove extra whitespace
    5. Remove emojis
    
    Args:
        text: Raw review text
        
    Returns:
        Cleaned text suitable for sentiment analysis
    """
    if not isinstance(text, str) or len(text) == 0:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Keep alphanumeric, spaces, and basic punctuation (important for sentiment)
    text = re.sub(r'[^a-zA-Z0-9\s\.\!\?\,\']', '', text)
    
    return text


def preprocess_reviews(df: pd.DataFrame, text_column: str = "ReviewText") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Preprocess all reviews in dataframe with data quality tracking.
    
    Args:
        df: Dataframe with review text
        text_column: Name of column containing review text
        
    Returns:
        Tuple of (processed_dataframe, quality_metrics)
        
    Raises:
        ValueError: If no valid reviews remain after preprocessing
    """
    logger.info(f"Preprocessing {len(df)} reviews...")
    
    quality_metrics = {
        "original_count": len(df),
        "empty_before_clean": 0,
        "removed_after_clean": 0,
        "final_count": 0
    }
    
    # Check for empty reviews
    quality_metrics["empty_before_clean"] = df[text_column].isna().sum() + (df[text_column].str.len() == 0).sum()
    if quality_metrics["empty_before_clean"] > 0:
        logger.warning(f"Found {quality_metrics['empty_before_clean']} empty/null reviews")
    
    # Clean text
    df["CleanedText"] = df[text_column].fillna("").apply(clean_text)
    
    # Remove rows with empty cleaned text
    before = len(df)
    df = df[df["CleanedText"].str.len() > 3].copy()  # Require minimum 3 chars
    quality_metrics["removed_after_clean"] = before - len(df)
    quality_metrics["final_count"] = len(df)
    
    if quality_metrics["removed_after_clean"] > 0:
        logger.warning(f"Removed {quality_metrics['removed_after_clean']} reviews with insufficient text after cleaning")
    
    if len(df) == 0:
        raise ValueError("No valid reviews remaining after preprocessing")
    
    logger.info(f"Successfully preprocessed {len(df)} reviews (quality: {len(df)/quality_metrics['original_count']*100:.1f}%)")
    return df, quality_metrics


# -------------------------------------------------
# Sentiment Analysis Functions
# -------------------------------------------------
def analyze_sentiment_textblob(text: str) -> Tuple[float, str, float, float]:
    """
    Analyze sentiment using TextBlob (polarity-based approach).
    
    TextBlob Polarity Scale: -1.0 (most negative) to +1.0 (most positive)
    TextBlob Subjectivity Scale: 0.0 (objective) to 1.0 (subjective)
    Interpretation:
        - [-1.0, -0.1): Negative
        - [-0.1, 0.1): Neutral
        - [0.1, 1.0]: Positive
    
    Args:
        text: Cleaned review text
        
    Returns:
        Tuple of (polarity_score, sentiment_label, subjectivity_score, confidence_score)
    """
    if not text or len(text) == 0:
        return 0.0, "Neutral", 0.0, 0.0
    
    try:
        blob = TextBlob(text)
        polarity = round(blob.sentiment.polarity, 4)
        subjectivity = round(blob.sentiment.subjectivity, 4)
        
        # Classify based on polarity
        if polarity > 0.1:
            label = "Positive"
        elif polarity < -0.1:
            label = "Negative"
        else:
            label = "Neutral"
        
        # Confidence: based on distance from neutral threshold
        confidence = round(abs(polarity) * (1 - abs(0.5 - subjectivity)), 4)
        
        return polarity, label, subjectivity, confidence
        
    except Exception as e:
        logger.warning(f"Error analyzing sentiment for text '{text[:50]}...': {str(e)[:100]}")
        return 0.0, "Neutral", 0.0, 0.0


def analyze_sentiment_vader(text: str) -> Tuple[float, str, float]:
    """
    Analyze sentiment using VADER (social media/informal text).
    
    VADER Compound Score: -1.0 (most negative) to +1.0 (most positive)
    More robust for:
    - Sarcasm detection
    - Informal language (abbreviations, slang)
    - Emojis and punctuation emphasis
    
    Args:
        text: Cleaned review text
        
    Returns:
        Tuple of (compound_score, sentiment_label, confidence_score)
    """
    if not vader_available or not text or len(text) == 0:
        return 0.0, "Neutral", 0.0
    
    try:
        sia = SentimentIntensityAnalyzer()
        scores = sia.polarity_scores(text)
        compound = round(scores['compound'], 4)
        
        # Classify based on compound score
        if compound >= 0.05:
            label = "Positive"
        elif compound <= -0.05:
            label = "Negative"
        else:
            label = "Neutral"
        
        # Confidence: max of positive, negative, neutral proportions
        confidence = round(max(scores['pos'], scores['neg'], scores['neu']), 4)
        
        return compound, label, confidence
        
    except Exception as e:
        logger.debug(f"VADER unavailable for text: {str(e)[:100]}")
        return 0.0, "Neutral", 0.0


def compute_sentiment_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute sentiment scores for all reviews using TextBlob (primary method).
    
    Also computes VADER if available for comparison/robustness.
    Includes subjectivity and confidence scores.
    
    Args:
        df: Dataframe with CleanedText column
        
    Returns:
        Dataframe with sentiment columns added
    """
    logger.info("Computing sentiment scores...")
    
    # TextBlob analysis (primary)
    results = df["CleanedText"].apply(analyze_sentiment_textblob)
    df["SentimentScore"] = results.apply(lambda x: x[0])
    df["SentimentLabel"] = results.apply(lambda x: x[1])
    df["Subjectivity"] = results.apply(lambda x: x[2])
    df["TextBlobConfidence"] = results.apply(lambda x: x[3])
    
    # VADER analysis (optional, for robustness)
    if vader_available:
        logger.info("Computing VADER scores for comparison...")
        results_vader = df["CleanedText"].apply(analyze_sentiment_vader)
        df["VADERScore"] = results_vader.apply(lambda x: x[0])
        df["VADERLabel"] = results_vader.apply(lambda x: x[1])
        df["VADERConfidence"] = results_vader.apply(lambda x: x[2])
    
    logger.info(f"Sentiment computation completed for {len(df)} reviews")
    return df


def compute_sentiment_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute comprehensive summary statistics for sentiment analysis.
    
    Args:
        df: Dataframe with sentiment columns
        
    Returns:
        Dictionary with statistics including quality metrics
        
    Raises:
        ValueError: If dataframe is empty or missing required columns
    """
    logger.info("Computing sentiment statistics...")
    
    if len(df) == 0 or "SentimentLabel" not in df.columns:
        raise ValueError("Invalid dataframe for statistics computation")
    
    total_reviews = len(df)
    
    # Sentiment distribution
    sentiment_counts = df["SentimentLabel"].value_counts().to_dict()
    sentiment_pct = df["SentimentLabel"].value_counts(normalize=True).to_dict()
    
    # Score statistics with proper formatting
    try:
        score_stats = {
            "mean": float(df["SentimentScore"].mean()),
            "median": float(df["SentimentScore"].median()),
            "std": float(df["SentimentScore"].std()),
            "min": float(df["SentimentScore"].min()),
            "max": float(df["SentimentScore"].max())
        }
    except Exception as e:
        logger.warning(f"Error computing score statistics: {e}")
        score_stats = {"mean": 0.0, "median": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    
    # Subjectivity statistics
    try:
        subjectivity_stats = {
            "mean": float(df["Subjectivity"].mean()),
            "max": float(df["Subjectivity"].max())
        }
    except Exception:
        subjectivity_stats = {"mean": 0.0, "max": 0.0}
    
    # Per-customer sentiment (if CustomerID available)
    customer_sentiment = {}
    if "CustomerID" in df.columns:
        try:
            grouped = df.groupby("CustomerID").agg({
                "SentimentScore": ["mean", "count"],
                "SentimentLabel": lambda x: x.mode()[0] if len(x.mode()) > 0 else "Neutral"
            })
            customer_sentiment = {
                "customer_count": len(grouped),
                "avg_reviews_per_customer": float(grouped[("SentimentScore", "count")].mean())
            }
        except Exception as e:
            logger.debug(f"Error computing customer sentiment: {e}")
    
    stats = {
        "total_reviews": total_reviews,
        "sentiment_counts": sentiment_counts,
        "sentiment_pct": sentiment_pct,
        "score_statistics": score_stats,
        "subjectivity_statistics": subjectivity_stats,
        "customer_sentiment": customer_sentiment
    }
    
    return stats


# -------------------------------------------------
# Visualization Functions
# -------------------------------------------------
def plot_sentiment_distribution(df: pd.DataFrame, plots_dir: Path) -> None:
    """
    Create professional visualizations for sentiment analysis results.
    
    Args:
        df: Dataframe with sentiment columns
        plots_dir: Directory to save plots
        
    Raises:
        ValueError: If dataframe missing required sentiment columns
    """
    logger.info("Generating sentiment visualizations...")
    
    if "SentimentLabel" not in df.columns:
        raise ValueError("Missing SentimentLabel column")
    
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # 1. Sentiment Label Distribution (Pie Chart)
    fig, ax = plt.subplots(figsize=(10, 7))
    sentiment_counts = df["SentimentLabel"].value_counts()
    colors = {'Positive': '#6A994E', 'Neutral': '#F2CC8F', 'Negative': '#D62828'}
    color_list = [colors.get(label, '#999999') for label in sentiment_counts.index]
    
    wedges, texts, autotexts = ax.pie(
        sentiment_counts.values,
        labels=sentiment_counts.index,
        autopct='%1.1f%%',
        colors=color_list,
        explode=(0.05, 0.05, 0.05),
        startangle=90,
        textprops={'fontsize': 11, 'fontweight': 'bold'}
    )
    ax.set_title("Sentiment Distribution\n(Customer Reviews)", fontsize=13, fontweight='bold', pad=20)
    plt.tight_layout()
    plot_path = plots_dir / "sentiment_distribution.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Sentiment distribution pie chart saved to {plot_path}")
    
    # 2. Sentiment Score Distribution (Histogram)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(df["SentimentScore"], bins=30, color='#2E86AB', edgecolor='black', alpha=0.7)
    ax.axvline(df["SentimentScore"].mean(), color='#A23B72', linestyle='--', linewidth=2, label=f'Mean: {df["SentimentScore"].mean():.3f}')
    ax.axvline(df["SentimentScore"].median(), color='#F18F01', linestyle='--', linewidth=2, label=f'Median: {df["SentimentScore"].median():.3f}')
    ax.set_xlabel("Sentiment Score", fontsize=11, fontweight='bold')
    ax.set_ylabel("Frequency", fontsize=11, fontweight='bold')
    ax.set_title("Sentiment Score Distribution\n(TextBlob Polarity)", fontsize=13, fontweight='bold', pad=20)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plot_path = plots_dir / "sentiment_score_histogram.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Sentiment score histogram saved to {plot_path}")
    
    # 3. Sentiment by Count (Bar Chart)
    fig, ax = plt.subplots(figsize=(10, 6))
    sentiment_counts = df["SentimentLabel"].value_counts()
    bars = ax.bar(
        sentiment_counts.index,
        sentiment_counts.values,
        color=[colors.get(label, '#999999') for label in sentiment_counts.index],
        edgecolor='black',
        alpha=0.8,
        width=0.6
    )
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax.set_ylabel("Number of Reviews", fontsize=11, fontweight='bold')
    ax.set_title("Review Count by Sentiment", fontsize=13, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plot_path = plots_dir / "sentiment_count_bar.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Sentiment count bar chart saved to {plot_path}")


def print_sentiment_summary(stats: Dict[str, Any]) -> None:
    """
    Print comprehensive sentiment analysis summary to console and logs.
    
    Args:
        stats: Sentiment statistics dictionary
    """
    logger.info("" + "=" * 70)
    logger.info("SENTIMENT ANALYSIS SUMMARY")
    logger.info("=" * 70)
    
    logger.info(f"\nTotal Reviews Analyzed: {stats['total_reviews']}")
    
    logger.info("\n--- SENTIMENT DISTRIBUTION ---")
    for sentiment, count in stats['sentiment_counts'].items():
        pct = stats['sentiment_pct'].get(sentiment, 0) * 100
        logger.info(f"  {sentiment:12s}: {count:3d} reviews ({pct:5.1f}%)")
    
    logger.info("\n--- SCORE STATISTICS (TextBlob Polarity Scale: -1 to +1) ---")
    score_stats = stats['score_statistics']
    logger.info(f"  Mean:     {score_stats.get('mean', 0.0):7.4f}")
    logger.info(f"  Median:   {score_stats.get('median', 0.0):7.4f}")
    logger.info(f"  Std Dev:  {score_stats.get('std', 0.0):7.4f}")
    logger.info(f"  Range:    [{score_stats.get('min', 0.0):.4f}, {score_stats.get('max', 0.0):.4f}]")
    
    logger.info("\n--- SUBJECTIVITY STATISTICS (Scale: 0=Objective to 1=Subjective) ---")
    subj_stats = stats.get('subjectivity_statistics', {})
    logger.info(f"  Mean:     {subj_stats.get('mean', 0.0):7.4f}")
    logger.info(f"  Max:      {subj_stats.get('max', 0.0):7.4f}")
    
    if stats.get('customer_sentiment'):
        logger.info("\n--- CUSTOMER SENTIMENT ---")
        cust_stats = stats['customer_sentiment']
        logger.info(f"  Unique Customers: {cust_stats.get('customer_count', 0)}")
        logger.info(f"  Avg Reviews/Customer: {cust_stats.get('avg_reviews_per_customer', 0):.2f}")
    
    logger.info("\n" + "=" * 70)


# -------------------------------------------------
# Main Functions
# -------------------------------------------------
def load_and_validate_data(input_path: Path) -> pd.DataFrame:
    """
    Load and validate customer reviews dataset.
    
    OPTIONAL FILE: reviews.csv or customer_reviews.csv
    Returns None if file not found (graceful degradation).
    
    Args:
        input_path: Path to reviews CSV file
        
    Returns:
        Validated dataframe or None if file missing
    """
    logger.info("=" * 60)
    logger.info("SENTIMENT ANALYSIS - DATA VALIDATION")
    logger.info("=" * 60)
    
    # Try multiple possible filenames
    possible_paths = [
        input_path,
        DATA_DIR / "reviews.csv",
        DATA_DIR / "customer_reviews.csv"
    ]
    
    df = None
    found_path = None
    for path in possible_paths:
        if path.exists():
            found_path = path
            break
    
    if found_path is None:
        logger.warning("=" * 60)
        logger.warning("⊘ SENTIMENT ANALYSIS SKIPPED")
        logger.warning("⊘ Reason: No review files found")
        logger.warning(f"⊘ Searched for: customer_reviews.csv, reviews.csv")
        logger.warning("⊘ Solution: Upload reviews.csv with ReviewText column")
        logger.warning("=" * 60)
        return None
    
    try:
        df = pd.read_csv(found_path)
        logger.info(f"✓ Found {len(df)} review records in {found_path.name}")
    except Exception as e:
        logger.warning(f"⚠ Failed to load {found_path}: {e}")
        return None
    
    # Find text column (try common names)
    text_column = None
    for col_name in ["ReviewText", "review_text", "Review", "text", "Text", "comment", "Comment"]:
        if col_name in df.columns:
            text_column = col_name
            break
    
    if text_column is None:
        logger.warning("=" * 60)
        logger.warning("⊘ SENTIMENT ANALYSIS SKIPPED")
        logger.warning("⊘ Reason: No text column found in reviews file")
        logger.warning(f"⊘ Available columns: {list(df.columns)}")
        logger.warning("⊘ Expected: ReviewText, review_text, Review, text, or comment")
        logger.warning("=" * 60)
        return None
    
    # Rename to standard column name
    if text_column != "ReviewText":
        df.rename(columns={text_column: "ReviewText"}, inplace=True)
        logger.info(f"✓ Renamed '{text_column}' to 'ReviewText'")
    
    # Check for empty reviews
    empty_count = df["ReviewText"].isna().sum()
    if empty_count > 0:
        logger.warning(f"⚠ Found {empty_count} empty reviews (will be filtered)")
    
    # Remove empty reviews
    df = df.dropna(subset=["ReviewText"])
    df = df[df["ReviewText"].str.strip().str.len() > 0]
    
    if len(df) == 0:
        logger.warning("=" * 60)
        logger.warning("⊘ SENTIMENT ANALYSIS SKIPPED")
        logger.warning("⊘ Reason: No valid review text after filtering")
        logger.warning("=" * 60)
        return None
    
    logger.info(f"✓ Validated {len(df)} reviews for sentiment analysis")
    logger.info("=" * 60)
    return df
    """
    Load and validate customer reviews dataset.
    
    Args:
        input_path: Path to customer_reviews.csv
        
    Returns:
        Validated dataframe
        
    Raises:
        FileNotFoundError: If input file not found
        ValueError: If required columns missing
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Review file not found: {input_path}")
    
    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} reviews from {input_path}")
    
    # Validate required columns
    required_cols = ["ReviewText"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    if len(df) == 0:
        raise ValueError("Dataset is empty")
    
    logger.info(f"Validated {len(df)} reviews for sentiment analysis")
    return df


def save_sentiment_results(df: pd.DataFrame, output_path: Path) -> None:
    """
    Save sentiment analysis results to CSV with comprehensive columns.
    
    Args:
        df: Dataframe with sentiment columns
        output_path: Output file path
        
    Raises:
        IOError: If file write fails
    """
    try:
        # Define columns in priority order
        cols_to_save = ["ReviewID", "CustomerID", "ReviewDate", "ReviewText", 
                        "CleanedText", "SentimentScore", "SentimentLabel", 
                        "Subjectivity", "TextBlobConfidence"]
        if "VADERScore" in df.columns:
            cols_to_save.extend(["VADERScore", "VADERLabel", "VADERConfidence"])
        
        # Keep only available columns
        cols_to_save = [c for c in cols_to_save if c in df.columns]
        
        # Save with proper formatting
        df[cols_to_save].to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Sentiment results saved to {output_path} ({len(df)} reviews, {len(cols_to_save)} columns)")
        
    except IOError as e:
        logger.error(f"Failed to save sentiment results: {e}")
        raise


def main() -> None:
    """
    Main execution pipeline for Phase 6: Sentiment Analysis.
    
    Pipeline:
        1. Load and validate customer reviews
        2. Preprocess text (clean, normalize, validate)
        3. Analyze sentiment with TextBlob + optional VADER
        4. Compute comprehensive statistics
        5. Generate professional visualizations
        6. Save results with quality metrics
    """
    try:
        logger.info("=" * 60)
        logger.info("PHASE 6: SENTIMENT ANALYSIS STARTED")
        logger.info("=" * 60)
        
        # Step 1: Load and validate data
        logger.info("\n[STEP 1/5] Loading and validating reviews...")
        input_path = DATA_DIR / "customer_reviews.csv"
        df = load_and_validate_data(input_path)
        
        # If no reviews available, skip sentiment analysis gracefully
        if df is None:
            logger.info("Sentiment Analysis skipped - exiting gracefully")
            sys.exit(0)  # Exit with success (not a failure)
        
        logger.info(f"  Status: Loaded {len(df)} reviews")
        
        # Step 2: Preprocess reviews
        logger.info("\n[STEP 2/5] Preprocessing and cleaning text...")
        df, quality_metrics = preprocess_reviews(df, text_column="ReviewText")
        logger.info(f"  Status: {quality_metrics['final_count']} valid reviews")
        
        # Step 3: Compute sentiment scores
        logger.info("\n[STEP 3/5] Analyzing sentiment...")
        df = compute_sentiment_scores(df)
        logger.info(f"  Status: Sentiment analysis complete")
        
        # Step 4: Compute statistics
        logger.info("\n[STEP 4/5] Computing statistics...")
        stats = compute_sentiment_statistics(df)
        print_sentiment_summary(stats)
        
        # Step 5: Generate visualizations
        logger.info("\n[STEP 5/5] Generating visualizations...")
        plot_sentiment_distribution(df, PLOTS_DIR)
        logger.info(f"  Status: Generated 3 visualizations")
        
        # Save results
        output_path = DATA_DIR / "sentiment_results.csv"
        save_sentiment_results(df, output_path)
        
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 6: SENTIMENT ANALYSIS COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"\nOutputs:")
        logger.info(f"  - Results: {output_path}")
        logger.info(f"  - Logs:    {LOGS_DIR / 'sentiment_analysis.log'}")
        logger.info(f"  - Plots:   {PLOTS_DIR}/")
        
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
