"""SQLAlchemy 2.x models for the full admin demo.

This module defines the database models used in the full admin demo application,
demonstrating proper async SQLAlchemy 2.x patterns with relationships and
association tables.

Models:
    - User: Admin users with roles and authentication
    - Article: Content with status workflow and author relationship
    - Tag: Content categorization with slugs
    - ArticleTag: Many-to-many association between Article and Tag
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = ["Article", "ArticleTag", "Base", "Tag", "User", "UserRole", "ArticleStatus"]


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class UserRole(str, enum.Enum):
    """User role enumeration for RBAC."""

    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class ArticleStatus(str, enum.Enum):
    """Article publication status."""

    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# Association table for Article <-> Tag many-to-many relationship
ArticleTag = Table(
    "article_tag",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("article.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    """User model representing admin panel users.

    Attributes:
        id: Primary key.
        email: Unique email address used for authentication.
        name: Display name for the user.
        password_hash: Hashed password for authentication.
        role: User's role for RBAC (viewer, editor, admin, superadmin).
        is_active: Whether the user account is active.
        created_at: Timestamp when the user was created.
        updated_at: Timestamp when the user was last updated.
        articles: List of articles authored by this user.
    """

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    articles: Mapped[list[Article]] = relationship("Article", back_populates="author", lazy="selectin")

    def __repr__(self) -> str:
        """Return string representation of the user."""
        return f"<User(id={self.id}, email={self.email!r}, role={self.role.value!r})>"


class Article(Base):
    """Article model representing content entries.

    Attributes:
        id: Primary key.
        title: Article title.
        content: Full article content (text/markdown).
        status: Publication status (draft, review, published, archived).
        author_id: Foreign key to the author (User).
        created_at: Timestamp when the article was created.
        published_at: Timestamp when the article was published (nullable).
        author: The User who authored this article.
        tags: List of tags associated with this article.
    """

    __tablename__ = "article"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ArticleStatus] = mapped_column(Enum(ArticleStatus), default=ArticleStatus.DRAFT, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    author: Mapped[User | None] = relationship("User", back_populates="articles", lazy="selectin")
    tags: Mapped[list[Tag]] = relationship("Tag", secondary=ArticleTag, back_populates="articles", lazy="selectin")

    def __repr__(self) -> str:
        """Return string representation of the article."""
        return f"<Article(id={self.id}, title={self.title!r}, status={self.status.value!r})>"


class Tag(Base):
    """Tag model for content categorization.

    Attributes:
        id: Primary key.
        name: Display name for the tag.
        slug: URL-friendly slug (unique).
        articles: List of articles with this tag.
    """

    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Relationships
    articles: Mapped[list[Article]] = relationship(
        "Article", secondary=ArticleTag, back_populates="tags", lazy="selectin"
    )

    def __repr__(self) -> str:
        """Return string representation of the tag."""
        return f"<Tag(id={self.id}, name={self.name!r}, slug={self.slug!r})>"
