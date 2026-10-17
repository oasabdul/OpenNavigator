const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "numeric",
  minute: "2-digit",
});

const shortDateFormatter = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  hour: "numeric",
  minute: "2-digit",
});

const milesFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
const preciseMilesFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
const loadFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

export function formatDuration(minutes: number): string {
  const rounded = Math.max(0, Math.round(minutes));
  if (rounded < 60) return `${rounded} min`;
  const hours = Math.floor(rounded / 60);
  const remainder = rounded % 60;
  return remainder === 0 ? `${hours}h` : `${hours}h ${remainder}m`;
}

export function formatMiles(miles: number): string {
  return `${miles >= 100 ? milesFormatter.format(miles) : preciseMilesFormatter.format(miles)} mi`;
}

export function formatLoad(pounds: number): string {
  return `${loadFormatter.format(pounds)} lb`;
}

export function formatTime(iso: string): string {
  return timeFormatter.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTimeFormatter.format(new Date(iso));
}

export function formatShortDateTime(iso: string): string {
  return shortDateFormatter.format(new Date(iso));
}

export function formatHourOffset(hour: number): string {
  return `+${hour}h`;
}

export function formatWind(mph: number): string {
  return `${mph.toFixed(1)} mph`;
}

export function formatPrecip(inchesPerHour: number): string {
  return `${inchesPerHour.toFixed(2)} in/hr`;
}

export function formatTemperature(value: number | null): string {
  return value === null ? "—" : `${Math.round(value)}°F`;
}

export function arrivalIso(departureIso: string, durationMinutes: number): string {
  return new Date(new Date(departureIso).getTime() + durationMinutes * 60_000).toISOString();
}

export function toDatetimeLocalValue(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export function defaultDepartureValue(): string {
  const date = new Date(Date.now() + 60 * 60_000);
  date.setSeconds(0, 0);
  const minutes = date.getMinutes();
  date.setMinutes(minutes + ((15 - (minutes % 15)) % 15));
  return toDatetimeLocalValue(date);
}

export function toIsoDeparture(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new Error("Enter a valid departure date and time.");
  }
  return date.toISOString();
}

export function classNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}
