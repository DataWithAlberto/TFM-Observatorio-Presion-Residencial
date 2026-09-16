# Contraste prospectivo 2023

## Objetivo

El módulo `/prospectiva` hace visible la diferencia entre los dos productos
validados del observatorio:

- IPR-4 observado: cuatro capas, con sus pesos renormalizados.
- IPR-5 prospectivo: las mismas cuatro capas más un 15 % de riesgo futuro.

Ambos productos comparten el corte base 2023. La brecha no es una serie
temporal ni una predicción de cambio municipal.

## Identidad de composición

La renormalización del IPR-4 permite escribir:

`IPR-5 = 0,85 × IPR-4 + 0,15 × Riesgo futuro`

Por tanto:

`Brecha = IPR-5 − IPR-4 = 0,15 × (Riesgo futuro − IPR-4)`

La plataforma calcula la brecha únicamente a partir de los resultados
canónicos ya validados. No modifica pesos, puntuaciones ni scripts analíticos.

## Universo y ausencias

- Universo mostrado: 306 municipios.
- Contrastes calculables: 303.
- Sin contraste: Cádiz, San Fernando y Getxo.

Los tres valores ausentes se conservan como nulos porque no existe IPR-5
validado para esos municipios. No se imputan ni se convierten en cero.

## Representación

- Escala cartográfica divergente fija: −15, 0, +15.
- Azul: IPR-5 menor que IPR-4.
- Neutro: igualdad entre composiciones.
- Rojo: IPR-5 mayor que IPR-4.
- Gris: sin contraste.

El mapa, la dispersión, la tabla y el CSV consumen el mismo contrato
`api_contraste_prospectivo`.

## API

`GET /api/v1/prospectiva`

Filtros disponibles:

- `ccaa`
- `provincia`
- `search`
- `min_brecha`
- `max_brecha`
- `formato=json|csv`

Los filtros de brecha mantienen visibles los nulos para que la ausencia de
IPR-5 siga siendo explícita.
