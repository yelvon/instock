<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  HomeFilled,
  DataLine,
  Histogram,
  Setting,
  Search,
} from "@element-plus/icons-vue";
import AppBreadcrumb from "@/components/ui/AppBreadcrumb.vue";
import { goOps } from "@/utils/navLinks";

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
const navFilter = ref("");

const filteredNavGroups = computed(() => {
  const q = navFilter.value.trim().toLowerCase();
  if (!q) return navGroups.value;
  return navGroups.value
    .map((g) => ({
      ...g,
      items: g.items.filter((it) => it.name.toLowerCase().includes(q)),
    }))
    .filter((g) => g.items.length > 0);
});

const menuActive = computed(() => {
  const p = route.path;
  if (p === "/" || p === "/home") return "/home";
  if (p.startsWith("/ops")) return "/ops";
  if (p.startsWith("/backtest/data")) return "/backtest/data/overview";
  if (p.startsWith("/backtest/run")) return "/backtest/run";
  if (p.startsWith("/backtest")) return "/backtest/run";
  if (route.name === "table") {
    const tn = route.query.table_name;
    if (typeof tn === "string" && tn) {
      for (const g of navGroups.value) {
        for (const it of g.items) {
          if (it.url.includes(`table_name=${tn}`)) return it.url;
        }
      }
    }
    return "/table";
  }
  if (route.name === "indicators") return route.fullPath;
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
  if (index === "/ops") {
    goOps(router, "quick");
    return;
  }
  if (index === "/backtest/data/overview") {
    void router.push("/backtest/data/overview");
    return;
  }
  if (index === "/backtest/run") {
    void router.push("/backtest/run");
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
          <div class="menu-group-title">工作台</div>
          <el-menu-item index="/home">
            <el-icon><HomeFilled /></el-icon>
            <span>首页</span>
          </el-menu-item>

          <div class="menu-group-title">数据运维</div>
          <el-menu-item index="/ops">
            <el-icon><Setting /></el-icon>
            <span>数据运维</span>
          </el-menu-item>

          <div class="menu-group-title">策略回测</div>
          <el-menu-item index="/backtest/data/overview">
            <el-icon><Histogram /></el-icon>
            <span>准备数据</span>
          </el-menu-item>
          <el-menu-item index="/backtest/run">
            <el-icon><Histogram /></el-icon>
            <span>运行回测</span>
          </el-menu-item>

          <div class="menu-group-title nav-browse-head">
            <span>数据浏览</span>
          </div>
          <div class="nav-search">
            <el-input
              v-model="navFilter"
              size="small"
              placeholder="筛选表名"
              clearable
              :prefix-icon="Search"
            />
          </div>
          <el-sub-menu
            v-for="g in filteredNavGroups"
            :key="g.type"
            :index="'g:' + g.type"
          >
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
      <AppBreadcrumb />
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
.menu-group-title {
  padding: 14px 20px 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #6b7c93;
}
.nav-browse-head {
  padding-top: 10px;
}
.nav-search {
  padding: 0 12px 8px;
}
.main {
  padding: 16px 20px 32px;
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}
</style>
