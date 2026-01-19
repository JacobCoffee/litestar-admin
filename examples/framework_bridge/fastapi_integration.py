"""Example showing FastAPI application with Litestar admin mounted.

This example demonstrates how to integrate litestar-admin with an existing
FastAPI application using ASGI mounting. This pattern is useful when you have
a FastAPI backend and want a powerful admin panel without building one from scratch.

Key concepts:
- ASGI sub-application mounting with FastAPI's mount()
- Shared SQLAlchemy async engine between frameworks
- Proper lifecycle management with FastAPI's lifespan
- Pydantic models coexisting with SQLAlchemy models

Requirements:
    pip install fastapi litestar litestar-admin sqlalchemy[asyncio] aiosqlite uvicorn

Usage:
    uvicorn examples.framework_bridge.fastapi_integration:app --reload

Note:
    This pattern allows gradual migration from FastAPI to Litestar, or simply
    using the best tool for each job - FastAPI for your main API, litestar-admin
    for administration.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, HTTPException
from litestar import Litestar
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from litestar_admin import AdminConfig, AdminPlugin, ModelView

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

# =============================================================================
# Database Models (SQLAlchemy - used by both frameworks)
# =============================================================================


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class User(Base):
    """User model for the application."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(100), nullable=False, unique=True)
    full_name = Column(String(200))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Product(Base):
    """Product model for e-commerce functionality."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(String(2000))
    price = Column(Integer, nullable=False)  # Price in cents
    sku = Column(String(50), unique=True)
    stock_quantity = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Order(Base):
    """Order model for tracking purchases."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")
    total_amount = Column(Integer, nullable=False)  # Amount in cents
    created_at = Column(DateTime, server_default=func.now())


# =============================================================================
# Pydantic Models (for FastAPI request/response validation)
# =============================================================================


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: str
    username: str
    full_name: str | None = None


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    full_name: str | None
    is_active: bool
    created_at: datetime | None


class ProductCreate(BaseModel):
    """Schema for creating a new product."""

    name: str
    description: str | None = None
    price: int
    sku: str
    stock_quantity: int = 0


class ProductResponse(BaseModel):
    """Schema for product response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: int
    sku: str | None
    stock_quantity: int
    is_available: bool


# =============================================================================
# Database Configuration (shared)
# =============================================================================

DATABASE_URL = "sqlite+aiosqlite:///./fastapi_admin_demo.db"

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Yields:
        An async database session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# =============================================================================
# Litestar Admin Configuration
# =============================================================================


class UserAdmin(ModelView, model=User):
    """Admin view for User model."""

    column_list = ["id", "email", "username", "is_active", "is_superuser", "created_at"]
    column_searchable_list = ["email", "username", "full_name"]
    column_sortable_list = ["id", "email", "username", "created_at"]
    column_default_sort = ("created_at", True)  # Sort by newest first
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True


class ProductAdmin(ModelView, model=Product):
    """Admin view for Product model."""

    column_list = ["id", "name", "sku", "price", "stock_quantity", "is_available"]
    column_searchable_list = ["name", "sku", "description"]
    column_sortable_list = ["id", "name", "price", "stock_quantity"]
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True

    # Custom formatting could be added here
    # column_formatters = {"price": lambda v: f"${v/100:.2f}"}


class OrderAdmin(ModelView, model=Order):
    """Admin view for Order model."""

    column_list = ["id", "user_id", "status", "total_amount", "created_at"]
    column_sortable_list = ["id", "status", "total_amount", "created_at"]
    column_default_sort = ("created_at", True)
    can_create = True
    can_edit = True
    can_delete = False  # Orders should not be deleted


def create_litestar_admin() -> Litestar:
    """Create the Litestar admin application.

    Returns:
        Configured Litestar application with admin panel.
    """
    return Litestar(
        plugins=[
            AdminPlugin(
                config=AdminConfig(
                    title="FastAPI + Litestar Admin",
                    base_url="/",
                    views=[UserAdmin, ProductAdmin, OrderAdmin],
                    auto_discover=False,
                    debug=True,
                )
            )
        ],
    )


# Create admin app instance
admin_app = create_litestar_admin()


# =============================================================================
# FastAPI Application
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan.

    Handles database initialization and cleanup for both
    FastAPI and the mounted Litestar admin.

    Args:
        app: The FastAPI application instance.

    Yields:
        None during the application's active lifespan.
    """
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Database initialized")
    print("FastAPI docs available at: http://localhost:8000/docs")
    print("Admin panel available at: http://localhost:8000/admin")

    yield

    # Shutdown
    await engine.dispose()
    print("Database connections closed")


# Create main FastAPI application
app = FastAPI(
    title="FastAPI + Litestar Admin Example",
    description="Example showing FastAPI with litestar-admin mounted as a sub-application",
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# FastAPI Endpoints
# =============================================================================


@app.get("/")
async def root() -> dict:
    """Root endpoint with application info.

    Returns:
        Dictionary with application information and useful URLs.
    """
    return {
        "message": "FastAPI application with Litestar Admin",
        "documentation": "/docs",
        "admin_panel": "/admin",
        "api_endpoints": {
            "users": "/api/v1/users",
            "products": "/api/v1/products",
        },
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status dictionary.
    """
    return {"status": "healthy", "database": "connected"}


# -----------------------------------------------------------------------------
# User Endpoints
# -----------------------------------------------------------------------------


@app.post("/api/v1/users", response_model=UserResponse, status_code=201)
async def create_user(user_data: UserCreate, session: AsyncSession = Depends(get_db_session)) -> User:
    """Create a new user.

    Args:
        user_data: The user creation data.
        session: The database session.

    Returns:
        The created user.
    """
    user = User(**user_data.model_dump())
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


@app.get("/api/v1/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_db_session),
) -> list[User]:
    """List all users with pagination.

    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        session: The database session.

    Returns:
        List of users.
    """
    from sqlalchemy import select

    result = await session.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, session: AsyncSession = Depends(get_db_session)) -> User:
    """Get a specific user by ID.

    Args:
        user_id: The user's ID.
        session: The database session.

    Returns:
        The requested user.

    Raises:
        HTTPException: If user not found.
    """
    from sqlalchemy import select

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# -----------------------------------------------------------------------------
# Product Endpoints
# -----------------------------------------------------------------------------


@app.post("/api/v1/products", response_model=ProductResponse, status_code=201)
async def create_product(
    product_data: ProductCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Product:
    """Create a new product.

    Args:
        product_data: The product creation data.
        session: The database session.

    Returns:
        The created product.
    """
    product = Product(**product_data.model_dump())
    session.add(product)
    await session.flush()
    await session.refresh(product)
    return product


@app.get("/api/v1/products", response_model=list[ProductResponse])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    available_only: bool = False,
    session: AsyncSession = Depends(get_db_session),
) -> list[Product]:
    """List all products with optional filtering.

    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        available_only: If True, only return available products.
        session: The database session.

    Returns:
        List of products.
    """
    from sqlalchemy import select

    query = select(Product)
    if available_only:
        query = query.where(Product.is_available == True)  # noqa: E712
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


@app.get("/api/v1/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, session: AsyncSession = Depends(get_db_session)) -> Product:
    """Get a specific product by ID.

    Args:
        product_id: The product's ID.
        session: The database session.

    Returns:
        The requested product.

    Raises:
        HTTPException: If product not found.
    """
    from sqlalchemy import select

    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# =============================================================================
# Mount Litestar Admin
# =============================================================================

# Mount the Litestar admin app at /admin
# All admin routes will be available under /admin/*
app.mount("/admin", admin_app)


# =============================================================================
# Alternative: Multiple Admin Instances
# =============================================================================


def create_multi_admin_app() -> FastAPI:
    """Create FastAPI app with multiple admin panels.

    This demonstrates how you could have different admin panels
    for different purposes (e.g., main admin, reports admin).

    Returns:
        FastAPI application with multiple admin mounts.
    """
    main_app = FastAPI(title="Multi-Admin Example", lifespan=lifespan)

    # Main admin with full access
    main_admin = Litestar(
        plugins=[
            AdminPlugin(
                config=AdminConfig(
                    title="Main Admin",
                    base_url="/",
                    views=[UserAdmin, ProductAdmin, OrderAdmin],
                    auto_discover=False,
                )
            )
        ],
    )

    # Reports admin with read-only views
    class ReadOnlyOrderAdmin(ModelView, model=Order):
        """Read-only order admin for reports."""

        column_list = ["id", "user_id", "status", "total_amount", "created_at"]
        can_create = False
        can_edit = False
        can_delete = False
        can_export = True

    reports_admin = Litestar(
        plugins=[
            AdminPlugin(
                config=AdminConfig(
                    title="Reports Admin",
                    base_url="/",
                    views=[ReadOnlyOrderAdmin],
                    auto_discover=False,
                )
            )
        ],
    )

    main_app.mount("/admin", main_admin)
    main_app.mount("/reports", reports_admin)

    return main_app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
