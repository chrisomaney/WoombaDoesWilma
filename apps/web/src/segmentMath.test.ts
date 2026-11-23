import { describe, expect, it } from "vitest";
import { ensureClipSegments, paintRange, resizeSegmentEdge } from "./segmentMath";
import type { Segment } from "./api";

const base: Segment[] = [];

describe("segmentMath", () => {
  it("ensures a full keep segment", () => {
    const segs = ensureClipSegments(base, "c1", 1000);
    expect(segs).toHaveLength(1);
    expect(segs[0].state).toBe("keep");
    expect(segs[0].out_ms).toBe(1000);
  });

  it("paints a cut in the middle", () => {
    const start = ensureClipSegments(base, "c1", 3000);
    const next = paintRange(start, "c1", 3000, 1000, 2000, "cut");
    const mine = next.filter((s) => s.clip_id === "c1");
    expect(mine.map((s) => s.state)).toEqual(["keep", "cut", "keep"]);
    expect(mine[1].in_ms).toBe(1000);
    expect(mine[1].out_ms).toBe(2000);
  });

  it("resizes a cut edge", () => {
    const start = paintRange(ensureClipSegments(base, "c1", 3000), "c1", 3000, 1000, 2000, "cut");
    const cut = start.find((s) => s.state === "cut")!;
    const next = resizeSegmentEdge(start, "c1", 3000, cut.id, "out", 2200);
    const updated = next.find((s) => s.id === cut.id)!;
    expect(updated.out_ms).toBe(2200);
  });
});
