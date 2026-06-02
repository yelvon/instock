/** 任务运行轮询：小 tail + 退避，减轻 run_detail 负载 */

export const POLL_TAIL_CHARS = 2048;
export const POLL_INTERVAL_MS = 2000;
export const POLL_INTERVAL_MAX_MS = 8000;

export function runDetailUrl(runId: string, tail = POLL_TAIL_CHARS): string {
  const base = `/instock/api/sync/run_detail?id=${encodeURIComponent(runId)}`;
  return tail > 0 ? `${base}&tail=${tail}` : base;
}

export function nextPollIntervalMs(
  prevMs: number,
  progressKey: string,
  lastProgressKey: string
): { intervalMs: number; progressKey: string } {
  if (progressKey && progressKey === lastProgressKey) {
    return {
      intervalMs: Math.min(POLL_INTERVAL_MAX_MS, Math.round(prevMs * 1.5)),
      progressKey,
    };
  }
  return { intervalMs: POLL_INTERVAL_MS, progressKey };
}

export function progressKeyFromRun(run: {
  progress_current?: number;
  progress_total?: number;
  progress_bytes?: number;
  progress_lines?: number;
  progress_hint?: string;
}): string {
  return [
    run.progress_current ?? 0,
    run.progress_total ?? 0,
    run.progress_bytes ?? 0,
    run.progress_lines ?? 0,
    (run.progress_hint || "").trim(),
  ].join("|");
}
