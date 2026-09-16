import { defineConfig } from "@playwright/test";

const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL;

/**
 * API ya en marcha, normalmente la de Docker en el 8000. Con ella, Playwright
 * solo levanta la web y no hace falta el entorno de Python: el arranque del
 * proyecto no lo pide, así que las pruebas tampoco deberían exigirlo.
 */
const externalApiUrl = process.env.PLAYWRIGHT_API_URL;
const apiUrl = externalApiUrl || "http://localhost:8100";

const webServer = {
  command: `NEXT_PUBLIC_API_URL=${apiUrl} npm run dev -- -p 3100`,
  url: "http://localhost:3100/observatorio",
  reuseExistingServer: false,
  timeout: 30_000,
};

const apiServer = {
  command:
    "CORS_ORIGINS=http://localhost:3100 python -m uvicorn app.main:app --app-dir ../api --host 127.0.0.1 --port 8100",
  url: "http://localhost:8100/health",
  reuseExistingServer: true,
  timeout: 30_000,
};

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  fullyParallel: false,
  use: {
    baseURL: externalBaseUrl || "http://localhost:3100",
    viewport: { width: 1365, height: 900 },
  },
  // Sin variables, Playwright levanta la API y la web. Con PLAYWRIGHT_API_URL,
  // solo la web. Con PLAYWRIGHT_BASE_URL, nada: todo corre ya por tu cuenta.
  webServer: externalBaseUrl
    ? undefined
    : externalApiUrl
      ? [webServer]
      : [apiServer, webServer],
});
