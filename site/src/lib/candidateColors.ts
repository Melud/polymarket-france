// Couleurs alignées sur les nuances politiques utilisées par Wikipédia
// (Modèle:Infobox Parti politique français/couleurs) plutôt que sur des
// teintes arbitraires, pour rester cohérent avec les graphiques électoraux
// habituels. Deux candidats du même parti partagent donc la même couleur
// (ex. Bardella/Le Pen en RN, Retailleau/Lisnard en LR). Le fond du site est
// clair précisément pour que ces bleus foncés (RN/LR/Horizons) restent
// lisibles sans avoir à les modifier.
const CANDIDATE_COLORS: Record<string, string> = {
  "Jordan Bardella": "#0D378A", // RN
  "Marine Le Pen": "#0D378A", // RN
  "Bruno Retailleau": "#0066CC", // LR
  "David Lisnard": "#0066CC", // LR
  "Édouard Philippe": "#0001B8", // Horizons
  "Gabriel Attal": "#FFEB00", // Renaissance
  "Jean-Luc Mélenchon": "#CC2443", // LFI
  "Raphaël Glucksmann": "#FFC0C0", // Place Publique
  "François Hollande": "#FF8080", // PS
  "Dominique de Villepin": "#999999", // sans étiquette
};

// Palettes propres à un marché précis, complètement indépendantes de
// CANDIDATE_COLORS : utile quand un marché oppose des candidats du même
// parti entre eux (la convention "couleur = nuance politique" n'a alors
// aucun sens) — la même personne peut donc avoir une couleur différente
// ici et dans les autres marchés, volontairement.
const MARKET_PALETTES: Record<string, Record<string, string>> = {
  "socialist-party-of-france-presidential-nominee-20260710182042067": {
    "Raphaël Glucksmann": "#D6482B", // vermillon
    "Olivier Faure": "#2E8B57", // vert
    "Philippe Brun": "#8E44AD", // violet
    "Ségolène Royal": "#E8A33D", // ambre
    "François Hollande": "#1F6F8B", // bleu pétrole
    "Boris Vallaud": "#6D4C41", // marron
    "Jérôme Guedj": "#B7950B", // ocre
    "Karim Bouamrane": "#16A085", // turquoise
    "Carole Delga": "#C2185B", // framboise
    "Bernard Cazeneuve": "#495057", // ardoise
  },
};

// Même gris neutre que "sans étiquette" : plutôt qu'une couleur arbitraire,
// on assume qu'un candidat non mappé n'a pas (encore) de nuance connue.
const FALLBACK_COLOR = "#999999";

// RN/LR/Horizons sont trois bleus assez proches (fidèles aux nuances
// Wikipédia, gardées telles quelles) — sur un graphique en courbes où
// plusieurs se retrouvent ensemble, la couleur seule ne suffit pas à les
// distinguer. On ajoute un motif de trait (plein/tirets/pointillés) en plus
// de la couleur, uniquement pour ces cas-là. Format Chart.js `borderDash`.
const CANDIDATE_DASH: Record<string, number[]> = {
  "Bruno Retailleau": [6, 4], // LR — tirets
  "David Lisnard": [6, 4], // LR — tirets
  "Édouard Philippe": [2, 3], // Horizons — pointillés
};
const SOLID: number[] = [];

// Selon les marchés Polymarket, un même candidat peut être orthographié avec
// ou sans accents (ex. "Raphaël"/"Raphael" Glucksmann, "François"/"Francois"
// Hollande) — on compare donc les noms sans diacritiques. `\p{Diacritic}`
// (propriété Unicode, syntaxe ASCII pure) plutôt qu'une plage de caractères
// combinants littéraux, pour rester correct quel que soit l'encodage utilisé
// pour lire ce fichier.
function normalizeName(name: string): string {
  return name.normalize("NFD").replace(/\p{Diacritic}/gu, "");
}

function normalizeMap(map: Record<string, string>): Record<string, string> {
  return Object.fromEntries(Object.entries(map).map(([name, color]) => [normalizeName(name), color]));
}

const NORMALIZED_COLORS = normalizeMap(CANDIDATE_COLORS);
const NORMALIZED_MARKET_PALETTES: Record<string, Record<string, string>> = Object.fromEntries(
  Object.entries(MARKET_PALETTES).map(([slug, map]) => [slug, normalizeMap(map)])
);
const NORMALIZED_DASH: Record<string, number[]> = Object.fromEntries(
  Object.entries(CANDIDATE_DASH).map(([name, dash]) => [normalizeName(name), dash])
);

export function candidateColor(name: string, marketSlug?: string): string {
  const normalized = normalizeName(name);
  const palette = marketSlug ? NORMALIZED_MARKET_PALETTES[marketSlug] : undefined;
  if (palette) {
    return palette[normalized] ?? FALLBACK_COLOR;
  }
  return NORMALIZED_COLORS[normalized] ?? FALLBACK_COLOR;
}

// Motif de trait pour le graphique (indépendant du marché : seules les
// couleurs de parti globales sont assez proches pour en avoir besoin, les
// palettes propres à un marché — ex. la primaire PS — sont déjà distinctes).
export function candidateLineDash(name: string): number[] {
  return NORMALIZED_DASH[normalizeName(name)] ?? SOLID;
}
