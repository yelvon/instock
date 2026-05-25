<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { CandlestickChart, BarChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
  DataZoomComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import type { ECBasicOption } from "echarts/types/dist/shared";
import { getBacktestRunKline, type BacktestKlinePayload } from "@/api/backtest";

use([
  CanvasRenderer,
  CandlestickChart,
  BarChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  DataZoomComponent,
]);

const props = defineProps<{
  runId: string;
  codes: string[];
}>();

const selectedCode = ref("");
const loading = ref(false);
const error = ref("");
const payload = ref<BacktestKlinePayload | null>(null);

watch(
  () => props.codes,
  (codes) => {
    const list = codes?.filter(Boolean) || [];
    if (!list.length) {
      selectedCode.value = "";
      return;
    }
    if (!list.includes(selectedCode.value)) {
      selectedCode.value = list[0];
    }
  },
  { immediate: true }
);

watch(
  () => [props.runId, selectedCode.value] as const,
  async ([runId, code]) => {
    if (!runId || !code) {
      payload.value = null;
      return;
    }
    loading.value = true;
    error.value = "";
    try {
      payload.value = await getBacktestRunKline(runId, code);
    } catch (e) {
      payload.value = null;
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  },
  { immediate: true }
);

const chartOption = computed<ECBasicOption>(() => {
  const p = payload.value;
  if (!p?.dates?.length) return {};
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
  return {
    backgroundColor: "transparent",
    animation: false,
    legend: { data: ["K线", "成交量"], textStyle: { color: "#c7d0dc" } },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
    },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: [
      { left: 56, right: 24, top: 36, height: "52%" },
      { left: 56, right: 24, top: "72%", height: "16%" },
    ],
    xAxis: [
      { type: "category", data: p.dates, boundaryGap: true, gridIndex: 0, axisLine: { lineStyle: { color: "#3a4553" } } },
      { type: "category", data: p.dates, boundaryGap: true, gridIndex: 1, axisLine: { lineStyle: { color: "#3a4553" } } },
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
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: p.volume,
        itemStyle: { color: "rgba(120, 144, 156, 0.45)" },
      },
    ],
  };
});

const markSummary = computed(() => {
  const m = payload.value?.marks || [];
  const buys = m.filter((x) => x.side === "buy").length;
  const sells = m.filter((x) => x.side === "sell").length;
  return { buys, sells };
});
</script>

<template>
  <el-card shadow="never" class="kline-card">
    <template #header>
      <div class="kline-head">
        <span class="kline-title">K 线与买卖点</span>
        <el-select
          v-if="codes.length"
          v-model="selectedCode"
          size="small"
          style="width: 140px"
          placeholder="选择股票"
        >
          <el-option v-for="c in codes" :key="c" :label="c" :value="c" />
        </el-select>
        <el-text v-if="payload && !payload.empty" type="info" size="small">
          {{ payload.adjustType }} · 买 {{ markSummary.buys }} / 卖 {{ markSummary.sells }}
        </el-text>
      </div>
    </template>
    <div v-loading="loading" class="kline-body">
      <el-alert v-if="error" type="error" :title="error" show-icon :closable="false" />
      <el-alert
        v-else-if="payload?.empty"
        type="warning"
        :title="payload.hint || '无 K 线数据'"
        show-icon
        :closable="false"
      />
      <v-chart
        v-else-if="payload?.dates?.length"
        class="kline-chart"
        :option="chartOption"
        autoresize
      />
      <el-empty v-else description="请选择股票代码" />
      <p class="kline-note muted">
        买卖点取自回测<strong>成交记录</strong>（T+1 开盘价撮合），标记在成交日对应价位。
      </p>
    </div>
  </el-card>
</template>

<style scoped>
.kline-card {
  margin-top: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.kline-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.kline-title {
  font-weight: 600;
  font-size: 14px;
  color: #e8eef5;
}
.kline-chart {
  height: 420px;
  width: 100%;
}
.kline-note {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
}
.muted {
  color: var(--el-text-color-secondary);
}
</style>
