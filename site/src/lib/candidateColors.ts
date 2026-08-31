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
