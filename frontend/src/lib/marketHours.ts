import { toZonedTime } from 'date-fns-tz';

const EST_TIMEZONE = 'America/New_York';

// US Market Holidays 2025 (can be expanded)
const MARKET_HOLIDAYS_2025 = [
  '2025-01-01', // New Year's Day
  '2025-01-20', // Martin Luther King Jr. Day
  '2025-02-17', // Presidents' Day
  '2025-04-18', // Good Friday
  '2025-05-26', // Memorial Day
  '2025-07-04', // Independence Day
  '2025-09-01', // Labor Day
  '2025-11-27', // Thanksgiving
  '2025-12-25', // Christmas
];

export function isMarketHours(timestamp: string | Date): boolean {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  const estDate = toZonedTime(date, EST_TIMEZONE);
  
  // Check if weekend
  const dayOfWeek = estDate.getDay();
  if (dayOfWeek === 0 || dayOfWeek === 6) {
    return false; // Sunday or Saturday
  }
  
  // Check if holiday
  const dateStr = estDate.toISOString().split('T')[0];
  if (MARKET_HOLIDAYS_2025.includes(dateStr)) {
    return false;
  }
  
  // Check if within market hours (9:30 AM - 4:00 PM EST)
  const hours = estDate.getHours();
  const minutes = estDate.getMinutes();
  const totalMinutes = hours * 60 + minutes;
  
  const marketOpen = 9 * 60 + 30;  // 9:30 AM
  const marketClose = 16 * 60;     // 4:00 PM
  
  return totalMinutes >= marketOpen && totalMinutes < marketClose;
}

export interface MarketHoursSegment {
  start: string;
  end: string;
  isMarketHours: boolean;
}

export function getMarketHoursSegments(data: Array<{ timestamp: string }>): MarketHoursSegment[] {
  if (data.length === 0) return [];
  
  const segments: MarketHoursSegment[] = [];
  let currentSegment: MarketHoursSegment | null = null;
  
  for (const point of data) {
    const inMarketHours = isMarketHours(point.timestamp);
    
    if (!currentSegment) {
      currentSegment = {
        start: point.timestamp,
        end: point.timestamp,
        isMarketHours: inMarketHours
      };
    } else if (currentSegment.isMarketHours === inMarketHours) {
      // Extend current segment
      currentSegment.end = point.timestamp;
    } else {
      // Save current segment and start new one
      segments.push(currentSegment);
      currentSegment = {
        start: point.timestamp,
        end: point.timestamp,
        isMarketHours: inMarketHours
      };
    }
  }
  
  if (currentSegment) {
    segments.push(currentSegment);
  }
  
  return segments;
}

