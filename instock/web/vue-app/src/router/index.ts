import {
  createRouter,
  createWebHistory,
  type RouteLocationNormalized,
} from "vue-router";
import { queryClient } from "@/queryClient";
import { legacyJobInnerTab, normalizeOpsTab } from "@/utils/navLinks";

function titleFromRoute(to: RouteLocationNormalized): string {
  const m = to.meta?.title as string | undefined;
  if (m) return m;
  if (to.path.includes("/ops")) return "数据运维";
  if (to.path.includes("backtest-data")) return "回测数据管理";
  if (to.path.includes("/backtest/data")) return "准备数据";
  if (to.path.includes("backtest/guide")) return "自定义策略";
  if (to.path.includes("/backtest/run")) return "运行回测";
  if (to.path.includes("backtest")) return "策略回测";
  return "InStock";
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      component: () => import("@/layouts/MainLayout.vue"),
      children: [
        { path: "", redirect: "/home" },
        {
          path: "home",
          name: "home",
          component: () => import("@/features/home/HomeView.vue"),
          meta: { title: "首页", breadcrumb: ["工作台"] },
        },
        {
          path: "ops",
          name: "ops",
          component: () => import("@/views/DataOpsLayout.vue"),
          meta: { title: "数据运维", breadcrumb: ["数据运维"] },
        },
        {
          path: "sync",
          redirect: (to) => ({ path: "/ops", query: { ...to.query, tab: "quick" } }),
        },
        {
          path: "jobs",
          redirect: (to) => {
            const legacy = String(to.query.tab || "jobs");
            const tab = normalizeOpsTab(legacy);
            const inner = legacyJobInnerTab(legacy);
            const query: Record<string, string> = { ...to.query, tab } as Record<string, string>;
            if (inner && (tab === "jobs" || tab === "advanced")) {
              query.jobTab = inner;
            }
            return { path: "/ops", query };
          },
        },
        {
          path: "table",
          name: "table",
          component: () => import("@/features/table/DataTableView.vue"),
          meta: { title: "数据表", breadcrumb: ["数据浏览", "数据表"] },
        },
        {
          path: "indicators",
          name: "indicators",
          component: () => import("@/features/indicators/IndicatorsView.vue"),
          meta: { title: "股票指标", breadcrumb: ["数据浏览", "股票指标"] },
        },
        {
          path: "backtest-data",
          redirect: "/backtest/data/overview",
        },
        {
          path: "backtest-data/:tab",
          redirect: (to) => `/backtest/data/${String(to.params.tab)}`,
        },
        {
          path: "backtest",
          component: () => import("@/features/backtest/BacktestLayout.vue"),
          meta: { title: "策略回测" },
          redirect: "/backtest/run",
          children: [
            {
              path: "data",
              component: () => import("@/features/backtest-data/BacktestDataLayout.vue"),
              meta: { title: "准备数据" },
              redirect: "/backtest/data/overview",
              children: [
                {
                  path: "overview",
                  name: "backtest-data-overview",
                  component: () =>
                    import("@/features/backtest-data/BacktestDataOverviewView.vue"),
                  meta: {
                    title: "概览",
                    breadcrumb: ["策略回测", "准备数据", "概览"],
                  },
                },
                {
                  path: "bars",
                  name: "backtest-data-bars",
                  component: () =>
                    import("@/features/backtest-data/BacktestDataBarsView.vue"),
                  meta: {
                    title: "标准日线",
                    breadcrumb: ["策略回测", "准备数据", "标准日线"],
                  },
                },
                {
                  path: "ingest",
                  name: "backtest-data-ingest",
                  component: () =>
                    import("@/features/backtest-data/BacktestDataIngestView.vue"),
                  meta: {
                    title: "补数",
                    breadcrumb: ["策略回测", "准备数据", "补数"],
                  },
                },
                {
                  path: "gaps",
                  name: "backtest-data-gaps",
                  component: () =>
                    import("@/features/backtest-data/BacktestDataGapsView.vue"),
                  meta: {
                    title: "缺口诊断",
                    breadcrumb: ["策略回测", "准备数据", "缺口诊断"],
                  },
                },
              ],
            },
            {
              path: "run",
              name: "backtest-run",
              component: () => import("@/features/backtest/BacktestPlaceholderView.vue"),
              meta: {
                title: "运行回测",
                breadcrumb: ["策略回测", "运行回测"],
              },
            },
            {
              path: "guide",
              name: "backtest-guide",
              component: () => import("@/features/backtest/BacktestStrategyGuide.vue"),
              meta: {
                title: "自定义策略",
                breadcrumb: ["策略回测", "自定义策略"],
              },
            },
          ],
        },
      ],
    },
  ],
});

router.beforeEach((to, from, next) => {
  if (from.path.includes("/indicators")) {
    void queryClient.cancelQueries({ queryKey: ["klineBundle"] });
  }
  next();
});

router.afterEach((to) => {
  document.title = `${titleFromRoute(to)} · InStock`;
});

export default router;
