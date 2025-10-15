export interface EquityData {
  ticker: string;
  timestamp: string;
  price: number;
  volume: number;
}

export interface IndicatorData {
  ticker: string;
  timestamp: string;
  sma9: number;
  vwap: number;
}

export interface ChartDataPoint {
  timestamp: string;
  price: number;
  sma9: number;
  vwap: number;
  volume: number;
}

