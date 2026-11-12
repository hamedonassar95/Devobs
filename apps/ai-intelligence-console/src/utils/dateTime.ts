function pad(value: number): string {
  return String(value).padStart(2, '0');
}

/** Format a date for an input[type="datetime-local"] without changing its local clock time. */
export function toLocalDateTimeInput(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
