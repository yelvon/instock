import {
  createRouter,
  createWebHistory,
  type RouteLocationNormalized,
} from "vue-router";
import { queryClient } from "@/queryClient";

function titleFromRoute(to: RouteLocationNormalized): string {
  const m = to.meta?.title as string | undefined;
  if (m) return m;
  if (to.path.includes("backtest")) return "回测";
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
          path: "backtest",
          component: () => import("@/features/backtest/BacktestLayout.vue"),
          meta: { title: "回测" },
          children: [
            {
              path: "",
              name: "backtest-index",
              component: () => import("@/features/backtest/BacktestPlaceholderView.vue"),
              meta: { title: "回测（规划中）" },
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
