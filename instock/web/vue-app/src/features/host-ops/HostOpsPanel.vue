<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { ElMessage } from "element-plus";

interface HostOpsStatus {
  ready?: boolean;
  inside_docker?: boolean;
  host_reachable?: boolean;
  host_ops_url?: string | null;
  start_hint?: string;
  repo_root?: string;
  runner_version?: number;
}

interface HostRun {
  id?: string;
  task_id?: string;
  title?: string;
  status?: string;
  created_at?: string;
  finished_at?: string;
  exit_code?: number | null;
  progress_hint?: string;
  stdout_tail?: string;
}

const status = ref<HostOpsStatus | null>(null);
const activeRun = ref<HostRun | null>(null);
const logText = ref("");
const triggering = ref(false);
const reloadRecreate = ref(false);
const reloadPip = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const startCmd = computed(() => {
  const root = status.value?.repo_root || "/Users/fwj/stock/instock";
  return `cd ${root} && python3 scripts/host_ops_server.py`;
});

async function loadStatus() {
  try {
    const r = await fetch("/instock/api/host_ops/status");
    const j = await r.json();
    status.value = j;
  } catch {
    status.value = { ready: false };
  }
}

async function pollRun(id: string) {
  try {
    const r = await fetch(`/instock/api/host_ops/run_detail?id=${encodeURIComponent(id)}`);
    const j = await r.json();
    if (!j.ok || !j.run) return;
    activeRun.value = j.run;
    logText.value = String(j.run.stdout_tail || "");
    if (j.run.status === "running") return;
    stopPoll();
    if (j.run.status === "success") {
      ElMessage.success(`${j.run.title || "任务"} 完成`);
    } else if (j.run.status === "failed") {
      ElMessage.error(`${j.run.title || "任务"} 失败（退出码 ${j.run.exit_code ?? "?"}）`);
    }
  } catch {
    /* ignore */
  }
}

function startPoll(id: string) {
  stopPoll();
  void pollRun(id);
  pollTimer = setInterval(() => void pollRun(id), 1000);
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function triggerTask(taskId: string, options?: Record<string, unknown>, label?: string) {
  if (!status.value?.ready) {
    ElMessage.warning("请先启动宿主机运维服务（见下方说明）");
    return;
  }
  triggering.value = true;
  logText.value = "";
  try {
    const r = await fetch("/instock/api/host_ops/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json;charset=UTF-8" },
      body: JSON.stringify({ task_id: taskId, options: options || {} }),
    });
    const j = await r.json();
    if (!j.ok || !j.run?.id) {
      ElMessage.error(j.error || "启动失败");
      return;
    }
    ElMessage.success(`已启动：${label || j.run.title || taskId}`);
    startPoll(j.run.id);
  } catch (e) {
    ElMessage.error(String(e));
  } finally {
    triggering.value = false;
  }
}

async function cancelActive() {
  if (!activeRun.value?.id) return;
  await fetch("/instock/api/host_ops/cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify({ id: activeRun.value.id }),
  });
  ElMessage.info("已请求取消");
}

function copyStartCmd() {
  void navigator.clipboard.writeText(startCmd.value);
  ElMessage.success("已复制启动命令");
}

onMounted(() => void loadStatus());
onUnmounted(() => stopPoll());
</script>

<template>
  <el-card shadow="never" class="host-ops">
    <template #header>
      <div class="head">
        <span>Mac 宿主机运维</span>
        <el-button size="small" @click="loadStatus">刷新状态</el-button>
      </div>
    </template>

    <el-alert
      v-if="status && !status.ready"
      type="warning"
      show-icon
      :closable="false"
      title="宿主机服务未连接"
      class="mb"
    >
      <template #default>
        <p>页面内按钮需在 Mac 上运行一次运维服务（容器内 Web 无法直接执行 docker / prlctl）。</p>
        <p class="mono cmd">{{ startCmd }}</p>
        <el-button size="small" type="primary" @click="copyStartCmd">复制命令</el-button>
        <el-button size="small" @click="loadStatus">我已启动，再检测</el-button>
      </template>
    </el-alert>
    <el-alert
      v-else-if="status?.ready"
      type="success"
      show-icon
      :closable="false"
      class="mb"
    >
      <template #title>
        {{ status.host_reachable ? "已连接宿主机运维服务" : "本机直接执行模式" }}
        <span v-if="status.runner_version && status.runner_version < 3" class="warn-ver">
          （服务版本旧，请重启 host_ops_server）
        </span>
      </template>
    </el-alert>

    <el-space wrap class="mb">
      <el-button
        :loading="triggering"
        :disabled="!status?.ready"
        @click="triggerTask('tdx_sync', {}, '通达信 vipdoc 同步')"
      >
        同步 vipdoc → ~/tdx-local
      </el-button>
      <el-button
        type="primary"
        :loading="triggering"
        :disabled="!status?.ready"
        @click="
          triggerTask(
            'docker_dev_reload_backend',
            { recreate: reloadRecreate, pip: reloadPip },
            '重启后端'
          )
        "
      >
        重启后端（快）
      </el-button>
      <el-button
        :loading="triggering"
        :disabled="!status?.ready"
        @click="
          triggerTask(
            'docker_dev_reload_full',
            { pip: reloadPip },
            '全量重建'
          )
        "
      >
        全量重建（含 npm）
      </el-button>
      <el-button
        v-if="activeRun?.status === 'running'"
        type="danger"
        plain
        size="small"
        @click="cancelActive"
      >
        取消
      </el-button>
    </el-space>

    <el-form inline size="small" class="opts">
      <el-checkbox v-model="reloadRecreate">
        后端模式：重建容器（改 docker/.env 或 TDX 挂载时用，否则仅 restart）
      </el-checkbox>
      <el-checkbox v-model="reloadPip">pip 全量依赖（--pip）</el-checkbox>
    </el-form>

    <div v-if="activeRun" class="run-meta">
      <el-tag :type="activeRun.status === 'running' ? 'warning' : activeRun.status === 'success' ? 'success' : 'danger'" size="small">
        {{ activeRun.status }}
      </el-tag>
      <span class="muted">{{ activeRun.title }}</span>
      <span v-if="activeRun.progress_hint" class="muted"> · {{ activeRun.progress_hint }}</span>
    </div>

    <el-input
      v-model="logText"
      type="textarea"
      :rows="14"
      readonly
      placeholder="任务日志将显示在这里…"
      class="log-area"
    />
  </el-card>
</template>

<style scoped>
.host-ops {
  margin-top: 16px;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mb {
  margin-bottom: 12px;
}
.opts {
  margin-bottom: 12px;
}
.cmd {
  font-size: 12px;
  margin: 8px 0;
  word-break: break-all;
}
.run-meta {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.muted {
  color: #8b9cb3;
  font-size: 13px;
}
.log-area :deep(textarea) {
  font-family: ui-monospace, Menlo, monospace;
  font-size: 12px;
}
.warn-ver {
  color: #e6a23c;
  font-size: 12px;
  font-weight: normal;
}
</style>
