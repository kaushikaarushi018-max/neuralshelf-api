from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional
import pandas as pd
import time

from database import get_engine
from models import load_models, get_svd_recommendations, get_ncf_recommendations
from schemas import RecommendationResponse, RecommendationItem, FeedbackRequest, HealthResponse
from sqlalchemy import text

app = FastAPI(
    title="NeuralShelf Recommendation API",
    description="Production-grade recommendation engine using SVD and Neural CF",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("NeuralShelf API starting up...")
    load_models()
    print("✓ All models loaded and ready!")
    print("✓ Docs at http://localhost:8002/docs")

@app.get("/")
async def root():
    return {
        "message": "Welcome to NeuralShelf Recommendation API!",
        "version": "1.0.0",
        "docs":    "http://localhost:8002/docs",
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        models_loaded=True
    )

@app.get("/recommendations/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(
    user_id:  str,
    n:        int = Query(default=10, ge=1, le=50),
    model:    str = Query(default="svd"),
    ab_group: Optional[str] = Query(default=None)
):
    start_time = time.time()

    if ab_group == "A":
        model = "svd"
    elif ab_group == "B":
        model = "ncf"

    try:
        if model.lower() == "svd":
            recs = get_svd_recommendations(user_id, n)
        elif model.lower() == "ncf":
            recs = get_ncf_recommendations(user_id, n)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown model '{model}'")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    if recs.empty:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")

    items = [
        RecommendationItem(
            product_id=row["product_id"],
            predicted_rating=round(float(row["predicted_rating"]), 4),
            rank=i + 1,
        )
        for i, (_, row) in enumerate(recs.iterrows())
    ]

    return RecommendationResponse(
        user_id=user_id,
        model=model.upper(),
        ab_group=ab_group or ("A" if model == "svd" else "B"),
        recommendations=items,
        count=len(items),
        response_time_ms=round((time.time() - start_time) * 1000, 2),
        generated_at=datetime.now().isoformat(),
    )

@app.get("/models/performance")
async def get_model_performance():
    engine = get_engine()
    df = pd.read_sql("""
        SELECT model_name, metric_name, metric_value
        FROM model_performance
        ORDER BY model_name, metric_name
    """, engine)

    if df.empty:
        return {"message": "No performance data found"}

    result = {}
    for model_name in df["model_name"].unique():
        model_df = df[df["model_name"] == model_name]
        result[model_name] = {
            row["metric_name"]: round(row["metric_value"], 4)
            for _, row in model_df.iterrows()
        }
    return {"models": result, "retrieved_at": datetime.now().isoformat()}

@app.get("/ab-test/results")
async def get_ab_test_results():
    engine = get_engine()
    df = pd.read_sql(
        "SELECT * FROM ab_test_results ORDER BY run_at DESC",
        engine
    )
    if df.empty:
        return {"message": "No A/B test results found"}
    return {
        "tests": df.to_dict(orient="records"),
        "retrieved_at": datetime.now().isoformat()
    }

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO reviews
                (user_id, product_id, user_idx, product_idx, rating)
            SELECT :user_id, :product_id, u.user_idx, p.product_idx, :rating
            FROM users u, products p
            WHERE u.user_id = :user_id
              AND p.product_id = :product_id
            LIMIT 1
        """), {
            "user_id":    feedback.user_id,
            "product_id": feedback.product_id,
            "rating":     feedback.rating,
        })
        conn.commit()
    return {
        "message":   "Feedback received!",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/products/popular")
async def get_popular_products(n: int = Query(default=10, ge=1, le=50)):
    engine = get_engine()
    df = pd.read_sql(f"""
        SELECT product_id,
               COUNT(*) AS review_count,
               ROUND(AVG(rating), 2) AS avg_rating
        FROM reviews
        GROUP BY product_id
        ORDER BY review_count DESC
        LIMIT {n}
    """, engine)
    return {
        "popular_products": df.to_dict(orient="records"),
        "count": len(df)
    }
