<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  Coin,
  DataLine,
  Histogram,
  Download,
  Timer,
} from "@element-plus/icons-vue";
import PageShell from "@/components/ui/PageShell.vue";
import {
  goBacktestData,
  goBacktestRun,
  goGaps,
  goIngest,
  goOps,
} from "@/utils/navLinks";
import { listBacktestRuns, type BacktestRunListItem } from "@/api/backtest";

const router = useRouter();
const recentRuns = ref<BacktestRunListItem[]>([]);

const quickCards = [
  {
    title: "检查回测数据",
    desc: "缺口诊断与前置检查",
    icon: DataLine,
    action: () => goGaps(router),
  },
  {
    title: "补标准日线",
    desc: "通达信本地 / 多源补数",
    icon: Download,
    action: () => goIngest(router),
  },
  {
    title: "运行回测",
    desc: "策略配置与结果分析",
    icon: Histogram,
    action: () => goBacktestRun(router),
  },
  {
    title: "数据运维",
    desc: "同步、作业、执行记录",
    icon: Timer,
    action: () => goOps(router, "quick"),
  },
  {
    title: "准备数据概览",
    desc: "raw / qfq 标准库状态",
    icon: Coin,
    action: () => goBacktestData(router, "overview"),
  },
];

onMounted(async () => {
  try {
    recentRuns.value = (await listBacktestRuns()).slice(0, 3);
  } catch {
    recentRuns.value = [];
  }
});

function openRun(id: string) {
  goBacktestRun(router, id);
}
</script>

<template>
  <PageShell title="工作台" subtitle="常用入口与最近回测任务。">
    <el-row :gutter="12" class="quick-row">
      <el-col
        v-for="card in quickCards"
        :key="card.title"
        :xs="24"
        :sm="12"
        :md="8"
        :lg="8"
      >
        <el-card shadow="hover" class="quick-card" @click="card.action()">
          <div class="quick-inner">
            <el-icon class="quick-icon" :size="28"><component :is="card.icon" /></el-icon>
            <div>
              <div class="quick-title">{{ card.title }}</div>
              <div class="quick-desc">{{ card.desc }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="recentRuns.length" shadow="never" class="recent-card">
      <template #header>
        <span>最近回测</span>
      </template>
      <el-table :data="recentRuns" size="small" @row-click="(r) => openRun(r.id)">
        <el-table-column prop="title" label="任务" min-width="140" />
        <el-table-column prop="status" label="状态" width="90" />
        <el-table-column label="区间" min-width="160">
          <template #default="{ row }">{{ row.dateFrom }} ~ {{ row.dateTo }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-collapse class="help-collapse">
      <el-collapse-item title="ima 知识库" name="1">
          <ul class="links">
            <li>
              <a
                href="https://ima.qq.com/wiki/?shareId=8b0da768c77bc863f1cad8eb9482e37a6eeb26ad7171523b687d48c1a67c8e2c"
                target="_blank"
                rel="noopener noreferrer"
              >
                专业量化级股票因子池（ima 知识库）
              </a>
            </li>
          </ul>
        </el-collapse-item>
      <el-collapse-item title="一、综合选股" name="2">
          <pre class="doc">
综合选股支持股票范围、基本面、技术面、消息面、人气指标、行情数据等方面共 200 多个信息栏目进行自由组合选股。左侧菜单进入各数据表；完整说明见仓库 README。
          </pre>
        </el-collapse-item>
      <el-collapse-item title="二、股票每日数据" name="3">
          <pre class="doc">
包括每日股票数据、资金流向、龙虎榜、大宗交易、基本面、行业与概念资金流向、涨停原因、ETF 等。请在「数据运维」中运行对应作业生成表数据。
          </pre>
        </el-collapse-item>
      <el-collapse-item title="三、计算股票指标" name="4">
          <pre class="doc">
基于 TA-Lib、pandas 计算 MACD、KDJ、BOLL、RSI 等常用指标。在数据表中点击「代码」列可打开 K 线与指标副图页。
          </pre>
        </el-collapse-item>
      <el-collapse-item title="四～七、买卖信号、形态、筹码、策略" name="5">
          <pre class="doc">
系统支持指标买卖判定、K 线形态识别（60+ 形态）、筹码分布与多策略选股表。详细算法与字段含义见项目文档与左侧各数据模块。
          </pre>
        </el-collapse-item>
    </el-collapse>
  </PageShell>
</template>

<style scoped>
.quick-row {
  margin-bottom: 16px;
}
.quick-card {
  margin-bottom: 12px;
  cursor: pointer;
  border: 1px solid var(--el-border-color-lighter);
}
.quick-inner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.quick-icon {
  color: var(--el-color-primary);
  flex-shrink: 0;
}
.quick-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}
.quick-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
.recent-card {
  margin-bottom: 16px;
  border: 1px solid var(--el-border-color-lighter);
}
.help-collapse {
  margin-top: 8px;
}
.links {
  margin: 0;
  padding-left: 1.2rem;
}
.doc {
  margin: 0;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.55;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  padding: 12px;
  border-radius: 8px;
}
</style>
