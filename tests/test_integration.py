"""Integration tests for litestar-admin controllers with database.

This module contains comprehensive integration tests that verify the full CRUD
lifecycle, pagination, filtering, bulk operations, and export functionality
using an in-memory SQLite database via aiosqlite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from litestar import Litestar
from litestar.di import Provide
from litestar.testing import AsyncTestClient
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from litestar_admin import AdminConfig
from litestar_admin.controllers import (
    BulkActionsController,
    DashboardController,
    ExportController,
    ModelsController,
)
from litestar_admin.registry import ModelRegistry
from litestar_admin.views import BaseModelView

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# ==============================================================================
# Test Models
# ==============================================================================


class IntegrationBase(DeclarativeBase):
    """Base class for integration test models."""

    pass


class Author(IntegrationBase):
    """Test author model for relationship testing."""

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    articles: Mapped[list[Article]] = relationship("Article", back_populates="author")


class Article(IntegrationBase):
    """Test article model with foreign key relationship."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("authors.id"), nullable=False)

    # Relationships
    author: Mapped[Author] = relationship("Author", back_populates="articles")


class Category(IntegrationBase):
    """Test category model for simple CRUD operations."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ==============================================================================
# Model Views
# ==============================================================================


class AuthorAdmin(BaseModelView):
    """Admin view for Author model."""

    model = Author
    name = "Author"
    column_list = ["id", "name", "email", "bio", "is_active"]
    column_searchable_list = ["name", "email"]
    column_sortable_list = ["id", "name", "email"]
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True


class ArticleAdmin(BaseModelView):
    """Admin view for Article model."""

    model = Article
    name = "Article"
    column_list = ["id", "title", "content", "published", "author_id"]
    column_searchable_list = ["title", "content"]
    column_sortable_list = ["id", "title", "published"]
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True

    @classmethod
    async def bulk_publish(
        cls,
        session: AsyncSession,
        ids: list[Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Custom bulk action to publish multiple articles."""
        from sqlalchemy import select

        count = 0
        for pk in ids:
            query = select(Article).where(Article.id == pk)
            result = await session.scalars(query)
            article = result.first()
            if article:
                article.published = params.get("published", True)
                count += 1
        await session.flush()
        return {"affected": count, "status": "published" if params.get("published", True) else "unpublished"}


class CategoryAdmin(BaseModelView):
    """Admin view for Category model."""

    model = Category
    name = "Category"
    column_list = ["id", "name", "description"]
    column_searchable_list = ["name"]
    column_sortable_list = ["id", "name"]
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True


class ReadOnlyAuthorAdmin(BaseModelView):
    """Read-only admin view for testing permission restrictions."""

    model = Author
    name = "ReadOnlyAuthor"
    column_list = ["id", "name", "email"]
    can_create = False
    can_edit = False
    can_delete = False
    can_export = False


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
async def integration_engine():
    """Create an async SQLite engine for integration testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(IntegrationBase.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def integration_session_factory(integration_engine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory for integration testing."""
    return async_sessionmaker(
        integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def integration_session(integration_session_factory) -> AsyncIterator[AsyncSession]:
    """Create an async session for integration testing."""
    async with integration_session_factory() as session:
        yield session
        await session.commit()


@pytest.fixture
def integration_registry() -> ModelRegistry:
    """Create a model registry with test views."""
    registry = ModelRegistry()
    registry.register(AuthorAdmin)
    registry.register(ArticleAdmin)
    registry.register(CategoryAdmin)
    return registry


@pytest.fixture
def integration_config(integration_registry) -> AdminConfig:
    """Create admin config for integration testing."""
    return AdminConfig(
        title="Integration Test Admin",
        base_url="/admin",
        views=[AuthorAdmin, ArticleAdmin, CategoryAdmin],
        auto_discover=False,
        debug=True,
    )


@pytest.fixture
async def integration_app(
    integration_config,
    integration_registry,
    integration_session_factory,
) -> Litestar:
    """Create a Litestar app configured for integration testing."""

    async def get_db_session() -> AsyncIterator[AsyncSession]:
        """Provide database session for dependency injection."""
        async with integration_session_factory() as session:
            yield session
            await session.commit()

    return Litestar(
        route_handlers=[
            ModelsController,
            DashboardController,
            ExportController,
            BulkActionsController,
        ],
        dependencies={
            "admin_config": Provide(lambda: integration_config, sync_to_thread=False),
            "admin_registry": Provide(lambda: integration_registry, sync_to_thread=False),
            "db_session": Provide(get_db_session),
        },
        debug=True,
    )


@pytest.fixture
async def client(integration_app) -> AsyncIterator[AsyncTestClient[Litestar]]:
    """Create an async test client."""
    async with AsyncTestClient(integration_app) as test_client:
        yield test_client


@pytest.fixture
async def seeded_client(
    integration_app,
    integration_session_factory,
) -> AsyncIterator[AsyncTestClient[Litestar]]:
    """Create a test client with seeded data."""
    # Seed test data
    async with integration_session_factory() as session:
        # Create authors
        authors = [
            Author(name="John Doe", email="john@example.com", bio="Tech writer", is_active=True),
            Author(name="Jane Smith", email="jane@example.com", bio="Science blogger", is_active=True),
            Author(name="Bob Wilson", email="bob@example.com", bio="Travel writer", is_active=False),
        ]
        session.add_all(authors)
        await session.flush()

        # Create articles
        articles = [
            Article(title="Python Basics", content="Learn Python fundamentals", published=True, author_id=1),
            Article(title="Advanced Python", content="Deep dive into Python", published=False, author_id=1),
            Article(title="Science Today", content="Latest discoveries", published=True, author_id=2),
            Article(title="Travel Guide", content="Best destinations", published=False, author_id=3),
        ]
        session.add_all(articles)

        # Create categories
        categories = [
            Category(name="Technology", description="Tech articles"),
            Category(name="Science", description="Science articles"),
            Category(name="Travel", description="Travel articles"),
        ]
        session.add_all(categories)

        await session.commit()

    async with AsyncTestClient(integration_app) as test_client:
        yield test_client


# ==============================================================================
# ModelsController Tests
# ==============================================================================


@pytest.mark.integration
class TestModelsController:
    """Integration tests for ModelsController endpoints."""

    async def test_list_models(self, client: AsyncTestClient) -> None:
        """Test listing all registered models."""
        response = await client.get("/api/models")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 3

        model_names = {m["name"] for m in data}
        assert model_names == {"Author", "Article", "Category"}

        # Check model info structure
        author_info = next(m for m in data if m["name"] == "Author")
        assert author_info["model_name"] == "author"
        assert author_info["can_create"] is True
        assert author_info["can_edit"] is True
        assert author_info["can_delete"] is True

    async def test_list_records_empty(self, client: AsyncTestClient) -> None:
        """Test listing records when table is empty."""
        response = await client.get("/api/models/author")

        assert response.status_code == 200
        data = response.json()

        assert data["items"] == []
        assert data["total"] == 0
        assert data["offset"] == 0
        assert data["limit"] == 50

    async def test_list_records_with_data(self, seeded_client: AsyncTestClient) -> None:
        """Test listing records with seeded data."""
        response = await seeded_client.get("/api/models/author")

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 3
        assert data["total"] == 3

        # Verify record structure
        author = data["items"][0]
        assert "id" in author
        assert "name" in author
        assert "email" in author

    async def test_list_records_pagination(self, seeded_client: AsyncTestClient) -> None:
        """Test pagination of records."""
        # First page
        response = await seeded_client.get("/api/models/author?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["offset"] == 0
        assert data["limit"] == 2

        # Second page
        response = await seeded_client.get("/api/models/author?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 3
        assert data["offset"] == 2

    async def test_list_records_sorting(self, seeded_client: AsyncTestClient) -> None:
        """Test sorting of records."""
        # Sort by name ascending
        response = await seeded_client.get("/api/models/author?sort_by=name&sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names == sorted(names)

        # Sort by name descending
        response = await seeded_client.get("/api/models/author?sort_by=name&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names == sorted(names, reverse=True)

    async def test_list_records_search(self, seeded_client: AsyncTestClient) -> None:
        """Test searching records."""
        response = await seeded_client.get("/api/models/author?search=john")

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "John Doe"
        assert data["total"] == 1

    async def test_list_records_model_not_found(self, client: AsyncTestClient) -> None:
        """Test listing records for non-existent model."""
        response = await client.get("/api/models/NonExistentModel")

        assert response.status_code == 404

    async def test_create_record(self, client: AsyncTestClient) -> None:
        """Test creating a new record."""
        author_data = {
            "name": "New Author",
            "email": "new@example.com",
            "bio": "A new author",
            "is_active": True,
        }

        response = await client.post("/api/models/author", json=author_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "New Author"
        assert data["email"] == "new@example.com"
        assert data["bio"] == "A new author"
        assert data["is_active"] is True
        assert "id" in data

        # Verify record was created
        response = await client.get(f"/api/models/author/{data['id']}")
        assert response.status_code == 200
        fetched = response.json()
        assert fetched["name"] == "New Author"

    async def test_create_record_model_not_found(self, client: AsyncTestClient) -> None:
        """Test creating record for non-existent model."""
        response = await client.post("/api/models/NonExistent", json={"name": "Test"})

        assert response.status_code == 404

    async def test_get_record(self, seeded_client: AsyncTestClient) -> None:
        """Test retrieving a single record."""
        response = await seeded_client.get("/api/models/author/1")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == 1
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"

    async def test_get_record_not_found(self, seeded_client: AsyncTestClient) -> None:
        """Test retrieving a non-existent record."""
        response = await seeded_client.get("/api/models/author/9999")

        assert response.status_code == 404

    async def test_update_record_full(self, seeded_client: AsyncTestClient) -> None:
        """Test full update of a record via PUT."""
        update_data = {
            "name": "Updated Name",
            "email": "updated@example.com",
            "bio": "Updated bio",
            "is_active": False,
        }

        response = await seeded_client.put("/api/models/author/1", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Name"
        assert data["email"] == "updated@example.com"
        assert data["bio"] == "Updated bio"
        assert data["is_active"] is False

    async def test_update_record_partial(self, seeded_client: AsyncTestClient) -> None:
        """Test partial update of a record via PATCH."""
        update_data = {"name": "Partially Updated"}

        response = await seeded_client.patch("/api/models/author/1", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Partially Updated"
        # Original values should be preserved
        assert data["email"] == "john@example.com"

    async def test_update_record_not_found(self, seeded_client: AsyncTestClient) -> None:
        """Test updating a non-existent record."""
        response = await seeded_client.put("/api/models/author/9999", json={"name": "Test"})

        assert response.status_code == 404

    async def test_delete_record(self, seeded_client: AsyncTestClient) -> None:
        """Test deleting a record."""
        # First create a new record to delete
        author_data = {"name": "To Delete", "email": "delete@example.com", "is_active": True}
        create_response = await seeded_client.post("/api/models/author", json=author_data)
        assert create_response.status_code == 201
        record_id = create_response.json()["id"]

        # Delete the record
        response = await seeded_client.delete(f"/api/models/author/{record_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify record was deleted
        get_response = await seeded_client.get(f"/api/models/author/{record_id}")
        assert get_response.status_code == 404

    async def test_delete_record_not_found(self, seeded_client: AsyncTestClient) -> None:
        """Test deleting a non-existent record."""
        response = await seeded_client.delete("/api/models/author/9999")

        assert response.status_code == 404

    async def test_get_schema(self, client: AsyncTestClient) -> None:
        """Test retrieving model JSON schema."""
        response = await client.get("/api/models/author/schema")

        assert response.status_code == 200
        data = response.json()

        assert data["type"] == "object"
        assert data["title"] == "Author"
        assert "properties" in data
        # Note: "id" is excluded from form schema as it's auto-generated
        assert "name" in data["properties"]
        assert "email" in data["properties"]

    async def test_crud_lifecycle(self, client: AsyncTestClient) -> None:
        """Test complete CRUD lifecycle."""
        # CREATE
        author_data = {"name": "Lifecycle Test", "email": "lifecycle@example.com", "is_active": True}
        create_response = await client.post("/api/models/author", json=author_data)
        assert create_response.status_code == 201
        created = create_response.json()
        record_id = created["id"]

        # READ
        read_response = await client.get(f"/api/models/author/{record_id}")
        assert read_response.status_code == 200
        assert read_response.json()["name"] == "Lifecycle Test"

        # UPDATE (PATCH)
        patch_response = await client.patch(f"/api/models/author/{record_id}", json={"name": "Updated Lifecycle"})
        assert patch_response.status_code == 200
        assert patch_response.json()["name"] == "Updated Lifecycle"

        # UPDATE (PUT)
        put_data = {"name": "Full Update", "email": "fullupdate@example.com", "bio": "New bio", "is_active": False}
        put_response = await client.put(f"/api/models/author/{record_id}", json=put_data)
        assert put_response.status_code == 200
        assert put_response.json()["name"] == "Full Update"
        assert put_response.json()["is_active"] is False

        # DELETE
        delete_response = await client.delete(f"/api/models/author/{record_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True

        # Verify deletion
        verify_response = await client.get(f"/api/models/author/{record_id}")
        assert verify_response.status_code == 404


# ==============================================================================
# DashboardController Tests
# ==============================================================================


@pytest.mark.integration
class TestDashboardController:
    """Integration tests for DashboardController endpoints."""

    async def test_get_stats_empty(self, client: AsyncTestClient) -> None:
        """Test dashboard stats with empty database."""
        response = await client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_records"] == 0
        assert data["total_models"] == 3
        assert len(data["models"]) == 3

        # Check model stats structure
        author_stats = next(m for m in data["models"] if m["name"] == "Author")
        assert author_stats["count"] == 0
        assert author_stats["model_name"] == "author"

    async def test_get_stats_with_data(self, seeded_client: AsyncTestClient) -> None:
        """Test dashboard stats with seeded data."""
        response = await seeded_client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.json()

        # 3 authors + 4 articles + 3 categories = 10 total
        assert data["total_records"] == 10
        assert data["total_models"] == 3

        # Check individual model counts
        author_stats = next(m for m in data["models"] if m["name"] == "Author")
        assert author_stats["count"] == 3

        article_stats = next(m for m in data["models"] if m["name"] == "Article")
        assert article_stats["count"] == 4

        category_stats = next(m for m in data["models"] if m["name"] == "Category")
        assert category_stats["count"] == 3

    async def test_get_activity_empty(self, client: AsyncTestClient) -> None:
        """Test activity endpoint returns empty list when no audit logging."""
        response = await client.get("/api/dashboard/activity")

        assert response.status_code == 200
        data = response.json()

        # Activity logging not implemented yet, should return empty list
        assert data == []

    async def test_get_activity_with_limit(self, client: AsyncTestClient) -> None:
        """Test activity endpoint respects limit parameter."""
        response = await client.get("/api/dashboard/activity?limit=10")

        assert response.status_code == 200
        data = response.json()

        # Activity logging not implemented yet
        assert isinstance(data, list)

    async def test_get_widgets_empty(self, client: AsyncTestClient) -> None:
        """Test widgets endpoint with no custom widgets configured."""
        response = await client.get("/api/dashboard/widgets")

        assert response.status_code == 200
        data = response.json()

        assert data == []


# ==============================================================================
# ExportController Tests
# ==============================================================================


@pytest.mark.integration
class TestExportController:
    """Integration tests for ExportController endpoints."""

    async def test_export_csv_empty(self, client: AsyncTestClient) -> None:
        """Test CSV export with empty table."""
        response = await client.get("/api/models/author/export?format=csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]

        # Check CSV header
        content = response.text
        lines = content.strip().split("\n")
        assert len(lines) >= 1  # At least header row
        header = lines[0]
        assert "id" in header
        assert "name" in header
        assert "email" in header

    async def test_export_csv_with_data(self, seeded_client: AsyncTestClient) -> None:
        """Test CSV export with data."""
        response = await seeded_client.get("/api/models/author/export?format=csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        content = response.text
        lines = content.strip().split("\n")

        # Header + 3 data rows
        assert len(lines) == 4

        # Check data is present
        assert "John Doe" in content
        assert "jane@example.com" in content

    async def test_export_json_empty(self, client: AsyncTestClient) -> None:
        """Test JSON export with empty table."""
        response = await client.get("/api/models/author/export?format=json")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert data == []

    async def test_export_json_with_data(self, seeded_client: AsyncTestClient) -> None:
        """Test JSON export with data."""
        response = await seeded_client.get("/api/models/author/export?format=json")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert len(data) == 3

        # Check data structure
        author = data[0]
        assert "id" in author
        assert "name" in author
        assert "email" in author

    async def test_export_invalid_format(self, client: AsyncTestClient) -> None:
        """Test export with invalid format."""
        response = await client.get("/api/models/author/export?format=xml")

        assert response.status_code == 400

    async def test_export_model_not_found(self, client: AsyncTestClient) -> None:
        """Test export for non-existent model."""
        response = await client.get("/api/models/NonExistent/export")

        assert response.status_code == 404

    async def test_bulk_export_csv(self, seeded_client: AsyncTestClient) -> None:
        """Test bulk export of selected records in CSV format."""
        request_data = {"ids": [1, 2], "format": "csv"}

        response = await seeded_client.post("/api/models/author/bulk/export", json=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        content = response.text
        lines = content.strip().split("\n")

        # Header + 2 data rows
        assert len(lines) == 3

    async def test_bulk_export_json(self, seeded_client: AsyncTestClient) -> None:
        """Test bulk export of selected records in JSON format."""
        request_data = {"ids": [1, 3], "format": "json"}

        response = await seeded_client.post("/api/models/author/bulk/export", json=request_data)

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert len(data) == 2

    async def test_bulk_export_empty_ids(self, seeded_client: AsyncTestClient) -> None:
        """Test bulk export with empty IDs list."""
        request_data = {"ids": [], "format": "csv"}

        response = await seeded_client.post("/api/models/author/bulk/export", json=request_data)

        assert response.status_code == 400


# ==============================================================================
# BulkActionsController Tests
# ==============================================================================


@pytest.mark.integration
class TestBulkActionsController:
    """Integration tests for BulkActionsController endpoints."""

    async def test_bulk_delete(self, seeded_client: AsyncTestClient) -> None:
        """Test bulk delete operation."""
        # First, create some categories to delete
        for i in range(3):
            await seeded_client.post(
                "/api/models/category",
                json={"name": f"ToDelete{i}", "description": f"Delete me {i}"},
            )

        # Get the IDs of the newly created categories
        list_response = await seeded_client.get("/api/models/category?search=ToDelete")
        categories = list_response.json()["items"]
        ids_to_delete = [c["id"] for c in categories]

        # Perform bulk delete
        response = await seeded_client.post(
            "/api/models/category/bulk/delete",
            json={"ids": ids_to_delete, "soft_delete": False},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["deleted"] == 3

        # Verify records were deleted
        verify_response = await seeded_client.get("/api/models/category?search=ToDelete")
        assert verify_response.json()["total"] == 0

    async def test_bulk_delete_partial(self, seeded_client: AsyncTestClient) -> None:
        """Test bulk delete with some non-existent IDs."""
        # Create one category to delete
        create_response = await seeded_client.post(
            "/api/models/category",
            json={"name": "RealCategory", "description": "Real"},
        )
        real_id = create_response.json()["id"]

        # Try to delete including non-existent IDs
        response = await seeded_client.post(
            "/api/models/category/bulk/delete",
            json={"ids": [real_id, 9998, 9999], "soft_delete": False},
        )

        assert response.status_code == 200
        data = response.json()

        # Only one record should have been deleted
        assert data["deleted"] == 1

    async def test_bulk_delete_empty_ids(self, seeded_client: AsyncTestClient) -> None:
        """Test bulk delete with empty IDs list."""
        response = await seeded_client.post(
            "/api/models/category/bulk/delete",
            json={"ids": [], "soft_delete": False},
        )

        assert response.status_code == 400

    async def test_bulk_delete_model_not_found(self, seeded_client: AsyncTestClient) -> None:
        """Test bulk delete for non-existent model."""
        response = await seeded_client.post(
            "/api/models/NonExistent/bulk/delete",
            json={"ids": [1, 2, 3], "soft_delete": False},
        )

        assert response.status_code == 404

    async def test_custom_bulk_action(self, seeded_client: AsyncTestClient) -> None:
        """Test custom bulk action (publish articles)."""
        # Get unpublished articles
        list_response = await seeded_client.get("/api/models/article")
        articles = list_response.json()["items"]
        unpublished_ids = [a["id"] for a in articles if not a["published"]]

        # Execute custom bulk action
        response = await seeded_client.post(
            "/api/models/article/bulk/publish",
            json={"ids": unpublished_ids, "params": {"published": True}},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["affected"] == len(unpublished_ids)
        assert data["result"]["status"] == "published"

        # Verify articles are now published
        for article_id in unpublished_ids:
            article_response = await seeded_client.get(f"/api/models/article/{article_id}")
            assert article_response.json()["published"] is True

    async def test_custom_bulk_action_not_found(self, seeded_client: AsyncTestClient) -> None:
        """Test calling non-existent custom bulk action."""
        response = await seeded_client.post(
            "/api/models/article/bulk/nonexistent",
            json={"ids": [1, 2], "params": {}},
        )

        assert response.status_code == 404

    async def test_custom_bulk_action_empty_ids(self, seeded_client: AsyncTestClient) -> None:
        """Test custom bulk action with empty IDs."""
        response = await seeded_client.post(
            "/api/models/article/bulk/publish",
            json={"ids": [], "params": {}},
        )

        assert response.status_code == 400


# ==============================================================================
# Edge Cases and Error Handling Tests
# ==============================================================================


@pytest.mark.integration
class TestEdgeCasesAndErrorHandling:
    """Tests for edge cases and error handling."""

    async def test_pagination_limit_cap(self, seeded_client: AsyncTestClient) -> None:
        """Test that pagination limit is capped at 100."""
        response = await seeded_client.get("/api/models/author?limit=1000")

        assert response.status_code == 200
        data = response.json()

        # Limit should be capped at 100
        assert data["limit"] == 100

    async def test_negative_offset_normalized(self, seeded_client: AsyncTestClient) -> None:
        """Test that negative offset is normalized to 0."""
        response = await seeded_client.get("/api/models/author?offset=-10")

        assert response.status_code == 200
        data = response.json()

        # Offset should be normalized to 0
        assert data["offset"] == 0

    async def test_invalid_sort_order_defaults_to_asc(self, seeded_client: AsyncTestClient) -> None:
        """Test that invalid sort order defaults to ascending."""
        response = await seeded_client.get("/api/models/author?sort_by=name&sort_order=invalid")

        assert response.status_code == 200
        data = response.json()

        # Should still return results
        assert len(data["items"]) == 3

    async def test_search_case_insensitive(self, seeded_client: AsyncTestClient) -> None:
        """Test that search is case-insensitive."""
        # Search with uppercase
        response1 = await seeded_client.get("/api/models/author?search=JOHN")
        # Search with lowercase
        response2 = await seeded_client.get("/api/models/author?search=john")
        # Search with mixed case
        response3 = await seeded_client.get("/api/models/author?search=JoHn")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

        # All should return the same result
        assert response1.json()["total"] == response2.json()["total"] == response3.json()["total"] == 1

    async def test_create_with_missing_required_fields(self, client: AsyncTestClient) -> None:
        """Test creating record with missing required fields."""
        # Missing required 'email' field
        response = await client.post("/api/models/author", json={"name": "Only Name"})

        # Should fail due to database constraint
        assert response.status_code == 500

    async def test_special_characters_in_search(self, seeded_client: AsyncTestClient) -> None:
        """Test search with special characters."""
        # Create a record with special characters
        await seeded_client.post(
            "/api/models/category",
            json={"name": "Test & Special <Category>", "description": "Has 'quotes' and \"double\""},
        )

        # Search for it
        response = await seeded_client.get("/api/models/category?search=Special")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] >= 1

    async def test_concurrent_create_operations(self, client: AsyncTestClient) -> None:
        """Test concurrent create operations."""
        import asyncio

        async def create_author(index: int):
            return await client.post(
                "/api/models/author",
                json={
                    "name": f"Concurrent Author {index}",
                    "email": f"concurrent{index}@example.com",
                    "is_active": True,
                },
            )

        # Create 5 authors concurrently
        tasks = [create_author(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 201

        # Verify all were created
        list_response = await client.get("/api/models/author?search=Concurrent")
        assert list_response.json()["total"] == 5

    async def test_large_content_field(self, client: AsyncTestClient) -> None:
        """Test handling large content in text fields."""
        large_content = "A" * 10000  # 10KB of text

        response = await client.post(
            "/api/models/category",
            json={"name": "Large Content Test", "description": large_content},
        )

        assert response.status_code == 201
        data = response.json()

        # Verify large content was stored
        get_response = await client.get(f"/api/models/category/{data['id']}")
        assert len(get_response.json()["description"]) == 10000
