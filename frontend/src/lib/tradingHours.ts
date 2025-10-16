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

// Check if timestamp is within the last 30 minutes of trading (no new positions)
export function isEndOfSession(timestamp: string | Date): boolean {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  const estDate = toZonedTime(date, EST_TIMEZONE);
  
  // Check if weekend
  const dayOfWeek = estDate.getDay();
  if (dayOfWeek === 0 || dayOfWeek === 6) {
    return true; // Consider weekend as end of session
  }
  
  // Check if holiday
  const dateStr = estDate.toISOString().split('T')[0];
  if (MARKET_HOLIDAYS_2025.includes(dateStr)) {
    return true; // Consider holiday as end of session
  }
  
  // Check if within last 30 minutes of trading (3:30 PM - 4:00 PM EST)
  const hours = estDate.getHours();
  const minutes = estDate.getMinutes();
  const totalMinutes = hours * 60 + minutes;
  
  const stopTrading = 15 * 60 + 30; // 3:30 PM (30 mins before close)
  const marketClose = 16 * 60;      // 4:00 PM
  
  return totalMinutes >= stopTrading && totalMinutes < marketClose;
}

// Get market session type for background coloring
export type MarketSessionType = 'pre-market' | 'trading' | 'end-session' | 'after-hours' | 'weekend' | 'holiday';

export function getMarketSessionType(timestamp: string | Date): MarketSessionType {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  const estDate = toZonedTime(date, EST_TIMEZONE);
  
  // Check if weekend
  const dayOfWeek = estDate.getDay();
  if (dayOfWeek === 0 || dayOfWeek === 6) {
    return 'weekend';
  }
  
  // Check if holiday
  const dateStr = estDate.toISOString().split('T')[0];
  if (MARKET_HOLIDAYS_2025.includes(dateStr)) {
    return 'holiday';
  }
  
  // Check time periods
  const hours = estDate.getHours();
  const minutes = estDate.getMinutes();
  const totalMinutes = hours * 60 + minutes;
  
  const marketOpen = 9 * 60 + 30;  // 9:30 AM
  const stopTrading = 15 * 60 + 30; // 3:30 PM
  const marketClose = 16 * 60;     // 4:00 PM
  
  if (totalMinutes < marketOpen) {
    return 'pre-market';
  } else if (totalMinutes >= marketOpen && totalMinutes < stopTrading) {
    return 'trading';
  } else if (totalMinutes >= stopTrading && totalMinutes < marketClose) {
    return 'end-session';
  } else {
    return 'after-hours';
  }
}

export function getMarketSessionColor(sessionType: MarketSessionType): string {
  switch (sessionType) {
    case 'trading':
      return 'rgba(0, 0, 0, 0)'; // Transparent for trading hours
    case 'pre-market':
    case 'after-hours':
      return 'rgba(107, 114, 128, 0.1)'; // Light grey for non-trading hours
    case 'end-session':
      return 'rgba(75, 85, 99, 0.2)'; // Darker grey for end-of-session
    case 'weekend':
    case 'holiday':
      return 'rgba(55, 65, 81, 0.15)'; // Medium grey for weekends/holidays
    default:
      return 'rgba(0, 0, 0, 0)';
  }
}
