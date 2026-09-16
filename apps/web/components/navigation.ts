export type NavigationItem = {
  href: string;
  label: string;
  /** Rótulo más corto para la cabecera; la paleta usa siempre `label`. */
  short?: string;
  description: string;
  keywords: string;
};

/**
 * Las vistas de la aplicación, en el orden de la cabecera: primero lo que se
 * explora, después los análisis que acompañan al índice, y al final cómo se
 * calcula y de dónde salen los datos.
 */
export const NAVIGATION_ITEMS: NavigationItem[] = [
  {
    href: "/observatorio",
    label: "Mapa",
    description: "Filtra el territorio y selecciona un municipio.",
    keywords: "mapa explorar filtros territorio vivienda observatorio",
  },
  {
    href: "/ranking",
    label: "Relación",
    description: "Consulta, ordena y descarga la lista municipal.",
    keywords: "relación ranking lista municipios ordenar descargar tabla",
  },
  {
    href: "/prospectiva",
    label: "Riesgo futuro",
    description: "Compara la situación actual con el escenario futuro.",
    keywords: "prospectiva riesgo futuro clima comparación",
  },
  {
    href: "/comparar",
    label: "Comparar",
    description: "Contrasta entre dos y cuatro municipios.",
    keywords: "comparar comparación factores municipios",
  },
  {
    href: "/espacial",
    label: "Patrones espaciales",
    short: "Espacial",
    description: "Moran, LISA y la asociación entre municipios vecinos.",
    keywords: "espacial moran lisa clusters vecinos territorio",
  },
  {
    href: "/validacion-externa",
    label: "Validación externa",
    short: "Validación",
    description: "El índice frente al alquiler declarado, una variable ajena.",
    keywords: "validación externa alquiler correlación spearman contraste",
  },
  {
    href: "/analisis-ml",
    label: "Análisis ML",
    short: "ML",
    description: "Hasta dónde un modelo no lineal reconstruye el índice.",
    keywords: "machine learning xgboost shap exploratorio modelo",
  },
  {
    href: "/metodologia",
    label: "Cómo se calcula",
    description: "Revisa los factores y la fórmula de la puntuación.",
    keywords: "metodología cálculo fórmula factores índice",
  },
  {
    href: "/calidad",
    label: "Datos y fuentes",
    description: "Comprueba la procedencia, cobertura y calidad de los datos.",
    keywords: "calidad datos fuentes cobertura límites dqs",
  },
];
