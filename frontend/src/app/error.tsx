'use client';

interface ErrorProps {
  readonly error: Error & { digest?: string };
  readonly reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-error">Error</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">
          Something went wrong
        </h2>
        <p className="mt-2 text-muted">
          {error.message || 'An unexpected error occurred.'}
        </p>
        <button
          onClick={reset}
          type="button"
          className="mt-6 inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}
