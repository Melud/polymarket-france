export const SOURCE_LABELS: Record<string, string> = {
  polymarket: "Polymarket",
  kalshi: "Kalshi",
};

export function sourceLabel(source: string | undefined): string {
  return SOURCE_LABELS[source ?? "polymarket"] ?? "Polymarket";
}
