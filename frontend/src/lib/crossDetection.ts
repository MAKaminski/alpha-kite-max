import { ChartDataPoint } from '../../../shared/types';

export interface Cross {
  timestamp: string;
  price: number;
  sma9: number;
  vwap: number;
  direction: 'up' | 'down'; // 'up' = SMA9 crosses above VWAP, 'down' = SMA9 crosses below VWAP
}

export function detectCrosses(data: ChartDataPoint[]): Cross[] {
  const crosses: Cross[] = [];
  
  for (let i = 1; i < data.length; i++) {
    const prev = data[i - 1];
    const curr = data[i];
    
    // Check if SMA9 crossed VWAP
    const prevDiff = prev.sma9 - prev.vwap;
    const currDiff = curr.sma9 - curr.vwap;
    
    // Cross occurred if signs differ
    if (prevDiff * currDiff < 0) {
      crosses.push({
        timestamp: curr.timestamp,
        price: curr.price,
        sma9: curr.sma9,
        vwap: curr.vwap,
        direction: currDiff > 0 ? 'up' : 'down'
      });
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

