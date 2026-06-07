<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { CandlestickChart, BarChart, LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  MarkPointComponent,
  TooltipComponent,
  DataZoomComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import type { ECBasicOption } from "echarts/types/dist/shared";
import { FullScreen, RefreshRight } from "@element-plus/icons-vue";
import { getCanonicalKline } from "@/api/canonical";
import {
  buildKlineEchartsOption,
  PERIOD_LABELS,
  type KlineMark,
  type KlinePeriod,
  type KlineSeriesPayload,
} from "@/utils/klineChart";

use([
  CanvasRenderer,
  CandlestickChart,
  BarChart,
  LineChart,
  GridComponent,
  LegendComponent,
  MarkPointComponent,
  TooltipComponent,
  DataZoomComponent,
]);

type ChartExpose = { chart?: { resize: () => void; dispatchAction: (p: object) => void } };

const props = withDefaults(
  defineProps<{
    code?: string;
    dateFrom?: string;
    dateTo?: string;
    adjustType?: string;
    period?: KlinePeriod;
    payload?: KlineSeriesPayload | null;
    marks?: KlineMark[];
    loading?: boolean;
    error?: string;
    empty?: boolean;
    hint?: string;
    title?: string;
    subtitle?: string;
    showPeriodToggle?: boolean;
    showFullscreen?: boolean;
    embedded?: boolean;
  }>(),
  {
    adjustType: "raw",
    period: "daily",
    showPeriodToggle: true,
    showFullscreen: true,
    embedded: false,
  }
);

const emit = defineEmits<{
  "update:period": [KlinePeriod];
}>();

const periodLocal = ref<KlinePeriod>(props.period);
watch(
  () => props.period,
  (p) => {
    if (p) periodLocal.value = p;
  }
);

const internalLoading = ref(false);
const internalError = ref("");
const internalPayload = ref<KlineSeriesPayload | null>(null);
const internalEmpty = ref(false);
const internalHint = ref("");
const fullscreenVisible = ref(false);
const chartRef = ref<ChartExpose | null>(null);
const fullscreenChartRef = ref<ChartExpose | null>(null);

const useExternal = computed(() => props.payload !== undefined);

watch(periodLocal, (p) => emit("update:period", p));

watch(
  () =>
    [
      props.code,
      props.dateFrom,
      props.dateTo,
      props.adjustType,
      periodLocal.value,
      useExternal.value,
    ] as const,
  async ([code, dateFrom, dateTo, adjustType, period, external]) => {
    if (external) return;
    if (!code?.trim() || !dateFrom || !dateTo) {
      internalPayload.value = null;
      return;
    }
    internalLoading.value = true;
    internalError.value = "";
    try {
      const res = await getCanonicalKline({
        code: code.trim(),
        dateFrom,
        dateTo,
        adjustType: adjustType || "raw",
        period,
      });
      if (res.empty) {
        internalPayload.value = null;
        internalEmpty.value = true;
        internalHint.value = res.hint || "无 K 线数据";
        return;
      }
      internalEmpty.value = false;
      internalPayload.value = {
        dates: res.dates,
        ohlc: res.ohlc,
        volume: res.volume,
        marks: res.marks,
        adjustType: res.adjustType,
        period: res.period,
      };
    } catch (e) {
      internalPayload.value = null;
      internalError.value = e instanceof Error ? e.message : String(e);
    } finally {
      internalLoading.value = false;
    }
  },
  { immediate: true }
);

const seriesPayload = computed<KlineSeriesPayload | null>(() => {
  if (useExternal.value) {
    const p = props.payload;
    if (!p?.dates?.length) return null;
    return {
      ...p,
      marks: props.marks ?? p.marks,
    };
  }
  return internalPayload.value;
});

const isLoading = computed(() => props.loading ?? internalLoading.value);
const errorText = computed(() => props.error ?? internalError.value);
const isEmpty = computed(() => props.empty ?? internalEmpty.value);
const emptyHint = computed(() => props.hint ?? internalHint.value);
const canShowChart = computed(() => !!seriesPayload.value?.dates?.length && !errorText.value && !isEmpty.value);

const chartOption = computed<ECBasicOption>(() => {
  const p = seriesPayload.value;
  if (!p) return {};
  return buildKlineEchartsOption(p, "default");
});

const fullscreenChartOption = computed<ECBasicOption>(() => {
  const p = seriesPayload.value;
  if (!p) return {};
  return buildKlineEchartsOption(p, "large");
});

const metaLine = computed(() => {
  const p = seriesPayload.value;
  if (!p) return "";
  const parts = [props.adjustType || p.adjustType, PERIOD_LABELS[periodLocal.value]];
  if (p.marks?.length) {
    const buys = p.marks.filter((m) => m.side === "buy").length;
    const sells = p.marks.filter((m) => m.side === "sell").length;
    parts.push(`买 ${buys} / 卖 ${sells}`);
  }
  return parts.filter(Boolean).join(" · ");
});

function dispatchZoom(chart: ChartExpose | null, start: number, end: number) {
  chart?.chart?.dispatchAction({ type: "dataZoom", start, end });
}

function resetZoom(target: "inline" | "fullscreen" | "both" = "both") {
  if (target === "inline" || target === "both") dispatchZoom(chartRef.value, 0, 100);
  if (target === "fullscreen" || target === "both") dispatchZoom(fullscreenChartRef.value, 0, 100);
}

async function openFullscreen() {
  if (!canShowChart.value) return;
  fullscreenVisible.value = true;
  await nextTick();
  chartRef.value?.chart?.resize();
  fullscreenChartRef.value?.chart?.resize();
}

async function onFullscreenOpened() {
  await nextTick();
  fullscreenChartRef.value?.chart?.resize();
}

function onFullscreenClosed() {
  nextTick(() => chartRef.value?.chart?.resize());
}

const periodOptions = [
  { label: "日 K", value: "daily" },
  { label: "周 K", value: "weekly" },
  { label: "月 K", value: "monthly" },
];
</script>

<template>
  <component :is="embedded ? 'div' : 'el-card'" shadow="never" class="kline-card">
    <template v-if="!embedded" #header>
      <div class="kline-head">
        <span class="kline-title">{{ title || "K 线" }}</span>
        <el-segmented
          v-if="showPeriodToggle"
          v-model="periodLocal"
          size="small"
          :options="periodOptions"
        />
        <el-text v-if="metaLine" type="info" size="small">{{ metaLine }}</el-text>
        <el-text v-if="subtitle" type="info" size="small">{{ subtitle }}</el-text>
        <el-button
          v-if="showFullscreen && canShowChart"
          size="small"
          :icon="FullScreen"
          class="head-action"
          @click="openFullscreen"
        >
          全屏
        </el-button>
      </div>
    </template>
    <div v-if="embedded" class="kline-head embedded-head">
      <span class="kline-title">{{ title || "K 线" }}</span>
      <el-segmented
        v-if="showPeriodToggle"
        v-model="periodLocal"
        size="small"
        :options="periodOptions"
      />
      <el-text v-if="metaLine" type="info" size="small">{{ metaLine }}</el-text>
      <el-button
        v-if="showFullscreen && canShowChart"
        size="small"
        :icon="FullScreen"
        class="head-action"
        @click="openFullscreen"
      >
        全屏
      </el-button>
    </div>
    <div v-loading="isLoading" class="kline-body">
      <el-alert v-if="errorText" type="error" :title="errorText" show-icon :closable="false" />
      <el-alert
        v-else-if="isEmpty"
        type="warning"
        :title="emptyHint"
        show-icon
        :closable="false"
      />
      <el-empty
        v-else-if="!seriesPayload?.dates?.length && !isLoading"
        description="请填写股票代码与日期区间"
      />
      <template v-else-if="canShowChart">
        <v-chart
          ref="chartRef"
          class="kline-chart"
          :option="chartOption"
          autoresize
        />
        <p class="zoom-hint muted">滚轮缩放 · 拖拽平移 · 底部滑块选区间</p>
      </template>
      <slot name="footer" />
    </div>
  </component>

  <el-dialog
    v-model="fullscreenVisible"
    class="kline-fullscreen-dialog"
    fullscreen
    destroy-on-close
    :show-close="true"
    @opened="onFullscreenOpened"
    @closed="onFullscreenClosed"
  >
    <template #header>
      <div class="fs-head">
        <span class="fs-title">{{ title || "K 线" }} · 全屏</span>
        <el-segmented v-if="showPeriodToggle" v-model="periodLocal" size="small" :options="periodOptions" />
        <el-text v-if="metaLine" type="info" size="small">{{ metaLine }}</el-text>
        <div class="fs-actions">
          <el-button size="small" :icon="RefreshRight" @click="resetZoom('fullscreen')">重置缩放</el-button>
        </div>
      </div>
    </template>
    <div v-loading="isLoading" class="fs-body">
      <v-chart
        v-if="canShowChart"
        ref="fullscreenChartRef"
        class="kline-chart-fs"
        :option="fullscreenChartOption"
        autoresize
      />
      <p class="zoom-hint fs-hint muted">
        鼠标滚轮缩放 · 按住拖拽平移 · 拖动底部滑块选择日期区间 · B 买 / S 卖
      </p>
    </div>
  </el-dialog>
</template>

<style scoped>
.kline-card {
  margin-top: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.kline-head,
.embedded-head,
.fs-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.embedded-head {
  margin-bottom: 8px;
}
.kline-title,
.fs-title {
  font-weight: 600;
  font-size: 14px;
  color: #e8eef5;
}
.fs-title {
  font-size: 16px;
}
.head-action {
  margin-left: auto;
}
.fs-actions {
  margin-left: auto;
}
.kline-chart {
  height: 480px;
  width: 100%;
}
.kline-chart-fs {
  height: calc(100vh - 140px);
  min-height: 420px;
  width: 100%;
}
.kline-body,
.fs-body {
  min-height: 120px;
}
.zoom-hint {
  margin: 6px 4px 0;
  font-size: 12px;
  line-height: 1.4;
}
.fs-hint {
  margin-top: 8px;
}
.muted {
  color: var(--el-text-color-secondary);
}
</style>

<style>
.kline-fullscreen-dialog .el-dialog__body {
  padding-top: 8px;
  padding-bottom: 12px;
}
</style>
