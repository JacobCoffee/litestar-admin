"""Tests for relationship detection functionality."""

from __future__ import annotations

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String, Table, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from litestar_admin.relationships import (
    RelationshipDetector,
    RelationshipInfo,
    RelationshipType,
    get_relationship_detector,
)
from litestar_admin.views import ModelView

# ==============================================================================
# Test Models with Relationships
# ==============================================================================


class RelBase(DeclarativeBase):
    """Base class for relationship test models."""


class Author(RelBase):
    """Author model for testing MANY_TO_ONE and ONE_TO_MANY relationships."""

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)

    # ONE_TO_MANY relationship to Post
    posts: Mapped[list[Post]] = relationship("Post", back_populates="author")


class Post(RelBase):
    """Post model for testing MANY_TO_ONE relationships."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=True)

    # MANY_TO_ONE relationship to Author
    author_id: Mapped[int | None] = mapped_column(ForeignKey("authors.id"), nullable=True)
    author: Mapped[Author | None] = relationship("Author", back_populates="posts")


class Tag(RelBase):
    """Tag model for testing MANY_TO_MANY relationships."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


# Association table for MANY_TO_MANY - must be defined before ArticleWithTags
article_tags = Table(
    "article_tags",
    RelBase.metadata,
    Column("article_id", Integer, ForeignKey("articles.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Article(RelBase):
    """Article model with tags for MANY_TO_MANY testing."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # MANY_TO_MANY relationship to Tag
    tags: Mapped[list[Tag]] = relationship("Tag", secondary=article_tags)


class UserProfile(RelBase):
    """Profile model for testing ONE_TO_ONE relationships."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bio: Mapped[str] = mapped_column(String, nullable=True)


class UserWithProfile(RelBase):
    """User model with profile for ONE_TO_ONE testing."""

    __tablename__ = "users_with_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("user_profiles.id"), nullable=True)

    # ONE_TO_ONE relationship (uselist=False with FK on this side is MANY_TO_ONE technically)
    profile: Mapped[UserProfile | None] = relationship("UserProfile", uselist=False)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def detector() -> RelationshipDetector:
    """Return a fresh RelationshipDetector instance."""
    return RelationshipDetector()


@pytest.fixture
def sync_engine():
    """Create a sync SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    RelBase.metadata.create_all(engine)
    yield engine
    engine.dispose()


# ==============================================================================
# RelationshipType Tests
# ==============================================================================


class TestRelationshipType:
    """Tests for RelationshipType enum."""

    def test_enum_values(self) -> None:
        """Test that enum has expected values."""
        assert RelationshipType.MANY_TO_ONE.value == "many_to_one"
        assert RelationshipType.ONE_TO_MANY.value == "one_to_many"
        assert RelationshipType.MANY_TO_MANY.value == "many_to_many"
        assert RelationshipType.ONE_TO_ONE.value == "one_to_one"


# ==============================================================================
# RelationshipInfo Tests
# ==============================================================================


class TestRelationshipInfo:
    """Tests for RelationshipInfo dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic RelationshipInfo creation."""
        info = RelationshipInfo(
            name="author",
            related_model=Author,
            relationship_type=RelationshipType.MANY_TO_ONE,
            foreign_key_column="author_id",
            nullable=True,
            uselist=False,
        )
        assert info.name == "author"
        assert info.related_model is Author
        assert info.relationship_type == RelationshipType.MANY_TO_ONE
        assert info.foreign_key_column == "author_id"
        assert info.nullable is True
        assert info.uselist is False

    def test_related_model_name_auto_set(self) -> None:
        """Test that related_model_name is auto-set from related_model."""
        info = RelationshipInfo(
            name="author",
            related_model=Author,
            relationship_type=RelationshipType.MANY_TO_ONE,
        )
        assert info.related_model_name == "Author"

    def test_is_to_many_property(self) -> None:
        """Test is_to_many property."""
        one_to_many = RelationshipInfo(
            name="posts",
            related_model=Post,
            relationship_type=RelationshipType.ONE_TO_MANY,
            uselist=True,
        )
        assert one_to_many.is_to_many is True
        assert one_to_many.is_to_one is False

        many_to_one = RelationshipInfo(
            name="author",
            related_model=Author,
            relationship_type=RelationshipType.MANY_TO_ONE,
            uselist=False,
        )
        assert many_to_one.is_to_many is False
        assert many_to_one.is_to_one is True

    def test_to_dict(self) -> None:
        """Test to_dict method for JSON serialization."""
        info = RelationshipInfo(
            name="author",
            related_model=Author,
            relationship_type=RelationshipType.MANY_TO_ONE,
            foreign_key_column="author_id",
            back_populates="posts",
            nullable=True,
            uselist=False,
        )
        result = info.to_dict()
        assert result["name"] == "author"
        assert result["related_model_name"] == "Author"
        assert result["relationship_type"] == "many_to_one"
        assert result["foreign_key_column"] == "author_id"
        assert result["back_populates"] == "posts"
        assert result["nullable"] is True
        assert result["uselist"] is False


# ==============================================================================
# RelationshipDetector Tests
# ==============================================================================


class TestRelationshipDetector:
    """Tests for RelationshipDetector class."""

    def test_detect_many_to_one_relationship(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test detecting MANY_TO_ONE relationships."""
        relationships = detector.detect_relationships(Post)

        # Post has one relationship: author
        assert len(relationships) == 1

        author_rel = relationships[0]
        assert author_rel.name == "author"
        assert author_rel.related_model is Author
        assert author_rel.relationship_type == RelationshipType.MANY_TO_ONE
        assert author_rel.foreign_key_column == "author_id"
        assert author_rel.back_populates == "posts"
        assert author_rel.uselist is False

    def test_detect_one_to_many_relationship(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test detecting ONE_TO_MANY relationships."""
        relationships = detector.detect_relationships(Author)

        # Author has one relationship: posts
        assert len(relationships) == 1

        posts_rel = relationships[0]
        assert posts_rel.name == "posts"
        assert posts_rel.related_model is Post
        assert posts_rel.relationship_type == RelationshipType.ONE_TO_MANY
        assert posts_rel.back_populates == "author"
        assert posts_rel.uselist is True

    def test_detect_many_to_many_relationship(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test detecting MANY_TO_MANY relationships."""
        relationships = detector.detect_relationships(Article)

        # Article has one relationship: tags
        assert len(relationships) == 1

        tags_rel = relationships[0]
        assert tags_rel.name == "tags"
        assert tags_rel.related_model is Tag
        assert tags_rel.relationship_type == RelationshipType.MANY_TO_MANY
        assert tags_rel.secondary_table == "article_tags"
        assert tags_rel.uselist is True

    def test_get_foreign_key_column(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test get_foreign_key_column method."""
        fk = detector.get_foreign_key_column(Post, "author")
        assert fk == "author_id"

        # Non-existent relationship returns None
        fk_none = detector.get_foreign_key_column(Post, "nonexistent")
        assert fk_none is None

    def test_get_related_model(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test get_related_model method."""
        related = detector.get_related_model(Post, "author")
        assert related is Author

        # Non-existent relationship returns None
        related_none = detector.get_related_model(Post, "nonexistent")
        assert related_none is None

    def test_get_relationship_info(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test get_relationship_info method."""
        info = detector.get_relationship_info(Post, "author")
        assert info is not None
        assert info.name == "author"
        assert info.related_model is Author

        # Non-existent relationship returns None
        info_none = detector.get_relationship_info(Post, "nonexistent")
        assert info_none is None

    def test_get_display_column(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test get_display_column method."""
        # Author has 'name' column which is a preferred display column
        display = detector.get_display_column(Author)
        assert display == "name"

        # Post has 'title' column which is a preferred display column
        display_post = detector.get_display_column(Post)
        assert display_post == "title"

    def test_is_relationship(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test is_relationship method."""
        assert detector.is_relationship(Post, "author") is True
        assert detector.is_relationship(Post, "title") is False
        assert detector.is_relationship(Post, "nonexistent") is False

    def test_get_relationship_names(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test get_relationship_names method."""
        names = detector.get_relationship_names(Post)
        assert names == ["author"]

        names_author = detector.get_relationship_names(Author)
        assert names_author == ["posts"]

    def test_caching(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test that relationship detection results are cached."""
        # First call
        relationships1 = detector.detect_relationships(Post)
        # Second call should return cached result
        relationships2 = detector.detect_relationships(Post)

        # Should be the same object (cached)
        assert relationships1 is relationships2

    def test_clear_cache(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test clear_cache method."""
        # Populate cache
        detector.detect_relationships(Post)
        detector.get_display_column(Author)

        # Clear cache
        detector.clear_cache()

        # Cache should be empty
        assert len(detector._cache) == 0
        assert len(detector._display_column_cache) == 0


# ==============================================================================
# get_relationship_detector Tests
# ==============================================================================


class TestGetRelationshipDetector:
    """Tests for get_relationship_detector function."""

    def test_returns_singleton(self) -> None:
        """Test that get_relationship_detector returns a singleton."""
        detector1 = get_relationship_detector()
        detector2 = get_relationship_detector()
        assert detector1 is detector2

    def test_returns_relationship_detector_instance(self) -> None:
        """Test that the returned object is a RelationshipDetector."""
        detector = get_relationship_detector()
        assert isinstance(detector, RelationshipDetector)


# ==============================================================================
# ModelView Integration Tests
# ==============================================================================


class PostAdmin(ModelView, model=Post):
    """Admin view for Post model."""

    column_list = ["id", "title", "author_id", "author"]
    column_searchable_list = ["title"]


class AuthorAdmin(ModelView, model=Author):
    """Admin view for Author model."""

    column_list = ["id", "name", "email", "posts"]


class TestModelViewRelationships:
    """Tests for ModelView relationship integration."""

    def test_relationship_fields(self, sync_engine) -> None:
        """Test relationship_fields returns detected relationships."""
        relationships = PostAdmin.relationship_fields()
        assert len(relationships) == 1
        assert relationships[0].name == "author"
        assert relationships[0].related_model is Author

    def test_get_relationship_info(self, sync_engine) -> None:
        """Test get_relationship_info on ModelView."""
        info = PostAdmin.get_relationship_info("author")
        assert info is not None
        assert info.name == "author"
        assert info.relationship_type == RelationshipType.MANY_TO_ONE

        # Non-relationship returns None
        info_none = PostAdmin.get_relationship_info("title")
        assert info_none is None

    def test_get_relationship_names(self, sync_engine) -> None:
        """Test get_relationship_names on ModelView."""
        names = PostAdmin.get_relationship_names()
        assert "author" in names

    def test_is_relationship_field(self, sync_engine) -> None:
        """Test is_relationship_field on ModelView."""
        assert PostAdmin.is_relationship_field("author") is True
        assert PostAdmin.is_relationship_field("title") is False

    def test_get_column_info_for_regular_column(self, sync_engine) -> None:
        """Test get_column_info for a regular column."""
        info = PostAdmin.get_column_info("title")
        assert info["name"] == "title"
        assert info["is_relationship"] is False
        assert "type" in info

    def test_get_column_info_for_relationship(self, sync_engine) -> None:
        """Test get_column_info for a relationship column."""
        info = PostAdmin.get_column_info("author")
        assert info["name"] == "author"
        assert info["is_relationship"] is True
        assert info["relationship_type"] == "many_to_one"
        assert info["related_model_name"] == "Author"
        assert info["uselist"] is False

    def test_get_display_column_for_related_model(self, sync_engine) -> None:
        """Test get_display_column_for_related_model on ModelView."""
        display = PostAdmin.get_display_column_for_related_model("author")
        assert display == "name"  # Author has 'name' column

        # Non-existent relationship returns None
        display_none = PostAdmin.get_display_column_for_related_model("nonexistent")
        assert display_none is None


# ==============================================================================
# Edge Case Tests
# ==============================================================================


class TestEdgeCases:
    """Tests for edge cases in relationship detection."""

    def test_model_without_relationships(self, detector: RelationshipDetector, sync_engine) -> None:
        """Test detecting relationships on a model with no relationships."""
        # Tag model has no relationships defined
        relationships = detector.detect_relationships(Tag)
        assert relationships == []

    def test_non_sqlalchemy_class(self, detector: RelationshipDetector) -> None:
        """Test detecting relationships on a non-SQLAlchemy class."""

        class PlainClass:
            pass

        relationships = detector.detect_relationships(PlainClass)
        assert relationships == []

    def test_nullable_relationship(
        self,
        detector: RelationshipDetector,
        sync_engine,
    ) -> None:
        """Test nullable detection for relationships."""
        info = detector.get_relationship_info(Post, "author")
        assert info is not None
        # author_id is nullable=True, so relationship should be nullable
        assert info.nullable is True
