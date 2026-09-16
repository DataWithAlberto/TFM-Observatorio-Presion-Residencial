"use client";

import ReactECharts from "echarts-for-react";

import type { ProspectiveContrastRow } from "@/lib/api";
import { type ChartTokens, chartTokens } from "@/lib/chartTheme";
import { fmt, layerLabel } from "@/lib/format";

/**
 * Estilos compartidos por los gráficos: papel, tinta, radio 0 y sombra plana.
 * Se construyen a partir de los tokens en cada render porque ECharts necesita
 * colores literales.
 */
function styles(t: ChartTokens) {
  const tooltip = {
    backgroundColor: t.paper,
    borderColor: t.ink,
    borderWidth: 1,
    padding: [8, 10],
    textStyle: { color: t.ink, fontFamily: t.font, fontSize: 13 },
    axisPointer: {
      lineStyle: { color: t.muted, width: 1 },
      shadowStyle: { color: "rgb(23 32 27 / 7%)" },
    },
    extraCssText: "box-shadow: 5px 5px 0 rgb(23 32 27 / 12%); border-radius: 0;",
  };

  const axis = {
    axisLabel: { color: t.muted, fontFamily: t.font, fontSize: 12 },
    axisLine: { lineStyle: { color: t.ink, width: 1 } },
    axisTick: { show: false },
  };

  return {
    tooltip,
    axis,
    valueAxis: {
      ...axis,
      splitLine: { lineStyle: { color: t.rule, width: 1, type: "dashed" } },
    },
    legend: {
      textStyle: { color: t.ink2, fontFamily: t.font, fontSize: 12 },
      itemWidth: 18,
      itemHeight: 4,
      itemGap: 18,
      icon: "rect",
      bottom: 0,
    },
    axisName: {
      color: t.ink,
      fontFamily: t.font,
      fontSize: 12,
      fontWeight: 600,
    },
  };
}

export function ComparisonChart({
  items,
}: {
  items: { nombre: string; capas: { nombre: string; score: number | null }[] }[];
}) {
  const t = chartTokens();
  const s = styles(t);
  const layers = items[0]?.capas.map((layer) => layerLabel(layer.nombre, true)) ?? [];

  const option = {
    color: t.series,
    backgroundColor: "transparent",
    textStyle: { color: t.ink2, fontFamily: t.font },
    tooltip: {
      ...s.tooltip,
      trigger: "axis",
      axisPointer: { type: "shadow", shadowStyle: { color: "rgb(23 32 27 / 7%)" } },
    },
    legend: s.legend,
    grid: { left: 46, right: 18, top: 20, bottom: 60 },
    xAxis: {
      type: "category",
      data: layers,
      ...s.axis,
      axisLabel: { ...s.axis.axisLabel, interval: 0, rotate: 14 },
    },
    yAxis: { type: "value", min: 0, max: 100, ...s.valueAxis },
    series: items.map((item) => ({
      name: item.nombre,
      type: "bar",
      data: item.capas.map((layer) => layer.score),
      barMaxWidth: 34,
      itemStyle: { borderColor: t.ink, borderWidth: 1, borderRadius: 0 },
      emphasis: {
        focus: "series",
        itemStyle: { borderColor: t.accent, borderWidth: 2 },
      },
    })),
  };

  return (
    <ReactECharts
      option={option}
      style={{ height: 390 }}
      notMerge
      aria-label="Comparación de puntuaciones por factor"
    />
  );
}

type ScatterDatum = {
  value: [number, number, number];
  municipality: ProspectiveContrastRow;
};

/** Color de la diferencia sobre la rampa divergente de −15 a +15. */
function contrastColor(value: number, t: ChartTokens) {
  if (value < -7.5) return t.divergent[0];
  if (value < 0) return t.divergent[1];
  if (value > 7.5) return t.divergent[4];
  if (value > 0) return t.divergent[3];
  return t.divergent[2];
}

function escapeHTML(value: string) {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      })[character] ?? character,
  );
}

export function ProspectiveScatterChart({
  items,
  selectedId,
}: {
  items: ProspectiveContrastRow[];
  selectedId?: string | null;
}) {
  const t = chartTokens();
  const s = styles(t);

  const points = items
    .filter(
      (
        item,
      ): item is ProspectiveContrastRow & {
        ipr5_prospectivo: number;
        brecha: number;
      } => item.ipr5_prospectivo != null && item.brecha != null,
    )
    .map((item) => ({
      value: [item.ipr4_observado, item.ipr5_prospectivo, item.brecha],
      municipality: item,
      symbolSize: item.cod_ine === selectedId ? 14 : 8,
      itemStyle: {
        color: contrastColor(item.brecha, t),
        borderColor: t.ink,
        borderWidth: item.cod_ine === selectedId ? 3 : 0.75,
        opacity: item.cod_ine === selectedId ? 1 : 0.86,
      },
    }));

  const option = {
    backgroundColor: "transparent",
    textStyle: { color: t.ink2, fontFamily: t.font },
    aria: {
      enabled: true,
      description:
        "Gráfico que compara la situación actual con el resultado que añade el riesgo futuro.",
    },
    tooltip: {
      ...s.tooltip,
      trigger: "item",
      formatter: ({ data }: { data?: ScatterDatum }) => {
        if (!data?.municipality) return "";
        const item = data.municipality;
        const sign = item.brecha != null && item.brecha > 0 ? "+" : "";
        return [
          `<strong>${escapeHTML(item.nombre)}</strong>`,
          `Situación actual: ${fmt(item.ipr4_observado)}`,
          `Con riesgo futuro: ${fmt(item.ipr5_prospectivo)}`,
          `Diferencia: ${item.brecha == null ? "—" : `${sign}${fmt(item.brecha)}`}`,
        ].join("<br>");
      },
    },
    grid: { left: 58, right: 24, top: 30, bottom: 54 },
    xAxis: {
      type: "value",
      name: "Situación actual · IPR-4",
      min: 0,
      max: 100,
      nameLocation: "middle",
      nameGap: 34,
      nameTextStyle: s.axisName,
      ...s.valueAxis,
    },
    yAxis: {
      type: "value",
      name: "Con riesgo futuro · IPR-5",
      min: 0,
      max: 100,
      nameLocation: "middle",
      nameGap: 42,
      nameTextStyle: s.axisName,
      ...s.valueAxis,
    },
    series: [
      {
        name: "Misma puntuación",
        type: "line",
        data: [
          [0, 0],
          [100, 100],
        ],
        symbol: "none",
        silent: true,
        lineStyle: { color: t.ink, type: "dashed", width: 1.5 },
        tooltip: { show: false },
      },
      {
        name: "Municipios",
        type: "scatter",
        data: points,
        emphasis: {
          scale: 1.5,
          itemStyle: { borderColor: t.accent, borderWidth: 2, opacity: 1 },
        },
      },
    ],
  };

  return (
    <ReactECharts
      option={option}
      style={{ height: 430 }}
      notMerge
      aria-label="Comparación entre la situación actual y el resultado con riesgo futuro"
    />
  );
}
