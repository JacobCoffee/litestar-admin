"""Tests for file upload field types and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from litestar_admin.fields.file import (
    DEFAULT_FILE_EXTENSIONS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_THUMBNAIL_SIZE,
    FileField,
    FileFieldValidationError,
    ImageField,
    get_file_extension,
    is_image_extension,
    validate_file_field,
    validate_multiple_files,
)

if TYPE_CHECKING:
    pass


class TestFileField:
    """Tests for the FileField class."""

    def test_default_values(self) -> None:
        """Test FileField initializes with expected defaults."""
        field = FileField(name="document")

        assert field.name == "document"
        assert field.allowed_extensions is None
        assert field.max_size is None
        assert field.upload_to is None
        assert field.required is False
        assert field.multiple is False
        assert field.description is None
        assert field.label is None

    def test_allowed_extensions_set_default(self) -> None:
        """Test default allowed extensions are used when none specified."""
        field = FileField(name="document")
        assert field.allowed_extensions_set == DEFAULT_FILE_EXTENSIONS

    def test_allowed_extensions_set_custom(self) -> None:
        """Test custom allowed extensions are properly normalized."""
        field = FileField(name="document", allowed_extensions=["PDF", ".docx", "txt"])
        assert field.allowed_extensions_set == frozenset({"pdf", "docx", "txt"})

    def test_max_file_size_default(self) -> None:
        """Test default max file size is used when none specified."""
        field = FileField(name="document")
        assert field.max_file_size == DEFAULT_MAX_FILE_SIZE

    def test_max_file_size_custom(self) -> None:
        """Test custom max file size is used when specified."""
        custom_size = 5 * 1024 * 1024  # 5MB
        field = FileField(name="document", max_size=custom_size)
        assert field.max_file_size == custom_size

    def test_is_extension_allowed_valid(self) -> None:
        """Test extension validation passes for allowed extension."""
        field = FileField(name="document", allowed_extensions=["pdf", "docx"])
        assert field.is_extension_allowed("pdf") is True
        assert field.is_extension_allowed(".pdf") is True
        assert field.is_extension_allowed("PDF") is True

    def test_is_extension_allowed_invalid(self) -> None:
        """Test extension validation fails for disallowed extension."""
        field = FileField(name="document", allowed_extensions=["pdf", "docx"])
        assert field.is_extension_allowed("exe") is False
        assert field.is_extension_allowed("jpg") is False

    def test_is_size_allowed_valid(self) -> None:
        """Test size validation passes for allowed size."""
        field = FileField(name="document", max_size=1024)
        assert field.is_size_allowed(512) is True
        assert field.is_size_allowed(1024) is True

    def test_is_size_allowed_invalid(self) -> None:
        """Test size validation fails for too large or zero size."""
        field = FileField(name="document", max_size=1024)
        assert field.is_size_allowed(2048) is False
        assert field.is_size_allowed(0) is False
        assert field.is_size_allowed(-1) is False

    def test_to_dict(self) -> None:
        """Test field serialization to dictionary."""
        field = FileField(
            name="document",
            allowed_extensions=["pdf"],
            max_size=1024,
            upload_to="uploads",
            required=True,
            multiple=False,
            description="A document field",
            label="Document",
        )
        result = field.to_dict()

        assert result["name"] == "document"
        assert result["type"] == "file"
        assert result["allowed_extensions"] == ["pdf"]
        assert result["max_size"] == 1024
        assert result["upload_to"] == "uploads"
        assert result["required"] is True
        assert result["multiple"] is False
        assert result["description"] == "A document field"
        assert result["label"] == "Document"

    def test_to_dict_default_label(self) -> None:
        """Test field serialization generates label from name."""
        field = FileField(name="user_document")
        result = field.to_dict()
        assert result["label"] == "User Document"


class TestImageField:
    """Tests for the ImageField class."""

    def test_default_values(self) -> None:
        """Test ImageField initializes with expected defaults."""
        field = ImageField(name="photo")

        assert field.name == "photo"
        assert field.generate_thumbnail is True
        assert field.thumbnail_size == DEFAULT_THUMBNAIL_SIZE
        assert set(field.allowed_extensions or []) == set(DEFAULT_IMAGE_EXTENSIONS)

    def test_allowed_extensions_set_default(self) -> None:
        """Test default image extensions are used."""
        field = ImageField(name="photo")
        assert field.allowed_extensions_set == DEFAULT_IMAGE_EXTENSIONS

    def test_allowed_extensions_set_custom(self) -> None:
        """Test custom image extensions are properly normalized."""
        field = ImageField(name="photo", allowed_extensions=["PNG", ".jpg"])
        assert field.allowed_extensions_set == frozenset({"png", "jpg"})

    def test_thumbnail_size_custom(self) -> None:
        """Test custom thumbnail size is used."""
        field = ImageField(name="photo", thumbnail_size=(100, 100))
        assert field.thumbnail_size == (100, 100)

    def test_to_dict(self) -> None:
        """Test field serialization includes image-specific fields."""
        field = ImageField(
            name="photo",
            generate_thumbnail=True,
            thumbnail_size=(150, 150),
        )
        result = field.to_dict()

        assert result["name"] == "photo"
        assert result["type"] == "image"
        assert result["generate_thumbnail"] is True
        assert result["thumbnail_size"] == [150, 150]


class TestFileFieldValidationError:
    """Tests for the FileFieldValidationError dataclass."""

    def test_error_creation(self) -> None:
        """Test validation error creation."""
        error = FileFieldValidationError(
            field_name="document",
            error="File too large",
            error_code="file_too_large",
        )
        assert error.field_name == "document"
        assert error.error == "File too large"
        assert error.error_code == "file_too_large"


class TestValidateFileField:
    """Tests for the validate_file_field function."""

    @dataclass
    class MockUploadFile:
        """Mock UploadFile for testing."""

        filename: str | None
        size: int = 0
        content_type: str | None = None

    def test_required_field_missing(self) -> None:
        """Test validation fails for required field without file."""
        field = FileField(name="document", required=True)
        file = self.MockUploadFile(filename=None)

        errors = validate_file_field(file, field)  # type: ignore[arg-type]

        assert len(errors) == 1
        assert errors[0].error_code == "required"

    def test_optional_field_empty(self) -> None:
        """Test validation passes for optional field without file."""
        field = FileField(name="document", required=False)
        file = self.MockUploadFile(filename=None)

        errors = validate_file_field(file, field)  # type: ignore[arg-type]

        assert len(errors) == 0

    def test_no_extension(self) -> None:
        """Test validation fails for file without extension."""
        field = FileField(name="document")
        file = self.MockUploadFile(filename="noextension")

        errors = validate_file_field(file, field)  # type: ignore[arg-type]

        assert len(errors) == 1
        assert errors[0].error_code == "no_extension"

    def test_invalid_extension(self) -> None:
        """Test validation fails for disallowed extension."""
        field = FileField(name="document", allowed_extensions=["pdf"])
        file = self.MockUploadFile(filename="document.exe")

        errors = validate_file_field(file, field)  # type: ignore[arg-type]

        assert len(errors) == 1
        assert errors[0].error_code == "invalid_extension"

    def test_valid_extension(self) -> None:
        """Test validation passes for allowed extension."""
        field = FileField(name="document", allowed_extensions=["pdf"])
        file = self.MockUploadFile(filename="document.pdf")

        errors = validate_file_field(file, field)  # type: ignore[arg-type]

        assert len(errors) == 0

    def test_file_too_large_with_content(self) -> None:
        """Test validation fails for file exceeding max size."""
        field = FileField(name="document", max_size=100)
        file = self.MockUploadFile(filename="document.pdf")
        content = b"x" * 200  # 200 bytes

        errors = validate_file_field(file, field, file_content=content)  # type: ignore[arg-type]

        assert len(errors) == 1
        assert errors[0].error_code == "file_too_large"

    def test_file_size_allowed_with_content(self) -> None:
        """Test validation passes for file within size limit."""
        field = FileField(name="document", max_size=1000)
        file = self.MockUploadFile(filename="document.pdf")
        content = b"x" * 500

        errors = validate_file_field(file, field, file_content=content)  # type: ignore[arg-type]

        assert len(errors) == 0


class TestValidateMultipleFiles:
    """Tests for the validate_multiple_files function."""

    @dataclass
    class MockUploadFile:
        """Mock UploadFile for testing."""

        filename: str | None
        size: int = 0
        content_type: str | None = None

    def test_multiple_not_allowed(self) -> None:
        """Test validation fails when multiple files but not allowed."""
        field = FileField(name="document", multiple=False)
        files = [
            self.MockUploadFile(filename="doc1.pdf"),
            self.MockUploadFile(filename="doc2.pdf"),
        ]

        errors = validate_multiple_files(files, field)  # type: ignore[arg-type]

        assert len(errors) == 1
        assert errors[0].error_code == "multiple_not_allowed"

    def test_multiple_allowed(self) -> None:
        """Test validation passes for multiple files when allowed."""
        field = FileField(name="document", multiple=True, allowed_extensions=["pdf"])
        files = [
            self.MockUploadFile(filename="doc1.pdf"),
            self.MockUploadFile(filename="doc2.pdf"),
        ]

        errors = validate_multiple_files(files, field)  # type: ignore[arg-type]

        assert len(errors) == 0

    def test_required_empty_list(self) -> None:
        """Test validation fails for required field with empty list."""
        field = FileField(name="document", required=True, multiple=True)
        files: list = []

        errors = validate_multiple_files(files, field)  # type: ignore[arg-type]

        assert len(errors) == 1
        assert errors[0].error_code == "required"


class TestHelperFunctions:
    """Tests for helper functions in the file module."""

    def test_get_file_extension(self) -> None:
        """Test file extension extraction."""
        assert get_file_extension("document.pdf") == "pdf"
        assert get_file_extension("document.PDF") == "pdf"
        assert get_file_extension("file.tar.gz") == "gz"
        assert get_file_extension("noextension") == ""

    def test_is_image_extension(self) -> None:
        """Test image extension detection."""
        assert is_image_extension("jpg") is True
        assert is_image_extension(".jpeg") is True
        assert is_image_extension("PNG") is True
        assert is_image_extension("webp") is True
        assert is_image_extension("pdf") is False
        assert is_image_extension("exe") is False
