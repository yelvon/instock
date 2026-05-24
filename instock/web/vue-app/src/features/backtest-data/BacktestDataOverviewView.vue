<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Refresh } from "@element-plus/icons-vue";

interface CanonicalSummary {
  ready?: boolean;
  total_bars?: number;
  codes?: number;
  complete?: number;
  partial?: number;
  suspect?: number;
  by_primary_source?: { primary_source: string; c: number }[];
}

const router = useRouter();
const loading = ref(false);
const canonical = ref<CanonicalSummary | null>(null);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const r = await fetch("/instock/api/sync/canonical");
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
        <span>标准行情库 cn_stock_daily_bar</span>
        <el-button :icon="Refresh" size="small" @click="load">刷新</el-button>
      </div>
    </template>
    <el-alert v-if="error" type="error" :title="error" show-icon :closable="false" />
    <template v-else-if="canonical">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="状态">
          <el-tag :type="canonical.ready ? 'success' : 'info'" size="small">
            {{ canonical.ready ? "已就绪" : "空" }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="K 线条数">
          {{ (canonical.total_bars ?? 0).toLocaleString() }}
        </el-descriptions-item>
        <el-descriptions-item label="股票数">
          {{ canonical.codes ?? 0 }}
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
      </el-space>
    </template>
  </el-card>
</template>

<style scoped>
.row-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mt {
  margin-top: 16px;
}
</style>
