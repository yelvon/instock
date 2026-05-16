<script setup lang="ts">
defineProps<{
  title: string;
  subtitle?: string;
}>();
</script>

<template>
  <div class="page-shell">
    <header class="page-shell__head">
      <h1 class="page-shell__title">{{ title }}</h1>
      <p v-if="subtitle" class="page-shell__sub">{{ subtitle }}</p>
    </header>
    <div class="page-shell__body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.page-shell {
  max-width: 1400px;
}
.page-shell__head {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color);
}
.page-shell__title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.page-shell__sub {
  margin: 8px 0 0;
  font-size: 0.875rem;
  color: var(--el-text-color-secondary);
}
.page-shell__body {
  min-height: 120px;
}
</style>
