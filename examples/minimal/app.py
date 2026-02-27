"""Minimal litestar-admin example — auto-discovery, no ModelView boilerplate.

Run with:
    uvicorn examples.minimal.app:app --reload

Then visit: http://localhost:8000/admin
"""

from __future__ import annotations

from datetime import datetime

from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from litestar import Litestar
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar_admin import AdminConfig, AdminPlugin


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


db_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///:memory:",
    metadata=Base.metadata,
    create_all=True,
)

app = Litestar(
    plugins=[
        SQLAlchemyPlugin(config=db_config),
        AdminPlugin(config=AdminConfig(title="Minimal Admin")),
    ],
    debug=True,
)
