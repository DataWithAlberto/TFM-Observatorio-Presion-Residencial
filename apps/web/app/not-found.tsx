import "../tokens.css";
import "./(app)/base.css";

import Link from "next/link";

import Masthead from "@/components/hoja/Masthead";
import Sheet, { SheetBody } from "@/components/hoja/Sheet";

import styles from "./not-found.module.css";

/** Página no encontrada: la misma hoja, con la única salida útil. */
export default function NotFound() {
  return (
    <Sheet>
      <Masthead />
      <SheetBody>
        <div className={styles.page}>
          <p className={styles.code}>Error 404</p>
          <h1 className={styles.title}>Esta página no existe</h1>
          <p className={styles.text}>
            Puede que el enlace esté mal escrito o que la vista ya no esté disponible.
          </p>
          <Link className={styles.link} href="/observatorio">
            Volver al mapa
          </Link>
        </div>
      </SheetBody>
    </Sheet>
  );
}
