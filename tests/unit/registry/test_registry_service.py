# tests/unit/registry/test_registry_service.py
"""Unit tests for ProductRegistryService using mocked database sessions.

Uses pytest-asyncio with asyncio_mode=auto (set in pytest.ini).
Each test class groups related behaviour following Arrange-Act-Assert.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tinaa.registry.exceptions import (
    DuplicateEnvironmentError,
    DuplicateProductError,
    EndpointNotFoundError,
    EnvironmentNotFoundError,
    ProductNotFoundError,
)
from tinaa.registry.service import ProductRegistryService, _parse_repo_url, _slugify

# ---------------------------------------------------------------------------
# Shared UUIDs
# ---------------------------------------------------------------------------

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PRODUCT_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
ENV_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
ENDPOINT_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")


# ---------------------------------------------------------------------------
# ORM mock builders
# ---------------------------------------------------------------------------

def _make_product(**overrides: Any) -> MagicMock:
    """Return a mock Product ORM object with sensible defaults."""
    p = MagicMock()
    p.id = overrides.get("id", PRODUCT_ID)
    p.organization_id = overrides.get("organization_id", ORG_ID)
    p.name = overrides.get("name", "My App")
    p.slug = overrides.get("slug", "my-app")
    p.status = overrides.get("status", "active")
    p.repository_url = overrides.get("repository_url", None)
    p.repository_owner = overrides.get("repository_owner", None)
    p.repository_name = overrides.get("repository_name", None)
    p.environments = overrides.get("environments", [])
    return p


def _make_environment(**overrides: Any) -> MagicMock:
    """Return a mock Environment ORM object with sensible defaults."""
    e = MagicMock()
    e.id = overrides.get("id", ENV_ID)
    e.product_id = overrides.get("product_id", PRODUCT_ID)
    e.name = overrides.get("name", "production")
    e.base_url = overrides.get("base_url", "https://example.com")
    e.endpoints = overrides.get("endpoints", [])
    return e


def _make_endpoint(**overrides: Any) -> MagicMock:
    """Return a mock Endpoint ORM object with sensible defaults."""
    ep = MagicMock()
    ep.id = overrides.get("id", ENDPOINT_ID)
    ep.environment_id = overrides.get("environment_id", ENV_ID)
    ep.path = overrides.get("path", "/health")
    ep.is_monitored = overrides.get("is_monitored", True)
    ep.environment = overrides.get("environment", None)
    return ep


# ---------------------------------------------------------------------------
# Session / factory builders
# ---------------------------------------------------------------------------

def _make_session(
    scalars_result: list[Any] | None = None,
    scalar_result: Any = None,
) -> MagicMock:
    """Return a mock async SQLAlchemy session.

    ``scalar_result`` is returned by ``result.first()``.
    ``scalars_result`` is returned by ``result.all()``.
    """
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.all.return_value = scalars_result if scalars_result is not None else []
    result_mock.first.return_value = scalar_result
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    session.refresh = AsyncMock()
    return session


def make_session_factory(session: MagicMock):
    """Wrap a mock session in an async context manager factory."""

    @asynccontextmanager
    async def _factory():
        yield session

    return _factory


def _session_factory_with_sequence(
    firsts: list[Any],
    alls: list[list[Any]] | None = None,
) -> tuple[Any, MagicMock]:
    """Build a factory whose session returns successive first() / all() values.

    ``firsts[i]`` is the return value of the i-th ``result.first()`` call.
    ``alls[i]``   is the return value of the i-th ``result.all()``  call.

    Returns (factory, session).
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    session.refresh = AsyncMock()

    first_iter = iter(firsts)
    all_iter = iter(alls or [])

    def _make_result():
        result = MagicMock()
        result.first.return_value = next(first_iter, None)
        try:
            result.all.return_value = next(all_iter)
        except StopIteration:
            result.all.return_value = []
        return result

    session.execute = AsyncMock(side_effect=lambda _stmt: _make_result())

    @asynccontextmanager
    async def _factory():
        yield session

    return _factory, session


# ---------------------------------------------------------------------------
# _slugify tests
# ---------------------------------------------------------------------------

class TestSlugify:
    """Unit tests for the _slugify helper."""

    def test_lowercase(self):
        assert _slugify("MyApp") == "myapp"

    def test_spaces_become_hyphens(self):
        assert _slugify("My App") == "my-app"

    def test_special_chars_stripped(self):
        assert _slugify("My App! (v2)") == "my-app-v2"

    def test_multiple_spaces_collapse(self):
        assert _slugify("  lots   of   spaces  ") == "lots-of-spaces"

    def test_leading_trailing_hyphens_stripped(self):
        assert _slugify("---hello---") == "hello"

    def test_numbers_preserved(self):
        assert _slugify("App v2.0") == "app-v20"

    def test_already_slugified(self):
        assert _slugify("already-fine") == "already-fine"

    def test_empty_string(self):
        assert _slugify("") == ""


# ---------------------------------------------------------------------------
# _parse_repo_url tests
# ---------------------------------------------------------------------------

class TestParseRepoUrl:
    """Unit tests for the _parse_repo_url helper."""

    def test_bare_github_url(self):
        owner, name = _parse_repo_url("github.com/acme/webapp")
        assert owner == "acme"
        assert name == "webapp"

    def test_https_github_url(self):
        owner, name = _parse_repo_url("https://github.com/acme/my-repo")
        assert owner == "acme"
        assert name == "my-repo"

    def test_dot_git_suffix_stripped(self):
        owner, name = _parse_repo_url("https://github.com/acme/webapp.git")
        assert owner == "acme"
        assert name == "webapp"

    def test_gitlab_url(self):
        owner, name = _parse_repo_url("https://gitlab.com/org/project")
        assert owner == "org"
        assert name == "project"

    def test_none_returns_none_tuple(self):
        assert _parse_repo_url(None) == (None, None)

    def test_invalid_url_returns_none_tuple(self):
        assert _parse_repo_url("not-a-url") == (None, None)

    def test_url_without_repo_name_returns_none_tuple(self):
        assert _parse_repo_url("github.com/acme") == (None, None)


# ---------------------------------------------------------------------------
# ProductRegistryService — Product CRUD
# ---------------------------------------------------------------------------

class TestCreateProduct:
    """Tests for ProductRegistryService.create_product."""

    @pytest.mark.asyncio
    async def test_returns_response_on_success(self):
        session = _make_session(scalar_result=None)
        product = _make_product()

        with (
            _patch("Product", product),
            _patch("ProductResponse") as MockResponse,
        ):
            expected = MagicMock()
            MockResponse.model_validate.return_value = expected

            svc = ProductRegistryService(make_session_factory(session))
            data = _product_create_mock("My App")

            result = await svc.create_product(ORG_ID, data)

        assert result is expected

    @pytest.mark.asyncio
    async def test_raises_duplicate_when_slug_exists(self):
        existing = _make_product()
        session = _make_session(scalar_result=existing)

        svc = ProductRegistryService(make_session_factory(session))
        data = _product_create_mock("My App")

        with pytest.raises(DuplicateProductError) as exc_info:
            await svc.create_product(ORG_ID, data)

        assert exc_info.value.slug == "my-app"
        assert exc_info.value.org_id == ORG_ID

    @pytest.mark.asyncio
    async def test_slug_derived_from_name(self):
        session = _make_session(scalar_result=None)
        product = _make_product(slug="my-test-product")

        with (
            _patch("Product", product) as MockProduct,
            _patch("ProductResponse"),
        ):
            svc = ProductRegistryService(make_session_factory(session))
            await svc.create_product(ORG_ID, _product_create_mock("My Test Product"))

            kwargs = MockProduct.call_args.kwargs
            assert kwargs["slug"] == "my-test-product"

    @pytest.mark.asyncio
    async def test_repo_url_parsed_into_owner_and_name(self):
        session = _make_session(scalar_result=None)
        product = _make_product()

        with (
            _patch("Product", product) as MockProduct,
            _patch("ProductResponse"),
        ):
            svc = ProductRegistryService(make_session_factory(session))
            data = _product_create_mock(
                "My App", repository_url="https://github.com/acme/webapp"
            )
            await svc.create_product(ORG_ID, data)

            kwargs = MockProduct.call_args.kwargs
            assert kwargs["repository_owner"] == "acme"
            assert kwargs["repository_name"] == "webapp"


class TestGetProduct:
    """Tests for ProductRegistryService.get_product."""

    @pytest.mark.asyncio
    async def test_returns_response_when_found(self):
        product = _make_product()
        session = _make_session(scalar_result=product)

        with _patch("ProductResponse") as MockResponse:
            expected = MagicMock()
            MockResponse.model_validate.return_value = expected

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.get_product(PRODUCT_ID)

        assert result is expected

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        assert await svc.get_product(PRODUCT_ID) is None


class TestGetProductBySlug:
    """Tests for ProductRegistryService.get_product_by_slug."""

    @pytest.mark.asyncio
    async def test_returns_response_when_found(self):
        product = _make_product(slug="my-app")
        session = _make_session(scalar_result=product)

        with _patch("ProductResponse") as MockResponse:
            expected = MagicMock()
            MockResponse.model_validate.return_value = expected

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.get_product_by_slug(ORG_ID, "my-app")

        assert result is expected

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        assert await svc.get_product_by_slug(ORG_ID, "unknown") is None


class TestListProducts:
    """Tests for ProductRegistryService.list_products."""

    @pytest.mark.asyncio
    async def test_returns_all_products_for_org(self):
        products = [_make_product(), _make_product(id=uuid.uuid4())]
        session = _make_session(scalars_result=products)

        with _patch("ProductResponse") as MockResponse:
            MockResponse.model_validate.side_effect = lambda p, **kw: p

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.list_products(ORG_ID)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self):
        session = _make_session(scalars_result=[])
        svc = ProductRegistryService(make_session_factory(session))

        assert await svc.list_products(ORG_ID) == []

    @pytest.mark.asyncio
    async def test_status_filter_applied(self):
        session = _make_session(scalars_result=[_make_product(status="active")])

        with _patch("ProductResponse") as MockResponse:
            MockResponse.model_validate.side_effect = lambda p, **kw: p

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.list_products(ORG_ID, status="active")

        assert len(result) == 1


class TestUpdateProduct:
    """Tests for ProductRegistryService.update_product."""

    @pytest.mark.asyncio
    async def test_updates_and_returns_response(self):
        product = _make_product()
        session = _make_session(scalar_result=product)

        with _patch("ProductResponse") as MockResponse:
            expected = MagicMock()
            MockResponse.model_validate.return_value = expected

            svc = ProductRegistryService(make_session_factory(session))
            data = MagicMock()
            data.model_dump.return_value = {"name": "Updated Name", "status": None}

            result = await svc.update_product(PRODUCT_ID, data)

        assert result is expected

    @pytest.mark.asyncio
    async def test_raises_when_product_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        data = MagicMock()
        data.model_dump.return_value = {"name": "Updated"}

        with pytest.raises(ProductNotFoundError):
            await svc.update_product(PRODUCT_ID, data)


class TestDeleteProduct:
    """Tests for ProductRegistryService.delete_product."""

    @pytest.mark.asyncio
    async def test_returns_true_when_deleted(self):
        product = _make_product()
        session = _make_session(scalar_result=product)

        svc = ProductRegistryService(make_session_factory(session))
        result = await svc.delete_product(PRODUCT_ID)

        assert result is True
        session.delete.assert_called_once_with(product)

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        with pytest.raises(ProductNotFoundError):
            await svc.delete_product(PRODUCT_ID)


# ---------------------------------------------------------------------------
# Environment CRUD
# ---------------------------------------------------------------------------

class TestAddEnvironment:
    """Tests for ProductRegistryService.add_environment."""

    @pytest.mark.asyncio
    async def test_adds_environment_successfully(self):
        product = _make_product()
        env = _make_environment()
        factory, session = _session_factory_with_sequence(
            firsts=[product, None]  # product found, no duplicate
        )

        with (
            _patch("Environment", env),
            _patch("EnvironmentResponse") as MockResponse,
        ):
            expected = MagicMock()
            MockResponse.model_validate.return_value = expected

            svc = ProductRegistryService(factory)
            data = _env_create_mock("production")
            result = await svc.add_environment(PRODUCT_ID, data)

        assert result is expected

    @pytest.mark.asyncio
    async def test_raises_when_product_not_found(self):
        factory, _ = _session_factory_with_sequence(firsts=[None])
        svc = ProductRegistryService(factory)

        with pytest.raises(ProductNotFoundError):
            await svc.add_environment(PRODUCT_ID, _env_create_mock("production"))

    @pytest.mark.asyncio
    async def test_raises_on_duplicate_environment_name(self):
        product = _make_product()
        existing_env = _make_environment()
        factory, _ = _session_factory_with_sequence(
            firsts=[product, existing_env]  # product found, duplicate found
        )
        svc = ProductRegistryService(factory)

        with pytest.raises(DuplicateEnvironmentError):
            await svc.add_environment(PRODUCT_ID, _env_create_mock("production"))


class TestGetEnvironment:
    """Tests for ProductRegistryService.get_environment."""

    @pytest.mark.asyncio
    async def test_returns_response_when_found(self):
        env = _make_environment()
        session = _make_session(scalar_result=env)

        with _patch("EnvironmentResponse") as MockResponse:
            expected = MagicMock()
            MockResponse.model_validate.return_value = expected

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.get_environment(ENV_ID)

        assert result is expected

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        assert await svc.get_environment(ENV_ID) is None


class TestListEnvironments:
    """Tests for ProductRegistryService.list_environments."""

    @pytest.mark.asyncio
    async def test_returns_all_environments(self):
        envs = [_make_environment(), _make_environment(id=uuid.uuid4())]
        session = _make_session(scalars_result=envs)

        with _patch("EnvironmentResponse") as MockResponse:
            MockResponse.model_validate.side_effect = lambda e, **kw: e

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.list_environments(PRODUCT_ID)

        assert len(result) == 2


class TestUpdateEnvironment:
    """Tests for ProductRegistryService.update_environment."""

    @pytest.mark.asyncio
    async def test_updates_and_returns_response(self):
        env = _make_environment()
        session = _make_session(scalar_result=env)

        with _patch("EnvironmentResponse") as MockResponse:
            expected = MagicMock()
            MockResponse.model_validate.return_value = expected

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.update_environment(
                ENV_ID, {"base_url": "https://new.example.com"}
            )

        assert result is expected

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        with pytest.raises(EnvironmentNotFoundError):
            await svc.update_environment(ENV_ID, {"base_url": "https://new.example.com"})


class TestDeleteEnvironment:
    """Tests for ProductRegistryService.delete_environment."""

    @pytest.mark.asyncio
    async def test_returns_true_when_deleted(self):
        env = _make_environment()
        session = _make_session(scalar_result=env)

        svc = ProductRegistryService(make_session_factory(session))
        result = await svc.delete_environment(ENV_ID)

        assert result is True
        session.delete.assert_called_once_with(env)

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        with pytest.raises(EnvironmentNotFoundError):
            await svc.delete_environment(ENV_ID)


# ---------------------------------------------------------------------------
# Endpoint CRUD
# ---------------------------------------------------------------------------

class TestAddEndpoint:
    """Tests for ProductRegistryService.add_endpoint."""

    @pytest.mark.asyncio
    async def test_adds_endpoint_successfully(self):
        env = _make_environment()
        endpoint = _make_endpoint()
        session = _make_session(scalar_result=env)

        with (
            _patch("Endpoint", endpoint),
            _patch("EndpointResponse") as MockResponse,
        ):
            expected = MagicMock()
            MockResponse.model_validate.return_value = expected

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.add_endpoint(ENV_ID, _endpoint_create_mock())

        assert result is expected

    @pytest.mark.asyncio
    async def test_raises_when_environment_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        with pytest.raises(EnvironmentNotFoundError):
            await svc.add_endpoint(ENV_ID, _endpoint_create_mock())


class TestGetEndpoint:
    """Tests for ProductRegistryService.get_endpoint."""

    @pytest.mark.asyncio
    async def test_returns_response_when_found(self):
        endpoint = _make_endpoint()
        session = _make_session(scalar_result=endpoint)

        with _patch("EndpointResponse") as MockResponse:
            expected = MagicMock()
            MockResponse.model_validate.return_value = expected

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.get_endpoint(ENDPOINT_ID)

        assert result is expected

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        assert await svc.get_endpoint(ENDPOINT_ID) is None


class TestListEndpoints:
    """Tests for ProductRegistryService.list_endpoints."""

    @pytest.mark.asyncio
    async def test_returns_all_endpoints_for_env(self):
        endpoints = [_make_endpoint(), _make_endpoint(id=uuid.uuid4())]
        session = _make_session(scalars_result=endpoints)

        with _patch("EndpointResponse") as MockResponse:
            MockResponse.model_validate.side_effect = lambda e, **kw: e

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.list_endpoints(ENV_ID)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_monitored_only_flag_included(self):
        endpoints = [_make_endpoint(is_monitored=True)]
        session = _make_session(scalars_result=endpoints)

        with _patch("EndpointResponse") as MockResponse:
            MockResponse.model_validate.side_effect = lambda e, **kw: e

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.list_endpoints(ENV_ID, monitored_only=True)

        assert len(result) == 1


class TestUpdateEndpoint:
    """Tests for ProductRegistryService.update_endpoint."""

    @pytest.mark.asyncio
    async def test_updates_and_returns_response(self):
        endpoint = _make_endpoint()
        session = _make_session(scalar_result=endpoint)

        with _patch("EndpointResponse") as MockResponse:
            expected = MagicMock()
            MockResponse.model_validate.return_value = expected

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.update_endpoint(ENDPOINT_ID, {"path": "/api/health"})

        assert result is expected

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        with pytest.raises(EndpointNotFoundError):
            await svc.update_endpoint(ENDPOINT_ID, {"path": "/api/health"})


class TestDeleteEndpoint:
    """Tests for ProductRegistryService.delete_endpoint."""

    @pytest.mark.asyncio
    async def test_returns_true_when_deleted(self):
        endpoint = _make_endpoint()
        session = _make_session(scalar_result=endpoint)

        svc = ProductRegistryService(make_session_factory(session))
        result = await svc.delete_endpoint(ENDPOINT_ID)

        assert result is True
        session.delete.assert_called_once_with(endpoint)

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        with pytest.raises(EndpointNotFoundError):
            await svc.delete_endpoint(ENDPOINT_ID)


# ---------------------------------------------------------------------------
# Bulk registration
# ---------------------------------------------------------------------------

class TestRegisterProductFull:
    """Tests for ProductRegistryService.register_product_full."""

    @pytest.mark.asyncio
    async def test_registers_product_with_environments_and_endpoints(self):
        svc = ProductRegistryService(make_session_factory(_make_session()))

        product_response = MagicMock()
        product_response.id = PRODUCT_ID

        env_response = MagicMock()
        env_response.id = ENV_ID

        svc.create_product = AsyncMock(return_value=product_response)
        svc.add_environment = AsyncMock(return_value=env_response)
        svc.add_endpoint = AsyncMock(return_value=MagicMock())

        product_data = _product_create_mock("My App")
        environments = [{"name": "production", "base_url": "https://example.com"}]
        endpoints = [
            {"env_name": "production", "path": "/health", "is_monitored": True}
        ]

        result = await svc.register_product_full(
            ORG_ID, product_data, environments, endpoints
        )

        svc.create_product.assert_called_once_with(ORG_ID, product_data)
        svc.add_environment.assert_called_once()
        svc.add_endpoint.assert_called_once()
        assert result is product_response

    @pytest.mark.asyncio
    async def test_registers_product_with_no_environments(self):
        svc = ProductRegistryService(make_session_factory(_make_session()))

        product_response = MagicMock()
        product_response.id = PRODUCT_ID

        svc.create_product = AsyncMock(return_value=product_response)
        svc.add_environment = AsyncMock()
        svc.add_endpoint = AsyncMock()

        result = await svc.register_product_full(
            ORG_ID, _product_create_mock("My App"), [], []
        )

        svc.create_product.assert_called_once()
        svc.add_environment.assert_not_called()
        svc.add_endpoint.assert_not_called()
        assert result is product_response

    @pytest.mark.asyncio
    async def test_endpoints_without_matching_env_skipped(self):
        svc = ProductRegistryService(make_session_factory(_make_session()))

        product_response = MagicMock()
        product_response.id = PRODUCT_ID
        env_response = MagicMock()
        env_response.id = ENV_ID

        svc.create_product = AsyncMock(return_value=product_response)
        svc.add_environment = AsyncMock(return_value=env_response)
        svc.add_endpoint = AsyncMock()

        environments = [{"name": "production", "base_url": "https://example.com"}]
        # Endpoint references a non-existent env name
        endpoints = [{"env_name": "does-not-exist", "path": "/health"}]

        await svc.register_product_full(
            ORG_ID, _product_create_mock("My App"), environments, endpoints
        )

        svc.add_endpoint.assert_not_called()


# ---------------------------------------------------------------------------
# Query operations
# ---------------------------------------------------------------------------

class TestGetProductWithEnvironments:
    """Tests for ProductRegistryService.get_product_with_environments."""

    @pytest.mark.asyncio
    async def test_returns_nested_dict_with_environments_and_endpoints(self):
        endpoint = _make_endpoint()
        env = _make_environment(endpoints=[endpoint])
        product = _make_product(environments=[env])
        session = _make_session(scalar_result=product)

        with (
            _patch("ProductResponse") as MockP,
            _patch("EnvironmentResponse") as MockE,
            _patch("EndpointResponse") as MockEP,
        ):
            MockP.model_validate.return_value = MagicMock()
            MockE.model_validate.return_value = MagicMock()
            MockEP.model_validate.return_value = MagicMock()

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.get_product_with_environments(PRODUCT_ID)

        assert "product" in result
        assert "environments" in result
        assert isinstance(result["environments"], list)
        assert len(result["environments"]) == 1
        assert "environment" in result["environments"][0]
        assert "endpoints" in result["environments"][0]

    @pytest.mark.asyncio
    async def test_raises_when_product_not_found(self):
        session = _make_session(scalar_result=None)
        svc = ProductRegistryService(make_session_factory(session))

        with pytest.raises(ProductNotFoundError):
            await svc.get_product_with_environments(PRODUCT_ID)


class TestFindProductsByRepo:
    """Tests for ProductRegistryService.find_products_by_repo."""

    @pytest.mark.asyncio
    async def test_returns_matching_products(self):
        repo_url = "https://github.com/acme/webapp"
        products = [_make_product(repository_url=repo_url)]
        session = _make_session(scalars_result=products)

        with _patch("ProductResponse") as MockResponse:
            MockResponse.model_validate.side_effect = lambda p, **kw: p

            svc = ProductRegistryService(make_session_factory(session))
            result = await svc.find_products_by_repo(repo_url)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_match(self):
        session = _make_session(scalars_result=[])
        svc = ProductRegistryService(make_session_factory(session))

        result = await svc.find_products_by_repo("https://github.com/missing/repo")

        assert result == []


class TestGetEndpointsForMonitoring:
    """Tests for ProductRegistryService.get_endpoints_for_monitoring."""

    @pytest.mark.asyncio
    async def test_returns_monitored_endpoints_across_all_products(self):
        env = _make_environment()
        endpoint = _make_endpoint(is_monitored=True, environment=env)
        session = _make_session(scalars_result=[endpoint])

        svc = ProductRegistryService(make_session_factory(session))
        result = await svc.get_endpoints_for_monitoring()

        assert len(result) == 1
        assert result[0]["endpoint"] is endpoint

    @pytest.mark.asyncio
    async def test_filters_by_product_id(self):
        env = _make_environment()
        endpoint = _make_endpoint(is_monitored=True, environment=env)
        session = _make_session(scalars_result=[endpoint])

        svc = ProductRegistryService(make_session_factory(session))
        result = await svc.get_endpoints_for_monitoring(product_id=PRODUCT_ID)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none_monitored(self):
        session = _make_session(scalars_result=[])
        svc = ProductRegistryService(make_session_factory(session))

        result = await svc.get_endpoints_for_monitoring()

        assert result == []


# ---------------------------------------------------------------------------
# Exception class tests
# ---------------------------------------------------------------------------

class TestExceptions:
    """Tests verifying the custom exception classes."""

    def test_product_not_found_stores_id_in_message(self):
        err = ProductNotFoundError(PRODUCT_ID)
        assert str(PRODUCT_ID) in str(err)
        assert err.product_id == PRODUCT_ID

    def test_environment_not_found_stores_id_in_message(self):
        err = EnvironmentNotFoundError(ENV_ID)
        assert str(ENV_ID) in str(err)
        assert err.env_id == ENV_ID

    def test_endpoint_not_found_stores_id_in_message(self):
        err = EndpointNotFoundError(ENDPOINT_ID)
        assert str(ENDPOINT_ID) in str(err)
        assert err.endpoint_id == ENDPOINT_ID

    def test_duplicate_product_stores_org_and_slug(self):
        err = DuplicateProductError(ORG_ID, "my-app")
        assert "my-app" in str(err)
        assert err.org_id == ORG_ID
        assert err.slug == "my-app"

    def test_duplicate_environment_stores_product_and_name(self):
        err = DuplicateEnvironmentError(PRODUCT_ID, "production")
        assert "production" in str(err)
        assert err.product_id == PRODUCT_ID
        assert err.name == "production"

    def test_all_exceptions_inherit_from_registry_error(self):
        from tinaa.registry.exceptions import RegistryError

        for exc_class, args in [
            (ProductNotFoundError, (PRODUCT_ID,)),
            (EnvironmentNotFoundError, (ENV_ID,)),
            (EndpointNotFoundError, (ENDPOINT_ID,)),
            (DuplicateProductError, (ORG_ID, "slug")),
            (DuplicateEnvironmentError, (PRODUCT_ID, "prod")),
        ]:
            assert isinstance(exc_class(*args), RegistryError)


# ---------------------------------------------------------------------------
# Private test helpers
# ---------------------------------------------------------------------------

def _product_create_mock(name: str, **extra: Any) -> MagicMock:
    """Build a minimal ProductCreate-like mock."""
    data = MagicMock()
    data.name = name
    data.repository_url = extra.get("repository_url", None)
    dump = {
        "name": name,
        "description": None,
        "repository_url": data.repository_url,
        "default_branch": "main",
        "status": "active",
        "config": {},
    }
    dump.update(extra)
    data.model_dump.return_value = dump
    return data


def _env_create_mock(name: str) -> MagicMock:
    """Build a minimal EnvironmentCreate-like mock."""
    data = MagicMock()
    data.name = name
    data.model_dump.return_value = {
        "name": name,
        "base_url": "https://example.com",
        "env_type": "production",
        "is_active": True,
        "monitoring_interval_seconds": 300,
    }
    return data


def _endpoint_create_mock() -> MagicMock:
    """Build a minimal EndpointCreate-like mock."""
    data = MagicMock()
    data.model_dump.return_value = {
        "path": "/health",
        "method": "GET",
        "is_monitored": True,
        "expected_status_code": 200,
    }
    return data


def _patch(name: str, return_value: Any = None):
    """Contextmanager: patch a name inside tinaa.registry.service."""
    from unittest.mock import patch as _unittest_patch

    target = f"tinaa.registry.service.{name}"
    if return_value is None:
        return _unittest_patch(target)
    # When return_value is a non-Mock ORM object we want the class constructor
    # to return it, and model_validate to also be a MagicMock.
    mock_cls = MagicMock()
    mock_cls.return_value = return_value
    mock_cls.model_validate = MagicMock()
    return _unittest_patch(target, mock_cls)
