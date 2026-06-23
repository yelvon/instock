import { describe, expect, it } from "vitest";
import { buildMaintenanceGuide } from "./maintenanceGuide";

describe("buildMaintenanceGuide", () => {
  it("marks local data as blocked when vipdoc is unavailable", () => {
    const guide = buildMaintenanceGuide(
      { dir_exists: false, vipdoc_exists: false, healthcheck: false },
      { total_bars: 0, qfq_total_bars: 0, suspect: 0 }
    );

    expect(guide.readyForBacktest).toBe(false);
    expect(guide.steps[0].status).toBe("blocked");
    expect(guide.nextAction?.id).toBe("configure_tdx");
  });

  it("recommends qfq derivation when raw exists but qfq is empty", () => {
    const guide = buildMaintenanceGuide(
      { dir_exists: true, vipdoc_exists: true, healthcheck: true },
      { total_bars: 100, qfq_total_bars: 0, suspect: 0 }
    );

    expect(guide.readyForBacktest).toBe(true);
    expect(guide.steps.map((s) => s.status)).toEqual([
      "done",
      "done",
      "todo",
      "todo",
    ]);
    expect(guide.nextAction?.id).toBe("derive_qfq");
  });

  it("reports ready with a warning when suspect rows exist", () => {
    const guide = buildMaintenanceGuide(
      { dir_exists: true, vipdoc_exists: true, healthcheck: true },
      { total_bars: 100, qfq_total_bars: 100, suspect: 2 }
    );

    expect(guide.readyForBacktest).toBe(true);
    expect(guide.qualityWarning).toContain("2");
    expect(guide.nextAction?.id).toBe("check_gaps");
  });
});
