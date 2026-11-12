export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function computeCooloffMetrics(startedAt: string, cooloffDays: number) {
  const startMs = new Date(startedAt).getTime();
  const totalMs = cooloffDays * 86_400_000;
  const elapsedMs = Math.max(0, Date.now() - startMs);
  const remainingMs = Math.max(0, startMs + totalMs - Date.now());

  const elapsedDays = Math.min(
    cooloffDays,
    Math.floor(elapsedMs / 86_400_000),
  );
  const remainingDays = Math.max(0, Math.ceil(remainingMs / 86_400_000));

  return {
    elapsedDays,
    remainingDays,
    progressPercent: Math.min(100, Math.round((elapsedMs / totalMs) * 100)),
  };
}

