"""
Personal AI OS - Rule Import API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.rule_import import (
    ImportPreviewRequest, ImportExecuteRequest,
    ImportPreviewResponse, ImportExecuteResponse,
    TemplateResponse, TemplatesListResponse
)
from app.dependencies import get_db
from app.services.import_service import ImportService, get_available_templates, load_template
from app.services.rule_engine import RuleEngineService


router = APIRouter()


@router.post("/rules/import/preview", response_model=ImportPreviewResponse)
async def preview_import(
    request: ImportPreviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Preview what a rule import would do without making changes.

    Shows which rules would be created, merged, or skipped.
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(request.user_id)

    import_service = ImportService(db)

    # Validate
    rules_data = [r.model_dump() for r in request.rules]
    validation = import_service.validate_import({"rules": rules_data})

    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={
            "message": "Validation failed",
            "errors": validation["errors"],
        })

    # Preview
    result = await import_service.preview_import(
        user_id=user.id,
        rules=validation["validated_rules"],
    )

    return ImportPreviewResponse(**result)


@router.post("/rules/import", response_model=ImportExecuteResponse)
async def execute_import(
    request: ImportExecuteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a bulk rule import.

    Strategies:
    - skip_duplicates: Skip rules that are similar to existing ones
    - merge: Reinforce existing similar rules
    - overwrite: Update existing similar rules with new content
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(request.user_id)

    import_service = ImportService(db)

    # Validate
    rules_data = [r.model_dump() for r in request.rules]
    validation = import_service.validate_import({"rules": rules_data})

    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={
            "message": "Validation failed",
            "errors": validation["errors"],
        })

    # Validate strategy
    valid_strategies = {"skip_duplicates", "merge", "overwrite"}
    if request.strategy not in valid_strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Must be one of: {', '.join(valid_strategies)}"
        )

    # Execute
    result = await import_service.execute_import(
        user_id=user.id,
        rules=validation["validated_rules"],
        strategy=request.strategy,
    )

    await db.commit()

    return ImportExecuteResponse(**result)


@router.get("/rules/templates", response_model=TemplatesListResponse)
async def list_templates():
    """List available pre-built rule template packs."""
    templates = get_available_templates()
    return TemplatesListResponse(
        templates=[TemplateResponse(**t) for t in templates],
        total=len(templates),
    )


@router.get("/rules/templates/{template_id}")
async def get_template(template_id: str):
    """Get the full contents of a rule template pack."""
    template = load_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template
