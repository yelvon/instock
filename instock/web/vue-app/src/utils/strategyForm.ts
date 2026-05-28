import type { BacktestStrategyItem, StrategyParamDef } from "@/api/backtest";

export const CATEGORY_LABELS: Record<string, string> = {
  baseline: "基准策略",
  technical: "技术指标",
  screening: "选股桥接",
  plugin: "插件策略",
};

export const CATEGORY_ORDER = ["baseline", "technical", "screening", "plugin"];

export function strategyParamsFromItem(s: BacktestStrategyItem | undefined): Record<string, number | string | boolean> {
  if (!s) return {};
  const defs = s.params?.length ? s.params : legacyParamDefs(s);
  const out: Record<string, number | string | boolean> = {};
  for (const p of defs) {
    if (p.default !== undefined && p.default !== null) {
      out[p.key] = p.default as number | string | boolean;
    }
  }
  return out;
}

function legacyParamDefs(s: BacktestStrategyItem): StrategyParamDef[] {
  return Object.entries(s.paramSchema || {}).map(([key, defaultVal]) => ({
    key,
    label: key,
    type: typeof defaultVal === "number" ? "float" : typeof defaultVal === "boolean" ? "bool" : "str",
    default: defaultVal,
    required: true,
  }));
}

export function groupedStrategies(strategies: BacktestStrategyItem[]) {
  const groups = new Map<string, BacktestStrategyItem[]>();
  for (const cat of CATEGORY_ORDER) {
    groups.set(cat, []);
  }
  for (const s of strategies) {
    const cat = s.category && groups.has(s.category) ? s.category : "plugin";
    if (!groups.has(cat)) groups.set(cat, []);
    groups.get(cat)!.push(s);
  }
  return CATEGORY_ORDER.filter((c) => (groups.get(c)?.length ?? 0) > 0).map((c) => ({
    category: c,
    label: CATEGORY_LABELS[c] || c,
    items: groups.get(c) || [],
  }));
}

export function validateStrategyParamsClient(
  strategyId: string,
  params: Record<string, number | string | boolean>,
  defs: StrategyParamDef[]
): string | null {
  for (const p of defs) {
    const val = params[p.key];
    if (val === undefined || val === null || val === "") {
      if (p.required && p.default === undefined) {
        return `请填写 ${p.label}`;
      }
      continue;
    }
    const n = Number(val);
    if ((p.type === "int" || p.type === "float") && Number.isFinite(n)) {
      if (p.min != null && n < p.min) return `${p.label} 不能小于 ${p.min}`;
      if (p.max != null && n > p.max) return `${p.label} 不能大于 ${p.max}`;
    }
  }
  if (strategyId === "moving_average_cross") {
    const fast = Number(params.fast);
    const slow = Number(params.slow);
    if (Number.isFinite(fast) && Number.isFinite(slow) && fast >= slow) {
      return "快线周期必须小于慢线周期";
    }
  }
  if (strategyId === "macd_cross") {
    const fast = Number(params.fast);
    const slow = Number(params.slow);
    if (Number.isFinite(fast) && Number.isFinite(slow) && fast >= slow) {
      return "MACD 快线周期必须小于慢线周期";
    }
  }
  if (strategyId === "rsi_reversal") {
    const os = Number(params.oversold);
    const ob = Number(params.overbought);
    if (Number.isFinite(os) && Number.isFinite(ob) && os >= ob) {
      return "RSI 超卖阈值必须小于超买阈值";
    }
  }
  return null;
}
