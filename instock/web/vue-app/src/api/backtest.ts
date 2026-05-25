import { $api } from "@/api/client";

export interface BacktestRunListItem {
  id: string;
  title: string;
  status: "queued" | "running" | "success" | "failed" | "cancelled";
  createdAt?: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  dateFrom?: string;
  dateTo?: string;
  strategy?: string;
  universe?: { type: string; codes: string[] };
  progress?: {
    currentDate?: string;
    processedDays?: number;
    totalDays?: number;
    message?: string;
  };
  summary?: {
    totalReturn?: number;
    annualReturn?: number;
    maxDrawdown?: number;
    sharpe?: number;
    tradeCount?: number;
  };
  error?: { code?: string; message?: string } | string | null;
}

export interface BacktestRunDetail extends BacktestRunListItem {
  ok: boolean;
  params?: Record<string, unknown>;
  lineage?: Record<string, unknown>;
  metrics?: Record<string, number>;
  equity?: {
    time: string[];
    value: number[];
    totalAssets?: number[];
    dailyReturn?: number[];
  };
  benchmark?: { name?: string; time: string[]; value: number[] };
  drawdown?: { time: string[]; value: number[]; totalAssets?: number[] };
  orders?: Record<string, unknown>[];
  trades?: Record<string, unknown>[];
  positions?: Record<string, unknown>[];
  dailyAccounts?: Record<string, unknown>[];
}

export interface BacktestCreatePayload {
  title: string;
  dateFrom: string;
  dateTo: string;
  universe: { type: "codes"; codes: string[] };
  strategy: { id: string; params: Record<string, number | string | boolean> };
  broker: {
    initialCash: number;
    matchPrice: string;
    commissionRate: number;
    minCommission: number;
    stampTaxRate: number;
    slippageBps: number;
  };
  risk: {
    maxPositions: number;
    maxWeightPerSymbol: number;
    maxGrossExposure: number;
  };
  data: {
    profile: string;
    priceMode: string;
    requirePrerequisites: boolean;
  };
}

export interface BacktestStrategyItem {
  id: string;
  title: string;
  description: string;
  paramSchema: Record<string, number | string | boolean>;
}

export async function listBacktestStrategies(): Promise<BacktestStrategyItem[]> {
  const res = await $api<{ ok: boolean; strategies: BacktestStrategyItem[] }>(
    "/instock/api/backtest/strategies"
  );
  return res.strategies || [];
}

export async function listBacktestRuns(): Promise<BacktestRunListItem[]> {
  const res = await $api<{ ok: boolean; items: BacktestRunListItem[] }>(
    "/instock/api/backtest/runs"
  );
  return res.items || [];
}

export async function createBacktestRun(payload: BacktestCreatePayload): Promise<BacktestRunListItem> {
  const res = await $api<{ ok: boolean; run: BacktestRunListItem }>(
    "/instock/api/backtest/runs",
    { method: "POST", body: payload }
  );
  return res.run;
}

export async function getBacktestRun(id: string): Promise<BacktestRunDetail> {
  return $api<BacktestRunDetail>(`/instock/api/backtest/runs/${encodeURIComponent(id)}`);
}

export async function cancelBacktestRun(id: string): Promise<BacktestRunListItem> {
  const res = await $api<{ ok: boolean; run: BacktestRunListItem }>(
    `/instock/api/backtest/runs/${encodeURIComponent(id)}/cancel`,
    { method: "POST" }
  );
  return res.run;
}

export async function deleteBacktestRun(id: string): Promise<{ ok: boolean; deletedBytes: number }> {
  return $api(`/instock/api/backtest/runs/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export interface BacktestKlineMark {
  date: string;
  side: "buy" | "sell";
  price: number;
  qty: number;
  label: string;
}

export interface BacktestKlinePayload {
  ok: boolean;
  code: string;
  adjustType: string;
  dateFrom: string;
  dateTo: string;
  dates: string[];
  ohlc: number[][];
  volume: number[];
  marks: BacktestKlineMark[];
  empty?: boolean;
  hint?: string;
}

export async function getBacktestRunKline(
  runId: string,
  code: string
): Promise<BacktestKlinePayload> {
  const q = new URLSearchParams({ code });
  return $api<BacktestKlinePayload>(
    `/instock/api/backtest/runs/${encodeURIComponent(runId)}/kline?${q.toString()}`
  );
}
