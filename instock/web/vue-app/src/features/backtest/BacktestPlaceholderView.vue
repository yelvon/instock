<script setup lang="ts">
import { computed, ref, watch } from "vue";
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
import PageShell from "@/components/ui/PageShell.vue";
import {
  cancelBacktestRun,
  createBacktestRun,
  deleteBacktestRun,
  getBacktestRun,
  listBacktestRuns,
  type BacktestCreatePayload,
  type BacktestRunDetail,
  type BacktestRunListItem,
} from "@/api/backtest";

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
      { missing_trade_dates?: string[]; suggested_jobs?: string[]; table?: string }
    >;
  };
}

const precheck = ref<DataHealthReport | null>(null);
const createGapReport = ref<Record<string, unknown> | null>(null);

const form = ref({
  title: "双均线示例回测",
  dateFrom: "2024-01-01",
  dateTo: "2024-03-31",
  codesText: "600000",
  fast: 5,
  slow: 20,
  initialCash: 1000000,
  commissionRate: 0.0003,
  minCommission: 5,
  stampTaxRate: 0.001,
  maxWeightPerSymbol: 0.1,
  requirePrerequisites: true,
  barDataSource: "auto",
});

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
      id: "moving_average_cross",
      params: { fast: form.value.fast, slow: form.value.slow },
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
      priceMode: "raw",
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
  submitting.value = true;
  createGapReport.value = null;
  try {
    const run = await createBacktestRun(buildPayload());
    selectedId.value = run.id;
    await loadRuns();
    await loadDetail(run.id);
    ElMessage.success("回测任务已创建");
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
    const url = `/instock/api/sync/data_health?from=${encodeURIComponent(form.value.dateFrom)}&to=${encodeURIComponent(form.value.dateTo)}`;
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
  auto: "sync_bars_mootdx_job",
  mootdx: "sync_bars_mootdx_job",
  tushare: "sync_bars_tushare_job",
  akshare: "sync_bars_akshare_job",
  eastmoney: "sync_bars_eastmoney_job",
};

async function triggerKlineSync() {
  syncSubmitting.value = true;
  const src = form.value.barDataSource || "tushare";
  const canonJob = CANONICAL_BAR_JOB[src] || "sync_bars_tushare_job";
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

function goDataSources() {
  void router.push({ path: "/jobs", query: { tab: "sources" } });
}

function goLineage() {
  void router.push({ path: "/jobs", query: { tab: "lineage" } });
}

const precheckMessages = computed(() => precheck.value?.backtest_prerequisites?.messages || []);
const precheckMissingSpot = computed(() => precheck.value?.missing_spot_trade_dates || []);

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

void loadRuns();
</script>

<template>
  <PageShell title="策略回测" subtitle="日线事件驱动回测：收益曲线、回撤、订单、成交、持仓与账户快照">
    <div class="bt-grid">
      <el-card shadow="never" class="bt-panel">
        <template #header>
          <div class="panel-head">
            <span>新建回测</span>
            <el-button size="small" :loading="submitting" type="primary" @click="submitRun">运行</el-button>
          </div>
        </template>
        <el-form label-position="top" size="small">
          <el-form-item label="名称">
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
          <el-row :gutter="8">
            <el-col :span="12"><el-form-item label="短均线"><el-input-number v-model="form.fast" :min="2" :max="120" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="长均线"><el-input-number v-model="form.slow" :min="3" :max="250" /></el-form-item></el-col>
          </el-row>
          <el-row :gutter="8">
            <el-col :span="12"><el-form-item label="初始资金"><el-input-number v-model="form.initialCash" :min="10000" :step="10000" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="单票上限"><el-input-number v-model="form.maxWeightPerSymbol" :min="0.01" :max="1" :step="0.01" /></el-form-item></el-col>
          </el-row>
          <el-row :gutter="8">
            <el-col :span="12"><el-form-item label="佣金率"><el-input-number v-model="form.commissionRate" :min="0" :step="0.0001" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="印花税"><el-input-number v-model="form.stampTaxRate" :min="0" :step="0.0001" /></el-form-item></el-col>
          </el-row>
          <el-form-item>
            <el-checkbox v-model="form.requirePrerequisites">严格检查本地数据完整性</el-checkbox>
          </el-form-item>
          <el-form-item label="补数数据源">
            <el-select v-model="form.barDataSource" size="small">
              <el-option label="mootdx（标准库作业）" value="mootdx" />
              <el-option label="Tushare（标准库作业）" value="tushare" />
              <el-option label="Akshare（标准库作业）" value="akshare" />
              <el-option label="东财（标准库作业）" value="eastmoney" />
              <el-option label="仅东财" value="eastmoney" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-space wrap>
              <el-button size="small" :loading="precheckLoading" @click="runPrecheck">先检查数据</el-button>
              <el-button size="small" @click="goDataSources">数据源工作台</el-button>
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
                <div v-if="precheckMissingSpot.length">缺主快照交易日：{{ precheckMissingSpot.slice(0, 8).join(", ") }}{{ precheckMissingSpot.length > 8 ? "…" : "" }}</div>
                <div class="muted">日线缺口优先在任务中心配置/验证 Tushare，再触发 K 线补数任务。</div>
                <el-space wrap class="mt-mini">
                  <el-button link type="primary" @click="goDataSources">检查 Tushare</el-button>
                  <el-button link type="primary" @click="goLineage">查看数据血缘</el-button>
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
                <el-button link type="primary" @click="goDataSources">去验证 Tushare</el-button>
                <el-button link type="primary" @click="goLineage">去补齐数据</el-button>
              </el-space>
            </template>
          </el-alert>
        </el-form>
      </el-card>

      <el-card shadow="never" class="bt-panel">
        <template #header>
          <div class="panel-head">
            <span>任务列表</span>
            <el-button size="small" :loading="loading" @click="loadRuns">刷新</el-button>
          </div>
        </template>
        <el-table :data="runs" size="small" height="430" highlight-current-row @row-click="(row: BacktestRunListItem) => (selectedId = row.id)">
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

    <el-card v-if="detail" shadow="never" class="mt">
      <template #header>
        <div class="panel-head">
          <span>{{ detail.title }}</span>
          <el-text type="info">{{ detail.dateFrom }} ~ {{ detail.dateTo }}</el-text>
        </div>
      </template>

      <el-alert v-if="detail.status === 'failed'" type="error" :closable="false" :title="typeof detail.error === 'string' ? detail.error : detail.error?.message || '回测失败'" />

      <template v-if="detail.status !== 'failed'">
      <el-row :gutter="12" class="metric-row">
        <el-col :span="4"><el-statistic title="累计收益" :value="pct(detail.metrics?.totalReturn)" /></el-col>
        <el-col :span="4"><el-statistic title="年化收益" :value="pct(detail.metrics?.annualReturn)" /></el-col>
        <el-col :span="4"><el-statistic title="最大回撤" :value="pct(detail.metrics?.maxDrawdown)" /></el-col>
        <el-col :span="4"><el-statistic title="夏普" :value="detail.metrics?.sharpe ?? '-'" /></el-col>
        <el-col :span="4"><el-statistic title="换手率" :value="pct(detail.metrics?.turnover)" /></el-col>
        <el-col :span="4"><el-statistic title="交易次数" :value="detail.metrics?.tradeCount ?? 0" /></el-col>
      </el-row>

      <el-row :gutter="12" class="mt">
        <el-col :span="14"><v-chart class="chart" :option="equityOption" autoresize /></el-col>
        <el-col :span="10"><v-chart class="chart" :option="drawdownOption" autoresize /></el-col>
      </el-row>

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
            <el-descriptions-item label="策略">{{ detail.params?.strategy }}</el-descriptions-item>
            <el-descriptions-item label="价格口径">{{ detail.params?.priceMode }}</el-descriptions-item>
            <el-descriptions-item label="数据 profile">{{ detail.lineage?.profile }}</el-descriptions-item>
            <el-descriptions-item label="行情源">{{ detail.lineage?.barProvider }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
      </template>
    </el-card>

    <el-empty v-else-if="!detailLoading" description="暂无回测结果，请先创建任务" />
  </PageShell>
</template>

<style scoped>
.bt-grid {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  gap: 12px;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.bt-panel {
  min-height: 520px;
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
