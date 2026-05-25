import {
  createRouter,
  createWebHistory,
  type RouteLocationNormalized,
} from "vue-router";
import { queryClient } from "@/queryClient";

function titleFromRoute(to: RouteLocationNormalized): string {
  const m = to.meta?.title as string | undefined;
  if (m) return m;
  if (to.path.includes("backtest-data")) return "回测数据管理";
  if (to.path.includes("backtest/guide")) return "自定义策略";
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
          meta: { title: "首页" },
        },
        {
          path: "sync",
          name: "sync",
          component: () => import("@/views/SyncView.vue"),
          meta: { title: "数据同步" },
        },
        {
          path: "jobs",
          name: "jobs",
          component: () => import("@/views/JobCenterView.vue"),
          meta: { title: "任务中心" },
        },
        {
          path: "table",
          name: "table",
          component: () => import("@/features/table/DataTableView.vue"),
          meta: { title: "数据表" },
        },
        {
          path: "indicators",
          name: "indicators",
          component: () => import("@/features/indicators/IndicatorsView.vue"),
          meta: { title: "股票指标" },
        },
        {
          path: "backtest-data",
          component: () => import("@/features/backtest-data/BacktestDataLayout.vue"),
          meta: { title: "回测数据管理" },
          redirect: "/backtest-data/overview",
          children: [
            {
              path: "overview",
              name: "backtest-data-overview",
              component: () =>
                import("@/features/backtest-data/BacktestDataOverviewView.vue"),
              meta: { title: "概览" },
            },
            {
              path: "bars",
              name: "backtest-data-bars",
              component: () =>
                import("@/features/backtest-data/BacktestDataBarsView.vue"),
              meta: { title: "标准日线" },
            },
            {
              path: "ingest",
              name: "backtest-data-ingest",
              component: () =>
                import("@/features/backtest-data/BacktestDataIngestView.vue"),
              meta: { title: "补数" },
            },
            {
              path: "gaps",
              name: "backtest-data-gaps",
              component: () =>
                import("@/features/backtest-data/BacktestDataGapsView.vue"),
              meta: { title: "缺口诊断" },
            },
          ],
        },
        {
          path: "backtest",
          component: () => import("@/features/backtest/BacktestLayout.vue"),
          meta: { title: "回测" },
          children: [
            {
              path: "",
              name: "backtest-index",
              component: () => import("@/features/backtest/BacktestPlaceholderView.vue"),
              meta: { title: "运行回测" },
            },
            {
              path: "guide",
              name: "backtest-guide",
              component: () => import("@/features/backtest/BacktestStrategyGuide.vue"),
              meta: { title: "自定义策略" },
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
