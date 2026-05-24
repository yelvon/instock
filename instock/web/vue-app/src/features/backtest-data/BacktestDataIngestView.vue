<script setup lang="ts">
import { useRouter } from "vue-router";
import MootdxLocalPanel from "@/features/mootdx/MootdxLocalPanel.vue";

const router = useRouter();

function onRunStarted() {
  void router.push({ path: "/jobs", query: { tab: "runs" } });
}
</script>

<template>
  <el-card shadow="never">
    <template #header>补数与同步</template>
    <p class="hint">
      通达信本地 vipdoc 写入标准表 <code>cn_stock_daily_bar</code>。全站作业编排仍在
      <el-button link type="primary" @click="router.push('/jobs')">任务中心</el-button>。
    </p>
    <MootdxLocalPanel :on-run-started="onRunStarted" />
  </el-card>
</template>

<style scoped>
.hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: #8b9cb3;
  line-height: 1.5;
}
</style>
