"""
Personal AI OS - Shared Variable Routes

REST API routes for managing dynamic rule variables and shared parameters.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.dependencies import get_db
from app.services.variable_service import VariableService
from app.api.schemas.variables import SharedVariableUpsert, SharedVariableResponse

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.post("/variables", response_model=SharedVariableResponse)
async def set_variable(
    body: SharedVariableUpsert,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a dynamic variable parameter for the user."""
    service = VariableService(db)
    try:
        variable = await service.set_variable(
            user_id=user_id,
            name=body.name,
            value=body.value,
            description=body.description,
        )
        return variable
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/variables", response_model=List[SharedVariableResponse])
async def list_variables(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all variables currently defined for the user."""
    service = VariableService(db)
    return await service.list_variables(user_id)


@router.delete("/variables/{name}", response_model=dict)
async def delete_variable(
    name: str,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a dynamic variable by its alphanumeric name identifier."""
    service = VariableService(db)
    result = await service.delete_variable(user_id, name)
    if result["count"] == 0:
        raise HTTPException(status_code=404, detail="Variable not found")
    return {"deleted": True}
