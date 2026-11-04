"""Read and manage the runtime-editable AI prompts."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.ai_prompt_defaults import JOBS_JSON_PLACEHOLDER, USER_PROMPT_KEY
from app.db import get_session
from app.models import AIPrompt

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class AIPromptOut(BaseModel):
    key: str
    name: str
    description: str
    default_prompt: str
    prompt: str
    is_customized: bool


class AIPromptUpdate(BaseModel):
    prompt: str


def _to_prompt_out(row: AIPrompt) -> AIPromptOut:
    return AIPromptOut(
        key=row.key,
        name=row.name,
        description=row.description,
        default_prompt=row.default_prompt,
        prompt=row.prompt,
        is_customized=row.prompt != row.default_prompt,
    )


@router.get("", response_model=list[AIPromptOut])
def list_ai_prompts(session: Session = Depends(get_session)):
    """Return all prompts and their immutable reset defaults."""
    rows = session.exec(select(AIPrompt).order_by(AIPrompt.name)).all()
    return [_to_prompt_out(row) for row in rows]


@router.put("/{prompt_key}", response_model=AIPromptOut)
def update_ai_prompt(
    prompt_key: str,
    body: AIPromptUpdate,
    session: Session = Depends(get_session),
):
    """Save one prompt without affecting the others."""
    row = session.get(AIPrompt, prompt_key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_key}' not found")
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if prompt_key == USER_PROMPT_KEY and JOBS_JSON_PLACEHOLDER not in body.prompt:
        raise HTTPException(
            status_code=400,
            detail=f"User prompt must include the {JOBS_JSON_PLACEHOLDER} placeholder",
        )

    row.prompt = body.prompt
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_prompt_out(row)


@router.post("/{prompt_key}/reset", response_model=AIPromptOut)
def reset_ai_prompt(prompt_key: str, session: Session = Depends(get_session)):
    """Restore one prompt to the default captured when it was seeded."""
    row = session.get(AIPrompt, prompt_key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_key}' not found")

    row.prompt = row.default_prompt
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_prompt_out(row)
