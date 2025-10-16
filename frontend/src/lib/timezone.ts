import { format, toZonedTime } from 'date-fns-tz';

const EST_TIMEZONE = 'America/New_York';

export function formatToEST(date: Date | string, formatString: string = 'h:mm a'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const estDate = toZonedTime(dateObj, EST_TIMEZONE);
  return format(estDate, formatString, { timeZone: EST_TIMEZONE });
}

export function getCurrentEST(): Date {
  return toZonedTime(new Date(), EST_TIMEZONE);
}

export function formatESTClock(): string {
  const now = getCurrentEST();
  const ms = now.getMilliseconds().toString().padStart(3, '0').substring(0, 2);
  return `${format(now, 'HH:mm:ss', { timeZone: EST_TIMEZONE })}:${ms}`;
}

