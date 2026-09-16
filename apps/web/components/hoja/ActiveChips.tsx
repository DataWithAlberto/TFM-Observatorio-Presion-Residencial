import styles from "./active-chips.module.css";

export type Chip = {
  key: string;
  label: string;
  onRemove: () => void;
};

/**
 * Los filtros puestos, a la vista y reversibles de un golpe. Sin ellos el
 * usuario no sabe por qué la pantalla enseña menos municipios de los que hay.
 */
export default function ActiveChips({ chips }: { chips: Chip[] }) {
  if (chips.length === 0) return null;
  return (
    <ul className={styles.chips} aria-label="Filtros activos">
      {chips.map((chip) => (
        <li key={chip.key}>
          <button type="button" onClick={chip.onRemove} aria-label={`Quitar ${chip.label}`}>
            {chip.label}
            <i aria-hidden="true">×</i>
          </button>
        </li>
      ))}
    </ul>
  );
}
