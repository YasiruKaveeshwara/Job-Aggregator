"""
Layered secret/config resolution.

Order of precedence, checked in this exact order:
  1. The Setting table in SQLite (set via the Settings screen, POST /api/settings)
  2. An environment variable of the same name (from backend/.env in web-app/dev mode)
  3. None, if neither is set

This means: the web app, running with a filled-in .env file, behaves EXACTLY as it
always has, because step 2 will always find the value before step 3 is ever reached.
The desktop .exe ships with NO .env file bundled inside it, so step 2 finds nothing,
and the app falls through to None until the person using it enters a value through
the Settings screen (which writes to the Setting table, so step 1 then succeeds on
every future lookup).
"""

import os
from typing import Optional

from sqlmodel import Session

from app.db import engine
from app.models import Setting


def get_secret(key: str) -> Optional[str]:
    """Look up a config value. Checks the database first, then the environment.
    Returns None if not found anywhere. NEVER raises just because a value is missing —
    callers must handle a None return gracefully."""
    with Session(engine) as session:
        row = session.get(Setting, key)
        if row is not None and row.value:
            return row.value

    env_value = os.environ.get(key)
    if env_value:
        return env_value

    return None


def set_secret(key: str, value: str) -> None:
    """Save (or overwrite) a value in the Setting table. This is what the Settings
    screen calls when the user clicks Save. This does NOT touch the .env file —
    it only ever writes to the database."""
    with Session(engine) as session:
        existing = session.get(Setting, key)
        if existing is not None:
            existing.value = value
            session.add(existing)
        else:
            session.add(Setting(key=key, value=value))
        session.commit()


def is_secret_configured(key: str) -> bool:
    """Returns True/False only — never returns the actual value. Used by the
    /api/settings/status endpoint so the frontend can show a checkmark without
    ever receiving the real secret back."""
    return get_secret(key) is not None
