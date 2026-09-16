import styles from "./quality-scale.module.css";

const STEPS = [
  { id: "muy_baja", label: "Muy baja", range: "< 50" },
  { id: "baja", label: "Baja", range: "50–70" },
  { id: "media", label: "Media", range: "70–85" },
  { id: "alta", label: "Alta", range: "≥ 85" },
];

/**
 * Los cuatro niveles del DQS con la escala de calidad, distinta de la rampa
 * de presión para que un mapa de calidad no se confunda con uno de presión.
 */
export default function QualityScale() {
  return (
    <ul className={styles.scale}>
      {STEPS.map((step, index) => (
        <li key={step.id}>
          <i data-step={index + 1} aria-hidden="true" />
          <span>{step.label}</span>
          <small>{step.range}</small>
        </li>
      ))}
    </ul>
  );
}
