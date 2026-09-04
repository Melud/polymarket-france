// Deux plateformes peuvent suivre la même question (ex. "Prochaine élection
// présidentielle française" sur Polymarket ET Kalshi) — un marché Kalshi porte
// alors un champ "pairs_with" pointant vers le slug Polymarket équivalent.
// On regroupe ces paires en une seule carte (un slider bascule entre les deux
// jeux de données côté site) plutôt que d'afficher deux cartes séparées.
export interface SourceEntry {
  slug: string;
  market: any;
}

export interface MarketCardGroup {
  slug: string; // slug "canonique" du groupe (celui de la carte, du lien copié...)
  sources: Record<string, SourceEntry>;
}

export function groupMarkets(markets: Record<string, any>): MarketCardGroup[] {
  const entries = Object.entries(markets);

  // un pairs_with qui pointe vers un slug absent (marché retiré, faute de
  // frappe...) est ignoré : le marché reste affiché seul plutôt que de disparaître
  const childOf = new Map<string, string>();
  for (const [slug, m] of entries) {
    if (m.pairs_with && markets[m.pairs_with]) {
      childOf.set(slug, m.pairs_with);
    }
  }

  const groups = new Map<string, MarketCardGroup>();
  for (const [slug, m] of entries) {
    if (childOf.has(slug)) continue;
    groups.set(slug, { slug, sources: { [m.source ?? "polymarket"]: { slug, market: m } } });
  }
  for (const [slug, m] of entries) {
    const primarySlug = childOf.get(slug);
    if (primarySlug && groups.has(primarySlug)) {
      groups.get(primarySlug)!.sources[m.source ?? "kalshi"] = { slug, market: m };
    }
  }

  return [...groups.values()];
}

// pour une page dédiée à un slug précis (ex. /marche/kalshi-.../), retrouve le
// groupe fusionné auquel il appartient ainsi que la clé de source à activer
// par défaut (pour que le contenu visible corresponde à l'aperçu de lien de
// CE slug précis, même si la carte affiche ensuite les deux sources).
export function findGroupForSlug(
  groups: MarketCardGroup[],
  slug: string
): { group: MarketCardGroup; initialSource: string } | null {
  for (const group of groups) {
    for (const [source, entry] of Object.entries(group.sources)) {
      if (entry.slug === slug) {
        return { group, initialSource: source };
      }
    }
  }
  return null;
}
