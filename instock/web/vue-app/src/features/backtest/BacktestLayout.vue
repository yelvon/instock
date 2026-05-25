<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const tabs = [
  { path: "/backtest", label: "运行回测" },
  { path: "/backtest/guide", label: "自定义策略" },
];

const activeTab = computed(() =>
  route.path.startsWith("/backtest/guide") ? "/backtest/guide" : "/backtest"
);
</script>

<template>
  <div class="bt-layout">
    <div class="bt-head">
      <div>
        <h1 class="bt-title">策略回测</h1>
        <p class="bt-sub">
          日线事件驱动撮合：标准库 <code>cn_stock_daily_bar</code> · T+1 开盘成交 ·
          权益曲线与订单明细
        </p>
      </div>
      <el-space wrap>
        <el-button plain size="small" @click="router.push('/backtest-data/overview')">
          回测数据管理
        </el-button>
        <el-button type="primary" plain size="small" @click="router.push('/backtest-data/ingest')">
          去补数
        </el-button>
      </el-space>
    </div>
    <el-tabs
      :model-value="activeTab"
      class="bt-tabs"
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
.bt-layout {
  max-width: 1400px;
}
.bt-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}
.bt-title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 600;
  color: #e8eef5;
}
.bt-sub {
  margin: 0;
  font-size: 13px;
  color: #8b9cb3;
  line-height: 1.5;
}
.bt-sub code {
  font-size: 12px;
  color: #a8c4e8;
}
.bt-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}
</style>
