/**
 * Bookings and arrivals (v1 scope accepted 2026-10-03 23:37Z).
 *
 * A visitor asks for a date and a party size. Code, not a model, checks the
 * farm sheet (open days, hours, capacity, price) and the seats already
 * confirmed on that slot, then proposes ONE exact book_slot action for Noor.
 * Her approval of that envelope confirms the booking and blocks the seats;
 * the confirmation message to the visitor is a separate send_message action
 * with its own approval. Arrival and no-show are owner records; nothing is
 * sent. Anything the sheet does not say (no price, no capacity, a closed day)
 * is a question for a person, never a guess.
 */

import { reconcileSlot, type SlotRequest, validateAppointment } from "./calendar.js";
import type { Sha256 } from "./canon.js";
import { formatTimestamp } from "./clock.js";
import { type ActionEnvelope, type Recipient, sealEnvelope } from "./envelope.js";
import type { FactRevision, FarmSheet, Weekday } from "./facts.js";
import type { Money } from "./money.js";

export interface BookingRequest {
  request_id: string;
  visitor_name: string;
  /** How to reach the visitor: the channel they wrote on. */
  contact: Recipient;
  /** Absolute local date, YYYY-MM-DD, in the farm's time zone. */
  date: string;
  /** Local start time HH:MM; defaults to the farm's opening time. */
  time?: string;
  party_size: number;
  /** Source message the request came from, when there is one (evidence for the preview). */
  source_id?: string;
}

export type BookingState = "tentative" | "confirmed" | "declined" | "cancelled";
export type ArrivalRecord = "arrived" | "no_show";

export interface Booking {
  booking_id: string;
  request: BookingRequest;
  slot_id: string;
  slot_start: string;
  slot_end: string;
  price: Money;
  fact_revision: number;
  state: BookingState;
  arrival: ArrivalRecord | null;
}

export type CapacityFailureReason = "missing_fact" | "closed_day" | "outside_hours" | "bad_date" | "bad_party_size" | "no_capacity";

export type CapacityVerdict =
  | { ok: true; remaining_after: number; slot_id: string; slot_start: string; slot_end: string; price: Money }
  | { ok: false; reason: CapacityFailureReason; detail: string };

const WEEKDAYS: Weekday[] = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

function weekdayOf(date: string): Weekday | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  if (!m) return null;
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  if (d.getUTCFullYear() !== Number(m[1]) || d.getUTCMonth() !== Number(m[2]) - 1 || d.getUTCDate() !== Number(m[3])) return null;
  return WEEKDAYS[d.getUTCDay()] ?? null;
}

function minutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number) as [number, number];
  return h * 60 + m;
}

/** Code answers "can we take this party on this date?" from the farm sheet and the confirmed seats. */
export function checkCapacity(sheet: FarmSheet, confirmed: readonly Booking[], request: BookingRequest, timezone = "Africa/Nairobi"): CapacityVerdict {
  if (!Number.isInteger(request.party_size) || request.party_size < 1) return { ok: false, reason: "bad_party_size", detail: "party size must be a whole number of at least 1" };
  const appointment = validateAppointment({ date: request.date, time: request.time ?? (sheet.hours ? sheet.hours.start.slice(0, 5) : null), timezone });
  if (!appointment.ok) return { ok: false, reason: "bad_date", detail: appointment.detail };
  if (sheet.capacity_per_tour === null || sheet.price_per_person_kes === null) {
    return { ok: false, reason: "missing_fact", detail: "the farm sheet has no capacity or no price yet; ask Noor (farm setup)" };
  }
  if (sheet.days === null || sheet.hours === null) return { ok: false, reason: "missing_fact", detail: "the farm sheet has no days or hours yet; ask Noor (farm setup)" };
  const weekday = weekdayOf(request.date);
  if (!weekday || !sheet.days.includes(weekday)) return { ok: false, reason: "closed_day", detail: `the farm does not take visitors on ${weekday ?? request.date}` };
  const start = appointment.time;
  if (minutes(start) < minutes(sheet.hours.start.slice(0, 5)) || minutes(start) >= minutes(sheet.hours.end.slice(0, 5))) {
    return { ok: false, reason: "outside_hours", detail: `tours run ${sheet.hours.start.slice(0, 5)} to ${sheet.hours.end.slice(0, 5)}` };
  }
  const slot_id = `${request.date}T${start}`;
  const taken = confirmed.filter((b) => b.state === "confirmed" && b.slot_id === slot_id).reduce((n, b) => n + b.request.party_size, 0);
  const remaining = sheet.capacity_per_tour - taken;
  if (request.party_size > remaining) return { ok: false, reason: "no_capacity", detail: `${remaining} of ${sheet.capacity_per_tour} seats left on ${slot_id}` };
  const price: Money = { amount_minor: sheet.price_per_person_kes * request.party_size * 100, currency: "KES", exponent: 2 };
  return { ok: true, remaining_after: remaining - request.party_size, slot_id, slot_start: start, slot_end: sheet.hours.end.slice(0, 5), price };
}

export interface BookingProposalInput {
  request: BookingRequest;
  facts: FactRevision;
  confirmed: readonly Booking[];
  tenant_id: string;
  action_id: string;
  booking_id: string;
  created_at_ms: number;
  valid_for_ms: number;
  /** Exactly what Noor is shown. Experience owns reviewed copy; the core checks numbers elsewhere. */
  preview_text: string;
  render_locale: string;
  timezone?: string;
}

export type BookingProposalResult =
  | { ok: true; envelope: ActionEnvelope; booking: Booking }
  | { ok: false; reason: CapacityFailureReason; detail: string }
  | { ok: false; reason: "invalid_envelope"; detail: string; errors: string[] };

/** One exact book_slot action plus the tentative booking it would confirm. Nothing is blocked until Noor approves. */
export function proposeBooking(input: BookingProposalInput, sha256: Sha256): BookingProposalResult {
  const check = checkCapacity(input.facts.sheet, input.confirmed, input.request, input.timezone);
  if (!check.ok) return { ok: false, reason: check.reason, detail: check.detail };
  const booking: Booking = {
    booking_id: input.booking_id,
    request: input.request,
    slot_id: check.slot_id,
    slot_start: check.slot_start,
    slot_end: check.slot_end,
    price: check.price,
    fact_revision: input.facts.revision,
    state: "tentative",
    arrival: null,
  };
  const sealed = sealEnvelope(
    {
      schema: "sauti.action_envelope",
      schema_version: "1.0.0",
      action_id: input.action_id,
      tenant_id: input.tenant_id,
      kind: "book_slot",
      created_at: formatTimestamp(input.created_at_ms),
      valid_until: formatTimestamp(input.created_at_ms + input.valid_for_ms),
      fact_revision: input.facts.revision,
      recipient: { channel: "local", address: "owner", language: input.request.contact.language },
      payload: { type: "book_slot", booking_id: input.booking_id, slot_date: input.request.date, slot_start: check.slot_start, slot_end: check.slot_end, party_size: input.request.party_size, price: check.price },
      evidence: [],
      preview: { text: input.preview_text, render_locale: input.render_locale },
      authority: { level: "owner", owner_context_required: true },
    },
    sha256,
  );
  if (!sealed.ok) return { ok: false, reason: "invalid_envelope", detail: "the booking proposal does not satisfy the contract", errors: sealed.errors };
  return { ok: true, envelope: sealed.value, booking };
}

/**
 * Noor approved the book_slot envelope (through approveExact). Confirm the booking
 * on the authoritative calendar: the seats are re-checked against what is confirmed
 * NOW, because other bookings may have landed since the proposal. Offline devices
 * stay tentative (see calendar.reconcileSlot).
 */
export function confirmBooking(booking: Booking, approvedEnvelope: ActionEnvelope, sheet: FarmSheet, confirmed: readonly Booking[], authoritative: boolean, requested_at: string): { ok: true; booking: Booking } | { ok: false; reason: "envelope_mismatch" | "not_authoritative" | "no_capacity"; detail: string } {
  const p = approvedEnvelope.payload;
  if (approvedEnvelope.kind !== "book_slot" || p.type !== "book_slot" || p.booking_id !== booking.booking_id || p.slot_date !== booking.request.date || p.party_size !== booking.request.party_size) {
    return { ok: false, reason: "envelope_mismatch", detail: "the approved action is not this booking" };
  }
  if (!authoritative) return { ok: false, reason: "not_authoritative", detail: "this device is not the authoritative calendar; the booking stays tentative until reconciled" };
  const capacity = sheet.capacity_per_tour ?? 0;
  const already = confirmed.filter((b) => b.state === "confirmed" && b.slot_id === booking.slot_id).map((b) => ({ booking_id: b.booking_id, party_size: b.request.party_size }));
  const req: SlotRequest = { booking_id: booking.booking_id, slot_id: booking.slot_id, party_size: booking.request.party_size, requested_at, authority: "authoritative" };
  const [outcome] = reconcileSlot({ slot_id: booking.slot_id, capacity }, already, [req]);
  if (!outcome || outcome.state !== "confirmed") return { ok: false, reason: "no_capacity", detail: outcome?.reason ?? "no outcome" };
  return { ok: true, booking: { ...booking, state: "confirmed" } };
}

/** Owner record only: arrived or did not show. Nothing is sent, no fact changes. */
export function recordArrival(booking: Booking, status: ArrivalRecord): { ok: true; booking: Booking } | { ok: false; reason: "not_confirmed"; detail: string } {
  if (booking.state !== "confirmed") return { ok: false, reason: "not_confirmed", detail: `booking is ${booking.state}; only confirmed visits get an arrival record` };
  return { ok: true, booking: { ...booking, arrival: status } };
}
