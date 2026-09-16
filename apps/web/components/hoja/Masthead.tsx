"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useState } from "react";

import CommandPalette from "@/components/CommandPalette";
import MunicipalitySearch from "@/components/hoja/MunicipalitySearch";
import { NAVIGATION_ITEMS } from "@/components/navigation";

import styles from "./masthead.module.css";

/**
 * Rutas que llevan el buscador de municipio en la cabecera. Filtran por el
 * parámetro `buscar`, así que el campo puede vivir fuera de la página.
 */
const SEARCH_ROUTES = new Set(["/observatorio", "/ranking", "/prospectiva"]);

/**
 * Cabecera de la hoja: marca, navegación, buscador y paleta de comandos.
 *
 * Por debajo de 1200 px la navegación se pliega tras el botón «Menú» para no
 * mostrar dos cosas a la vez; conserva `aria-label="Navegación principal"` y
 * el par `aria-controls`/`aria-expanded` que usan las pruebas.
 */
export default function Masthead() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const showSearch = SEARCH_ROUTES.has(pathname);

  return (
    <header className={styles.top}>
      <Link href="/observatorio" className={styles.word}>
        Presión residencial
      </Link>

      <nav
        className={`${styles.nav}${menuOpen ? ` ${styles.navOpen}` : ""}`}
        id="primary-navigation"
        aria-label="Navegación principal"
      >
        {NAVIGATION_ITEMS.map(({ href, label, short }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              onClick={() => setMenuOpen(false)}
            >
              {short ?? label}
            </Link>
          );
        })}
      </nav>

      <div className={styles.tools}>
        {showSearch && (
          <Suspense fallback={null}>
            <MunicipalitySearch basePath={pathname} />
          </Suspense>
        )}
        <CommandPalette />
        <button
          type="button"
          className={styles.menuToggle}
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? "Cerrar" : "Menú"}
        </button>
      </div>
    </header>
  );
}
