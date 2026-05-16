<script setup lang="ts">
import { Loading } from "@element-plus/icons-vue";

defineProps<{
  text?: string;
}>();
</script>

<template>
  <div class="wrap">
    <el-icon class="spin"><Loading /></el-icon>
    <span>{{ text || "加载中…" }}</span>
  </div>
</template>

<style scoped>
.wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px;
  color: var(--el-text-color-secondary);
}
.spin {
  font-size: 22px;
  animation: rot 0.9s linear infinite;
}
@keyframes rot {
  to {
    transform: rotate(360deg);
  }
}
</style>
