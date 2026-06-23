export type GuideStepStatus = "done" | "todo" | "blocked" | "warning";

export interface LocalDataStatus {
  dir_exists?: boolean;
  vipdoc_exists?: boolean;
  healthcheck?: boolean;
}

export interface CanonicalStatus {
  total_bars?: number;
  qfq_total_bars?: number;
  suspect?: number;
}

export interface GuideStep {
  id: string;
  title: string;
  description: string;
  status: GuideStepStatus;
}

export interface GuideAction {
  id: string;
  label: string;
  target: "configure" | "ingest" | "qfq" | "gaps" | "backtest";
}

export interface MaintenanceGuide {
  readyForBacktest: boolean;
  qualityWarning: string;
  nextAction?: GuideAction;
  steps: GuideStep[];
}

function hasLocalVipdoc(local?: LocalDataStatus | null): boolean {
  return !!local?.dir_exists && !!local?.vipdoc_exists && !!local?.healthcheck;
}

function count(v: unknown): number {
  const n = Number(v || 0);
  return Number.isFinite(n) ? n : 0;
}

export function buildMaintenanceGuide(
  local?: LocalDataStatus | null,
  canonical?: CanonicalStatus | null
): MaintenanceGuide {
  const localReady = hasLocalVipdoc(local);
  const rawRows = count(canonical?.total_bars);
  const qfqRows = count(canonical?.qfq_total_bars);
  const suspectRows = count(canonical?.suspect);
  const rawReady = rawRows > 0;
  const qfqReady = qfqRows > 0;
  const qualityWarning = suspectRows > 0 ? `存在 ${suspectRows} 行 suspect，请回测前重点检查。` : "";

  const steps: GuideStep[] = [
    {
      id: "local",
      title: "本地通达信",
      description: "确认 INSTOCK_TDX_DIR、vipdoc 和样本日线可读。",
      status: localReady ? "done" : "blocked",
    },
    {
      id: "raw",
      title: "raw 标准日线",
      description: "写入 cn_stock_daily_bar，作为回测主数据。",
      status: rawReady ? "done" : localReady ? "todo" : "blocked",
    },
    {
      id: "qfq",
      title: "前复权 qfq",
      description: "由 raw + gbbq 派生 cn_stock_daily_bar_qfq。",
      status: qfqReady ? "done" : rawReady ? "todo" : "blocked",
    },
    {
      id: "verify",
      title: "缺口与质量复检",
      description: "检查目标区间、股票和复权口径是否可回测。",
      status: rawReady && qfqReady ? (suspectRows ? "warning" : "done") : "todo",
    },
  ];

  let nextAction: GuideAction | undefined;
  if (!localReady) {
    nextAction = { id: "configure_tdx", label: "检查通达信挂载", target: "configure" };
  } else if (!rawReady) {
    nextAction = { id: "ingest_raw", label: "补 raw 标准日线", target: "ingest" };
  } else if (!qfqReady) {
    nextAction = { id: "derive_qfq", label: "派生 qfq", target: "qfq" };
  } else if (suspectRows > 0) {
    nextAction = { id: "check_gaps", label: "复检缺口与质量", target: "gaps" };
  } else {
    nextAction = { id: "run_backtest", label: "运行回测", target: "backtest" };
  }

  return {
    readyForBacktest: rawReady,
    qualityWarning,
    nextAction,
    steps,
  };
}
