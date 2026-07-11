from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Any = None


def ok(message: str, data: Any = None) -> dict:
    return {"success": True, "message": message, "data": data}
