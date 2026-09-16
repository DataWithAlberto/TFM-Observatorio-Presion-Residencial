import type { Metadata, Viewport } from "next";

import Providers from "@/components/Providers";
import { fontVariables } from "@/lib/fonts";

export const metadata: Metadata = {
  title: "Presión sobre la vivienda",
  description:
    "Consulta y compara la presión sobre la vivienda en 306 municipios españoles",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" data-scroll-behavior="smooth">
      <body className={fontVariables}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
