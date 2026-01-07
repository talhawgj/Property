"""
Prompt model for AI property description templates.
"""

import json
from datetime import datetime
from typing import Optional, Any

from pydantic import field_validator
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Text


class Prompt(SQLModel, table=True):
    """Model for AI prompts stored in public.prompts table."""

    __tablename__ = "prompts"
    __table_args__ = {"schema": "public"}

    prompt_id: str = Field(primary_key=True, description="Unique prompt identifier")
    general_rules: Optional[str] = Field(default=None, sa_column=Column(Text), description="General rules for the prompt")
    markdown_handling: Optional[str] = Field(default=None, sa_column=Column(Text), description="Markdown formatting rules")
    required_output: Optional[str] = Field(default=None, sa_column=Column(Text), description="Required output structure (JSON)")
    style_and_output: Optional[str] = Field(default=None, sa_column=Column(Text), description="Style and output guidelines")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
        description="Last update timestamp",
    )


class PromptResponse(SQLModel):
    """Response model for prompt data."""

    prompt_id: str
    general_rules: Optional[str] = None
    markdown_handling: Optional[str] = None
    required_output: Optional[Any] = None  # Can be string or dict
    style_and_output: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator('required_output', mode='before')
    @classmethod
    def parse_required_output(cls, v):
        """Parse required_output if it's a dict, stringify if needed."""
        if v is None:
            return None
        if isinstance(v, dict):
            return json.dumps(v)
        if isinstance(v, str):
            # Try to parse and re-stringify to ensure it's valid JSON
            try:
                parsed = json.loads(v)
                return json.dumps(parsed)
            except json.JSONDecodeError:
                return v
        return str(v)


class PromptUpdate(SQLModel):
    """Model for updating prompt data."""

    general_rules: Optional[str] = None
    markdown_handling: Optional[str] = None
    required_output: Optional[Any] = None  # Can be string or dict
    style_and_output: Optional[str] = None

    @field_validator('required_output', mode='before')
    @classmethod
    def parse_required_output(cls, v):
        """Ensure required_output is stored as JSON string."""
        if v is None:
            return None
        if isinstance(v, dict):
            return json.dumps(v)
        return v
