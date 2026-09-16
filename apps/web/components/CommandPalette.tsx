"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { NAVIGATION_ITEMS } from "@/components/navigation";

import styles from "./hoja/command-palette.module.css";

function normalize(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("es");
}

export default function CommandPalette() {
  const router = useRouter();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  const filteredItems = useMemo(() => {
    const needle = normalize(query.trim());
    if (!needle) return NAVIGATION_ITEMS;
    return NAVIGATION_ITEMS.filter((item) =>
      normalize(
        `${item.label} ${item.description} ${item.keywords}`,
      ).includes(needle),
    );
  }, [query]);

  const openPalette = useCallback(() => {
    const dialog = dialogRef.current;
    if (!dialog || dialog.open) return;
    setQuery("");
    setActiveIndex(0);
    dialog.showModal();
    window.requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  const closePalette = useCallback(() => {
    dialogRef.current?.close();
  }, []);

  const openItem = useCallback(
    (href: string) => {
      closePalette();
      router.push(href);
    },
    [closePalette, router],
  );

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openPalette();
      }
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [openPalette]);

  return (
    <>
      <button
        type="button"
        className={styles.trigger}
        aria-label="Abrir navegación rápida"
        aria-haspopup="dialog"
        aria-controls="command-palette"
        onClick={openPalette}
      >
        <svg
          className={styles.triggerIcon}
          viewBox="0 0 20 20"
          aria-hidden="true"
        >
          <circle cx="8.5" cy="8.5" r="5.25" />
          <path d="m12.5 12.5 4 4" />
        </svg>
        <span>Ir a una vista…</span>
        <kbd>⌘K</kbd>
      </button>

      <dialog
        ref={dialogRef}
        className={styles.dialog}
        id="command-palette"
        aria-labelledby="command-title"
        onCancel={closePalette}
        onClick={(event) => {
          if (event.target === event.currentTarget) closePalette();
        }}
      >
        <div className={styles.panel}>
          <div className={styles.heading}>
            <div>
              <span>Navegación rápida</span>
              <h2 id="command-title">Ir a una vista</h2>
            </div>
            <button
              type="button"
              className={styles.close}
              aria-label="Cerrar navegación rápida"
              onClick={closePalette}
            >
              Cerrar
            </button>
          </div>

          <label className={styles.field}>
            <span>Buscar una vista</span>
            <input
              ref={inputRef}
              type="search"
              value={query}
              placeholder="Mapa, ranking, metodología…"
              role="combobox"
              aria-expanded="true"
              aria-controls="command-results"
              aria-activedescendant={
                filteredItems[activeIndex]
                  ? `command-item-${activeIndex}`
                  : undefined
              }
              onChange={(event) => {
                setQuery(event.target.value);
                setActiveIndex(0);
              }}
              onKeyDown={(event) => {
                if (event.key === "ArrowDown") {
                  event.preventDefault();
                  setActiveIndex((index) =>
                    filteredItems.length
                      ? (index + 1) % filteredItems.length
                      : 0,
                  );
                }
                if (event.key === "ArrowUp") {
                  event.preventDefault();
                  setActiveIndex((index) =>
                    filteredItems.length
                      ? (index - 1 + filteredItems.length) %
                        filteredItems.length
                      : 0,
                  );
                }
                if (event.key === "Enter" && filteredItems[activeIndex]) {
                  event.preventDefault();
                  openItem(filteredItems[activeIndex].href);
                }
                if (event.key === "Escape") closePalette();
              }}
            />
          </label>

          <div
            className={styles.results}
            id="command-results"
            role="listbox"
            aria-label="Vistas disponibles"
          >
            {filteredItems.length ? (
              filteredItems.map((item, index) => (
                <button
                  type="button"
                  id={`command-item-${index}`}
                  key={item.href}
                  className={index === activeIndex ? styles.isActive : undefined}
                  role="option"
                  aria-selected={index === activeIndex}
                  onMouseMove={() => setActiveIndex(index)}
                  onClick={() => openItem(item.href)}
                >
                  <span>
                    <strong>{item.label}</strong>
                    <small>{item.description}</small>
                  </span>
                  <span aria-hidden="true">↗</span>
                </button>
              ))
            ) : (
              <p className={styles.empty} role="status">
                No hay una vista que coincida. Prueba con “mapa”, “comparar” o
                “fuentes”.
              </p>
            )}
          </div>

          <div className={styles.help} aria-hidden="true">
            <span>
              <kbd>↑</kbd>
              <kbd>↓</kbd> recorrer
            </span>
            <span>
              <kbd>↵</kbd> abrir
            </span>
            <span>
              <kbd>esc</kbd> cerrar
            </span>
          </div>
        </div>
      </dialog>
    </>
  );
}
