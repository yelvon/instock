<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft } from "@element-plus/icons-vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import type { ECBasicOption } from "echarts/types/dist/shared";
import { ElMessage } from "element-plus";
import BacktestKlineChart from "@/features/backtest/BacktestKlineChart.vue";
import {
  cancelBacktestRun,
  compareBacktestRuns,
  createBacktestRun,
  deleteBacktestRun,
  getBacktestBatch,
  getBacktestRun,
  listBacktestRuns,
  listBacktestStrategies,
  startGridBatch,
  startWalkforwardBatch,
  backtestExportUrl,
  type BacktestCreatePayload,
  type BacktestRunDetail,
  type BacktestRunListItem,
  type BacktestStrategyItem,
  type StrategyParamDef,
} from "@/api/backtest";
import {
  groupedStrategies,
  strategyParamsFromItem,
  validateStrategyParamsClient,
} from "@/utils/strategyForm";
import {
  goBacktestGuide,
  goBacktestRun,
  goBars,
  goGaps,
  goIngest,
  goOpsRun,
} from "@/utils/navLinks";

use([CanvasRenderer, LineChart, GridComponent, LegendComponent, TooltipComponent]);

const router = useRouter();
const route = useRoute();
const runs = ref<BacktestRunListItem[]>([]);
const selectedId = ref("");
const selectedCompareIds = ref<string[]>([]);
const detail = ref<BacktestRunDetail | null>(null);
const loading = ref(false);
const detailLoading = ref(false);
const submitting = ref(false);
const precheckLoading = ref(false);
const syncSubmitting = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;
const formCollapse = ref(["strategy"]);
const resultTab = ref("overview");
const viewMode = ref<"list" | "detail">("list");
const isNarrow = ref(false);
let narrowMql: MediaQueryList | null = null;

function onNarrowChange(e: MediaQueryListEvent | MediaQueryList) {
  isNarrow.value = e.matches;
  if (!e.matches) viewMode.value = "list";
}

interface HealthRemediation {
  id?: string;
  title?: string;
  dates?: string[];
  actions?: string[];
}

interface DataHealthReport {
  ok: boolean;
  date_from?: string;
  date_to?: string;
  expected_trade_days?: number;
  missing_spot_trade_dates?: string[];
  remediation?: HealthRemediation[];
  backtest_prerequisites_ok?: boolean;
  backtest_prerequisites?: {
    messages?: string[];
    domains?: Record<
      string,
      {
        missing_trade_dates?: string[];
        code_missing?: Record<string, string[]>;
        suggested_jobs?: string[];
        table?: string;
      }
    >;
  };
}

const precheck = ref<DataHealthReport | null>(null);
const createGapReport = ref<Record<string, unknown> | null>(null);

const strategies = ref<BacktestStrategyItem[]>([]);
const strategyId = ref("moving_average_cross");
const strategyParams = ref<Record<string, number | string | boolean>>({
  fast: 5,
  slow: 20,
});

const form = ref({
  title: "双均线示例回测",
  dateFrom: "2024-01-01",
  dateTo: "2024-03-31",
  universeType: "codes" as "codes" | "selection_table" | "strategy_table",
  codesText: "600000",
  selectionTable: "cn_stock_selection",
  strategyTable: "cn_stock_strategy_enter",
  benchmarkCode: "" as "" | "000300" | "000905",
  slippageBps: 0,
  initialCash: 1000000,
  commissionRate: 0.0003,
  minCommission: 5,
  stampTaxRate: 0.001,
  maxWeightPerSymbol: 0.1,
  requirePrerequisites: true,
  barDataSource: "mootdx",
  priceMode: "raw" as "raw" | "qfq",
});

const researchForm = ref({
  gridParam1: "fast",
  gridValues1: "5,10",
  gridParam2: "slow",
  gridValues2: "20,30",
  trainDays: 60,
  testDays: 20,
  stepDays: 20,
  compareIds: "",
});
const researchBatchId = ref("");
const researchCompare = ref<Array<{ id: string; title?: string; metrics?: Record<string, number> }>>([]);
const researchSubmitting = ref(false);

const priceModeLabel = (mode: unknown) => (mode === "qfq" ? "前复权" : "不复权");

const selectedStrategy = computed(() =>
  strategies.value.find((s) => s.id === strategyId.value)
);

const strategyGroups = computed(() => groupedStrategies(strategies.value));

const strategyDetailLabel = computed(() => {
  const p = detail.value?.params as Record<string, unknown> | undefined;
  if (!p) return "";
  const title = p.strategyTitle as string | undefined;
  const id = p.strategy as string | undefined;
  if (title && id) return `${title}（${id}）`;
  return String(title || id || "");
});

const paramDefs = computed((): StrategyParamDef[] => {
  const s = selectedStrategy.value;
  if (!s) return [];
  if (s.params?.length) return s.params;
  return Object.entries(s.paramSchema || {}).map(([key, defaultVal]) => ({
    key,
    label: key,
    type: typeof defaultVal === "number" ? "float" : typeof defaultVal === "boolean" ? "bool" : "str",
    default: defaultVal,
    required: true,
  }));
});

function applyStrategyDefaults(id: string) {
  const s = strategies.value.find((x) => x.id === id);
  if (!s) return;
  strategyParams.value = strategyParamsFromItem(s);
  if (!form.value.title || form.value.title.endsWith("回测")) {
    form.value.title = `${s.title}回测`;
  }
}

watch(strategyId, (id) => applyStrategyDefaults(id));

function pct(v: unknown): string {
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  return `${(n * 100).toFixed(2)}%`;
}

function money(v: unknown): string {
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  return n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function codes(): string[] {
  return form.value.codesText
    .replace(/\n/g, ",")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

function buildPayload(): BacktestCreatePayload {
  let universe: BacktestCreatePayload["universe"];
  if (form.value.universeType === "selection_table") {
    universe = { type: "selection_table", table: form.value.selectionTable };
  } else if (form.value.universeType === "strategy_table") {
    universe = { type: "strategy_table", table: form.value.strategyTable };
  } else {
    universe = { type: "codes", codes: codes() };
  }
  const benchmark =
    form.value.benchmarkCode === "000300"
      ? { code: "000300", name: "沪深300" }
      : form.value.benchmarkCode === "000905"
        ? { code: "000905", name: "中证500" }
        : undefined;
  return {
    title: form.value.title,
    dateFrom: form.value.dateFrom,
    dateTo: form.value.dateTo,
    universe,
    strategy: {
      id: strategyId.value,
      params: { ...strategyParams.value },
    },
    broker: {
      initialCash: form.value.initialCash,
      matchPrice: "next_open",
      commissionRate: form.value.commissionRate,
      minCommission: form.value.minCommission,
      stampTaxRate: form.value.stampTaxRate,
      slippageBps: form.value.slippageBps,
    },
    risk: {
      maxPositions: 20,
      maxWeightPerSymbol: form.value.maxWeightPerSymbol,
      maxGrossExposure: 1,
    },
    data: {
      profile: "backtest",
      priceMode: form.value.priceMode,
      requirePrerequisites: form.value.requirePrerequisites,
    },
    benchmark,
  };
}

async function loadRuns() {
  loading.value = true;
  try {
    runs.value = await listBacktestRuns();
    const rid = String(route.query.runId || "");
    if (rid && runs.value.some((r) => r.id === rid)) {
      selectedId.value = rid;
    }
  } finally {
    loading.value = false;
  }
}

async function loadDetail(id: string) {
  if (!id) return;
  detailLoading.value = true;
  try {
    detail.value = await getBacktestRun(id);
  } finally {
    detailLoading.value = false;
  }
}

async function submitRun() {
  if (form.value.universeType === "codes" && !codes().length) {
    ElMessage.warning("请至少输入一个股票代码");
    return;
  }
  const err = validateStrategyParamsClient(
    strategyId.value,
    strategyParams.value,
    paramDefs.value
  );
  if (err) {
    ElMessage.warning(err);
    return;
  }
  submitting.value = true;
  createGapReport.value = null;
  try {
    const run = await createBacktestRun(buildPayload());
    selectRun(run.id);
    await loadRuns();
    await loadDetail(run.id);
    ElMessage.success("回测任务已创建");
    resultTab.value = "overview";
  } catch (e: unknown) {
    const err = e as { data?: Record<string, unknown>; message?: string };
    if (err.data?.error === "BACKTEST_DATA_GAP") {
      createGapReport.value = (err.data.prerequisites as Record<string, unknown>) || null;
      ElMessage.error(String(err.data.message || "回测主数据缺失"));
    } else {
      ElMessage.error(err.message || "创建失败");
    }
  } finally {
    submitting.value = false;
  }
}

async function runPrecheck() {
  precheckLoading.value = true;
  createGapReport.value = null;
  try {
    const qs = new URLSearchParams({
      from: form.value.dateFrom,
      to: form.value.dateTo,
      profile: "backtest",
      adjust_type: form.value.priceMode,
    });
    const c = codes();
    if (c.length) qs.set("codes", c.join(","));
    const url = `/instock/api/sync/data_health?${qs.toString()}`;
    const r = await fetch(url);
    const j = await r.json();
    if (!j.ok) {
      ElMessage.error(j.error || "数据预检失败");
      return;
    }
    precheck.value = j;
    if (j.backtest_prerequisites_ok) {
      ElMessage.success("回测前置数据检查通过");
    } else {
      ElMessage.warning("存在数据缺口，请先补数或关闭严格检查");
    }
  } catch (e) {
    ElMessage.error(String(e));
  } finally {
    precheckLoading.value = false;
  }
}

const CANONICAL_BAR_JOB: Record<string, string> = {
  mootdx: "sync_bars_mootdx_local_job",
  mootdx_online: "sync_bars_mootdx_job",
  tushare: "sync_bars_tushare_job",
  akshare: "sync_bars_akshare_job",
  eastmoney: "sync_bars_eastmoney_job",
};

async function triggerKlineSync() {
  syncSubmitting.value = true;
  const src = form.value.barDataSource || "mootdx";
  const canonJob = CANONICAL_BAR_JOB[src] || "sync_bars_mootdx_local_job";
  try {
    const r = await fetch("/instock/api/sync/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json;charset=UTF-8" },
      body: JSON.stringify({
        job_id: canonJob,
        date_mode: "range",
        date_start: form.value.dateFrom,
        date_end: form.value.dateTo,
      }),
    });
    const j = await r.json();
    if (!j.ok || !j.run?.id) {
      ElMessage.error(j.error || "触发补数失败");
      return;
    }
    ElMessage.success("K 线补数任务已触发，可在数据运维查看进度");
    goOpsRun(router, j.run.id);
  } catch (e) {
    ElMessage.error(String(e));
  } finally {
    syncSubmitting.value = false;
  }
}

function goBacktestDataTab(tab: "ingest" | "gaps" | "bars" = "ingest") {
  if (tab === "ingest") goIngest(router);
  else if (tab === "gaps") goGaps(router);
  else goBars(router);
}

function goDataSources() {
  goIngest(router);
}

function selectRun(id: string) {
  selectedId.value = id;
  goBacktestRun(router, id);
  if (isNarrow.value) viewMode.value = "detail";
}

function clearSelection() {
  selectedId.value = "";
  detail.value = null;
  goBacktestRun(router);
  if (isNarrow.value) viewMode.value = "list";
}

function applyRoutePrefill() {
  const from = String(route.query.from || "");
  const to = String(route.query.to || "");
  const priceMode = String(route.query.priceMode || "");
  const codesRaw = String(route.query.codes || "");
  if (from) form.value.dateFrom = from;
  if (to) form.value.dateTo = to;
  if (priceMode === "raw" || priceMode === "qfq") form.value.priceMode = priceMode;
  if (codesRaw) {
    form.value.universeType = "codes";
    form.value.codesText = codesRaw;
  }
}

function backToList() {
  viewMode.value = "list";
}

const precheckMessages = computed(() => precheck.value?.backtest_prerequisites?.messages || []);
const precheckMissingCanon = computed(() => {
  const d = precheck.value?.backtest_prerequisites?.domains?.canonical_daily_bar;
  return d?.missing_trade_dates || [];
});
const precheckCodeMissing = computed(() => {
  const d = precheck.value?.backtest_prerequisites?.domains?.canonical_daily_bar;
  return d?.code_missing || {};
});
const createGapMessages = computed(() => {
  const messages = createGapReport.value?.messages;
  return Array.isArray(messages) ? messages.map(String) : [];
});
const createGapCanon = computed(() => {
  const domains = createGapReport.value?.domains as
    | Record<string, { missing_trade_dates?: string[]; code_missing?: Record<string, string[]>; quality_issues?: Record<string, number>; suggested_jobs?: string[] }>
    | undefined;
  return domains?.canonical_daily_bar || {};
});
const createGapMissingDates = computed(() => createGapCanon.value.missing_trade_dates || []);
const createGapCodeMissing = computed(() => createGapCanon.value.code_missing || {});
const createGapQuality = computed(() => createGapCanon.value.quality_issues || {});

async function cancelRun(id: string) {
  await cancelBacktestRun(id);
  await loadRuns();
  await loadDetail(id);
}

async function deleteRun(id: string) {
  await deleteBacktestRun(id);
  if (selectedId.value === id) {
    clearSelection();
  }
  await loadRuns();
}

function parseGridValues(raw: string): (number | string)[] {
  return raw
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean)
    .map((x) => (Number.isFinite(Number(x)) ? Number(x) : x));
}

async function runParamGrid() {
  researchSubmitting.value = true;
  try {
    const grid: Record<string, (number | string)[]> = {};
    const v1 = parseGridValues(researchForm.value.gridValues1);
    const v2 = parseGridValues(researchForm.value.gridValues2);
    if (v1.length) grid[researchForm.value.gridParam1] = v1;
    if (v2.length) grid[researchForm.value.gridParam2] = v2;
    const batch = await startGridBatch({ basePayload: buildPayload(), grid });
    researchBatchId.value = batch.id;
    ElMessage.success(`参数网格已启动：${batch.id.slice(0, 8)}`);
  } catch (e) {
    ElMessage.error(String(e));
  } finally {
    researchSubmitting.value = false;
  }
}

async function runWalkforward() {
  researchSubmitting.value = true;
  try {
    const batch = await startWalkforwardBatch({
      basePayload: buildPayload(),
      trainDays: researchForm.value.trainDays,
      testDays: researchForm.value.testDays,
      stepDays: researchForm.value.stepDays,
    });
    researchBatchId.value = batch.id;
    ElMessage.success(`Walk-forward 已启动：${batch.id.slice(0, 8)}`);
  } catch (e) {
    ElMessage.error(String(e));
  } finally {
    researchSubmitting.value = false;
  }
}

async function loadResearchBatch() {
  if (!researchBatchId.value.trim()) return;
  try {
    await getBacktestBatch(researchBatchId.value.trim());
    ElMessage.success("批量任务已刷新");
  } catch (e) {
    ElMessage.error(String(e));
  }
}

async function runCompare() {
  const ids = (selectedCompareIds.value.length >= 2 ? selectedCompareIds.value.join(",") : researchForm.value.compareIds)
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  if (ids.length < 2) {
    ElMessage.warning("请至少输入 2 个 run id");
    return;
  }
  try {
    const res = await compareBacktestRuns(ids);
    researchCompare.value = res.items || [];
  } catch (e) {
    ElMessage.error(String(e));
  }
}

function compareSelectedRuns() {
  if (selectedCompareIds.value.length < 2) {
    ElMessage.warning("请至少勾选 2 个历史 run");
    return;
  }
  researchForm.value.compareIds = selectedCompareIds.value.join(",");
  resultTab.value = "research";
  void runCompare();
}

function onCompareSelectionChange(rows: BacktestRunListItem[]) {
  selectedCompareIds.value = rows.map((r) => r.id);
}

function exportCurrentRun() {
  if (!detail.value?.id) return;
  window.open(backtestExportUrl(detail.value.id), "_blank");
}

const selectedRun = computed(() => runs.value.find((r) => r.id === selectedId.value));

const hasRunning = computed(() =>
  runs.value.some((r) => r.status === "queued" || r.status === "running")
);

const equityOption = computed<ECBasicOption>(() => {
  const d = detail.value;
  const time = d?.equity?.time || [];
  return {
    tooltip: { trigger: "axis" },
    legend: { data: ["策略权益", d?.benchmark?.name || "基准"] },
    grid: { left: 40, right: 18, top: 36, bottom: 32 },
    xAxis: { type: "category", data: time },
    yAxis: { type: "value", name: "权益" },
    series: [
      { name: "策略权益", type: "line", data: d?.equity?.value || [], showSymbol: false },
      {
        name: d?.benchmark?.name || "基准",
        type: "line",
        data: d?.benchmark?.value || [],
        showSymbol: false,
      },
    ],
  };
});

const drawdownOption = computed<ECBasicOption>(() => ({
  tooltip: { trigger: "axis", valueFormatter: (v: unknown) => pct(v) },
  grid: { left: 48, right: 18, top: 24, bottom: 32 },
  xAxis: { type: "category", data: detail.value?.drawdown?.time || [] },
  yAxis: { type: "value", name: "回撤", axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
  series: [
    {
      name: "策略回撤",
      type: "line",
      data: detail.value?.drawdown?.value || [],
      showSymbol: false,
      areaStyle: {},
    },
  ],
}));

watch(selectedId, (id) => {
  if (id) void loadDetail(id);
});

watch(
  () => route.query.runId,
  (rid) => {
    const id = String(rid || "");
    if (id && id !== selectedId.value) {
      selectedId.value = id;
      if (isNarrow.value) viewMode.value = "detail";
    } else if (!id && selectedId.value) {
      selectedId.value = "";
      detail.value = null;
    }
  },
  { immediate: true }
);

watch(hasRunning, (running) => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  if (running) {
    pollTimer = setInterval(() => {
      void loadRuns();
      if (selectedId.value) void loadDetail(selectedId.value);
    }, 2000);
  }
});

async function loadStrategies() {
  try {
    strategies.value = await listBacktestStrategies();
    if (strategies.value.length && !strategies.value.some((s) => s.id === strategyId.value)) {
      strategyId.value = strategies.value[0].id;
    }
    applyStrategyDefaults(strategyId.value);
  } catch {
    strategies.value = [];
  }
}

onMounted(() => {
  applyRoutePrefill();
  narrowMql = window.matchMedia("(max-width: 1100px)");
  isNarrow.value = narrowMql.matches;
  narrowMql.addEventListener("change", onNarrowChange);
  void loadRuns();
  void loadStrategies();
});

onUnmounted(() => {
  narrowMql?.removeEventListener("change", onNarrowChange);
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<template>
  <div class="bt-page">
    <div
      class="bt-master-detail"
      :class="{ narrow: isNarrow, 'show-detail': viewMode === 'detail' }"
    >
      <el-card
        v-show="!isNarrow || viewMode === 'list'"
        shadow="never"
        class="bt-panel bt-list-panel"
      >
        <template #header>
          <div class="panel-head">
            <span class="panel-title">历史任务</span>
            <el-space wrap>
              <el-button size="small" link type="primary" @click="clearSelection">新建</el-button>
              <el-button size="small" :loading="loading" @click="loadRuns">刷新</el-button>
            </el-space>
          </div>
        </template>
        <el-table
          :data="runs"
          size="small"
          :height="isNarrow ? 360 : 520"
          highlight-current-row
          class="runs-table"
          :row-class-name="({ row }: { row: BacktestRunListItem }) => (row.id === selectedId ? 'is-active' : '')"
          @selection-change="onCompareSelectionChange"
          @row-click="(row: BacktestRunListItem) => selectRun(row.id)"
        >
          <el-table-column type="selection" width="38" />
          <el-table-column prop="status" label="状态" width="86">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : row.status === 'running' ? 'warning' : 'info'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="名称" min-width="120" />
          <el-table-column label="进度" width="110">
            <template #default="{ row }">
              <el-progress
                v-if="row.status === 'running' || row.status === 'queued'"
                :percentage="row.progress?.totalDays ? Math.round(((row.progress?.processedDays || 0) / row.progress.totalDays) * 100) : 0"
                :indeterminate="!row.progress?.totalDays"
                :stroke-width="6"
              />
              <span v-else class="muted">{{ row.progress?.message || "—" }}</span>
            </template>
          </el-table-column>
          <el-table-column label="收益" width="80"><template #default="{ row }">{{ pct(row.summary?.totalReturn) }}</template></el-table-column>
          <el-table-column label="回撤" width="80"><template #default="{ row }">{{ pct(row.summary?.maxDrawdown) }}</template></el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button v-if="row.status === 'running' || row.status === 'queued'" link type="warning" @click.stop="cancelRun(row.id)">取消</el-button>
              <el-button link type="danger" @click.stop="deleteRun(row.id)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button
          class="mt-mini"
          size="small"
          :disabled="selectedCompareIds.length < 2"
          @click="compareSelectedRuns"
        >
          对比勾选 run
        </el-button>
      </el-card>

      <div v-show="!isNarrow || viewMode === 'detail'" class="bt-main-panel">
        <el-button
          v-if="isNarrow && viewMode === 'detail'"
          class="back-list-btn"
          link
          type="primary"
          @click="backToList"
        >
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>

        <el-card v-if="!selectedId" shadow="never" class="bt-panel bt-panel-form">
          <template #header>
            <div class="panel-head">
              <span class="panel-title">回测配置</span>
              <el-space wrap>
                <el-button size="small" link type="primary" @click="goBacktestGuide(router)">
                  如何添加策略
                </el-button>
                <el-button size="small" :loading="submitting" type="primary" @click="submitRun">
                  运行回测
                </el-button>
              </el-space>
            </div>
          </template>
          <el-form label-position="top" size="small" class="bt-form">
            <el-collapse v-model="formCollapse">
              <el-collapse-item title="策略与标的" name="strategy">
                <el-form-item label="策略">
            <el-select
              v-model="strategyId"
              filterable
              placeholder="选择策略"
              style="width: 100%"
            >
              <el-option-group
                v-for="g in strategyGroups"
                :key="g.category"
                :label="g.label"
              >
                <el-option
                  v-for="s in g.items"
                  :key="s.id"
                  :label="s.title"
                  :value="s.id"
                  :disabled="!!s.deprecated"
                >
                  <span>{{ s.title }}</span>
                  <span class="opt-id muted">{{ s.id }}</span>
                </el-option>
              </el-option-group>
            </el-select>
            <p v-if="selectedStrategy?.description" class="field-hint">
              {{ selectedStrategy.description }}
            </p>
            <el-space v-if="selectedStrategy?.dependencyDomains?.length" wrap class="mt-mini">
              <el-text size="small" type="info">依赖数据：</el-text>
              <el-tag
                v-for="domain in selectedStrategy.dependencyDomains"
                :key="domain"
                size="small"
                type="info"
              >
                {{ domain }}
              </el-tag>
            </el-space>
          </el-form-item>
          <el-row v-if="paramDefs.length" :gutter="8" class="param-row">
            <el-col v-for="p in paramDefs" :key="p.key" :span="12">
              <el-form-item :label="p.label">
                <el-input-number
                  v-if="p.type === 'int' || p.type === 'float'"
                  v-model="strategyParams[p.key] as number"
                  :min="p.min"
                  :max="p.max"
                  :precision="p.type === 'int' ? 0 : 2"
                  :step="p.type === 'float' ? 0.01 : 1"
                  style="width: 100%"
                />
                <el-switch
                  v-else-if="p.type === 'bool'"
                  v-model="strategyParams[p.key] as boolean"
                />
                <el-input v-else v-model="strategyParams[p.key] as string" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-divider content-position="left">标的与区间</el-divider>
          <el-form-item label="股票池类型">
            <el-radio-group v-model="form.universeType">
              <el-radio label="codes">手动代码</el-radio>
              <el-radio label="selection_table">综合选股表</el-radio>
              <el-radio label="strategy_table">策略信号表</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.universeType === 'codes'" label="股票代码">
            <el-input v-model="form.codesText" type="textarea" :rows="2" placeholder="600000,000001" />
          </el-form-item>
          <el-form-item v-else-if="form.universeType === 'selection_table'" label="选股表">
            <el-input v-model="form.selectionTable" placeholder="cn_stock_selection" />
          </el-form-item>
          <el-form-item v-else label="策略信号表">
            <el-input v-model="form.strategyTable" placeholder="cn_stock_strategy_enter" />
          </el-form-item>
          <el-form-item label="任务名称">
            <el-input v-model="form.title" />
          </el-form-item>
          <el-row :gutter="8">
            <el-col :span="12">
              <el-form-item label="开始日期">
                <el-date-picker
                  v-model="form.dateFrom"
                  type="date"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="结束日期">
                <el-date-picker
                  v-model="form.dateTo"
                  type="date"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
              </el-collapse-item>
              <el-collapse-item title="资金与费用" name="broker">
          <el-form-item label="基准指数">
            <el-select v-model="form.benchmarkCode" style="width: 100%">
              <el-option label="无基准" value="" />
              <el-option label="沪深300 (000300)" value="000300" />
              <el-option label="中证500 (000905)" value="000905" />
            </el-select>
          </el-form-item>
          <el-form-item label="滑点 (bps)">
            <el-input-number v-model="form.slippageBps" :min="0" :max="100" :step="1" style="width: 100%" />
          </el-form-item>
          <el-form-item label="价格口径">
            <el-radio-group v-model="form.priceMode">
              <el-radio label="raw">不复权（通达信本地 raw）</el-radio>
              <el-radio label="qfq">前复权（标准库 qfq）</el-radio>
            </el-radio-group>
            <p v-if="form.priceMode === 'qfq'" class="field-hint">
              需先在数据运维派生前复权；可在「准备数据 → 概览」查看 qfq 行数。
            </p>
          </el-form-item>
          <el-row :gutter="8">
            <el-col :span="12"><el-form-item label="初始资金"><el-input-number v-model="form.initialCash" :min="10000" :step="10000" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="单票上限"><el-input-number v-model="form.maxWeightPerSymbol" :min="0.01" :max="1" :step="0.01" /></el-form-item></el-col>
          </el-row>
          <el-row :gutter="8">
            <el-col :span="12"><el-form-item label="佣金率"><el-input-number v-model="form.commissionRate" :min="0" :step="0.0001" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="印花税"><el-input-number v-model="form.stampTaxRate" :min="0" :step="0.0001" /></el-form-item></el-col>
          </el-row>
              </el-collapse-item>
              <el-collapse-item title="研究工具" name="research">
                <el-form-item label="网格参数1">
                  <el-input v-model="researchForm.gridParam1" placeholder="fast" style="width: 120px" />
                  <el-input v-model="researchForm.gridValues1" placeholder="5,10" class="ml-mini" />
                </el-form-item>
                <el-form-item label="网格参数2">
                  <el-input v-model="researchForm.gridParam2" placeholder="slow" style="width: 120px" />
                  <el-input v-model="researchForm.gridValues2" placeholder="20,30" class="ml-mini" />
                </el-form-item>
                <el-form-item>
                  <el-button size="small" :loading="researchSubmitting" @click="runParamGrid">运行参数网格</el-button>
                </el-form-item>
                <el-divider content-position="left">Walk-forward</el-divider>
                <el-row :gutter="8">
                  <el-col :span="8"><el-form-item label="训练日"><el-input-number v-model="researchForm.trainDays" :min="10" /></el-form-item></el-col>
                  <el-col :span="8"><el-form-item label="测试日"><el-input-number v-model="researchForm.testDays" :min="5" /></el-form-item></el-col>
                  <el-col :span="8"><el-form-item label="步长"><el-input-number v-model="researchForm.stepDays" :min="1" /></el-form-item></el-col>
                </el-row>
                <el-form-item>
                  <el-button size="small" :loading="researchSubmitting" @click="runWalkforward">运行 Walk-forward</el-button>
                </el-form-item>
                <el-divider content-position="left">多 run 对比</el-divider>
                <el-form-item label="run ids">
                  <el-input v-model="researchForm.compareIds" placeholder="uuid1,uuid2" />
                </el-form-item>
                <el-form-item>
                  <el-space wrap>
                    <el-button size="small" @click="runCompare">对比</el-button>
                    <el-input v-model="researchBatchId" placeholder="批量任务 batchId" style="width: 220px" />
                    <el-button size="small" link @click="loadResearchBatch">刷新 batch</el-button>
                  </el-space>
                </el-form-item>
                <el-table v-if="researchCompare.length" :data="researchCompare" size="small" class="mt-mini">
                  <el-table-column prop="id" label="run" min-width="160" />
                  <el-table-column prop="title" label="名称" min-width="120" />
                  <el-table-column label="收益" width="90"><template #default="{ row }">{{ pct(row.metrics?.totalReturn) }}</template></el-table-column>
                  <el-table-column label="夏普" width="80"><template #default="{ row }">{{ row.metrics?.sharpe ?? "-" }}</template></el-table-column>
                </el-table>
              </el-collapse-item>
              <el-collapse-item title="数据检查" name="data">
          <el-form-item>
            <el-checkbox v-model="form.requirePrerequisites">严格检查标准日线完整性</el-checkbox>
          </el-form-item>
          <el-form-item label="缺口时补数数据源">
            <el-select v-model="form.barDataSource" size="small">
              <el-option label="通达信本地 vipdoc（推荐）" value="mootdx" />
              <el-option label="mootdx 本地→在线" value="mootdx_online" />
              <el-option label="Tushare" value="tushare" />
              <el-option label="Akshare" value="akshare" />
              <el-option label="东财" value="eastmoney" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-space wrap>
              <el-button size="small" :loading="precheckLoading" @click="runPrecheck">先检查数据</el-button>
              <el-button size="small" @click="goDataSources">通达信本地补数</el-button>
              <el-button size="small" :loading="syncSubmitting" @click="triggerKlineSync">
                触发 K 线补数
              </el-button>
            </el-space>
          </el-form-item>
          <el-alert
            v-if="precheck && precheck.backtest_prerequisites_ok"
            type="success"
            show-icon
            :closable="false"
            title="回测前置数据检查通过"
          />
          <el-alert
            v-else-if="precheck && !precheck.backtest_prerequisites_ok"
            type="warning"
            show-icon
            :closable="false"
            title="发现回测数据缺口"
          >
            <template #default>
              <div class="gap-box">
                <div v-if="precheckMessages.length">{{ precheckMessages.join("；") }}</div>
                <div v-if="precheckMissingCanon.length">
                  标准日线缺交易日：{{ precheckMissingCanon.slice(0, 8).join(", ") }}{{ precheckMissingCanon.length > 8 ? "…" : "" }}
                </div>
                <div v-for="(dates, c) in precheckCodeMissing" :key="c" class="muted">
                  {{ c }} 缺 {{ dates.length }} 日
                </div>
                <div class="muted">
                  {{
                    form.priceMode === "qfq"
                      ? "请到「回测数据管理」补 raw 并派生 qfq，或任务中心运行「派生前复权」。"
                      : "请到「回测数据管理」补通达信本地标准日线（raw）。"
                  }}
                </div>
                <el-space wrap class="mt-mini">
                  <el-button link type="primary" @click="goBacktestDataTab('gaps')">缺口诊断</el-button>
                  <el-button link type="primary" @click="goBacktestDataTab('ingest')">去补数</el-button>
                  <el-button link type="primary" @click="goBacktestDataTab('bars')">浏览标准日线</el-button>
                </el-space>
              </div>
            </template>
          </el-alert>
          <el-alert
            v-if="createGapReport"
            class="mt-mini"
            type="error"
            show-icon
            :closable="false"
            title="创建失败：回测主数据缺失"
          >
            <template #default>
              <div class="gap-box">
                <div v-if="createGapMessages.length">{{ createGapMessages.join("；") }}</div>
                <div v-if="createGapMissingDates.length">
                  标准日线缺交易日：{{ createGapMissingDates.slice(0, 8).join(", ") }}{{ createGapMissingDates.length > 8 ? "…" : "" }}
                </div>
                <div v-for="(dates, c) in createGapCodeMissing" :key="c" class="muted">
                  {{ c }} 缺 {{ dates.length }} 日（示例 {{ dates.slice(0, 4).join(", ") }}）
                </div>
                <div v-if="Object.values(createGapQuality).some((n) => Number(n) > 0)" class="muted">
                  质量问题：suspect={{ createGapQuality.suspect || 0 }}，partial={{ createGapQuality.partial || 0 }}，low_score={{ createGapQuality.low_score || 0 }}
                </div>
              </div>
              <el-space wrap>
                <el-button link type="primary" @click="goBacktestDataTab('ingest')">准备数据 · 补数</el-button>
                <el-button link type="primary" @click="goBacktestDataTab('gaps')">缺口诊断</el-button>
              </el-space>
            </template>
          </el-alert>
              </el-collapse-item>
            </el-collapse>
        </el-form>
      </el-card>

        <el-card
          v-else-if="detail"
          id="bt-results-anchor"
          v-loading="detailLoading"
          shadow="never"
          class="bt-results-card"
        >
      <template #header>
        <div class="panel-head">
          <span class="panel-title">{{ detail.title }}</span>
          <el-space wrap>
            <el-button size="small" link @click="clearSelection">新建回测</el-button>
            <el-button v-if="detail.status === 'success'" size="small" link type="primary" @click="exportCurrentRun">导出 CSV</el-button>
            <el-tag size="small" :type="detail.status === 'success' ? 'success' : detail.status === 'failed' ? 'danger' : 'warning'">
              {{ detail.status }}
            </el-tag>
            <el-text type="info">{{ detail.dateFrom }} ~ {{ detail.dateTo }}</el-text>
            <el-text v-if="strategyDetailLabel" type="info" size="small">
              策略 {{ strategyDetailLabel }}
            </el-text>
          </el-space>
        </div>
      </template>

      <el-alert v-if="detail.status === 'failed'" type="error" :closable="false" :title="typeof detail.error === 'string' ? detail.error : detail.error?.message || '回测失败'" />

      <template v-if="detail.status !== 'failed'">
        <el-affix :offset="72" class="result-tabs-affix">
          <el-tabs v-model="resultTab" class="result-tabs">
            <el-tab-pane label="总览" name="overview" />
            <el-tab-pane label="K 线" name="kline" />
            <el-tab-pane label="成交与持仓" name="trades" />
            <el-tab-pane label="研究" name="research" />
          </el-tabs>
        </el-affix>

        <div v-show="resultTab === 'overview'">
      <div class="metric-grid">
        <div class="metric-tile">
          <span class="metric-label">累计收益</span>
          <span class="metric-value">{{ pct(detail.metrics?.totalReturn) }}</span>
        </div>
        <div class="metric-tile">
          <span class="metric-label">年化收益</span>
          <span class="metric-value">{{ pct(detail.metrics?.annualReturn) }}</span>
        </div>
        <div class="metric-tile">
          <span class="metric-label">最大回撤</span>
          <span class="metric-value metric-warn">{{ pct(detail.metrics?.maxDrawdown) }}</span>
        </div>
        <div class="metric-tile">
          <span class="metric-label">夏普</span>
          <span class="metric-value">{{ detail.metrics?.sharpe ?? "-" }}</span>
        </div>
        <div class="metric-tile">
          <span class="metric-label">换手率</span>
          <span class="metric-value">{{ pct(detail.metrics?.turnover) }}</span>
        </div>
        <div class="metric-tile">
          <span class="metric-label">交易次数</span>
          <span class="metric-value">{{ detail.metrics?.tradeCount ?? 0 }}</span>
        </div>
        <div v-if="detail.metrics?.excessReturn != null" class="metric-tile">
          <span class="metric-label">超额收益</span>
          <span class="metric-value">{{ pct(detail.metrics?.excessReturn) }}</span>
        </div>
        <div v-if="detail.metrics?.alpha != null" class="metric-tile">
          <span class="metric-label">Alpha</span>
          <span class="metric-value">{{ detail.metrics?.alpha ?? "-" }}</span>
        </div>
        <div v-if="detail.metrics?.informationRatio != null" class="metric-tile">
          <span class="metric-label">信息比率</span>
          <span class="metric-value">{{ detail.metrics?.informationRatio ?? "-" }}</span>
        </div>
      </div>

      <el-row :gutter="12" class="mt">
        <el-col :span="14"><v-chart class="chart" :option="equityOption" autoresize /></el-col>
        <el-col :span="10"><v-chart class="chart" :option="drawdownOption" autoresize /></el-col>
      </el-row>
        </div>

        <div v-show="resultTab === 'kline'">
      <BacktestKlineChart
        v-if="detail.status === 'success'"
        :run-id="detail.id"
        :codes="detail.universe?.codes || codes()"
      />
        </div>

        <div v-show="resultTab === 'trades'">
      <el-tabs class="mt inner-trade-tabs">
        <el-tab-pane label="订单记录">
          <el-table :data="detail.orders || []" size="small" height="320">
            <el-table-column prop="createdDate" label="生成日" width="110" />
            <el-table-column prop="targetDate" label="目标日" width="110" />
            <el-table-column prop="code" label="代码" width="90" />
            <el-table-column prop="side" label="方向" width="70" />
            <el-table-column prop="requestedQty" label="请求数量" width="100" />
            <el-table-column prop="status" label="状态" width="90" />
            <el-table-column prop="rejectReason" label="拒单原因" width="120" />
            <el-table-column prop="reason" label="策略原因" min-width="160" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="成交记录">
          <el-table :data="detail.trades || []" size="small" height="320">
            <el-table-column prop="date" label="日期" width="110" />
            <el-table-column prop="code" label="代码" width="90" />
            <el-table-column prop="side" label="方向" width="70" />
            <el-table-column prop="qty" label="数量" width="90" />
            <el-table-column prop="price" label="价格" width="90" />
            <el-table-column prop="amount" label="成交额" width="110" />
            <el-table-column prop="commission" label="佣金" width="90" />
            <el-table-column prop="stampTax" label="印花税" width="90" />
            <el-table-column prop="totalCost" label="总费用" width="90" />
            <el-table-column prop="cashAfter" label="成交后现金" min-width="120" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="持仓">
          <el-table :data="detail.positions || []" size="small" height="320">
            <el-table-column prop="date" label="日期" width="110" />
            <el-table-column prop="code" label="代码" width="90" />
            <el-table-column prop="qty" label="持仓" width="90" />
            <el-table-column prop="sellableQty" label="可卖" width="90" />
            <el-table-column prop="costPrice" label="成本价" width="90" />
            <el-table-column prop="closePrice" label="收盘价" width="90" />
            <el-table-column prop="marketValue" label="市值" width="110" />
            <el-table-column prop="unrealizedPnl" label="浮盈亏" width="110" />
            <el-table-column prop="weight" label="权重" width="90"><template #default="{ row }">{{ pct(row.weight) }}</template></el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="账户快照">
          <el-table :data="detail.dailyAccounts || []" size="small" height="320">
            <el-table-column prop="date" label="日期" width="110" />
            <el-table-column label="现金" width="120"><template #default="{ row }">{{ money(row.cash) }}</template></el-table-column>
            <el-table-column label="持仓市值" width="120"><template #default="{ row }">{{ money(row.marketValue) }}</template></el-table-column>
            <el-table-column label="总资产" width="120"><template #default="{ row }">{{ money(row.totalAssets) }}</template></el-table-column>
            <el-table-column label="当日收益" width="100"><template #default="{ row }">{{ pct(row.dailyReturn) }}</template></el-table-column>
            <el-table-column label="累计收益" width="100"><template #default="{ row }">{{ pct(row.cumulativeReturn) }}</template></el-table-column>
            <el-table-column label="回撤" width="100"><template #default="{ row }">{{ pct(row.drawdown) }}</template></el-table-column>
            <el-table-column prop="tradeCount" label="成交次数" width="100" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="参数与血缘">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="run_id">{{ detail.id }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ detail.status }}</el-descriptions-item>
            <el-descriptions-item label="策略">{{ strategyDetailLabel || detail.params?.strategy }}</el-descriptions-item>
            <el-descriptions-item label="价格口径">
              {{ priceModeLabel(detail.params?.priceMode) }}
              <span class="muted">({{ detail.params?.priceMode || "raw" }})</span>
            </el-descriptions-item>
            <el-descriptions-item label="数据 profile">{{ detail.lineage?.profile }}</el-descriptions-item>
            <el-descriptions-item label="行情源">{{ detail.lineage?.barProvider }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
        </div>

        <div v-show="resultTab === 'research'">
          <el-alert type="info" :closable="false" show-icon title="可在新建表单「研究工具」发起参数网格 / Walk-forward；此处对比历史 run。" />
          <el-form label-position="top" size="small" class="mt">
            <el-form-item label="对比 run ids">
              <el-input v-model="researchForm.compareIds" placeholder="uuid1,uuid2" />
            </el-form-item>
            <el-button size="small" @click="runCompare">对比选中 runs</el-button>
          </el-form>
          <el-table v-if="researchCompare.length" :data="researchCompare" size="small" class="mt">
            <el-table-column prop="id" label="run" min-width="180" />
            <el-table-column prop="title" label="名称" min-width="120" />
            <el-table-column label="累计收益" width="100"><template #default="{ row }">{{ pct(row.metrics?.totalReturn) }}</template></el-table-column>
            <el-table-column label="夏普" width="80"><template #default="{ row }">{{ row.metrics?.sharpe ?? "-" }}</template></el-table-column>
            <el-table-column label="最大回撤" width="100"><template #default="{ row }">{{ pct(row.metrics?.maxDrawdown) }}</template></el-table-column>
          </el-table>
        </div>
      </template>
        </el-card>

        <el-empty
          v-else-if="!detailLoading && !runs.length"
          class="bt-empty"
          description="暂无回测任务，请配置后点击「运行回测」"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.bt-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bt-master-detail {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.bt-master-detail.narrow {
  grid-template-columns: 1fr;
}
.bt-main-panel {
  min-width: 0;
}
.bt-list-panel :deep(.el-card__body) {
  padding-top: 8px;
}
.back-list-btn {
  margin-bottom: 8px;
}
.runs-table :deep(.is-active) {
  background: rgba(64, 158, 255, 0.08);
}
.result-tabs-affix :deep(.el-affix--fixed) {
  background: var(--el-bg-color);
  padding: 4px 0;
  z-index: 10;
}
.result-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}
.inner-trade-tabs {
  margin-top: 0;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.panel-title {
  font-weight: 600;
  font-size: 14px;
  color: #e8eef5;
}
.bt-panel {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.bt-panel-form {
  min-height: 360px;
}
.field-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
.param-row {
  margin-bottom: 4px;
}
.bt-results-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}
.ml-mini {
  margin-left: 8px;
  width: calc(100% - 128px);
}
.metric-tile {
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--el-fill-color-darker);
  border: 1px solid var(--el-border-color-extra-light);
}
.metric-label {
  display: block;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: #e8eef5;
}
.metric-warn {
  color: #f0a020;
}
.bt-empty {
  margin-top: 24px;
}
.mt {
  margin-top: 12px;
}
.mt-mini {
  margin-top: 6px;
}
.muted {
  color: var(--el-text-color-secondary);
}
.opt-id {
  margin-left: 8px;
  font-size: 11px;
}
.gap-box {
  font-size: 12px;
  line-height: 1.6;
}
.mini-pre {
  max-height: 180px;
  overflow: auto;
  padding: 8px;
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
  font-size: 12px;
}
.metric-row {
  margin-bottom: 8px;
}
.chart {
  height: 320px;
}
@media (max-width: 1100px) {
  .bt-grid {
    grid-template-columns: 1fr;
  }
}
</style>
