// Feature Flags Service
// This service manages feature toggles for the application

export interface FeatureFlag {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  category: 'ui' | 'data' | 'trading' | 'experimental' | 'debug';
  dependencies?: string[]; // Other feature flags this depends on
  lastModified: string;
  modifiedBy: string;
}

export interface FeatureFlagState {
  flags: Record<string, FeatureFlag>;
  lastUpdated: string;
}

class FeatureFlagsService {
  private flags: Record<string, FeatureFlag> = {};
  private listeners: Array<(flags: Record<string, FeatureFlag>) => void> = [];
  private storageKey = 'alpha-kite-feature-flags';

  constructor() {
    this.loadFromStorage();
    this.initializeDefaultFlags();
  }

  private initializeDefaultFlags() {
    const defaultFlags: FeatureFlag[] = [
      // UI Features
      {
        id: 'real-time-clock',
        name: 'Real-time Clock',
        description: 'Display live EST clock with milliseconds',
        enabled: true,
        category: 'ui',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'signals-dashboard',
        name: 'Signals Dashboard',
        description: 'Show SMA9/VWAP cross signals table',
        enabled: true,
        category: 'ui',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'trading-dashboard',
        name: 'Trading Dashboard',
        description: 'Show positions, trades, and P&L dashboard',
        enabled: true,
        category: 'ui',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'admin-panel',
        name: 'Admin Panel',
        description: 'System monitoring and configuration panel',
        enabled: true,
        category: 'ui',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'chart-zoom',
        name: 'Chart Zoom',
        description: 'Click and drag to zoom into chart sections',
        enabled: false,
        category: 'ui',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'non-market-hours-toggle',
        name: 'Non-Market Hours Toggle',
        description: 'Show/hide non-market hours on chart',
        enabled: true,
        category: 'ui',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'dark-mode',
        name: 'Dark Mode',
        description: 'Enable dark mode theme toggle',
        enabled: true,
        category: 'ui',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'period-selector',
        name: 'Period Selector',
        description: 'Switch between minute and hour data views',
        enabled: false,
        category: 'ui',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },

      // Data Features
      {
        id: 'real-time-data',
        name: 'Real-time Data Streaming',
        description: 'Enable real-time data updates every minute',
        enabled: true,
        category: 'data',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'option-prices',
        name: 'Option Price Display',
        description: 'Show option price markers on chart',
        enabled: true,
        category: 'data',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'real-time-options',
        name: 'Real-time Option Prices',
        description: 'Stream real-time option price updates',
        enabled: false,
        category: 'data',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'cross-detection',
        name: 'Cross Detection',
        description: 'Detect and highlight SMA9/VWAP crosses',
        enabled: true,
        category: 'data',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'market-hours-highlighting',
        name: 'Market Hours Highlighting',
        description: 'Highlight market vs non-market hours on chart',
        enabled: true,
        category: 'data',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },

      // Trading Features
      {
        id: 'paper-trading',
        name: 'Paper Trading',
        description: 'Enable simulated trading based on signals',
        enabled: false,
        category: 'trading',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'position-tracking',
        name: 'Position Tracking',
        description: 'Track open positions and P&L',
        enabled: false,
        category: 'trading',
        dependencies: ['paper-trading'],
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'auto-trading',
        name: 'Automatic Trading',
        description: 'Automatically execute trades based on signals',
        enabled: false,
        category: 'trading',
        dependencies: ['paper-trading', 'position-tracking'],
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'risk-management',
        name: 'Risk Management',
        description: 'Implement stop-loss and take-profit rules',
        enabled: false,
        category: 'trading',
        dependencies: ['paper-trading'],
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },

      // Experimental Features
      {
        id: 'advanced-charting',
        name: 'Advanced Charting',
        description: 'Additional technical indicators and chart types',
        enabled: false,
        category: 'experimental',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'multi-ticker',
        name: 'Multi-Ticker Support',
        description: 'Support for multiple tickers simultaneously',
        enabled: false,
        category: 'experimental',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'backtesting',
        name: 'Backtesting Engine',
        description: 'Historical strategy testing capabilities',
        enabled: false,
        category: 'experimental',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },

      // Debug Features
      {
        id: 'debug-logs',
        name: 'Debug Logging',
        description: 'Enable detailed console logging',
        enabled: false,
        category: 'debug',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'performance-metrics',
        name: 'Performance Metrics',
        description: 'Show performance timing information',
        enabled: false,
        category: 'debug',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      },
      {
        id: 'mock-data',
        name: 'Mock Data Mode',
        description: 'Use mock data instead of real API calls',
        enabled: false,
        category: 'debug',
        lastModified: new Date().toISOString(),
        modifiedBy: 'system'
      }
    ];

    // Only add flags that don't already exist
    defaultFlags.forEach(flag => {
      if (!this.flags[flag.id]) {
        this.flags[flag.id] = flag;
      }
    });

    this.saveToStorage();
  }

  private loadFromStorage() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        const parsed = JSON.parse(stored) as FeatureFlagState;
        this.flags = parsed.flags || {};
      }
    } catch (error) {
      console.warn('Failed to load feature flags from storage:', error);
    }
  }

  private saveToStorage() {
    try {
      const state: FeatureFlagState = {
        flags: this.flags,
        lastUpdated: new Date().toISOString()
      };
      localStorage.setItem(this.storageKey, JSON.stringify(state));
    } catch (error) {
      console.warn('Failed to save feature flags to storage:', error);
    }
  }

  private notifyListeners() {
    this.listeners.forEach(listener => listener(this.flags));
  }

  // Public API
  public getFlag(id: string): FeatureFlag | undefined {
    return this.flags[id];
  }

  public isEnabled(id: string): boolean {
    const flag = this.flags[id];
    if (!flag) return false;

    // Check dependencies
    if (flag.dependencies) {
      for (const depId of flag.dependencies) {
        if (!this.isEnabled(depId)) {
          return false;
        }
      }
    }

    return flag.enabled;
  }

  public setFlag(id: string, enabled: boolean, modifiedBy: string = 'user') {
    const flag = this.flags[id];
    if (flag) {
      flag.enabled = enabled;
      flag.lastModified = new Date().toISOString();
      flag.modifiedBy = modifiedBy;
      this.saveToStorage();
      this.notifyListeners();
    }
  }

  public getAllFlags(): Record<string, FeatureFlag> {
    return { ...this.flags };
  }

  public getFlagsByCategory(category: FeatureFlag['category']): FeatureFlag[] {
    return Object.values(this.flags).filter(flag => flag.category === category);
  }

  public subscribe(listener: (flags: Record<string, FeatureFlag>) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  public resetToDefaults() {
    this.flags = {};
    this.initializeDefaultFlags();
    this.notifyListeners();
  }

  public exportFlags(): string {
    return JSON.stringify(this.flags, null, 2);
  }

  public importFlags(jsonString: string) {
    try {
      const imported = JSON.parse(jsonString);
      this.flags = imported;
      this.saveToStorage();
      this.notifyListeners();
    } catch {
      throw new Error('Invalid feature flags JSON');
    }
  }
}

// Singleton instance
export const featureFlags = new FeatureFlagsService();

// React hook for using feature flags
export function useFeatureFlag(flagId: string): boolean {
  const [enabled, setEnabled] = React.useState(featureFlags.isEnabled(flagId));

  React.useEffect(() => {
    const unsubscribe = featureFlags.subscribe(() => {
      setEnabled(featureFlags.isEnabled(flagId));
    });
    return unsubscribe;
  }, [flagId]);

  return enabled;
}

// React hook for getting all flags
export function useFeatureFlags(): Record<string, FeatureFlag> {
  const [flags, setFlags] = React.useState(featureFlags.getAllFlags());

  React.useEffect(() => {
    const unsubscribe = featureFlags.subscribe(setFlags);
    return unsubscribe;
  }, []);

  return flags;
}
