import { $api } from "@/api/client";
import type { KlineMark, KlinePeriod } from "@/utils/klineChart";

export interface CanonicalKlinePayload {
  ok: boolean;
  code: string;
  adjustType: string;
  period: KlinePeriod;
  dateFrom: string;
  dateTo: string;
  dates: string[];
  ohlc: number[][];
  volume: number[];
  marks?: KlineMark[];
  empty?: boolean;
  hint?: string;
}

export async function getCanonicalKline(params: {
  code: string;
  dateFrom: string;
  dateTo: string;
  adjustType?: string;
  period?: KlinePeriod;
}): Promise<CanonicalKlinePayload> {
  const q = new URLSearchParams({
    code: params.code,
    date_from: params.dateFrom,
    date_to: params.dateTo,
    adjust_type: params.adjustType || "raw",
    period: params.period || "daily",
  });
  return $api<CanonicalKlinePayload>(`/instock/api/canonical/kline?${q.toString()}`);
}
