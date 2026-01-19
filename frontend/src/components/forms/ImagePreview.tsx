"use client";

import { forwardRef, useCallback, useEffect, useState, type HTMLAttributes } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";

// ============================================================================
// Types
// ============================================================================

export interface ImagePreviewProps extends Omit<HTMLAttributes<HTMLDivElement>, "onClick"> {
  /** URL of the image to display */
  src: string;
  /** Alt text for the image */
  alt?: string;
  /** Thumbnail URL (falls back to src if not provided) */
  thumbnailSrc?: string;
  /** Whether the image can be clicked to open lightbox */
  enableLightbox?: boolean;
  /** Callback when remove button is clicked */
  onRemove?: () => void;
  /** Whether the remove button is disabled */
  removeDisabled?: boolean;
  /** Size of the thumbnail */
  size?: "sm" | "md" | "lg";
  /** Whether to show a border around the thumbnail */
  bordered?: boolean;
}

export interface ImageLightboxProps {
  /** Whether the lightbox is open */
  isOpen: boolean;
  /** Callback to close the lightbox */
  onClose: () => void;
  /** URL of the image to display */
  src: string;
  /** Alt text for the image */
  alt?: string;
}

// ============================================================================
// Icons
// ============================================================================

function XIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="3,6 5,6 21,6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function ExpandIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="15,3 21,3 21,9" />
      <polyline points="9,21 3,21 3,15" />
      <line x1="21" y1="3" x2="14" y2="10" />
      <line x1="3" y1="21" x2="10" y2="14" />
    </svg>
  );
}

function ImageBrokenIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="3" y1="3" x2="21" y2="21" />
    </svg>
  );
}

// ============================================================================
// ImageLightbox Component
// ============================================================================

/**
 * Full-screen lightbox modal for viewing images.
 */
export function ImageLightbox({ isOpen, onClose, src, alt = "Image preview" }: ImageLightboxProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  // Reset loading/error state when src changes
  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      setHasError(false);
    }
  }, [isOpen, src]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  const handleImageLoad = useCallback(() => {
    setIsLoading(false);
  }, []);

  const handleImageError = useCallback(() => {
    setIsLoading(false);
    setHasError(true);
  }, []);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose],
  );

  if (!isOpen) return null;

  const lightboxContent = (
    <div
      className={cn(
        "fixed inset-0 z-50",
        "flex items-center justify-center",
        "bg-black/90 backdrop-blur-sm",
        "animate-[fadeIn_150ms_ease-out]",
      )}
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label="Image preview"
    >
      {/* Close Button */}
      <button
        type="button"
        onClick={onClose}
        className={cn(
          "absolute top-4 right-4 z-10",
          "p-2 rounded-full",
          "bg-black/50 text-white/80",
          "hover:bg-black/70 hover:text-white",
          "transition-colors duration-150",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-white",
        )}
        aria-label="Close preview"
      >
        <XIcon className="w-6 h-6" />
      </button>

      {/* Image Container */}
      <div className="relative max-w-[90vw] max-h-[90vh]">
        {/* Loading Indicator */}
        {isLoading && !hasError && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          </div>
        )}

        {/* Error State */}
        {hasError && (
          <div className="flex flex-col items-center justify-center p-8 text-white/60">
            <ImageBrokenIcon className="w-16 h-16 mb-4" />
            <p className="text-sm">Failed to load image</p>
          </div>
        )}

        {/* Image */}
        {!hasError && (
          <img
            src={src}
            alt={alt}
            className={cn(
              "max-w-[90vw] max-h-[90vh] object-contain",
              "rounded-[var(--radius-md)]",
              "animate-[scaleIn_200ms_ease-out]",
              isLoading && "opacity-0",
            )}
            onLoad={handleImageLoad}
            onError={handleImageError}
          />
        )}
      </div>

      {/* Image Info */}
      {alt && !hasError && (
        <div
          className={cn(
            "absolute bottom-4 left-1/2 -translate-x-1/2",
            "px-4 py-2 rounded-full",
            "bg-black/50 text-white/80 text-sm",
            "max-w-[80vw] truncate",
          )}
        >
          {alt}
        </div>
      )}
    </div>
  );

  if (typeof document === "undefined") return null;

  return createPortal(lightboxContent, document.body);
}

ImageLightbox.displayName = "ImageLightbox";

// ============================================================================
// Size Configurations
// ============================================================================

const sizeStyles = {
  sm: "w-12 h-12",
  md: "w-20 h-20",
  lg: "w-32 h-32",
};

// ============================================================================
// ImagePreview Component
// ============================================================================

/**
 * Image preview thumbnail component with optional lightbox and remove button.
 *
 * Features:
 * - Thumbnail display with configurable size
 * - Click to open full-size lightbox
 * - Remove button for deletion
 * - Loading and error states
 * - Accessible with proper ARIA attributes
 *
 * @example
 * ```tsx
 * <ImagePreview
 *   src="/uploads/image.jpg"
 *   alt="Product image"
 *   enableLightbox
 *   onRemove={() => handleRemove()}
 *   size="md"
 * />
 * ```
 */
export const ImagePreview = forwardRef<HTMLDivElement, ImagePreviewProps>(
  (
    {
      src,
      alt = "Image preview",
      thumbnailSrc,
      enableLightbox = true,
      onRemove,
      removeDisabled = false,
      size = "md",
      bordered = true,
      className,
      ...props
    },
    ref,
  ) => {
    const [isLightboxOpen, setIsLightboxOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [hasError, setHasError] = useState(false);
    const [isHovered, setIsHovered] = useState(false);

    const displaySrc = thumbnailSrc || src;

    const handleImageLoad = useCallback(() => {
      setIsLoading(false);
    }, []);

    const handleImageError = useCallback(() => {
      setIsLoading(false);
      setHasError(true);
    }, []);

    const handleClick = useCallback(() => {
      if (enableLightbox && !hasError) {
        setIsLightboxOpen(true);
      }
    }, [enableLightbox, hasError]);

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent) => {
        if ((e.key === "Enter" || e.key === " ") && enableLightbox && !hasError) {
          e.preventDefault();
          setIsLightboxOpen(true);
        }
      },
      [enableLightbox, hasError],
    );

    const handleRemoveClick = useCallback(
      (e: React.MouseEvent) => {
        e.stopPropagation();
        onRemove?.();
      },
      [onRemove],
    );

    const closeLightbox = useCallback(() => {
      setIsLightboxOpen(false);
    }, []);

    return (
      <>
        <div
          ref={ref}
          className={cn(
            "relative inline-block rounded-[var(--radius-md)] overflow-hidden",
            bordered && "border border-[var(--color-border)]",
            "bg-[var(--color-card)]",
            sizeStyles[size],
            enableLightbox && !hasError && "cursor-pointer",
            className,
          )}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          onClick={handleClick}
          onKeyDown={handleKeyDown}
          tabIndex={enableLightbox && !hasError ? 0 : -1}
          role={enableLightbox && !hasError ? "button" : undefined}
          aria-label={enableLightbox && !hasError ? `View ${alt} full size` : undefined}
          {...props}
        >
          {/* Loading State */}
          {isLoading && !hasError && (
            <div className="absolute inset-0 flex items-center justify-center bg-[var(--color-card)]">
              <div className="w-5 h-5 border-2 border-[var(--color-muted)]/30 border-t-[var(--color-muted)] rounded-full animate-spin" />
            </div>
          )}

          {/* Error State */}
          {hasError && (
            <div className="absolute inset-0 flex items-center justify-center bg-[var(--color-card)]">
              <ImageBrokenIcon className="w-6 h-6 text-[var(--color-muted)]" />
            </div>
          )}

          {/* Image */}
          {!hasError && (
            <img
              src={displaySrc}
              alt={alt}
              className={cn(
                "w-full h-full object-cover",
                "transition-transform duration-200",
                isHovered && enableLightbox && "scale-105",
                isLoading && "opacity-0",
              )}
              onLoad={handleImageLoad}
              onError={handleImageError}
            />
          )}

          {/* Hover Overlay */}
          {enableLightbox && !hasError && isHovered && (
            <div
              className={cn(
                "absolute inset-0",
                "bg-black/40 flex items-center justify-center",
                "transition-opacity duration-150",
              )}
            >
              <ExpandIcon className="w-6 h-6 text-white" />
            </div>
          )}

          {/* Remove Button */}
          {onRemove && (
            <button
              type="button"
              onClick={handleRemoveClick}
              disabled={removeDisabled}
              className={cn(
                "absolute top-1 right-1",
                "p-1 rounded-full",
                "bg-[var(--color-error)] text-white",
                "opacity-0 transition-opacity duration-150",
                isHovered && "opacity-100",
                "hover:bg-[var(--color-error)]/80",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "focus:outline-none focus:opacity-100 focus-visible:ring-2 focus-visible:ring-white",
              )}
              aria-label={`Remove ${alt}`}
            >
              <TrashIcon className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Lightbox Modal */}
        <ImageLightbox
          isOpen={isLightboxOpen}
          onClose={closeLightbox}
          src={src}
          alt={alt}
        />
      </>
    );
  },
);

ImagePreview.displayName = "ImagePreview";

// ============================================================================
// ImagePreviewGrid Component
// ============================================================================

export interface ImagePreviewGridProps {
  /** Array of image sources */
  images: Array<{
    src: string;
    thumbnailSrc?: string;
    alt?: string;
    id?: string;
  }>;
  /** Callback when an image is removed */
  onRemove?: (index: number) => void;
  /** Whether remove buttons are disabled */
  removeDisabled?: boolean;
  /** Size of the thumbnails */
  size?: "sm" | "md" | "lg";
  /** Additional CSS classes */
  className?: string;
}

/**
 * Grid layout for multiple image previews.
 *
 * @example
 * ```tsx
 * <ImagePreviewGrid
 *   images={[
 *     { src: "/image1.jpg", alt: "Image 1" },
 *     { src: "/image2.jpg", alt: "Image 2" },
 *   ]}
 *   onRemove={(index) => handleRemove(index)}
 * />
 * ```
 */
export function ImagePreviewGrid({
  images,
  onRemove,
  removeDisabled = false,
  size = "md",
  className,
}: ImagePreviewGridProps) {
  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {images.map((image, index) => (
        <ImagePreview
          key={image.id || index}
          src={image.src}
          {...(image.thumbnailSrc ? { thumbnailSrc: image.thumbnailSrc } : {})}
          alt={image.alt || `Image ${index + 1}`}
          {...(onRemove ? { onRemove: () => onRemove(index) } : {})}
          removeDisabled={removeDisabled}
          size={size}
          enableLightbox
        />
      ))}
    </div>
  );
}

ImagePreviewGrid.displayName = "ImagePreviewGrid";
