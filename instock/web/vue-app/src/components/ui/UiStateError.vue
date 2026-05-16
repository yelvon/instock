<script setup lang="ts">
defineProps<{
  message: string;
}>();
</script>

<template>
  <el-alert type="error" :closable="false" show-icon :title="message" />
</template>
