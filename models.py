import joblib
import numpy as np
import pandas as pd

_svd_model  = None
_mappings   = None
_reviews_df = None

# Models are in the same folder as the app
MODEL_DIR = "/app"

def load_models():
    global _svd_model, _mappings, _reviews_df

    print("  Loading SVD model...")
    _svd_model = joblib.load(f"{MODEL_DIR}/model_svd.pkl")
    print("  ✓ SVD loaded")

    print("  Loading mappings...")
    _mappings = joblib.load(f"{MODEL_DIR}/neuralshelf_mappings.pkl")
    print("  ✓ Mappings loaded")

    print("  Loading reviews from MySQL...")
    from database import get_engine
    engine = get_engine()
    _reviews_df = pd.read_sql(
        "SELECT user_id, product_id, user_idx, product_idx, rating FROM reviews",
        engine
    )
    print(f"  ✓ {len(_reviews_df):,} reviews loaded")


def get_svd_recommendations(user_id: str, n: int = 10) -> pd.DataFrame:
    if _svd_model is None:
        raise Exception("Models not loaded")

    reviewed     = set(_reviews_df[_reviews_df["user_id"] == user_id]["product_id"])
    all_products = set(_reviews_df["product_id"].unique())
    unreviewed   = all_products - reviewed

    if not unreviewed:
        return pd.DataFrame()

    predictions = []
    for product_id in unreviewed:
        pred = _svd_model.predict(user_id, product_id)
        predictions.append({
            "product_id":       product_id,
            "predicted_rating": pred.est,
        })

    recs = pd.DataFrame(predictions)
    return recs.sort_values(
        "predicted_rating", ascending=False
    ).head(n).reset_index(drop=True)


def get_ncf_recommendations(user_id: str, n: int = 10) -> pd.DataFrame:
    # NCF not available in cloud deployment
    # SVD is the production model (better RMSE: 1.10 vs 1.16)
    return get_svd_recommendations(user_id, n)
