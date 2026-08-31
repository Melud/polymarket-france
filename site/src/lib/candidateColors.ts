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

  // Primaire du Parti socialiste : tous ces candidats sont du même parti,
  // donc logiquement une seule couleur — mais ils s'affrontent entre eux
  // dans ce marché précis, il faut donc pouvoir les distinguer. Palette
  // catégorielle arbitraire (pas de nuance Wikipédia dédiée par candidat),
  // choisie pour ne pas entrer en collision avec les couleurs de parti
  // utilisées ailleurs sur le site.
  "Olivier Faure": "#2E8B57", // vert
  "Philippe Brun": "#8E44AD", // violet
  "Ségolène Royal": "#E67E22", // orange
  "Karim Bouamrane": "#16A085", // turquoise
  "Boris Vallaud": "#6D4C41", // marron
  "Jérôme Guedj": "#B7950B", // ocre
  "Bernard Cazeneuve": "#34495E", // ardoise
  "Carole Delga": "#9B59B6", // mauve
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

const NORMALIZED_COLORS: Record<string, string> = Object.fromEntries(
  Object.entries(CANDIDATE_COLORS).map(([name, color]) => [normalizeName(name), color])
);

export function candidateColor(name: string): string {
  return NORMALIZED_COLORS[normalizeName(name)] ?? FALLBACK_COLOR;
}
