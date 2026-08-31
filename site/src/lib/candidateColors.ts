// Couleurs alignées sur les nuances politiques utilisées par Wikipédia
// (Modèle:Infobox Parti politique français/couleurs) plutôt que sur des
// teintes arbitraires, pour rester cohérent avec les graphiques électoraux
// habituels. Deux candidats du même parti partagent donc la même couleur
// (ex. Bardella/Le Pen en RN, Retailleau/Lisnard en LR).
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

const FALLBACK_COLOR = "#4f8cff";

export function candidateColor(name: string): string {
  return CANDIDATE_COLORS[name] ?? FALLBACK_COLOR;
}
