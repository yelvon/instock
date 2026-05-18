/** 东财 push2 后台探测：启动后轮询日志，不阻塞其它 API。 */

export type EastmoneyProbeResult = {
  ok?: boolean;
  rows?: number;
  total?: number;
  elapsed_ms?: number;
  push2_preference?: string;
  push2_host?: string | null;
  cookie_configured?: boolean;
  cookie_bytes?: number;
  error?: string;
};

export type EastmoneyProbePoll = {
  status: string;
  logs: string[];
  done: boolean;
  result?: EastmoneyProbeResult | null;
  elapsed_ms?: number;
};

export async function startEastmoneyProbe(push2Host?: string): Promise<{
  ok: boolean;
  probe_id?: string;
  error?: string;
}> {
  const r = await fetch("/instock/api/sync/eastmoney_probe", {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify(push2Host ? { push2_host: push2Host } : {}),
  });
  return r.json();
}

export async function fetchEastmoneyProbe(probeId: string): Promise<
  { ok: boolean } & EastmoneyProbePoll
> {
  const r = await fetch(
    `/instock/api/sync/eastmoney_probe?id=${encodeURIComponent(probeId)}`
  );
  return r.json();
}

export async function cancelEastmoneyProbe(probeId: string): Promise<void> {
  await fetch(
    `/instock/api/sync/eastmoney_probe?id=${encodeURIComponent(probeId)}`,
    { method: "DELETE" }
  );
}

export function runEastmoneyProbePoll(
  probeId: string,
  onUpdate: (snap: EastmoneyProbePoll) => void,
  intervalMs = 500
): () => void {
  let stopped = false;
  const tick = async () => {
    if (stopped) return;
    try {
      const j = await fetchEastmoneyProbe(probeId);
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
