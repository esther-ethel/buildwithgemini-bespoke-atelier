"""Seed script to populate Firestore with initial sewing patterns."""

from google.cloud import firestore

# Hardcode GCP Project ID explicitly (do NOT use GOOGLE_CLOUD_PROJECT or google.auth.default())
FIRESTORE_PROJECT = "qwiklabs-gcp-03-7d5352e0a1dc"


SEED_PATTERNS = [
    {
        "pattern_id": "old-money-waistcoat",
        "name": "Old Money Tailored Waistcoat",
        "aesthetic": "Old Money",
        "difficulty": "Intermediate",
        "recommended_fabrics": ["Wool Tweed", "Linen-Cotton Blend", "Worst Wool", "Heavy Suit Linen"],
        "yardage_estimate": "1.75 yards (60 inch width)",
        "base_measurements": {
            "bust": 36.0,
            "waist": 28.0,
            "hip": 38.0,
            "back_length": 16.5,
            "unit": "inches"
        },
        "description": "Structured v-neck tailored vest featuring front welt pockets, back cinching tie, and princess seam shaping."
    },
    {
        "pattern_id": "vintage-1950s-circle-skirt",
        "name": "1950s Full Circle Skirt Dress",
        "aesthetic": "Vintage 1950s",
        "difficulty": "Beginner-Friendly",
        "recommended_fabrics": ["Cotton Poplin", "Taffeta", "Polished Cotton", "Gingham Broadcloth"],
        "yardage_estimate": "4.5 yards (44 inch width)",
        "base_measurements": {
            "bust": 35.0,
            "waist": 26.5,
            "hip": 37.0,
            "skirt_length": 28.0,
            "unit": "inches"
        },
        "description": "Mid-century classic silhouette featuring a fitted boatneck bodice, full 360-degree circle skirt, and deep side seam pockets."
    },
    {
        "pattern_id": "cottagecore-milkmaid-dress",
        "name": "Cottagecore Tiered Milkmaid Dress",
        "aesthetic": "Cottagecore",
        "difficulty": "Intermediate",
        "recommended_fabrics": ["Linen Voile", "Gathered Cotton Lawn", "Rayon Crepe", "Embroidered Eyelet"],
        "yardage_estimate": "3.8 yards (54 inch width)",
        "base_measurements": {
            "bust": 34.0,
            "waist": 27.0,
            "hip": 38.0,
            "bodice_height": 13.0,
            "unit": "inches"
        },
        "description": "Romantic prairie style with elasticated puff sleeves, gathered drawstring milkmaid bust cups, and a flowing tiered midi skirt."
    },
    {
        "pattern_id": "minimalist-wide-leg-trousers",
        "name": "Minimalist High-Waisted Wide-Leg Trousers",
        "aesthetic": "Minimalist",
        "difficulty": "Advanced",
        "recommended_fabrics": ["Heavy Linen", "Wool Crepe", "Tencel Twill", "Cotton Gabardine"],
        "yardage_estimate": "2.75 yards (58 inch width)",
        "base_measurements": {
            "waist": 28.0,
            "hip": 39.0,
            "inseam": 31.0,
            "crotch_depth": 11.5,
            "unit": "inches"
        },
        "description": "Clean Architectural high-waisted trousers with front double pleats, concealed fly zip, slant side pockets, and wide straight leg."
    }
]


def seed_database():
    db = firestore.Client(project=FIRESTORE_PROJECT)
    print(f"Connected to Firestore project: {db.project}")
    patterns_ref = db.collection("patterns")
    
    for pattern in SEED_PATTERNS:
        doc_id = pattern["pattern_id"]
        patterns_ref.document(doc_id).set(pattern)
        print(f"Seeded pattern doc '{doc_id}': {pattern['name']}")

    print("Firestore seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
