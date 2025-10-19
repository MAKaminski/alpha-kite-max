'use client';

import { Cross } from '@/lib/crossDetection';
import { getMarketHoursSegments, isRegularTradingHours } from '@/lib/marketHours';
import { TradeOptionPrice, getOptionPriceColor, getOptionPriceSymbol } from '@/lib/optionPrices';
import { RealTimeOptionPrice } from '@/lib/realTimeOptions';
import { formatToEST } from '@/lib/timezone';
import React, { memo } from 'react';
import { Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceArea, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from 'recharts';
import { ChartDataPoint } from '../../../shared/types';

interface SyntheticOptionPrice {
  id: number;
  timestamp: string;
  ticker: string;
  option_symbol: string;
  option_type: string;
  strike_price: number;
  expiration_date: string;
  spot_price: number;
  market_price: number;
  bid: number;
  ask: number;
  volume: number;
  open_interest: number;
  implied_volatility: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  data_source: string;
}

interface EquityChartProps {
  data: ChartDataPoint[];
  ticker: string;
  crosses: Cross[];
  optionPrices?: TradeOptionPrice[];
  realTimeOptionPrices?: RealTimeOptionPrice[];
  syntheticOptionPrices?: SyntheticOptionPrice[];
  showNonMarketHours?: boolean;
  onToggleNonMarketHours?: (show: boolean) => void;
  marketHoursHighlighting?: boolean;
  period?: 'minute' | 'hour';
}

function EquityChart({ 
  data, 
  ticker, 
  crosses, 
  optionPrices = [], 
  realTimeOptionPrices = [],
  syntheticOptionPrices = [],
  showNonMarketHours = false,
  onToggleNonMarketHours,
  marketHoursHighlighting = true,
  period = 'minute'
}: EquityChartProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const estDate = new Date(date.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const minutes = estDate.getMinutes();
    const hours = estDate.getHours();
    
    // Only show labels at 30-minute intervals starting from market open (10:00 AM)
    const marketOpenHour = 10;
    
    // Check if this is a 30-minute interval
    const isMarketHour = hours >= marketOpenHour && hours < 15; // 10:00 AM - 3:00 PM
    const isHalfHour = minutes === 0 || minutes === 30;
    
    if (isMarketHour && isHalfHour) {
      return formatToEST(timestamp, 'h:mm a');
    }
    
    return '';
  };

  const formatPrice = (value: number) => `$${value.toFixed(2)}`;

  // Safely filter data based on showNonMarketHours setting
  const filteredData = React.useMemo(() => {
    if (!data || data.length === 0) return [];
    
    return showNonMarketHours 
      ? data 
      : data.filter(point => {
          try {
            return isRegularTradingHours(point.timestamp);
          } catch (error) {
            console.warn('Error checking market hours:', error);
            return true; // Default to showing the point
          }
        });
  }, [data, showNonMarketHours]);

  // Prepare chart data with option prices
  const chartData = React.useMemo(() => {
    return filteredData.map(point => {
      try {
        const cross = (crosses || []).find(c => c.timestamp === point.timestamp);
        const optionPrice = (optionPrices || []).find(op => op.timestamp === point.timestamp);
        const realTimeOption = (realTimeOptionPrices || []).find(rt => rt.timestamp === point.timestamp);
        const syntheticOption = (syntheticOptionPrices || []).find(so => so.timestamp === point.timestamp);
        
        return {
          ...point,
          crossMarker: cross ? cross.sma9 : null,  // Mark at SMA9/VWAP cross point
          optionPrice: realTimeOption ? realTimeOption.put_price : 
                      optionPrice ? optionPrice.price : null,
          optionType: realTimeOption ? 'PUT' : 
                     optionPrice ? optionPrice.option_type : null,
          optionSymbol: realTimeOption ? `${ticker}_PUT_${realTimeOption.put_strike}` : 
                       optionPrice ? optionPrice.option_symbol : null,
          syntheticOptionPrice: syntheticOption ? syntheticOption.market_price : null,
          syntheticOptionType: syntheticOption ? syntheticOption.option_type : null,
          syntheticOptionSymbol: syntheticOption ? syntheticOption.option_symbol : null
        };
      } catch (error) {
        console.warn('Error processing chart point:', error);
        return {
          ...point,
          crossMarker: null,
          optionPrice: null,
          optionType: null,
          optionSymbol: null,
          syntheticOptionPrice: null,
          syntheticOptionType: null,
          syntheticOptionSymbol: null
        };
      }
    });
  }, [filteredData, crosses, optionPrices, realTimeOptionPrices, syntheticOptionPrices, ticker]);

  // Get market hours segments for background shading
  const marketSegments = React.useMemo(() => {
    try {
      return getMarketHoursSegments(data || []);
    } catch (error) {
      console.warn('Error getting market segments:', error);
      return [];
    }
  }, [data]);

  // Format volume for display
  const formatVolume = (value: number) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toString();
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Chart | SMA9, Session VWAP ({period === 'minute' ? 'Minute' : 'Hour'} Data)
              </h2>
              {(syntheticOptionPrices && syntheticOptionPrices.length > 0) && (
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">
                    🧮 SYNTHETIC OPTIONS DATA (Black-Scholes Model)
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    • Real data: Solid markers • Synthetic data: Dashed markers
                  </span>
                </div>
              )}
            </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <input
              type="checkbox"
              checked={showNonMarketHours}
              onChange={(e) => onToggleNonMarketHours?.(e.target.checked)}
              className="rounded border-gray-300 dark:border-gray-600"
            />
            Show non-market hours
          </label>
        </div>
      </div>
      
      {/* Main Price Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
          
                {/* Shade non-market hours with darker background (only if showing non-market hours and highlighting is enabled) */}
                {showNonMarketHours && marketHoursHighlighting && marketSegments.filter(seg => !seg.isMarketHours).map((segment, idx) => (
                  <ReferenceArea
                    key={`non-market-${idx}`}
                    x1={segment.start}
                    x2={segment.end}
                    fill="#374151"
                    fillOpacity={0.15}
                    ifOverflow="extendDomain"
                  />
                ))}
          
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatTime}
            stroke="#6B7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            tickFormatter={formatPrice}
            stroke="#6B7280"
            style={{ fontSize: '12px' }}
            domain={['auto', 'auto']}
            label={{ value: 'Price (EST)', angle: -90, position: 'insideLeft', style: { fill: '#6B7280' } }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#F9FAFB',
            }}
            labelFormatter={(label) => `${formatToEST(label, 'h:mm:ss a')} EST`}
            formatter={(value: number) => [`$${value.toFixed(2)}`, '']}
          />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={false}
            name={`${ticker} Price`}
          />
          <Line
            type="monotone"
            dataKey="sma9"
            stroke="#10B981"
            strokeWidth={2}
            dot={false}
            name="SMA9"
            strokeDasharray="5 5"
          />
          <Line
            type="monotone"
            dataKey="vwap"
            stroke="#A855F7"
            strokeWidth={2}
            dot={false}
            name="Session VWAP"
            strokeDasharray="5 5"
          />
              {/* Cross markers as red circles */}
              <Line
                type="monotone"
                dataKey="crossMarker"
                stroke="none"
                dot={{ fill: '#EF4444', r: 6, strokeWidth: 2, stroke: '#FFF' }}
                name="Crosses"
                isAnimationActive={false}
              />
              
              {/* Real option price markers */}
              {optionPrices && optionPrices.length > 0 && (
                <Scatter
                  dataKey="optionPrice"
                  fill="#8884d8"
                  shape={(props: unknown) => {
                    try {
                      const { cx, cy, payload } = props as { cx: number; cy: number; payload: { optionPrice?: number; optionType?: string } };
                      if (!payload?.optionPrice) {
                        return <circle cx={0} cy={0} r={0} fill="transparent" />;
                      }
                      
                      const color = getOptionPriceColor(payload.optionType as 'PUT' | 'CALL');
                      const symbol = getOptionPriceSymbol(payload.optionType as 'PUT' | 'CALL');
                      
                      return (
                        <g>
                          <circle
                            cx={cx}
                            cy={cy}
                            r={8}
                            fill={color}
                            stroke="#FFF"
                            strokeWidth={2}
                          />
                          <text
                            x={cx}
                            y={cy + 4}
                            textAnchor="middle"
                            fill="#FFF"
                            fontSize="10"
                            fontWeight="bold"
                          >
                            {symbol}
                          </text>
                        </g>
                      );
                    } catch (error) {
                      console.warn('Error rendering option marker:', error);
                      return <circle cx={0} cy={0} r={0} fill="transparent" />;
                    }
                  }}
                  name="Real Option Prices"
                />
              )}

              {/* Synthetic option price markers */}
              {syntheticOptionPrices && syntheticOptionPrices.length > 0 && (
                <Scatter
                  dataKey="syntheticOptionPrice"
                  fill="#F59E0B"
                  shape={(props: unknown) => {
                    try {
                      const { cx, cy, payload } = props as { cx: number; cy: number; payload: { syntheticOptionPrice?: number; syntheticOptionType?: string } };
                      if (!payload?.syntheticOptionPrice) {
                        return <circle cx={0} cy={0} r={0} fill="transparent" />;
                      }
                      
                      const color = payload.syntheticOptionType === 'CALL' ? '#F59E0B' : '#EF4444';
                      const symbol = payload.syntheticOptionType === 'CALL' ? 'C' : 'P';
                      
                      return (
                        <g>
                          <circle
                            cx={cx}
                            cy={cy}
                            r={6}
                            fill={color}
                            stroke="#FFF"
                            strokeWidth={2}
                            strokeDasharray="3 3"
                          />
                          <text
                            x={cx}
                            y={cy + 3}
                            textAnchor="middle"
                            fill="#FFF"
                            fontSize="8"
                            fontWeight="bold"
                          >
                            {symbol}
                          </text>
                          <text
                            x={cx}
                            y={cy - 8}
                            textAnchor="middle"
                            fill="#FFF"
                            fontSize="6"
                            fontWeight="bold"
                          >
                            SYN
                          </text>
                        </g>
                      );
                    } catch (error) {
                      console.warn('Error rendering synthetic option marker:', error);
                      return <circle cx={0} cy={0} r={0} fill="transparent" />;
                    }
                  }}
                  name="Synthetic Option Prices"
                />
              )}
            </ComposedChart>
      </ResponsiveContainer>

      {/* Volume Bar Chart */}
      <div className="mt-2">
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={chartData} margin={{ top: 0, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
            
            {/* Shade non-market hours to match main chart */}
            {showNonMarketHours && marketHoursHighlighting && marketSegments.filter(seg => !seg.isMarketHours).map((segment, idx) => (
              <ReferenceArea
                key={`volume-non-market-${idx}`}
                x1={segment.start}
                x2={segment.end}
                fill="#374151"
                fillOpacity={0.15}
                ifOverflow="extendDomain"
              />
            ))}
            
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatTime}
              stroke="#6B7280"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              tickFormatter={formatVolume}
              stroke="#6B7280"
              style={{ fontSize: '12px' }}
              domain={[0, 'auto']}
              label={{ value: 'Volume', angle: -90, position: 'insideLeft', style: { fill: '#6B7280', fontSize: '12px' } }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '8px',
                color: '#F9FAFB',
              }}
              labelFormatter={(label) => `${formatToEST(label, 'h:mm:ss a')} EST`}
              formatter={(value: number) => [formatVolume(value), 'Volume']}
            />
            <Bar
              dataKey="volume"
              fill="#3B82F6"
              opacity={0.6}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Export memoized version to prevent unnecessary re-renders when parent re-renders
export default memo(EquityChart);
