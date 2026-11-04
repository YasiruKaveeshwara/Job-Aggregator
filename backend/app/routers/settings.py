"""
Settings API. Lets the frontend (web app or desktop app, both use the same
endpoints) check which secrets are configured and save new ones — WITHOUT ever
exposing the real value back over the API once it has been saved.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.gemini_models import list_available_gemini_models
from app.secrets import get_secret, is_secret_configured, set_secret

router = APIRouter(prefix="/api/settings", tags=["settings"])

# The list of keys this app allows to be configured through the Settings screen.
MANAGED_KEYS = ["GEMINI_API_KEY", "GEMINI_MODEL"]


class SettingUpdate(BaseModel):
    key: str
    value: str


class ModelListRequest(BaseModel):
    api_key: str | None = None


@router.get("/status")
def get_settings_status():
    """Returns True/False per managed key. NEVER returns the actual secret value."""
    return {
        "GEMINI_API_KEY": is_secret_configured("GEMINI_API_KEY"),
        "GEMINI_MODEL": get_secret("GEMINI_MODEL") or "",
    }


@router.post("")
def update_setting(payload: SettingUpdate):
    """Saves a new value for one managed key. Write-only: the response confirms
    it was saved, but does not echo the value back."""
    if payload.key not in MANAGED_KEYS:
        return {"error": f"'{payload.key}' is not a configurable setting."}
    value = payload.value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Setting value cannot be empty.")
    set_secret(payload.key, value)
    return {"key": payload.key, "configured": True}


@router.post("/models")
def list_gemini_models(payload: ModelListRequest):
    """List generateContent-capable Gemini models available to the supplied key."""
    api_key = (payload.api_key or get_secret("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=400, detail="Save or enter a Gemini API key first."
        )

    try:
        return list_available_gemini_models(api_key)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not load Gemini models: {exc}"
        ) from exc
