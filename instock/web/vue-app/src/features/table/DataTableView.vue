<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { AgGridVue } from "ag-grid-vue3";
import type {
  ColDef,
  GridApi,
  GridOptions,
  GridReadyEvent,
  CellClickedEvent,
  SortChangedEvent,
} from "ag-grid-community";
import { ElMessage } from "element-plus";
import * as XLSX from "xlsx";
import PageShell from "@/components/ui/PageShell.vue";
import UiStateError from "@/components/ui/UiStateError.vue";
import UiStateLoading from "@/components/ui/UiStateLoading.vue";
import { eastmoneyQuoteUrl } from "@/utils/eastmoney";

interface ColInfo {
  value: string;
  caption: string;
  width?: number | string;
}

interface TableMetaOk {
  ok: true;
  table_name: string;
  name: string;
  is_realtime: boolean;
  date_default: string;
  column_names: ColInfo[];
  view_modes?: string[];
  default_filters?: Record<string, string>;
  requires_view_filter?: boolean;
}

export interface TableFiltersPayload {
  code: string;
  dateFrom: string;
  dateTo: string;
  adjustType: string;
}

const props = withDefaults(
  defineProps<{
    fixedTableName?: string;
    embedded?: boolean;
    defaultViewMode?: "cross_section" | "series";
  }>(),
  {
    embedded: false,
    defaultViewMode: "cross_section",
  }
);

const emit = defineEmits<{
  filtersChange: [filters: TableFiltersPayload];
}>();

function emitFiltersChange() {
  emit("filtersChange", {
    code: codeStr.value.trim(),
    dateFrom: dateFromStr.value,
    dateTo: dateToStr.value,
    adjustType: adjustType.value || "raw",
  });
}

const route = useRoute();
const router = useRouter();

function queryParamOne(v: string | string[] | undefined | null): string {
  if (v == null) return "";
  const s = Array.isArray(v) ? (v[0] ?? "") : v;
  return String(s).trim();
}

function instockAbsUrl(path: string): string {
  if (typeof window === "undefined") return path;
  const p = path.startsWith("/") ? path : `/${path}`;
  return new URL(p, window.location.origin).href;
}

function unknownErrorMessage(e: unknown, fallback: string): string {
  if (e == null) return fallback;
  if (e instanceof Error) {
    if (e.name === "AbortError") return "";
    if (e.message) return e.message;
    return e.name ? `${e.name}（无 message）` : fallback;
  }
  if (typeof e === "string" && e) return e;
  return fallback;
}

const tableName = computed(() =>
  props.fixedTableName ||
  queryParamOne(route.query.table_name as string | string[] | undefined)
);
const dateStr = ref("");
const viewMode = ref<"cross_section" | "series">(props.defaultViewMode);
const codeStr = ref("");
const adjustType = ref("raw");
const dateFromStr = ref("");
const dateToStr = ref("");

const hasViewModes = computed(
  () => (meta.value?.view_modes?.length ?? 0) > 0 || !!props.fixedTableName
);

function canLoadRows(): boolean {
  if (!tableName.value || !meta.value) return false;
  if (viewMode.value === "series") {
    return !!codeStr.value.trim();
  }
  return !!dateStr.value;
}

const meta = ref<TableMetaOk | null>(null);
const metaLoading = ref(false);
const metaError = ref<string | null>(null);
let metaAbort: AbortController | null = null;
let metaReqId = 0;
let rowsDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const rows = ref<Record<string, unknown>[]>([]);
const totalRows = ref(0);
const page = ref(1);
const pageSize = ref(500);
/** 服务端全表排序（分页下表头排序仅对当前页无效） */
const sortCol = ref<string | null>(null);
const sortDir = ref<"asc" | "desc" | null>(null);
const exportLoading = ref(false);
const rowsLoading = ref(false);
const rowsError = ref<string | null>(null);
let rowsAbort: AbortController | null = null;
let rowsReqId = 0;

async function loadTableMeta(tn: string) {
  const reqId = ++metaReqId;
  metaAbort?.abort();
  const ac = new AbortController();
  metaAbort = ac;

  metaLoading.value = true;
  metaError.value = null;

  const url = instockAbsUrl(
    "/instock/api/table_meta?table_name=" + encodeURIComponent(tn)
  );

  try {
    const r = await fetch(url, { signal: ac.signal });
    const text = await r.text();
    let j: TableMetaOk & { ok?: boolean; error?: string };
    try {
      j = JSON.parse(text) as typeof j;
    } catch {
      const t = text.trim();
      if (t.startsWith("<")) {
        throw new Error(`HTTP ${r.status}：返回 HTML。请求: ${url}`);
      }
      throw new Error(
        `HTTP ${r.status}：响应非 JSON（前 120 字：${t.slice(0, 120)}）`
      );
    }
    if (!r.ok || !j.ok) {
      throw new Error((j as { error?: string }).error || `HTTP ${r.status}`);
    }
    if (ac.signal.aborted || reqId !== metaReqId) return;
    meta.value = j as TableMetaOk;
    if (j.date_default) dateStr.value = j.date_default;
    if (j.default_filters?.adjust_type) {
      adjustType.value = j.default_filters.adjust_type;
    }
    if (j.view_modes?.length) {
      const preferred = props.defaultViewMode;
      viewMode.value = j.view_modes.includes(preferred)
        ? preferred
        : (j.view_modes[0] as "cross_section" | "series");
    }
  } catch (e) {
    if (ac.signal.aborted || reqId !== metaReqId) return;
    const msg = unknownErrorMessage(e, "加载表信息失败");
    meta.value = null;
    metaError.value = msg || "加载表信息失败";
  } finally {
    if (reqId === metaReqId) metaLoading.value = false;
  }
}

interface PagedRowsResponse {
  ok?: boolean;
  total?: number;
  page?: number;
  page_size?: number;
  rows?: Record<string, unknown>[];
  error?: string;
}

async function loadTableRows(
  name: string,
  date: string,
  pageNum = 1,
  opts?: { pageSize?: number; all?: boolean }
) {
  const reqId = ++rowsReqId;
  rowsAbort?.abort();
  const ac = new AbortController();
  rowsAbort = ac;

  rowsLoading.value = true;
  rowsError.value = null;

  const ps = opts?.all ? 2000 : (opts?.pageSize ?? pageSize.value);
  const qs = new URLSearchParams({
    name,
    page: String(pageNum),
    page_size: String(ps),
  });
  if (viewMode.value) qs.set("view_mode", viewMode.value);
  if (adjustType.value) qs.set("adjust_type", adjustType.value);
  if (viewMode.value === "series") {
    if (codeStr.value.trim()) qs.set("code", codeStr.value.trim());
    if (dateFromStr.value) qs.set("date_from", dateFromStr.value);
    if (dateToStr.value) qs.set("date_to", dateToStr.value);
  } else if (date) {
    qs.set("date", date);
  }
  if (sortCol.value) {
    qs.set("sort_col", sortCol.value);
    qs.set("sort_dir", sortDir.value || "desc");
  }
  const url = instockAbsUrl(`/instock/api_data?${qs.toString()}`);

  try {
    const r = await fetch(url, { signal: ac.signal });
    const text = await r.text();
    if (r.status === 404) {
      let errMsg = "表或数据不存在";
      try {
        const j = JSON.parse(text) as { error?: string };
        if (j.error) errMsg = j.error;
      } catch {
        /* ignore */
      }
      throw new Error(errMsg);
    }
    if (!r.ok) throw new Error(`加载失败 HTTP ${r.status}`);
    const parsed = JSON.parse(text) as
      | Record<string, unknown>[]
      | PagedRowsResponse;
    if (ac.signal.aborted || reqId !== rowsReqId) return;

    if (Array.isArray(parsed)) {
      rows.value = parsed;
      totalRows.value = parsed.length;
      page.value = 1;
      emitFiltersChange();
      return;
    }

    if (!parsed.rows || !Array.isArray(parsed.rows)) {
      throw new Error("返回格式异常");
    }
    rows.value = parsed.rows;
    totalRows.value = parsed.total ?? parsed.rows.length;
    page.value = parsed.page ?? pageNum;
    if (parsed.page_size) pageSize.value = parsed.page_size;
    emitFiltersChange();
  } catch (e) {
    if (ac.signal.aborted || reqId !== rowsReqId) return;
    rows.value = [];
    totalRows.value = 0;
    const msg = unknownErrorMessage(e, "加载失败");
    rowsError.value = msg || "加载失败";
  } finally {
    if (reqId === rowsReqId) rowsLoading.value = false;
  }
}

onUnmounted(() => {
  metaReqId++;
  rowsReqId++;
  if (rowsDebounceTimer) clearTimeout(rowsDebounceTimer);
  metaAbort?.abort();
  rowsAbort?.abort();
  metaLoading.value = false;
  rowsLoading.value = false;
});

watch(
  tableName,
  (tn) => {
    metaReqId++;
    rowsReqId++;
    metaAbort?.abort();
    rowsAbort?.abort();
    metaLoading.value = false;
    rowsLoading.value = false;
    meta.value = null;
    metaError.value = null;
    rows.value = [];
    totalRows.value = 0;
    page.value = 1;
    sortCol.value = null;
    sortDir.value = null;
    rowsError.value = null;
    if (!tn) return;
    void loadTableMeta(tn);
  },
  { immediate: true }
);

watch(
  () =>
    [
      tableName.value,
      dateStr.value,
      meta.value?.table_name,
      viewMode.value,
      codeStr.value,
      adjustType.value,
      dateFromStr.value,
      dateToStr.value,
    ] as const,
  ([name]) => {
    rows.value = [];
    totalRows.value = 0;
    page.value = 1;
    sortCol.value = null;
    sortDir.value = null;
    rowsError.value = null;
    if (!name || !meta.value || !canLoadRows()) return;
    if (rowsDebounceTimer) clearTimeout(rowsDebounceTimer);
    rowsDebounceTimer = setTimeout(() => {
      rowsDebounceTimer = null;
      void loadTableRows(name, dateStr.value, 1);
    }, 400);
  }
);

function retryMeta() {
  if (tableName.value) void loadTableMeta(tableName.value);
}

function reloadData() {
  if (!tableName.value || !meta.value || !canLoadRows()) return;
  const d = viewMode.value === "series" ? "" : dateStr.value;
  void loadTableRows(tableName.value, d, page.value);
}

function onPageChange(p: number) {
  page.value = p;
  if (!tableName.value || !meta.value || !canLoadRows()) return;
  const d = viewMode.value === "series" ? "" : dateStr.value;
  void loadTableRows(tableName.value, d, p);
}

const showMetaError = computed(() => !!metaError.value && !meta.value);
const showMetaLoading = computed(() => metaLoading.value && !meta.value);
const showRowsLoading = computed(() => rowsLoading.value);
const showRowsError = computed(() => !!rowsError.value && !rowsLoading.value);

const columnDefs = ref<ColDef[]>([]);

watch(
  () => meta.value?.column_names,
  (cols) => {
    if (!cols?.length) {
      columnDefs.value = [];
      return;
    }
    columnDefs.value = cols.map((c, i) => {
      const w = typeof c.width === "number" ? c.width : Number(c.width) || 100;
      const def: ColDef = {
        field: c.value,
        headerName: c.caption,
        width: Math.max(w, 72),
        sortable: true,
        /** 排序由服务端全表 ORDER BY，避免仅排当前页 */
        comparator: () => 0,
        filter: "agTextColumnFilter",
        floatingFilter: false,
        pinned: i < 3 ? "left" : undefined,
      };
      if (c.value === "code") {
        def.cellStyle = {
          color: "#7ec8ff",
          cursor: "pointer",
          fontWeight: "600",
        };
      }
      if (c.value === "name") {
        def.cellStyle = { color: "#f5f8fc", fontWeight: "500" };
      }
      if (c.value === "change_rate") {
        def.cellStyle = (p) => {
          const v = p.value;
          if (v == null || v === "") return { color: "#f0f4f9" };
          const n = parseFloat(String(v));
          if (n > 0) return { color: "#ff8585", fontWeight: "600" };
          if (n < 0) return { color: "#7ee787", fontWeight: "600" };
          return { color: "#f0f4f9" };
        };
      }
      return def;
    });
  },
  { immediate: true }
);

const defaultColDef: ColDef = {
  resizable: true,
  minWidth: 80,
  suppressMovable: false,
};

const gridOptions: GridOptions = {
  rowHeight: 36,
  headerHeight: 42,
  animateRows: false,
  suppressColumnVirtualisation: false,
  suppressCellFocus: false,
  enableCellTextSelection: true,
  tooltipShowDelay: 400,
  localeText: {
    filterOoo: "筛选…",
    equals: "等于",
    notEqual: "不等于",
    contains: "包含",
    notContains: "不包含",
    startsWith: "开头是",
    endsWith: "结尾是",
    blank: "空白",
    notBlank: "非空白",
    noRowsToShow: "暂无数据",
  },
};

const gridApi = ref<GridApi | null>(null);

function onGridReady(e: GridReadyEvent) {
  gridApi.value = e.api;
}

function onSortChanged(e: SortChangedEvent) {
  const api = e.api;
  const sorted = api
    .getColumnState()
    .filter((c) => c.sort != null && c.sort !== undefined);
  const nextCol = sorted.length ? sorted[0].colId ?? null : null;
  const nextDir =
    sorted.length && sorted[0].sort === "asc"
      ? "asc"
      : sorted.length
        ? "desc"
        : null;
  if (nextCol === sortCol.value && nextDir === sortDir.value) return;
  sortCol.value = nextCol;
  sortDir.value = nextDir;
  page.value = 1;
  if (tableName.value && dateStr.value) {
    void loadTableRows(tableName.value, dateStr.value, 1);
  }
}

function onCellClicked(e: CellClickedEvent) {
  if (e.colDef?.field !== "code" || !e.data) return;
  const row = e.data as Record<string, unknown>;
  const code = row.code;
  if (code == null || code === "") return;
  let d = row.date;
  if (d && typeof d === "string") d = d.split("T")[0];
  else d = dateStr.value;
  const name = (row.name as string) || "";
  const codeStr = String(code);

  const ev = e.event as MouseEvent | undefined;
  if (ev?.ctrlKey || ev?.metaKey) {
    void router.push({
      name: "indicators",
      query: { code: codeStr, date: String(d), name },
    });
    return;
  }

  const url = eastmoneyQuoteUrl(codeStr);
  if (url) window.open(url, "_blank", "noopener,noreferrer");
}

async function exportExcel() {
  if (!tableName.value || !canLoadRows()) return;
  try {
    exportLoading.value = true;
    const allPages: Record<string, unknown>[] = [];
    let p = 1;
    let total = totalRows.value || 1;
    while (allPages.length < total) {
      const qs = new URLSearchParams({
        name: tableName.value,
        page: String(p),
        page_size: "2000",
      });
      if (viewMode.value) qs.set("view_mode", viewMode.value);
      if (adjustType.value) qs.set("adjust_type", adjustType.value);
      if (viewMode.value === "series") {
        if (codeStr.value.trim()) qs.set("code", codeStr.value.trim());
        if (dateFromStr.value) qs.set("date_from", dateFromStr.value);
        if (dateToStr.value) qs.set("date_to", dateToStr.value);
      } else {
        qs.set("date", dateStr.value);
      }
      if (sortCol.value) {
        qs.set("sort_col", sortCol.value);
        qs.set("sort_dir", sortDir.value || "desc");
      }
      const r = await fetch(instockAbsUrl(`/instock/api_data?${qs.toString()}`));
      const j = (await r.json()) as PagedRowsResponse;
      if (!r.ok || !j.rows?.length) break;
      allPages.push(...j.rows);
      total = j.total ?? allPages.length;
      if (j.rows.length < 2000) break;
      p += 1;
    }
    if (!allPages.length) {
      ElMessage.warning("无数据可导出");
      return;
    }
    const ws = XLSX.utils.json_to_sheet(allPages);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "data");
    const fn =
      viewMode.value === "series"
        ? `${tableName.value}_${codeStr.value || "series"}.xlsx`
        : `${tableName.value}_${dateStr.value}.xlsx`;
    XLSX.writeFile(wb, fn);
    ElMessage.success(`已导出 ${allPages.length.toLocaleString()} 条`);
  } catch {
    ElMessage.error("导出失败");
  } finally {
    exportLoading.value = false;
  }
}

const pageTitle = computed(() =>
  props.embedded ? "标准日线" : meta.value?.name || "数据表"
);
const pageSubtitle = computed(() =>
  props.embedded
    ? "回测读 cn_stock_daily_bar；按交易日横截面或按股票代码查历史序列"
    : "日期切换后自动加载；点击列标题按全表排序（非仅当前页）；点击代码打开东方财富，⌘/Ctrl+点击进指标页。"
);
const rowCountLabel = computed(() => {
  if (!totalRows.value && !rows.value.length) return "";
  const total = totalRows.value || rows.value.length;
  if (total <= pageSize.value) {
    return `共 ${total.toLocaleString()} 条`;
  }
  const from = (page.value - 1) * pageSize.value + 1;
  const to = Math.min(page.value * pageSize.value, total);
  return `共 ${total.toLocaleString()} 条，当前第 ${from.toLocaleString()}–${to.toLocaleString()} 条`;
});
const showPagination = computed(
  () => totalRows.value > pageSize.value && !rowsLoading.value
);
const loadHint = computed(() => {
  if (!tableName.value) return "请在侧栏选择数据表，或从地址栏带上 ?table_name=…";
  return "";
});
</script>

<template>
  <component :is="props.embedded ? 'div' : PageShell" v-bind="props.embedded ? {} : { title: pageTitle, subtitle: pageSubtitle }">
    <UiStateError v-if="showMetaError" :message="metaError || '加载表信息失败'" />
    <div v-if="showMetaError" class="retry-row">
      <el-text v-if="tableName" type="info" size="small">
        表名：{{ tableName }}
      </el-text>
      <el-button type="primary" size="small" @click="retryMeta">重试加载</el-button>
    </div>
    <UiStateLoading v-else-if="showMetaLoading" text="加载表信息…" />
    <template v-else-if="!tableName">
      <el-alert type="info" :closable="false" :title="loadHint" />
    </template>
    <template v-else-if="meta">
      <div class="toolbar">
        <el-segmented
          v-if="hasViewModes"
          v-model="viewMode"
          :options="[
            { label: '按交易日', value: 'cross_section' },
            { label: '按股票代码', value: 'series' },
          ]"
        />
        <template v-if="viewMode === 'series'">
          <span class="muted">代码</span>
          <el-input
            v-model="codeStr"
            placeholder="600000"
            style="width: 110px"
            size="small"
          />
          <span class="muted">区间</span>
          <el-date-picker
            v-model="dateFromStr"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="起"
            size="small"
            style="width: 140px"
          />
          <el-date-picker
            v-model="dateToStr"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="止"
            size="small"
            style="width: 140px"
          />
        </template>
        <template v-else>
          <span class="muted">日期</span>
          <el-date-picker
            v-model="dateStr"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 160px; margin: 0 12px"
          />
        </template>
        <template v-if="hasViewModes">
          <span class="muted">复权</span>
          <el-select v-model="adjustType" size="small" style="width: 96px">
            <el-option label="raw" value="raw" />
            <el-option label="qfq" value="qfq" />
            <el-option label="hfq" value="hfq" />
          </el-select>
        </template>
        <el-button type="primary" @click="reloadData">刷新</el-button>
        <el-button :loading="exportLoading" @click="exportExcel">导出 Excel</el-button>
      </div>
      <UiStateError v-if="showRowsError" :message="rowsError || '加载失败'" />
      <UiStateLoading v-else-if="showRowsLoading" text="加载表格…" />
      <template v-else>
        <el-text v-if="!rows.length" type="info" size="small">
          当前日期暂无数据（可在「数据同步」运行对应作业）
        </el-text>
        <div v-else class="table-panel">
          <div v-if="rowCountLabel" class="table-meta-bar">
            <el-text class="meta-count">{{ rowCountLabel }}</el-text>
            <el-text class="meta-hint">点击代码 → 东方财富；⌘/Ctrl+点击 → 指标页</el-text>
          </div>
          <el-pagination
            v-if="showPagination"
            v-model:current-page="page"
            :page-size="pageSize"
            :total="totalRows"
            layout="total, prev, pager, next, jumper"
            background
            class="table-pager"
            @current-change="onPageChange"
          />
          <div
            class="ag-theme-quartz-dark ag-grid-instock ag-grid-wrap"
            style="height: min(72vh, 640px); width: 100%"
          >
            <AgGridVue
              class="ag-theme-quartz-dark ag-grid-instock"
              style="width: 100%; height: 100%"
              :grid-options="gridOptions"
              :column-defs="columnDefs"
              :default-col-def="defaultColDef"
              :row-data="rows"
              row-selection="multiple"
              @grid-ready="onGridReady"
              @sort-changed="onSortChanged"
              @cell-clicked="onCellClicked"
            />
          </div>
        </div>
      </template>
    </template>
  </component>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.table-panel {
  margin-top: 4px;
}
.table-meta-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  padding: 0 2px;
}
.meta-count {
  color: #e8eef5;
  font-size: 13px;
  font-weight: 500;
}
.meta-hint {
  color: #9fb0c4;
  font-size: 12px;
}
.ag-grid-wrap {
  margin-top: 0;
}
.table-pager {
  margin-bottom: 10px;
  justify-content: flex-end;
}
.retry-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  flex-wrap: wrap;
}
</style>
