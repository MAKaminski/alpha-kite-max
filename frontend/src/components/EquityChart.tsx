'use client';

import React from 'react';
import { Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceArea, Scatter, ComposedChart } from 'recharts';
import { ChartDataPoint } from '../../../shared/types';
import { Cross } from '@/lib/crossDetection';
import { formatToEST } from '@/lib/timezone';
import { getMarketHoursSegments, isRegularTradingHours } from '@/lib/marketHours';
import { TradeOptionPrice, getOptionPriceColor, getOptionPriceSymbol } from '@/lib/optionPrices';
import { RealTimeOptionPrice } from '@/lib/realTimeOptions';

interface EquityChartProps {
  data: ChartDataPoint[];
  ticker: string;
  crosses: Cross[];
  optionPrices?: TradeOptionPrice[];
  realTimeOptionPrices?: RealTimeOptionPrice[];
  showNonMarketHours?: boolean;
  onToggleNonMarketHours?: (show: boolean) => void;
  marketHoursHighlighting?: boolean;
  period?: 'minute' | 'hour';
}

export default function EquityChart({ 
  data, 
  ticker, 
  crosses, 
  optionPrices = [], 
  realTimeOptionPrices = [],
  showNonMarketHours = true,
  onToggleNonMarketHours,
  marketHoursHighlighting = true,
  period = 'minute'
}: EquityChartProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const estDate = new Date(date.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const minutes = estDate.getMinutes();
    const hours = estDate.getHours();
    
    // Only show labels at 30-minute intervals starting from market open (9:30 AM)
    const marketOpenHour = 9;
    
    // Check if this is a 30-minute interval
    const isMarketHour = hours >= marketOpenHour && hours < 16; // 9:30 AM - 4:00 PM
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
        
        return {
          ...point,
          crossMarker: cross ? cross.sma9 : null,  // Mark at SMA9/VWAP cross point
          optionPrice: realTimeOption ? realTimeOption.put_price : 
                      optionPrice ? optionPrice.price : null,
          optionType: realTimeOption ? 'PUT' : 
                     optionPrice ? optionPrice.option_type : null,
          optionSymbol: realTimeOption ? `${ticker}_PUT_${realTimeOption.put_strike}` : 
                       optionPrice ? optionPrice.option_symbol : null
        };
      } catch (error) {
        console.warn('Error processing chart point:', error);
        return {
          ...point,
          crossMarker: null,
          optionPrice: null,
          optionType: null,
          optionSymbol: null
        };
      }
    });
  }, [filteredData, crosses, optionPrices, realTimeOptionPrices, ticker]);

  // Get market hours segments for background shading
  const marketSegments = React.useMemo(() => {
    try {
      return getMarketHoursSegments(data || []);
    } catch (error) {
      console.warn('Error getting market segments:', error);
      return [];
    }
  }, [data]);

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Chart | SMA9, Session VWAP ({period === 'minute' ? 'Minute' : 'Hour'} Data)
            </h2>
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
      
      <ResponsiveContainer width="100%" height={500}>
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
              
              {/* Option price markers */}
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
                  name="Option Prices"
                />
              )}
            </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

