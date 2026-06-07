import type { ECBasicOption } from "echarts/types/dist/shared";

export type KlinePeriod = "daily" | "weekly" | "monthly";

/** 主图均线周期（含常用短均线 + 用户要求的 13/45/60/100/250） */
export const KLINE_MA_PERIODS = [5, 10, 13, 20, 45, 60, 100, 250] as const;

const MA_COLORS: Record<number, string> = {
  5: "#e0e0e0",
  10: "#fac858",
  13: "#ff9800",
  20: "#5470c6",
  45: "#91cc75",
  60: "#00bcd4",
  100: "#ce93d8",
  250: "#78909c",
};

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

export type KlineChartLayout = "default" | "large";

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

/** ECharts candlestick 行: [open, close, low, high] */
function barLow(row: number[]): number {
  return row[2] ?? row[1] ?? 0;
}

function barHigh(row: number[]): number {
  return row[3] ?? row[1] ?? 0;
}

/**
 * 同花顺风格买卖点：B 红、S 绿，贴在 K 线下方/上方。
 */
function buildTradeMarkPoints(
  dates: string[],
  ohlc: number[][],
  marks: KlineMark[] | undefined
): Record<string, unknown>[] {
  const out: Record<string, unknown>[] = [];
  for (const m of marks || []) {
    const d = m.date.slice(0, 10);
    let idx = dates.indexOf(d);
    if (idx < 0) idx = dates.findIndex((x) => x.slice(0, 10) === d);
    if (idx < 0 || !ohlc[idx]) continue;
    const row = ohlc[idx];
    const isBuy = m.side === "buy";
    const low = barLow(row);
    const high = barHigh(row);
    const y = isBuy
      ? Math.min(m.price > 0 ? m.price : low, low) * 0.985
      : Math.max(m.price > 0 ? m.price : high, high) * 1.015;
    out.push({
      name: isBuy ? "买" : "卖",
      coord: [dates[idx], y],
      value: `${isBuy ? "B" : "S"} ${m.qty}`,
      symbol: "circle",
      symbolSize: 22,
      itemStyle: {
        color: isBuy ? "#e53935" : "#43a047",
        borderColor: "#ffffff",
        borderWidth: 1.5,
      },
      label: {
        show: true,
        formatter: isBuy ? "B" : "S",
        color: "#ffffff",
        fontSize: 11,
        fontWeight: "bold",
      },
    });
  }
  return out;
}

export function buildKlineEchartsOption(
  p: KlineSeriesPayload,
  layout: KlineChartLayout = "default"
): ECBasicOption {
  if (!p.dates?.length) return {};

  const large = layout === "large";
  const closes = p.ohlc.map((row) => row[1]);
  const markPoints = buildTradeMarkPoints(p.dates, p.ohlc, p.marks);

  const volumeData = p.volume.map((v, i) => {
    const row = p.ohlc[i];
    const up = row && row[1] >= row[0];
    return {
      value: v,
      itemStyle: { color: up ? "#ef5350" : "#26a69a" },
    };
  });

  const maSeries = KLINE_MA_PERIODS.map((period) => ({
    name: `MA${period}`,
    type: "line" as const,
    xAxisIndex: 0,
    yAxisIndex: 0,
    data: sma(closes, period),
    showSymbol: false,
    lineStyle: { width: period >= 100 ? 1.2 : 1, color: MA_COLORS[period] },
    z: 2,
  }));

  const legend = ["K线", ...KLINE_MA_PERIODS.map((n) => `MA${n}`), "成交量"];

  const legendSelected: Record<string, boolean> = {};
  for (const n of KLINE_MA_PERIODS) {
    legendSelected[`MA${n}`] = n <= 20 || n === 13;
  }

  return {
    backgroundColor: "transparent",
    animation: false,
    legend: {
      type: "scroll",
      data: legend,
      textStyle: { color: "#c7d0dc" },
      selected: legendSelected,
    },
    tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: large
      ? [
          { left: 64, right: 32, top: 64, height: "58%" },
          { left: 64, right: 32, top: "76%", height: "14%" },
        ]
      : [
          { left: 56, right: 24, top: 56, height: "50%" },
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
      {
        type: "inside",
        xAxisIndex: [0, 1],
        start: 0,
        end: 100,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: true,
      },
      {
        type: "slider",
        xAxisIndex: [0, 1],
        bottom: large ? 12 : 4,
        height: large ? 28 : 18,
        borderColor: "#3a4553",
        fillerColor: "rgba(64,158,255,0.15)",
        handleSize: large ? "110%" : "100%",
      },
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
          data: markPoints,
          z: 20,
        },
        z: 5,
      },
      ...maSeries,
      {
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeData,
        z: 1,
      },
    ],
  };
}

export const PERIOD_LABELS: Record<KlinePeriod, string> = {
  daily: "日 K",
  weekly: "周 K",
  monthly: "月 K",
};
