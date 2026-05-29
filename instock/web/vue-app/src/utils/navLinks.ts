import type { Router } from "vue-router";

export type OpsTab = "quick" | "jobs" | "mootdx" | "runs" | "advanced";
export type BacktestDataTab = "overview" | "bars" | "ingest" | "gaps";

const OPS_TAB_SET = new Set<OpsTab>(["quick", "jobs", "mootdx", "runs", "advanced"]);

/** 将旧任务中心 tab 名或 /ops?tab= 归一化为数据运维顶层 Tab */
export function normalizeOpsTab(tab: string | undefined | null): OpsTab {
  const t = String(tab || "").toLowerCase();
  const map: Record<string, OpsTab> = {
    quick: "quick",
    jobs: "jobs",
    manual: "jobs",
    schedule: "jobs",
    mootdx: "mootdx",
    runs: "runs",
    advanced: "advanced",
    lineage: "advanced",
    sources: "advanced",
    governance: "advanced",
  };
  const mapped = map[t];
  if (mapped) return mapped;
  return OPS_TAB_SET.has(t as OpsTab) ? (t as OpsTab) : "quick";
}

/** /jobs?tab=manual|schedule|… 保留内层 JobCenter 子 Tab */
export function legacyJobInnerTab(tab: string | undefined | null): string | undefined {
  const t = String(tab || "").toLowerCase();
  if (["manual", "schedule", "mootdx", "runs", "sources", "lineage", "governance"].includes(t)) {
    return t;
  }
  return undefined;
}

export function goHome(router: Router) {
  void router.push("/home");
}

export function goOps(router: Router, tab: OpsTab = "quick") {
  void router.push({ path: "/ops", query: { tab } });
}

export function goSync(router: Router) {
  goOps(router, "quick");
}

export function goJobs(router: Router, tab: OpsTab = "jobs") {
  goOps(router, tab);
}

export function goBacktestData(router: Router, tab: BacktestDataTab = "overview") {
  void router.push(`/backtest/data/${tab}`);
}

export function goBacktestRun(router: Router, runId?: string) {
  void router.push({
    path: "/backtest/run",
    query: runId ? { runId } : {},
  });
}

export function goRunBacktest(router: Router) {
  goBacktestRun(router);
}

export function goIngest(router: Router) {
  goBacktestData(router, "ingest");
}

export function goGaps(router: Router) {
  goBacktestData(router, "gaps");
}

export function goBars(router: Router) {
  goBacktestData(router, "bars");
}

export function goBacktestGuide(router: Router) {
  void router.push("/backtest/guide");
}
