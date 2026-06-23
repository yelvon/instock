import { describe, expect, it } from "vitest";
import router from "../router";
import { legacyJobInnerTab, normalizeOpsTab } from "../utils/navLinks";

describe("router redirects", () => {
  it("resolves string redirects for backtest legacy paths", () => {
    const legacyBars = router.resolve("/backtest-data/bars");
    const legacyRoot = router.resolve("/backtest-data");
    const backtestRoot = router.resolve("/backtest");

    expect(legacyBars.matched[1].redirect).toBeTypeOf("function");
    expect(legacyRoot.matched[1].redirect).toBe("/backtest/data/overview");
    expect(backtestRoot.matched[1].redirect).toBe("/backtest/run");
  });

  it("maps /jobs query through normalizeOpsTab + jobTab (redirect target)", () => {
    const legacyTabs = ["manual", "schedule", "mootdx", "runs", "lineage", "sources"];
    for (const legacy of legacyTabs) {
      const tab = normalizeOpsTab(legacy);
      const inner = legacyJobInnerTab(legacy);
      expect(tab).not.toBe("quick");
      if (inner && (tab === "jobs" || tab === "advanced")) {
        expect(["manual", "schedule", "sources", "lineage", "governance"]).toContain(inner);
      }
    }
  });
});
