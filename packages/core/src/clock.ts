/**
 * Monotonic time for authority decisions.
 *
 * A device wall clock can be set backwards. If expiry were judged on the wall
 * clock alone, rolling the clock back would resurrect an expired approval. The
 * store keeps the highest wall-clock value it has ever observed; the effective
 * time is the maximum of the two. A wall clock far behind the high-water mark
 * marks the clock suspect, which HOLDS dispatch. It never extends authority.
 */

export interface ClockState {
  /** Highest wall-clock value ever observed, ms since epoch. Persisted by the host. */
  highWaterMs: number;
}

export interface ClockReading {
  state: ClockState;
  effectiveMs: number;
  suspect: boolean;
}

export const CLOCK_TOLERANCE_MS = 5 * 60 * 1000;

export function observeClock(state: ClockState, wallMs: number, toleranceMs: number = CLOCK_TOLERANCE_MS): ClockReading {
  if (!Number.isFinite(wallMs)) throw new RangeError("wall clock must be a finite number");
  const highWaterMs = Math.max(state.highWaterMs, wallMs);
  return {
    state: { highWaterMs },
    effectiveMs: Math.max(wallMs, state.highWaterMs),
    suspect: wallMs < state.highWaterMs - toleranceMs,
  };
}

const TIMESTAMP = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$/;

/** Strict RFC 3339 UTC second-precision timestamp to ms, or null. Rejects 2026-02-30 and 24:00. */
export function parseTimestamp(text: string): number | null {
  const m = TIMESTAMP.exec(text);
  if (!m) return null;
  const [y, mo, d, h, mi, s] = [m[1], m[2], m[3], m[4], m[5], m[6]].map((x) => Number(x)) as [number, number, number, number, number, number];
  const ms = Date.UTC(y, mo - 1, d, h, mi, s);
  const back = new Date(ms);
  if (back.getUTCFullYear() !== y || back.getUTCMonth() !== mo - 1 || back.getUTCDate() !== d) return null;
  if (back.getUTCHours() !== h || back.getUTCMinutes() !== mi || back.getUTCSeconds() !== s) return null;
  return ms;
}

export function formatTimestamp(ms: number): string {
  const d = new Date(ms);
  const p = (n: number, w = 2): string => String(n).padStart(w, "0");
  return `${p(d.getUTCFullYear(), 4)}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}T${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}Z`;
}

/** True when the action's validity window has closed at the effective time. */
export function isExpired(validUntil: string, effectiveMs: number): boolean {
  const until = parseTimestamp(validUntil);
  if (until === null) return true; // an unparseable expiry is treated as expired: fail closed
  return effectiveMs >= until;
}
