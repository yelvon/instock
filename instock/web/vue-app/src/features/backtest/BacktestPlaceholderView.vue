<script setup lang="ts">
import PageShell from "@/components/ui/PageShell.vue";
</script>

<template>
  <PageShell
    title="策略回测（规划中）"
    subtitle="后端将提供任务列表、权益曲线、成交与持仓等 JSON；前端使用 AG Grid + lightweight-charts 展示。详见 docs/backtest-api-contract.md。"
  >
    <el-alert
      type="info"
      :closable="false"
      title="此模块尚未接入 Python 回测引擎（如 vectorbt / Backtrader）。路由与文档已预留，便于二期对接。"
    />
  </PageShell>
</template>
