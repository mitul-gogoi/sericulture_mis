"""Land + GPS request DTOs."""
from typing import List, Optional, Dict
from pydantic import BaseModel

__all__ = ["LandDetailIn", "LandIn", "GpsSubmitIn", "GpsVerifyIn"]


class LandDetailIn(BaseModel):
    dag_no: Optional[str] = ""
    patta_no: Optional[str] = ""
    land_type: Optional[str] = "Owned"


class LandIn(LandDetailIn):
    farmer_id: str


class GpsSubmitIn(BaseModel):
    farmer_land_id: str
    points: List[Dict[str, float]]


class GpsVerifyIn(BaseModel):
    farmer_land_id: str
    decision: str
    reason: Optional[str] = ""
    override_overlap: bool = False
