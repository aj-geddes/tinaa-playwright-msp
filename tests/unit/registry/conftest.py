# tests/unit/registry/conftest.py
"""Inject stub model modules before registry service is imported.

The real SQLAlchemy ORM models require a live database metadata setup and
have complex dataclass-ordering constraints that prevent clean import in
unit tests.  This conftest installs minimal stub modules into ``sys.modules``
so that ``tinaa.registry.service`` can be imported and tested without
triggering any ORM machinery.

It also patches ``tinaa.registry.service.select`` with a MagicMock so that
``select(StubClass).where(...)`` calls do not hit real SQLAlchemy coercion
logic.  The mock session in each test ignores the statement value entirely.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Minimal stubs for Pydantic schemas and ORM classes
# ---------------------------------------------------------------------------

class _SchemaStub:
    """Minimal Pydantic BaseModel stub sufficient for unit tests."""

    model_config: dict = {}

    @classmethod
    def model_validate(cls, obj, **_kwargs):  # noqa: ANN001
        return obj

    def model_dump(self, **_kwargs):
        return {}


class ProductCreate(_SchemaStub):
    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class ProductUpdate(_SchemaStub):
    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class ProductResponse(_SchemaStub):
    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class EnvironmentCreate(_SchemaStub):
    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def model_dump(self, **_kwargs):
        return {k: v for k, v in self.__dict__.items()}


class EnvironmentResponse(_SchemaStub):
    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class EndpointCreate(_SchemaStub):
    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def model_dump(self, **_kwargs):
        return {k: v for k, v in self.__dict__.items()}


class EndpointResponse(_SchemaStub):
    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class Product:
    """ORM stub with class-level column descriptors for use in where() clauses."""

    # Class-level column descriptor stubs (SQLAlchemy uses these in .where())
    id = MagicMock(name="Product.id")
    organization_id = MagicMock(name="Product.organization_id")
    slug = MagicMock(name="Product.slug")
    status = MagicMock(name="Product.status")
    repository_url = MagicMock(name="Product.repository_url")
    name = MagicMock(name="Product.name")

    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


class Environment:
    """ORM stub with class-level column descriptors."""

    id = MagicMock(name="Environment.id")
    product_id = MagicMock(name="Environment.product_id")
    name = MagicMock(name="Environment.name")
    base_url = MagicMock(name="Environment.base_url")

    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


class Endpoint:
    """ORM stub with class-level column descriptors."""

    id = MagicMock(name="Endpoint.id")
    environment_id = MagicMock(name="Endpoint.environment_id")
    path = MagicMock(name="Endpoint.path")
    is_monitored = MagicMock(name="Endpoint.is_monitored")

    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


class Organization:
    pass


# ---------------------------------------------------------------------------
# Build stub modules
# ---------------------------------------------------------------------------

def _stub(name: str, **attrs: object) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


_STUBS: dict[str, types.ModuleType] = {
    "tinaa.models": _stub(
        "tinaa.models",
        Product=Product,
        ProductCreate=ProductCreate,
        ProductUpdate=ProductUpdate,
        ProductResponse=ProductResponse,
        Environment=Environment,
        EnvironmentCreate=EnvironmentCreate,
        EnvironmentResponse=EnvironmentResponse,
        Endpoint=Endpoint,
        EndpointCreate=EndpointCreate,
        EndpointResponse=EndpointResponse,
        Organization=Organization,
    ),
    "tinaa.models.product": _stub(
        "tinaa.models.product",
        Product=Product,
        ProductCreate=ProductCreate,
        ProductUpdate=ProductUpdate,
        ProductResponse=ProductResponse,
    ),
    "tinaa.models.environment": _stub(
        "tinaa.models.environment",
        Environment=Environment,
        EnvironmentCreate=EnvironmentCreate,
        EnvironmentResponse=EnvironmentResponse,
    ),
    "tinaa.models.endpoint": _stub(
        "tinaa.models.endpoint",
        Endpoint=Endpoint,
        EndpointCreate=EndpointCreate,
        EndpointResponse=EndpointResponse,
    ),
    "tinaa.models.organization": _stub(
        "tinaa.models.organization",
        Organization=Organization,
    ),
    "tinaa.database": _stub("tinaa.database"),
    "tinaa.database.session": _stub(
        "tinaa.database.session",
        get_session=MagicMock(),
    ),
}

# ---------------------------------------------------------------------------
# Load the registry service with stubs, then immediately restore real modules.
#
# Strategy:
#   1. Save any real modules that are about to be displaced.
#   2. Install stubs so the registry service import resolves against them.
#   3. Evict any cached registry modules and import fresh with stubs active.
#   4. Patch ``select`` on the loaded service to avoid ORM machinery.
#   5. Immediately restore real modules in sys.modules so that test modules
#      in OTHER packages that do inline imports are unaffected.
#
# The registry service module retains its bound references to the stub classes
# (captured at import time), so tests against the service still work correctly.
# ---------------------------------------------------------------------------

# Step 1 – save real modules that are currently in sys.modules.
_saved_real: dict[str, types.ModuleType] = {
    name: sys.modules[name]
    for name in _STUBS
    if name in sys.modules
}

# Step 2 – install stubs.
for _name, _mod in _STUBS.items():
    sys.modules[_name] = _mod

# Step 3 – evict cached registry modules so they re-resolve imports.
for _cached in list(sys.modules):
    if _cached in ("tinaa.registry.service", "tinaa.registry", "tinaa.registry.exceptions"):
        del sys.modules[_cached]

import tinaa.registry.exceptions  # noqa: E402  (re-import clean)
import tinaa.registry.service as _svc_module  # noqa: E402

# Step 4 – patch ``select`` so SQLAlchemy statement construction is skipped.
_select_mock = MagicMock(name="select")
_select_mock.return_value = MagicMock(name="select_result")
_svc_module.select = _select_mock

# Step 5 – restore real modules immediately so other packages are unaffected.
# Stubs are no longer in sys.modules; the service module itself still holds
# references to stub classes captured during its import in step 3.
for _name in _STUBS:
    sys.modules.pop(_name, None)
sys.modules.update(_saved_real)
