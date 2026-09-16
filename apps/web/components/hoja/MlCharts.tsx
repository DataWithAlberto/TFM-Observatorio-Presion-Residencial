"use client";

import ReactECharts from "echarts-for-react";

import { chartTokens } from "@/lib/chartTheme";

export type MlReport = {
  features: { name: string; label: string; mean_abs_shap: number }[];
  rows: {
    cod_ine: string;
    nombre: string;
    score: number;
    xgboost: number;
    absolute_error: number;
    shap: number[];
    imputed_values: number[];
  }[];
};

/**
 * Los cuatro gráficos del análisis exploratorio, con los tokens de la hoja.
 * Se dibujan con ECharts porque el enjambre SHAP pide un lienzo; el resto
 * podría ir en SVG, pero se mantienen juntos para que se lean como un solo
 * sistema.
 */
function useOptions(report: MlReport) {
  const t = chartTokens();
  const axisLabel = { color: t.muted, fontFamily: t.font, fontSize: 12 };
  const axisLine = { lineStyle: { color: t.ink, width: 1 } };
  const nameStyle = { color: t.ink, fontFamily: t.font, fontSize: 12, fontWeight: 600 };
  const split = { lineStyle: { color: t.rule, width: 1, type: "dashed" } };
  const common = {
    animation: false,
    backgroundColor: "transparent",
    textStyle: { color: t.ink2, fontFamily: t.font },
    tooltip: {
      trigger: "item",
      backgroundColor: t.paper,
      borderColor: t.ink,
      borderWidth: 1,
      textStyle: { color: t.ink, fontFamily: t.font, fontSize: 13 },
      extraCssText: "box-shadow: 5px 5px 0 rgb(23 32 27 / 12%); border-radius: 0;",
    },
    grid: { left: 60, right: 25, top: 24, bottom: 56 },
  };

  const order = report.features
    .map((feature, index) => ({ ...feature, index }))
    .sort((a, b) => b.mean_abs_shap - a.mean_abs_shap);

  const maxError = Math.max(...report.rows.map((row) => row.absolute_error), 2);
  const bins = Array.from({ length: Math.floor(maxError / 2) + 1 }, () => 0);
  report.rows.forEach((row) => {
    bins[Math.floor(row.absolute_error / 2)] += 1;
  });

  // Enjambre: apilado determinista dentro de intervalos de contribución.
  const swarm: number[][] = [];
  const extent = Math.max(...report.rows.flatMap((row) => row.shap.map(Math.abs)), 1);
  order.forEach((feature, rank) => {
    const values = report.rows.map((row) => row.imputed_values[feature.index]);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const groups = new Map<number, number[]>();
    report.rows.forEach((row, rowIndex) => {
      const bin = Math.round(row.shap[feature.index] / (extent / 45));
      groups.set(bin, [...(groups.get(bin) ?? []), rowIndex]);
    });
    groups.forEach((indices) =>
      indices.forEach((rowIndex, slot) => {
        const offset = (slot - (indices.length - 1) / 2) * Math.min(0.08, 0.65 / indices.length);
        swarm.push([
          report.rows[rowIndex].shap[feature.index],
          rank + offset,
          max === min ? 0.5 : (values[rowIndex] - min) / (max - min),
        ]);
      }),
    );
  });

  return {
    scatter: {
      ...common,
      xAxis: {
        type: "value",
        name: "Puntuación por la fórmula",
        nameLocation: "middle",
        nameGap: 32,
        nameTextStyle: nameStyle,
        min: 0,
        max: 100,
        axisLabel,
        axisLine,
        splitLine: split,
      },
      yAxis: {
        type: "value",
        name: "Salida del XGBoost",
        nameTextStyle: nameStyle,
        min: 0,
        max: 100,
        axisLabel,
        axisLine,
        splitLine: split,
      },
      series: [
        {
          type: "scatter",
          symbolSize: 6,
          itemStyle: { color: t.series[0], opacity: 0.75 },
          data: report.rows.map((row) => ({ name: row.nombre, value: [row.score, row.xgboost] })),
        },
        {
          type: "line",
          data: [
            [0, 0],
            [100, 100],
          ],
          showSymbol: false,
          silent: true,
          lineStyle: { type: "dashed", color: t.muted, width: 1 },
        },
      ],
    },
    errors: {
      ...common,
      xAxis: {
        type: "category",
        name: "Error absoluto (puntos)",
        nameLocation: "middle",
        nameGap: 36,
        nameTextStyle: nameStyle,
        data: bins.map((_, index) => `${index * 2}–${(index + 1) * 2}`),
        axisLabel,
        axisLine,
      },
      yAxis: {
        type: "value",
        name: "Municipios",
        nameTextStyle: nameStyle,
        minInterval: 1,
        axisLabel,
        axisLine,
        splitLine: split,
      },
      series: [{ type: "bar", data: bins, itemStyle: { color: t.series[0], borderRadius: 0 } }],
    },
    global: {
      ...common,
      grid: { left: 190, right: 25, top: 12, bottom: 50 },
      xAxis: {
        type: "value",
        name: "Media de |SHAP| (puntos)",
        nameLocation: "middle",
        nameGap: 30,
        nameTextStyle: nameStyle,
        axisLabel,
        axisLine,
        splitLine: split,
      },
      yAxis: {
        type: "category",
        inverse: true,
        data: order.map((feature) => feature.label),
        axisLabel: { ...axisLabel, color: t.ink, width: 170, overflow: "break" },
        axisLine,
      },
      series: [
        {
          type: "bar",
          data: order.map((feature) => feature.mean_abs_shap),
          itemStyle: { color: t.series[0], borderRadius: 0 },
          barMaxWidth: 22,
        },
      ],
    },
    beeswarm: {
      ...common,
      grid: { left: 190, right: 25, top: 12, bottom: 84 },
      xAxis: {
        type: "value",
        name: "Contribución SHAP (puntos)",
        nameLocation: "middle",
        nameGap: 28,
        nameTextStyle: nameStyle,
        axisLabel,
        axisLine,
        splitLine: split,
      },
      yAxis: {
        type: "value",
        inverse: true,
        min: -0.5,
        max: order.length - 0.5,
        interval: 0.5,
        axisLabel: {
          ...axisLabel,
          color: t.ink,
          width: 170,
          overflow: "break",
          formatter: (value: number) =>
            Number.isInteger(value) ? (order[value]?.label ?? "") : "",
        },
        axisLine,
        splitLine: { show: false },
      },
      visualMap: {
        type: "continuous",
        min: 0,
        max: 1,
        dimension: 2,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        text: ["Entrada alta", "Entrada baja"],
        textStyle: { color: t.ink2, fontFamily: t.font, fontSize: 12 },
        calculable: false,
        inRange: { color: [t.divergent[0], t.divergent[4]] },
      },
      series: [
        {
          type: "scatter",
          symbolSize: 4,
          data: swarm,
          encode: { x: 0, y: 1, tooltip: [0, 2] },
          markLine: {
            silent: true,
            symbol: "none",
            label: { show: false },
            lineStyle: { color: t.ink, width: 1 },
            data: [{ xAxis: 0 }],
          },
        },
      ],
    },
  };
}

export default function MlCharts({
  report,
  which,
  height,
}: {
  report: MlReport;
  which: "scatter" | "errors" | "global" | "beeswarm";
  height: number;
}) {
  const options = useOptions(report);
  return <ReactECharts option={options[which]} notMerge style={{ height, width: "100%" }} />;
}
