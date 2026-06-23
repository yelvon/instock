import { describe, expect, it } from "vitest";
import { legacyJobInnerTab, opsRunsQuery, normalizeOpsTab } from "./navLinks";

describe("normalizeOpsTab", () => {
  it("maps legacy job center tabs to ops tabs", () => {
    expect(normalizeOpsTab("manual")).toBe("jobs");
    expect(normalizeOpsTab("schedule")).toBe("jobs");
    expect(normalizeOpsTab("mootdx")).toBe("mootdx");
    expect(normalizeOpsTab("runs")).toBe("runs");
    expect(normalizeOpsTab("lineage")).toBe("advanced");
    expect(normalizeOpsTab("sources")).toBe("advanced");
  });

  it("falls back to quick for unknown tabs", () => {
    expect(normalizeOpsTab("unknown")).toBe("quick");
    expect(normalizeOpsTab(undefined)).toBe("quick");
  });
});

describe("legacyJobInnerTab", () => {
  it("preserves inner job center tab names", () => {
    expect(legacyJobInnerTab("schedule")).toBe("schedule");
    expect(legacyJobInnerTab("lineage")).toBe("lineage");
  });

  it("returns undefined for ops-level tabs", () => {
    expect(legacyJobInnerTab("jobs")).toBeUndefined();
    expect(legacyJobInnerTab("quick")).toBeUndefined();
  });
});

describe("opsRunsQuery", () => {
  it("builds a runs tab query with the selected run id", () => {
    expect(opsRunsQuery("abc-123")).toEqual({ tab: "runs", runId: "abc-123" });
  });

  it("omits blank run ids", () => {
    expect(opsRunsQuery(" ")).toEqual({ tab: "runs" });
  });
});
