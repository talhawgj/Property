"""
Routes for managing AI prompt templates.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlmodel import select as sqlmodel_select

from db import get_session
from models.prompt import Prompt, PromptResponse, PromptUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prompts", tags=["Prompts"])


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    session: AsyncSession = Depends(get_session),
) -> PromptResponse:
    """
    Get a specific prompt by ID.

    Args:
        prompt_id: The prompt identifier (e.g., 'prop-insights').
        session: Database session.

    Returns:
        Prompt data.
    """
    try:
        result = await session.execute(
            select(Prompt).where(Prompt.prompt_id == prompt_id)
        )
        prompt = result.scalar_one_or_none()

        if not prompt:
            raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")

        return PromptResponse.model_validate(prompt)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch prompt: {str(e)}")


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    prompt_update: PromptUpdate,
    session: AsyncSession = Depends(get_session),
) -> PromptResponse:
    """
    Update a specific prompt.

    Args:
        prompt_id: The prompt identifier.
        prompt_update: Updated prompt data.
        session: Database session.

    Returns:
        Updated prompt data.
    """
    try:
        # Check if prompt exists
        result = await session.execute(
            select(Prompt).where(Prompt.prompt_id == prompt_id)
        )
        existing_prompt = result.scalar_one_or_none()

        if not existing_prompt:
            raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")

        # Update only provided fields
        update_data = prompt_update.model_dump(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Perform update
        stmt = (
            update(Prompt)
            .where(Prompt.prompt_id == prompt_id)
            .values(**update_data)
            .returning(Prompt)
        )
        
        result = await session.execute(stmt)
        await session.commit()
        
        updated_prompt = result.scalar_one()
        
        logger.info(f"Updated prompt {prompt_id}")
        
        return PromptResponse.model_validate(updated_prompt)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update prompt: {str(e)}")


@router.post("/{prompt_id}", response_model=PromptResponse, status_code=201)
async def create_prompt(
    prompt_id: str,
    prompt_data: PromptUpdate,
    session: AsyncSession = Depends(get_session),
) -> PromptResponse:
    """
    Create a new prompt.

    Args:
        prompt_id: The prompt identifier.
        prompt_data: Prompt data.
        session: Database session.

    Returns:
        Created prompt data.
    """
    try:
        # Check if prompt already exists
        result = await session.execute(
            select(Prompt).where(Prompt.prompt_id == prompt_id)
        )
        existing_prompt = result.scalar_one_or_none()

        if existing_prompt:
            raise HTTPException(
                status_code=409, 
                detail=f"Prompt '{prompt_id}' already exists. Use PUT to update."
            )

        # Create new prompt
        new_prompt = Prompt(
            prompt_id=prompt_id,
            **prompt_data.model_dump(exclude_unset=True)
        )

        session.add(new_prompt)
        await session.commit()
        await session.refresh(new_prompt)

        logger.info(f"Created prompt {prompt_id}")

        return PromptResponse.model_validate(new_prompt)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create prompt: {str(e)}")


@router.get("/", response_model=list[PromptResponse])
async def list_prompts(
    session: AsyncSession = Depends(get_session),
) -> list[PromptResponse]:
    """
    List all prompts.

    Args:
        session: Database session.

    Returns:
        List of all prompts.
    """
    try:
        result = await session.execute(select(Prompt))
        prompts = result.scalars().all()

        return [PromptResponse.model_validate(p) for p in prompts]

    except Exception as e:
        logger.error(f"Error listing prompts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list prompts: {str(e)}")
