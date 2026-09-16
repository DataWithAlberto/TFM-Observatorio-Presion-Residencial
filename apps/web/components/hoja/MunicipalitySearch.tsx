"use client";

import { useRouter, useSearchParams } from "next/navigation";

import styles from "./masthead.module.css";

/**
 * Buscador de municipio de la cabecera. Escribe el parámetro `buscar` en la
 * URL, que es la fuente de verdad del explorador; al cambiar la búsqueda se
 * suelta el municipio seleccionado, igual que hace `useExplorer`.
 */
export default function MunicipalitySearch({ basePath }: { basePath: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const value = searchParams.get("buscar") ?? "";

  const update = (next: string) => {
    const params = new URLSearchParams(searchParams);
    params.delete("municipio");
    if (next) params.set("buscar", next);
    else params.delete("buscar");
    const query = params.toString();
    router.replace(query ? `${basePath}?${query}` : basePath, { scroll: false });
  };

  return (
    <label className={styles.search}>
      <span className="visually-hidden">Buscar municipio</span>
      <input
        type="search"
        value={value}
        placeholder="Buscar municipio"
        autoComplete="off"
        onChange={(event) => update(event.target.value)}
      />
    </label>
  );
}
