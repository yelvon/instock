<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const tabs = [
  { path: "/backtest-data/overview", label: "概览" },
  { path: "/backtest-data/bars", label: "标准日线" },
  { path: "/backtest-data/ingest", label: "补数" },
  { path: "/backtest-data/gaps", label: "缺口诊断" },
];

const activeTab = computed(() => route.path);
</script>

<template>
  <div class="btd-layout">
    <div class="btd-head">
      <div>
        <h1 class="btd-title">回测数据管理</h1>
        <p class="btd-sub">
          日线回测以 <code>cn_stock_daily_bar</code> 为准，与每日快照
          <code>cn_stock_spot</code> 独立。
        </p>
      </div>
      <el-button type="primary" plain size="small" @click="router.push('/backtest')">
        去运行回测
      </el-button>
    </div>
    <el-tabs
      :model-value="activeTab"
      class="btd-tabs"
      @tab-click="(pane: { paneName: string | number }) => router.push(String(pane.paneName))"
    >
      <el-tab-pane
        v-for="t in tabs"
        :key="t.path"
        :label="t.label"
        :name="t.path"
      />
    </el-tabs>
    <router-view />
  </div>
</template>

<style scoped>
.btd-layout {
  max-width: 1400px;
}
.btd-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}
.btd-title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 600;
  color: #e8eef5;
}
.btd-sub {
  margin: 0;
  font-size: 13px;
  color: #8b9cb3;
  line-height: 1.5;
}
.btd-sub code {
  font-size: 12px;
  color: #a8c4e8;
}
.btd-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}
</style>
