// Lissage exponentiel simple : s(t) = α·y(t) + (1-α)·s(t-1), s(0) = y(0).
// Un trou (null, candidat pas encore dans le marché ce jour-là) ne fait pas
// avancer l'état — on reporte simplement la dernière valeur lissée connue.
export function ema(values: (number | null)[], alpha: number): (number | null)[] {
  const out: (number | null)[] = [];
  let s: number | null = null;
  for (const v of values) {
    if (v == null) {
      out.push(s);
      continue;
    }
    s = s == null ? v : alpha * v + (1 - alpha) * s;
    out.push(s);
  }
  return out;
}
