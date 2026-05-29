<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageShell from "@/components/ui/PageShell.vue";
import SyncView from "@/views/SyncView.vue";
import JobCenterView from "@/views/JobCenterView.vue";
import type { OpsTab } from "@/utils/navLinks";
import { normalizeOpsTab } from "@/utils/navLinks";

const route = useRoute();
const router = useRouter();

const OPS_TABS: { name: OpsTab; label: string }[] = [
  { name: "quick", label: "快捷同步" },
  { name: "jobs", label: "作业与定时" },
  { name: "mootdx", label: "通达信本地" },
  { name: "runs", label: "执行记录" },
  { name: "advanced", label: "高级治理" },
];

const activeTab = computed({
  get: () => normalizeOpsTab(String(route.query.tab || "quick")),
  set: (tab: OpsTab) => {
    void router.replace({ path: "/ops", query: { tab } });
  },
});

watch(
  () => route.query.tab,
  (tab) => {
    if (!tab && route.path === "/ops") {
      void router.replace({ path: "/ops", query: { tab: "quick" } });
    }
  },
  { immediate: true }
);
</script>

<template>
  <PageShell
    title="数据运维"
    subtitle="Cookie 与快照偏好、手动作业、定时任务、通达信本地补数、执行记录与数据血缘。"
  >
    <el-tabs v-model="activeTab" type="border-card" class="ops-tabs">
      <el-tab-pane
        v-for="t in OPS_TABS"
        :key="t.name"
        :label="t.label"
        :name="t.name"
        lazy
      >
        <SyncView v-if="t.name === 'quick'" embedded />
        <JobCenterView v-else embedded :lock-tab="t.name" />
      </el-tab-pane>
    </el-tabs>
  </PageShell>
</template>

<style scoped>
.ops-tabs {
  border-radius: 10px;
}
.ops-tabs :deep(.el-tabs__content) {
  padding-top: 12px;
}
</style>
