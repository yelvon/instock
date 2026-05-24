<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";

const dateFrom = ref("2024-01-01");
const dateTo = ref("2026-05-22");
const codesText = ref("600000");
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
      ElMessage.success("标准日线前置检查通过");
    } else {
      ElMessage.warning("存在数据缺口");
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
    <template #header>缺口诊断（标准日线）</template>
    <el-form label-position="top" size="small" class="form">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="开始日期">
            <el-input v-model="dateFrom" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="结束日期">
            <el-input v-model="dateTo" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
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
      title="回测前置数据检查通过"
    />
    <el-alert
      v-else-if="report && !report.backtest_prerequisites_ok"
      class="mt"
      type="warning"
      show-icon
      :closable="false"
      title="发现回测数据缺口"
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
        <p class="hint">请到「补数」页执行通达信本地补标准日线。</p>
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
</style>
