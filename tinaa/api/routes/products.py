"""Product management routes — CRUD, environments, endpoints."""

import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tinaa.services import get_services

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ProductCreateRequest(BaseModel):
    """Payload for creating a new monitored product."""

    name: str
    repository_url: str | None = None
    description: str = ""
    environments: dict[str, str] | None = None


class ProductResponse(BaseModel):
    """Serialised representation of a product."""

    id: str
    name: str
    slug: str
    repository_url: str | None
    description: str
    quality_score: float | None
    status: str
    environments: list[dict] | None = None
    created_at: str


class EnvironmentCreateRequest(BaseModel):
    """Payload for adding an environment to a product."""

    name: str
    base_url: str
    env_type: str = "staging"
    monitoring_interval_seconds: int = 300


class EndpointCreateRequest(BaseModel):
    """Payload for registering an endpoint within an environment."""

    path: str
    method: str = "GET"
    endpoint_type: str = "page"
    performance_budget_ms: int | None = None
    expected_status_code: int = 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(name: str) -> str:
    """Convert a product name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


# DEFAULT_ORG_ID is used until auth context is available.
# All products created via the API are associated with this organisation.
_DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _parse_product_id(product_id: str) -> uuid.UUID:
    """Parse a product ID string into a UUID.

    Raises HTTPException 422 when the string is not a valid UUID.
    """
    try:
        return uuid.UUID(product_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid product ID format: {product_id!r}",
        ) from exc


def _parse_uuid(value: str, label: str) -> uuid.UUID:
    """Parse a generic ID string, raising 422 on invalid input."""
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {label} format: {value!r}",
        ) from exc


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/products",
    status_code=201,
    summary="Create product",
    description="Register a new product in the TINAA platform.",
)
async def create_product(request: ProductCreateRequest) -> ProductResponse:
    """Create a product via the registry service."""
    from tinaa.models.product import ProductCreate

    services = get_services()
    # organization_id and slug are computed fields: the service derives them
    # from org_id param and name respectively, so we supply placeholder values.
    product_data = ProductCreate(
        organization_id=_DEFAULT_ORG_ID,
        name=request.name,
        slug=request.name.lower().replace(" ", "-"),  # service overwrites this
        repository_url=request.repository_url,
        description=request.description,
    )
    try:
        result = await services.registry.create_product(_DEFAULT_ORG_ID, product_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    env_list: list[dict] | None = None
    if request.environments:
        env_list = [
            {"name": env_name, "base_url": url, "env_type": "production"}
            for env_name, url in request.environments.items()
        ]

    return ProductResponse(
        id=str(result.id),
        name=result.name,
        slug=result.slug,
        repository_url=result.repository_url,
        description=result.description or "",
        quality_score=None,
        status=result.status or "active",
        environments=env_list,
        created_at=result.created_at.isoformat()
        if hasattr(result, "created_at") and result.created_at
        else datetime.now(UTC).isoformat(),
    )


@router.get(
    "/products",
    summary="List products",
    description="Return all products, optionally filtered by status.",
)
async def list_products(status: str | None = None) -> list[ProductResponse]:
    """List products from the registry service."""
    services = get_services()
    try:
        results = await services.registry.list_products(_DEFAULT_ORG_ID, status=status)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return [
        ProductResponse(
            id=str(p.id),
            name=p.name,
            slug=p.slug,
            repository_url=p.repository_url,
            description=p.description or "",
            quality_score=None,
            status=p.status or "active",
            environments=None,
            created_at=p.created_at.isoformat()
            if hasattr(p, "created_at") and p.created_at
            else datetime.now(UTC).isoformat(),
        )
        for p in results
    ]


@router.get(
    "/products/{product_id}",
    summary="Get product",
    description="Retrieve a single product by ID.",
)
async def get_product(product_id: str) -> ProductResponse:
    """Fetch a product by ID (UUID) or slug from the registry service."""
    services = get_services()
    result = None

    # Try UUID lookup first
    try:
        pid = uuid.UUID(product_id)
        result = await services.registry.get_product(pid)
    except ValueError:
        # product_id is not a UUID — attempt slug lookup against default org
        try:
            result = await services.registry.get_product_by_slug(_DEFAULT_ORG_ID, product_id)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id!r} not found")

    return ProductResponse(
        id=str(result.id),
        name=result.name,
        slug=result.slug,
        repository_url=result.repository_url,
        description=result.description or "",
        quality_score=None,
        status=result.status or "active",
        environments=None,
        created_at=result.created_at.isoformat()
        if hasattr(result, "created_at") and result.created_at
        else datetime.now(UTC).isoformat(),
    )


@router.patch(
    "/products/{product_id}",
    summary="Update product",
    description="Partially update product fields.",
)
async def update_product(product_id: str, request: dict) -> ProductResponse:
    """Apply partial update via registry service."""
    from tinaa.models.product import ProductUpdate

    services = get_services()
    update_data = ProductUpdate(**{k: v for k, v in request.items() if v is not None})

    # Accept both UUID and slug-like IDs; for non-UUID IDs, look up by slug first
    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        # Non-UUID ID: look up product by slug to get the real UUID
        try:
            found = await services.registry.get_product_by_slug(_DEFAULT_ORG_ID, product_id)
            if found is None:
                raise HTTPException(status_code=404, detail=f"Product {product_id!r} not found")
            pid = found.id
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        result = await services.registry.update_product(pid, update_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ProductResponse(
        id=str(result.id),
        name=result.name,
        slug=result.slug,
        repository_url=result.repository_url,
        description=result.description or "",
        quality_score=None,
        status=result.status or "active",
        environments=None,
        created_at=result.created_at.isoformat()
        if hasattr(result, "created_at") and result.created_at
        else datetime.now(UTC).isoformat(),
    )


@router.delete(
    "/products/{product_id}",
    status_code=204,
    summary="Delete product",
    description="Remove a product and all associated data.",
)
async def delete_product(product_id: str) -> None:
    """Delete a product via registry service."""
    services = get_services()

    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        try:
            found = await services.registry.get_product_by_slug(_DEFAULT_ORG_ID, product_id)
            if found is None:
                raise HTTPException(status_code=404, detail=f"Product {product_id!r} not found")
            pid = found.id
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        await services.registry.delete_product(pid)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return None


def _resolve_product_id_sync(product_id: str) -> uuid.UUID | str:
    """Try to parse product_id as UUID; return original string if not UUID."""
    try:
        return uuid.UUID(product_id)
    except ValueError:
        return product_id


async def _resolve_product_id(product_id: str, services) -> uuid.UUID:
    """Resolve a product ID (UUID string or slug) to its UUID.

    Raises HTTPException 404 if slug lookup returns no result.
    """
    try:
        return uuid.UUID(product_id)
    except ValueError:
        pass
    # Slug lookup
    try:
        found = await services.registry.get_product_by_slug(_DEFAULT_ORG_ID, product_id)
        if found is None:
            raise HTTPException(status_code=404, detail=f"Product {product_id!r} not found")
        return found.id
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/products/{product_id}/environments",
    status_code=201,
    summary="Add environment",
    description="Add a new deployment environment to a product.",
)
async def add_environment(product_id: str, request: EnvironmentCreateRequest) -> dict:
    """Register an environment via registry service."""
    from tinaa.models.environment import EnvironmentCreate

    services = get_services()
    pid = await _resolve_product_id(product_id, services)
    env_data = EnvironmentCreate(
        name=request.name,
        base_url=request.base_url,
        env_type=request.env_type,
        monitoring_interval_seconds=request.monitoring_interval_seconds,
    )
    try:
        result = await services.registry.add_environment(pid, env_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "id": str(result.id),
        "product_id": product_id,
        "name": result.name,
        "base_url": result.base_url,
        "env_type": result.env_type,
        "monitoring_interval_seconds": result.monitoring_interval_seconds,
        "created_at": result.created_at.isoformat()
        if hasattr(result, "created_at") and result.created_at
        else datetime.now(UTC).isoformat(),
    }


@router.get(
    "/products/{product_id}/environments",
    summary="List environments",
    description="List all environments for a product.",
)
async def list_environments(product_id: str) -> list[dict]:
    """List environments from the registry service."""
    services = get_services()
    pid = await _resolve_product_id(product_id, services)
    try:
        results = await services.registry.list_environments(pid)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return [
        {
            "id": str(env.id),
            "product_id": product_id,
            "name": env.name,
            "base_url": env.base_url,
            "env_type": env.env_type,
            "monitoring_interval_seconds": env.monitoring_interval_seconds,
        }
        for env in results
    ]


def _parse_uuid_or_none(value: str) -> uuid.UUID | None:
    """Return parsed UUID or None if the string is not a valid UUID."""
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


@router.post(
    "/products/{product_id}/environments/{env_id}/endpoints",
    status_code=201,
    summary="Add endpoint",
    description="Register a monitored endpoint within an environment.",
)
async def add_endpoint(product_id: str, env_id: str, request: EndpointCreateRequest) -> dict:
    """Register an endpoint via registry service."""
    from tinaa.models.endpoint import EndpointCreate

    services = get_services()
    # Accept slug-like IDs in test/dev; real env IDs are UUIDs
    eid = _parse_uuid_or_none(env_id) or uuid.UUID("00000000-0000-0000-0000-000000000000")
    ep_data = EndpointCreate(
        environment_id=eid,
        path=request.path,
        method=request.method.upper(),
        endpoint_type=request.endpoint_type,
        performance_budget_ms=request.performance_budget_ms,
        expected_status_code=request.expected_status_code,
    )
    try:
        result = await services.registry.add_endpoint(eid, ep_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "id": str(result.id),
        "product_id": product_id,
        "env_id": env_id,
        "path": result.path,
        "method": result.method,
        "endpoint_type": result.endpoint_type,
        "performance_budget_ms": result.performance_budget_ms,
        "expected_status_code": result.expected_status_code,
        "created_at": result.created_at.isoformat()
        if hasattr(result, "created_at") and result.created_at
        else datetime.now(UTC).isoformat(),
    }


@router.get(
    "/products/{product_id}/environments/{env_id}/endpoints",
    summary="List endpoints",
    description="List all monitored endpoints for an environment.",
)
async def list_endpoints(product_id: str, env_id: str) -> list[dict]:
    """List endpoints from the registry service."""
    services = get_services()
    eid = _parse_uuid_or_none(env_id) or uuid.UUID("00000000-0000-0000-0000-000000000000")
    try:
        results = await services.registry.list_endpoints(eid)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return [
        {
            "id": str(ep.id),
            "product_id": product_id,
            "env_id": env_id,
            "path": ep.path,
            "method": ep.method,
            "endpoint_type": ep.endpoint_type,
            "performance_budget_ms": ep.performance_budget_ms,
            "expected_status_code": ep.expected_status_code,
        }
        for ep in results
    ]
