<script setup lang="ts">
defineProps<{
  message?: string;
}>();
</script>

<template>
  <el-empty :description="message || '暂无数据'" />
</template>
