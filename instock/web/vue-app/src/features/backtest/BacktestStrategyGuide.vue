<script setup lang="ts">
import { ref, onMounted } from "vue";
import { listBacktestStrategies, type BacktestStrategyItem } from "@/api/backtest";

const strategies = ref<BacktestStrategyItem[]>([]);

onMounted(async () => {
  try {
    strategies.value = await listBacktestStrategies();
  } catch {
    strategies.value = [];
  }
});
</script>

<template>
  <el-card shadow="never" class="guide-card">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="回测策略在 Python 后端注册，Web 页会自动列出已注册策略。"
    />

    <h3 class="guide-h3">方式一：插件目录（推荐）</h3>
    <p class="guide-p">
      在仓库中新建文件（复制示例即可）：
      <code>instock/core/backtest/strategies/plugins/my_strategy.py</code>
    </p>
    <pre class="guide-pre">from instock.core.backtest.strategy import Strategy
from instock.core.backtest.registry import register

class MyStrategy(Strategy):
    strategy_id = "my_strategy"
    default_params = {"threshold": 0.02}

    def next(self, date: str) -> None:
        # 通过 self.cerebro.buy_target_weight / sell_all 下单
        ...

register(
    MyStrategy.strategy_id,
    MyStrategy,
    title="我的策略",
    description="简要说明",
    param_schema={"threshold": 0.02},
)</pre>
    <p class="guide-p muted">
      保存后<strong>重启 InStock 容器</strong>（或重载 Web 进程），在「运行回测」页的策略下拉框中应出现新项。
      示例文件 <code>example_hold.py</code> 默认未注册，需取消注释或复制改名。
    </p>

    <h3 class="guide-h3">方式二：环境变量加载外部模块</h3>
    <p class="guide-p">
      在 <code>docker/.env</code> 增加：
      <code>INSTOCK_STRATEGY_PLUGINS=your_package.your_module</code>（逗号分隔多个模块路径），模块末尾需调用
      <code>register(...)</code>。
    </p>

    <h3 class="guide-h3">方式三：内置策略包</h3>
    <p class="guide-p">
      在 <code>instock/core/backtest/strategies/</code> 新建模块，并在
      <code>registry.py</code> 的 <code>_register_builtins()</code> 中 import 后
      <code>register(...)</code>。
    </p>

    <h3 class="guide-h3">策略内可用 API（禁止访问 Web/数据库）</h3>
    <ul class="guide-ul">
      <li><code>self.cerebro.prepared[code]</code> — 该股历史 K 线 DataFrame</li>
      <li><code>self.cerebro.buy_target_weight(date, code, target_weight, reason=...)</code></li>
      <li><code>self.cerebro.sell_all(date, code, reason=...)</code></li>
      <li><code>self.cerebro.broker.get_position_qty(code)</code></li>
      <li><code>self.params</code> — 页面上传入的参数字典</li>
    </ul>

    <h3 class="guide-h3">本地验证</h3>
    <pre class="guide-pre">cd instock
PYTHONPATH=. python3 -m unittest tests.test_backtest_registry tests.test_backtest_service -v</pre>

    <h3 class="guide-h3">当前已注册策略</h3>
    <el-table v-if="strategies.length" :data="strategies" size="small" stripe>
      <el-table-column prop="id" label="id" width="180" />
      <el-table-column prop="title" label="名称" width="140" />
      <el-table-column prop="description" label="说明" min-width="200" />
      <el-table-column label="默认参数" min-width="160">
        <template #default="{ row }">
          <code class="inline-code">{{ JSON.stringify(row.paramSchema) }}</code>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="未能加载策略列表，请检查 API /instock/api/backtest/strategies" />

    <p class="guide-p muted">
      详细说明见仓库 <code>docs/plan/自定义回测策略.md</code>、<code>docs/plan/回测Backtrader式架构.md</code>。
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
.guide-p {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}
.guide-ul {
  margin: 0 0 12px;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.7;
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
.muted {
  color: var(--el-text-color-secondary);
}
code,
.inline-code {
  font-size: 12px;
  color: #79bbff;
}
</style>
