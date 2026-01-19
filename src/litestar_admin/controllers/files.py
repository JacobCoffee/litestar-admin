"""FilesController for file upload and management.

This module provides REST API endpoints for file uploads, downloads, and deletion
in the admin panel.

Example:
    The controller is automatically registered by AdminPlugin.
    Access endpoints at:
    - POST /admin/api/files/upload - Upload a file
    - DELETE /admin/api/files/{path:path} - Delete a file
    - GET /admin/api/files/{path:path} - Serve or redirect to a file
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from litestar import Controller, Request, delete, get, post
from litestar.datastructures import UploadFile  # noqa: TC002  # Required for runtime signature
from litestar.enums import RequestEncodingType
from litestar.exceptions import NotFoundException
from litestar.params import Body, Parameter
from litestar.response import Redirect, Response
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from litestar_admin.logging import get_logger

_logger = get_logger(__name__)

from litestar_admin.contrib.storages import AdminStorageBackend
from litestar_admin.fields.file import (
    FileField,
    ImageField,
    validate_file_field,
)

__all__ = [
    "DeleteFileResponse",
    "FileInfoResponse",
    "FilesController",
    "ThumbnailResponse",
    "UploadFileRequest",
    "UploadFileResponse",
]


@dataclass
class UploadFileRequest:
    """Request body for file upload.

    Attributes:
        model_name: The name of the model this file belongs to.
        field_name: The name of the field this file belongs to.
    """

    model_name: str
    field_name: str


@dataclass
class UploadFileResponse:
    """Response for successful file upload.

    Attributes:
        success: Whether the upload was successful.
        storage_path: The path where the file was stored.
        original_filename: The original filename from the upload.
        file_size: The size of the file in bytes.
        content_type: The MIME type of the file.
        public_url: The public URL to access the file.
        thumbnail_path: Path to the generated thumbnail (for images).
        thumbnail_url: URL to access the thumbnail (for images).
    """

    success: bool
    storage_path: str
    original_filename: str
    file_size: int
    content_type: str | None = None
    public_url: str | None = None
    thumbnail_path: str | None = None
    thumbnail_url: str | None = None


@dataclass
class DeleteFileResponse:
    """Response for file deletion.

    Attributes:
        success: Whether the deletion was successful.
        path: The path of the deleted file.
        message: Optional message about the deletion.
    """

    success: bool
    path: str
    message: str | None = None


@dataclass
class FileInfoResponse:
    """Response with file information.

    Attributes:
        exists: Whether the file exists.
        path: The storage path of the file.
        public_url: The public URL to access the file.
    """

    exists: bool
    path: str
    public_url: str | None = None


@dataclass
class ValidationErrorResponse:
    """Response for validation errors.

    Attributes:
        success: Always False for validation errors.
        errors: List of validation error details.
    """

    success: bool
    errors: list[dict[str, str]]


@dataclass
class ThumbnailResponse:
    """Response with thumbnail information.

    Attributes:
        success: Whether thumbnail generation was successful.
        thumbnail_path: The storage path of the thumbnail.
        thumbnail_url: The public URL to access the thumbnail.
        width: Actual width of the generated thumbnail.
        height: Actual height of the generated thumbnail.
        format: The output format (webp, jpeg, png).
        size_bytes: Size of the thumbnail in bytes.
    """

    success: bool
    thumbnail_path: str | None = None
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    format: str | None = None
    size_bytes: int | None = None
    error: str | None = None


class FilesController(Controller):
    """Controller for file upload and management.

    Provides endpoints for uploading, serving, and deleting files.
    Integrates with the storage backend system and file field validation.

    Example:
        The controller is automatically registered by AdminPlugin.
        Upload a file::

            POST /admin/api/files/upload
            Content-Type: multipart/form-data

            file: <binary>
            model_name: "user"
            field_name: "avatar"
    """

    path = "/api/files"
    tags: ClassVar[list[str]] = ["Files"]

    @post(
        "/upload",
        status_code=HTTP_201_CREATED,
        summary="Upload a file",
        description="Upload a file for a specific model field.",
    )
    async def upload_file(
        self,
        request: Request,
        admin_storage: AdminStorageBackend | None = None,
    ) -> UploadFileResponse | Response[ValidationErrorResponse]:
        """Upload a file for a model field.

        This endpoint handles file uploads with validation against the provided
        field configuration. It supports both regular files and images with
        optional thumbnail generation.

        Args:
            admin_storage: The storage backend for file operations.
            data: The uploaded file from the multipart form.
            model_name: The name of the model this file belongs to.
            field_name: The name of the field this file belongs to.
            allowed_extensions: Comma-separated list of allowed extensions.
            max_size: Maximum file size in bytes.
            generate_thumbnail: Whether to generate a thumbnail (for images).

        Returns:
            UploadFileResponse on success, or validation error response.

        Raises:
            ValidationException: If the file fails validation.
        """
        # Get query params
        model_name = request.query_params.get("model_name", "unknown")
        field_name = request.query_params.get("field_name", "file")
        allowed_extensions = request.query_params.get("allowed_extensions")
        max_size_str = request.query_params.get("max_size")
        max_size = int(max_size_str) if max_size_str else None
        generate_thumbnail = request.query_params.get("generate_thumbnail", "false").lower() == "true"

        # Debug logging
        _logger.info(f"=== FILE UPLOAD DEBUG ===")
        _logger.info(f"model_name: {model_name}")
        _logger.info(f"field_name: {field_name}")
        _logger.info(f"admin_storage: {admin_storage}")
        _logger.info(f"Content-Type: {request.headers.get('content-type')}")

        # Check if storage is configured
        if admin_storage is None:
            _logger.error("Storage not configured!")
            return Response(
                content=ValidationErrorResponse(
                    success=False,
                    errors=[
                        {
                            "field": field_name,
                            "error": "File storage is not configured. Configure storage in AdminConfig.",
                        }
                    ],
                ),
                status_code=HTTP_200_OK,
            )

        # Get uploaded file from form data
        try:
            form_data = await request.form()
            _logger.info(f"Form data keys: {list(form_data.keys())}")
            for key, value in form_data.items():
                _logger.info(f"  {key}: {type(value).__name__} = {value if not isinstance(value, UploadFile) else f'UploadFile({value.filename})'}")
        except Exception as e:
            _logger.error(f"Error parsing form data: {e}")
            return Response(
                content=ValidationErrorResponse(
                    success=False,
                    errors=[
                        {
                            "field": field_name,
                            "error": f"Error parsing form data: {e}",
                        }
                    ],
                ),
                status_code=HTTP_200_OK,
            )

        data = form_data.get("data")
        _logger.info(f"data field: {type(data).__name__ if data else 'None'}")
        if not isinstance(data, UploadFile):
            return Response(
                content=ValidationErrorResponse(
                    success=False,
                    errors=[
                        {
                            "field": field_name,
                            "error": "No file uploaded. Please select a file.",
                        }
                    ],
                ),
                status_code=HTTP_200_OK,
            )

        # Read file content
        file_content = await data.read()
        _logger.info(f"File content length: {len(file_content)} bytes")

        # Only validate if explicit restrictions are provided
        # Otherwise allow any file type through the generic endpoint
        if allowed_extensions or max_size:
            extensions_list = None
            if allowed_extensions:
                extensions_list = [ext.strip() for ext in allowed_extensions.split(",")]

            if generate_thumbnail:
                field_config: FileField = ImageField(
                    name=field_name,
                    allowed_extensions=extensions_list,
                    max_size=max_size,
                    generate_thumbnail=True,
                )
            else:
                field_config = FileField(
                    name=field_name,
                    allowed_extensions=extensions_list,
                    max_size=max_size,
                )

            _logger.info(f"File config: extensions={extensions_list}, max_size={max_size}")

            # Validate the file
            validation_errors = validate_file_field(data, field_config, file_content=file_content)
            _logger.info(f"Validation errors: {validation_errors}")

            if validation_errors:
                for err in validation_errors:
                    _logger.error(f"Validation error: field={err.field_name}, error={err.error}, code={err.error_code}")
                return Response(
                    content=ValidationErrorResponse(
                        success=False,
                        errors=[
                            {
                                "field": err.field_name,
                                "error": err.error,
                                "code": err.error_code,
                            }
                            for err in validation_errors
                        ],
                    ),
                    status_code=422,
                )
        else:
            _logger.info("No validation restrictions specified, allowing any file type")
            field_config = None

        # Upload the file
        try:
            _logger.info(f"Starting upload to storage... generate_thumbnail={generate_thumbnail}")
            # Generate thumbnail if requested (regardless of validation config)
            should_generate_thumb = generate_thumbnail or (isinstance(field_config, ImageField) and field_config.generate_thumbnail)
            if should_generate_thumb:
                storage_path, thumbnail_path = await admin_storage.upload_with_thumbnail(
                    file_content=file_content,
                    filename=data.filename or "unnamed",
                    model_name=model_name,
                    field_name=field_name,
                )
                thumbnail_url = admin_storage.get_public_url(thumbnail_path) if thumbnail_path else None
                _logger.info(f"Thumbnail generated: {thumbnail_path} -> {thumbnail_url}")
            else:
                storage_path = await admin_storage.upload(
                    file_content=file_content,
                    filename=data.filename or "unnamed",
                    model_name=model_name,
                    field_name=field_name,
                )
                thumbnail_path = None
                thumbnail_url = None

            public_url = admin_storage.get_public_url(storage_path)
            _logger.info(f"Upload successful: {storage_path} -> {public_url}")
        except Exception as e:
            _logger.error(f"Upload failed: {e}", exc_info=True)
            return Response(
                content=ValidationErrorResponse(
                    success=False,
                    errors=[
                        {
                            "field": field_name,
                            "error": f"Upload failed: {e}",
                        }
                    ],
                ),
                status_code=500,
            )

        return UploadFileResponse(
            success=True,
            storage_path=storage_path,
            original_filename=data.filename or "unnamed",
            file_size=len(file_content),
            content_type=data.content_type,
            public_url=public_url,
            thumbnail_path=thumbnail_path,
            thumbnail_url=thumbnail_url,
        )

    @post(
        "/upload/validate",
        status_code=HTTP_200_OK,
        summary="Validate file upload",
        description="Validate a file against field configuration without uploading.",
    )
    async def validate_upload(
        self,
        data: UploadFile = Body(media_type=RequestEncodingType.MULTI_PART),
        field_name: str = Body(),
        allowed_extensions: str | None = Body(default=None),
        max_size: int | None = Body(default=None),
        is_image: bool = Body(default=False),  # noqa: FBT001
        required: bool = Body(default=False),  # noqa: FBT001
    ) -> dict[str, Any]:
        """Validate a file without uploading.

        This endpoint allows pre-validation of files before actual upload,
        useful for client-side validation feedback.

        Args:
            data: The uploaded file to validate.
            field_name: The name of the field for error reporting.
            allowed_extensions: Comma-separated list of allowed extensions.
            max_size: Maximum file size in bytes.
            is_image: Whether this is an image field.
            required: Whether the field is required.

        Returns:
            Dictionary with validation result and any errors.
        """
        extensions_list = None
        if allowed_extensions:
            extensions_list = [ext.strip() for ext in allowed_extensions.split(",")]

        if is_image:
            field_config: FileField = ImageField(
                name=field_name,
                allowed_extensions=extensions_list,
                max_size=max_size,
                required=required,
            )
        else:
            field_config = FileField(
                name=field_name,
                allowed_extensions=extensions_list,
                max_size=max_size,
                required=required,
            )

        # Read file content for size validation
        file_content = await data.read()

        # Validate
        validation_errors = validate_file_field(data, field_config, file_content=file_content)

        if validation_errors:
            return {
                "valid": False,
                "errors": [
                    {
                        "field": err.field_name,
                        "error": err.error,
                        "code": err.error_code,
                    }
                    for err in validation_errors
                ],
            }

        return {
            "valid": True,
            "file_info": {
                "filename": data.filename,
                "size": len(file_content),
                "content_type": data.content_type,
            },
        }

    @delete(
        "/{file_path:path}",
        status_code=HTTP_200_OK,
        summary="Delete a file",
        description="Delete a file from storage by its path.",
    )
    async def delete_file(
        self,
        file_path: str,
        admin_storage: AdminStorageBackend,
    ) -> DeleteFileResponse:
        """Delete a file from storage.

        Args:
            file_path: The storage path of the file to delete.
            admin_storage: The storage backend for file operations.

        Returns:
            DeleteFileResponse indicating success or failure.

        Raises:
            NotFoundException: If the file does not exist.
        """
        # Check if file exists
        if not await admin_storage.exists(file_path):
            raise NotFoundException(f"File not found: {file_path}")

        # Delete the file
        await admin_storage.delete(file_path)

        return DeleteFileResponse(
            success=True,
            path=file_path,
            message="File deleted successfully",
        )

    @get(
        "/{file_path:path}",
        status_code=HTTP_200_OK,
        summary="Get file or redirect",
        description="Serve a file or redirect to its storage URL.",
    )
    async def get_file(
        self,
        file_path: str,
        admin_storage: AdminStorageBackend,
        download: bool = False,  # noqa: FBT001, FBT002
    ) -> Response[bytes] | Redirect:
        """Get a file from storage.

        This endpoint either serves the file directly or redirects to its
        public URL depending on the storage configuration.

        Args:
            file_path: The storage path of the file.
            admin_storage: The storage backend for file operations.
            download: If True, force download with Content-Disposition header.

        Returns:
            File content or redirect to public URL.

        Raises:
            NotFoundException: If the file does not exist.
        """
        # Check if file exists
        if not await admin_storage.exists(file_path):
            raise NotFoundException(f"File not found: {file_path}")

        # Get public URL
        public_url = admin_storage.get_public_url(file_path)

        # If we have a public URL that's not a relative path, redirect
        if public_url.startswith(("http://", "https://")):
            return Redirect(path=public_url)

        # Otherwise, serve the file directly
        content = await admin_storage.read(file_path)

        # Determine content type from extension
        filename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
        content_type = _get_content_type(filename)

        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        return Response(
            content=content,
            media_type=content_type,
            headers=headers,
        )

    @get(
        "/info/{file_path:path}",
        status_code=HTTP_200_OK,
        summary="Get file info",
        description="Get information about a file without downloading it.",
    )
    async def get_file_info(
        self,
        file_path: str,
        admin_storage: AdminStorageBackend,
    ) -> FileInfoResponse:
        """Get information about a file.

        Args:
            file_path: The storage path of the file.
            admin_storage: The storage backend for file operations.

        Returns:
            FileInfoResponse with file existence and URL.
        """
        exists = await admin_storage.exists(file_path)
        public_url = admin_storage.get_public_url(file_path) if exists else None

        return FileInfoResponse(
            exists=exists,
            path=file_path,
            public_url=public_url,
        )

    @staticmethod
    def _validate_thumbnail_params(
        file_path: str,
        size: str,
        format: str | None,  # noqa: A002
        quality: int | None,
    ) -> ThumbnailResponse | tuple[int, int]:
        """Validate thumbnail request parameters.

        Returns either a ThumbnailResponse with error or parsed size tuple.
        """
        from litestar_admin.contrib.storages.thumbnails import ThumbnailGenerator

        # Validate that it's an image
        if not ThumbnailGenerator.is_supported_image(file_path):
            return ThumbnailResponse(
                success=False,
                error=f"Not a supported image format: {file_path}",
            )

        # Parse size string
        parsed_size = ThumbnailGenerator.parse_size_string(size)
        if parsed_size is None:
            return ThumbnailResponse(
                success=False,
                error=f"Invalid size format: {size}. Expected format: WIDTHxHEIGHT (e.g., 200x200)",
            )

        # Validate quality if provided
        if quality is not None and not 1 <= quality <= 100:  # noqa: PLR2004
            return ThumbnailResponse(
                success=False,
                error="Quality must be between 1 and 100",
            )

        # Validate format if provided
        if format is not None:
            allowed_formats = {"jpeg", "jpg", "png", "webp"}
            if format.lower() not in allowed_formats:
                return ThumbnailResponse(
                    success=False,
                    error=f"Invalid format: {format}. Allowed: {', '.join(sorted(allowed_formats))}",
                )

        return parsed_size

    @get(
        "/thumbnail/{file_path:path}",
        status_code=HTTP_200_OK,
        summary="Get or generate thumbnail",
        description="Get an existing thumbnail or generate one on-the-fly for an image.",
    )
    async def get_thumbnail(
        self,
        file_path: str,
        admin_storage: AdminStorageBackend,
        size: str = "200x200",
        format: str | None = None,  # noqa: A002
        quality: int | None = None,
        download: bool = False,  # noqa: FBT001, FBT002
    ) -> Response[bytes] | ThumbnailResponse:
        """Get or generate a thumbnail for an image.

        This endpoint returns a thumbnail for the specified image. If a thumbnail
        at the requested size already exists, it is returned. Otherwise, a new
        thumbnail is generated and stored for future requests.

        Args:
            file_path: The storage path of the source image.
            admin_storage: The storage backend for file operations.
            size: Thumbnail size in format 'WIDTHxHEIGHT' (e.g., '200x200').
            format: Output format (webp, jpeg, png). Defaults to configured format.
            quality: Quality for JPEG/WebP (1-100). Defaults to configured quality.
            download: If True, force download with Content-Disposition header.

        Returns:
            The thumbnail image bytes or error response.

        Raises:
            NotFoundException: If the source file does not exist.

        Example:
            GET /admin/api/files/thumbnail/uploads/user/avatar/photo.jpg?size=150x150&format=webp
        """
        # Check if source file exists
        if not await admin_storage.exists(file_path):
            raise NotFoundException(f"File not found: {file_path}")

        # Validate parameters
        validation_result = self._validate_thumbnail_params(file_path, size, format, quality)
        if isinstance(validation_result, ThumbnailResponse):
            return validation_result
        parsed_size = validation_result

        try:
            # Get or generate thumbnail
            thumbnail_content, thumbnail_path = await admin_storage.get_or_generate_thumbnail(
                path=file_path,
                size=parsed_size,
                format=format,
                quality=quality,
            )

            # Get content type for the thumbnail
            content_type = _get_thumbnail_content_type(format or admin_storage.config.thumbnails.format)

            # Build response headers
            headers = {}
            if download:
                filename = thumbnail_path.rsplit("/", 1)[-1] if "/" in thumbnail_path else thumbnail_path
                headers["Content-Disposition"] = f'attachment; filename="{filename}"'

            return Response(
                content=thumbnail_content,
                media_type=content_type,
                headers=headers,
            )

        except FileNotFoundError:
            raise NotFoundException(f"File not found: {file_path}") from None
        except ValueError as e:
            return ThumbnailResponse(
                success=False,
                error=str(e),
            )

    @get(
        "/thumbnail/info/{file_path:path}",
        status_code=HTTP_200_OK,
        summary="Get thumbnail info",
        description="Get information about a thumbnail without downloading it.",
    )
    async def get_thumbnail_info(
        self,
        file_path: str,
        admin_storage: AdminStorageBackend,
        size: str = "200x200",
        format: str | None = None,  # noqa: A002
    ) -> ThumbnailResponse:
        """Get information about a thumbnail.

        This endpoint checks if a thumbnail exists and returns its metadata
        without generating or downloading it.

        Args:
            file_path: The storage path of the source image.
            admin_storage: The storage backend for file operations.
            size: Thumbnail size in format 'WIDTHxHEIGHT' (e.g., '200x200').
            format: Output format (webp, jpeg, png).

        Returns:
            ThumbnailResponse with thumbnail existence and URL.
        """
        from litestar_admin.contrib.storages.thumbnails import ThumbnailGenerator

        # Check if source file exists
        if not await admin_storage.exists(file_path):
            return ThumbnailResponse(
                success=False,
                error=f"Source file not found: {file_path}",
            )

        # Validate that it's an image
        if not ThumbnailGenerator.is_supported_image(file_path):
            return ThumbnailResponse(
                success=False,
                error=f"Not a supported image format: {file_path}",
            )

        # Parse size string
        parsed_size = ThumbnailGenerator.parse_size_string(size)
        if parsed_size is None:
            return ThumbnailResponse(
                success=False,
                error=f"Invalid size format: {size}. Expected format: WIDTHxHEIGHT (e.g., 200x200)",
            )

        output_format = format or admin_storage.config.thumbnails.format

        generator = ThumbnailGenerator(default_format=output_format)
        thumb_path = generator.get_thumbnail_path(file_path, parsed_size, output_format)

        # Check if thumbnail exists
        exists = await admin_storage.exists(thumb_path)

        if exists:
            thumbnail_url = admin_storage.get_public_url(thumb_path)
            return ThumbnailResponse(
                success=True,
                thumbnail_path=thumb_path,
                thumbnail_url=thumbnail_url,
                width=parsed_size[0],
                height=parsed_size[1],
                format=output_format,
            )

        return ThumbnailResponse(
            success=True,
            thumbnail_path=None,
            thumbnail_url=None,
            width=parsed_size[0],
            height=parsed_size[1],
            format=output_format,
            error="Thumbnail does not exist yet. Use GET /thumbnail/{path} to generate it.",
        )


def _get_thumbnail_content_type(output_format: str) -> str:
    """Get the MIME content type for a thumbnail format.

    Args:
        output_format: The thumbnail output format (webp, jpeg, png).

    Returns:
        The MIME content type string.
    """
    format_lower = output_format.lower()
    if format_lower in ("jpg", "jpeg"):
        return "image/jpeg"
    if format_lower == "png":
        return "image/png"
    if format_lower == "webp":
        return "image/webp"
    return "image/jpeg"


def _get_content_type(filename: str) -> str:
    """Get the MIME content type for a filename.

    Args:
        filename: The filename to get the content type for.

    Returns:
        The MIME content type string.
    """
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    content_types = {
        # Images
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "svg": "image/svg+xml",
        "ico": "image/x-icon",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        # Documents
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "txt": "text/plain",
        "csv": "text/csv",
        "rtf": "application/rtf",
        "odt": "application/vnd.oasis.opendocument.text",
        "ods": "application/vnd.oasis.opendocument.spreadsheet",
        "odp": "application/vnd.oasis.opendocument.presentation",
        # Archives
        "zip": "application/zip",
        "tar": "application/x-tar",
        "gz": "application/gzip",
        "7z": "application/x-7z-compressed",
        "rar": "application/vnd.rar",
        # Text/Code
        "json": "application/json",
        "xml": "application/xml",
        "yaml": "application/x-yaml",
        "yml": "application/x-yaml",
        "md": "text/markdown",
        "html": "text/html",
        "css": "text/css",
        "js": "application/javascript",
    }

    return content_types.get(extension, "application/octet-stream")
