import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import random

# Create sample customer reviews dataset
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "Sales_Intelligence_Project" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

reviews_data = {
    "ReviewID": [f"R{i+1:03d}" for i in range(20)],
    "CustomerID": [f"C{random.randint(1, 5):03d}" for _ in range(20)],
    "ReviewText": [
        "This product is absolutely amazing! Exceeded all my expectations. Highly recommended!",
        "Good quality, but shipping took longer than expected.",
        "Terrible! Product broke after one week. Very disappointed.",
        "It's okay. Nothing special, but does the job.",
        "Excellent customer service and fast delivery. Very happy with purchase!",
        "Waste of money. Doesn't work as advertised.",
        "Average product. Could be better for the price.",
        "Love it! Best purchase I've made this year!",
        "Not bad, but there are better alternatives available.",
        "Absolutely horrible experience. Will never buy again.",
        "Pretty good! Meets expectations and good value.",
        "Fantastic! Exactly what I was looking for.",
        "Meh. It's just a regular product, nothing impressive.",
        "Outstanding quality and professional support!",
        "Defective unit received. Returned it immediately.",
        "Very satisfied with this purchase. Definitely recommend!",
        "Poor quality for the price. Expected much better.",
        "Excellent product! Fast shipping and great packaging!",
        "Mediocre at best. Disappointed with quality.",
        "Fantastic experience! Will definitely buy again soon!"
    ],
    "ReviewDate": [
        (datetime.now() - timedelta(days=random.randint(1, 90))).strftime('%Y-%m-%d')
        for _ in range(20)
    ]
}

df = pd.DataFrame(reviews_data)
df.to_csv(DATA_DIR / "customer_reviews.csv", index=False)
print(f"Created sample reviews file with {len(df)} reviews")
print(f"Saved to: {DATA_DIR / 'customer_reviews.csv'}")
