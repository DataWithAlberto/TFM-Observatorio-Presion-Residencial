/**
 * Paleta de los gráficos de ECharts.
 *
 * ECharts pinta sobre un lienzo y no resuelve `var(--…)`, así que los colores
 * se leen de `tokens.css` en tiempo de ejecución en lugar de repetirse aquí.
 * Durante el render en servidor no hay documento del que leer, pero tampoco
 * hay lienzo: el gráfico solo se dibuja tras montarse en el navegador.
 */
function token(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export type ChartTokens = {
  ink: string;
  ink2: string;
  paper: string;
  muted: string;
  rule: string;
  accent: string;
  series: string[];
  divergent: string[];
  missing: string;
  font: string;
  mono: string;
};

export function chartTokens(): ChartTokens {
  return {
    ink: token("--color-ink"),
    ink2: token("--color-ink-2"),
    paper: token("--color-paper"),
    muted: token("--color-muted"),
    rule: token("--color-rule"),
    accent: token("--color-accent"),
    series: [
      token("--data-series-1"),
      token("--data-series-2"),
      token("--data-series-3"),
      token("--data-series-4"),
      token("--data-series-5"),
    ],
    divergent: [
      token("--data-div-1"),
      token("--data-div-2"),
      token("--data-div-3"),
      token("--data-div-4"),
      token("--data-div-5"),
    ],
    missing: token("--color-map-missing"),
    font: token("--font-display"),
    mono: token("--font-mono"),
  };
}
