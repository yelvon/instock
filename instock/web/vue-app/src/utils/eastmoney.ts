/** 东方财富个股行情页 URL（与 kline_bundle_export / Bokeh 指标页一致） */
export function eastmoneyQuoteUrl(code: string): string {
  const c = String(code ?? "").trim();
  if (!c) return "";
  const codeName = c.startsWith("6") ? `SH${c}` : `SZ${c}`;
  return `https://quote.eastmoney.com/${codeName}.html`;
}
