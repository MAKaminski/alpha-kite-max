import { ChartDataPoint } from '../../../shared/types';
import { isRegularTradingHours } from './marketHours';

export interface Cross {
  timestamp: string;
  price: number;
  sma9: number;
  vwap: number;
  direction: 'up' | 'down'; // 'up' = SMA9 crosses above VWAP, 'down' = SMA9 crosses below VWAP
}

export function detectCrosses(data: ChartDataPoint[]): Cross[] {
  const crosses: Cross[] = [];
  let lastDirection: 'up' | 'down' | null = null;

  for (let i = 1; i < data.length; i++) {
    const prev = data[i - 1];
    const curr = data[i];

    // Only detect crosses during regular trading hours (9:30 AM - 4:00 PM EST)
    if (!isRegularTradingHours(curr.timestamp)) {
      continue;
    }

    // Check if SMA9 crossed VWAP
    const prevDiff = prev.sma9 - prev.vwap;
    const currDiff = curr.sma9 - curr.vwap;

    // Cross occurred if signs differ
    if (prevDiff * currDiff < 0) {
      const direction = currDiff > 0 ? 'up' : 'down';

      // Only add if direction changed from last cross (prevent consecutive same-direction crosses)
      if (lastDirection === null || lastDirection !== direction) {
        crosses.push({
          timestamp: curr.timestamp,
          price: curr.price,
          sma9: curr.sma9,
          vwap: curr.vwap,
          direction
        });
        lastDirection = direction;
      }
    }
  }

  return crosses;
}

export function filterCrossesByDate(crosses: Cross[], targetDate: Date): Cross[] {
  const targetDateStr = targetDate.toISOString().split('T')[0];
  return crosses.filter(cross => {
    const crossDateStr = new Date(cross.timestamp).toISOString().split('T')[0];
    return crossDateStr === targetDateStr;
  });
}

