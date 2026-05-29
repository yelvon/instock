<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

interface Crumb {
  label: string;
  to?: string;
}

const crumbs = computed((): Crumb[] => {
  const items: Crumb[] = [{ label: "InStock", to: "/home" }];
  const metaBc = route.meta.breadcrumb as string[] | undefined;
  if (metaBc?.length) {
    for (let i = 0; i < metaBc.length; i++) {
      const label = metaBc[i];
      const isLast = i === metaBc.length - 1;
      let to: string | undefined;
      if (!isLast) {
        if (i === 0 && label === "策略回测") to = "/backtest/run";
        else if (i === 0 && label === "数据运维") to = "/ops";
        else if (i === 0 && label === "准备数据") to = "/backtest/data/overview";
      }
      items.push({ label, to: isLast ? undefined : to });
    }
    return items;
  }
  const title = (route.meta.title as string) || "";
  if (title && route.path !== "/home") {
    items.push({ label: title });
  }
  return items;
});

function onCrumb(c: Crumb) {
  if (c.to) void router.push(c.to);
}
</script>

<template>
  <el-breadcrumb v-if="crumbs.length > 1" class="app-bc" separator="/">
    <el-breadcrumb-item v-for="(c, i) in crumbs" :key="i">
      <span
        v-if="c.to"
        class="bc-link"
        role="link"
        tabindex="0"
        @click="onCrumb(c)"
        @keydown.enter="onCrumb(c)"
      >
        {{ c.label }}
      </span>
      <span v-else>{{ c.label }}</span>
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<style scoped>
.app-bc {
  margin-bottom: 12px;
  font-size: 13px;
}
.bc-link {
  color: var(--el-color-primary);
  cursor: pointer;
}
.bc-link:hover {
  text-decoration: underline;
}
</style>
