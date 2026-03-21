# tinaa/registry/exceptions.py
"""Custom exceptions for the Product Registry Service."""


class RegistryError(Exception):
    """Base exception for registry errors."""


class ProductNotFoundError(RegistryError):
    """Raised when a product cannot be found by its identifier."""

    def __init__(self, product_id: object) -> None:
        super().__init__(f"Product not found: {product_id}")
        self.product_id = product_id


class EnvironmentNotFoundError(RegistryError):
    """Raised when an environment cannot be found by its identifier."""

    def __init__(self, env_id: object) -> None:
        super().__init__(f"Environment not found: {env_id}")
        self.env_id = env_id


class EndpointNotFoundError(RegistryError):
    """Raised when an endpoint cannot be found by its identifier."""

    def __init__(self, endpoint_id: object) -> None:
        super().__init__(f"Endpoint not found: {endpoint_id}")
        self.endpoint_id = endpoint_id


class DuplicateProductError(RegistryError):
    """Raised when a product slug already exists within an organization."""

    def __init__(self, org_id: object, slug: str) -> None:
        super().__init__(f"Product with slug '{slug}' already exists in organization {org_id}")
        self.org_id = org_id
        self.slug = slug


class DuplicateEnvironmentError(RegistryError):
    """Raised when an environment name already exists within a product."""

    def __init__(self, product_id: object, name: str) -> None:
        super().__init__(f"Environment '{name}' already exists in product {product_id}")
        self.product_id = product_id
        self.name = name
