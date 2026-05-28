<script setup lang="ts">
import { ref } from "vue";
import DataTableView, {
  type TableFiltersPayload,
} from "@/features/table/DataTableView.vue";
import CanonicalKlineChart from "@/features/charts/CanonicalKlineChart.vue";

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
    <DataTableView
      fixed-table-name="cn_stock_daily_bar"
      embedded
      default-view-mode="series"
      @filters-change="onFiltersChange"
    />
    <CanonicalKlineChart
      :code="chartFilters.code"
      :date-from="chartFilters.dateFrom"
      :date-to="chartFilters.dateTo"
      :adjust-type="chartFilters.adjustType"
      title="标准库 K 线"
      subtitle="数据来自 cn_stock_daily_bar（raw）/ cn_stock_daily_bar_qfq（前复权派生）"
    />
  </div>
</template>

<style scoped>
.bars-page {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
