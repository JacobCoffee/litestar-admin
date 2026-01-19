"""ImportController for CSV data import functionality."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from litestar import Controller, post
from litestar.datastructures import UploadFile  # noqa: TC002 - Required at runtime for Litestar DI
from litestar.exceptions import NotFoundException, ValidationException
from litestar.status_codes import HTTP_200_OK
from sqlalchemy import inspect

# Litestar requires these imports at runtime for dependency injection type resolution
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from litestar_admin.registry import ModelRegistry  # noqa: TC001

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapper

__all__ = [
    "ColumnMapping",
    "ColumnTypeInfo",
    "ImportController",
    "ImportExecuteResponse",
    "ImportPreviewResponse",
    "ImportValidationResponse",
    "RowError",
]

# Configuration constants
PREVIEW_ROW_COUNT = 10
MAX_SAMPLE_ROWS_FOR_TYPE_DETECTION = 100
SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
SUPPORTED_DELIMITERS = [",", ";", "\t", "|"]


@dataclass
class ColumnTypeInfo:
    """Information about a detected column type.

    Attributes:
        csv_column: The CSV column header name.
        detected_type: The detected data type (string, integer, float, boolean, date, datetime).
        sample_values: A few sample values from this column.
        nullable: Whether null/empty values were detected.
    """

    csv_column: str
    detected_type: str
    sample_values: list[str]
    nullable: bool = False


@dataclass
class ModelFieldInfo:
    """Information about a model field for mapping.

    Attributes:
        name: The field/column name.
        type: The JSON schema type.
        format: Optional format (date, datetime, email, etc.).
        nullable: Whether the field is nullable.
        required: Whether the field is required.
        primary_key: Whether this is a primary key.
        max_length: Maximum length for string fields.
    """

    name: str
    type: str
    format: str | None = None
    nullable: bool = True
    required: bool = False
    primary_key: bool = False
    max_length: int | None = None


@dataclass
class ImportPreviewResponse:
    """Response for CSV import preview.

    Attributes:
        headers: List of CSV column headers.
        preview_rows: First N rows of data as list of dicts.
        column_types: Detected type information for each column.
        model_schema: Model field information for mapping.
        delimiter: Detected delimiter character.
        encoding: Detected file encoding.
        total_rows: Estimated total number of data rows.
    """

    headers: list[str]
    preview_rows: list[dict[str, Any]]
    column_types: list[ColumnTypeInfo]
    model_schema: list[ModelFieldInfo]
    delimiter: str
    encoding: str
    total_rows: int


@dataclass
class ColumnMapping:
    """Mapping from a CSV column to a model field.

    Attributes:
        csv_column: The CSV column header name.
        model_field: The target model field name.
        transform: Optional transformation to apply (none, lowercase, uppercase, trim).
    """

    csv_column: str
    model_field: str
    transform: Literal["none", "lowercase", "uppercase", "trim"] | None = None


@dataclass
class RowError:
    """Validation error for a specific row.

    Attributes:
        row_number: The 1-indexed row number in the CSV.
        field: The field name where the error occurred.
        value: The problematic value.
        error: Description of the error.
    """

    row_number: int
    field: str
    value: str | None
    error: str


@dataclass
class ImportValidationResponse:
    """Response for CSV import validation.

    Attributes:
        errors: List of validation errors per row.
        valid_count: Number of rows that passed validation.
        invalid_count: Number of rows that failed validation.
        total_rows: Total number of rows processed.
        sample_valid_rows: Sample of valid rows for preview.
    """

    errors: list[RowError]
    valid_count: int
    invalid_count: int
    total_rows: int
    sample_valid_rows: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ImportExecuteResponse:
    """Response for CSV import execution (stub for now).

    Attributes:
        success: Whether the import was initiated successfully.
        message: Status message.
        job_id: Optional job ID for async import tracking.
    """

    success: bool
    message: str
    job_id: str | None = None


class ImportController(Controller):
    """Controller for importing model data from CSV files.

    Provides endpoints for previewing, validating, and executing CSV imports.
    The import process is designed as a multi-step wizard:

    1. Preview: Upload CSV, detect format, show preview with type detection
    2. Validate: Submit column mappings, validate all rows against model schema
    3. Execute: Perform the actual import (stub - to be implemented in task 9.7.4)

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - POST /admin/api/models/{model}/import/preview
        - POST /admin/api/models/{model}/import/validate
        - POST /admin/api/models/{model}/import/execute
    """

    path = "/api/models"
    tags: ClassVar[list[str]] = ["Import"]

    @post(
        "/{model_name:str}/import/preview",
        status_code=HTTP_200_OK,
        summary="Preview CSV import",
        description="Parse CSV file and return preview with detected types and model schema.",
    )
    async def preview_import(
        self,
        model_name: str,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,  # noqa: ARG002
        data: UploadFile,
    ) -> ImportPreviewResponse:
        """Preview a CSV file for import.

        Parses the uploaded CSV file, auto-detects the delimiter and encoding,
        and returns a preview with detected column types and the model schema
        for mapping configuration.

        Args:
            model_name: The name of the model to import into.
            admin_registry: The model registry containing all registered views.
            db_session: The database session (unused but required for DI).
            data: The uploaded CSV file.

        Returns:
            Preview response with headers, sample rows, detected types, and model schema.

        Raises:
            NotFoundException: If the model is not found.
            ValidationException: If the file cannot be parsed as CSV.
        """
        view_class = self._get_view_class(admin_registry, model_name)

        # Read and parse the CSV file
        content, encoding = await self._read_file_with_encoding(data)
        delimiter = self._detect_delimiter(content)

        try:
            rows, headers, total_rows = self._parse_csv(content, delimiter)
        except Exception as e:
            msg = f"Failed to parse CSV file: {e}"
            raise ValidationException(msg) from e

        if not headers:
            msg = "CSV file appears to be empty or has no headers"
            raise ValidationException(msg)

        # Get preview rows
        preview_rows = [dict(zip(headers, row, strict=False)) for row in rows[:PREVIEW_ROW_COUNT]]

        # Detect column types
        column_types = self._detect_column_types(headers, rows)

        # Get model schema
        model_schema = self._get_model_field_info(view_class.model)

        return ImportPreviewResponse(
            headers=headers,
            preview_rows=preview_rows,
            column_types=column_types,
            model_schema=model_schema,
            delimiter=delimiter,
            encoding=encoding,
            total_rows=total_rows,
        )

    @post(
        "/{model_name:str}/import/validate",
        status_code=HTTP_200_OK,
        summary="Validate CSV import",
        description="Validate all CSV rows against model schema with provided column mappings.",
    )
    async def validate_import(
        self,
        model_name: str,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,  # noqa: ARG002
        data: UploadFile,
        column_mappings: list[ColumnMapping],
    ) -> ImportValidationResponse:
        """Validate a CSV file for import.

        Parses the entire CSV file and validates each row against the model
        schema using the provided column mappings.

        Args:
            model_name: The name of the model to import into.
            admin_registry: The model registry containing all registered views.
            db_session: The database session (unused but required for DI).
            data: The uploaded CSV file.
            column_mappings: List of column mappings from CSV to model fields.

        Returns:
            Validation response with errors, valid/invalid counts.

        Raises:
            NotFoundException: If the model is not found.
            ValidationException: If the file cannot be parsed or mappings are invalid.
        """
        view_class = self._get_view_class(admin_registry, model_name)
        model = view_class.model

        # Validate column mappings
        model_fields = self._get_model_field_info(model)
        model_field_names = {f.name for f in model_fields}

        for mapping in column_mappings:
            if mapping.model_field not in model_field_names:
                msg = f"Unknown model field: '{mapping.model_field}'"
                raise ValidationException(msg)

        # Read and parse the CSV file
        content, _ = await self._read_file_with_encoding(data)
        delimiter = self._detect_delimiter(content)

        try:
            rows, headers, total_rows = self._parse_csv(content, delimiter)
        except Exception as e:
            msg = f"Failed to parse CSV file: {e}"
            raise ValidationException(msg) from e

        # Build lookup structures
        mapping_dict = {m.csv_column: m for m in column_mappings}
        field_info_dict = {f.name: f for f in model_fields}

        # Validate all rows
        errors: list[RowError] = []
        valid_count = 0
        sample_valid_rows: list[dict[str, Any]] = []

        for row_idx, row in enumerate(rows, start=2):  # Start at 2 (1-indexed, after header)
            row_data = dict(zip(headers, row, strict=False))
            row_errors = self._validate_row(
                row_number=row_idx,
                row_data=row_data,
                mapping_dict=mapping_dict,
                field_info_dict=field_info_dict,
            )

            if row_errors:
                errors.extend(row_errors)
            else:
                valid_count += 1
                # Collect sample valid rows for preview
                if len(sample_valid_rows) < PREVIEW_ROW_COUNT:
                    transformed_row = self._transform_row(row_data, mapping_dict)
                    sample_valid_rows.append(transformed_row)

        invalid_count = total_rows - valid_count

        return ImportValidationResponse(
            errors=errors[:100],  # Limit errors to first 100 for response size
            valid_count=valid_count,
            invalid_count=invalid_count,
            total_rows=total_rows,
            sample_valid_rows=sample_valid_rows,
        )

    @post(
        "/{model_name:str}/import/execute",
        status_code=HTTP_200_OK,
        summary="Execute CSV import",
        description="Execute the CSV import with provided column mappings (stub for task 9.7.4).",
    )
    async def execute_import(
        self,
        model_name: str,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,  # noqa: ARG002
        data: UploadFile,  # noqa: ARG002
        column_mappings: list[ColumnMapping],  # noqa: ARG002
    ) -> ImportExecuteResponse:
        """Execute a CSV import (stub for task 9.7.4).

        This endpoint will perform the actual import operation.
        Currently returns a placeholder response.

        Args:
            model_name: The name of the model to import into.
            admin_registry: The model registry containing all registered views.
            db_session: The database session.
            data: The uploaded CSV file.
            column_mappings: List of column mappings from CSV to model fields.

        Returns:
            Execution response (placeholder for now).

        Raises:
            NotFoundException: If the model is not found.
        """
        # Verify model exists
        self._get_view_class(admin_registry, model_name)

        # Stub response - actual implementation in task 9.7.4
        return ImportExecuteResponse(
            success=True,
            message=f"Import execution for '{model_name}' will be implemented in task 9.7.4",
            job_id=None,
        )

    @staticmethod
    def _get_view_class(
        registry: ModelRegistry,
        model_name: str,
    ) -> Any:
        """Get the view class for a model by name.

        Args:
            registry: The model registry.
            model_name: The model name to look up.

        Returns:
            The view class for the model.

        Raises:
            NotFoundException: If the model is not found.
        """
        if not registry.has_model_by_name(model_name):
            msg = f"Model '{model_name}' not found"
            raise NotFoundException(msg)
        return registry.get_view_by_name(model_name)

    @staticmethod
    async def _read_file_with_encoding(upload_file: UploadFile) -> tuple[str, str]:
        """Read an uploaded file and detect its encoding.

        Tries multiple encodings to find one that works, starting with UTF-8.

        Args:
            upload_file: The uploaded file.

        Returns:
            Tuple of (decoded content, detected encoding).

        Raises:
            ValidationException: If the file cannot be decoded with any supported encoding.
        """
        raw_content = await upload_file.read()

        # Try each encoding sequentially
        def try_decode(data: bytes, enc: str) -> str | None:
            """Attempt to decode bytes with the given encoding."""
            try:
                return data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                return None

        for encoding in SUPPORTED_ENCODINGS:
            content = try_decode(raw_content, encoding)
            if content is not None:
                return content, encoding

        msg = f"Unable to decode file. Tried encodings: {', '.join(SUPPORTED_ENCODINGS)}"
        raise ValidationException(msg)

    @staticmethod
    def _detect_delimiter(content: str) -> str:
        """Auto-detect the CSV delimiter from file content.

        Uses the csv.Sniffer for detection, with fallback to comma.

        Args:
            content: The file content as a string.

        Returns:
            The detected delimiter character.
        """
        # Take first few lines for sniffing
        sample = "\n".join(content.split("\n")[:20])

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="".join(SUPPORTED_DELIMITERS))
            return dialect.delimiter
        except csv.Error:
            # Fallback: count occurrences of each delimiter
            delimiter_counts = {d: sample.count(d) for d in SUPPORTED_DELIMITERS}
            return max(delimiter_counts, key=delimiter_counts.get)  # type: ignore[arg-type]

    @staticmethod
    def _parse_csv(content: str, delimiter: str) -> tuple[list[list[str]], list[str], int]:
        """Parse CSV content into rows.

        Args:
            content: The CSV content as a string.
            delimiter: The delimiter character to use.

        Returns:
            Tuple of (data rows, headers, total row count).

        Raises:
            ValidationException: If the CSV is malformed.
        """
        reader = csv.reader(io.StringIO(content), delimiter=delimiter)
        rows = list(reader)

        if not rows:
            return [], [], 0

        headers = rows[0]
        data_rows = rows[1:]
        total_rows = len(data_rows)

        # Validate row lengths
        header_len = len(headers)
        for idx, row in enumerate(data_rows):
            if len(row) != header_len:
                msg = f"Row {idx + 2} has {len(row)} columns, expected {header_len}"
                raise ValidationException(msg)

        return data_rows, headers, total_rows

    @staticmethod
    def _detect_column_types(headers: list[str], rows: list[list[str]]) -> list[ColumnTypeInfo]:
        """Detect data types for each CSV column.

        Examines sample values to infer the most likely type.

        Args:
            headers: List of column headers.
            rows: List of data rows.

        Returns:
            List of ColumnTypeInfo for each column.
        """
        sample_rows = rows[:MAX_SAMPLE_ROWS_FOR_TYPE_DETECTION]
        column_types: list[ColumnTypeInfo] = []

        for col_idx, header in enumerate(headers):
            values = [row[col_idx] for row in sample_rows if col_idx < len(row)]
            non_empty_values = [v for v in values if v.strip()]
            sample_values = non_empty_values[:5]

            nullable = len(non_empty_values) < len(values)
            detected_type = ImportController._infer_type(non_empty_values)

            column_types.append(
                ColumnTypeInfo(
                    csv_column=header,
                    detected_type=detected_type,
                    sample_values=sample_values,
                    nullable=nullable,
                )
            )

        return column_types

    @staticmethod
    def _infer_type(values: list[str]) -> str:
        """Infer the data type from a list of string values.

        Args:
            values: List of string values to analyze.

        Returns:
            Detected type: 'integer', 'float', 'boolean', 'date', 'datetime', or 'string'.
        """
        if not values:
            return "string"

        # Patterns for type detection
        int_pattern = re.compile(r"^-?\d+$")
        float_pattern = re.compile(r"^-?\d+\.?\d*$|^-?\d*\.?\d+$")
        bool_pattern = re.compile(r"^(true|false|yes|no|1|0)$", re.IGNORECASE)
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        datetime_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?")

        type_counts: dict[str, int] = {
            "integer": 0,
            "float": 0,
            "boolean": 0,
            "date": 0,
            "datetime": 0,
            "string": 0,
        }

        for raw_value in values:
            cleaned_value = raw_value.strip()
            if datetime_pattern.match(cleaned_value):
                type_counts["datetime"] += 1
            elif date_pattern.match(cleaned_value):
                type_counts["date"] += 1
            elif bool_pattern.match(cleaned_value):
                type_counts["boolean"] += 1
            elif int_pattern.match(cleaned_value):
                type_counts["integer"] += 1
            elif float_pattern.match(cleaned_value):
                type_counts["float"] += 1
            else:
                type_counts["string"] += 1

        # Return the most common type
        # Prefer more specific types in case of ties
        priority = ["datetime", "date", "boolean", "float", "integer", "string"]
        max_count = max(type_counts.values())

        for type_name in priority:
            if type_counts[type_name] == max_count:
                return type_name

        return "string"

    @staticmethod
    def _get_model_field_info(model: type[Any]) -> list[ModelFieldInfo]:
        """Extract field information from a SQLAlchemy model.

        Args:
            model: The SQLAlchemy model class.

        Returns:
            List of ModelFieldInfo for each column.
        """
        mapper: Mapper[Any] = inspect(model)
        fields: list[ModelFieldInfo] = []

        # Type mapping from SQLAlchemy to JSON schema types
        type_map: dict[str, tuple[str, str | None]] = {
            "INTEGER": ("integer", None),
            "BIGINTEGER": ("integer", None),
            "SMALLINTEGER": ("integer", None),
            "FLOAT": ("number", None),
            "NUMERIC": ("number", None),
            "DECIMAL": ("number", None),
            "BOOLEAN": ("boolean", None),
            "STRING": ("string", None),
            "VARCHAR": ("string", None),
            "TEXT": ("string", "textarea"),
            "DATE": ("string", "date"),
            "DATETIME": ("string", "date-time"),
            "TIMESTAMP": ("string", "date-time"),
            "TIME": ("string", "time"),
            "UUID": ("string", "uuid"),
            "JSON": ("object", None),
            "JSONB": ("object", None),
        }

        for column in mapper.columns:
            type_name = type(column.type).__name__.upper()
            json_type, json_format = type_map.get(type_name, ("string", None))

            # Determine if field is required
            has_default = column.default is not None or column.server_default is not None
            is_required = not column.nullable and not has_default and not column.primary_key

            # Get max length for string types
            max_length = None
            if hasattr(column.type, "length") and column.type.length:
                max_length = column.type.length

            fields.append(
                ModelFieldInfo(
                    name=column.name,
                    type=json_type,
                    format=json_format,
                    nullable=column.nullable,
                    required=is_required,
                    primary_key=column.primary_key,
                    max_length=max_length,
                )
            )

        return fields

    def _validate_row(
        self,
        row_number: int,
        row_data: dict[str, str],
        mapping_dict: dict[str, ColumnMapping],
        field_info_dict: dict[str, ModelFieldInfo],
    ) -> list[RowError]:
        """Validate a single row against the model schema.

        Args:
            row_number: The 1-indexed row number.
            row_data: The row data as a dict (csv_column -> value).
            mapping_dict: Mapping from csv_column to ColumnMapping.
            field_info_dict: Mapping from model_field to ModelFieldInfo.

        Returns:
            List of validation errors for this row.
        """
        errors: list[RowError] = []

        # Check required fields are provided
        required_fields = {f.name for f in field_info_dict.values() if f.required}
        mapped_model_fields = {m.model_field for m in mapping_dict.values()}
        missing_required = required_fields - mapped_model_fields

        for field_name in missing_required:
            errors.append(
                RowError(
                    row_number=row_number,
                    field=field_name,
                    value=None,
                    error=f"Required field '{field_name}' is not mapped",
                )
            )

        # Validate each mapped field
        for csv_column, mapping in mapping_dict.items():
            value = row_data.get(csv_column, "")
            field_info = field_info_dict.get(mapping.model_field)

            if field_info is None:
                continue

            # Apply transform
            transformed_value = self._apply_transform(value, mapping.transform)

            # Validate the value
            error = self._validate_value(transformed_value, field_info)
            if error:
                errors.append(
                    RowError(
                        row_number=row_number,
                        field=mapping.model_field,
                        value=value,
                        error=error,
                    )
                )

        return errors

    @staticmethod
    def _apply_transform(
        value: str,
        transform: Literal["none", "lowercase", "uppercase", "trim"] | None,
    ) -> str:
        """Apply a transformation to a value.

        Args:
            value: The original value.
            transform: The transformation to apply.

        Returns:
            The transformed value.
        """
        if transform is None or transform == "none":
            return value.strip()  # Always trim by default
        if transform == "lowercase":
            return value.strip().lower()
        if transform == "uppercase":
            return value.strip().upper()
        if transform == "trim":
            return value.strip()
        return value

    @staticmethod
    def _validate_value(value: str, field_info: ModelFieldInfo) -> str | None:  # noqa: PLR0911, C901
        """Validate a value against a field's constraints.

        Args:
            value: The value to validate.
            field_info: The field information with constraints.

        Returns:
            Error message if validation fails, None otherwise.
        """
        # Check required/nullable
        if not value:
            if field_info.required:
                return f"Field '{field_info.name}' is required"
            return None  # Empty value is OK for nullable fields

        # Type validation
        if field_info.type == "integer":
            try:
                int(value)
            except ValueError:
                return f"Expected integer, got '{value}'"

        elif field_info.type == "number":
            try:
                float(value)
            except ValueError:
                return f"Expected number, got '{value}'"

        elif field_info.type == "boolean" and value.lower() not in ("true", "false", "1", "0", "yes", "no"):
            return f"Expected boolean, got '{value}'"

        # Format validation
        if field_info.format == "date" and not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return f"Expected date format YYYY-MM-DD, got '{value}'"

        if field_info.format == "date-time" and not re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", value):
            return f"Expected datetime format, got '{value}'"

        if field_info.format == "uuid":
            uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
            if not re.match(uuid_pattern, value.lower()):
                return f"Expected UUID format, got '{value}'"

        # Max length validation
        if field_info.max_length and len(value) > field_info.max_length:
            return f"Value exceeds max length of {field_info.max_length} characters"

        return None

    def _transform_row(
        self,
        row_data: dict[str, str],
        mapping_dict: dict[str, ColumnMapping],
    ) -> dict[str, Any]:
        """Transform a row using the column mappings.

        Args:
            row_data: The row data as a dict (csv_column -> value).
            mapping_dict: Mapping from csv_column to ColumnMapping.

        Returns:
            Transformed row as dict (model_field -> transformed value).
        """
        result: dict[str, Any] = {}

        for csv_column, mapping in mapping_dict.items():
            value = row_data.get(csv_column, "")
            transformed_value = self._apply_transform(value, mapping.transform)
            result[mapping.model_field] = transformed_value

        return result
