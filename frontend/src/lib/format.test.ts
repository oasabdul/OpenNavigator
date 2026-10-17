import { describe, expect, it } from "vitest";

import {
  arrivalIso,
  formatDuration,
  formatLoad,
  formatMiles,
  formatPrecip,
  formatWind,
  toDatetimeLocalValue,
  toIsoDeparture,
} from "./format";

describe("format helpers", () => {
  it("formats durations", () => {
    expect(formatDuration(0)).toBe("0 min");
    expect(formatDuration(59.4)).toBe("59 min");
    expect(formatDuration(60)).toBe("1h");
    expect(formatDuration(281)).toBe("4h 41m");
  });

  it("formats distance, load, wind, and precipitation", () => {
    expect(formatMiles(12.34)).toBe("12.3 mi");
    expect(formatMiles(213.5)).toBe("214 mi");
    expect(formatLoad(42000)).toBe("42,000 lb");
    expect(formatWind(40.04)).toBe("40.0 mph");
    expect(formatPrecip(0.5)).toBe("0.50 in/hr");
  });

  it("formats a local datetime input value", () => {
    expect(toDatetimeLocalValue(new Date(2026, 9, 18, 7, 5))).toBe("2026-10-18T07:05");
  });

  it("converts a local departure value to ISO and rejects invalid values", () => {
    const iso = toIsoDeparture("2026-10-18T07:05");
    expect(new Date(iso).getFullYear()).toBe(2026);
    expect(() => toIsoDeparture("not-a-date")).toThrow("valid departure");
  });

  it("adds duration to a departure", () => {
    expect(arrivalIso("2026-10-18T12:00:00Z", 90)).toBe("2026-10-18T13:30:00.000Z");
  });
});
