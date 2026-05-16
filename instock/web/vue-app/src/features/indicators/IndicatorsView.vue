<script setup lang="ts">
import { computed, ref, watch, onUnmounted, shallowRef } from "vue";
import { useRoute } from "vue-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/vue-query";
import { queryClient as globalQueryClient } from "@/queryClient";
import { useResizeObserver } from "@vueuse/core";
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
} from "lightweight-charts";
import type { IChartApi, ISeriesApi, Time } from "lightweight-charts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import type { ECBasicOption } from "echarts/types/dist/shared";
import PageShell from "@/components/ui/PageShell.vue";
import UiStateError from "@/components/ui/UiStateError.vue";
import UiStateLoading from "@/components/ui/UiStateLoading.vue";

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent]);

interface KlineBundle {
  ok: boolean;
  code: string;
  date: string;
  stockName: string;
  bars: Record<string, unknown>[];
  indicatorTabs: {
    title: string;
    desc: string;
    series: { key: string; name: string; values: (number | null)[] }[];
  }[];
  attention: { supported: boolean; state: string };
  links: Record<string, string | null>;
}

const route = useRoute();
const queryClient = useQueryClient();

const code = computed(() => (route.query.code as string) || "");
const date = computed(() => (route.query.date as string) || "");
const stockName = computed(() => (route.query.name as string) || "");

function instockAbsUrl(path: string): string {
  if (typeof window === "undefined") return path;
  const p = path.startsWith("/") ? path : `/${path}`;
  return new URL(p, window.location.origin).href;
}

function abortAfterMs(ms: number): AbortSignal {
  if (typeof AbortSignal.timeout === "function") {
    return AbortSignal.timeout(ms);
  }
  const ac = new AbortController();
  window.setTimeout(() => ac.abort(), ms);
  return ac.signal;
}

function mergeAbortSignals(
  querySignal: AbortSignal | undefined,
  timeoutMs: number
): AbortSignal {
  const timeoutSignal = abortAfterMs(timeoutMs);
  if (!querySignal) return timeoutSignal;
  if (typeof AbortSignal.any === "function") {
    return AbortSignal.any([querySignal, timeoutSignal]);
  }
  const ac = new AbortController();
  const abort = () => ac.abort();
  querySignal.addEventListener("abort", abort);
  timeoutSignal.addEventListener("abort", abort);
  return ac.signal;
}

const bundleQuery = useQuery({
  queryKey: computed(() => ["klineBundle", code.value, date.value, stockName.value]),
  enabled: computed(() => !!code.value && !!date.value),
  retry: 0,
  refetchOnWindowFocus: false,
  queryFn: async ({ signal }): Promise<KlineBundle> => {
    const q = new URLSearchParams({
      code: code.value,
      date: date.value,
      name: stockName.value,
    });
    const reqSignal = mergeAbortSignals(signal, 25_000);
    try {
      const r = await fetch(instockAbsUrl("/instock/api/kline_bundle?" + q.toString()), {
        signal: reqSignal,
      });
      const text = await r.text();
      let j: KlineBundle & { ok?: boolean; error?: string };
      try {
        j = JSON.parse(text) as typeof j;
      } catch {
        throw new Error(`HTTP ${r.status}：响应非 JSON`);
      }
      if (!r.ok || !j.ok) {
        throw new Error(j.error || `HTTP ${r.status}`);
      }
      return j as KlineBundle;
    } catch (e) {
      if (reqSignal.aborted || (e instanceof Error && e.name === "AbortError")) {
        throw new Error("已取消或超时（离开指标页会中断拉取，避免阻塞其它页面）");
      }
      throw e;
    }
  },
});

onUnmounted(() => {
  void globalQueryClient.cancelQueries({ queryKey: ["klineBundle"] });
});

const chartEl = ref<HTMLElement | null>(null);
const chart = shallowRef<IChartApi | null>(null);

function timeStr(d: unknown): string {
  if (d == null) return "";
  if (typeof d === "string") return d.split("T")[0].slice(0, 10);
  return String(d).slice(0, 10);
}

function num(v: unknown): number | undefined {
  if (v == null || v === "") return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
}

function disposeChart() {
  chart.value?.remove();
  chart.value = null;
}

function buildChart() {
  disposeChart();
  const el = chartEl.value;
  const bars = bundleQuery.data.value?.bars;
  if (!el || !bars?.length) return;

  const byT = new Map<string, Record<string, unknown>>();
  for (const row of bars) {
    const t = timeStr(row.date);
    if (!t) continue;
    byT.set(t, row);
  }
  const sorted = Array.from(byT.entries()).sort(([a], [b]) => a.localeCompare(b));

  const c = createChart(el, {
    layout: { textColor: "#c7d0dc", background: { type: "solid", color: "#141922" } },
    grid: { vertLines: { color: "#2a3340" }, horzLines: { color: "#2a3340" } },
    rightPriceScale: { borderColor: "#2a3340" },
    timeScale: { borderColor: "#2a3340" },
  });
  chart.value = c;

  const cs = c.addSeries(CandlestickSeries, {
    upColor: "#ef5350",
    downColor: "#26a69a",
    borderVisible: false,
    wickUpColor: "#ef5350",
    wickDownColor: "#26a69a",
  });

  const vs = c.addSeries(HistogramSeries, {
    color: "#5470c6",
    priceFormat: { type: "volume" },
    priceScaleId: "",
  });
  vs.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

  const ma = c.addSeries(LineSeries, { color: "#fac858", lineWidth: 1 });

  const candleData = sorted.map(([t, row]) => ({
    time: t as Time,
    open: num(row.open) ?? 0,
    high: num(row.high) ?? 0,
    low: num(row.low) ?? 0,
    close: num(row.close) ?? 0,
  }));
  cs.setData(candleData);

  const volData = sorted.map(([t, row]) => ({
    time: t as Time,
    value: num(row.volume) ?? 0,
    color: row.is_red === "1" ? "#ef535055" : "#26a69a55",
  }));
  vs.setData(volData);

  const maPts = sorted
    .map(([t, row]) => ({ time: t as Time, value: num(row.ma10) }))
    .filter((p) => p.value != null) as { time: Time; value: number }[];
  if (maPts.length) ma.setData(maPts);

  c.timeScale().fitContent();
}

watch(
  () => [bundleQuery.data.value, chartEl.value] as const,
  () => {
    if (bundleQuery.isSuccess && bundleQuery.data.value?.bars?.length) {
      requestAnimationFrame(() => buildChart());
    }
  },
  { flush: "post" }
);

useResizeObserver(chartEl, () => {
  if (chart.value && chartEl.value) {
    chart.value.applyOptions({
      width: chartEl.value.clientWidth,
      height: chartEl.value.clientHeight,
    });
  }
});

onUnmounted(() => disposeChart());

const tabIndex = ref(0);

const echartsOption = computed<ECBasicOption>(() => {
  const tabs = bundleQuery.data.value?.indicatorTabs;
  if (!tabs?.length) return {};
  const tab = tabs[tabIndex.value];
  if (!tab?.series?.length) return {};
  const n = tab.series[0]?.values?.length ?? 0;
  const x = Array.from({ length: n }, (_, i) => String(i));
  const series = tab.series.map((s) => ({
    type: "line" as const,
    name: s.name,
    data: (s.values ?? []).map((v) => (v == null ? null : v)),
    showSymbol: false,
    smooth: false,
  }));
  return {
    backgroundColor: "transparent",
    textStyle: { color: "#c7d0dc" },
    tooltip: { trigger: "axis" },
    legend: { type: "scroll", bottom: 0, textStyle: { color: "#c7d0dc" } },
    grid: { left: 48, right: 24, top: 28, bottom: 64 },
    xAxis: { type: "category", data: x, boundaryGap: false },
    yAxis: { type: "value", scale: true, splitLine: { lineStyle: { color: "#2a3340" } } },
    series,
  };
});

const attentionMutation = useMutation({
  mutationFn: async (next: string) => {
    const otype = next === "1" ? "1" : "0";
    await fetch(
      `/instock/control/attention?code=${encodeURIComponent(code.value)}&otype=${otype}`
    );
    return next;
  },
  onSuccess: () => {
    void queryClient.invalidateQueries({
      queryKey: ["klineBundle", code.value, date.value, stockName.value],
    });
  },
});

const pageTitle = computed(
  () => `${bundleQuery.data.value?.code || code.value} · 指标`
);
</script>

<template>
  <PageShell :title="pageTitle" :subtitle="stockName || bundleQuery.data?.stockName || ''">
    <UiStateError
      v-if="!code || !date"
      message="缺少 code 或 date 参数。请从数据表点击代码进入。"
    />
    <UiStateError
      v-else-if="bundleQuery.isError"
      :message="(bundleQuery.error as Error)?.message || '加载失败'"
    />
    <div v-if="bundleQuery.isError && code && date" class="retry-row">
      <el-button type="primary" size="small" @click="() => bundleQuery.refetch()">
        重试
      </el-button>
    </div>
    <UiStateLoading v-else-if="bundleQuery.isPending" />
    <template v-else-if="bundleQuery.data">
      <div class="toolbar">
        <template v-if="bundleQuery.data.attention.supported">
          <el-button
            size="small"
            type="primary"
            :loading="attentionMutation.isPending"
            @click="
              attentionMutation.mutate(
                bundleQuery.data.attention.state === '1' ? '0' : '1'
              )
            "
          >
            {{ bundleQuery.data.attention.state === "1" ? "取关" : "关注" }}
          </el-button>
        </template>
        <el-link
          v-if="bundleQuery.data.links.eastmoneyHq"
          :href="bundleQuery.data.links.eastmoneyHq!"
          target="_blank"
          type="primary"
        >
          行情
        </el-link>
        <el-link
          v-if="bundleQuery.data.links.eastmoneyF10"
          :href="bundleQuery.data.links.eastmoneyF10!"
          target="_blank"
          type="primary"
        >
          资料
        </el-link>
        <el-link
          v-if="bundleQuery.data.links.tdxMine"
          :href="bundleQuery.data.links.tdxMine!"
          target="_blank"
          type="primary"
        >
          扫雷
        </el-link>
        <el-link
          v-if="bundleQuery.data.links.patternArticle"
          :href="bundleQuery.data.links.patternArticle!"
          target="_blank"
        >
          形态说明
        </el-link>
      </div>

      <div ref="chartEl" class="lw-chart" />

      <el-tabs v-model="tabIndex" type="border-card" class="sub-tabs">
        <el-tab-pane
          v-for="(tab, idx) in bundleQuery.data.indicatorTabs"
          :key="tab.title + idx"
          :label="tab.title"
          :name="idx"
        >
          <div v-if="tab.desc" class="desc" v-html="tab.desc" />
        </el-tab-pane>
      </el-tabs>
      <v-chart class="echart" :option="echartsOption" autoresize />
    </template>
  </PageShell>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}
.lw-chart {
  width: 100%;
  height: 360px;
  margin-bottom: 16px;
}
.sub-tabs {
  margin-top: 4px;
}
.echart {
  height: 300px;
  width: 100%;
}
.desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
  max-height: 72px;
  overflow: auto;
}
.retry-row {
  margin-top: 8px;
}
</style>
