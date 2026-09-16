import Link from "next/link";

import { SOURCE_BODIES } from "@/lib/sources";

import styles from "./colophon.module.css";

/**
 * Pie de la hoja con la atribución mínima de los datos.
 *
 * Los organismos se nombran en todas las vistas, no solo en la página de
 * fuentes: quien llega a una ficha por un enlace directo tiene que poder ver
 * de dónde sale lo que está leyendo. El detalle del recurso concreto y de las
 * condiciones de cada organismo vive en «Datos y fuentes», enlazado aquí.
 *
 * La cartografía base la acredita el propio mapa con su control de créditos.
 */
export default function Colophon() {
  return (
    <footer className={styles.colophon}>
      <p>
        <b>Datos:</b> {SOURCE_BODIES.join(" · ")}. Elaboración propia a partir de
        estos recursos; cada organismo conserva sus condiciones de reutilización.
      </p>
      <Link href="/calidad#procedencia">Procedencia y condiciones</Link>
    </footer>
  );
}
