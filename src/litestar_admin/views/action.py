"""ActionView class for one-off admin operations."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from litestar_admin.views.admin_view import BaseAdminView

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = ["ActionResult", "ActionView", "FormField"]


@dataclass
class FormField:
    """Definition for a form field in an action view.

    Attributes:
        name: The field identifier/name.
        label: Display label for the field.
        field_type: The type of form input (text, select, checkbox, etc.).
        required: Whether the field is required.
        default: Default value for the field.
        placeholder: Placeholder text for input fields.
        help_text: Help text displayed below the field.
        options: Options for select/radio fields as list of {value, label} dicts.
        validation: Optional validation rules (min, max, pattern, etc.).

    Example::

        FormField(
            name="cache_type",
            label="Cache Type",
            field_type="select",
            required=True,
            options=[
                {"value": "all", "label": "All Caches"},
                {"value": "user", "label": "User Cache"},
                {"value": "session", "label": "Session Cache"},
            ],
        )
    """

    name: str
    label: str
    field_type: Literal[
        "text",
        "textarea",
        "number",
        "email",
        "password",
        "select",
        "multiselect",
        "checkbox",
        "radio",
        "date",
        "datetime",
        "file",
        "hidden",
    ] = "text"
    required: bool = False
    default: Any = None
    placeholder: str = ""
    help_text: str = ""
    options: list[dict[str, str]] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON serialization.

        Returns:
            Dictionary with all field properties.
        """
        return {
            "name": self.name,
            "label": self.label,
            "type": self.field_type,
            "required": self.required,
            "default": self.default,
            "placeholder": self.placeholder,
            "helpText": self.help_text,
            "options": self.options,
            "validation": self.validation,
        }


@dataclass
class ActionResult:
    """Result of an action execution.

    Attributes:
        success: Whether the action completed successfully.
        message: Human-readable result message.
        redirect: Optional URL to redirect to after action completes.
        data: Optional additional data to return to the frontend.
        refresh: Whether to refresh the current view after action.

    Example::

        ActionResult(
            success=True,
            message="Cache cleared successfully!",
            data={"cleared_entries": 1523},
        )

        ActionResult(
            success=False,
            message="Failed to send emails: SMTP server unavailable",
        )

        ActionResult(
            success=True,
            message="Export complete",
            redirect="/admin/exports/download/123",
        )
    """

    success: bool
    message: str
    redirect: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    refresh: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON serialization.

        Returns:
            Dictionary with result properties.
        """
        return {
            "success": self.success,
            "message": self.message,
            "redirect": self.redirect,
            "data": self.data,
            "refresh": self.refresh,
        }


class ActionView(BaseAdminView):
    """Base class for admin action views.

    ActionView is used for one-off operations that don't directly map to CRUD
    operations on a model. Examples include:

    - Running database cleanup/maintenance tasks
    - Sending bulk notifications
    - Regenerating caches
    - Importing/exporting data
    - Running scheduled jobs manually

    Subclasses must implement the `execute` method which performs the actual
    action logic.

    Attributes:
        view_type: Always "action" for action views.
        form_fields: List of FormField definitions for action inputs.
        confirmation_message: Optional message shown in confirmation dialog.
        requires_confirmation: Whether to show a confirmation dialog.
        submit_label: Label for the submit button.
        success_redirect: Optional URL to redirect to on success.
        dangerous: Whether this is a dangerous/destructive action (affects styling).

    Example::

        from litestar_admin.views import ActionView, ActionResult, FormField


        class ClearCacheAction(ActionView):
            name = "Clear Cache"
            icon = "trash"
            category = "Maintenance"
            confirmation_message = "Are you sure you want to clear the cache?"

            form_fields = [
                FormField(
                    name="cache_type",
                    label="Cache Type",
                    field_type="select",
                    required=True,
                    options=[
                        {"value": "all", "label": "All Caches"},
                        {"value": "user", "label": "User Cache Only"},
                    ],
                ),
                FormField(
                    name="confirm_clear",
                    label="I understand this action cannot be undone",
                    field_type="checkbox",
                    required=True,
                ),
            ]

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                cache_type = data.get("cache_type", "all")
                # Perform cache clearing logic
                await cache_service.clear(cache_type)
                return ActionResult(
                    success=True,
                    message=f"Successfully cleared {cache_type} cache!",
                    refresh=True,
                )
    """

    # View type discriminator - always "action" for ActionView
    view_type: ClassVar[Literal["action"]] = "action"

    # Form configuration
    form_fields: ClassVar[list[FormField]] = []

    # Confirmation settings
    confirmation_message: ClassVar[str] = ""
    requires_confirmation: ClassVar[bool] = True

    # Button/UI settings
    submit_label: ClassVar[str] = "Execute"
    success_redirect: ClassVar[str | None] = None
    dangerous: ClassVar[bool] = False

    # Execution settings
    run_in_background: ClassVar[bool] = False
    timeout_seconds: ClassVar[int] = 60

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize subclass with sensible defaults.

        Args:
            **kwargs: Additional keyword arguments.
        """
        # Check if name was explicitly defined on this class (not inherited)
        name_explicitly_set = "name" in cls.__dict__

        # Set name from class name if not specified, stripping "Action" suffix
        if not name_explicitly_set and cls.__name__ != "ActionView":
            cls.name = cls.__name__.replace("Action", "").replace("View", "").replace("Admin", "")

        # Always re-derive identity from name for ActionView subclasses
        # This ensures proper URL-safe identifiers even when name is explicitly set
        if cls.__name__ != "ActionView":
            cls.identity = cls.name.lower().replace(" ", "-")

        super().__init_subclass__(**kwargs)

        # Auto-set requires_confirmation if confirmation_message is provided
        if cls.confirmation_message and not cls.requires_confirmation:
            cls.requires_confirmation = True

    @abstractmethod
    async def execute(self, data: dict[str, Any]) -> ActionResult:
        """Execute the action with the provided form data.

        Subclasses must implement this method to perform the actual action logic.
        The method receives validated form data and should return an ActionResult
        indicating success/failure and any relevant messages or data.

        Args:
            data: Dictionary of form field values submitted by the user.

        Returns:
            ActionResult indicating the outcome of the action.

        Raises:
            Exception: Any exception raised will be caught and converted to
                an error ActionResult by the framework.

        Example::

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                try:
                    count = await self.clear_cache(data["cache_type"])
                    return ActionResult(
                        success=True,
                        message=f"Cleared {count} cache entries",
                    )
                except CacheError as e:
                    return ActionResult(
                        success=False,
                        message=f"Cache clear failed: {e}",
                    )
        """
        ...

    @classmethod
    async def validate_data(cls, data: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate form data before execution.

        Override this method to implement custom validation logic beyond
        the basic field-level validation.

        Args:
            data: Dictionary of form field values.

        Returns:
            Tuple of (is_valid, error_message). If is_valid is False,
            error_message should contain a human-readable error.

        Example::

            @classmethod
            async def validate_data(cls, data: dict[str, Any]) -> tuple[bool, str | None]:
                if data.get("start_date") > data.get("end_date"):
                    return False, "Start date must be before end date"
                return True, None
        """
        # Check required fields
        for form_field in cls.form_fields:
            if form_field.required:
                value = data.get(form_field.name)
                if value is None or value == "":
                    return False, f"Field '{form_field.label}' is required"

        return True, None

    @classmethod
    async def can_execute(cls, connection: ASGIConnection) -> bool:
        """Check if the current user can execute this action.

        Override this method to implement custom authorization logic
        for the action.

        Args:
            connection: The current ASGI connection.

        Returns:
            True if the user can execute this action.

        Example::

            @classmethod
            async def can_execute(cls, connection: ASGIConnection) -> bool:
                user = connection.user
                return user.is_admin and user.has_permission("cache.clear")
        """
        return await cls.is_accessible(connection)

    @classmethod
    def get_form_schema(cls) -> list[dict[str, Any]]:
        """Get the form schema for rendering the action form.

        Returns:
            List of form field definitions as dictionaries.
        """
        return [f.to_dict() for f in cls.form_fields]

    @classmethod
    def get_action_info(cls) -> dict[str, Any]:
        """Get action metadata for the frontend.

        Returns:
            Dictionary with action configuration.
        """
        return {
            **cls.get_navigation_info(),
            "formFields": cls.get_form_schema(),
            "confirmationMessage": cls.confirmation_message,
            "requiresConfirmation": cls.requires_confirmation,
            "submitLabel": cls.submit_label,
            "successRedirect": cls.success_redirect,
            "dangerous": cls.dangerous,
            "runInBackground": cls.run_in_background,
            "timeoutSeconds": cls.timeout_seconds,
        }

    @classmethod
    def get_api_routes(cls) -> list[dict[str, Any]]:
        """Return API route definitions for this action view.

        Action views expose:
        - GET endpoint for action metadata/form schema
        - POST endpoint for action execution

        Returns:
            List of route definitions.
        """
        base_path = f"/api/actions/{cls.identity}"
        return [
            {
                "path": base_path,
                "methods": ["GET"],
                "operation": "info",
                "name": f"{cls.identity}-info",
            },
            {
                "path": base_path,
                "methods": ["POST"],
                "operation": "execute",
                "name": f"{cls.identity}-execute",
            },
        ]
