'use client';

import {
  forwardRef,
  useEffect,
  useCallback,
  type HTMLAttributes,
  type ReactNode,
  type MouseEvent,
} from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/utils';

export interface ModalProps extends HTMLAttributes<HTMLDivElement> {
  isOpen: boolean;
  onClose: () => void;
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
  children?: ReactNode;
}

export const Modal = forwardRef<HTMLDivElement, ModalProps>(
  (
    {
      isOpen,
      onClose,
      closeOnOverlayClick = true,
      closeOnEscape = true,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const handleEscape = useCallback(
      (e: KeyboardEvent) => {
        if (closeOnEscape && e.key === 'Escape') {
          onClose();
        }
      },
      [closeOnEscape, onClose]
    );

    const handleOverlayClick = (e: MouseEvent<HTMLDivElement>) => {
      if (closeOnOverlayClick && e.target === e.currentTarget) {
        onClose();
      }
    };

    useEffect(() => {
      if (isOpen) {
        document.addEventListener('keydown', handleEscape);
        document.body.style.overflow = 'hidden';
      }

      return () => {
        document.removeEventListener('keydown', handleEscape);
        document.body.style.overflow = '';
      };
    }, [isOpen, handleEscape]);

    if (!isOpen) return null;

    const modalContent = (
      <div
        className={cn(
          'fixed inset-0 z-50',
          'flex items-center justify-center p-4',
          'animate-[fadeIn_150ms_ease-out]'
        )}
        onClick={handleOverlayClick}
        role="dialog"
        aria-modal="true"
      >
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm"
          aria-hidden="true"
        />
        <div
          ref={ref}
          className={cn(
            'relative z-10 w-full max-w-lg',
            'bg-[var(--color-card)] rounded-[var(--radius-lg)]',
            'border border-[var(--color-border)]',
            'shadow-2xl shadow-black/40',
            'animate-[scaleIn_150ms_ease-out]',
            className
          )}
          {...props}
        >
          {children}
        </div>
      </div>
    );

    if (typeof document === 'undefined') return null;

    return createPortal(modalContent, document.body);
  }
);

Modal.displayName = 'Modal';

export interface ModalHeaderProps extends HTMLAttributes<HTMLDivElement> {
  onClose?: () => void;
  children?: ReactNode;
}

export const ModalHeader = forwardRef<HTMLDivElement, ModalHeaderProps>(
  ({ onClose, className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'flex items-center justify-between',
          'px-6 py-4',
          'border-b border-[var(--color-border)]',
          className
        )}
        {...props}
      >
        <h2 className="text-lg font-semibold text-[var(--color-foreground)]">
          {children}
        </h2>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className={cn(
              'p-1 rounded-[var(--radius-md)]',
              'text-[var(--color-muted)] hover:text-[var(--color-foreground)]',
              'hover:bg-[var(--color-card-hover)]',
              'transition-colors duration-150',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]'
            )}
            aria-label="Close modal"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    );
  }
);

ModalHeader.displayName = 'ModalHeader';

export interface ModalBodyProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

export const ModalBody = forwardRef<HTMLDivElement, ModalBodyProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('px-6 py-4', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

ModalBody.displayName = 'ModalBody';

export interface ModalFooterProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

export const ModalFooter = forwardRef<HTMLDivElement, ModalFooterProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'flex items-center justify-end gap-3',
          'px-6 py-4',
          'border-t border-[var(--color-border)]',
          'bg-[var(--color-background)]/50',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

ModalFooter.displayName = 'ModalFooter';
