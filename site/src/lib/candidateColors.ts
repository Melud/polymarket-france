// Couleurs alignées sur les nuances politiques utilisées par Wikipédia
// (Modèle:Infobox Parti politique français/couleurs), en éclaircissant les
// bleus (RN/LR/Horizons) : les codes d'origine (#0D378A, #0066CC, #0001B8)
// étaient trop proches du noir pour rester lisibles sur le fond sombre du
// site — on garde la teinte de chaque parti mais dans une version plus
// claire, distincte les unes des autres. Deux candidats du même parti
// partagent donc la même couleur (ex. Bardella/Le Pen en RN, Retailleau/
// Lisnard en LR).
const CANDIDATE_COLORS: Record<string, string> = {
  "Jordan Bardella": "#3B5FC4", // RN (bleu marine éclairci)
  "Marine Le Pen": "#3B5FC4", // RN
  "Bruno Retailleau": "#2E9CFF", // LR (bleu ciel)
  "David Lisnard": "#2E9CFF", // LR
  "Édouard Philippe": "#6C63FF", // Horizons (bleu-violet)
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
