"""
Settings API. Lets the frontend (web app or desktop app, both use the same
endpoints) check which secrets are configured and save new ones — WITHOUT ever
exposing the real value back over the API once it has been saved.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.secrets import set_secret, is_secret_configured

router = APIRouter(prefix="/api/settings", tags=["settings"])

# The list of keys this app allows to be configured through the Settings screen.
MANAGED_KEYS = ["GEMINI_API_KEY"]


class SettingUpdate(BaseModel):
    key: str
    value: str


@router.get("/status")
def get_settings_status():
    """Returns True/False per managed key. NEVER returns the actual secret value."""
    return {key: is_secret_configured(key) for key in MANAGED_KEYS}


@router.post("")
def update_setting(payload: SettingUpdate):
    """Saves a new value for one managed key. Write-only: the response confirms
    it was saved, but does not echo the value back."""
    if payload.key not in MANAGED_KEYS:
        return {"error": f"'{payload.key}' is not a configurable setting."}
    set_secret(payload.key, payload.value)
    return {"key": payload.key, "configured": True}
