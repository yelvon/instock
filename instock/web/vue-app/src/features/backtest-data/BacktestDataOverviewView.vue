<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Refresh } from "@element-plus/icons-vue";

interface CanonicalSummary {
  ready?: boolean;
  total_bars?: number;
  codes?: number;
  qfq_total_bars?: number;
  qfq_codes?: number;
  complete?: number;
  partial?: number;
  suspect?: number;
  approximate?: boolean;
  codes_is_universe?: boolean;
  by_primary_source?: { primary_source: string; c: number }[];
}

const router = useRouter();
const loading = ref(false);
const canonical = ref<CanonicalSummary | null>(null);
const error = ref("");

async function load(exact = false) {
  loading.value = true;
  error.value = "";
  try {
    const qs = exact ? "?refresh=1" : "?light=1";
    const r = await fetch(`/instock/api/sync/canonical${qs}`);
    const j = await r.json();
    if (!j.ok) {
      error.value = j.error || "加载失败";
      return;
    }
    const { ok: _ok, ...rest } = j;
    canonical.value = rest as CanonicalSummary;
  } catch (e) {
    error.value = String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(() => void load());
</script>

<template>
  <el-card v-loading="loading" shadow="never">
    <template #header>
      <div class="row-head">
        <span>标准行情库（raw + qfq）</span>
        <el-button :icon="Refresh" size="small" @click="load(false)">刷新</el-button>
        <el-button size="small" @click="load(true)">精确统计</el-button>
      </div>
    </template>
    <el-alert v-if="error" type="error" :title="error" show-icon :closable="false" />
    <template v-else-if="canonical">
      <el-alert
        v-if="canonical.approximate"
        type="info"
        :closable="false"
        show-icon
        class="mb"
        title="当前为快速估算（约），行数来自库表统计；股票数/质量可能来自上次精确统计。需要准确数字请点「精确统计」（约 15 秒）。"
      />
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="状态">
          <el-tag :type="canonical.ready ? 'success' : 'info'" size="small">
            {{ canonical.ready ? "已就绪" : "空" }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="raw K 线 / 股票数">
          {{ (canonical.total_bars ?? 0).toLocaleString() }}{{ canonical.approximate ? "（约）" : "" }}
          /
          {{ canonical.codes ?? 0 }}{{ canonical.codes_is_universe ? "（主表）" : "" }}
        </el-descriptions-item>
        <el-descriptions-item label="qfq K 线 / 股票数">
          {{ (canonical.qfq_total_bars ?? 0).toLocaleString() }}{{ canonical.approximate ? "（约）" : "" }}
          /
          {{ canonical.qfq_codes ?? 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="质量 complete / partial / suspect">
          {{ canonical.complete ?? 0 }} / {{ canonical.partial ?? 0 }} /
          {{ canonical.suspect ?? 0 }}
        </el-descriptions-item>
      </el-descriptions>
      <el-table
        v-if="canonical.by_primary_source?.length"
        class="mt"
        :data="canonical.by_primary_source"
        size="small"
        stripe
      >
        <el-table-column prop="primary_source" label="主来源" />
        <el-table-column prop="c" label="行数" />
      </el-table>
      <el-space wrap class="mt">
        <el-button type="primary" @click="router.push('/backtest-data/bars')">
          浏览标准日线
        </el-button>
        <el-button @click="router.push('/backtest-data/ingest')">补数</el-button>
        <el-button @click="router.push('/backtest-data/gaps')">缺口诊断</el-button>
        <el-button @click="router.push('/jobs')">任务中心（派生 qfq）</el-button>
      </el-space>
      <el-alert
        class="mt"
        type="info"
        :closable="false"
        show-icon
        title="首次前复权请在任务中心运行「派生前复权」--mode full，或「一键：通达信本地+前复权」。raw 补数成功后可自动增量派生（INSTOCK_AUTO_DERIVE_QFQ=1）。"
      />
    </template>
  </el-card>
</template>

<style scoped>
.row-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mb {
  margin-bottom: 12px;
}
.mt {
  margin-top: 16px;
}
</style>
