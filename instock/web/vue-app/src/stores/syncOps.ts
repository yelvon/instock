import { defineStore } from "pinia";
import { ref } from "vue";

export interface JobItem {
  id: string;
  title: string;
  hint?: string;
  description?: string;
  group?: string;
  depends_on?: string;
}

export interface RunRow {
  id: string;
  job_id: string;
  label: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  exit_code?: number | null;
  date_mode?: string;
  date_list?: string;
  date_start?: string;
  date_end?: string;
  qfq_mode?: string;
  spot_data_source?: string;
  bar_data_source?: string;
  trigger_source?: string;
  schedule_title?: string;
  schedule_id?: string;
  progress_bytes?: number;
  progress_lines?: number;
  error_line_count?: number;
  last_errors_tail?: string;
  stdout_tail?: string;
  error_message?: string;
  progress_hint?: string;
  progress_current?: number;
  progress_total?: number;
  batch_ids?: string[];
}

export interface ScheduleRow {
  id: string;
  title: string;
  enabled: boolean;
  job_id: string;
  date_mode: string;
  date_start: string;
  date_end: string;
  date_list: string;
  weekdays: number[];
  times: string[];
  spot_data_source: string;
}

export interface SchedulerStatus {
  enabled_globally?: boolean;
  schedule_count?: number;
  last_tick_at?: string;
  tick_age_seconds?: number | null;
  fire_history_count?: number;
  requires_web_process?: boolean;
}

export interface SchedulerFireRow {
  id: string;
  fired_at: string;
  schedule_title?: string;
  job_label?: string;
  job_id?: string;
  trigger_time?: string;
  status: string;
  run_id?: string;
  message?: string;
}

export const useSyncOpsStore = defineStore("syncOps", () => {
  const jobs = ref<JobItem[]>([]);
  const runs = ref<RunRow[]>([]);
  const prefs = ref<Record<string, unknown>>({});
  const schedGlobal = ref(true);
  const schedDraft = ref<ScheduleRow[]>([]);
  const schedStatus = ref<SchedulerStatus | null>(null);
  const schedFireHistory = ref<SchedulerFireRow[]>([]);

  let jobsLoaded = false;
  let runsLoaded = false;
  let prefsLoaded = false;
  let schedLoaded = false;

  async function loadJobs(force = false) {
    if (jobsLoaded && !force) return jobs.value;
    const r = await fetch("/instock/api/sync/jobs");
    const j = await r.json();
    if (j.ok && Array.isArray(j.jobs)) {
      jobs.value = j.jobs;
      jobsLoaded = true;
    }
    return jobs.value;
  }

  async function loadRuns(limit = 100, force = false) {
    if (runsLoaded && !force) return runs.value;
    const r = await fetch(`/instock/api/sync/runs?limit=${limit}`);
    const j = await r.json();
    if (j.ok && Array.isArray(j.runs)) {
      runs.value = j.runs;
      runsLoaded = true;
    }
    return runs.value;
  }

  async function loadPrefs(force = false) {
    if (prefsLoaded && !force) return prefs.value;
    const r = await fetch("/instock/api/sync/prefs");
    const j = await r.json();
    if (j.ok && j.prefs) {
      prefs.value = j.prefs;
      prefsLoaded = true;
    }
    return prefs.value;
  }

  async function loadScheduler(force = false) {
    if (schedLoaded && !force) {
      return {
        schedGlobal: schedGlobal.value,
        schedDraft: schedDraft.value,
        schedStatus: schedStatus.value,
        schedFireHistory: schedFireHistory.value,
      };
    }
    const r = await fetch("/instock/api/sync/scheduler?history_limit=50");
    const j = await r.json();
    if (j.ok) {
      schedGlobal.value = j.config?.enabled_globally !== false;
      schedDraft.value = JSON.parse(JSON.stringify(j.config?.schedules || []));
      schedStatus.value = j.status || null;
      schedFireHistory.value = Array.isArray(j.fire_history) ? j.fire_history : [];
      schedLoaded = true;
    }
    return {
      schedGlobal: schedGlobal.value,
      schedDraft: schedDraft.value,
      schedStatus: schedStatus.value,
      schedFireHistory: schedFireHistory.value,
    };
  }

  async function bootstrapOps(force = false) {
    await Promise.all([loadJobs(force), loadRuns(100, force), loadPrefs(force)]);
  }

  function invalidateRuns() {
    runsLoaded = false;
  }

  function invalidateScheduler() {
    schedLoaded = false;
  }

  return {
    jobs,
    runs,
    prefs,
    schedGlobal,
    schedDraft,
    schedStatus,
    schedFireHistory,
    loadJobs,
    loadRuns,
    loadPrefs,
    loadScheduler,
    bootstrapOps,
    invalidateRuns,
    invalidateScheduler,
  };
});
