# Limitaciones conocidas

- El selector anual ofrece 2023 porque es el único IPR compuesto validado.
- La evolución previa a 2023 corresponde a capas normalizadas; no se presenta
  como una serie histórica completa del IPR.
- La brecha prospectiva compara IPR-5 e IPR-4 sobre el mismo corte 2023. No es
  una evolución temporal ni una predicción puntual de subida o bajada.
- Cádiz, San Fernando y Getxo permanecen sin contraste porque no se imputa el
  riesgo futuro; nunca se representan como brecha cero.
- Los promedios de provincia, CCAA y España son referencias descriptivas del
  universo de 306 municipios, no índices territoriales oficiales.
- El histórico turístico usa el último corte disponible de cada año.
- El contexto territorial procede de OpenFreeMap y requiere conexión. Si no
  responde, la coropleta municipal sigue disponible sobre un fondo local y la
  interfaz muestra el aviso correspondiente.
- deck.gl, extrusión 3D y teselas vectoriales quedan pospuestos: no aportan
  rendimiento relevante para 306 polígonos.
- MongoDB no se incluye porque todavía no existe un módulo NLP integrado.
- En un despliegue remoto debe configurarse `NEXT_PUBLIC_API_URL` con la URL
  pública de FastAPI o añadir un reverse proxy same-origin.
- `npm audit --omit=dev` no detecta vulnerabilidades en producción. La
  auditoría completa informa de avisos transitivos en las herramientas de
  desarrollo de `eslint-config-next`; no llegan al bundle ni al contenedor de
  ejecución y actualizar ESLint fuera del rango compatible rompe actualmente
  el plugin oficial de Next.js.

- El DQS evalúa solo la cobertura y actualidad de las cuatro capas observadas.
  La consistencia municipal no es evaluable y la proyección IPR-5 no tiene DQS
  propio. En 2023 todos obtienen 99,0625: estas métricas no capturan todos los
  posibles errores o sesgos. Véase [metodología DQS](DATA_QUALITY_SCORE.md).
