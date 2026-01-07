"""
Prompt model for AI property description templates.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Prompt(SQLModel, table=True):
    """Model for AI prompts stored in public.prompts table."""

    __tablename__ = "prompts"
    __table_args__ = {"schema": "public"}

    prompt_id: str = Field(primary_key=True, description="Unique prompt identifier")
    general_rules: Optional[str] = Field(default=None, description="General rules for the prompt")
    markdown_handling: Optional[str] = Field(default=None, description="Markdown formatting rules")
    required_output: Optional[str] = Field(default=None, description="Required output structure (JSON)")
    style_and_output: Optional[str] = Field(default=None, description="Style and output guidelines")
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
    required_output: Optional[str] = None
    style_and_output: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PromptUpdate(SQLModel):
    """Model for updating prompt data."""

    general_rules: Optional[str] = None
    markdown_handling: Optional[str] = None
    required_output: Optional[str] = None
    style_and_output: Optional[str] = None
