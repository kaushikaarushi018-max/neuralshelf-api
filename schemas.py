from pydantic import BaseModel, Field
from typing import List, Optional

class RecommendationItem(BaseModel):
    product_id:       str
    predicted_rating: float
    rank:             int

class RecommendationResponse(BaseModel):
    user_id:            str
    model:              str
    ab_group:           str
    recommendations:    List[RecommendationItem]
    count:              int
    response_time_ms:   float
    generated_at:       str

class FeedbackRequest(BaseModel):
    user_id:    str
    product_id: str
    rating:     float = Field(ge=1.0, le=5.0)

class HealthResponse(BaseModel):
    status:        str
    timestamp:     str
    version:       str
    models_loaded: bool
