<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { goBacktestData, goBacktestGuide, goBacktestRun } from "@/utils/navLinks";

const route = useRoute();
const router = useRouter();

const runId = computed(() => String(route.query.runId || ""));

const steps = [
  { title: "准备数据", path: "/backtest/data/overview" },
  { title: "运行回测", path: "/backtest/run" },
  { title: "查看结果", path: "/backtest/run" },
];

const activeStep = computed(() => {
  if (route.path.startsWith("/backtest/data")) return 0;
  if (route.path.startsWith("/backtest/guide")) return 1;
  if (runId.value) return 2;
  if (route.path.startsWith("/backtest/run")) return 1;
  return 1;
});

function onStepClick(idx: number) {
  const step = steps[idx];
  if (!step) return;
  if (idx === 2 && runId.value) {
    goBacktestRun(router, runId.value);
    return;
  }
  void router.push(step.path);
}
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
      <el-button link type="primary" @click="goBacktestGuide(router)">
        自定义策略
      </el-button>
    </div>
    <div class="bt-steps-row">
      <el-steps :active="activeStep" finish-status="success" simple class="bt-steps">
        <el-step
          v-for="(s, i) in steps"
          :key="s.title"
          :title="s.title"
          class="bt-step-click"
          @click="onStepClick(i)"
        />
      </el-steps>
    </div>
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
.bt-steps-row {
  margin-bottom: 12px;
}
.bt-steps {
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}
.bt-step-click {
  cursor: pointer;
}
</style>
