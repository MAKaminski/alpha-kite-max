interface EmptyProps {
  message: string;
  hint?: string;
}

export function Empty({ message, hint }: EmptyProps) {
  return (
    <div className="rounded-md border border-dashed border-[var(--border)] px-4 py-12 text-center">
      <div className="text-sm font-medium">{message}</div>
      {hint ? (
        <div className="mt-1 text-xs text-[var(--muted)]">{hint}</div>
      ) : null}
    </div>
  );
}
