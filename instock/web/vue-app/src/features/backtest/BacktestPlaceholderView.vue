<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
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
  createBacktestRun,
  deleteBacktestRun,
  getBacktestRun,
  listBacktestRuns,
  listBacktestStrategies,
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

use([CanvasRenderer, LineChart, GridComponent, LegendComponent, TooltipComponent]);

const router = useRouter();
const runs = ref<BacktestRunListItem[]>([]);
const selectedId = ref("");
const detail = ref<BacktestRunDetail | null>(null);
const loading = ref(false);
const detailLoading = ref(false);
const submitting = ref(false);
const precheckLoading = ref(false);
const syncSubmitting = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;

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
  codesText: "600000",
  initialCash: 1000000,
  commissionRate: 0.0003,
  minCommission: 5,
  stampTaxRate: 0.001,
  maxWeightPerSymbol: 0.1,
  requirePrerequisites: true,
  barDataSource: "mootdx",
  priceMode: "raw" as "raw" | "qfq",
});

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
  return {
    title: form.value.title,
    dateFrom: form.value.dateFrom,
    dateTo: form.value.dateTo,
    universe: { type: "codes", codes: codes() },
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
      slippageBps: 0,
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
  };
}

async function loadRuns() {
  loading.value = true;
  try {
    runs.value = await listBacktestRuns();
    if (!selectedId.value && runs.value[0]?.id) {
      selectedId.value = runs.value[0].id;
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
  if (!codes().length) {
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
    selectedId.value = run.id;
    await loadRuns();
    await loadDetail(run.id);
    ElMessage.success("回测任务已创建");
    document.getElementById("bt-results-anchor")?.scrollIntoView({ behavior: "smooth" });
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
    if (!j.ok) {
      ElMessage.error(j.error || "触发补数失败");
      return;
    }
    ElMessage.success("K 线补数任务已触发，可在任务中心查看进度");
    void router.push({ path: "/jobs", query: { tab: "runs" } });
  } catch (e) {
    ElMessage.error(String(e));
  } finally {
    syncSubmitting.value = false;
  }
}

function goBacktestData(tab: "ingest" | "gaps" | "bars" = "ingest") {
  void router.push(`/backtest-data/${tab}`);
}

function goDataSources() {
  goBacktestData("ingest");
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

async function cancelRun(id: string) {
  await cancelBacktestRun(id);
  await loadRuns();
  await loadDetail(id);
}

async function deleteRun(id: string) {
  await deleteBacktestRun(id);
  if (selectedId.value === id) {
    selectedId.value = "";
    detail.value = null;
  }
  await loadRuns();
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
  void loadRuns();
  void loadStrategies();
});
</script>

<template>
  <div class="bt-page">
    <div class="bt-grid">
      <el-card shadow="never" class="bt-panel bt-panel-form">
        <template #header>
          <div class="panel-head">
            <span class="panel-title">回测配置</span>
            <el-space wrap>
              <el-button size="small" link type="primary" @click="router.push('/backtest/guide')">
                如何添加策略
              </el-button>
              <el-button size="small" :loading="submitting" type="primary" @click="submitRun">
                运行回测
              </el-button>
            </el-space>
          </div>
        </template>
        <el-form label-position="top" size="small" class="bt-form">
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
          <el-form-item label="任务名称">
            <el-input v-model="form.title" />
          </el-form-item>
          <el-row :gutter="8">
            <el-col :span="12">
              <el-form-item label="开始日期">
                <el-input v-model="form.dateFrom" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="结束日期">
                <el-input v-model="form.dateTo" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="股票代码">
            <el-input v-model="form.codesText" type="textarea" :rows="2" placeholder="600000,000001" />
          </el-form-item>
          <el-form-item label="价格口径">
            <el-radio-group v-model="form.priceMode">
              <el-radio label="raw">不复权（通达信本地 raw）</el-radio>
              <el-radio label="qfq">前复权（标准库 qfq）</el-radio>
            </el-radio-group>
            <p v-if="form.priceMode === 'qfq'" class="field-hint">
              需先在任务中心派生前复权；可在「回测数据管理 → 概览」查看 qfq 行数。
            </p>
          </el-form-item>
          <el-divider content-position="left">资金与费用</el-divider>
          <el-row :gutter="8">
            <el-col :span="12"><el-form-item label="初始资金"><el-input-number v-model="form.initialCash" :min="10000" :step="10000" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="单票上限"><el-input-number v-model="form.maxWeightPerSymbol" :min="0.01" :max="1" :step="0.01" /></el-form-item></el-col>
          </el-row>
          <el-row :gutter="8">
            <el-col :span="12"><el-form-item label="佣金率"><el-input-number v-model="form.commissionRate" :min="0" :step="0.0001" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="印花税"><el-input-number v-model="form.stampTaxRate" :min="0" :step="0.0001" /></el-form-item></el-col>
          </el-row>
          <el-divider content-position="left">数据检查</el-divider>
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
                  <el-button link type="primary" @click="goBacktestData('gaps')">缺口诊断</el-button>
                  <el-button link type="primary" @click="goBacktestData('ingest')">去补数</el-button>
                  <el-button link type="primary" @click="goBacktestData('bars')">浏览标准日线</el-button>
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
              <pre class="mini-pre">{{ JSON.stringify(createGapReport, null, 2) }}</pre>
              <el-space wrap>
                <el-button link type="primary" @click="goBacktestData('ingest')">回测数据管理 · 补数</el-button>
                <el-button link type="primary" @click="goBacktestData('gaps')">缺口诊断</el-button>
              </el-space>
            </template>
          </el-alert>
        </el-form>
      </el-card>

      <el-card shadow="never" class="bt-panel bt-panel-runs">
        <template #header>
          <div class="panel-head">
            <span class="panel-title">历史任务</span>
            <el-button size="small" :loading="loading" @click="loadRuns">刷新</el-button>
          </div>
        </template>
        <el-table
          :data="runs"
          size="small"
          height="520"
          highlight-current-row
          class="runs-table"
          @row-click="(row: BacktestRunListItem) => (selectedId = row.id)"
        >
          <el-table-column prop="status" label="状态" width="86">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : row.status === 'running' ? 'warning' : 'info'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="名称" min-width="140" />
          <el-table-column label="收益" width="92"><template #default="{ row }">{{ pct(row.summary?.totalReturn) }}</template></el-table-column>
          <el-table-column label="回撤" width="92"><template #default="{ row }">{{ pct(row.summary?.maxDrawdown) }}</template></el-table-column>
          <el-table-column label="操作" width="128">
            <template #default="{ row }">
              <el-button v-if="row.status === 'running' || row.status === 'queued'" link type="warning" @click.stop="cancelRun(row.id)">取消</el-button>
              <el-button link type="danger" @click.stop="deleteRun(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-card v-if="detail" id="bt-results-anchor" shadow="never" class="bt-results-card">
      <template #header>
        <div class="panel-head">
          <span class="panel-title">{{ detail.title }}</span>
          <el-space wrap>
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
      </div>

      <el-row :gutter="12" class="mt">
        <el-col :span="14"><v-chart class="chart" :option="equityOption" autoresize /></el-col>
        <el-col :span="10"><v-chart class="chart" :option="drawdownOption" autoresize /></el-col>
      </el-row>

      <BacktestKlineChart
        v-if="detail.status === 'success'"
        :run-id="detail.id"
        :codes="detail.universe?.codes || codes()"
      />

      <el-tabs class="mt">
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
      </template>
    </el-card>

    <el-empty v-else-if="!detailLoading && !runs.length" class="bt-empty" description="暂无回测任务，请在左侧配置后点击「运行回测」" />
  </div>
</template>

<style scoped>
.bt-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bt-grid {
  display: grid;
  grid-template-columns: minmax(360px, 420px) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
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
  min-height: 520px;
}
.bt-panel-runs :deep(.el-card__body) {
  padding-top: 8px;
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
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
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
