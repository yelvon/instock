<script setup lang="ts">
import PageShell from "@/components/ui/PageShell.vue";
</script>

<template>
  <PageShell title="InStock 股票系统" subtitle="数据抓取、指标计算、形态识别与策略选股。">
    <el-collapse>
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
包括每日股票数据、资金流向、龙虎榜、大宗交易、基本面、行业与概念资金流向、涨停原因、ETF 等。请在「数据同步」中运行对应作业生成表数据。
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
