<script setup lang="ts">
import DataTableView from "@/features/table/DataTableView.vue";
</script>

<template>
  <DataTableView
    fixed-table-name="cn_stock_daily_bar"
    embedded
    default-view-mode="cross_section"
  />
</template>
