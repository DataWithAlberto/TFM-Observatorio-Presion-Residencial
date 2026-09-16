CREATE OR REPLACE VIEW api_ipr_municipal AS
SELECT i.cod_ine,m.nombre,m.provincia,m.comunidad_autonoma,i.anio,
 i.ipr4_nacional_observado score_observado,i.percentil_ipr4 percentil_observado,
 i.categoria_ipr4 categoria_observada,i.ranking_ipr4 ranking_observado,
 i.elegible_ipr5_prospectivo,i.ipr5_prospectivo score_prospectivo,
 i.percentil_ipr5_prospectivo percentil_prospectivo,
 i.categoria_ipr5_prospectivo categoria_prospectiva,
 i.ranking_ipr5_prospectivo ranking_prospectivo,
 i.score_normalizado_asequibilidad asequibilidad,i.score_normalizado_turismo turismo,
 i.score_normalizado_especulacion especulacion,i.score_normalizado_gentrificacion gentrificacion,
 i.score_normalizado_riesgo_futuro riesgo_futuro,
 i.contribucion_asequibilidad,i.contribucion_turismo,i.contribucion_especulacion,
 i.contribucion_gentrificacion,i.contribucion_riesgo_futuro,
 i.peso_asequibilidad,i.peso_turismo,i.peso_especulacion,i.peso_gentrificacion,
 i.peso_riesgo_futuro,i.capas_validas,i.metodo,i.version_metodologia,
 q.dqs_score, q.quality_level,
 CASE WHEN q.cod_ine IS NULL THEN NULL ELSE
   jsonb_build_object('score',q.dqs_score,'level',q.quality_level,
     'coverage',q.coverage_score,'recency',q.recency_score,
     'consistency',q.consistency_score,'calculation_version',q.calculation_version,
     'calculated_at',q.calculated_at) || q.details END AS data_quality
FROM indice_presion_residencial i JOIN municipios m USING(cod_ine)
LEFT JOIN data_quality_municipal q ON q.cod_ine=i.cod_ine AND q.anio=i.anio
 AND q.calculation_version='dqs-ipr4-1.0';

CREATE OR REPLACE VIEW api_contraste_prospectivo AS
SELECT cod_ine,nombre,provincia,comunidad_autonoma,anio,
 score_observado::double precision AS ipr4_observado,
 score_prospectivo::double precision AS ipr5_prospectivo,
 riesgo_futuro::double precision AS riesgo_futuro,
 CASE
   WHEN score_prospectivo IS NULL THEN NULL
   ELSE (score_prospectivo-score_observado)::double precision
 END AS brecha
FROM api_ipr_municipal;

DROP VIEW IF EXISTS api_calidad_municipal;
CREATE VIEW api_calidad_municipal AS
SELECT cod_ine,anio,
 num_nonnulls(score_normalizado_asequibilidad,score_normalizado_turismo,
   score_normalizado_especulacion,score_normalizado_gentrificacion)
   AS capas_observadas_validas,
 ROUND(num_nonnulls(score_normalizado_asequibilidad,score_normalizado_turismo,
   score_normalizado_especulacion,score_normalizado_gentrificacion)::numeric/4*100,1)
   AS cobertura_observada_pct,
 capas_validas AS capas_prospectivas_validas,
 ROUND((capas_validas::numeric/5)*100,1) AS cobertura_prospectiva_pct,
 num_nonnulls(score_normalizado_asequibilidad,score_normalizado_turismo,
   score_normalizado_especulacion,score_normalizado_gentrificacion)=4
   AS elegible_observado,
 elegible_ipr5_prospectivo AS elegible_prospectivo,
 (5-capas_validas) AS nulos_prospectivos,
 NULL::integer AS imputaciones,
 version_metodologia,
 (SELECT a.data_quality FROM api_ipr_municipal a
  WHERE a.cod_ine=indice_presion_residencial.cod_ine
    AND a.anio=indice_presion_residencial.anio) AS data_quality
FROM indice_presion_residencial;
CREATE INDEX IF NOT EXISTS idx_municipios_provincia ON municipios(provincia);
CREATE INDEX IF NOT EXISTS idx_municipios_ccaa ON municipios(comunidad_autonoma);
