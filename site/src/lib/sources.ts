export const SOURCE_LABELS: Record<string, string> = {
  polymarket: "Polymarket",
  kalshi: "Kalshi",
  manifold: "Manifold",
};

export function sourceLabel(source: string | undefined): string {
  return SOURCE_LABELS[source ?? "polymarket"] ?? "Polymarket";
}
