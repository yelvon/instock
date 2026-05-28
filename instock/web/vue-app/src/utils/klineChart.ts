import type { ECBasicOption } from "echarts/types/dist/shared";

export type KlinePeriod = "daily" | "weekly" | "monthly";

export interface KlineMark {
  date: string;
  side: "buy" | "sell";
  price: number;
  qty: number;
  label?: string;
}

export interface KlineSeriesPayload {
  dates: string[];
  ohlc: number[][];
  volume: number[];
  marks?: KlineMark[];
  adjustType?: string;
  period?: KlinePeriod;
}

export function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i + 1 < period) {
      out.push(null);
      continue;
    }
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += values[j];
    out.push(Number((sum / period).toFixed(4)));
  }
  return out;
}

export function buildKlineEchartsOption(p: KlineSeriesPayload): ECBasicOption {
  if (!p.dates?.length) return {};

  const closes = p.ohlc.map((row) => row[1]);
  const ma5 = sma(closes, 5);
  const ma10 = sma(closes, 10);
  const ma20 = sma(closes, 20);

  const volumeData = p.volume.map((v, i) => {
    const row = p.ohlc[i];
    const up = row && row[1] >= row[0];
    return {
      value: v,
      itemStyle: { color: up ? "#ef5350" : "#26a69a" },
    };
  });

  const buyMarks = (p.marks || [])
    .filter((m) => m.side === "buy")
    .map((m) => ({
      name: "买",
      coord: [m.date, m.price],
      value: `买 ${m.qty}`,
      symbol: "triangle",
      symbolSize: 14,
      itemStyle: { color: "#26a69a", borderColor: "#1b5e20" },
      label: { show: true, formatter: "买", color: "#fff", fontSize: 10 },
    }));
  const sellMarks = (p.marks || [])
    .filter((m) => m.side === "sell")
    .map((m) => ({
      name: "卖",
      coord: [m.date, m.price],
      value: `卖 ${m.qty}`,
      symbol: "triangle",
      symbolRotate: 180,
      symbolSize: 14,
      itemStyle: { color: "#ef5350", borderColor: "#b71c1c" },
      label: { show: true, formatter: "卖", color: "#fff", fontSize: 10 },
    }));

  const legend = ["K线", "MA5", "MA10", "MA20", "成交量"];

  return {
    backgroundColor: "transparent",
    animation: false,
    legend: { data: legend, textStyle: { color: "#c7d0dc" } },
    tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: [
      { left: 56, right: 24, top: 48, height: "50%" },
      { left: 56, right: 24, top: "72%", height: "16%" },
    ],
    xAxis: [
      {
        type: "category",
        data: p.dates,
        boundaryGap: true,
        gridIndex: 0,
        axisLine: { lineStyle: { color: "#3a4553" } },
      },
      {
        type: "category",
        data: p.dates,
        boundaryGap: true,
        gridIndex: 1,
        axisLine: { lineStyle: { color: "#3a4553" } },
      },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitLine: { lineStyle: { color: "#2a3340" } } },
      { scale: true, gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } },
    ],
    dataZoom: [
      { type: "inside", xAxisIndex: [0, 1], start: 0, end: 100 },
      { type: "slider", xAxisIndex: [0, 1], bottom: 4, height: 18 },
    ],
    series: [
      {
        name: "K线",
        type: "candlestick",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: p.ohlc,
        itemStyle: {
          color: "#ef5350",
          color0: "#26a69a",
          borderColor: "#ef5350",
          borderColor0: "#26a69a",
        },
        markPoint: {
          symbolKeepAspect: true,
          data: [...buyMarks, ...sellMarks],
        },
      },
      {
        name: "MA5",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ma5,
        showSymbol: false,
        lineStyle: { width: 1, color: "#fac858" },
      },
      {
        name: "MA10",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ma10,
        showSymbol: false,
        lineStyle: { width: 1, color: "#91cc75" },
      },
      {
        name: "MA20",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ma20,
        showSymbol: false,
        lineStyle: { width: 1, color: "#5470c6" },
      },
      {
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeData,
      },
    ],
  };
}

export const PERIOD_LABELS: Record<KlinePeriod, string> = {
  daily: "日 K",
  weekly: "周 K",
  monthly: "月 K",
};
