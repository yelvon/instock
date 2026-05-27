<script setup lang="ts">
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";

function todayIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const dateFrom = ref("2006-01-01");
const dateTo = ref(todayIso());
const adjustType = ref<"raw" | "qfq">("raw");
const codesText = ref("600000");

const adjustLabel = computed(() =>
  adjustType.value === "qfq" ? "前复权（qfq）" : "不复权（raw）"
);
const loading = ref(false);
const report = ref<{
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
} | null>(null);

async function runCheck() {
  loading.value = true;
  report.value = null;
  try {
    const codes = codesText.value
      .replace(/\n/g, ",")
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
    const qs = new URLSearchParams({
      from: dateFrom.value,
      to: dateTo.value,
      profile: "backtest",
      adjust_type: adjustType.value,
    });
    if (codes.length) qs.set("codes", codes.join(","));
    const r = await fetch(`/instock/api/sync/data_health?${qs.toString()}`);
    const j = await r.json();
    if (!j.ok) {
      ElMessage.error(j.error || "检查失败");
      return;
    }
    report.value = j;
    if (j.backtest_prerequisites_ok) {
      ElMessage.success(`${adjustLabel.value} 标准日线检查通过`);
    } else {
      ElMessage.warning(`${adjustLabel.value} 存在数据缺口`);
    }
  } catch (e) {
    ElMessage.error(String(e));
  } finally {
    loading.value = false;
  }
}

const canonDomain = () =>
  report.value?.backtest_prerequisites?.domains?.canonical_daily_bar;
</script>

<template>
  <el-card shadow="never">
    <template #header>缺口诊断（标准日线 · {{ adjustLabel }}）</template>
    <el-form label-position="top" size="small" class="form">
      <el-row :gutter="12">
        <el-col :span="6">
          <el-form-item label="开始日期">
            <el-date-picker
              v-model="dateFrom"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="2006-01-01"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="结束日期">
            <el-date-picker
              v-model="dateTo"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="今天"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="价格口径">
            <el-select v-model="adjustType" style="width: 100%">
              <el-option label="不复权 raw" value="raw" />
              <el-option label="前复权 qfq" value="qfq" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="股票代码（逗号分隔，可空=全市场按日）">
            <el-input v-model="codesText" placeholder="600000,000001" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-button type="primary" :loading="loading" @click="runCheck">检查</el-button>
    </el-form>

    <el-alert
      v-if="report?.backtest_prerequisites_ok"
      class="mt"
      type="success"
      show-icon
      :closable="false"
      :title="`${adjustLabel} 数据检查通过`"
    />
    <el-alert
      v-else-if="report && !report.backtest_prerequisites_ok"
      class="mt"
      type="warning"
      show-icon
      :closable="false"
      :title="`发现 ${adjustLabel} 数据缺口`"
    >
      <template #default>
        <div v-if="report.backtest_prerequisites?.messages?.length">
          {{ report.backtest_prerequisites.messages.join("；") }}
        </div>
        <div v-if="canonDomain()?.missing_trade_dates?.length" class="mt-mini">
          全市场缺交易日（前 12）：
          {{ canonDomain()!.missing_trade_dates!.slice(0, 12).join(", ") }}
          <span v-if="(canonDomain()!.missing_trade_dates!.length || 0) > 12">…</span>
        </div>
        <div
          v-for="(dates, code) in canonDomain()?.code_missing || {}"
          :key="code"
          class="mt-mini"
        >
          {{ code }} 缺 {{ dates.length }} 日（示例 {{ dates.slice(0, 5).join(", ") }}）
        </div>
        <p v-if="canonDomain()?.table" class="hint muted">检测表：{{ canonDomain()?.table }}</p>
        <p v-if="canonDomain()?.suggested_jobs?.length" class="hint muted">
          建议作业：{{ canonDomain()!.suggested_jobs!.join("、") }}
        </p>
        <p class="hint">
          {{
            adjustType === "qfq"
              ? "raw 不全请先「补数」；qfq 不全请在任务中心运行「派生前复权」或 ingest gbbq 后派生。"
              : "请到「补数」页执行通达信本地补标准日线（raw）。"
          }}
        </p>
      </template>
    </el-alert>
  </el-card>
</template>

<style scoped>
.form {
  max-width: 960px;
}
.mt {
  margin-top: 16px;
}
.mt-mini {
  margin-top: 8px;
  font-size: 13px;
}
.hint {
  margin-top: 8px;
  color: #8b9cb3;
  font-size: 12px;
}
.muted {
  color: var(--el-text-color-secondary);
}
</style>
