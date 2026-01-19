"""HTTP API data provider for CustomView.

This module provides an HTTPAPIView class that fetches data from
external HTTP APIs, enabling admin interfaces for third-party services.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, ClassVar, Literal

from litestar_admin.views.custom import CustomView, ListResult

__all__ = ["HTTPAPIView"]


class HTTPAPIView(CustomView):
    """CustomView that fetches data from an external HTTP API.

    This view enables creating admin interfaces for external REST APIs,
    useful for:
    - Managing third-party service data
    - Aggregating data from multiple microservices
    - Creating unified admin panels for distributed systems
    - Read-only dashboards for external data sources

    Note:
        This implementation requires the httpx package for async HTTP requests.
        Install with: pip install httpx

    Attributes:
        api_base_url: Base URL for the API (must be set by subclass).
        api_headers: Default headers to include in all requests.
        api_timeout: Request timeout in seconds.
        list_endpoint: Endpoint path for listing items (relative to base URL).
        detail_endpoint: Endpoint path template for single item (uses {id} placeholder).
        create_endpoint: Endpoint path for creating items.
        update_endpoint: Endpoint path template for updating items.
        delete_endpoint: Endpoint path template for deleting items.
        items_key: Key in response JSON containing the items list.
        total_key: Key in response JSON containing total count.
        page_param: Query parameter name for page number.
        page_size_param: Query parameter name for page size.
        search_param: Query parameter name for search.
        sort_param: Query parameter name for sort field.
        order_param: Query parameter name for sort order.

    Example::

        class GitHubReposView(HTTPAPIView):
            name = "GitHub Repositories"
            icon = "github"
            api_base_url = "https://api.github.com"
            api_headers = {"Accept": "application/vnd.github.v3+json"}
            list_endpoint = "/users/{username}/repos"
            detail_endpoint = "/repos/{owner}/{repo}"
            items_key = None  # Response is a list directly
            pk_field = "id"

            columns = [
                ColumnDefinition(name="id", type="integer"),
                ColumnDefinition(name="name", type="string", sortable=True),
                ColumnDefinition(name="full_name", type="string"),
                ColumnDefinition(name="description", type="text", searchable=True),
                ColumnDefinition(name="stargazers_count", type="integer", sortable=True),
                ColumnDefinition(name="html_url", type="url"),
            ]

            # Custom parameters for this API
            username = "octocat"

            async def get_list(self, **kwargs) -> ListResult:
                # Override to customize the request
                endpoint = self.list_endpoint.format(username=self.username)
                return await self._fetch_list(endpoint, **kwargs)
    """

    # API configuration (must be set by subclass)
    api_base_url: ClassVar[str] = ""
    api_headers: ClassVar[dict[str, str]] = {}
    api_timeout: ClassVar[float] = 30.0

    # Endpoint paths (relative to base URL)
    list_endpoint: ClassVar[str] = ""
    detail_endpoint: ClassVar[str] = "/{id}"
    create_endpoint: ClassVar[str] = ""
    update_endpoint: ClassVar[str] = "/{id}"
    delete_endpoint: ClassVar[str] = "/{id}"

    # Response parsing
    items_key: ClassVar[str | None] = "items"  # Key containing items list, None if root is list
    total_key: ClassVar[str | None] = "total"  # Key containing total count, None to use len(items)

    # Request parameter names
    page_param: ClassVar[str] = "page"
    page_size_param: ClassVar[str] = "page_size"
    search_param: ClassVar[str] = "search"
    sort_param: ClassVar[str] = "sort_by"
    order_param: ClassVar[str] = "sort_order"

    # HTTP API views are typically read-only by default
    can_create: ClassVar[bool] = False
    can_edit: ClassVar[bool] = False
    can_delete: ClassVar[bool] = False

    @classmethod
    def _get_base_url(cls) -> str:
        """Get the API base URL.

        Returns:
            The base URL string.

        Raises:
            ValueError: If api_base_url is not set.
        """
        if not cls.api_base_url:
            msg = f"{cls.__name__} must define 'api_base_url' class attribute"
            raise ValueError(msg)
        return cls.api_base_url.rstrip("/")

    @classmethod
    def _get_httpx_client(cls) -> Any:
        """Get an httpx AsyncClient instance.

        Returns:
            Configured httpx.AsyncClient.

        Raises:
            ImportError: If httpx is not installed.
        """
        try:
            import httpx
        except ImportError as e:
            msg = "httpx is required for HTTPAPIView. Install with: pip install httpx"
            raise ImportError(msg) from e

        return httpx.AsyncClient(
            base_url=cls._get_base_url(),
            headers=cls.api_headers,
            timeout=cls.api_timeout,
        )

    async def _fetch_list(
        self,
        endpoint: str,
        page: int = 1,
        page_size: int = 25,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> ListResult:
        """Fetch a list of items from the API.

        This is a helper method that can be called from get_list implementations.

        Args:
            endpoint: API endpoint path.
            page: Page number.
            page_size: Items per page.
            filters: Filter parameters.
            sort_by: Sort field.
            sort_order: Sort direction.
            search: Search query.

        Returns:
            ListResult with items and pagination info.
        """
        params: dict[str, Any] = {
            self.page_param: page,
            self.page_size_param: page_size,
        }

        if search:
            params[self.search_param] = search

        if sort_by:
            params[self.sort_param] = sort_by
            params[self.order_param] = sort_order

        if filters:
            params.update(filters)

        async with self._get_httpx_client() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

        # Parse response - extract items from response data
        items = data.get(self.items_key, []) if self.items_key else (data if isinstance(data, list) else [])

        # Extract total count from response or use items length
        total = data.get(self.total_key, len(items)) if self.total_key and isinstance(data, dict) else len(items)

        return ListResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def _fetch_one(self, endpoint: str) -> dict[str, Any] | None:
        """Fetch a single item from the API.

        Args:
            endpoint: API endpoint path.

        Returns:
            Item data or None if not found.
        """
        async with self._get_httpx_client() as client:
            response = await client.get(endpoint)
            if response.status_code == HTTPStatus.NOT_FOUND:
                return None
            response.raise_for_status()
            return response.json()

    async def get_list(
        self,
        page: int = 1,
        page_size: int = 25,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> ListResult:
        """Retrieve a paginated list of items from the API.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            filters: Dictionary of filter field names to values.
            sort_by: Field name to sort by.
            sort_order: Sort direction ("asc" or "desc").
            search: Search query string.

        Returns:
            ListResult containing items and pagination info.
        """
        endpoint = self.list_endpoint or ""
        return await self._fetch_list(
            endpoint,
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )

    async def get_one(self, item_id: str) -> dict[str, Any] | None:
        """Retrieve a single item by its identifier.

        Args:
            item_id: The unique identifier for the item.

        Returns:
            Item data as a dictionary, or None if not found.
        """
        endpoint = self.detail_endpoint.format(id=item_id)
        return await self._fetch_one(endpoint)

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new item via the API.

        Args:
            data: Dictionary of field values for the new item.

        Returns:
            The created item data from the API response.
        """
        # Call pre-create hook
        data = await self.on_before_create(data)

        endpoint = self.create_endpoint or self.list_endpoint or ""

        async with self._get_httpx_client() as client:
            response = await client.post(endpoint, json=data)
            response.raise_for_status()
            result = response.json()

        # Call post-create hook
        await self.on_after_create(result)

        return result

    async def update(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing item via the API.

        Args:
            item_id: The unique identifier for the item.
            data: Dictionary of field values to update.

        Returns:
            The updated item data from the API response.
        """
        # Call pre-update hook
        data = await self.on_before_update(item_id, data)

        endpoint = self.update_endpoint.format(id=item_id)

        async with self._get_httpx_client() as client:
            response = await client.patch(endpoint, json=data)
            response.raise_for_status()
            result = response.json()

        # Call post-update hook
        await self.on_after_update(result)

        return result

    async def delete(self, item_id: str) -> bool:
        """Delete an item via the API.

        Args:
            item_id: The unique identifier for the item to delete.

        Returns:
            True if deletion was successful.
        """
        # Call pre-delete hook
        await self.on_before_delete(item_id)

        endpoint = self.delete_endpoint.format(id=item_id)

        async with self._get_httpx_client() as client:
            response = await client.delete(endpoint)
            response.raise_for_status()

        # Call post-delete hook
        await self.on_after_delete(item_id)

        return True
