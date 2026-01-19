"""Controllers for non-model views (CustomView, ActionView, PageView, EmbedView)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Literal, cast

from litestar import Controller, Request, delete, get, post, put
from litestar.exceptions import NotFoundException, PermissionDeniedException
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from litestar_admin.registry import ViewRegistry  # noqa: TC001
from litestar_admin.views import ActionView, CustomView, EmbedView, PageView

if TYPE_CHECKING:
    from litestar_admin.views import ActionResult, ListResult

__all__ = [
    # Controllers
    "ActionsController",
    "CustomViewsController",
    "EmbedsController",
    "PagesController",
    # DTOs - CustomView
    "CustomViewDeleteResponse",
    "CustomViewInfo",
    "CustomViewListResponse",
    "CustomViewSchemaResponse",
    # DTOs - ActionView
    "ActionExecuteRequest",
    "ActionExecuteResponse",
    "ActionInfoResponse",
    # DTOs - PageView
    "PageContentResponse",
    "PageMetadataResponse",
    # DTOs - EmbedView
    "EmbedConfigResponse",
    "EmbedPropsResponse",
]


# =============================================================================
# CustomView DTOs
# =============================================================================


@dataclass
class CustomViewInfo:
    """Information about a registered custom view.

    Attributes:
        name: The display name of the view.
        identity: URL-safe identifier for the view.
        icon: Icon identifier for the view.
        category: Category grouping for the view.
        pk_field: Name of the primary key field.
        can_create: Whether new items can be created.
        can_edit: Whether items can be edited.
        can_delete: Whether items can be deleted.
        can_view_details: Whether item details can be viewed.
    """

    name: str
    identity: str
    icon: str = "table"
    category: str | None = None
    pk_field: str = "id"
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_view_details: bool = True


@dataclass
class CustomViewListResponse:
    """Response for listing custom view items with pagination.

    Attributes:
        items: List of item dictionaries.
        total: Total number of items matching the query.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        has_next: Whether there is a next page.
        has_prev: Whether there is a previous page.
    """

    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    has_next: bool = False
    has_prev: bool = False


@dataclass
class CustomViewDeleteResponse:
    """Response for delete operations.

    Attributes:
        success: Whether the deletion was successful.
        message: Optional message describing the result.
    """

    success: bool
    message: str = ""


@dataclass
class CustomViewSchemaResponse:
    """Response containing the schema for a custom view.

    Attributes:
        schema: JSON Schema dictionary describing the item structure.
        columns: List of column definitions.
    """

    schema: dict[str, Any]
    columns: list[dict[str, Any]]


# =============================================================================
# ActionView DTOs
# =============================================================================


@dataclass
class ActionInfoResponse:
    """Information about an action view.

    Attributes:
        name: The display name of the action.
        identity: URL-safe identifier for the action.
        icon: Icon identifier for the action.
        form_fields: List of form field definitions.
        confirmation_message: Message shown in confirmation dialog.
        requires_confirmation: Whether to show confirmation dialog.
        submit_label: Label for the submit button.
        dangerous: Whether this is a dangerous/destructive action.
    """

    name: str
    identity: str
    icon: str
    form_fields: list[dict[str, Any]]
    confirmation_message: str = ""
    requires_confirmation: bool = True
    submit_label: str = "Execute"
    dangerous: bool = False


@dataclass
class ActionExecuteRequest:
    """Request body for action execution.

    Attributes:
        data: Dictionary of form field values.
    """

    data: dict[str, Any]


@dataclass
class ActionExecuteResponse:
    """Response from action execution.

    Attributes:
        success: Whether the action completed successfully.
        message: Human-readable result message.
        redirect: Optional URL to redirect to after action completes.
        data: Optional additional data returned from the action.
        refresh: Whether to refresh the current view.
    """

    success: bool
    message: str
    redirect: str | None = None
    data: dict[str, Any] | None = None
    refresh: bool = False


# =============================================================================
# PageView DTOs
# =============================================================================


@dataclass
class PageMetadataResponse:
    """Metadata for a page view.

    Attributes:
        name: The display name of the page.
        identity: URL-safe identifier for the page.
        icon: Icon identifier for the page.
        content_type: Type of content (markdown, html, text, dynamic, template).
        layout: Page layout type.
        refresh_interval: Auto-refresh interval in seconds.
        content: Static content (for non-dynamic pages).
    """

    name: str
    identity: str
    icon: str
    content_type: Literal["markdown", "html", "text", "dynamic", "template"]
    layout: Literal["default", "full-width", "sidebar"] = "default"
    refresh_interval: int = 0
    content: str | None = None


@dataclass
class PageContentResponse:
    """Dynamic content response for a page view.

    Attributes:
        content: Dynamic content data from the page.
    """

    content: dict[str, Any]


# =============================================================================
# EmbedView DTOs
# =============================================================================


@dataclass
class EmbedConfigResponse:
    """Configuration for an embed view.

    Attributes:
        type: Embed type (iframe or component).
        width: CSS width value.
        height: CSS height value.
        min_height: CSS min-height value.
        layout: Layout mode (full, sidebar, card).
        refresh_interval: Auto-refresh interval in seconds.
        show_toolbar: Whether to show toolbar.
        url: URL for iframe embeds.
        sandbox: Iframe sandbox attributes.
        allow: Iframe allow attributes.
        loading: Iframe loading strategy.
        referrer_policy: Iframe referrer policy.
        component_name: Name of React component for component embeds.
        props: Static props for component embeds.
    """

    type: Literal["iframe", "component"]
    width: str = "100%"
    height: str = "100%"
    min_height: str = "400px"
    layout: Literal["full", "sidebar", "card"] = "full"
    refresh_interval: int = 0
    show_toolbar: bool = True
    # iframe-specific
    url: str | None = None
    sandbox: str | None = None
    allow: str | None = None
    loading: Literal["eager", "lazy"] | None = None
    referrer_policy: str | None = None
    # component-specific
    component_name: str | None = None
    props: dict[str, Any] | None = None


@dataclass
class EmbedPropsResponse:
    """Dynamic props for an embed view component.

    Attributes:
        props: Dictionary of props to pass to the component.
    """

    props: dict[str, Any]


# =============================================================================
# CustomViewsController
# =============================================================================


class CustomViewsController(Controller):
    """Controller for CRUD operations on CustomView data sources.

    Provides REST API endpoints for managing data from custom (non-model) views.
    CustomViews can connect to external APIs, in-memory data, files, or any
    custom data provider.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - GET /admin/api/custom - List all registered custom views
        - GET /admin/api/custom/{view_identity} - List items for a custom view
        - POST /admin/api/custom/{view_identity} - Create a new item
        - GET /admin/api/custom/{view_identity}/{item_id} - Get a single item
        - PUT /admin/api/custom/{view_identity}/{item_id} - Update an item
        - DELETE /admin/api/custom/{view_identity}/{item_id} - Delete an item
        - GET /admin/api/custom/{view_identity}/schema - Get schema
    """

    path = "/api/custom"
    tags: ClassVar[list[str]] = ["Custom Views"]

    @get(
        "/",
        status_code=HTTP_200_OK,
        summary="List registered custom views",
        description="Returns a list of all custom views registered with the admin panel.",
    )
    async def list_custom_views(
        self,
        admin_registry: ViewRegistry,
    ) -> list[CustomViewInfo]:
        """List all registered custom views with their metadata.

        Args:
            admin_registry: The view registry containing all registered views.

        Returns:
            List of custom view information objects.
        """
        views = cast("list[type[CustomView]]", admin_registry.list_custom_views())
        return [
            CustomViewInfo(
                name=view.name,
                identity=view.identity,
                icon=view.icon,
                category=view.category,
                pk_field=view.pk_field,
                can_create=view.can_create,
                can_edit=view.can_edit,
                can_delete=view.can_delete,
                can_view_details=view.can_view_details,
            )
            for view in views
        ]

    @get(
        "/{view_identity:str}",
        status_code=HTTP_200_OK,
        summary="List items for a custom view",
        description="Returns paginated items for a specific custom view.",
    )
    async def list_items(
        self,
        view_identity: str,
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
        page: int = 1,
        page_size: int = 25,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> CustomViewListResponse:
        """List items for a specific custom view with pagination and filtering.

        Args:
            view_identity: The identity of the registered custom view.
            request: The current request.
            admin_registry: The view registry.
            page: Page number (1-indexed).
            page_size: Number of items per page (max 100).
            sort_by: Field name to sort by.
            sort_order: Sort order ("asc" or "desc").
            search: Search string for searchable columns.

        Returns:
            Paginated response with items and total count.

        Raises:
            NotFoundException: If the view is not registered.
            PermissionDeniedException: If the user cannot access the view.
        """
        view_class = _get_custom_view(admin_registry, view_identity)

        # Check access
        if not await view_class.is_accessible(request):
            raise PermissionDeniedException(f"Access denied to view '{view_identity}'")

        # Validate and cap parameters
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        # Instantiate view and fetch data
        view_instance = view_class()
        result: ListResult = await view_instance.get_list(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )

        return CustomViewListResponse(
            items=result.items,
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            has_next=result.has_next,
            has_prev=result.has_prev,
        )

    @get(
        "/{view_identity:str}/schema",
        status_code=HTTP_200_OK,
        summary="Get custom view schema",
        description="Returns the schema and column definitions for a custom view.",
    )
    async def get_schema(
        self,
        view_identity: str,
        admin_registry: ViewRegistry,
    ) -> CustomViewSchemaResponse:
        """Get the JSON schema and column definitions for a custom view.

        Args:
            view_identity: The identity of the registered custom view.
            admin_registry: The view registry.

        Returns:
            Schema response with JSON schema and column definitions.

        Raises:
            NotFoundException: If the view is not registered.
        """
        view_class = _get_custom_view(admin_registry, view_identity)

        schema = view_class.get_schema()
        columns = [
            {
                "name": col.name,
                "label": col.label,
                "type": col.type,
                "sortable": col.sortable,
                "searchable": col.searchable,
                "filterable": col.filterable,
                "visible": col.visible,
                "format": col.format,
            }
            for col in view_class.get_list_columns()
        ]

        return CustomViewSchemaResponse(schema=schema, columns=columns)

    @get(
        "/{view_identity:str}/{item_id:str}",
        status_code=HTTP_200_OK,
        summary="Get a single item",
        description="Returns a single item by its identifier.",
    )
    async def get_item(
        self,
        view_identity: str,
        item_id: str,
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
    ) -> dict[str, Any]:
        """Get a single item by identifier.

        Args:
            view_identity: The identity of the registered custom view.
            item_id: The item identifier.
            request: The current request.
            admin_registry: The view registry.

        Returns:
            The item as a dictionary.

        Raises:
            NotFoundException: If the view or item is not found.
            PermissionDeniedException: If the user cannot access the view.
        """
        view_class = _get_custom_view(admin_registry, view_identity)

        if not await view_class.is_accessible(request):
            raise PermissionDeniedException(f"Access denied to view '{view_identity}'")

        view_instance = view_class()
        item = await view_instance.get_one(item_id)

        if item is None:
            raise NotFoundException(f"Item '{item_id}' not found in '{view_identity}'")

        return item

    @post(
        "/{view_identity:str}",
        status_code=HTTP_201_CREATED,
        summary="Create a new item",
        description="Creates a new item in the custom view.",
    )
    async def create_item(
        self,
        view_identity: str,
        data: dict[str, Any],
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
    ) -> dict[str, Any]:
        """Create a new item in a custom view.

        Args:
            view_identity: The identity of the registered custom view.
            data: The item data to create.
            request: The current request.
            admin_registry: The view registry.

        Returns:
            The created item as a dictionary.

        Raises:
            NotFoundException: If the view is not registered.
            PermissionDeniedException: If the user cannot create items.
        """
        view_class = _get_custom_view(admin_registry, view_identity)

        if not view_class.can_create:
            raise PermissionDeniedException(f"Create not allowed for view '{view_identity}'")

        if not await view_class.can_create_item(request):
            raise PermissionDeniedException(f"Access denied to create in view '{view_identity}'")

        view_instance = view_class()

        # Run pre-create hook
        data = await view_instance.on_before_create(data)

        # Create the item
        item = await view_instance.create(data)

        # Run post-create hook
        await view_instance.on_after_create(item)

        return item

    @put(
        "/{view_identity:str}/{item_id:str}",
        status_code=HTTP_200_OK,
        summary="Update an item",
        description="Updates an existing item in the custom view.",
    )
    async def update_item(
        self,
        view_identity: str,
        item_id: str,
        data: dict[str, Any],
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
    ) -> dict[str, Any]:
        """Update an existing item.

        Args:
            view_identity: The identity of the registered custom view.
            item_id: The item identifier.
            data: The fields to update.
            request: The current request.
            admin_registry: The view registry.

        Returns:
            The updated item as a dictionary.

        Raises:
            NotFoundException: If the view or item is not found.
            PermissionDeniedException: If the user cannot edit items.
        """
        view_class = _get_custom_view(admin_registry, view_identity)

        if not view_class.can_edit:
            raise PermissionDeniedException(f"Edit not allowed for view '{view_identity}'")

        view_instance = view_class()

        # Get existing item to check permissions
        existing_item = await view_instance.get_one(item_id)
        if existing_item is None:
            raise NotFoundException(f"Item '{item_id}' not found in '{view_identity}'")

        if not await view_class.can_edit_item(request, existing_item):
            raise PermissionDeniedException(f"Access denied to edit item '{item_id}'")

        # Run pre-update hook
        data = await view_instance.on_before_update(item_id, data)

        # Update the item
        item = await view_instance.update(item_id, data)

        # Run post-update hook
        await view_instance.on_after_update(item)

        return item

    @delete(
        "/{view_identity:str}/{item_id:str}",
        status_code=HTTP_200_OK,
        summary="Delete an item",
        description="Deletes an item from the custom view.",
    )
    async def delete_item(
        self,
        view_identity: str,
        item_id: str,
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
    ) -> CustomViewDeleteResponse:
        """Delete an item by identifier.

        Args:
            view_identity: The identity of the registered custom view.
            item_id: The item identifier.
            request: The current request.
            admin_registry: The view registry.

        Returns:
            Delete response indicating success.

        Raises:
            NotFoundException: If the view or item is not found.
            PermissionDeniedException: If the user cannot delete items.
        """
        view_class = _get_custom_view(admin_registry, view_identity)

        if not view_class.can_delete:
            raise PermissionDeniedException(f"Delete not allowed for view '{view_identity}'")

        view_instance = view_class()

        # Get existing item to check permissions
        existing_item = await view_instance.get_one(item_id)
        if existing_item is None:
            raise NotFoundException(f"Item '{item_id}' not found in '{view_identity}'")

        if not await view_class.can_delete_item(request, existing_item):
            raise PermissionDeniedException(f"Access denied to delete item '{item_id}'")

        # Run pre-delete hook
        await view_instance.on_before_delete(item_id)

        # Delete the item
        success = await view_instance.delete(item_id)

        if not success:
            raise NotFoundException(f"Item '{item_id}' not found in '{view_identity}'")

        # Run post-delete hook
        await view_instance.on_after_delete(item_id)

        return CustomViewDeleteResponse(success=True, message=f"Item '{item_id}' deleted successfully")


# =============================================================================
# ActionsController
# =============================================================================


class ActionsController(Controller):
    """Controller for ActionView endpoints.

    Provides REST API endpoints for admin actions. Actions are one-off operations
    that don't directly map to CRUD operations, such as cache clearing, data
    export, or maintenance tasks.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - GET /admin/api/actions - List all registered actions
        - GET /admin/api/actions/{view_identity} - Get action metadata
        - POST /admin/api/actions/{view_identity}/execute - Execute action
    """

    path = "/api/actions"
    tags: ClassVar[list[str]] = ["Actions"]

    @get(
        "/",
        status_code=HTTP_200_OK,
        summary="List registered actions",
        description="Returns a list of all actions registered with the admin panel.",
    )
    async def list_actions(
        self,
        admin_registry: ViewRegistry,
    ) -> list[ActionInfoResponse]:
        """List all registered action views with their metadata.

        Args:
            admin_registry: The view registry containing all registered views.

        Returns:
            List of action information objects.
        """
        views = cast("list[type[ActionView]]", admin_registry.list_action_views())
        return [
            ActionInfoResponse(
                name=view.name,
                identity=view.identity,
                icon=view.icon,
                form_fields=view.get_form_schema(),
                confirmation_message=view.confirmation_message,
                requires_confirmation=view.requires_confirmation,
                submit_label=view.submit_label,
                dangerous=view.dangerous,
            )
            for view in views
        ]

    @get(
        "/{view_identity:str}",
        status_code=HTTP_200_OK,
        summary="Get action metadata",
        description="Returns metadata for a specific action including form fields.",
    )
    async def get_action_info(
        self,
        view_identity: str,
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
    ) -> ActionInfoResponse:
        """Get metadata for a specific action.

        Args:
            view_identity: The identity of the registered action.
            request: The current request.
            admin_registry: The view registry.

        Returns:
            Action metadata including form field definitions.

        Raises:
            NotFoundException: If the action is not registered.
            PermissionDeniedException: If the user cannot access the action.
        """
        view_class = _get_action_view(admin_registry, view_identity)

        if not await view_class.is_accessible(request):
            raise PermissionDeniedException(f"Access denied to action '{view_identity}'")

        return ActionInfoResponse(
            name=view_class.name,
            identity=view_class.identity,
            icon=view_class.icon,
            form_fields=view_class.get_form_schema(),
            confirmation_message=view_class.confirmation_message,
            requires_confirmation=view_class.requires_confirmation,
            submit_label=view_class.submit_label,
            dangerous=view_class.dangerous,
        )

    @post(
        "/{view_identity:str}/execute",
        status_code=HTTP_200_OK,
        summary="Execute an action",
        description="Executes the action with the provided form data.",
    )
    async def execute_action(
        self,
        view_identity: str,
        data: dict[str, Any],
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
    ) -> ActionExecuteResponse:
        """Execute an action with the provided form data.

        Args:
            view_identity: The identity of the registered action.
            data: Dictionary of form field values.
            request: The current request.
            admin_registry: The view registry.

        Returns:
            Action execution result.

        Raises:
            NotFoundException: If the action is not registered.
            PermissionDeniedException: If the user cannot execute the action.
        """
        view_class = _get_action_view(admin_registry, view_identity)

        if not await view_class.can_execute(request):
            raise PermissionDeniedException(f"Access denied to execute action '{view_identity}'")

        # Validate the form data
        is_valid, error_message = await view_class.validate_data(data)
        if not is_valid:
            return ActionExecuteResponse(
                success=False,
                message=error_message or "Validation failed",
            )

        # Execute the action
        view_instance = view_class()
        try:
            result: ActionResult = await view_instance.execute(data)
            return ActionExecuteResponse(
                success=result.success,
                message=result.message,
                redirect=result.redirect,
                data=result.data,
                refresh=result.refresh,
            )
        except Exception as exc:
            return ActionExecuteResponse(
                success=False,
                message=f"Action failed: {exc!s}",
            )


# =============================================================================
# PagesController
# =============================================================================


class PagesController(Controller):
    """Controller for PageView endpoints.

    Provides REST API endpoints for custom content pages. Pages can contain
    static content (markdown, HTML) or dynamic content fetched at request time.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - GET /admin/api/pages - List all registered pages
        - GET /admin/api/pages/{view_identity} - Get page metadata
        - GET /admin/api/pages/{view_identity}/content - Get dynamic content
    """

    path = "/api/pages"
    tags: ClassVar[list[str]] = ["Pages"]

    @get(
        "/",
        status_code=HTTP_200_OK,
        summary="List registered pages",
        description="Returns a list of all pages registered with the admin panel.",
    )
    async def list_pages(
        self,
        admin_registry: ViewRegistry,
    ) -> list[PageMetadataResponse]:
        """List all registered page views with their metadata.

        Args:
            admin_registry: The view registry containing all registered views.

        Returns:
            List of page metadata objects.
        """
        views = cast("list[type[PageView]]", admin_registry.list_page_views())
        return [
            PageMetadataResponse(
                name=view.name,
                identity=view.identity,
                icon=view.icon,
                content_type=view.content_type,
                layout=view.layout,
                refresh_interval=view.refresh_interval,
                content=view.content if view.content_type in ("markdown", "html", "text") else None,
            )
            for view in views
        ]

    @get(
        "/{view_identity:str}",
        status_code=HTTP_200_OK,
        summary="Get page metadata",
        description="Returns metadata for a specific page.",
    )
    async def get_page_metadata(
        self,
        view_identity: str,
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
    ) -> PageMetadataResponse:
        """Get metadata for a specific page.

        Args:
            view_identity: The identity of the registered page.
            request: The current request.
            admin_registry: The view registry.

        Returns:
            Page metadata including content type and static content.

        Raises:
            NotFoundException: If the page is not registered.
            PermissionDeniedException: If the user cannot access the page.
        """
        view_class = _get_page_view(admin_registry, view_identity)

        if not await view_class.is_accessible(request):
            raise PermissionDeniedException(f"Access denied to page '{view_identity}'")

        return PageMetadataResponse(
            name=view_class.name,
            identity=view_class.identity,
            icon=view_class.icon,
            content_type=view_class.content_type,
            layout=view_class.layout,
            refresh_interval=view_class.refresh_interval,
            content=view_class.content if view_class.content_type in ("markdown", "html", "text") else None,
        )

    @get(
        "/{view_identity:str}/content",
        status_code=HTTP_200_OK,
        summary="Get page content",
        description="Returns dynamic content for a page.",
    )
    async def get_page_content(
        self,
        view_identity: str,
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
    ) -> PageContentResponse:
        """Get dynamic content for a page.

        This endpoint is used for pages with content_type="dynamic" to fetch
        runtime-generated content.

        Args:
            view_identity: The identity of the registered page.
            request: The current request.
            admin_registry: The view registry.

        Returns:
            Page content data.

        Raises:
            NotFoundException: If the page is not registered.
            PermissionDeniedException: If the user cannot access the page.
        """
        view_class = _get_page_view(admin_registry, view_identity)

        if not await view_class.is_accessible(request):
            raise PermissionDeniedException(f"Access denied to page '{view_identity}'")

        view_instance = view_class()
        content = await view_instance.get_content()

        return PageContentResponse(content=content)


# =============================================================================
# EmbedsController
# =============================================================================


class EmbedsController(Controller):
    """Controller for EmbedView endpoints.

    Provides REST API endpoints for embedded content. Embeds can be iframes
    pointing to external dashboards or custom React components.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - GET /admin/api/embeds - List all registered embeds
        - GET /admin/api/embeds/{view_identity}/config - Get embed configuration
        - GET /admin/api/embeds/{view_identity}/props - Get dynamic props
    """

    path = "/api/embeds"
    tags: ClassVar[list[str]] = ["Embeds"]

    @get(
        "/",
        status_code=HTTP_200_OK,
        summary="List registered embeds",
        description="Returns a list of all embeds registered with the admin panel.",
    )
    async def list_embeds(
        self,
        admin_registry: ViewRegistry,
    ) -> list[EmbedConfigResponse]:
        """List all registered embed views with their configurations.

        Args:
            admin_registry: The view registry containing all registered views.

        Returns:
            List of embed configuration objects.
        """
        views = cast("list[type[EmbedView]]", admin_registry.list_embed_views())
        result: list[EmbedConfigResponse] = []

        for view in views:
            config = EmbedConfigResponse(
                type=view.embed_type,
                width=view.width,
                height=view.height,
                min_height=view.min_height,
                layout=view.layout,
                refresh_interval=view.refresh_interval,
                show_toolbar=view.show_toolbar,
            )

            if view.embed_type == "iframe":
                config.url = view.embed_url
                config.sandbox = view.sandbox
                config.allow = view.allow
                config.loading = view.loading
                config.referrer_policy = view.referrer_policy
            else:
                config.component_name = view.component_name
                config.props = view.props

            result.append(config)

        return result

    @get(
        "/{view_identity:str}/config",
        status_code=HTTP_200_OK,
        summary="Get embed configuration",
        description="Returns the full configuration for an embed view.",
    )
    async def get_embed_config(
        self,
        view_identity: str,
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
    ) -> EmbedConfigResponse:
        """Get the configuration for a specific embed.

        Args:
            view_identity: The identity of the registered embed.
            request: The current request.
            admin_registry: The view registry.

        Returns:
            Embed configuration including URL/component settings.

        Raises:
            NotFoundException: If the embed is not registered.
            PermissionDeniedException: If the user cannot access the embed.
        """
        view_class = _get_embed_view(admin_registry, view_identity)

        if not await view_class.is_accessible(request):
            raise PermissionDeniedException(f"Access denied to embed '{view_identity}'")

        # Get full config with dynamic values resolved
        view_instance = view_class()
        full_config = await view_instance.get_full_config(request)

        config = EmbedConfigResponse(
            type=full_config.get("type", "iframe"),
            width=full_config.get("width", "100%"),
            height=full_config.get("height", "100%"),
            min_height=full_config.get("min_height", "400px"),
            layout=full_config.get("layout", "full"),
            refresh_interval=full_config.get("refresh_interval", 0),
            show_toolbar=full_config.get("show_toolbar", True),
        )

        if config.type == "iframe":
            config.url = full_config.get("url")
            config.sandbox = full_config.get("sandbox")
            config.allow = full_config.get("allow")
            config.loading = full_config.get("loading")
            config.referrer_policy = full_config.get("referrer_policy")
        else:
            config.component_name = full_config.get("component_name")
            config.props = full_config.get("props")

        return config

    @get(
        "/{view_identity:str}/props",
        status_code=HTTP_200_OK,
        summary="Get embed props",
        description="Returns dynamic props for a component embed.",
    )
    async def get_embed_props(
        self,
        view_identity: str,
        request: Request[Any, Any, Any],
        admin_registry: ViewRegistry,
    ) -> EmbedPropsResponse:
        """Get dynamic props for an embed component.

        This endpoint is primarily used for component embeds to fetch
        runtime-generated props.

        Args:
            view_identity: The identity of the registered embed.
            request: The current request.
            admin_registry: The view registry.

        Returns:
            Dictionary of props for the component.

        Raises:
            NotFoundException: If the embed is not registered.
            PermissionDeniedException: If the user cannot access the embed.
        """
        view_class = _get_embed_view(admin_registry, view_identity)

        if not await view_class.is_accessible(request):
            raise PermissionDeniedException(f"Access denied to embed '{view_identity}'")

        view_instance = view_class()
        props = await view_instance.get_props(request)

        return EmbedPropsResponse(props=props)


# =============================================================================
# Helper Functions
# =============================================================================


def _get_custom_view(registry: ViewRegistry, identity: str) -> type[CustomView]:
    """Get a CustomView class by identity.

    Args:
        registry: The view registry.
        identity: The view identity.

    Returns:
        The CustomView class.

    Raises:
        NotFoundException: If the view is not found or is not a CustomView.
    """
    try:
        view_class = registry.get_view_by_name(identity)
    except KeyError as exc:
        raise NotFoundException(f"Custom view '{identity}' not found") from exc

    if not issubclass(view_class, CustomView):
        raise NotFoundException(f"View '{identity}' is not a custom view")

    return view_class


def _get_action_view(registry: ViewRegistry, identity: str) -> type[ActionView]:
    """Get an ActionView class by identity.

    Args:
        registry: The view registry.
        identity: The view identity.

    Returns:
        The ActionView class.

    Raises:
        NotFoundException: If the view is not found or is not an ActionView.
    """
    try:
        view_class = registry.get_view_by_name(identity)
    except KeyError as exc:
        raise NotFoundException(f"Action '{identity}' not found") from exc

    if not issubclass(view_class, ActionView):
        raise NotFoundException(f"View '{identity}' is not an action view")

    return view_class


def _get_page_view(registry: ViewRegistry, identity: str) -> type[PageView]:
    """Get a PageView class by identity.

    Args:
        registry: The view registry.
        identity: The view identity.

    Returns:
        The PageView class.

    Raises:
        NotFoundException: If the view is not found or is not a PageView.
    """
    try:
        view_class = registry.get_view_by_name(identity)
    except KeyError as exc:
        raise NotFoundException(f"Page '{identity}' not found") from exc

    if not issubclass(view_class, PageView):
        raise NotFoundException(f"View '{identity}' is not a page view")

    return view_class


def _get_embed_view(registry: ViewRegistry, identity: str) -> type[EmbedView]:
    """Get an EmbedView class by identity.

    Args:
        registry: The view registry.
        identity: The view identity.

    Returns:
        The EmbedView class.

    Raises:
        NotFoundException: If the view is not found or is not an EmbedView.
    """
    try:
        view_class = registry.get_view_by_name(identity)
    except KeyError as exc:
        raise NotFoundException(f"Embed '{identity}' not found") from exc

    if not issubclass(view_class, EmbedView):
        raise NotFoundException(f"View '{identity}' is not an embed view")

    return view_class
