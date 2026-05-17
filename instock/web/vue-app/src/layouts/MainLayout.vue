<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  HomeFilled,
  Download,
  DataLine,
  Histogram,
  Timer,
} from "@element-plus/icons-vue";

const route = useRoute();
const router = useRouter();

interface NavItem {
  name: string;
  url: string;
}
interface NavGroup {
  type: string;
  ico: string;
  items: NavItem[];
}

const navGroups = ref<NavGroup[]>([]);

const menuActive = computed(() => {
  const p = route.path;
  if (p === "/" || p === "/home") return "/home";
  return p;
});

onMounted(async () => {
  try {
    const r = await fetch("/instock/api/nav");
    const j = await r.json();
    if (j.ok && Array.isArray(j.groups)) {
      navGroups.value = j.groups;
    }
  } catch {
    /* ignore */
  }
});

type SpaNavTarget =
  | string
  | { name: "table"; query?: { table_name: string } };

/** 将经典 /instock/data?... 转为 SPA 路由 */
function legacyUrlToSpaPath(url: string): SpaNavTarget | null {
  try {
    const u = new URL(url, window.location.origin);
    if (u.pathname === "/instock/data") {
      const tn = u.searchParams.get("table_name");
      if (tn) {
        return { name: "table", query: { table_name: tn } } as const;
      }
      return { name: "table" } as const;
    }
    if (u.pathname === "/instock/data/indicators") {
      const code = u.searchParams.get("code");
      const date = u.searchParams.get("date");
      const name = u.searchParams.get("name") || "";
      if (code && date) {
        const q = new URLSearchParams({ code, date });
        if (name) q.set("name", name);
        return `/indicators?${q.toString()}`;
      }
    }
  } catch {
    return null;
  }
  return null;
}

function onMenuSelect(index: string) {
  const spa = legacyUrlToSpaPath(index);
  if (spa) {
    void router.push(spa as Parameters<typeof router.push>[0]);
    return;
  }
  if (index === "/home" || index === "/") {
    void router.push("/home");
    return;
  }
  if (index === "/sync") {
    void router.push("/sync");
    return;
  }
  if (index === "/jobs") {
    void router.push("/jobs");
    return;
  }
  if (index === "/backtest") {
    void router.push("/backtest");
    return;
  }
  if (index.startsWith("http://") || index.startsWith("https://")) {
    window.open(index, "_blank", "noopener,noreferrer");
    return;
  }
}
</script>

<template>
  <el-container class="layout-root">
    <el-aside width="240px" class="aside">
      <div class="brand">
        <el-icon><DataLine /></el-icon>
        <span>InStock</span>
      </div>
      <el-scrollbar>
        <el-menu
          :default-active="menuActive"
          :router="false"
          class="side-menu"
          background-color="#0f1419"
          text-color="#c7d0dc"
          active-text-color="#79bbff"
          @select="onMenuSelect"
        >
          <el-menu-item index="/home">
            <el-icon><HomeFilled /></el-icon>
            <span>首页</span>
          </el-menu-item>
          <el-menu-item index="/sync">
            <el-icon><Download /></el-icon>
            <span>数据同步</span>
          </el-menu-item>
          <el-menu-item index="/jobs">
            <el-icon><Timer /></el-icon>
            <span>任务中心</span>
          </el-menu-item>
          <el-menu-item index="/backtest">
            <el-icon><Histogram /></el-icon>
            <span>回测（规划）</span>
          </el-menu-item>

          <el-sub-menu v-for="g in navGroups" :key="g.type" :index="'g:' + g.type">
            <template #title>
              <span>{{ g.type }}</span>
            </template>
            <el-menu-item v-for="it in g.items" :key="it.url" :index="it.url">
              {{ it.name }}
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-scrollbar>
    </el-aside>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.layout-root {
  min-height: 100vh;
  background: var(--el-bg-color-page);
}
.aside {
  background: #0f1419;
  border-right: 1px solid #1f2a36;
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 18px;
  font-weight: 600;
  font-size: 16px;
  color: #e8eef5;
  border-bottom: 1px solid #1f2a36;
}
.side-menu {
  border-right: none;
}
.main {
  padding: 16px 20px 32px;
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}
</style>
