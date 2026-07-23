"""User-account DTOs."""
from pydantic import BaseModel

__all__ = ["DistrictAdminCreateIn"]


class DistrictAdminCreateIn(BaseModel):
    name: str
    mobile_no: str
    password: str
    district_id: str
