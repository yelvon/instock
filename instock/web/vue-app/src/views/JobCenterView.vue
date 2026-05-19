<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Refresh, VideoPlay, VideoPause } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import PageShell from "@/components/ui/PageShell.vue";
import {
  cancelEastmoneyProbe,
  runEastmoneyProbePoll,
  startEastmoneyProbe,
} from "@/api/eastmoneyProbe";
import {
  cancelMootdxProbe,
  runMootdxProbePoll,
  startMootdxProbe,
} from "@/api/mootdxProbe";

const router = useRouter();
const route = useRoute();
const activeTab = ref(String(route.query.tab || "manual"));

interface JobItem {
  id: string;
  title: string;
  hint?: string;
  description?: string;
}

interface RunRow {
  id: string;
  job_id: string;
  label: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  exit_code?: number | null;
  date_mode?: string;
  date_list?: string;
  date_start?: string;
  date_end?: string;
  spot_data_source?: string;
  bar_data_source?: string;
  trigger_source?: string;
  schedule_title?: string;
  schedule_id?: string;
  progress_bytes?: number;
  progress_lines?: number;
  error_line_count?: number;
  last_errors_tail?: string;
  stdout_tail?: string;
  error_message?: string;
  progress_hint?: string;
  progress_current?: number;
  progress_total?: number;
  batch_ids?: string[];
}

interface ScheduleRow {
  id: string;
  title: string;
  enabled: boolean;
  job_id: string;
  date_mode: string;
  date_start: string;
  date_end: string;
  date_list: string;
  weekdays: number[];
  times: string[];
  spot_data_source: string;
}

interface BatchRow {
  batch_id: string;
  domain_id: string;
  trade_date?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  scope_type?: string | null;
  scope_key?: string | null;
  row_count?: number | null;
  source_provider: string;
  enrich_providers?: unknown;
  mixed_source?: boolean;
  adjust_type?: string | null;
  profile?: string;
  input_batches?: unknown;
  status: string;
  job_id?: string | null;
  created_at?: string | null;
}

const jobs = ref<JobItem[]>([]);
const jobId = ref("basic_data_daily_job");
const dateMode = ref<"default" | "list" | "range">("default");
const dateList = ref("");
const dateStart = ref("");
const dateEnd = ref("");
const spotSource = ref("eastmoney");
const barSource = ref("auto");
const runMsg = ref("");

const runs = ref<RunRow[]>([]);
const selectedRunIds = ref<string[]>([]);
const detailId = ref("");
const detailRun = ref<RunRow | null>(null);
const detailErr = ref("");
const detailOut = ref("");

const trackingId = ref<string | null>(null);
const stopping = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;
const progressPanel = ref(false);
const progressText = ref("");
const progressPercent = ref(0);
const progressIndeterminate = ref(true);
const liveOut = ref("");
const liveErr = ref("");
const showErrBox = ref(false);
const runningLabel = ref("");

const schedGlobal = ref(true);
const schedDraft = ref<ScheduleRow[]>([]);
const schedMsg = ref("");
const schTitle = ref("");
const schTimes = ref("");
const schSpot = ref("eastmoney");
const schJobId = ref("basic_data_daily_job");
const schWeekdays = ref<number[]>([0, 1, 2, 3, 4]);
const wdOptions = [
  { v: 0, l: "一" },
  { v: 1, l: "二" },
  { v: 2, l: "三" },
  { v: 3, l: "四" },
  { v: 4, l: "五" },
  { v: 5, l: "六" },
  { v: 6, l: "日" },
];

const batchDomain = ref("");
const batches = ref<BatchRow[]>([]);
const batchMsg = ref("");

const govEnv = ref<Record<string, string | boolean>>({});
const govHint = ref("");

const dhFrom = ref("");
const dhTo = ref("");
const dhMsg = ref("");
const dhSummary = ref("");
const dhBtOk = ref<boolean | null>(null);
const dhRemediation = ref("");
const dhMissingCsv = ref("");

interface ChainStep {
  order: number;
  role: string;
  provider: string;
  strict?: boolean;
  when?: string | null;
  fill_mode?: string | null;
  mode?: string | null;
}

interface MootdxDetail {
  provider_id: string;
  INSTOCK_TDX_DIR?: string;
  dir_exists?: boolean;
  vipdoc_exists?: boolean;
  healthcheck?: boolean;
  sample_ok?: boolean;
  sample_rows?: number;
  sample_error?: string | null;
  active_in_chain?: boolean;
  fallback_when?: string;
  hint?: string;
}

interface TushareDetail {
  provider_id: string;
  token_configured?: boolean;
  token_source?: string;
  healthcheck?: boolean;
  sample_ok?: boolean;
  sample_rows?: number;
  sample_error?: string | null;
  active_in_chain?: boolean;
  capabilities?: string[];
  hint?: string;
}

interface ProviderStatus {
  provider_id: string;
  import_ok: boolean;
  healthcheck: boolean;
  error?: string | null;
  capabilities: string[];
}

const dsMsg = ref("");
const dsLoading = ref(false);
const dsReport = ref<{
  mootdx_installed?: boolean;
  profile?: string;
  bar_mode?: string;
  use_data_registry?: boolean;
  registry_enabled_for_bars?: boolean;
  mootdx_local?: MootdxDetail;
  mootdx_online?: MootdxDetail;
  tushare?: TushareDetail;
  providers?: ProviderStatus[];
  domains?: Record<
    string,
    { profile_current?: ChainStep[]; profile_live?: ChainStep[]; profile_backtest?: ChainStep[] }
  >;
  recent_bar_batches?: BatchRow[];
  management?: {
    docker_env?: string[];
    docker_volume?: string;
    verify_cli?: string[];
    doc?: string;
  };
} | null>(null);
const verifyCode = ref("600000");
const verifyMsg = ref("");
const emProbing = ref(false);
const emProbeLogs = ref("");
const emProbeId = ref("");
let stopEmProbePoll: (() => void) | null = null;
const mootdxProbing = ref(false);
const mootdxProbeLogs = ref("");
const mootdxProbeId = ref("");
let stopMootdxProbePoll: (() => void) | null = null;

const domainOptions = [
  { value: "", label: "全部域" },
  { value: "daily_spot_snapshot", label: "daily_spot_snapshot" },
  { value: "daily_bar_raw", label: "daily_bar_raw" },
  { value: "derived_indicators", label: "derived_indicators" },
  { value: "trade_calendar", label: "trade_calendar" },
];

function formatRunConditions(r: RunRow): string {
  let prefix = "";
  if (r.trigger_source === "scheduler") {
    prefix = `【定时】${r.schedule_title || r.schedule_id || ""} · `;
  }
  if (r.job_id === "init_job" || r.job_id === "sync_trade_calendar_job") {
    return prefix + "默认";
  }
  const dm = (r.date_mode || "default").toLowerCase();
  let cond = dm === "default" ? "默认" : dm === "list" ? `枚举：${r.date_list || ""}` : `区间：${r.date_start}~${r.date_end}`;
  if (r.job_id === "basic_data_daily_job" && r.spot_data_source) {
    cond += ` · 快照：${r.spot_data_source}`;
  }
  if (r.job_id === "mootdx_bars_sync_job" && r.bar_data_source) {
    cond += ` · 日线源：${r.bar_data_source}`;
  }
  return prefix + cond;
}

function statusType(st: string) {
  if (st === "success") return "success";
  if (st === "failed") return "danger";
  if (st === "cancelled") return "warning";
  return "info";
}

function statusLabel(st: string) {
  const m: Record<string, string> = {
    success: "成功",
    failed: "失败",
    cancelled: "已停止",
    running: "运行中",
  };
  return m[st] || st;
}

async function loadJobs() {
  const r = await fetch("/instock/api/sync/jobs");
  const j = await r.json();
  if (j.ok && Array.isArray(j.jobs)) jobs.value = j.jobs;
}

async function loadPrefs() {
  const r = await fetch("/instock/api/sync/prefs");
  const j = await r.json();
  if (j.ok && j.prefs?.default_spot_data_source) {
    spotSource.value = j.prefs.default_spot_data_source;
  }
}

async function loadRuns() {
  const r = await fetch("/instock/api/sync/runs?limit=100");
  const j = await r.json();
  if (j.ok && Array.isArray(j.runs)) {
    runs.value = j.runs;
    const run = j.runs.find((x: RunRow) => x.status === "running");
    if (run && !trackingId.value) startPoll(run.id);
  }
}

async function loadBatches() {
  batchMsg.value = "加载中…";
  let url = "/instock/api/sync/data_batches?limit=80";
  if (batchDomain.value) url += `&domain_id=${encodeURIComponent(batchDomain.value)}`;
  const r = await fetch(url);
  const j = await r.json();
  if (!j.ok) {
    batchMsg.value = j.error || "失败";
    return;
  }
  batches.value = j.batches || [];
  batchMsg.value = `共 ${batches.value.length} 条`;
}

async function loadGovEnv() {
  const r = await fetch("/instock/api/sync/governance_env");
  const j = await r.json();
  if (j.ok) {
    govEnv.value = j.env || {};
    govHint.value = j.hint || "";
  }
}

async function loadDataSources() {
  dsLoading.value = true;
  dsMsg.value = "加载中…";
  try {
    const r = await fetch("/instock/api/sync/data_sources");
    const j = await r.json();
    if (!j.ok) {
      dsMsg.value = j.error || "失败";
      return;
    }
    dsReport.value = j;
    dsMsg.value = j.mootdx_installed ? "已加载" : "提示：容器内未安装 mootdx，在线源不可用";
  } catch (e) {
    dsMsg.value = String(e);
  } finally {
    dsLoading.value = false;
  }
}

function teardownEmProbe() {
  if (stopEmProbePoll) {
    stopEmProbePoll();
    stopEmProbePoll = null;
  }
}

function teardownMootdxProbe() {
  if (stopMootdxProbePoll) {
    stopMootdxProbePoll();
    stopMootdxProbePoll = null;
  }
}

async function runMootdxProbe(mode: "auto" | "local" | "online") {
  if (mootdxProbing.value) return;
  teardownMootdxProbe();
  mootdxProbing.value = true;
  mootdxProbeLogs.value = "";
  verifyMsg.value = `mootdx(${mode}) 后台探测中…`;
  try {
    const start = await startMootdxProbe(mode);
    if (!start.ok || !start.probe_id) {
      verifyMsg.value = start.error || "启动失败";
      mootdxProbing.value = false;
      return;
    }
    mootdxProbeId.value = start.probe_id;
    stopMootdxProbePoll = runMootdxProbePoll(start.probe_id, (snap) => {
      mootdxProbeLogs.value = (snap.logs || []).join("\n");
      if (!snap.done) return;
      mootdxProbing.value = false;
      teardownMootdxProbe();
      const res = snap.result || {};
      if (snap.status === "success" && res.ok) {
        const extra =
          res.universe_online != null
            ? `；在线列表约 ${res.universe_online} 只`
            : res.universe_scan != null
              ? `；本地扫描约 ${res.universe_scan} 只`
              : "";
        verifyMsg.value = `${res.provider_id || mode} OK：样本 ${res.rows} 行${extra}`;
        ElMessage.success("mootdx 可用");
      } else if (snap.status !== "cancelled") {
        verifyMsg.value = res.error || "mootdx 不可用";
        ElMessage.error(verifyMsg.value);
      } else {
        verifyMsg.value = "已取消 mootdx 探测";
      }
      void loadDataSources();
    });
  } catch (e) {
    verifyMsg.value = String(e);
    mootdxProbing.value = false;
    teardownMootdxProbe();
  }
}

async function verifyProvider(providerId: string) {
  if (providerId === "eastmoney") {
    if (emProbing.value) return;
    teardownEmProbe();
    emProbing.value = true;
    emProbeLogs.value = "";
    verifyMsg.value = "东财探测已在后台运行…";
    try {
      const start = await startEastmoneyProbe();
      if (!start.ok || !start.probe_id) {
        verifyMsg.value = start.error || "启动失败";
        emProbing.value = false;
        return;
      }
      emProbeId.value = start.probe_id;
      stopEmProbePoll = runEastmoneyProbePoll(start.probe_id, (snap) => {
        emProbeLogs.value = (snap.logs || []).join("\n");
        if (!snap.done) return;
        emProbing.value = false;
        teardownEmProbe();
        const res = snap.result || {};
        if (snap.status === "success" && res.ok) {
          const nodeHint =
            res.push2_preference === "auto"
              ? `auto→${res.push2_host || "—"}`
              : String(res.push2_host || res.push2_preference);
          verifyMsg.value = `东财 OK：${res.rows} 条 / 约 ${res.total} 只，${res.elapsed_ms}ms，节点 ${nodeHint}`;
          ElMessage.success("东财接口可用");
        } else {
          verifyMsg.value = res.error || "东财不可用";
          ElMessage.error(verifyMsg.value);
        }
        void loadDataSources();
      });
    } catch (e) {
      verifyMsg.value = String(e);
      emProbing.value = false;
      teardownEmProbe();
    }
    return;
  }
  if (providerId === "mootdx_local") {
    await runMootdxProbe("local");
    return;
  }
  if (providerId === "mootdx_online") {
    await runMootdxProbe("online");
    return;
  }
  verifyMsg.value = `检测 ${providerId}…`;
  try {
    const r = await fetch("/instock/api/sync/data_sources", {
      method: "POST",
      headers: { "Content-Type": "application/json;charset=UTF-8" },
      body: JSON.stringify({ provider_id: providerId, code: verifyCode.value.trim() || "600000" }),
    });
    const j = await r.json();
    if (j.ok && !j.async) {
      const tokenHint =
        providerId === "tushare" && j.token_source ? `，token=${j.token_source}` : "";
      verifyMsg.value = `${providerId}：样本 ${j.rows} 行，healthcheck=${j.healthcheck}${tokenHint}`;
      ElMessage.success(verifyMsg.value);
    } else {
      verifyMsg.value = j.error || "检测失败";
      ElMessage.error(verifyMsg.value);
    }
    await loadDataSources();
  } catch (e) {
    verifyMsg.value = String(e);
    ElMessage.error(verifyMsg.value);
  }
}

function chainRoleLabel(role: string) {
  return role === "enrich" ? "enrich" : "chain";
}

function initDhDates() {
  const t = new Date();
  const pad = (n: number) => (n < 10 ? "0" : "") + n;
  const iso = (d: Date) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  dhTo.value = iso(t);
  dhFrom.value = iso(new Date(t.getFullYear(), t.getMonth(), t.getDate() - 60));
}

async function runDh() {
  dhMsg.value = "检查中…";
  const url = `/instock/api/sync/data_health?from=${encodeURIComponent(dhFrom.value)}&to=${encodeURIComponent(dhTo.value)}`;
  const r = await fetch(url);
  const j = await r.json();
  if (!j.ok) {
    dhMsg.value = j.error || "失败";
    return;
  }
  dhMsg.value = `区间 ${j.date_from} ~ ${j.date_to}`;
  dhBtOk.value = j.backtest_prerequisites_ok;
  const miss = (j.missing_spot_trade_dates as string[]) || [];
  dhMissingCsv.value = miss.join(",");
  dhSummary.value = `应交易日 ${j.expected_trade_days} · 缺主表 ${miss.length} 天`;
  try {
    dhRemediation.value = JSON.stringify(
      { remediation: j.remediation, backtest: j.backtest_prerequisites },
      null,
      2
    );
  } catch {
    dhRemediation.value = "";
  }
}

function applyDhToManual() {
  if (!dhMissingCsv.value.trim()) {
    ElMessage.warning("无缺失日");
    return;
  }
  activeTab.value = "manual";
  jobId.value = "basic_data_daily_job";
  dateMode.value = "list";
  dateList.value = dhMissingCsv.value;
  runMsg.value = "已从回测检查填入缺日枚举";
}

async function pollOnce() {
  if (!trackingId.value) return;
  const r = await fetch(
    "/instock/api/sync/run_detail?id=" + encodeURIComponent(trackingId.value)
  );
  const j = await r.json();
  if (!j.ok || !j.run) return;
  const row = j.run as RunRow;
  runningLabel.value = row.label || row.job_id || "";
  const sec = Math.max(
    0,
    Math.floor((Date.now() - Date.parse(row.started_at.replace(" ", "T"))) / 1000)
  );
  const b = row.progress_bytes ?? 0;
  const ln = row.progress_lines ?? 0;
  const ec = row.error_line_count ?? 0;
  const hint = (row.progress_hint || "").trim();
  const cur = row.progress_current ?? 0;
  const tot = row.progress_total ?? 0;
  if (tot > 0 && cur > 0) {
    progressPercent.value = Math.min(100, Math.round((cur / tot) * 100));
    progressIndeterminate.value = false;
  } else {
    progressPercent.value = 0;
    progressIndeterminate.value = true;
  }
  progressText.value = [
    `已运行约 ${sec} 秒`,
    tot > 0 ? `进度 ${cur}/${tot}` : "",
    hint ? `当前：${hint.replace(/^\[PROGRESS\]\s*/i, "")}` : "",
    `输出 ${b} 字节 · ${ln} 行 · 异常行约 ${ec}`,
  ]
    .filter(Boolean)
    .join(" · ");
  liveOut.value = row.stdout_tail || "";
  const tail = (row.last_errors_tail || "").trim();
  liveErr.value = tail;
  showErrBox.value =
    !!tail &&
    (row.status === "running" || row.status === "failed" || row.status === "cancelled");
  if (row.status !== "running") {
    stopPoll();
    await loadRuns();
    activeTab.value = "runs";
    await showDetail(row.id);
    progressPanel.value = false;
    if (row.status === "cancelled") {
      ElMessage.warning(row.error_message || "任务已手动停止");
    } else if (row.status === "success") {
      ElMessage.success("任务已完成");
      void loadBatches();
    } else {
      ElMessage.error((row.error_message || "任务失败").slice(0, 200));
    }
  }
}

function startPoll(id: string) {
  stopPoll();
  trackingId.value = id;
  progressPanel.value = true;
  void pollOnce();
  pollTimer = setInterval(() => void pollOnce(), 1200);
}

function stopPoll() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
  trackingId.value = null;
}

async function showDetail(id: string) {
  detailId.value = id;
  const r = await fetch("/instock/api/sync/run_detail?id=" + encodeURIComponent(id));
  const j = await r.json();
  if (!j.ok) return;
  const row = j.run as RunRow;
  detailRun.value = row;
  const parts: string[] = [];
  if (row.error_message) parts.push("【退出摘要】\n" + row.error_message);
  if ((row.last_errors_tail || "").trim()) {
    parts.push("【日志异常相关行】\n" + (row.last_errors_tail || ""));
  }
  detailErr.value = parts.length ? parts.join("\n\n") : "（无）";
  detailOut.value = row.stdout_tail || "";
}

async function triggerRun() {
  let dm = dateMode.value;
  if (
    jobId.value === "init_job" ||
    jobId.value === "sync_trade_calendar_job" ||
    jobId.value === "sync_stock_universe_job"
  ) {
    dm = "default";
  }
  const payload: Record<string, string> = {
    job_id: jobId.value,
    date_mode: dm,
    date_start: dateStart.value.trim(),
    date_end: dateEnd.value.trim(),
    date_list: dateList.value.trim(),
  };
  if (jobId.value === "basic_data_daily_job") {
    payload.spot_data_source = spotSource.value;
  }
  if (jobId.value === "mootdx_bars_sync_job") {
    payload.bar_data_source = barSource.value;
  }
  const r = await fetch("/instock/api/sync/trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify(payload),
  });
  const j = await r.json();
  if (j.ok && j.run?.id) {
    runMsg.value = "已启动 " + j.run.id;
    startPoll(j.run.id);
    await loadRuns();
    await showDetail(j.run.id);
  } else runMsg.value = j.error || "失败";
}

async function cancelRun() {
  if (!trackingId.value) return;
  stopping.value = true;
  try {
    const r = await fetch("/instock/api/sync/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json;charset=UTF-8" },
      body: JSON.stringify({ run_id: trackingId.value }),
    });
    const j = await r.json();
    if (j.ok) await pollOnce();
  } finally {
    stopping.value = false;
  }
}

async function retryRun(id: string) {
  const r = await fetch("/instock/api/sync/retry", {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify({ run_id: id }),
  });
  const j = await r.json();
  if (j.ok && j.run?.id) {
    startPoll(j.run.id);
    await loadRuns();
  }
}

async function deleteRun(id: string) {
  if (!window.confirm("删除该执行记录及日志？")) return;
  const r = await fetch("/instock/api/sync/delete_run", {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify({ id }),
  });
  const j = await r.json();
  if (j.ok) {
    if (detailId.value === id) detailId.value = "";
    await loadRuns();
  }
}

async function loadScheduler() {
  const r = await fetch("/instock/api/sync/scheduler");
  const j = await r.json();
  if (j.ok) {
    schedGlobal.value = j.config?.enabled_globally !== false;
    schedDraft.value = JSON.parse(JSON.stringify(j.config?.schedules || []));
    schedMsg.value = "已加载";
  }
}

function addSched() {
  const title = schTitle.value.trim();
  const lines = schTimes.value.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
  if (!title || !lines.length) {
    ElMessage.warning("请填写名称与时刻");
    return;
  }
  schedDraft.value.push({
    id: "sched_" + Date.now(),
    title,
    enabled: true,
    job_id: schJobId.value,
    date_mode: "default",
    date_start: "",
    date_end: "",
    date_list: "",
    weekdays: schWeekdays.value.length ? [...schWeekdays.value] : [0, 1, 2, 3, 4],
    times: lines,
    spot_data_source: schSpot.value,
  });
  schedDraft.value = [...schedDraft.value];
}

function removeSched(i: number) {
  schedDraft.value.splice(i, 1);
  schedDraft.value = [...schedDraft.value];
}

async function saveScheduler() {
  const r = await fetch("/instock/api/sync/scheduler", {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify({
      enabled_globally: schedGlobal.value,
      schedules: schedDraft.value,
    }),
  });
  const j = await r.json();
  schedMsg.value = j.ok ? "已保存" : j.error || "失败";
}

function fmtJson(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

watch(activeTab, (t) => {
  if (route.query.tab !== t) {
    void router.replace({ query: { ...route.query, tab: t } });
  }
  if (t === "runs") void loadRuns();
  if (t === "lineage") {
    void loadBatches();
    void loadGovEnv();
  }
  if (t === "sources") void loadDataSources();
  if (t === "schedule") void loadScheduler();
});

watch(batchDomain, () => void loadBatches());

onMounted(async () => {
  document.documentElement.classList.add("dark");
  await loadJobs();
  await loadPrefs();
  await loadRuns();
  await loadScheduler();
  initDhDates();
  void loadGovEnv();
});

onUnmounted(() => {
  stopPoll();
  teardownEmProbe();
  teardownMootdxProbe();
});
</script>

<template>
  <PageShell
    title="任务中心"
    subtitle="管理定时任务、后台作业执行记录与数据血缘；Cookie 与快照偏好仍在「数据同步」页。"
  >
    <div class="job-page">
      <el-alert type="info" show-icon :closable="false" class="top-hint">
        <template #title>
          数据同步页负责 Cookie、缺口快检；本页负责
          <strong>定时 / 手动作业 / 执行记录 / data_batch 血缘</strong>。
          <el-button link type="primary" @click="router.push('/sync')">前往数据同步</el-button>
        </template>
      </el-alert>

      <el-card v-show="progressPanel || trackingId" shadow="never" class="progress-card">
        <template #header>
          <div class="card-head">
            <span>任务运行中{{ runningLabel ? ` · ${runningLabel}` : "" }}</span>
            <el-button
              type="danger"
              plain
              size="small"
              :icon="VideoPause"
              :disabled="!trackingId"
              :loading="stopping"
              @click="cancelRun"
            >
              停止任务
            </el-button>
          </div>
        </template>
        <el-progress
          :percentage="progressPercent"
          :indeterminate="progressIndeterminate"
          :stroke-width="8"
          status="warning"
        />
        <el-text class="progress-meta">{{ progressText }}</el-text>
        <el-alert v-show="showErrBox" type="error" :closable="false" class="mt">
          <pre class="log-pre err">{{ liveErr }}</pre>
        </el-alert>
        <el-text tag="b" class="mt">实时输出</el-text>
        <pre class="log-pre soft">{{ liveOut }}</pre>
      </el-card>

      <el-tabs v-model="activeTab" type="border-card" class="main-tabs">
        <el-tab-pane label="手动作业" name="manual">
          <el-form label-width="100px" class="mt">
            <el-form-item label="作业">
              <el-select v-model="jobId" filterable style="width: 100%; max-width: 480px">
                <el-option v-for="j in jobs" :key="j.id" :label="j.title" :value="j.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="快照源">
              <el-select v-model="spotSource" style="width: 240px" :disabled="jobId !== 'basic_data_daily_job'">
                <el-option label="东财" value="eastmoney" />
                <el-option label="Baostock" value="baostock" />
                <el-option label="东财→宝上" value="auto" />
              </el-select>
            </el-form-item>
            <el-form-item label="日线源">
              <el-select v-model="barSource" style="width: 280px" :disabled="jobId !== 'mootdx_bars_sync_job'">
                <el-option label="自动链路（mootdx → Tushare → 东财）" value="auto" />
                <el-option label="仅 mootdx" value="mootdx" />
                <el-option label="仅 Tushare" value="tushare" />
                <el-option label="仅东财" value="eastmoney" />
              </el-select>
              <el-text v-if="jobId === 'mootdx_bars_sync_job'" size="small" type="info" style="margin-left: 8px">
                选择 Tushare 时需容器已安装 tushare 包并配置 token。
              </el-text>
            </el-form-item>
            <el-form-item label="日期">
              <el-radio-group
                v-model="dateMode"
                :disabled="
                  jobId === 'init_job' ||
                  jobId === 'sync_trade_calendar_job' ||
                  jobId === 'sync_stock_universe_job'
                "
              >
                <el-radio-button label="default">默认</el-radio-button>
                <el-radio-button label="list" :disabled="jobId === 'mootdx_bars_sync_job'">
                  枚举
                </el-radio-button>
                <el-radio-button label="range">区间</el-radio-button>
              </el-radio-group>
              <el-text
                v-if="jobId === 'mootdx_bars_sync_job'"
                size="small"
                type="info"
                style="display: block; margin-top: 6px"
              >
                默认从约 3 年前拉至今；区间只需填开始日（结束可选）。请先跑「同步证券主表」。
              </el-text>
            </el-form-item>
            <el-form-item v-if="dateMode === 'list'" label="枚举">
              <el-input v-model="dateList" placeholder="2024-06-01,2024-06-03" />
            </el-form-item>
            <el-form-item v-if="dateMode === 'range'" label="区间">
              <el-space wrap>
                <el-date-picker
                  v-model="dateStart"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="开始"
                  style="width: 180px"
                />
                <el-date-picker
                  v-model="dateEnd"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="结束"
                  style="width: 180px"
                />
              </el-space>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="VideoPlay" :disabled="!!trackingId" @click="triggerRun">
                开始执行
              </el-button>
              <el-button
                type="danger"
                plain
                :icon="VideoPause"
                :disabled="!trackingId"
                :loading="stopping"
                @click="cancelRun"
              >
                停止
              </el-button>
              <el-text type="primary">{{ runMsg }}</el-text>
              <el-text
                v-if="trackingId"
                type="warning"
                size="small"
                style="display: block; margin-top: 6px"
              >
                进度与日志见上方「任务运行中」面板；切换 Tab 不会中断轮询
              </el-text>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="定时任务" name="schedule">
          <el-switch v-model="schedGlobal" active-text="启用定时总开关" class="mt" />
          <el-table :data="schedDraft" stripe border size="small" class="mt">
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }">
                <el-checkbox v-model="row.enabled" />
              </template>
            </el-table-column>
            <el-table-column prop="title" label="名称" min-width="120" />
            <el-table-column prop="job_id" label="作业" width="160" show-overflow-tooltip />
            <el-table-column label="星期" width="100">
              <template #default="{ row }">
                {{ (row.weekdays || []).map((n: number) => ["一","二","三","四","五","六","日"][n]).join("") }}
              </template>
            </el-table-column>
            <el-table-column label="时刻" min-width="120">
              <template #default="{ row }">{{ (row.times || []).join(", ") }}</template>
            </el-table-column>
            <el-table-column prop="spot_data_source" label="快照源" width="90" />
            <el-table-column label="操作" width="80">
              <template #default="{ $index }">
                <el-button link type="danger" @click="removeSched($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="sched-form mt">
            <el-input v-model="schTitle" placeholder="任务名称" style="width: 180px" />
            <el-select v-model="schJobId" style="width: 200px">
              <el-option v-for="j in jobs" :key="j.id" :label="j.title" :value="j.id" />
            </el-select>
            <el-select v-model="schSpot" style="width: 120px">
              <el-option label="东财" value="eastmoney" />
              <el-option label="宝上" value="baostock" />
              <el-option label="自动" value="auto" />
            </el-select>
            <el-button @click="addSched">加入</el-button>
            <el-button type="primary" @click="saveScheduler">保存配置</el-button>
          </div>
          <el-checkbox-group v-model="schWeekdays" size="small" class="mt">
            <el-checkbox v-for="o in wdOptions" :key="o.v" :value="o.v">周{{ o.l }}</el-checkbox>
          </el-checkbox-group>
          <el-input v-model="schTimes" type="textarea" :rows="2" placeholder="每行 HH:MM" class="mt mono" />
          <el-text size="small" type="info">{{ schedMsg }}</el-text>
        </el-tab-pane>

        <el-tab-pane label="执行记录" name="runs">
          <el-space class="mt">
            <el-button :icon="Refresh" size="small" @click="loadRuns">刷新</el-button>
          </el-space>
          <el-table :data="runs" stripe border size="small" max-height="400" class="mt">
            <el-table-column prop="started_at" label="开始" width="150" />
            <el-table-column prop="label" label="作业" width="110" />
            <el-table-column label="条件" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">{{ formatRunConditions(row) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="batch_ids" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.batch_ids?.length">{{ row.batch_ids.join(", ") }}</span>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="showDetail(row.id)">详情</el-button>
                <el-button link @click="retryRun(row.id)">重试</el-button>
                <el-button link type="danger" @click="deleteRun(row.id)">删</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-card v-if="detailId && detailRun" shadow="never" class="mt detail-card">
            <template #header>输出 · {{ detailId }}</template>
            <el-descriptions :column="2" size="small" border>
              <el-descriptions-item label="batch_ids" :span="2">
                {{ (detailRun.batch_ids || []).join(", ") || "—" }}
              </el-descriptions-item>
              <el-descriptions-item label="退出码">{{ detailRun.exit_code }}</el-descriptions-item>
              <el-descriptions-item label="结束">{{ detailRun.finished_at }}</el-descriptions-item>
            </el-descriptions>
            <pre class="log-pre err mt">{{ detailErr }}</pre>
            <pre class="log-pre soft">{{ detailOut }}</pre>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="数据源" name="sources">
          <el-space wrap class="mt">
            <el-button :icon="Refresh" :loading="dsLoading" @click="loadDataSources">刷新状态</el-button>
            <el-input v-model="verifyCode" placeholder="检测样本代码" style="width: 140px" class="mono" />
            <el-text size="small" type="info">{{ dsMsg }}</el-text>
          </el-space>

          <el-alert
            v-if="dsReport && !dsReport.registry_enabled_for_bars"
            type="warning"
            show-icon
            :closable="false"
            class="mt"
            title="K 线尚未走 Registry：请设置 INSTOCK_USE_DATA_REGISTRY=1 或 INSTOCK_BAR_MODE=raw 并重启容器"
          />

          <el-card v-if="dsReport" shadow="never" class="mt src-card">
            <template #header>
              <div class="card-head">
                <span>东方财富（A 股快照 / push2）</span>
                <el-button
                  size="small"
                  type="success"
                  plain
                  :loading="emProbing"
                  @click="verifyProvider('eastmoney')"
                >
                  测试东财接口
                </el-button>
              </div>
            </template>
            <el-text size="small" type="info">
              请求行情列表首屏（与定时作业同源）；push2 节点在「数据同步 → 同步与快照偏好」配置；Cookie 在同页下方。
            </el-text>
            <el-text v-if="dsReport?.eastmoney_push2" size="small" type="info" class="mt">
              当前节点偏好：{{ dsReport.eastmoney_push2.preference }}
              <template v-if="dsReport.eastmoney_push2.preference === 'auto'">
                （自动顺序 {{ (dsReport.eastmoney_push2.auto_order || []).join(" → ") }}）
              </template>
            </el-text>
          </el-card>

          <el-row :gutter="16" class="mt" v-if="dsReport">
            <el-col :span="8">
              <el-card shadow="never" class="src-card">
                <template #header>
                  <div class="card-head">
                    <span>mootdx_local（本地通达信）</span>
                    <el-button size="small" :loading="mootdxProbing" @click="verifyProvider('mootdx_local')">
                      连通性检测
                    </el-button>
                  </div>
                </template>
                <el-descriptions :column="1" size="small" border>
                  <el-descriptions-item label="INSTOCK_TDX_DIR">
                    {{ dsReport.mootdx_local?.INSTOCK_TDX_DIR || "（未配置）" }}
                  </el-descriptions-item>
                  <el-descriptions-item label="目录 / vipdoc">
                    {{ dsReport.mootdx_local?.dir_exists ? "存在" : "不存在" }} /
                    {{ dsReport.mootdx_local?.vipdoc_exists ? "存在" : "不存在" }}
                  </el-descriptions-item>
                  <el-descriptions-item label="healthcheck">
                    <el-tag :type="dsReport.mootdx_local?.healthcheck ? 'success' : 'danger'" size="small">
                      {{ dsReport.mootdx_local?.healthcheck ? "通过" : "失败" }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="样本 K 线">
                    {{ dsReport.mootdx_local?.sample_ok ? `${dsReport.mootdx_local?.sample_rows} 行` : (dsReport.mootdx_local?.sample_error || "—") }}
                  </el-descriptions-item>
                  <el-descriptions-item label="chain 中生效">
                    <el-tag :type="dsReport.mootdx_local?.active_in_chain ? 'success' : 'info'" size="small">
                      {{ dsReport.mootdx_local?.active_in_chain ? "是（K 线首选）" : "否" }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
                <el-text size="small" type="info">{{ dsReport.mootdx_local?.hint }}</el-text>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="never" class="src-card">
                <template #header>
                  <div class="card-head">
                    <span>mootdx_online（在线 fallback）</span>
                    <el-button size="small" :loading="mootdxProbing" @click="verifyProvider('mootdx_online')">
                      连通性检测
                    </el-button>
                  </div>
                </template>
                <el-descriptions :column="1" size="small" border>
                  <el-descriptions-item label="mootdx 包">
                    <el-tag :type="dsReport.mootdx_installed ? 'success' : 'danger'" size="small">
                      {{ dsReport.mootdx_installed ? "已安装" : "未安装" }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="healthcheck">
                    <el-tag :type="dsReport.mootdx_online?.healthcheck ? 'success' : 'danger'" size="small">
                      {{ dsReport.mootdx_online?.healthcheck ? "通过" : "失败" }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="样本 K 线">
                    {{ dsReport.mootdx_online?.sample_ok ? `${dsReport.mootdx_online?.sample_rows} 行` : (dsReport.mootdx_online?.sample_error || "—") }}
                  </el-descriptions-item>
                  <el-descriptions-item label="启用时机">
                    {{ dsReport.mootdx_online?.fallback_when }}
                  </el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="never" class="src-card">
                <template #header>
                  <div class="card-head">
                    <span>Tushare（日线 fallback）</span>
                    <el-button size="small" @click="verifyProvider('tushare')">
                      验证 token
                    </el-button>
                  </div>
                </template>
                <el-descriptions :column="1" size="small" border>
                  <el-descriptions-item label="Token">
                    <el-tag :type="dsReport.tushare?.token_configured ? 'success' : 'danger'" size="small">
                      {{ dsReport.tushare?.token_configured ? "已配置" : "未配置" }}
                    </el-tag>
                    <span class="muted mono">
                      {{ dsReport.tushare?.token_source || "TUSHARE_TOKEN / token 文件" }}
                    </span>
                  </el-descriptions-item>
                  <el-descriptions-item label="healthcheck">
                    <el-tag :type="dsReport.tushare?.healthcheck ? 'success' : 'danger'" size="small">
                      {{ dsReport.tushare?.healthcheck ? "通过" : "失败" }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="样本 K 线">
                    {{
                      dsReport.tushare?.sample_ok
                        ? `${dsReport.tushare?.sample_rows} 行`
                        : (dsReport.tushare?.sample_error || "—")
                    }}
                  </el-descriptions-item>
                  <el-descriptions-item label="chain 中生效">
                    <el-tag :type="dsReport.tushare?.active_in_chain ? 'success' : 'info'" size="small">
                      {{ dsReport.tushare?.active_in_chain ? "是（raw 日线回退）" : "否" }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
                <el-text size="small" type="info">{{ dsReport.tushare?.hint }}</el-text>
              </el-card>
            </el-col>
          </el-row>

          <el-card v-if="dsReport" shadow="never" class="mt inner">
            <template #header>
              daily_bar_raw 解析链（当前 profile={{ dsReport.profile }}）
            </template>
            <el-table
              :data="dsReport.domains?.daily_bar_raw?.profile_current || []"
              size="small"
              stripe
              border
            >
              <el-table-column prop="order" label="#" width="50" />
              <el-table-column prop="role" label="角色" width="80">
                <template #default="{ row }">{{ chainRoleLabel(row.role) }}</template>
              </el-table-column>
              <el-table-column prop="provider" label="provider" width="130" />
              <el-table-column prop="strict" label="strict" width="70" align="center">
                <template #default="{ row }">{{ row.strict ? "是" : "—" }}</template>
              </el-table-column>
              <el-table-column prop="when" label="when" width="120" />
              <el-table-column prop="fill_mode" label="fill_mode" min-width="100" />
            </el-table>
          </el-card>

          <el-card v-if="dsReport?.providers" shadow="never" class="mt inner">
            <template #header>全部 Provider 健康状态</template>
            <el-table :data="dsReport.providers" size="small" stripe border>
              <el-table-column prop="provider_id" label="ID" width="130" />
              <el-table-column label="加载" width="70" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.import_ok ? 'success' : 'danger'" size="small">
                    {{ row.import_ok ? "OK" : "—" }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="health" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.healthcheck ? 'success' : 'info'" size="small">
                    {{ row.healthcheck ? "通过" : "失败" }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="capabilities" label="capabilities" min-width="200">
                <template #default="{ row }">{{ (row.capabilities || []).join(", ") }}</template>
              </el-table-column>
              <el-table-column prop="error" label="error" min-width="120" show-overflow-tooltip />
            </el-table>
          </el-card>

          <el-card v-if="dsReport?.recent_bar_batches?.length" shadow="never" class="mt inner">
            <template #header>最近 daily_bar_raw 入库批次</template>
            <el-table :data="dsReport.recent_bar_batches" size="small" stripe border>
              <el-table-column prop="created_at" label="时间" width="155" />
              <el-table-column prop="source_provider" label="主源" width="110" />
              <el-table-column prop="scope_key" label="code" width="90" />
              <el-table-column prop="adjust_type" label="复权" width="70" />
              <el-table-column prop="status" label="状态" width="80" />
              <el-table-column prop="batch_id" label="batch_id" min-width="120" show-overflow-tooltip />
            </el-table>
          </el-card>

          <el-card v-if="dsReport?.management" shadow="never" class="mt inner">
            <template #header>Docker 配置参考（修改后需重启 InStock）</template>
            <el-text tag="p" size="small">environment 示例：</el-text>
            <pre class="log-pre soft mono">{{ (dsReport.management.docker_env || []).join("\n") }}</pre>
            <el-text tag="p" size="small" class="mt">volumes 示例：</el-text>
            <pre class="log-pre soft mono">{{ dsReport.management.docker_volume }}</pre>
            <el-text tag="p" size="small" class="mt">CLI 验证：</el-text>
            <pre class="log-pre soft mono">{{ (dsReport.management.verify_cli || []).join("\n") }}</pre>
            <el-text size="small" type="info">文档：{{ dsReport.management.doc }}</el-text>
          </el-card>
          <el-text v-if="verifyMsg" size="small" class="mt">{{ verifyMsg }}</el-text>
          <pre v-if="emProbeLogs || mootdxProbeLogs" class="log-pre soft mt">{{
            emProbeLogs || mootdxProbeLogs
          }}</pre>
        </el-tab-pane>

        <el-tab-pane label="数据血缘" name="lineage">
          <el-card shadow="never" class="mt inner">
            <template #header>当前治理环境（只读）</template>
            <el-descriptions :column="2" size="small" border>
              <el-descriptions-item
                v-for="(val, key) in govEnv"
                :key="key"
                :label="String(key)"
              >
                {{ val }}
              </el-descriptions-item>
            </el-descriptions>
            <el-text size="small" type="warning">{{ govHint }}</el-text>
          </el-card>

          <el-card shadow="never" class="mt inner">
            <template #header>回测主数据检查</template>
            <el-space wrap>
              <el-date-picker v-model="dhFrom" type="date" value-format="YYYY-MM-DD" />
              <el-date-picker v-model="dhTo" type="date" value-format="YYYY-MM-DD" />
              <el-button type="primary" @click="runDh">检查</el-button>
              <el-button @click="applyDhToManual">缺日填入手动作业</el-button>
            </el-space>
            <el-space class="mt">
              <el-tag v-if="dhBtOk === true" type="success">回测前置：通过</el-tag>
              <el-tag v-else-if="dhBtOk === false" type="danger">回测前置：未通过</el-tag>
              <el-text>{{ dhSummary }}</el-text>
            </el-space>
            <pre v-if="dhRemediation" class="log-pre soft mt">{{ dhRemediation }}</pre>
          </el-card>

          <el-card shadow="never" class="mt inner">
            <template #header>
              <div class="card-head">
                <span>data_batch 入库批次</span>
                <el-space>
                  <el-select v-model="batchDomain" style="width: 200px" clearable placeholder="域">
                    <el-option
                      v-for="o in domainOptions"
                      :key="o.value"
                      :label="o.label"
                      :value="o.value"
                    />
                  </el-select>
                  <el-button :icon="Refresh" size="small" @click="loadBatches">刷新</el-button>
                </el-space>
              </div>
            </template>
            <el-text size="small">{{ batchMsg }}</el-text>
            <el-table :data="batches" size="small" stripe border max-height="360" class="mt">
              <el-table-column prop="created_at" label="时间" width="155" />
              <el-table-column prop="domain_id" label="域" width="150" />
              <el-table-column prop="trade_date" label="交易日" width="110" />
              <el-table-column prop="source_provider" label="主源" width="100" />
              <el-table-column prop="adjust_type" label="复权" width="70" />
              <el-table-column prop="profile" label="profile" width="80" />
              <el-table-column prop="row_count" label="行数" width="70" />
              <el-table-column prop="status" label="状态" width="80" />
              <el-table-column prop="job_id" label="job" width="140" show-overflow-tooltip />
              <el-table-column label="batch_id" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">
                  <span class="mono">{{ row.batch_id }}</span>
                </template>
              </el-table-column>
              <el-table-column label="enrich" width="100" show-overflow-tooltip>
                <template #default="{ row }">{{ fmtJson(row.enrich_providers) }}</template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </div>
  </PageShell>
</template>

<style scoped>
.job-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.top-hint {
  margin-bottom: 4px;
}
.main-tabs {
  border-radius: 10px;
}
.mt {
  margin-top: 12px;
}
.inner {
  border: none;
  background: transparent;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.sched-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.mono {
  font-family: ui-monospace, Menlo, Monaco, monospace;
  font-size: 12px;
}
.muted {
  color: var(--el-text-color-secondary);
}
.src-card {
  border-radius: 8px;
  height: 100%;
}
.progress-card {
  border-radius: 10px;
  border: 1px solid var(--el-color-warning-light-5);
}
.progress-meta {
  display: block;
  margin-top: 8px;
  font-size: 13px;
}
.log-pre {
  margin-top: 8px;
  padding: 10px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow: auto;
  border-radius: 6px;
}
.log-pre.soft {
  background: #1e2430;
  color: #d8dee9;
}
.log-pre.err {
  background: #2a1e22;
  color: #f0d0d5;
}
.detail-card {
  border-radius: 8px;
}
</style>
