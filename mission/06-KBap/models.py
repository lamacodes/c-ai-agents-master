from pydantic import BaseModel
from typing import Optional


class UserAccountContext(BaseModel):

    customer_id: int
    name: str
    tier: str = "basic"
    email: Optional[str] = None  # premium entreprise

class InputGuardRailOutput(BaseModel):

    is_off_topic: bool
    reason: str

class OutputGuardRailOutput(BaseModel):

    contains_off_topic: bool
    contains_reservation_data: bool
    contains_menu_data: bool
    contains_order_data: bool
    reason: str


class HandoffData(BaseModel):

    to_agent_name: str
    issue_type: str
    issue_description: str
    reason: str