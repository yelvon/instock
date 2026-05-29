<script setup lang="ts">
import { ref } from "vue";
import DataTableView, {
  type TableFiltersPayload,
} from "@/features/table/DataTableView.vue";
import CanonicalKlineChart from "@/features/charts/CanonicalKlineChart.vue";

const activePane = ref("table");
const chartFilters = ref<TableFiltersPayload>({
  code: "",
  dateFrom: "",
  dateTo: "",
  adjustType: "raw",
});

function onFiltersChange(f: TableFiltersPayload) {
  chartFilters.value = { ...f };
}
</script>

<template>
  <div class="bars-page">
    <el-tabs v-model="activePane" class="bars-tabs">
      <el-tab-pane label="表格" name="table">
        <DataTableView
          fixed-table-name="cn_stock_daily_bar"
          embedded
          default-view-mode="series"
          @filters-change="onFiltersChange"
        />
      </el-tab-pane>
      <el-tab-pane label="K 线" name="chart">
        <CanonicalKlineChart
          :code="chartFilters.code"
          :date-from="chartFilters.dateFrom"
          :date-to="chartFilters.dateTo"
          :adjust-type="chartFilters.adjustType"
          title="标准库 K 线"
          subtitle="数据来自 cn_stock_daily_bar（raw）/ cn_stock_daily_bar_qfq（前复权派生）"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.bars-page {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bars-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}
</style>
