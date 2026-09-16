import { Archivo, Spline_Sans_Mono } from "next/font/google";

/**
 * Las dos familias del sistema «Hoja catastral».
 *
 * Archivo cubre texto, titulares y cifras destacadas; su eje `wdth` da el
 * carácter de rotulación técnica (marca al 125 %, titulares al 112 %).
 * Spline Sans Mono queda reservada a códigos, puestos, microetiquetas y
 * columnas numéricas de tabla.
 *
 * Se exponen como variables CSS en el `<body>` desde `app/layout.tsx`;
 * `tokens.css` las consume en `--font-display` y `--font-mono`.
 */
export const archivo = Archivo({
  subsets: ["latin"],
  axes: ["wdth"],
  variable: "--pf-archivo",
  display: "swap",
});

export const splineMono = Spline_Sans_Mono({
  subsets: ["latin"],
  variable: "--pf-spline",
  display: "swap",
});

/** Clases de fuente para el elemento que abre el árbol de la aplicación. */
export const fontVariables = `${archivo.variable} ${splineMono.variable}`;
