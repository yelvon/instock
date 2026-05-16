<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { Refresh, VideoPlay } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import PageShell from "@/components/ui/PageShell.vue";

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
  trigger_source?: string;
  schedule_title?: string;
  schedule_id?: string;
  progress_bytes?: number;
  progress_lines?: number;
  error_line_count?: number;
  last_errors_tail?: string;
  stdout_tail?: string;
  stderr_tail?: string;
  error_message?: string;
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

const jobs = ref<JobItem[]>([]);
const jobId = ref("basic_data_daily_job");
const dateMode = ref<"default" | "list" | "range">("default");
const dateList = ref("");
const dateStart = ref("");
const dateEnd = ref("");
const spotSource = ref("eastmoney");
const runMsg = ref("");
const runs = ref<RunRow[]>([]);
const detailId = ref("");
const detailErr = ref("");
const detailOut = ref("");
const detailErrTail = ref("");

const trackingId = ref<string | null>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const progressPanel = ref(false);
const progressText = ref("");
const liveOut = ref("");
const liveErr = ref("");
const showErrBox = ref(false);

const prefsMsg = ref("");

const dhFrom = ref("");
const dhTo = ref("");
const dhMsg = ref("");
const dhSummary = ref("");
const dhRemediation = ref("");
const dhDaily = ref<Record<string, unknown>[]>([]);
const dhMissingCsv = ref("");
const dhCli = ref("");

const cookiePath = ref("");
const cookieText = ref("");
const cookieMsg = ref("");

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

let prefsDebounce: ReturnType<typeof setTimeout> | null = null;

function formatRunConditions(r: RunRow): string {
  let prefix = "";
  if (r.trigger_source === "scheduler") {
    prefix = `【定时】${r.schedule_title || r.schedule_id || ""} · `;
  }
  if (r.job_id === "init_job" || r.job_id === "sync_trade_calendar_job") {
    return prefix + "默认（初始化/日历）";
  }
  const dm = (r.date_mode || "default").toLowerCase();
  let cond = "";
  if (dm === "default") cond = "默认";
  else if (dm === "list")
    cond = r.date_list?.trim() ? `枚举：${r.date_list}` : "枚举：（未填）";
  else if (dm === "range") {
    const ds = (r.date_start || "").trim();
    const de = (r.date_end || "").trim();
    cond = `区间：${ds || "—"} ~ ${de || "—"}`;
  } else cond = `模式：${dm}`;
  if (r.job_id === "basic_data_daily_job") {
    const s = (r.spot_data_source || "").toLowerCase();
    const lab: Record<string, string> = {
      eastmoney: "东财",
      baostock: "Baostock",
      auto: "东财→宝上",
    };
    if (s && lab[s]) cond += ` · 快照：${lab[s]}`;
    else if (s) cond += ` · 快照：${s}`;
  }
  return prefix + cond;
}

function statusType(
  st: string
): "success" | "warning" | "info" | "danger" | "primary" {
  if (st === "success") return "success";
  if (st === "failed") return "danger";
  if (st === "running") return "info";
  return "info";
}

async function loadJobs() {
  const r = await fetch("/instock/api/sync/jobs");
  const j = await r.json();
  if (j.ok && Array.isArray(j.jobs)) {
    jobs.value = j.jobs;
  }
}

async function loadPrefs() {
  try {
    const r = await fetch("/instock/api/sync/prefs");
    const j = await r.json();
    if (j.ok && j.prefs?.default_spot_data_source) {
      spotSource.value = j.prefs.default_spot_data_source;
      prefsMsg.value = "已从服务器加载快照偏好";
    }
  } catch {
    prefsMsg.value = "";
  }
}

watch(spotSource, () => {
  prefsMsg.value = "保存中…";
  if (prefsDebounce) clearTimeout(prefsDebounce);
  prefsDebounce = setTimeout(async () => {
    try {
      const r = await fetch("/instock/api/sync/prefs", {
        method: "POST",
        headers: { "Content-Type": "application/json;charset=UTF-8" },
        body: JSON.stringify({ default_spot_data_source: spotSource.value }),
      });
      const j = await r.json();
      prefsMsg.value = j.ok ? "偏好已保存" : j.error || "保存失败";
    } catch {
      prefsMsg.value = "保存失败";
    }
  }, 400);
});

async function loadRuns() {
  const r = await fetch("/instock/api/sync/runs?limit=80");
  const j = await r.json();
  if (j.ok && Array.isArray(j.runs)) {
    runs.value = j.runs;
    const run = j.runs.find((x: RunRow) => x.status === "running");
    if (run && !trackingId.value) {
      startPoll(run.id);
    }
  }
}

async function pollOnce() {
  if (!trackingId.value) return;
  const r = await fetch(
    "/instock/api/sync/run_detail?id=" + encodeURIComponent(trackingId.value)
  );
  const j = await r.json();
  if (!j.ok || !j.run) return;
  const row = j.run as RunRow;
  const sec = Math.max(
    0,
    Math.floor((Date.now() - Date.parse(row.started_at.replace(" ", "T"))) / 1000)
  );
  const b = row.progress_bytes ?? 0;
  const ln = row.progress_lines ?? 0;
  const ec = row.error_line_count ?? 0;
  progressText.value = `已运行约 ${sec} 秒 · 输出 ${b} 字节 · ${ln} 行 · 异常相关行约 ${ec}`;
  liveOut.value = row.stdout_tail || "";
  const tail = (row.last_errors_tail || "").trim();
  liveErr.value = tail;
  showErrBox.value =
    !!tail && (row.status === "running" || row.status === "failed");
  if (row.status !== "running") {
    stopPoll();
    await loadRuns();
    showDetail(row.id);
    progressPanel.value = false;
    ElMessage[row.status === "success" ? "success" : "warning"](
      row.status === "success" ? "任务已完成" : "任务已结束"
    );
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
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  trackingId.value = null;
}

async function showDetail(id: string) {
  detailId.value = id;
  const r = await fetch("/instock/api/sync/run_detail?id=" + encodeURIComponent(id));
  const j = await r.json();
  if (!j.ok) {
    detailErr.value = j.error || "";
    return;
  }
  const row = j.run as RunRow;
  const parts: string[] = [];
  if (row.error_message) parts.push("【退出摘要】\n" + row.error_message);
  if ((row.last_errors_tail || "").trim())
    parts.push("【日志异常相关行】\n" + (row.last_errors_tail || ""));
  detailErr.value = parts.length ? parts.join("\n\n") : "（无）";
  detailOut.value = row.stdout_tail || "";
  detailErrTail.value = row.stderr_tail || "";
}

async function triggerRun() {
  runMsg.value = "";
  let dm = dateMode.value;
  if (jobId.value === "init_job" || jobId.value === "sync_trade_calendar_job") {
    dm = "default";
  }
  const payload: Record<string, string> = {
    job_id: jobId.value,
    date_mode: dm,
    date_start: "",
    date_end: "",
    date_list: "",
  };
  if (jobId.value === "basic_data_daily_job") {
    payload.spot_data_source = spotSource.value || "eastmoney";
  }
  if (dm === "list") payload.date_list = dateList.value.trim();
  if (dm === "range") {
    payload.date_start = dateStart.value.trim();
    payload.date_end = dateEnd.value.trim();
  }
  try {
    const r = await fetch("/instock/api/sync/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json;charset=UTF-8" },
      body: JSON.stringify(payload),
    });
    const j = await r.json();
    if (j.ok && j.run?.id) {
      runMsg.value = "已启动：" + j.run.id;
      startPoll(j.run.id);
      await loadRuns();
      await showDetail(j.run.id);
    } else {
      runMsg.value = j.error || "失败";
    }
  } catch (e) {
    runMsg.value = String(e);
  }
}

async function retryRun(id: string) {
  try {
    const r = await fetch("/instock/api/sync/retry", {
      method: "POST",
      headers: { "Content-Type": "application/json;charset=UTF-8" },
      body: JSON.stringify({ run_id: id }),
    });
    const j = await r.json();
    if (j.ok && j.run?.id) {
      startPoll(j.run.id);
      await loadRuns();
      await showDetail(j.run.id);
    } else ElMessage.error(j.error || "重试失败");
  } catch {
    ElMessage.error("重试请求失败");
  }
}

async function deleteRun(id: string) {
  if (!window.confirm("确定删除这条记录？")) return;
  try {
    const r = await fetch("/instock/api/sync/delete_run", {
      method: "POST",
      headers: { "Content-Type": "application/json;charset=UTF-8" },
      body: JSON.stringify({ id }),
    });
    const j = await r.json();
    if (j.ok) {
      if (detailId.value === id) {
        detailId.value = "";
        detailErr.value = "";
        detailOut.value = "";
        detailErrTail.value = "";
      }
      await loadRuns();
    } else ElMessage.error(j.error || "删除失败");
  } catch {
    ElMessage.error("删除失败");
  }
}

async function loadCookie() {
  cookieMsg.value = "";
  const r = await fetch("/instock/api/sync/cookie");
  const j = await r.json();
  if (j.ok) {
    cookiePath.value = j.path || "";
    cookieText.value = j.content || "";
    cookieMsg.value = j.exists ? `已加载，约 ${j.bytes} 字节` : "文件不存在，可直接粘贴保存";
  } else cookieMsg.value = j.error || "读取失败";
}

async function saveCookie() {
  cookieMsg.value = "保存中…";
  const r = await fetch("/instock/api/sync/cookie", {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify({ cookie: cookieText.value }),
  });
  const j = await r.json();
  cookieMsg.value = j.ok ? j.message || "已保存" : j.error || "失败";
}

function initDhDates() {
  const t = new Date();
  const pad = (n: number) => (n < 10 ? "0" : "") + n;
  const iso = (d: Date) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  dhTo.value = iso(t);
  const f = new Date(t.getFullYear(), t.getMonth(), t.getDate() - 60);
  dhFrom.value = iso(f);
}

async function runDh() {
  dhMsg.value = "检查中…";
  let url = "/instock/api/sync/data_health";
  if (dhFrom.value.trim() && dhTo.value.trim()) {
    url += `?from=${encodeURIComponent(dhFrom.value.trim())}&to=${encodeURIComponent(dhTo.value.trim())}`;
  }
  const r = await fetch(url);
  const j = await r.json();
  if (!j.ok) {
    dhMsg.value = j.error || "失败";
    return;
  }
  dhMsg.value = `完成（区间 ${j.date_from} ~ ${j.date_to}）`;
  const miss = (j.missing_spot_trade_dates as string[]) || [];
  dhMissingCsv.value = miss.join(",");
  dhSummary.value = `应交易日 ${j.expected_trade_days} · 缺主表日数 ${miss.length}`;
  try {
    dhRemediation.value = JSON.stringify(j.remediation || [], null, 2);
  } catch {
    dhRemediation.value = "";
  }
  dhDaily.value = (j.daily as Record<string, unknown>[]) || [];
  const cli = j.cli_hints || {};
  dhCli.value = `${cli.validate || ""} ； ${cli.gaps || ""}`;
}

function applyDhToForm() {
  const csv = dhMissingCsv.value.trim();
  if (!csv) {
    ElMessage.warning("请先运行检查");
    return;
  }
  jobId.value = "basic_data_daily_job";
  dateMode.value = "list";
  dateList.value = csv;
  runMsg.value = "已填入枚举日期，请点击开始执行";
  document.getElementById("runner-anchor")?.scrollIntoView({ behavior: "smooth" });
}

function jobDesc(): string {
  const j = jobs.value.find((x) => x.id === jobId.value);
  return j?.description || "（无说明）";
}

async function loadScheduler() {
  const r = await fetch("/instock/api/sync/scheduler");
  const j = await r.json();
  if (!j.ok) {
    schedMsg.value = j.error || "加载失败";
    return;
  }
  schedGlobal.value = j.config?.enabled_globally !== false;
  schedDraft.value = JSON.parse(JSON.stringify(j.config?.schedules || []));
  schedMsg.value = "已加载定时配置";
}

function removeSched(i: number) {
  schedDraft.value.splice(i, 1);
  schedDraft.value = [...schedDraft.value];
}

function addSched() {
  const title = schTitle.value.trim();
  const lines = schTimes.value
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (!title) {
    ElMessage.warning("请填写名称");
    return;
  }
  if (!lines.length) {
    ElMessage.warning("请至少一行 HH:MM");
    return;
  }
  const wd =
    schWeekdays.value.length > 0 ? [...schWeekdays.value] : [0, 1, 2, 3, 4];
  schedDraft.value.push({
    id: "sched_" + Date.now(),
    title,
    enabled: true,
    job_id: schJobId.value,
    date_mode: "default",
    date_start: "",
    date_end: "",
    date_list: "",
    weekdays: wd,
    times: lines,
    spot_data_source: schSpot.value,
  });
  schTitle.value = "";
  schTimes.value = "";
  schedMsg.value = "已加入列表，请保存";
}

async function saveScheduler() {
  schedMsg.value = "保存中…";
  const r = await fetch("/instock/api/sync/scheduler", {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify({
      version: 1,
      enabled_globally: schedGlobal.value,
      schedules: schedDraft.value,
    }),
  });
  const j = await r.json();
  if (j.ok) {
    schedMsg.value = "已保存";
    schedDraft.value = JSON.parse(JSON.stringify(j.config?.schedules || []));
  } else schedMsg.value = j.error || "保存失败";
}

onMounted(async () => {
  document.documentElement.classList.add("dark");
  await loadJobs();
  await loadPrefs();
  await loadRuns();
  await loadCookie();
  await loadScheduler();
  initDhDates();
});

onUnmounted(() => stopPoll());
</script>

<template>
  <PageShell
    title="数据同步"
    subtitle="触发 instock/job 脚本；长任务自动轮询进度。定时任务在下方配置后由 Web 进程每分钟检查，执行记录中带「【定时】」前缀。"
  >
    <div class="sync-page">
    <el-card shadow="never" class="block">
      <template #header>
        <span>同步与快照偏好</span>
      </template>
      <el-form label-width="160px">
        <el-form-item label="默认快照数据源">
          <el-select v-model="spotSource" style="width: 320px">
            <el-option label="东方财富（默认）" value="eastmoney" />
            <el-option label="Baostock（宝上）" value="baostock" />
            <el-option label="东财优先，失败或空则 Baostock" value="auto" />
          </el-select>
        </el-form-item>
      </el-form>
      <el-text type="info" size="small">{{ prefsMsg }}</el-text>
    </el-card>

    <el-card shadow="never" class="block">
      <template #header>
        <span>应用内定时任务</span>
      </template>
      <el-switch
        v-model="schedGlobal"
        active-text="启用总开关"
        style="margin-bottom: 12px"
        @change="schedMsg = '请点保存使总开关生效'"
      />
      <el-table :data="schedDraft" stripe border size="small" class="sched-table">
        <el-table-column prop="enabled" label="启用" width="70" align="center">
          <template #default="{ row }">
            <el-checkbox v-model="row.enabled" />
          </template>
        </el-table-column>
        <el-table-column prop="title" label="名称" min-width="120" />
        <el-table-column prop="job_id" label="作业" width="160" show-overflow-tooltip />
        <el-table-column label="星期" width="100">
          <template #default="{ row }">
            {{ (row.weekdays || []).map((n: number) => ["一", "二", "三", "四", "五", "六", "日"][n]).join("") }}
          </template>
        </el-table-column>
        <el-table-column prop="times" label="时刻" min-width="140">
          <template #default="{ row }">{{ (row.times || []).join(", ") }}</template>
        </el-table-column>
        <el-table-column prop="spot_data_source" label="快照源" width="100" />
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ $index }">
            <el-button type="danger" link @click="removeSched($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="sched-form">
        <el-input v-model="schTitle" placeholder="名称" style="width: 200px" />
        <el-select v-model="schJobId" style="width: 200px" placeholder="作业">
          <el-option v-for="j in jobs" :key="j.id" :label="j.title" :value="j.id" />
        </el-select>
        <el-select v-model="schSpot" style="width: 160px">
          <el-option label="东财" value="eastmoney" />
          <el-option label="宝上" value="baostock" />
          <el-option label="东财→宝上" value="auto" />
        </el-select>
        <el-button @click="addSched">加入列表</el-button>
        <el-button type="primary" @click="saveScheduler">保存全部定时配置</el-button>
      </div>
      <div class="wd-line">
        <span class="wd-label">星期：</span>
        <el-checkbox-group v-model="schWeekdays" size="small">
          <el-checkbox v-for="o in wdOptions" :key="o.v" :value="o.v">周{{ o.l }}</el-checkbox>
        </el-checkbox-group>
      </div>
      <el-input
        v-model="schTimes"
        type="textarea"
        :rows="3"
        placeholder="每行一个 HH:MM，如 09:30"
        class="mono"
      />
      <el-text type="info" size="small" style="margin-top: 8px; display: block">{{
        schedMsg
      }}</el-text>
    </el-card>

    <el-card shadow="never" class="block">
      <template #header>
        <span>数据缺口自检</span>
      </template>
      <el-space wrap>
        <el-date-picker v-model="dhFrom" type="date" value-format="YYYY-MM-DD" placeholder="开始" />
        <el-date-picker v-model="dhTo" type="date" value-format="YYYY-MM-DD" placeholder="结束" />
        <el-button type="primary" @click="runDh">检查</el-button>
      </el-space>
      <el-alert :title="dhMsg" type="info" show-icon class="mt" v-if="dhMsg" />
      <el-text class="mt" v-if="dhSummary">{{ dhSummary }}</el-text>
      <pre v-if="dhRemediation" class="mono mt dh-rem">{{ dhRemediation }}</pre>
      <el-input v-model="dhMissingCsv" type="textarea" :rows="2" readonly class="mono mt" />
      <el-button class="mt" @click="applyDhToForm">填入快照枚举并跳到执行</el-button>
      <el-table :data="dhDaily" size="small" stripe border class="mt" max-height="220">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="stock_rows" label="股票行数" width="90" />
        <el-table-column prop="etf_rows" label="ETF行数" width="90" />
        <el-table-column prop="missing_spot" label="缺主表" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.missing_spot" type="danger" size="small">是</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="low_stock" label="股票偏低" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.low_stock" type="warning" size="small">是</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
      </el-table>
      <el-text size="small" class="mono mt">{{ dhCli }}</el-text>
    </el-card>

    <el-card shadow="never" class="block">
      <template #header>
        <span>东方财富 Cookie</span>
      </template>
      <el-text size="small" type="info">{{ cookiePath }}</el-text>
      <el-input v-model="cookieText" type="textarea" :rows="4" class="mono mt" />
      <el-space class="mt">
        <el-button @click="loadCookie">重新加载</el-button>
        <el-button type="primary" @click="saveCookie">保存</el-button>
        <el-text type="info">{{ cookieMsg }}</el-text>
      </el-space>
    </el-card>

    <el-card id="runner-anchor" shadow="never" class="block">
      <template #header>
        <span>手动执行作业</span>
      </template>
      <el-form label-width="100px">
        <el-form-item label="作业">
          <el-select v-model="jobId" filterable style="width: 100%; max-width: 520px">
            <el-option v-for="j in jobs" :key="j.id" :label="j.title" :value="j.id" />
          </el-select>
          <el-text size="small" type="info" style="display: block; margin-top: 6px">{{
            jobs.find((x) => x.id === jobId)?.hint
          }}</el-text>
        </el-form-item>
        <el-form-item label="说明">
          <el-text style="white-space: pre-wrap">{{ jobDesc() }}</el-text>
        </el-form-item>
        <el-form-item label="日期参数">
          <el-radio-group v-model="dateMode" :disabled="jobId === 'init_job' || jobId === 'sync_trade_calendar_job'">
            <el-radio-button label="default">默认</el-radio-button>
            <el-radio-button label="list">枚举</el-radio-button>
            <el-radio-button label="range">区间</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="dateMode === 'list'" label="枚举日期">
          <el-input v-model="dateList" placeholder="2024-06-01,2024-06-03" />
        </el-form-item>
        <el-form-item v-if="dateMode === 'range'" label="区间">
          <el-space>
            <el-input v-model="dateStart" placeholder="开始 YYYY-MM-DD" style="width: 180px" />
            <el-input v-model="dateEnd" placeholder="结束" style="width: 180px" />
          </el-space>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="VideoPlay" @click="triggerRun">开始执行</el-button>
          <el-text type="primary" style="margin-left: 12px">{{ runMsg }}</el-text>
        </el-form-item>
      </el-form>

      <el-collapse-transition>
        <div v-show="progressPanel" class="progress-box">
          <el-progress :indeterminate="true" :stroke-width="8" status="warning" />
          <el-text>{{ progressText }}</el-text>
          <el-alert v-show="showErrBox" type="error" :closable="false" class="mt">
            <pre class="log-pre">{{ liveErr }}</pre>
          </el-alert>
          <el-text tag="b">实时输出</el-text>
          <pre class="log-pre soft">{{ liveOut }}</pre>
        </div>
      </el-collapse-transition>
    </el-card>

    <el-card shadow="never" class="block">
      <template #header>
        <div class="card-head">
          <span>执行记录</span>
          <el-button :icon="Refresh" size="small" @click="loadRuns">刷新</el-button>
        </div>
      </template>
      <el-table :data="runs" stripe border size="small" max-height="360">
        <el-table-column prop="started_at" label="开始时间" width="155" />
        <el-table-column prop="label" label="作业" width="120" show-overflow-tooltip />
        <el-table-column label="条件" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ formatRunConditions(row) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.progress_bytes }} B / {{ row.progress_lines }} 行
          </template>
        </el-table-column>
        <el-table-column prop="exit_code" label="退出码" width="80" align="center" />
        <el-table-column prop="finished_at" label="结束时间" width="155" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="showDetail(row.id)">查看</el-button>
            <el-button link type="primary" @click="retryRun(row.id)">重试</el-button>
            <el-button link type="danger" @click="deleteRun(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="detailId" shadow="never" class="block">
      <template #header>
        <div class="card-head">
          <span>输出详情</span>
          <el-text size="small" type="info">{{ detailId }}</el-text>
        </div>
      </template>
      <el-text tag="b">错误摘要与线索</el-text>
      <pre class="log-pre err">{{ detailErr }}</pre>
      <el-row :gutter="16" class="mt">
        <el-col :span="12">
          <el-text tag="b">stdout 尾部</el-text>
          <pre class="log-pre soft">{{ detailOut }}</pre>
        </el-col>
        <el-col :span="12">
          <el-text tag="b">stderr 尾部</el-text>
          <pre class="log-pre err">{{ detailErrTail }}</pre>
        </el-col>
      </el-row>
    </el-card>
    </div>
  </PageShell>
</template>

<style scoped>
.sync-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
}
.lead {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.6;
}
.block {
  border-radius: 10px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.mt {
  margin-top: 12px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.sched-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0;
  align-items: center;
}
.sched-table {
  width: 100%;
}
.wd-line {
  margin: 8px 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.wd-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.wd-tag {
  margin-right: 4px;
}
.progress-box {
  margin-top: 16px;
  padding: 12px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
}
.log-pre {
  margin: 8px 0 0;
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow: auto;
}
.log-pre.soft {
  background: #1e2430;
  color: #d8dee9;
  border: 1px solid #2e3642;
}
.log-pre.err {
  background: #2a1e22;
  color: #f0d0d5;
  border: 1px solid #4a3036;
}
</style>
