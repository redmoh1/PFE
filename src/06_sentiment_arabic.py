"""
Sales Intelligence Project - Phase 6: Arabic-Aware Customer Feedback
Upgraded with HuggingFace Transformers for Arabic NLP

WHY THIS UPGRADE:
- TextBlob is English-centric and inaccurate for Arabic
- Arabic requires:
  * Proper tokenization (handles diacritics, morphology)
  * Pre-trained Arabic models (AraBERT, CAMeL)
  * Right-to-left text handling

APPROACH:
1. Primary: HuggingFace Arabic sentiment model (aubmindlab/bert-base-arabertv02-twitter)
2. Fallback: TextBlob (for non-Arabic or if model unavailable)
3. Confidence scores for all predictions
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
import warnings

import pandas as pd
from textblob import TextBlob

# HuggingFace Transformers for Arabic
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers not available. Install with: pip install transformers torch")

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
        logging.FileHandler(LOGS_DIR / "sentiment_arabic.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Suppress transformers warnings
warnings.filterwarnings("ignore", category=UserWarning)

# -------------------------------------------------
# Column Detection
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


def is_arabic(text: str) -> bool:
    """Detect if text contains Arabic characters."""
    if not text or not isinstance(text, str):
        return False
    # Arabic Unicode range: \u0600-\u06FF
    arabic_chars = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
    return arabic_chars > len(text) * 0.3  # At least 30% Arabic


# -------------------------------------------------
# Arabic Customer Feedback (Production)
# -------------------------------------------------
class ArabicSentimentAnalyzer:
    """Production-grade Arabic sentiment analyzer using HuggingFace models."""
    
    def __init__(self, model_name: str = "CAMeL-Lab/bert-base-arabic-camelbert-msa-sentiment"):
        """Initialize Arabic sentiment analyzer.
        
        Recommended models:
        - CAMeL-Lab/bert-base-arabic-camelbert-msa-sentiment (Modern Standard Arabic)
        - aubmindlab/bert-base-arabertv02-twitter (Dialectal Arabic, social media)
        - CAMeL-Lab/bert-base-arabic-camelbert-da-sentiment (Dialectal Arabic)
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Transformers not installed. Run: pip install transformers torch")
        
        self.model_name = model_name
        logger.info(f"Loading Arabic sentiment model: {model_name}")
        
        try:
            # Load model with caching
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=model_name,
                tokenizer=model_name,
                device=0 if torch.cuda.is_available() else -1,  # GPU if available
                top_k=None,  # Return all scores
            )
            logger.info(f"Arabic model loaded successfully (device: {'GPU' if torch.cuda.is_available() else 'CPU'})")
        except Exception as e:
            logger.error(f"Failed to load Arabic model: {e}")
            raise
    
    def analyze(self, text: str) -> Dict:
        """Analyze sentiment of Arabic text with confidence scores.
        
        Returns:
            Dict with sentiment label, confidence, and polarity score
        """
        if pd.isna(text) or not str(text).strip():
            return {
                "sentiment": "Neutral",
                "confidence": 0.0,
                "polarity": 0.0,
                "method": "empty",
            }
        
        text = str(text).strip()
        
        try:
            # Get predictions with confidence scores
            results = self.sentiment_pipeline(text[:512])  # Limit to 512 tokens
            
            # Handle different model output formats
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], list):
                    # Multi-label output: [{'label': 'positive', 'score': 0.9}, ...]
                    results = results[0]
                
                # Find the prediction with highest confidence
                best_pred = max(results, key=lambda x: x['score'])
                label = best_pred['label'].lower()
                confidence = float(best_pred['score'])
                
                # Normalize label to Positive/Negative/Neutral
                if 'pos' in label or label == 'label_2':
                    sentiment = "Positive"
                    polarity = confidence
                elif 'neg' in label or label == 'label_0':
                    sentiment = "Negative"
                    polarity = -confidence
                else:
                    sentiment = "Neutral"
                    polarity = 0.0
                
                return {
                    "sentiment": sentiment,
                    "confidence": round(confidence, 4),
                    "polarity": round(polarity, 4),
                    "method": "arabic_bert",
                }
            else:
                # Fallback
                return {
                    "sentiment": "Neutral",
                    "confidence": 0.0,
                    "polarity": 0.0,
                    "method": "error",
                }
        
        except Exception as e:
            logger.warning(f"Arabic Customer Feedback failed: {e}")
            return {
                "sentiment": "Neutral",
                "confidence": 0.0,
                "polarity": 0.0,
                "method": "error",
            }


# -------------------------------------------------
# Fallback: TextBlob (English/General)
# -------------------------------------------------
def analyze_sentiment_textblob(text: str) -> Dict:
    """Fallback Customer Feedback using TextBlob (for English text)."""
    if pd.isna(text) or not str(text).strip():
        return {
            "sentiment": "Neutral",
            "confidence": 0.0,
            "polarity": 0.0,
            "subjectivity": 0.0,
            "method": "empty",
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
        
        # Confidence approximation (TextBlob doesn't provide this)
        confidence = min(abs(polarity), 1.0)
        
        return {
            "sentiment": sentiment,
            "confidence": round(confidence, 4),
            "polarity": round(polarity, 4),
            "subjectivity": round(subjectivity, 4),
            "method": "textblob",
        }
    except Exception as e:
        logger.warning(f"TextBlob analysis failed: {e}")
        return {
            "sentiment": "Neutral",
            "confidence": 0.0,
            "polarity": 0.0,
            "subjectivity": 0.0,
            "method": "error",
        }


# -------------------------------------------------
# Unified Customer Feedback
# -------------------------------------------------
class UnifiedSentimentAnalyzer:
    """Intelligent sentiment analyzer that chooses the right method based on language."""
    
    def __init__(self):
        self.arabic_analyzer = None
        if TRANSFORMERS_AVAILABLE:
            try:
                self.arabic_analyzer = ArabicSentimentAnalyzer()
                logger.info("Arabic sentiment analyzer initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Arabic analyzer: {e}")
                logger.warning("Falling back to TextBlob only")
        else:
            logger.warning("Transformers not available. Using TextBlob only.")
    
    def analyze(self, text: str) -> Dict:
        """Analyze sentiment with automatic language detection.
        
        Chooses Arabic model for Arabic text, TextBlob for English.
        """
        if pd.isna(text) or not str(text).strip():
            return {
                "sentiment": "Neutral",
                "confidence": 0.0,
                "polarity": 0.0,
                "method": "empty",
            }
        
        text = str(text).strip()
        
        # Language detection
        if is_arabic(text) and self.arabic_analyzer:
            return self.arabic_analyzer.analyze(text)
        else:
            return analyze_sentiment_textblob(text)


# -------------------------------------------------
# Batch Processing
# -------------------------------------------------
def analyze_reviews(company_name: str, use_arabic_model: bool = True) -> pd.DataFrame:
    """Analyze sentiment for all reviews of a company.
    
    Args:
        company_name: Company name (for file path)
        use_arabic_model: Whether to use Arabic model (True) or TextBlob only (False)
        
    Returns:
        DataFrame with Customer Feedback results
    """
    reviews_dir = DATA_DIR / company_name / "reviews"
    
    # Find reviews file
    review_files = list(reviews_dir.glob("*reviews*.csv"))
    if not review_files:
        raise FileNotFoundError(f"No reviews file found in {reviews_dir}")
    
    reviews_path = review_files[0]
    logger.info(f"Loading reviews from {reviews_path}")
    
    df = pd.read_csv(reviews_path)
    logger.info(f"Loaded {len(df)} reviews")
    
    # Find text column
    text_col = find_text_column(df)
    if not text_col:
        raise ValueError(f"No text column found. Expected one of: {TEXT_CANDIDATES}")
    
    # Initialize analyzer
    if use_arabic_model:
        analyzer = UnifiedSentimentAnalyzer()
        logger.info("Using unified analyzer (Arabic + TextBlob)")
    else:
        analyzer = None
        logger.info("Using TextBlob only")
    
    # Analyze each review
    results = []
    for idx, text in enumerate(df[text_col]):
        if idx % 100 == 0 and idx > 0:
            logger.info(f"Processed {idx}/{len(df)} reviews")
        
        if analyzer:
            result = analyzer.analyze(text)
        else:
            result = analyze_sentiment_textblob(text)
        
        results.append(result)
    
    # Add results to dataframe
    df["sentiment"] = [r["sentiment"] for r in results]
    df["confidence"] = [r["confidence"] for r in results]
    df["polarity"] = [r["polarity"] for r in results]
    df["analysis_method"] = [r["method"] for r in results]
    
    logger.info(f"Customer Feedback complete. Method distribution:")
    logger.info(df["analysis_method"].value_counts().to_dict())
    
    # Save results
    output_path = OUTPUT_DIR / f"{company_name}_sentiment_analysis.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"Results saved to {output_path}")
    
    # Generate summary
    summary = {
        "total_reviews": len(df),
        "sentiment_distribution": df["sentiment"].value_counts().to_dict(),
        "average_confidence": float(df["confidence"].mean()),
        "average_polarity": float(df["polarity"].mean()),
        "methods_used": df["analysis_method"].value_counts().to_dict(),
    }
    
    logger.info("Sentiment Summary:")
    for key, value in summary.items():
        logger.info(f"  {key}: {value}")
    
    return df


# -------------------------------------------------
# Main Execution
# -------------------------------------------------
if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else "Acme Corp"
    use_arabic = sys.argv[2].lower() != "false" if len(sys.argv) > 2 else True
    
    logger.info(f"Starting Customer Feedback for {company}")
    logger.info(f"Arabic model enabled: {use_arabic}")
    
    try:
        results_df = analyze_reviews(company, use_arabic)
        
        print("\n" + "="*70)
        print("Customer Feedback COMPLETE")
        print("="*70)
        print(f"Total Reviews: {len(results_df)}")
        print("\nSentiment Distribution:")
        for sentiment, count in results_df["sentiment"].value_counts().items():
            percentage = (count / len(results_df)) * 100
            print(f"  {sentiment}: {count} ({percentage:.1f}%)")
        print(f"\nAverage Confidence: {results_df['confidence'].mean():.2%}")
        print(f"Average Polarity: {results_df['polarity'].mean():.4f}")
        print("\nMethods Used:")
        for method, count in results_df["analysis_method"].value_counts().items():
            print(f"  {method}: {count}")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"Customer Feedback failed: {e}", exc_info=True)
        sys.exit(1)
