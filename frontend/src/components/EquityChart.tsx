'use client';

import { Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceArea, Scatter, ComposedChart } from 'recharts';
import { ChartDataPoint } from '../../../shared/types';
import { Cross } from '@/lib/crossDetection';
import { formatToEST } from '@/lib/timezone';
import { getMarketHoursSegments, isRegularTradingHours } from '@/lib/marketHours';
import { TradeOptionPrice, getOptionPriceColor, getOptionPriceSymbol } from '@/lib/optionPrices';
import ChartZoom, { useChartZoom } from './ChartZoom';

interface EquityChartProps {
  data: ChartDataPoint[];
  ticker: string;
  crosses: Cross[];
  optionPrices?: TradeOptionPrice[];
  showNonMarketHours?: boolean;
  onToggleNonMarketHours?: (show: boolean) => void;
}

export default function EquityChart({ 
  data, 
  ticker, 
  crosses, 
  optionPrices = [], 
  showNonMarketHours = true,
  onToggleNonMarketHours 
}: EquityChartProps) {
  const formatTime = (timestamp: string) => {
    return formatToEST(timestamp, 'h:mm a');
  };

  const formatPrice = (value: number) => `$${value.toFixed(2)}`;

  // Filter data based on showNonMarketHours setting
  const filteredData = showNonMarketHours 
    ? data 
    : data.filter(point => isRegularTradingHours(point.timestamp));

  // Prepare chart data with option prices
  const chartData = filteredData.map(point => {
    const cross = crosses.find(c => c.timestamp === point.timestamp);
    const optionPrice = optionPrices.find(op => op.timestamp === point.timestamp);
    
    return {
      ...point,
      crossMarker: cross ? cross.sma9 : null,  // Mark at SMA9/VWAP cross point
      optionPrice: optionPrice ? optionPrice.price : null,
      optionType: optionPrice ? optionPrice.option_type : null,
      optionSymbol: optionPrice ? optionPrice.option_symbol : null
    };
  });

  // Get market hours segments for background shading
  const marketSegments = getMarketHoursSegments(data);

  // Set up zoom functionality
  const { zoomedData, isZoomed, handleZoom, handleReset } = useChartZoom(chartData);

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Chart | SMA9, Session VWAP
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
      
      {/* Zoom Controls */}
      <ChartZoom 
        data={chartData}
        onZoom={handleZoom}
        onReset={handleReset}
        isZoomed={isZoomed}
      />
      
      <ResponsiveContainer width="100%" height={500}>
        <ComposedChart data={zoomedData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
          
          {/* Shade non-market hours with darker background (only if showing non-market hours) */}
          {showNonMarketHours && marketSegments.filter(seg => !seg.isMarketHours).map((segment, idx) => (
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
              <Scatter
                dataKey="optionPrice"
                fill="#8884d8"
                shape={(props: unknown) => {
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
                }}
                name="Option Prices"
              />
            </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

