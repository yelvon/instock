/** mootdx 后台探测：本地/在线/auto，轮询日志不阻塞 Web。 */

export type MootdxProbeResult = {
  ok?: boolean;
  provider_id?: string;
  rows?: number;
  universe_scan?: number;
  universe_online?: number;
  tdx_dir?: string;
  mode?: string;
  error?: string;
};

export type MootdxProbePoll = {
  status: string;
  logs: string[];
  done: boolean;
  result?: MootdxProbeResult | null;
  elapsed_ms?: number;
};

export async function startMootdxProbe(
  mode: "auto" | "local" | "online" = "auto"
): Promise<{ ok: boolean; probe_id?: string; error?: string }> {
  const r = await fetch("/instock/api/sync/mootdx_probe", {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify({ mode }),
  });
  return r.json();
}

export async function fetchMootdxProbe(
  probeId: string
): Promise<{ ok: boolean } & MootdxProbePoll> {
  const r = await fetch(
    `/instock/api/sync/mootdx_probe?id=${encodeURIComponent(probeId)}`
  );
  return r.json();
}

export async function cancelMootdxProbe(probeId: string): Promise<void> {
  await fetch(
    `/instock/api/sync/mootdx_probe?id=${encodeURIComponent(probeId)}`,
    { method: "DELETE" }
  );
}

export function runMootdxProbePoll(
  probeId: string,
  onUpdate: (snap: MootdxProbePoll) => void,
  intervalMs = 500
): () => void {
  let stopped = false;
  const tick = async () => {
    if (stopped) return;
    try {
      const j = await fetchMootdxProbe(probeId);
      if (j.ok) {
        onUpdate({
          status: j.status,
          logs: j.logs || [],
          done: !!j.done,
          result: j.result,
          elapsed_ms: j.elapsed_ms,
        });
        if (j.done) stop();
      }
    } catch {
      /* 下一轮重试 */
    }
  };
  const timer = setInterval(() => void tick(), intervalMs);
  void tick();
  const stop = () => {
    if (stopped) return;
    stopped = true;
    clearInterval(timer);
  };
  return stop;
}
