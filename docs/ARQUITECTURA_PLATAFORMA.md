# Arquitectura de la plataforma

La migración es incremental: los scripts `00`–`19`, sus SQL y las tablas
analíticas siguen siendo canónicos y no se mueven.

`Next.js → FastAPI → vistas api_* → tablas analíticas → PostGIS`

- MapLibre carga una geometría simplificada una vez y recibe valores separados.
  OpenFreeMap aporta el contexto vectorial abierto sobre datos OpenStreetMap;
  los municipios se dibujan debajo de sus etiquetas.
- ECharts 6 se usa para evolución y comparaciones por su integración React.
- FastAPI aplica Router → Servicio → Repositorio.
- Las vistas de `database/serving` son el contrato de consumo.
- TanStack Query separa estado remoto y caché; los filtros viven en la URL.
- Los valores ausentes conservan estado `sin dato` y nunca se convierten en 0.

## Contrato científico

- IPR-4 observado: 306 municipios, corte 2023.
- IPR-5 prospectivo: 303 municipios, corte base 2023.
- Riesgo futuro: proyección, no observación histórica.
- No existe todavía una serie temporal del IPR.

## Núcleo 2D validado

- filtros por indicador, producto, CCAA, provincia, score y municipio;
- MapLibre con tooltip, leyenda, selección, zoom, geometría cacheada y vistas
  Península, Canarias y España completa;
- contraste prospectivo IPR-5 − IPR-4 con escala divergente fija, 303 casos
  comparables, tres nulos explícitos, dispersión y CSV;
- ranking filtrable y exportable;
- ficha con pesos correctos por producto, históricos y comparativas;
- comparador de dos a cuatro municipios;
- páginas de metodología, calidad y fuentes;
- tests pytest, ESLint, TypeScript, build y Playwright.

El contraste usa la vista derivada `api_contraste_prospectivo`; no recalcula ni
duplica el índice canónico. deck.gl, 3D, teselas vectoriales, CI/CD y
observabilidad ampliada siguen siendo extensiones opcionales.
