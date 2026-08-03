from pydantic import BaseModel, field_validator
from typing import Optional, Literal


class TeamCreate(BaseModel):
    name: str


class TeamUpdate(BaseModel):
    name: Optional[str] = None


class TeamMemberAdd(BaseModel):
    email: str  # Changed from user_id to email
    role: Literal["Owner", "Admin", "Editor", "Viewer"] = "Viewer"

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError("Valid email address is required")
        return v

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        valid_roles = ["Owner", "Admin", "Editor", "Viewer"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}")
        return v


class TeamMemberUpdate(BaseModel):
    role: Literal["Owner", "Admin", "Editor", "Viewer"]

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        valid_roles = ["Owner", "Admin", "Editor", "Viewer"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}")
        return v


class TeamResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    created_at: Optional[str] = None
    members: list[dict] = []


class TeamMemberResponse(BaseModel):
    id: str
    team_id: str
    user_id: str
    role: str
    joined_at: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
