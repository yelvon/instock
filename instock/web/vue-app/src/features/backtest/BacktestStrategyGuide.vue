<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { listBacktestStrategies, type BacktestStrategyItem } from "@/api/backtest";
import { CATEGORY_LABELS, groupedStrategies } from "@/utils/strategyForm";

const strategies = ref<BacktestStrategyItem[]>([]);
const groups = computed(() => groupedStrategies(strategies.value));

onMounted(async () => {
  try {
    strategies.value = await listBacktestStrategies();
  } catch {
    strategies.value = [];
  }
});

function categoryLabel(cat: string) {
  return CATEGORY_LABELS[cat] || cat;
}
</script>

<template>
  <el-card shadow="never" class="guide-card">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="回测策略在 Python 后端注册，Web 页会自动列出已注册策略。"
    />

    <h3 class="guide-h3">方式一：插件目录（推荐试验）</h3>
    <p class="guide-p">
      在仓库中新建文件（复制示例即可）：
      <code>instock/core/backtest/strategies/plugins/my_strategy.py</code>
    </p>
    <pre class="guide-pre">from instock.core.backtest.strategy import Strategy
from instock.core.backtest.registry import register
from instock.core.backtest.strategy_meta import ParamDef

class MyStrategy(Strategy):
    strategy_id = "my_strategy"
    default_params = {"threshold": 0.02}

    def next(self, date: str) -> None:
        ...

register(
    MyStrategy.strategy_id,
    MyStrategy,
    title="我的策略",
    description="简要说明",
    category="plugin",
    param_defs=[ParamDef("threshold", "阈值", "float", 0.02, min=0.001, max=1)],
)</pre>
    <p class="guide-p muted">
      保存后<strong>重启 InStock 容器</strong>（或重载 Web 进程），在「运行回测」页的策略下拉框中应出现新项。
    </p>

    <h3 class="guide-h3">方式二：内置策略目录（团队维护）</h3>
    <p class="guide-p">
      在 <code>instock/core/backtest/strategies/</code> 实现策略类，并在
      <code>builtins_catalog.py</code> 登记（含中文 title、category、ParamDef）。
      详见 <code>docs/plan/回测策略目录.md</code>。
    </p>

    <h3 class="guide-h3">当前已注册策略（{{ strategies.length }}）</h3>
    <template v-for="g in groups" :key="g.category">
      <h4 class="guide-h4">{{ g.label }}（{{ g.items.length }}）</h4>
      <el-table :data="g.items" size="small" stripe class="mb">
        <el-table-column prop="id" label="id" width="220" />
        <el-table-column prop="title" label="名称" width="140" />
        <el-table-column prop="description" label="说明" min-width="200" />
        <el-table-column label="参数" min-width="200">
          <template #default="{ row }">
            <span v-if="row.params?.length">
              {{ row.params.map((p: { label: string }) => p.label).join("、") }}
            </span>
            <code v-else class="inline-code">{{ JSON.stringify(row.paramSchema) }}</code>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.deprecated" type="info" size="small">已下线</el-tag>
            <el-tag v-else size="small" type="success">可用</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </template>
    <el-empty v-if="!strategies.length" description="未能加载策略列表，请检查 API /instock/api/backtest/strategies" />

    <p class="guide-p muted">
      详细说明见
      <code>docs/plan/回测策略目录.md</code>、
      <code>docs/plan/自定义回测策略.md</code>、
      <code>docs/plan/回测Backtrader式架构.md</code>。
    </p>
  </el-card>
</template>

<style scoped>
.guide-card {
  border: 1px solid var(--el-border-color-lighter);
}
.guide-h3 {
  margin: 20px 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.guide-h3:first-of-type {
  margin-top: 12px;
}
.guide-h4 {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 600;
}
.guide-p {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}
.guide-pre {
  margin: 8px 0 12px;
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--el-fill-color-darker);
  color: #c5d4e8;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
}
.mb {
  margin-bottom: 12px;
}
.muted {
  color: var(--el-text-color-secondary);
}
code,
.inline-code {
  font-size: 12px;
  color: #79bbff;
}
</style>
