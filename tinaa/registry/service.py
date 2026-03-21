# tinaa/registry/service.py
"""Product Registry Service for the TINAA MSP platform.

Provides CRUD operations for Products, Environments, and Endpoints.
The service accepts a session factory (async context manager) so that
callers can supply either the real SQLAlchemy session or a test double.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select

from tinaa.models.endpoint import Endpoint, EndpointCreate, EndpointResponse
from tinaa.models.environment import Environment, EnvironmentCreate, EnvironmentResponse
from tinaa.models.product import Product, ProductCreate, ProductResponse, ProductUpdate
from tinaa.registry.exceptions import (
    DuplicateEnvironmentError,
    DuplicateProductError,
    EndpointNotFoundError,
    EnvironmentNotFoundError,
    ProductNotFoundError,
)

logger = logging.getLogger(__name__)

# Fields that ProductRegistryService computes from inputs and therefore must
# not be blindly copied from ProductCreate when constructing the ORM object.
_PRODUCT_COMPUTED_FIELDS: frozenset[str] = frozenset(
    {"organization_id", "name", "slug", "repository_owner", "repository_name"}
)

# ---------------------------------------------------------------------------
# Module-level helpers (public so tests can import directly)
# ---------------------------------------------------------------------------

_SLUG_STRIP_RE = re.compile(r"[^\w\s-]")
_SLUG_COLLAPSE_RE = re.compile(r"[\s_]+")


def _slugify(text: str) -> str:
    """Convert a product name into a URL-safe slug.

    Steps:
    1. Lowercase the text.
    2. Strip special characters (anything not alphanumeric, space, or hyphen).
    3. Collapse runs of whitespace/underscores into a single hyphen.
    4. Strip leading/trailing hyphens.
    """
    if not text:
        return ""
    text = text.lower()
    text = _SLUG_STRIP_RE.sub("", text)
    text = _SLUG_COLLAPSE_RE.sub("-", text)
    return text.strip("-")


_REPO_PATH_RE = re.compile(r"(?:https?://)?[^/]+/([^/]+)/([^/.]+)(?:\.git)?$")


def _parse_repo_url(url: str | None) -> tuple[str | None, str | None]:
    """Parse a repository URL into (owner, repository_name).

    Supports:
    - ``https://github.com/owner/repo``
    - ``github.com/owner/repo``
    - ``https://github.com/owner/repo.git``

    Returns:
        ``(None, None)`` for invalid or absent URLs.
    """
    if not url:
        return None, None
    match = _REPO_PATH_RE.search(url)
    if not match:
        return None, None
    owner, name = match.group(1), match.group(2)
    return owner, name


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ProductRegistryService:
    """Service for managing the product registry.

    All public methods are async and must be awaited.

    Args:
        session_factory: An async context manager factory.  Each call produces
            an async database session.  Usage example::

                async with self._session_factory() as session:
                    ...
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Product operations
    # ------------------------------------------------------------------

    async def create_product(self, org_id: UUID, data: ProductCreate) -> ProductResponse:
        """Create a new product for the given organization.

        The slug is derived automatically from ``data.name`` when not
        already set on ``data``.  Repository owner and name are parsed
        from ``data.repository_url`` when present.

        Raises:
            DuplicateProductError: If a product with the generated slug
                already exists within the organization.
        """
        slug = _slugify(data.name)
        repo_owner, repo_name = _parse_repo_url(getattr(data, "repository_url", None))

        async with self._session_factory() as session:
            existing = await self._fetch_first(
                session,
                select(Product).where(
                    Product.organization_id == org_id,
                    Product.slug == slug,
                ),
            )
            if existing is not None:
                raise DuplicateProductError(org_id, slug)

            extra = {
                k: v for k, v in data.model_dump().items() if k not in _PRODUCT_COMPUTED_FIELDS
            }
            product = Product(
                organization_id=org_id,
                name=data.name,
                slug=slug,
                repository_owner=repo_owner,
                repository_name=repo_name,
                **extra,
            )
            session.add(product)
            await session.flush()
            await session.refresh(product)
            await session.commit()
            logger.info("Created product '%s' (org=%s)", slug, org_id)
            return ProductResponse.model_validate(product)

    async def get_product(self, product_id: UUID) -> ProductResponse | None:
        """Return a product by ID, or ``None`` if not found."""
        async with self._session_factory() as session:
            product = await self._fetch_first(
                session,
                select(Product).where(Product.id == product_id),
            )
            if product is None:
                return None
            return ProductResponse.model_validate(product)

    async def get_product_by_slug(self, org_id: UUID, slug: str) -> ProductResponse | None:
        """Return a product by organization + slug, or ``None`` if not found."""
        async with self._session_factory() as session:
            product = await self._fetch_first(
                session,
                select(Product).where(
                    Product.organization_id == org_id,
                    Product.slug == slug,
                ),
            )
            if product is None:
                return None
            return ProductResponse.model_validate(product)

    async def list_products(self, org_id: UUID, status: str | None = None) -> list[ProductResponse]:
        """List products for an organization, optionally filtered by status."""
        async with self._session_factory() as session:
            stmt = select(Product).where(Product.organization_id == org_id)
            if status is not None:
                stmt = stmt.where(Product.status == status)
            rows = await self._fetch_all(session, stmt)
            return [ProductResponse.model_validate(p) for p in rows]

    async def update_product(self, product_id: UUID, data: ProductUpdate) -> ProductResponse:
        """Update product fields.  Only non-``None`` values in data are applied.

        Raises:
            ProductNotFoundError: If the product does not exist.
        """
        async with self._session_factory() as session:
            product = await self._fetch_first(
                session,
                select(Product).where(Product.id == product_id),
            )
            if product is None:
                raise ProductNotFoundError(product_id)

            for field, value in data.model_dump().items():
                if value is not None:
                    setattr(product, field, value)

            await session.flush()
            await session.refresh(product)
            await session.commit()
            logger.info("Updated product %s", product_id)
            return ProductResponse.model_validate(product)

    async def delete_product(self, product_id: UUID) -> bool:
        """Delete a product.

        Raises:
            ProductNotFoundError: If the product does not exist.

        Returns:
            ``True`` on success.
        """
        async with self._session_factory() as session:
            product = await self._fetch_first(
                session,
                select(Product).where(Product.id == product_id),
            )
            if product is None:
                raise ProductNotFoundError(product_id)

            await session.delete(product)
            await session.commit()
            logger.info("Deleted product %s", product_id)
            return True

    # ------------------------------------------------------------------
    # Environment operations
    # ------------------------------------------------------------------

    async def add_environment(
        self, product_id: UUID, data: EnvironmentCreate
    ) -> EnvironmentResponse:
        """Add an environment to a product.

        Raises:
            ProductNotFoundError: If the product does not exist.
            DuplicateEnvironmentError: If an environment with the same name
                already exists within the product.
        """
        async with self._session_factory() as session:
            product = await self._fetch_first(
                session,
                select(Product).where(Product.id == product_id),
            )
            if product is None:
                raise ProductNotFoundError(product_id)

            existing = await self._fetch_first(
                session,
                select(Environment).where(
                    Environment.product_id == product_id,
                    Environment.name == data.name,
                ),
            )
            if existing is not None:
                raise DuplicateEnvironmentError(product_id, data.name)

            env = Environment(
                product_id=product_id,
                **{k: v for k, v in data.model_dump().items() if k != "product_id"},
            )
            session.add(env)
            await session.flush()
            await session.refresh(env)
            await session.commit()
            logger.info("Added environment '%s' to product %s", data.name, product_id)
            return EnvironmentResponse.model_validate(env)

    async def get_environment(self, env_id: UUID) -> EnvironmentResponse | None:
        """Return an environment by ID, or ``None`` if not found."""
        async with self._session_factory() as session:
            env = await self._fetch_first(
                session,
                select(Environment).where(Environment.id == env_id),
            )
            if env is None:
                return None
            return EnvironmentResponse.model_validate(env)

    async def list_environments(self, product_id: UUID) -> list[EnvironmentResponse]:
        """List all environments for a product."""
        async with self._session_factory() as session:
            rows = await self._fetch_all(
                session,
                select(Environment).where(Environment.product_id == product_id),
            )
            return [EnvironmentResponse.model_validate(e) for e in rows]

    async def update_environment(self, env_id: UUID, data: dict[str, Any]) -> EnvironmentResponse:
        """Apply a dict of field updates to an environment.

        Raises:
            EnvironmentNotFoundError: If the environment does not exist.
        """
        async with self._session_factory() as session:
            env = await self._fetch_first(
                session,
                select(Environment).where(Environment.id == env_id),
            )
            if env is None:
                raise EnvironmentNotFoundError(env_id)

            for field, value in data.items():
                if value is not None:
                    setattr(env, field, value)

            await session.flush()
            await session.refresh(env)
            await session.commit()
            logger.info("Updated environment %s", env_id)
            return EnvironmentResponse.model_validate(env)

    async def delete_environment(self, env_id: UUID) -> bool:
        """Delete an environment.

        Raises:
            EnvironmentNotFoundError: If the environment does not exist.

        Returns:
            ``True`` on success.
        """
        async with self._session_factory() as session:
            env = await self._fetch_first(
                session,
                select(Environment).where(Environment.id == env_id),
            )
            if env is None:
                raise EnvironmentNotFoundError(env_id)

            await session.delete(env)
            await session.commit()
            logger.info("Deleted environment %s", env_id)
            return True

    # ------------------------------------------------------------------
    # Endpoint operations
    # ------------------------------------------------------------------

    async def add_endpoint(self, env_id: UUID, data: EndpointCreate) -> EndpointResponse:
        """Add an endpoint to an environment.

        Raises:
            EnvironmentNotFoundError: If the environment does not exist.
        """
        async with self._session_factory() as session:
            env = await self._fetch_first(
                session,
                select(Environment).where(Environment.id == env_id),
            )
            if env is None:
                raise EnvironmentNotFoundError(env_id)

            endpoint = Endpoint(
                environment_id=env_id,
                **{k: v for k, v in data.model_dump().items() if k != "environment_id"},
            )
            session.add(endpoint)
            await session.flush()
            await session.refresh(endpoint)
            await session.commit()
            logger.info("Added endpoint to environment %s", env_id)
            return EndpointResponse.model_validate(endpoint)

    async def get_endpoint(self, endpoint_id: UUID) -> EndpointResponse | None:
        """Return an endpoint by ID, or ``None`` if not found."""
        async with self._session_factory() as session:
            endpoint = await self._fetch_first(
                session,
                select(Endpoint).where(Endpoint.id == endpoint_id),
            )
            if endpoint is None:
                return None
            return EndpointResponse.model_validate(endpoint)

    async def list_endpoints(
        self, env_id: UUID, monitored_only: bool = False
    ) -> list[EndpointResponse]:
        """List endpoints for an environment.

        Args:
            env_id: Target environment UUID.
            monitored_only: When ``True``, return only endpoints where
                ``is_monitored`` is ``True``.
        """
        async with self._session_factory() as session:
            stmt = select(Endpoint).where(Endpoint.environment_id == env_id)
            if monitored_only:
                stmt = stmt.where(Endpoint.is_monitored == True)  # noqa: E712
            rows = await self._fetch_all(session, stmt)
            return [EndpointResponse.model_validate(ep) for ep in rows]

    async def update_endpoint(self, endpoint_id: UUID, data: dict[str, Any]) -> EndpointResponse:
        """Apply a dict of field updates to an endpoint.

        Raises:
            EndpointNotFoundError: If the endpoint does not exist.
        """
        async with self._session_factory() as session:
            endpoint = await self._fetch_first(
                session,
                select(Endpoint).where(Endpoint.id == endpoint_id),
            )
            if endpoint is None:
                raise EndpointNotFoundError(endpoint_id)

            for field, value in data.items():
                if value is not None:
                    setattr(endpoint, field, value)

            await session.flush()
            await session.refresh(endpoint)
            await session.commit()
            logger.info("Updated endpoint %s", endpoint_id)
            return EndpointResponse.model_validate(endpoint)

    async def delete_endpoint(self, endpoint_id: UUID) -> bool:
        """Delete an endpoint.

        Raises:
            EndpointNotFoundError: If the endpoint does not exist.

        Returns:
            ``True`` on success.
        """
        async with self._session_factory() as session:
            endpoint = await self._fetch_first(
                session,
                select(Endpoint).where(Endpoint.id == endpoint_id),
            )
            if endpoint is None:
                raise EndpointNotFoundError(endpoint_id)

            await session.delete(endpoint)
            await session.commit()
            logger.info("Deleted endpoint %s", endpoint_id)
            return True

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    async def register_product_full(
        self,
        org_id: UUID,
        product_data: ProductCreate,
        environments: list[dict[str, Any]],
        endpoints: list[dict[str, Any]],
    ) -> ProductResponse:
        """Register a product together with its environments and endpoints.

        This is the primary onboarding entry point.

        ``endpoints`` dicts must include an ``env_name`` key that corresponds
        to the ``name`` of one of the environments being registered.

        Args:
            org_id: The owning organization's UUID.
            product_data: Data for the product to create.
            environments: List of raw environment dicts (each is passed to
                :class:`~tinaa.models.environment.EnvironmentCreate`).
            endpoints: List of raw endpoint dicts.  Each must contain
                ``env_name`` so it can be attached to the correct environment.

        Returns:
            The created :class:`~tinaa.models.product.ProductResponse`.
        """
        product = await self.create_product(org_id, product_data)

        env_name_to_id: dict[str, UUID] = {}
        for env_dict in environments:
            env_create = EnvironmentCreate(**env_dict)
            env_response = await self.add_environment(product.id, env_create)
            env_name_to_id[env_create.name] = env_response.id

        for ep_dict in endpoints:
            ep_dict = dict(ep_dict)
            env_name = ep_dict.pop("env_name", None)
            env_id = env_name_to_id.get(env_name) if env_name else None
            if env_id is not None:
                ep_create = EndpointCreate(**ep_dict)
                await self.add_endpoint(env_id, ep_create)

        logger.info(
            "Registered product '%s' with %d env(s) and %d endpoint(s)",
            getattr(product, "slug", product_data.name),
            len(environments),
            len(endpoints),
        )
        return product

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    async def get_product_with_environments(self, product_id: UUID) -> dict[str, Any]:
        """Return a product together with all of its environments and endpoints.

        Returns:
            A dict with keys ``"product"`` and ``"environments"``.  Each entry
            in ``"environments"`` is a dict containing ``"environment"`` and
            ``"endpoints"``.

        Raises:
            ProductNotFoundError: If the product does not exist.
        """
        async with self._session_factory() as session:
            product = await self._fetch_first(
                session,
                select(Product).where(Product.id == product_id),
            )
            if product is None:
                raise ProductNotFoundError(product_id)

            product_response = ProductResponse.model_validate(product)
            environments_out: list[dict[str, Any]] = []
            for env in product.environments:
                env_response = EnvironmentResponse.model_validate(env)
                endpoint_responses = [EndpointResponse.model_validate(ep) for ep in env.endpoints]
                environments_out.append(
                    {
                        "environment": env_response,
                        "endpoints": endpoint_responses,
                    }
                )

            return {"product": product_response, "environments": environments_out}

    async def find_products_by_repo(self, repo_url: str) -> list[ProductResponse]:
        """Find all products whose ``repository_url`` matches the given URL."""
        async with self._session_factory() as session:
            rows = await self._fetch_all(
                session,
                select(Product).where(Product.repository_url == repo_url),
            )
            return [ProductResponse.model_validate(p) for p in rows]

    async def get_endpoints_for_monitoring(
        self, product_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        """Return all monitored endpoints, optionally filtered by product.

        Each result dict contains keys ``"endpoint"`` (the raw ORM object)
        and ``"environment"`` (the ORM environment linked via relationship).

        Args:
            product_id: When provided, restrict results to endpoints whose
                parent environment belongs to this product.
        """
        async with self._session_factory() as session:
            stmt = select(Endpoint).where(
                Endpoint.is_monitored == True  # noqa: E712
            )
            if product_id is not None:
                stmt = stmt.join(
                    Environment,
                    Environment.id == Endpoint.environment_id,
                ).where(Environment.product_id == product_id)

            rows = await self._fetch_all(session, stmt)
            return [
                {
                    "endpoint": ep,
                    "environment": getattr(ep, "environment", None),
                }
                for ep in rows
            ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _fetch_first(session: Any, stmt: Any) -> Any:
        """Execute a statement and return the first scalar result or None."""
        result = await session.execute(stmt)
        return result.first()

    @staticmethod
    async def _fetch_all(session: Any, stmt: Any) -> list[Any]:
        """Execute a statement and return all scalar results."""
        result = await session.execute(stmt)
        return result.all()
