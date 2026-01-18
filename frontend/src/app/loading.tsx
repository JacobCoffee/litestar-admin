export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-primary" />
        <p className="text-sm text-muted">Loading...</p>
      </div>
    </div>
  );
}
