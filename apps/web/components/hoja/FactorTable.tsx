import type { Detail } from "@/lib/api";
import { fmt, layerLabel, percent, rampStep, TYPE_LABELS } from "@/lib/format";

import styles from "./factor-table.module.css";

/**
 * Cuadro de factores: de qué se compone la puntuación y con qué tipo de dato
 * se ha medido cada parte. La columna «Tipo» está aquí porque una estimación
 * y un dato observado no se leen igual.
 */
export default function FactorTable({ detail }: { detail: Detail }) {
  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Factor</th>
            <th scope="col">Tipo</th>
            <th scope="col" className={styles.num}>
              Valor
            </th>
            <th scope="col" className={styles.num}>
              Peso
            </th>
            <th scope="col" className={styles.num}>
              Aporta
            </th>
            <th scope="col">
              <span className="visually-hidden">Barra</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {detail.capas.map((capa) => (
            <tr key={capa.nombre}>
              <td>{layerLabel(capa.nombre)}</td>
              <td>{TYPE_LABELS[capa.tipo] ?? capa.tipo}</td>
              <td className={styles.num}>{fmt(capa.score)}</td>
              <td className={styles.num}>{percent(capa.peso)}</td>
              <td className={styles.num}>{fmt(capa.contribucion)}</td>
              <td className={styles.barCell}>
                <i
                  data-step={rampStep(capa.score)}
                  style={{ "--v": `${capa.score ?? 0}%` } as React.CSSProperties}
                />
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={4}>Puntuación total</td>
            <td className={styles.num}>{fmt(detail.score)}</td>
            <td />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
