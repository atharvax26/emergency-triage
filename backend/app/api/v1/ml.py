"""ML prediction endpoints."""

import httpx
import logging
import os
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ml"])

# ML service URL and API key
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8001")
ML_API_KEY = os.getenv("ML_API_KEY", "system-key-789")


class VitalSigns(BaseModel):
    """Vital signs data."""
    systolic_bp: float = Field(..., ge=50, le=250)
    diastolic_bp: float = Field(..., ge=30, le=150)
    heart_rate: float = Field(..., ge=20, le=250)
    respiratory_rate: float = Field(..., ge=5, le=60)
    temperature: float = Field(..., ge=32.0, le=43.0)
    spo2: float = Field(..., ge=50, le=100)


class PatientData(BaseModel):
    """Patient data for prediction."""
    vitals: VitalSigns
    age: int = Field(..., ge=0, le=120)
    symptoms: Optional[list[str]] = None


class TriagePredictionRequest(BaseModel):
    """Triage prediction request."""
    patient_data: PatientData
    request_id: Optional[str] = None


class TriagePredictionResponse(BaseModel):
    """Triage prediction response."""
    raw_probability: float
    calibrated_probability: float
    risk_tier: str
    decision_label: str
    confidence: float
    safety_override: bool
    override_reason: Optional[str] = None
    model_version: str
    model_id: str
    inference_time_ms: float
    timestamp: str
    request_id: Optional[str] = None
    cache_hit: Optional[bool] = False


@router.post("/triage/predict", response_model=TriagePredictionResponse)
async def predict_triage(
    request: TriagePredictionRequest
):
    """
    Predict triage severity and risk tier using AI.
    
    Note: Authentication temporarily disabled for testing.
    """
    try:
        # Call ML inference service with 500ms timeout constraint
        async with httpx.AsyncClient(timeout=0.5) as client:
            response = await client.post(
                f"{ML_SERVICE_URL}/v1/predict",
                json=request.model_dump(),
                headers={"X-API-Key": ML_API_KEY}
            )
            response.raise_for_status()
            
        prediction = response.json()
        
        logger.info(
            f"Triage prediction: "
            f"risk_tier={prediction['risk_tier']}, "
            f"confidence={prediction['confidence']:.3f}"
        )
        
        return prediction
        
    except httpx.TimeoutException:
        logger.error("ML service timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ML service timeout - prediction took too long"
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"ML service error: {e.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ML service error: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"ML service connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML service unavailable - cannot connect"
        )
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.get("/health")
async def ml_health_check():
    """Check ML service health."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{ML_SERVICE_URL}/v1/health/liveness",
                headers={"X-API-Key": ML_API_KEY}
            )
            response.raise_for_status()
            
        return {
            "status": "healthy",
            "ml_service": "connected"
        }
    except Exception as e:
        logger.error(f"ML health check failed: {e}")
        return {
            "status": "unhealthy",
            "ml_service": "disconnected",
            "error": str(e)
        }
