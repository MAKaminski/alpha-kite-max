'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ChartDataPoint } from '../../../shared/types';

interface EquityChartProps {
  data: ChartDataPoint[];
  ticker: string;
}

export default function EquityChart({ data, ticker }: EquityChartProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  };

  const formatPrice = (value: number) => `$${value.toFixed(2)}`;

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Chart | SMA9, Session VWAP
      </h2>
      <ResponsiveContainer width="100%" height={500}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
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
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#F9FAFB',
            }}
            labelFormatter={(label) => formatTime(label)}
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
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

