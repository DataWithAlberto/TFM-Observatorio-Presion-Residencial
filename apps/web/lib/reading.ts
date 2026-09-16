import type { IndexRow } from "@/lib/api";

import { placeName } from "@/lib/format";

/**
 * Frase de lectura del explorador, calculada con las filas visibles y sin
 * interpretarlas: o cuenta cuántas hay, o dice dónde se concentran las diez
 * primeras. No hay adjetivos ni juicios, solo el recuento.
 */
export function readingFor(items: IndexRow[], ccaa: string, layer: string): string {
  if (items.length === 0) return "Ningún municipio cumple los filtros.";
  if (items.length < 10) {
    const verb = items.length === 1 ? "municipio cumple" : "municipios cumplen";
    return `${items.length} ${verb} los filtros.`;
  }

  const top = items.slice(0, 10);
  const counts = new Map<string, number>();
  top.forEach((row) => {
    const key = (ccaa ? row.provincia : row.comunidad_autonoma) ?? "";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });

  const [place, count] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
  const what =
    layer === "ipr"
      ? "con más presión"
      : layer === "calidad"
        ? "con mayor calidad del dato"
        : "con valores más altos";

  if (count < 2) {
    const scope = ccaa ? "provincias" : "comunidades";
    return `Los 10 municipios ${what} se reparten entre ${counts.size} ${scope}.`;
  }

  const where = ccaa ? `la provincia de ${placeName(place)}` : place;
  return `${count} de los 10 municipios ${what} están en ${where}.`;
}
