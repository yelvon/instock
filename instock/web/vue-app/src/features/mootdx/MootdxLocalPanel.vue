<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Refresh, VideoPlay } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import HostOpsPanel from "@/features/host-ops/HostOpsPanel.vue";

interface MootdxLocalDetail {
  INSTOCK_TDX_DIR?: string;
  dir_exists?: boolean;
  vipdoc_exists?: boolean;
  lday_sh_count?: number;
  lday_sz_count?: number;
  healthcheck?: boolean;
  sample_ok?: boolean;
  sample_rows?: number;
  sample_error?: string | null;
  hint?: string;
}

interface CanonicalSummary {
  ready?: boolean;
  total_bars?: number;
  codes?: number;
  complete?: number;
  suspect?: number;
}

const props = defineProps<{
  onRunStarted?: (runId: string, label: string) => void;
}>();

const loading = ref(false);
const verifyLoading = ref(false);
const verifyMsg = ref("");
const local = ref<MootdxLocalDetail | null>(null);
const canonical = ref<CanonicalSummary | null>(null);

const barDateMode = ref<"default" | "week" | "range">("week");
const barDateStart = ref("");
const barDateEnd = ref("");
const barLimit = ref(0);
const deriveQfqAfter = ref(true);
const qfqMode = ref<"incremental" | "full">("incremental");

const ready = computed(
  () =>
    !!local.value?.dir_exists &&
    !!local.value?.vipdoc_exists &&
    !!local.value?.healthcheck
);

const statusType = computed(() => (ready.value ? "success" : "warning"));

async function loadStatus(force = false) {
  loading.value = true;
  verifyMsg.value = "";
  try {
    const qs = force ? "?scope=panel&refresh=1" : "?scope=panel";
    const r = await fetch(`/instock/api/sync/data_sources${qs}`);
    const j = await r.json();
    if (!j.ok) {
      verifyMsg.value = j.error || "加载失败";
      return;
    }
    local.value = j.mootdx_local || null;
    canonical.value = j.canonical || null;
  } catch (e) {
    verifyMsg.value = String(e);
  } finally {
    loading.value = false;
  }
}

async function verifyLocal() {
  verifyLoading.value = true;
  verifyMsg.value = "检测中…";
  try {
    const r = await fetch("/instock/api/sync/data_sources", {
      method: "POST",
      headers: { "Content-Type": "application/json;charset=UTF-8" },
      body: JSON.stringify({ provider_id: "mootdx_local", code: "600000" }),
    });
    const j = await r.json();
    if (j.ok) {
      verifyMsg.value = `本地通达信 OK，样本 ${j.rows ?? "?"} 行`;
      ElMessage.success(verifyMsg.value);
    } else {
      verifyMsg.value = j.error || "检测失败";
      ElMessage.error(verifyMsg.value);
    }
    await loadStatus(true);
  } catch (e) {
    verifyMsg.value = String(e);
    ElMessage.error(verifyMsg.value);
  } finally {
    verifyLoading.value = false;
  }
}

async function triggerJob(
  jobId: string,
  label: string,
  extra?: Record<string, string>
) {
  const payload: Record<string, unknown> = {
    job_id: jobId,
    date_mode: jobId.includes("bars") ? barDateMode.value : "default",
    date_start: barDateStart.value.trim(),
    date_end: barDateEnd.value.trim(),
  };
  if (extra && Object.keys(extra).length) payload.extra_env = extra;
  if (jobId.includes("bars")) {
    payload.derive_qfq_after = deriveQfqAfter.value;
    payload.qfq_mode = qfqMode.value;
  }
  if (barLimit.value > 0 && jobId.includes("bars")) {
    ElMessage.info("试跑 limit 请用命令行 --limit；页面将跑全市场");
  }
  try {
    const r = await fetch("/instock/api/sync/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json;charset=UTF-8" },
      body: JSON.stringify(payload),
    });
    const j = await r.json();
    if (!j.ok || !j.run?.id) {
      ElMessage.error(j.error || "启动失败");
      return;
    }
    ElMessage.success(`已启动：${label}`);
    props.onRunStarted?.(j.run.id, label);
  } catch (e) {
    ElMessage.error(String(e));
  }
}

async function applyMootdxPreset() {
  try {
    const r = await fetch("/instock/api/sync/prefs", {
      method: "POST",
      headers: { "Content-Type": "application/json;charset=UTF-8" },
      body: JSON.stringify({
        apply_preset: "mootdx_local",
        scheduler_mode: "merge",
      }),
    });
    const j = await r.json();
    if (!j.ok) {
      ElMessage.error(j.error || "应用预设失败");
      return;
    }
    ElMessage.success("已应用「通达信本地」预设（含默认定时模板）");
  } catch (e) {
    ElMessage.error(String(e));
  }
}

onMounted(() => void loadStatus());
</script>

<template>
  <div class="mootdx-panel">
    <el-alert :type="statusType" show-icon :closable="false" class="mb">
      <template #title>
        <template v-if="ready">通达信本地数据已就绪，可直接补标准库。</template>
        <template v-else>请先配置 Docker 挂载 INSTOCK_TDX_DIR（vipdoc），并在虚拟机内完成盘后下载。</template>
      </template>
      <template #default>
        回测读 <strong>cn_stock_daily_bar</strong>；本页作业默认<strong>只读本地 vipdoc</strong>，不依赖 Akshare/东财 K 线。
      </template>
    </el-alert>

    <el-alert
      type="warning"
      show-icon
      :closable="false"
      class="mb"
      title="Mac / Parallels SMB 挂载建议 workers=1"
      description="若补数出现 Errno 5 EIO，请在 docker/.env 设 INSTOCK_MOOTDX_LOCAL_WORKERS=1；复制 vipdoc 到 Docker 本地卷后可提高并发。"
    />
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never" class="inner">
          <template #header>
            <div class="card-head">
              <span>本地路径状态</span>
              <el-button :icon="Refresh" size="small" :loading="loading" @click="loadStatus(true)">
                刷新
              </el-button>
            </div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="INSTOCK_TDX_DIR">
              <span class="mono">{{ local?.INSTOCK_TDX_DIR || "（未配置）" }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="目录 / vipdoc">
              {{ local?.dir_exists ? "存在" : "不存在" }} /
              {{ local?.vipdoc_exists ? "存在" : "不存在" }}
            </el-descriptions-item>
            <el-descriptions-item label="日线文件数">
              沪 {{ local?.lday_sh_count ?? 0 }} · 深 {{ local?.lday_sz_count ?? 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="healthcheck">
              <el-tag :type="local?.healthcheck ? 'success' : 'danger'" size="small">
                {{ local?.healthcheck ? "通过" : "失败" }}
              </el-tag>
              <span v-if="local?.sample_ok" class="muted"> · 样本 {{ local?.sample_rows }} 行</span>
              <span v-else-if="local?.sample_error" class="err-text"> · {{ local.sample_error }}</span>
            </el-descriptions-item>
          </el-descriptions>
          <el-space class="mt">
            <el-button type="primary" :loading="verifyLoading" @click="verifyLocal">
              检测本地 600000
            </el-button>
            <el-button @click="applyMootdxPreset">应用「通达信本地」预设</el-button>
          </el-space>
          <el-text v-if="verifyMsg" size="small" type="info" class="mt block">{{ verifyMsg }}</el-text>
          <el-text size="small" type="info" class="mt block">{{ local?.hint }}</el-text>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" class="inner">
          <template #header>标准库概况</template>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="状态">
              <el-tag :type="canonical?.ready ? 'success' : 'info'" size="small">
                {{ canonical?.ready ? "有数据" : "空" }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="行数 / 证券">
              {{ canonical?.total_bars ?? 0 }} / {{ canonical?.codes ?? 0 }} 只
            </el-descriptions-item>
            <el-descriptions-item label="冲突 suspect">
              {{ canonical?.suspect ?? 0 }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="mt inner">
      <template #header>推荐流程（按顺序）</template>
      <el-steps :active="ready ? 2 : 0" align-center finish-status="success" class="mb">
        <el-step title="盘后下载" description="虚拟机通达信更新 vipdoc" />
        <el-step title="扫描代码表" description="本地 vipdoc → cn_stock_universe" />
        <el-step title="补标准日线 + 前复权" description="raw → qfq 派生" />
      </el-steps>

      <el-form label-width="110px" class="action-form">
        <el-form-item label="K 线日期">
          <el-radio-group v-model="barDateMode">
            <el-radio-button label="week">最近一周</el-radio-button>
            <el-radio-button label="default">约3年</el-radio-button>
            <el-radio-button label="range">区间</el-radio-button>
          </el-radio-group>
          <el-text size="small" type="info" style="display: block; margin-top: 6px">
            日常盘后补数建议「最近一周」；配合存量跳过只写缺日。首次入库或大范围补历史请选「约3年」或自定义区间。
          </el-text>
        </el-form-item>
        <el-form-item v-if="barDateMode === 'range'" label="区间">
          <el-date-picker
            v-model="barDateStart"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始"
            style="width: 150px"
          />
          <span class="muted px">~</span>
          <el-date-picker
            v-model="barDateEnd"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束（可空）"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item label="前复权">
          <el-checkbox v-model="deriveQfqAfter">补 raw 后自动派生前复权（同一任务）</el-checkbox>
          <el-radio-group
            v-model="qfqMode"
            :disabled="!deriveQfqAfter"
            style="margin-left: 12px"
          >
            <el-radio-button label="incremental">增量</el-radio-button>
            <el-radio-button label="full">全量</el-radio-button>
          </el-radio-group>
          <el-text size="small" type="info" style="display: block; margin-top: 6px">
            前复权派生范围与上方「补数日期」一致（如最近一周），不会从 2006 重跑全市场。
            qfq 表为空时首次会自动全历史派生。需已 ingest gbbq。
          </el-text>
        </el-form-item>
        <el-form-item label="操作">
          <el-space wrap>
            <el-button
              type="primary"
              :icon="VideoPlay"
              :disabled="!ready"
              @click="
                triggerJob('sync_stock_universe_job', '证券主表(本地扫描)', {
                  INSTOCK_UNIVERSE_SOURCE: 'local',
                })
              "
            >
              ① 同步证券主表（本地）
            </el-button>
            <el-button
              type="success"
              :icon="VideoPlay"
              :disabled="!ready"
              @click="triggerJob('sync_bars_mootdx_local_job', '标准库·本地 raw+qfq')"
            >
              ② 补标准日线 + 前复权
            </el-button>
            <el-button
              :icon="VideoPlay"
              :disabled="!ready"
              @click="triggerJob('sync_bars_mootdx_job', '标准库·本地→在线')"
            >
              ③ 补标准日线（含在线回退）
            </el-button>
          </el-space>
        </el-form-item>
      </el-form>
      <el-text size="small" type="info">
        Parallels 需保持虚拟机开机；盘后请在 Win 通达信执行「盘后数据下载」。试跑可加命令行
        <code>--limit 20</code>。
      </el-text>
    </el-card>

    <HostOpsPanel />
  </div>
</template>

<style scoped>
.mootdx-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.mb {
  margin-bottom: 12px;
}
.mt {
  margin-top: 12px;
}
.mt.block {
  display: block;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mono {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  word-break: break-all;
}
.muted {
  color: var(--el-text-color-secondary);
}
.px {
  padding: 0 8px;
}
.err-text {
  color: var(--el-color-danger);
}
.action-form {
  max-width: 900px;
}
</style>
