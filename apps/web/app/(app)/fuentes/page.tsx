import TitleBlock from "@/components/hoja/TitleBlock";
import { DATA_SOURCES } from "@/lib/sources";

import styles from "../calidad/calidad.module.css";

export default function SourcesPage() {
  return (
    <div className={styles.page}>
      <article className={styles.prose}>
        <TitleBlock title="Fuentes y condiciones de uso" reading="El observatorio elabora sus resultados a partir de datos de organismos públicos." hint="El corte del índice observado es 2023; las fechas de cada fuente pueden ser diferentes." />
        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Procedencia de los datos</h2>
          <p>Elaboración propia con datos del INE, MIVAU, Dirección General del Catastro y AdapteCCa (AEMET y Oficina Española de Cambio Climático). Los organismos no respaldan ni avalan los resultados del observatorio.</p>
          <p>El INE establece CC BY 4.0 como licencia general de su información estadística, salvo indicación contraria, y autoriza únicamente los datos cuya fuente original sea el propio INE. Para los datos transformados debe citarse la fuente y la última actualización cuando conste en el original.</p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr><th scope="col">Organismo</th><th scope="col">Recurso</th><th scope="col">Qué aporta</th><th scope="col">Condiciones y revisión</th></tr></thead>
              <tbody>
                {DATA_SOURCES.map((source) => (
                  <tr key={`${source.organismo}-${source.recurso}`}>
                    <th scope="row">{source.organismo}</th>
                    <td>{source.url ? <a href={source.url} target="_blank" rel="noreferrer noopener">{source.recurso}</a> : source.recurso}</td>
                    <td>{source.aporta}</td>
                    <td><a href={source.condicionesUrl} target="_blank" rel="noreferrer noopener">{source.condiciones}</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Fechas y reutilización</h2>
          <p>Las fechas de descarga registradas y las huellas digitales están disponibles en el {" "}<a href="https://github.com/DataWithAlberto/TFM-Observatorio-Presion-Residencial/blob/main/data/data_manifest.json" target="_blank" rel="noreferrer noopener">manifiesto de datos</a>. La fecha de descarga no sustituye a la última actualización del productor; cuando esta no esté documentada no se puede confirmar aquí.</p>
          <p>Las condiciones de los recursos de MIVAU y Catastro, los modelos climáticos concretos y el origen de la geometría municipal aún requieren comprobación. No se ha confirmado la autorización para todos los usos comerciales o la redistribución de los datos originales y derivados. Consulta las condiciones de cada recurso antes de reutilizar las descargas.</p>
          <p>Las proyecciones climáticas CMIP6 de AdapteCCa usan el escenario SSP2-4.5 y representan tendencias inciertas a largo plazo, no predicciones exactas. Algunos modelos pueden restringir su uso comercial; sus condiciones deben comprobarse individualmente.</p>
          <p>La cartografía base del mapa tiene sus propios créditos, visibles en el mapa.</p>
        </section>
      </article>
    </div>
  );
}
