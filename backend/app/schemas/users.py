from typing import List, Optional
"""User-account DTOs."""
from pydantic import BaseModel

__all__ = ["DistrictAdminCreateIn"]


class DistrictAdminCreateIn(BaseModel):
    name: str
    mobile_no: str
    password: str
    # The first entry is the primary district. district_id is still accepted on its own so
    # any existing caller keeps working.
    district_id: Optional[str] = None
    district_ids: List[str] = []
    designation_id: Optional[str] = None
