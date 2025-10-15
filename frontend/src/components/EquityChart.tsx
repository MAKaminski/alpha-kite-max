'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceArea } from 'recharts';
import { ChartDataPoint } from '../../../shared/types';
import { Cross } from '@/lib/crossDetection';
import { formatToEST } from '@/lib/timezone';
import { getMarketHoursSegments } from '@/lib/marketHours';

interface EquityChartProps {
  data: ChartDataPoint[];
  ticker: string;
  crosses: Cross[];
}

export default function EquityChart({ data, ticker, crosses }: EquityChartProps) {
  const formatTime = (timestamp: string) => {
    return formatToEST(timestamp, 'h:mm a');
  };

  const formatPrice = (value: number) => `$${value.toFixed(2)}`;

  // Add cross marker data to chart data
  const chartData = data.map(point => {
    const isCross = crosses.some(c => c.timestamp === point.timestamp);
    return {
      ...point,
      crossMarker: isCross ? point.price : null
    };
  });

  // Get market hours segments for background shading
  const marketSegments = getMarketHoursSegments(data);

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Chart | SMA9, Session VWAP
      </h2>
      <ResponsiveContainer width="100%" height={500}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
          
          {/* Shade non-market hours with darker background */}
          {marketSegments.filter(seg => !seg.isMarketHours).map((segment, idx) => (
            <ReferenceArea
              key={`non-market-${idx}`}
              x1={segment.start}
              x2={segment.end}
              fill="#6B7280"
              fillOpacity={0.1}
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
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

