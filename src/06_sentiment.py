"""
Sales Intelligence Project - Phase 6: Customer Sentiment Analysis
NLP-based analysis of customer reviews.

=============================================================================
PROBLEM #2 FIX: Hard-Coded Column Assumptions
=============================================================================
This module now uses the Schema Resolver (when available) to auto-detect
column names, making it work with different data schemas.

=============================================================================
PROBLEM #4 FIX: Pipeline Rigidity  
=============================================================================
Sentiment Analysis REQUIRES review text. If the dataset doesn't have text
reviews, this analysis will gracefully skip.
The pipeline controller checks for REVIEW_TEXT availability before calling
this module.
=============================================================================

Supports:
- English text using TextBlob
- Arabic text detection with fallback to keyword-based sentiment

LIMITATION: TextBlob does not support Arabic. For production Arabic NLP, consider:
- CAMeL Tools (https://github.com/CAMeL-Lab/camel_tools)
- AraBERT via HuggingFace transformers
- ArabicSentiment (pip install arabic-sentiment)
"""

import logging
import sys
import re
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
# Schema Resolver Integration
# -------------------------------------------------
try:
    from schema_resolver import SchemaResolver, SemanticField, can_perform_analysis
    SCHEMA_RESOLVER_AVAILABLE = True
    logger.info("Schema Resolver loaded successfully")
except ImportError:
    SCHEMA_RESOLVER_AVAILABLE = False
    logger.warning("Schema Resolver not available - using fallback column detection")


def resolve_sentiment_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Resolve required columns for sentiment analysis.
    
    Sentiment Analysis requires:
    - review_text column (REVIEW_TEXT) - for text analysis
    - rating column (RATING) - optional, for validation
    
    Returns dict with resolved column names or None if not found.
    """
    if SCHEMA_RESOLVER_AVAILABLE:
        resolver = SchemaResolver()
        result = resolver.resolve(df, "reviews")
        
        return {
            "text": result.get_column(SemanticField.REVIEW_TEXT),
            "rating": result.get_column(SemanticField.RATING)
        }
    else:
        # Fallback detection
        text_candidates = ["ReviewText", "review_text", "Review", "text", "Text", "comment", "Comment", "feedback", "Feedback"]
        rating_candidates = ["Rating", "rating", "Score", "score", "Stars", "stars"]
        
        text_col = next((c for c in text_candidates if c in df.columns), None)
        rating_col = next((c for c in rating_candidates if c in df.columns), None)
        
        return {"text": text_col, "rating": rating_col}


# -------------------------------------------------
# Language Detection
# -------------------------------------------------
# Arabic Unicode range: \u0600-\u06FF (Arabic), \u0750-\u077F (Arabic Supplement)
ARABIC_PATTERN = re.compile(r'[\u0600-\u06FF\u0750-\u077F]')

# Common Arabic sentiment keywords (basic lexicon)
ARABIC_POSITIVE_WORDS = [
    'ممتاز', 'رائع', 'جيد', 'حلو', 'جميل', 'مذهل', 'عظيم', 'أحب', 'سعيد', 'شكرا',
    'مبدع', 'متميز', 'افضل', 'أفضل', 'محترم', 'راضي', 'سريع', 'مريح', 'نظيف'
]
ARABIC_NEGATIVE_WORDS = [
    'سيء', 'رديء', 'سيئ', 'فظيع', 'مقرف', 'بطيء', 'غالي', 'مشكلة', 'خراب', 'كذب',
    'نصب', 'احتيال', 'زفت', 'وسخ', 'متأخر', 'خسارة', 'ضعيف', 'محبط', 'زعلان'
]


def is_arabic(text: str) -> bool:
    """Check if text contains Arabic characters."""
    if not text:
        return False
    arabic_chars = len(ARABIC_PATTERN.findall(text))
    return arabic_chars > len(text) * 0.3  # >30% Arabic chars


def detect_language(text: str) -> str:
    """Detect language of text (simplified: Arabic vs English)."""
    if is_arabic(text):
        return "arabic"
    return "english"


# -------------------------------------------------
# Text Column Detection (Legacy - now uses resolve_sentiment_columns)
# -------------------------------------------------
TEXT_CANDIDATES = ["ReviewText", "review_text", "Review", "text", "Text", "comment", "Comment", "feedback", "Feedback"]
RATING_CANDIDATES = ["Rating", "rating", "Score", "score", "Stars", "stars"]


def find_text_column(df: pd.DataFrame) -> Optional[str]:
    """Find the text column in the dataframe."""
    resolved = resolve_sentiment_columns(df)
    if resolved.get("text"):
        return resolved["text"]
    # Legacy fallback
    for col in TEXT_CANDIDATES:
        if col in df.columns:
            return col
    return None


def find_rating_column(df: pd.DataFrame) -> Optional[str]:
    """Find the rating column in the dataframe."""
    resolved = resolve_sentiment_columns(df)
    if resolved.get("rating"):
        return resolved["rating"]
    # Legacy fallback
    for col in RATING_CANDIDATES:
        if col in df.columns:
            return col
    return None


import re

# -------------------------------------------------
# Language Detection
# -------------------------------------------------
def detect_language(text: str) -> str:
    """
    Simple language detection based on character ranges.
    
    Returns:
        'ar' for Arabic, 'en' for English/other
    """
    if not text or not str(text).strip():
        return 'en'
    
    text_str = str(text)
    # Arabic Unicode range: \u0600-\u06FF (Arabic), \u0750-\u077F (Arabic Supplement)
    arabic_chars = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F]', text_str))
    total_chars = len(re.findall(r'\w', text_str))
    
    if total_chars == 0:
        return 'en'
    
    # If more than 30% Arabic characters, consider it Arabic
    if arabic_chars / total_chars > 0.3:
        return 'ar'
    return 'en'


# -------------------------------------------------
# Sentiment Analysis
# -------------------------------------------------

# Arabic sentiment words (common positive/negative terms)
ARABIC_POSITIVE = {
    'ممتاز', 'رائع', 'جيد', 'جميل', 'سعيد', 'أحب', 'أعجبني', 'مذهل', 'عظيم', 'مميز',
    'أفضل', 'إيجابي', 'نظيف', 'سريع', 'محترف', 'شكرا', 'ممتازة', 'رائعة', 'جيدة'
}
ARABIC_NEGATIVE = {
    'سيء', 'سيئ', 'سيئة', 'فظيع', 'كره', 'لا أحب', 'مشكلة', 'سلبي', 'بطيء', 'غالي',
    'خطأ', 'مكسور', 'ضعيف', 'فشل', 'أسوأ', 'رديء', 'قبيح', 'مزعج', 'محبط'
}

# -------------------------------------------------
# English Sentiment Lexicon (No external dependencies)
# -------------------------------------------------
ENGLISH_POSITIVE = {
    'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'awesome',
    'love', 'loved', 'loving', 'like', 'liked', 'best', 'better', 'beautiful',
    'happy', 'glad', 'pleased', 'satisfied', 'perfect', 'nice', 'brilliant',
    'outstanding', 'superb', 'incredible', 'impressive', 'exceptional', 'positive',
    'recommend', 'recommended', 'helpful', 'useful', 'easy', 'fast', 'quick',
    'friendly', 'professional', 'quality', 'reliable', 'efficient', 'comfortable',
    'pleasant', 'enjoy', 'enjoyed', 'enjoying', 'delicious', 'tasty', 'fresh',
    'clean', 'smooth', 'well', 'worth', 'affordable', 'reasonable', 'fair',
    'thank', 'thanks', 'grateful', 'appreciate', 'appreciated', 'value', 'valuable'
}

ENGLISH_NEGATIVE = {
    'bad', 'terrible', 'horrible', 'awful', 'poor', 'worst', 'worse', 'hate',
    'hated', 'hating', 'dislike', 'disappointed', 'disappointing', 'disappointment',
    'angry', 'annoyed', 'annoying', 'frustrating', 'frustrated', 'frustration',
    'problem', 'problems', 'issue', 'issues', 'broken', 'defective', 'faulty',
    'slow', 'delayed', 'late', 'wrong', 'error', 'mistake', 'fail', 'failed',
    'failure', 'useless', 'waste', 'wasted', 'overpriced', 'expensive', 'cheap',
    'rude', 'unprofessional', 'incompetent', 'unreliable', 'difficult', 'hard',
    'confusing', 'complicated', 'dirty', 'ugly', 'uncomfortable', 'unpleasant',
    'never', 'nothing', 'nobody', 'nowhere', 'neither', 'nor', 'no', 'not',
    'refund', 'return', 'complaint', 'complain', 'regret', 'sorry', 'unfortunately'
}

INTENSIFIERS = {'very', 'really', 'extremely', 'absolutely', 'totally', 'completely', 'highly', 'super'}
NEGATORS = {'not', "n't", 'no', 'never', 'neither', 'nobody', 'nothing', 'nowhere'}


def analyze_arabic_sentiment(text: str) -> Dict:
    """
    Analyze sentiment for Arabic text using keyword-based approach.
    
    NOTE: For production, consider using:
    - CAMeL Tools (https://camel-tools.readthedocs.io/)
    - AraBERT via HuggingFace transformers
    - Azure Cognitive Services Arabic sentiment
    
    Current implementation uses simple keyword matching as a baseline.
    """
    if pd.isna(text) or not str(text).strip():
        return {
            "polarity": 0.0,
            "subjectivity": 0.5,
            "sentiment": "Neutral",
            "keywords": "",
            "language": "ar"
        }
    
    text_str = str(text).strip()
    words = set(re.findall(r'[\u0600-\u06FF]+', text_str))
    
    pos_count = len(words & ARABIC_POSITIVE)
    neg_count = len(words & ARABIC_NEGATIVE)
    total_sentiment_words = pos_count + neg_count
    
    if total_sentiment_words == 0:
        polarity = 0.0
        sentiment = "Neutral"
    else:
        # Simple polarity calculation
        polarity = (pos_count - neg_count) / total_sentiment_words
        if polarity > 0.1:
            sentiment = "Positive"
        elif polarity < -0.1:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
    
    # Extract Arabic keywords (first 5 words)
    keywords = list(words)[:5]
    keywords_str = ", ".join(keywords) if keywords else ""
    
    return {
        "polarity": round(polarity, 4),
        "subjectivity": 0.5,  # Cannot determine subjectivity with keyword approach
        "sentiment": sentiment,
        "keywords": keywords_str,
        "language": "ar"
    }


def analyze_sentiment(text: str) -> Dict:
    """
    Analyze sentiment of a single text using TextBlob.
    
    Automatically detects language and uses appropriate analyzer:
    - English/Latin: TextBlob
    - Arabic: Keyword-based approach
    
    Returns:
        Dict with polarity, subjectivity, sentiment label, and detected language
    """
    if pd.isna(text) or not str(text).strip():
        return {
            "polarity": 0.0,
            "subjectivity": 0.0,
            "sentiment": "Neutral",
            "keywords": "",
            "language": "unknown"
        }
    
    # Detect language
    lang = detect_language(text)
    
    if lang == 'ar':
        return analyze_arabic_sentiment(text)
    
    # English: use TextBlob
    try:
        blob = TextBlob(str(text))
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Classify sentiment based on polarity
        if polarity > 0.1:
            sentiment = "Positive"
        elif polarity < -0.1:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
        
        # Extract keywords (nouns and adjectives)
        try:
            keywords = [word for word, tag in blob.tags if tag in ('NN', 'NNS', 'JJ', 'JJR', 'JJS')][:5]
            keywords_str = ", ".join(keywords) if keywords else ""
        except:
            # Fallback if POS tagging fails
            words = str(text).split()
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                          'it', 'to', 'for', 'of', 'in', 'on', 'with', 'this', 'that', 'i'}
            keywords = [w.strip('.,!?";:()[]') for w in words 
                        if len(w) > 3 and w.lower() not in stop_words][:5]
            keywords_str = ", ".join(keywords) if keywords else ""
        
        return {
            "polarity": round(polarity, 4),
            "subjectivity": round(subjectivity, 4),
            "sentiment": sentiment,
            "keywords": keywords_str,
            "language": "en"
        }
    except Exception as e:
        logger.warning(f"Error analyzing text: {e}")
        return {
            "polarity": 0.0,
            "subjectivity": 0.0,
            "sentiment": "Neutral",
            "keywords": "",
            "language": "unknown"
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
