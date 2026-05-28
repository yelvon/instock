<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { CandlestickChart, BarChart, LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
  DataZoomComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import type { ECBasicOption } from "echarts/types/dist/shared";
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
  TooltipComponent,
  DataZoomComponent,
]);

const props = withDefaults(
  defineProps<{
    code?: string;
    dateFrom?: string;
    dateTo?: string;
    adjustType?: string;
    period?: KlinePeriod;
    /** 外部已拉取的数据（如回测 API），设置后不再请求 canonical/kline */
    payload?: KlineSeriesPayload | null;
    marks?: KlineMark[];
    loading?: boolean;
    error?: string;
    empty?: boolean;
    hint?: string;
    title?: string;
    subtitle?: string;
    showPeriodToggle?: boolean;
    embedded?: boolean;
  }>(),
  {
    adjustType: "raw",
    period: "daily",
    showPeriodToggle: true,
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

const chartOption = computed<ECBasicOption>(() => {
  const p = seriesPayload.value;
  if (!p) return {};
  return buildKlineEchartsOption(p);
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
          :options="[
            { label: '日 K', value: 'daily' },
            { label: '周 K', value: 'weekly' },
            { label: '月 K', value: 'monthly' },
          ]"
        />
        <el-text v-if="metaLine" type="info" size="small">{{ metaLine }}</el-text>
        <el-text v-if="subtitle" type="info" size="small">{{ subtitle }}</el-text>
      </div>
    </template>
    <div v-if="embedded" class="kline-head embedded-head">
      <span class="kline-title">{{ title || "K 线" }}</span>
      <el-segmented
        v-if="showPeriodToggle"
        v-model="periodLocal"
        size="small"
        :options="[
          { label: '日 K', value: 'daily' },
          { label: '周 K', value: 'weekly' },
          { label: '月 K', value: 'monthly' },
        ]"
      />
      <el-text v-if="metaLine" type="info" size="small">{{ metaLine }}</el-text>
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
      <v-chart
        v-else-if="seriesPayload?.dates?.length"
        class="kline-chart"
        :option="chartOption"
        autoresize
      />
      <slot name="footer" />
    </div>
  </component>
</template>

<style scoped>
.kline-card {
  margin-top: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.kline-head,
.embedded-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.embedded-head {
  margin-bottom: 8px;
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
.kline-body {
  min-height: 120px;
}
</style>
