from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PHQ9ResultSchema(BaseModel):
    id: int
    total_score: int
    severity: str
    created_at: datetime
    
    # Síntomas individuales
    q1_interest: int
    q2_depressed: int
    q3_sleep: int
    q4_energy: int
    q5_appetite: int
    q6_failure: int
    q7_concentration: int
    q8_movement: int
    q9_suicide: int
    
    class Config:
        from_attributes = True


class DepressionDetectionSchema(BaseModel):
    id: int
    is_depressive: bool
    confidence_score: float
    risk_level: str
    detected_keywords: Optional[List[str]]
    detected_at: datetime
    
    class Config:
        from_attributes = True


class MentalHealthSummarySchema(BaseModel):
    # PHQ-9
    latest_phq9_score: Optional[int]
    latest_phq9_severity: Optional[str]
    latest_phq9_date: Optional[datetime]
    total_phq9_assessments: int
    
    # Detecciones
    depression_detection_count: int
    last_detection_date: Optional[datetime]
    high_risk_detections: int
    
    # Estado general
    overall_risk_level: str
    requires_attention: bool
    
    class Config:
        from_attributes = True
