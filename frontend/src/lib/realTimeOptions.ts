import { supabase } from './supabase';

export interface RealTimeOptionPrice {
  timestamp: string;
  ticker: string;
  put_strike: number;
  put_price: number;
  call_strike: number;
  call_price: number;
  current_price: number;
}

export interface OptionPriceUpdate {
  ticker: string;
  put_price: number;
  call_price: number;
  current_price: number;
  timestamp: string;
}

class RealTimeOptionsService {
  private static instance: RealTimeOptionsService;
  private updateInterval: NodeJS.Timeout | null = null;
  private subscribers: Set<(update: OptionPriceUpdate) => void> = new Set();
  private currentTicker: string = 'QQQ';
  private isRunning: boolean = false;

  static getInstance(): RealTimeOptionsService {
    if (!RealTimeOptionsService.instance) {
      RealTimeOptionsService.instance = new RealTimeOptionsService();
    }
    return RealTimeOptionsService.instance;
  }

  subscribe(callback: (update: OptionPriceUpdate) => void): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  start(ticker: string): void {
    if (this.isRunning && this.currentTicker === ticker) {
      return; // Already running for this ticker
    }

    this.stop(); // Stop any existing interval
    this.currentTicker = ticker;
    this.isRunning = true;

    // Start polling for option prices every 30 seconds
    this.updateInterval = setInterval(() => {
      this.fetchOptionPrices();
    }, 30000);

    // Fetch immediately
    this.fetchOptionPrices();
  }

  stop(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
    this.isRunning = false;
  }

  private async fetchOptionPrices(): Promise<void> {
    try {
      // For now, we'll create mock data that simulates real option pricing
      // In a real implementation, this would call your backend API
      const currentPrice = 590 + (Math.random() - 0.5) * 10; // Mock current price around $590
      
      // Mock option prices with some realistic volatility
      const putPrice = Math.max(0.05, 2.50 + (Math.random() - 0.5) * 1.0);
      const callPrice = Math.max(0.05, 2.75 + (Math.random() - 0.5) * 1.0);

      const update: OptionPriceUpdate = {
        ticker: this.currentTicker,
        put_price: putPrice,
        call_price: callPrice,
        current_price: currentPrice,
        timestamp: new Date().toISOString()
      };

      // Notify all subscribers
      this.subscribers.forEach(callback => {
        try {
          callback(update);
        } catch (error) {
          console.error('Error in option price callback:', error);
        }
      });

      // Store in database for historical tracking
      await this.storeOptionPrice(update);

    } catch (error) {
      console.error('Error fetching option prices:', error);
    }
  }

  private async storeOptionPrice(update: OptionPriceUpdate): Promise<void> {
    try {
      // Store the option price update in a dedicated table
      // This would be a new table for real-time option prices
      const { error } = await supabase
        .from('real_time_option_prices')
        .upsert({
          ticker: update.ticker,
          put_price: update.put_price,
          call_price: update.call_price,
          current_price: update.current_price,
          timestamp: update.timestamp
        });

      if (error) {
        console.warn('Could not store option price (table may not exist yet):', error);
      }
    } catch (error) {
      console.warn('Error storing option price:', error);
    }
  }

  async getHistoricalOptionPrices(ticker: string, date: Date): Promise<RealTimeOptionPrice[]> {
    try {
      const dateStr = date.toISOString().split('T')[0];
      
      const { data, error } = await supabase
        .from('real_time_option_prices')
        .select('*')
        .eq('ticker', ticker)
        .gte('timestamp', `${dateStr}T00:00:00`)
        .lte('timestamp', `${dateStr}T23:59:59`)
        .order('timestamp', { ascending: true });

      if (error) {
        console.warn('Could not fetch historical option prices:', error);
        return [];
      }

      return data || [];
    } catch (error) {
      console.error('Error fetching historical option prices:', error);
      return [];
    }
  }
}

export const realTimeOptionsService = RealTimeOptionsService.getInstance();
