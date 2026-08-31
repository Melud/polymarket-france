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
  "Olivier Faure": "#FF8080", // PS
  "Nathalie Arthaud": "#BB0000", // LO
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

export function candidateColor(name: string, marketSlug?: string): string {
  const normalized = normalizeName(name);
  const palette = marketSlug ? NORMALIZED_MARKET_PALETTES[marketSlug] : undefined;
  if (palette) {
    return palette[normalized] ?? FALLBACK_COLOR;
  }
  return NORMALIZED_COLORS[normalized] ?? FALLBACK_COLOR;
}

// Certains marchés (ex. "Macron out by...?") ont des outcomes qui sont des
// échéances ("December 31, 2026", "October 31") plutôt que des noms de
// candidats — les initiales mot-par-mot donnaient le même résultat pour deux
// dates différentes (ex. "December 31, 2026" et "December 31, 2025" →
// toutes les deux "D32"). On les détecte pour reformater en JJ/MM/AA, comme
// les dates de l'axe du graphique, plutôt que de risquer une autre collision
// avec une abréviation par mot.
const MONTHS = [
  "january", "february", "march", "april", "may", "june",
  "july", "august", "september", "october", "november", "december",
];
const DATE_LABEL = /^([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})?$/;

// Un outcome est une échéance (pas un candidat) si son nom correspond au
// format "Mois JJ[, AAAA]" utilisé par ces marchés.
export function isDateLabel(name: string): boolean {
  const m = name.match(DATE_LABEL);
  return !!m && MONTHS.includes(m[1].toLowerCase());
}

// Initiale de chaque mot du nom (espaces et traits d'union), ex.
// "Jean-Luc Mélenchon" -> "JLM", "Marine Le Pen" -> "MLP". Utilisé pour les
// étiquettes de courbe (plus lisibles en gros que le nom complet) et en
// rappel entre parenthèses dans la légende.
export function candidateInitials(name: string): string {
  const dateMatch = name.match(DATE_LABEL);
  if (dateMatch) {
    const monthIndex = MONTHS.indexOf(dateMatch[1].toLowerCase());
    if (monthIndex !== -1) {
      const day = dateMatch[2].padStart(2, "0");
      const month = String(monthIndex + 1).padStart(2, "0");
      const year = dateMatch[3] ? `/${dateMatch[3].slice(2)}` : "";
      return `${day}/${month}${year}`;
    }
  }
  return name
    .split(/[\s-]+/)
    .filter(Boolean)
    .map((word) => word[0].toUpperCase())
    .join("");
}
