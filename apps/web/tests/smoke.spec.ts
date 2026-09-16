import { expect, test } from "@playwright/test";

test("observatorio carga datos reales y persiste filtros", async ({ page }) => {
  await page.goto("/observatorio");
  await expect(
    page.getByRole("heading", { name: "Presión residencial total" }),
  ).toBeVisible();
  await expect(page.getByText("306 de 306", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Filtros" }).click();
  await page
    .getByRole("combobox", { name: "Comunidad autónoma" })
    .selectOption({ label: "Principado de Asturias" });
  await expect(page).toHaveURL(/ccaa=Principado(\+|%20)de(\+|%20)Asturias/);
  await expect(
    page.getByText("6 municipios cumplen los filtros.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("6 de 306", { exact: true })).toBeVisible();

  await page.getByRole("radio", { name: "Viviendas turísticas" }).click();
  await expect(page).toHaveURL(/capa=turismo/);
  await expect(
    page.getByRole("heading", {
      name: "Presión de las viviendas turísticas",
    }),
  ).toBeVisible();
});

test("la frase de lectura se calcula con los municipios visibles", async ({
  page,
}) => {
  await page.goto("/observatorio?ccaa=Principado+de+Asturias");
  await expect(
    page.getByText("6 municipios cumplen los filtros.", { exact: true }),
  ).toBeVisible();
});

test("la columna lateral muestra o los diez primeros o el municipio", async ({
  page,
}) => {
  await page.goto("/observatorio");
  const side = page.getByRole("complementary", { name: "Primeros puestos" });
  await expect(
    side.getByRole("heading", { name: "Los diez con más presión" }),
  ).toBeVisible();

  await page.goto("/observatorio?municipio=29067");
  const panel = page.getByRole("complementary", {
    name: "Municipio seleccionado",
  });
  await expect(panel.getByRole("heading", { name: "Málaga" })).toBeVisible();
  await expect(panel.getByText("90,4", { exact: true })).toBeVisible();
  await expect(panel.getByText(/Supera al 99 %/)).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Los diez con más presión" }),
  ).toBeHidden();
});

test("las fichas de filtro activo se quitan desde el titular", async ({
  page,
}) => {
  await page.goto("/observatorio?ccaa=Principado+de+Asturias");
  const chips = page.getByRole("list", { name: "Filtros activos" });
  const chip = chips.getByRole("button", {
    name: "Quitar Principado de Asturias",
  });
  await expect(chip).toBeVisible();

  await chip.click();
  await expect(page).not.toHaveURL(/ccaa=/);
  await expect(chips).toBeHidden();
});

test("mapa carga contexto cartográfico y controles de encuadre", async ({
  page,
}) => {
  await page.goto("/observatorio");

  const map = page.getByRole("region", {
    name: "Mapa interactivo de presión sobre la vivienda",
  });
  await expect(map).toBeVisible();
  await expect(map.locator("canvas.maplibregl-canvas")).toBeVisible();

  const mapBox = await map.boundingBox();
  expect(mapBox?.width).toBeGreaterThan(600);
  expect(mapBox?.height).toBeGreaterThan(450);
  const viewport = page.viewportSize();
  expect(mapBox?.y).toBeLessThan((viewport?.height ?? 900) * 0.7);
  const visibleMapHeight =
    Math.min(
      (mapBox?.y ?? 0) + (mapBox?.height ?? 0),
      viewport?.height ?? 900,
    ) - Math.max(mapBox?.y ?? 0, 0);
  expect(visibleMapHeight).toBeGreaterThan(250);

  await expect(page.locator(".maplibregl-ctrl-attrib-inner")).toContainText(
    /OpenStreetMap|OpenMapTiles|OpenFreeMap/i,
  );

  const territorialView = page.getByRole("group", {
    name: "Vista territorial del mapa",
  });
  await expect(territorialView).toBeVisible();
  await expect(
    territorialView.getByRole("button", { name: "Península" }),
  ).toBeVisible();
  await expect(
    territorialView.getByRole("button", { name: "Canarias" }),
  ).toBeVisible();
  await expect(
    territorialView.getByRole("button", { name: "España completa" }),
  ).toBeVisible();
});

test("el mapa ofrece selección equivalente por teclado", async ({ page }) => {
  await page.goto("/observatorio");

  const picker = page.locator(".map-keyboard-picker");
  await picker.getByText(/Elegir municipio en lista/).click();
  await picker.getByRole("button", { name: /^Madrid/ }).click();

  await expect(page).toHaveURL(/municipio=28079/);
});

test("la navegación rápida filtra, cierra y abre una vista", async ({
  page,
}) => {
  await page.goto("/observatorio");

  await page.keyboard.press("Control+K");
  const dialog = page.getByRole("dialog", { name: "Ir a una vista" });
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();

  await page
    .getByRole("button", { name: "Abrir navegación rápida" })
    .click();
  await dialog
    .getByRole("combobox", { name: "Buscar una vista" })
    .fill("fuentes");
  await expect(
    dialog.getByRole("option", { name: /Datos y fuentes/ }),
  ).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/calidad$/);
});

test("ficha observada usa cuatro capas y comparativas", async ({ page }) => {
  await page.goto("/municipio/28079?producto=observado");
  await expect(page.getByRole("heading", { name: "Madrid" })).toBeVisible();

  // La cobertura de factores vive ahora en el cajetín completo.
  await expect(page.getByText("Factores con dato", { exact: true })).toBeVisible();
  await expect(page.getByText("4 de 4", { exact: true })).toBeVisible();

  await expect(
    page.getByRole("heading", { name: "Situación frente al entorno" }),
  ).toBeVisible();
  await expect(page.getByText("España (306 municipios)")).toBeVisible();
});

test("ranking y comparador cargan productos coherentes", async ({ page }) => {
  await page.goto("/ranking?capa=ipr&producto=observado");
  await expect(
    page.getByRole("heading", { name: "Relación de municipios" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Descargar tabla (.csv)" }),
  ).toBeVisible();

  await page.goto(
    "/comparar?producto=observado&municipio=28079&municipio=08019",
  );
  await expect(page.getByRole("heading", { name: "Madrid" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Barcelona" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Comparación por factores" }),
  ).toBeVisible();
});

test("la comparación con riesgo futuro explica sus límites y conserva los nulos", async ({
  page,
}) => {
  await page.goto("/prospectiva");
  await expect(
    page.getByRole("heading", {
      name: "Cómo cambia el resultado al añadir el riesgo futuro",
    }),
  ).toBeVisible();
  await expect(
    page.getByText("No dice cómo será el municipio en el futuro."),
  ).toBeVisible();
  await expect(
    page.getByText("303 con ambas puntuaciones · 3 sin datos suficientes"),
  ).toBeVisible();
  await expect(
    page.getByRole("region", {
      name: "Mapa interactivo de presión sobre la vivienda",
    }),
  ).toBeVisible();

  const search = page.getByRole("searchbox", { name: "Buscar municipio" });
  await search.fill("Madrid");
  await expect(page).toHaveURL(/buscar=Madrid/);

  // La tabla vive en su propia pestaña: el mapa y la relación ya no se apilan.
  await page.getByRole("radio", { name: "Tabla" }).click();
  const table = page.getByRole("table");
  await table.getByRole("button", { name: "Seleccionar Madrid" }).click();
  await expect(page).toHaveURL(/municipio=28079/);

  const selected = page.locator(".contrast-selected");
  await expect(selected.getByRole("heading", { name: "Madrid" })).toBeVisible();
  const values = await selected.evaluate((element) => ({
    ipr4: Number(element.getAttribute("data-ipr4")),
    ipr5: Number(element.getAttribute("data-ipr5")),
    gap: Number(element.getAttribute("data-gap")),
  }));
  expect(values.gap).toBeCloseTo(values.ipr5 - values.ipr4, 8);

  await page.reload();
  await expect(selected.getByRole("heading", { name: "Madrid" })).toBeVisible();

  await search.fill("Getxo");
  const getxoRow = table.getByRole("row", { name: /Getxo/ });
  await expect(getxoRow).toContainText("—");
  await getxoRow.getByRole("button", { name: "Seleccionar Getxo" }).click();
  await expect(selected).toContainText("No se puede comparar");
});

test("la explicación pública deja las fórmulas como detalle opcional", async ({
  page,
}) => {
  await page.goto("/metodologia");
  await expect(
    page.getByRole("heading", { name: "Cómo obtenemos la puntuación" }),
  ).toBeVisible();
  const formula = page.getByText(
    "IPR-5 = 0,30A + 0,20T + 0,20E + 0,15G + 0,15R",
  );
  await expect(formula).toBeHidden();
  await page.getByText("Ver la fórmula exacta").click();
  await expect(formula).toBeVisible();

  await page.goto("/calidad");
  await expect(
    page.getByRole("heading", {
      name: "Qué datos usamos y qué información falta",
    }),
  ).toBeVisible();
  await expect(page.getByText("nunca la convertimos en cero")).toBeVisible();
});

test("la pantalla principal sigue siendo usable en móvil", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/observatorio");
  await expect(
    page.getByRole("heading", { name: "Presión residencial total" }),
  ).toBeVisible();
  const filterToggle = page.getByRole("button", { name: "Filtros" });
  await expect(filterToggle).toBeVisible();
  const map = page.getByRole("region", {
    name: "Mapa interactivo de presión sobre la vivienda",
  });
  const mapBox = await map.boundingBox();
  expect(mapBox?.y).toBeLessThan(844);
  expect(844 - (mapBox?.y ?? 844)).toBeGreaterThan(120);
  const widths = await page.evaluate(() => ({
    viewport: window.innerWidth,
    page: document.documentElement.scrollWidth,
  }));
  expect(widths.page).toBeLessThanOrEqual(widths.viewport + 1);

  await expect(
    page.getByRole("searchbox", { name: "Buscar municipio" }),
  ).toBeVisible();

  await filterToggle.click();
  await expect(
    page.getByRole("combobox", { name: "Comunidad autónoma" }),
  ).toBeVisible();
});

test("la cabecera y la página no desbordan los anchos objetivo", async ({
  page,
}) => {
  for (const width of [320, 375, 414, 768]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/observatorio");

    const widths = await page.evaluate(() => ({
      viewport: window.innerWidth,
      page: document.documentElement.scrollWidth,
    }));
    expect(widths.page).toBeLessThanOrEqual(widths.viewport + 1);

    await page.getByRole("button", { name: "Menú" }).click();
    await expect(
      page.getByRole("navigation", { name: "Navegación principal" }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("navigation", { name: "Navegación principal" })
        .getByRole("link", { name: "Datos y fuentes" }),
    ).toBeVisible();
  }
});

test("ninguna ruta desborda en horizontal entre 320 y 1440 px", async ({
  page,
}) => {
  test.setTimeout(240_000);
  const routes = [
    "/observatorio",
    "/municipio/28079?producto=observado",
    "/ranking",
    "/comparar?producto=observado&municipio=28079&municipio=08019",
    "/prospectiva",
    "/metodologia",
    "/calidad",
    "/espacial",
    "/validacion-externa",
    "/analisis-ml",
  ];

  for (const width of [320, 375, 414, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 844 });
    for (const route of routes) {
      await page.goto(route, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1200);
      const widths = await page.evaluate(() => ({
        viewport: window.innerWidth,
        page: document.documentElement.scrollWidth,
      }));
      expect(
        widths.page,
        `${route} a ${width} px desborda`,
      ).toBeLessThanOrEqual(widths.viewport + 1);
    }
  }
});

test("la capa de calidad del dato tiene su propio mapa y escala", async ({ page }) => {
  await page.goto("/observatorio?capa=calidad");
  await expect(
    page.getByRole("heading", { name: "Calidad del dato del IPR-4" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Mapa interactivo de calidad del dato" }),
  ).toBeVisible();
  await expect(page.getByText("Calidad del dato · niveles")).toBeVisible();
});

test("la ficha municipal añade la calidad del dato y el histórico comparable", async ({
  page,
}) => {
  await page.goto("/municipio/28079?producto=observado");
  await expect(page.getByRole("heading", { name: "Madrid" })).toBeVisible();
  await expect(page.getByLabel("Calidad del dato del IPR-4")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /Evolución comparable/ }),
  ).toBeVisible();
  await expect(page.getByText(/Panel fijo de \d+ municipios/)).toBeVisible();
});

test("la ficha separa la posición dentro del año de la puntuación del factor", async ({
  page,
}) => {
  await page.goto("/municipio/28079?producto=observado");
  // El panel histórico se construye con posiciones; la puntuación va al lado
  // para poder atarla con el cuadro de factores de la misma hoja.
  await expect(
    page.getByRole("columnheader", { name: "Posición en el panel" }),
  ).toBeVisible();
  await expect(
    page.getByRole("columnheader", { name: "Puntuación del factor" }),
  ).toBeVisible();

  const series = page.getByRole("heading", { name: "Series originales de los factores" });
  await series.scrollIntoViewIfNeeded();
  await expect(page.getByText(/en posición dentro de su año/)).toBeVisible();
  // Los índices comparten esa escala; el punto conserva su puntuación.
  const indice = page.locator("figure title", { hasText: "Índice total (IPR-4)" }).first();
  await expect(indice).toHaveText(/posición .+ · puntuación /);
});

test("toda vista acredita las fuentes y la procedencia queda enlazada", async ({
  page,
}) => {
  // La atribución no puede vivir solo en la página de fuentes: quien entra por
  // un enlace directo a una ficha también tiene que ver de dónde sale el dato.
  await page.goto("/municipio/28079?producto=observado");
  const pie = page.getByRole("contentinfo");
  await expect(pie.getByText(/Instituto Nacional de Estad/)).toBeVisible();
  await pie.getByRole("link", { name: "Procedencia y condiciones" }).click();
  await expect(page).toHaveURL(/\/calidad#procedencia$/);

  const procedencia = page.locator("#procedencia");
  await expect(
    procedencia.getByRole("heading", { name: "Procedencia y condiciones de reutilización" }),
  ).toBeVisible();
  // Cada fila enlaza el aviso legal del organismo, no una licencia inventada.
  const filas = procedencia.locator("tbody tr");
  expect(await filas.count()).toBeGreaterThan(8);
  await expect(procedencia.getByRole("link", { name: /Aviso legal del INE/ }).first()).toBeVisible();
  await expect(
    procedencia.getByRole("link", { name: /Política de datos del Centro de Descargas/ }),
  ).toBeVisible();
});

test("la página de datos resume el DQS y enlaza a su mapa", async ({ page }) => {
  await page.goto("/calidad");
  await expect(
    page.getByRole("heading", { name: "Calidad del dato del IPR-4 (DQS)" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Ver el mapa de calidad del dato" }),
  ).toHaveAttribute("href", "/observatorio?capa=calidad");
});

test("los patrones espaciales muestran el Moran global y la ficha local", async ({
  page,
}) => {
  await page.goto("/espacial");
  await expect(
    page.getByRole("heading", { name: "Patrones espaciales del IPR-4" }),
  ).toBeVisible();
  await expect(page.getByText(/I de Moran \d/)).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Mapa interactivo de asociaciones locales LISA" }),
  ).toBeVisible();
  await page.getByRole("combobox", { name: "Consultar municipio" }).selectOption({
    label: "Madrid",
  });
  await expect(
    page.getByRole("region", { name: "Resultado espacial del municipio" }),
  ).toContainText("IPR-4 observado");
});

test("la validación externa publica la correlación y sus límites", async ({ page }) => {
  await page.goto("/validacion-externa");
  await expect(
    page.getByRole("heading", { name: "Validación externa del índice" }),
  ).toBeVisible();
  await expect(page.getByText(/Spearman ρ = 0,54/)).toBeVisible();
  await expect(page.getByText("Correlación no implica causalidad", { exact: false })).toBeVisible();
});

test("el análisis con ML se presenta como exploratorio, nunca como predicción", async ({
  page,
}) => {
  await page.goto("/analisis-ml");
  await expect(
    page.getByRole("heading", { name: "Análisis exploratorio con Machine Learning" }),
  ).toBeVisible();
  await expect(page.getByText("Índice publicado = fórmula interpretable.")).toBeVisible();
  await expect(page.getByRole("row", { name: /XGBoost/ })).toBeVisible();
});
