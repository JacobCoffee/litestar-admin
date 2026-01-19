"""ModelView class with model class binding."""

from __future__ import annotations

from typing import Any

from litestar_admin.views.base import BaseModelView

__all__ = ["ModelView"]


class ModelView(BaseModelView):
    """Model view with automatic model class binding.

    This class extends BaseModelView to allow specifying the model class
    as a class parameter, enabling cleaner syntax for defining admin views.

    Example::

        from litestar_admin import ModelView
        from myapp.models import User


        class UserAdmin(ModelView, model=User):
            column_list = ["id", "email", "name"]
            column_searchable_list = ["email", "name"]
    """

    def __init_subclass__(cls, model: type[Any] | None = None, **kwargs: Any) -> None:
        """Initialize subclass with model binding.

        Args:
            model: The SQLAlchemy model class to manage.
            **kwargs: Additional keyword arguments passed to parent.
        """
        if model is not None:
            cls.model = model

        super().__init_subclass__(**kwargs)
