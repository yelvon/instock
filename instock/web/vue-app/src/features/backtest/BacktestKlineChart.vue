<script setup lang="ts">
import { computed, ref, watch } from "vue";
import CanonicalKlineChart from "@/features/charts/CanonicalKlineChart.vue";
import { getBacktestRunKline, type BacktestKlinePayload } from "@/api/backtest";
import type { KlinePeriod } from "@/utils/klineChart";

const props = defineProps<{
  runId: string;
  codes: string[];
}>();

const selectedCode = ref("");
const period = ref<KlinePeriod>("daily");
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
  () => [props.runId, selectedCode.value, period.value] as const,
  async ([runId, code, p]) => {
    if (!runId || !code) {
      payload.value = null;
      return;
    }
    loading.value = true;
    error.value = "";
    try {
      payload.value = await getBacktestRunKline(runId, code, p);
    } catch (e) {
      payload.value = null;
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  },
  { immediate: true }
);

const chartPayload = computed(() => {
  const p = payload.value;
  if (!p?.dates?.length) return null;
  return {
    dates: p.dates,
    ohlc: p.ohlc,
    volume: p.volume,
    marks: p.marks,
    adjustType: p.adjustType,
    period: p.period,
  };
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
      </div>
    </template>
    <CanonicalKlineChart
      embedded
      :payload="chartPayload"
      :marks="payload?.marks"
      :loading="loading"
      :error="error"
      :empty="payload?.empty"
      :hint="payload?.hint"
      :adjust-type="payload?.adjustType"
      v-model:period="period"
      :show-period-toggle="true"
    />
    <p class="kline-note muted">
      买卖点取自回测<strong>成交记录</strong>（T+1 开盘价撮合），标记在成交日对应价位。
    </p>
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
.kline-note {
  margin: 8px 12px 12px;
  font-size: 12px;
  line-height: 1.5;
}
.muted {
  color: var(--el-text-color-secondary);
}
</style>
