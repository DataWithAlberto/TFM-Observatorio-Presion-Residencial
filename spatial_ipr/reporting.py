"""Artefactos exportables y muestras de vecinos para revisión humana."""
from pathlib import Path
import os

import geopandas as gpd
import numpy as np

COLORS = {"HH": "#b33c43", "LL": "#285f98", "HL": "#d68c36", "LH": "#8c61ad", "NS": "#c2c8cd"}


def create_report(payload: dict, geometry_path: Path, destination: Path):
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/tfm13-matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    destination.mkdir(parents=True, exist_ok=True)
    geometry = gpd.read_file(geometry_path).set_index("cod_ine").to_crs(4326)
    audit = payload["audit"]
    lines = ["# Auditoría y resultados espaciales del IPR", "",
        f'Versión: {payload["metadata"]["calculation_version"]}. Semilla: {payload["years"][0]["seed"]}.', "",
        "## Auditoría previa", "", "| Comprobación | Resultado |", "|---|---:|"]
    for field in ["municipios_ipr", "municipios_con_geometria", "geometrias_validas", "geometrias_nulas",
                  "geometrias_vacias", "municipios_sin_match", "municipios_sin_vecinos", "crs"]:
        lines.append(f'| {field} | {audit[field]} |')
    for field in ["geometrias_invalidas", "geometrias_duplicadas", "ids_geometria_duplicados", "ids_ipr_duplicados"]:
        lines.append(f'| {field} | {len(audit[field])} |')
    lines += ["", "## Vecindad y alcance", "",
        "Queen es la matriz principal, normalizada por fila. Rook se compara antes de mirar significación.",
        "El universo es una muestra municipal discontinua: ausencia de vecinos en la muestra no implica aislamiento físico.", "",
        "| Método | Enlaces dirigidos | Aislados | Componentes | Vecinos mín./máx./media |", "|---|---:|---:|---:|---|"]
    for method in ["queen", "rook"]:
        w = audit[method]
        lines.append(f'| {method} | {w["directed_edges"]} | {len(w["islands"])} | {w["components"]} | '
                     f'{w["neighbor_min"]}/{w["neighbor_max"]}/{w["neighbor_mean"]:.2f} |')
    distances = [item["distance_km"] for item in audit["island_diagnostics"]]
    if distances:
        lines += ["", f'KNN k=1 evaluado en {len(distances)} aislados: distancia elipsoidal al punto representativo '
            f'del candidato más cercano, mín. {min(distances):.1f} km, mediana {np.median(distances):.1f} km, '
            f'máx. {max(distances):.1f} km. No aplicado: proximidad entre puntos no acredita contigüidad ni '
            'conectividad territorial, especialmente a través del mar. Se conserva Queen y se explicita su cobertura.', "",
            "| Municipio aislado | INE | Candidato KNN (no aplicado) | km |", "|---|---|---|---:|"]
        for row in audit["island_diagnostics"]:
            lines.append(f'| {row["nombre"]} | {row["cod_ine"]} | {row["nearest_cod_ine"]} | {row["distance_km"]:.1f} |')
    lines += ["", "## Moran global y multiplicidad", "",
        "Contraste bilateral de permutaciones (dos veces la cola inclusiva menor, con corrección +1).",
        "FDR Benjamini–Hochberg es la vista principal: reduce descubrimientos locales espurios; se conserva una vista exploratoria sin corrección.",
        "Los NS incluyen aislados no evaluables, identificados por separado. El denominador de porcentajes es todo el universo.", "",
        "| Año | n evaluados/total | I | E[I] | z perm. | p bilateral | Sin corrección | FDR |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for result in payload["years"]:
        rows = result["items"]
        tested = [row for row in rows if row["eligible"]]
        raw = sum(row["is_significant_raw"] for row in rows)
        corrected = sum(row["is_significant"] for row in rows)
        year = result["anio"]
        lines += [f'| {year} | {len(tested)}/{len(rows)} | {result["moran_i"]:.6f} | {result["expected_i"]:.6f} | '
            f'{result["z_score"]:.3f} | {result["p_value"]:.4f} | {raw} | {corrected} |']
        fig, ax = plt.subplots(figsize=(8, 6), layout="constrained")
        x = np.array([row["standardized_ipr"] for row in tested])
        y = np.array([row["spatial_lag"] for row in tested])
        ax.scatter(x, y, s=18, color="#285f98", alpha=.65)
        limit = max(abs(x).max(), abs(y).max()) * 1.1
        ax.plot([-limit, limit], [-limit * result["moran_i"], limit * result["moran_i"]], color="#b33c43", label=f'Pendiente = I = {result["moran_i"]:.3f}')
        ax.axhline(0, color="gray", linewidth=.8)
        ax.axvline(0, color="gray", linewidth=.8)
        for label, px, py in [("HH", .95, .95), ("LH", .05, .95), ("LL", .05, .05), ("HL", .95, .05)]:
            ax.text(px, py, label, transform=ax.transAxes, ha="center")
        ax.set(xlabel="IPR estandarizado (municipios evaluables)", ylabel="Spatial lag del IPR estandarizado",
               title=f'Moran scatterplot · {year} · n={len(tested)} · p={result["p_value"]:.4f}', xlim=(-limit, limit), ylim=(-limit, limit))
        ax.legend(loc="upper center")
        fig.savefig(destination / f"moran_scatterplot_{year}.png", dpi=160)
        plt.close(fig)
    for result in payload["years"]:
        year = result["anio"]
        rows = result["items"]
        lines += ["", f'## Categorías y revisión municipal · {year}', "",
            f'Permutaciones: {result["permutations"]}. Alfa: {result["alpha"]}. {result["interpretation"].capitalize()}.', "",
            "| Categoría | FDR | % universo | Sin corrección |", "|---|---:|---:|---:|"]
        for item in result["summary"]:
            lines.append(f'| {item["cluster_type"]} | {item["count"]} | {item["percentage"]:.2f}% | {item["raw_count"]} |')
        lines += ["", f'![Moran scatterplot {year}](moran_scatterplot_{year}.png)', "",
                  "Los cuadrantes son descriptivos; pertenecer a HH en el scatterplot no acredita un clúster significativo.", "",
                  "Muestra determinista por categoría: menor p entre los evaluables. Si no hay ejemplos FDR, se revisa el resultado exploratorio y se indica expresamente."]
        lookup = {row["cod_ine"]: row for row in rows}
        for kind in COLORS:
            candidates = [row for row in rows if row["eligible"] and row["cluster_type"] == kind
                          and (kind != "NS" or row["cluster_type_raw"] == "NS")]
            criterion = "FDR"
            if not candidates:
                candidates = [row for row in rows if row["eligible"] and row["cluster_type_raw"] == kind]
                criterion = "sin corrección; exploratorio"
            if not candidates:
                lines += ["", f'### {kind}', "", "No hay municipios de esta categoría; no se fabrica un ejemplo."]
                continue
            row = min(candidates, key=lambda item: (item["p_value"], item["cod_ine"]))
            code = row["cod_ine"]
            lines += ["", f'### {kind}: {geometry.loc[code, "nombre"]} ({code}) — {criterion}', "",
                f'IPR {row["ipr"]:.2f}; z {row["standardized_ipr"]:.3f}; lag(z) {row["spatial_lag"]:.3f}; '
                f'I local {row["local_moran_i"]:.4f}; p {row["p_value"]:.4f}; q FDR {row["p_value_fdr"]:.4f}.', "",
                "| Vecino INE | Nombre | IPR | z | Peso |", "|---|---|---:|---:|---:|"]
            for neighbor in row["neighbors"]:
                other = lookup[neighbor]
                lines.append(f'| {neighbor} | {geometry.loc[neighbor, "nombre"]} | {other["ipr"]:.2f} | {other["standardized_ipr"]:.3f} | {1 / row["neighbor_count"]:.3f} |')
            sample = geometry.loc[[code, *row["neighbors"]]]
            fig, ax = plt.subplots(figsize=(6, 5), layout="constrained")
            sample.plot(ax=ax, color=[COLORS[kind], *["#e5e7eb"] * row["neighbor_count"]], edgecolor="#263747")
            points = sample.geometry.representative_point()
            for neighbor in row["neighbors"]:
                ax.plot([points.loc[code].x, points.loc[neighbor].x], [points.loc[code].y, points.loc[neighbor].y], color="#263747", linewidth=1)
            for name, point in points.items():
                ax.annotate(name, (point.x, point.y), fontsize=8)
            ax.set_title(f'{kind} · {geometry.loc[code, "nombre"]} · {year}\n{criterion}')
            ax.set_axis_off()
            fig.savefig(destination / f"vecinos_{year}_{kind}.png", dpi=150)
            plt.close(fig)
            lines += ["", f'![Vecinos Queen de {code}](vecinos_{year}_{kind}.png)']
    lines += ["", "## Alcance de las conclusiones", "",
        "RQ2: Moran global contrasta estructura espacial en los municipios con contigüidad dentro de la muestra; LISA localiza asociaciones y outliers.",
        "La existencia de autocorrelación espacial indica que la distribución territorial del IPR no es independiente del entorno geográfico, pero no demuestra relaciones causales entre municipios.",
        "El IPR mide intensidad relativa; Moran mide estructura espacial. No son intercambiables.",
        "DQS no está implementado en esta revisión del proyecto; se conserva como no disponible, sin sustituirlo por cobertura.",
        "Solo se publica histórico si el fichero de entrada contiene años, universo y metodología comparables. Actualmente solo existe el corte 2023.", ""]
    (destination / "informe.md").write_text("\n".join(lines))
