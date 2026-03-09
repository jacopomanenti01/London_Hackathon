"""Schema management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/schemas", tags=["schemas"])


@router.get("/active")
async def get_active_schema(request: Request) -> dict:
    """Get the currently active profile schema configuration."""
    deps = request.app.state.deps
    schema = deps.schema_service.get_active_schema()
    return {
        "schema_id": schema.schema_id,
        "version": schema.version,
        "is_active": schema.is_active,
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "required": s.required,
                "freshness_days": s.freshness_days,
                "fields": [
                    {
                        "id": f.id,
                        "data_type": f.data_type,
                        "required": f.required,
                        "ttl_days": f.ttl_days,
                    }
                    for f in s.fields
                ],
            }
            for s in schema.sections
        ],
    }


@router.get("/")
async def list_schemas(request: Request) -> dict:
    """List all available schema IDs."""
    deps = request.app.state.deps
    return {"schemas": deps.schema_service.available_schemas}


@router.post("/activate/{schema_id}")
async def activate_schema(schema_id: str, request: Request) -> dict:
    """Activate a specific schema version.

    This changes the active schema used for all subsequent profile builds.
    """
    deps = request.app.state.deps
    schema = deps.schema_service.activate_schema(schema_id)
    return {
        "schema_id": schema.schema_id,
        "version": schema.version,
        "is_active": schema.is_active,
        "message": f"Schema '{schema_id}' activated",
    }
