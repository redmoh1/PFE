"""
Sales Intelligence Project - Phase 6: Customer Sentiment Analysis
NLP-based analysis of customer reviews using TextBlob.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from textblob import TextBlob

# -------------------------------------------------
# Paths & Logging
# -------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
LOGS_DIR = BASE_DIR / "logs"

OUTPUT_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "sentiment_analysis.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# -------------------------------------------------
# Text Column Detection
# -------------------------------------------------
TEXT_CANDIDATES = ["ReviewText", "review_text", "Review", "text", "Text", "comment", "Comment", "feedback", "Feedback"]
RATING_CANDIDATES = ["Rating", "rating", "Score", "score", "Stars", "stars"]


def find_text_column(df: pd.DataFrame) -> Optional[str]:
    """Find the text column in the dataframe."""
    for col in TEXT_CANDIDATES:
        if col in df.columns:
            return col
    return None


def find_rating_column(df: pd.DataFrame) -> Optional[str]:
    """Find the rating column in the dataframe."""
    for col in RATING_CANDIDATES:
        if col in df.columns:
            return col
    return None


# -------------------------------------------------
# Sentiment Analysis
# -------------------------------------------------
def analyze_sentiment(text: str) -> Dict:
    """
    Analyze sentiment of a single text using TextBlob.
    
    Returns:
        Dict with polarity, subjectivity, and sentiment label
    """
    if pd.isna(text) or not str(text).strip():
        return {
            "polarity": 0.0,
            "subjectivity": 0.0,
            "sentiment": "Neutral",
            "keywords": ""
        }
    
    try:
        blob = TextBlob(str(text))
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Classify sentiment
        if polarity > 0.1:
            sentiment = "Positive"
        elif polarity < -0.1:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
        
        # Extract keywords (nouns from the text)
        keywords = [word for word, tag in blob.tags if tag.startswith('NN')][:5]
        keywords_str = ", ".join(keywords) if keywords else ""
        
        return {
            "polarity": round(polarity, 4),
            "subjectivity": round(subjectivity, 4),
            "sentiment": sentiment,
            "keywords": keywords_str
        }
    except Exception as e:
        logger.warning(f"Error analyzing text: {e}")
        return {
            "polarity": 0.0,
            "subjectivity": 0.0,
            "sentiment": "Neutral",
            "keywords": ""
        }


def process_reviews(df: pd.DataFrame, text_col: str) -> pd.DataFrame:
    """
    Process all reviews and add sentiment columns.
    """
    logger.info(f"Analyzing sentiment for {len(df)} reviews...")
    
    results = []
    for idx, row in df.iterrows():
        text = row[text_col]
        sentiment_data = analyze_sentiment(text)
        results.append(sentiment_data)
    
    # Add sentiment columns
    df = df.copy()
    df["Polarity"] = [r["polarity"] for r in results]
    df["Subjectivity"] = [r["subjectivity"] for r in results]
    df["Sentiment"] = [r["sentiment"] for r in results]
    df["Keywords"] = [r["keywords"] for r in results]
    
    return df


def generate_summary(df: pd.DataFrame) -> Dict:
    """
    Generate sentiment summary statistics.
    """
    sentiment_counts = df["Sentiment"].value_counts().to_dict()
    total = len(df)
    
    summary = {
        "total_reviews": total,
        "positive_count": sentiment_counts.get("Positive", 0),
        "neutral_count": sentiment_counts.get("Neutral", 0),
        "negative_count": sentiment_counts.get("Negative", 0),
        "positive_pct": round(sentiment_counts.get("Positive", 0) / total * 100, 2) if total > 0 else 0,
        "neutral_pct": round(sentiment_counts.get("Neutral", 0) / total * 100, 2) if total > 0 else 0,
        "negative_pct": round(sentiment_counts.get("Negative", 0) / total * 100, 2) if total > 0 else 0,
        "avg_polarity": round(df["Polarity"].mean(), 4) if not df.empty else 0,
        "avg_subjectivity": round(df["Subjectivity"].mean(), 4) if not df.empty else 0,
    }
    
    return summary


def generate_visualizations(df: pd.DataFrame, summary: Dict):
    """
    Generate sentiment analysis visualizations.
    """
    try:
        import matplotlib.pyplot as plt
        
        # Sentiment Distribution Pie Chart
        sentiment_counts = df["Sentiment"].value_counts()
        
        if len(sentiment_counts) > 0:
            colors = {
                "Positive": "#22c55e",
                "Neutral": "#94a3b8", 
                "Negative": "#ef4444"
            }
            
            fig, axes = plt.subplots(1, 2, figsize=(14, 6))
            
            # Pie chart
            pie_colors = [colors.get(s, "#94a3b8") for s in sentiment_counts.index]
            explode = [0.05] * len(sentiment_counts)
            
            axes[0].pie(
                sentiment_counts.values,
                labels=sentiment_counts.index,
                autopct='%1.1f%%',
                colors=pie_colors,
                explode=explode,
                startangle=90
            )
            axes[0].set_title("Sentiment Distribution", fontsize=14, fontweight='bold')
            
            # Polarity histogram
            axes[1].hist(df["Polarity"], bins=20, color='#2563eb', edgecolor='white', alpha=0.7)
            axes[1].axvline(x=0, color='#ef4444', linestyle='--', linewidth=2, label='Neutral')
            axes[1].set_xlabel("Polarity Score")
            axes[1].set_ylabel("Frequency")
            axes[1].set_title("Polarity Distribution", fontsize=14, fontweight='bold')
            axes[1].legend()
            
            plt.tight_layout()
            plt.savefig(PLOTS_DIR / "sentiment_analysis.png", dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Sentiment visualization saved to {PLOTS_DIR / 'sentiment_analysis.png'}")
            
    except Exception as e:
        logger.warning(f"Failed to generate visualizations: {e}")


def main():
    """Main sentiment analysis pipeline."""
    try:
        logger.info("=" * 70)
        logger.info("Phase 6: Customer Sentiment Analysis")
        logger.info("=" * 70)
        
        # Find reviews file
        reviews_path = DATA_DIR / "customer_reviews.csv"
        
        if not reviews_path.exists():
            logger.error(f"Reviews file not found: {reviews_path}")
            sys.exit(1)
        
        # Load reviews
        df = pd.read_csv(reviews_path)
        logger.info(f"Loaded {len(df)} reviews from {reviews_path}")
        
        # Find text column
        text_col = find_text_column(df)
        if not text_col:
            logger.error("No text column found in reviews file")
            logger.error(f"Expected one of: {TEXT_CANDIDATES}")
            sys.exit(1)
        
        logger.info(f"Using text column: {text_col}")
        
        # Process reviews
        df = process_reviews(df, text_col)
        
        # Generate summary
        summary = generate_summary(df)
        
        logger.info("\n--- SENTIMENT SUMMARY ---")
        logger.info(f"Total Reviews: {summary['total_reviews']}")
        logger.info(f"Positive: {summary['positive_count']} ({summary['positive_pct']}%)")
        logger.info(f"Neutral: {summary['neutral_count']} ({summary['neutral_pct']}%)")
        logger.info(f"Negative: {summary['negative_count']} ({summary['negative_pct']}%)")
        logger.info(f"Average Polarity: {summary['avg_polarity']}")
        logger.info(f"Average Subjectivity: {summary['avg_subjectivity']}")
        
        # Generate visualizations
        generate_visualizations(df, summary)
        
        # Save results
        output_path = DATA_DIR / "sentiment_results.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"\nSentiment results saved to {output_path} ({len(df)} reviews, {len(df.columns)} columns)")
        
        logger.info("=" * 70)
        logger.info("Phase 6: Sentiment Analysis Completed Successfully")
        logger.info("=" * 70)
        logger.info(f"\nOutputs:")
        logger.info(f"  - Results: {output_path}")
        logger.info(f"  - Plots:   {PLOTS_DIR}/")
        
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
