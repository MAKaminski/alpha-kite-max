'use client';

import React from 'react';
import { CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type OptionRow = {
  timestamp: string;
  market_price: number;
};

export default function OptionsChartStandalone() {
  const [data, setData] = React.useState<OptionRow[]>([]);
  const [date, setDate] = React.useState<string>(new Date('2025-10-17').toISOString().slice(0,10));
  const ticker = 'QQQ';

  React.useEffect(() => {
    const load = async () => {
      const res = await fetch(`/api/get-options-for-chart?ticker=${ticker}&date=${date}`);
      const json = await res.json();
      const rows: OptionRow[] = (json.data || []).map((r: { timestamp: string; market_price: number }) => ({ timestamp: r.timestamp, market_price: r.market_price }));
      // minute-bucket average
      const byMinute: Record<string, { sum: number; count: number }> = {};
      for (const r of rows) {
        const minute = r.timestamp.slice(0,16) + ':00';
        if (!byMinute[minute]) byMinute[minute] = { sum: 0, count: 0 };
        byMinute[minute].sum += r.market_price;
        byMinute[minute].count += 1;
      }
      const series = Object.entries(byMinute).map(([ts, agg]) => ({ timestamp: ts, optionPrice: agg.sum / agg.count }));
      series.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
      setData(series);
    };
    load();
  }, [date]);

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour: 'numeric', minute: '2-digit' });
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm">
        <label className="text-gray-700 dark:text-gray-200">Date</label>
        <input className="bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded px-2 py-1" type="date" value={date} onChange={(e)=>setDate(e.target.value)} />
      </div>
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
          <XAxis dataKey="timestamp" tickFormatter={formatTime} stroke="#6B7280" style={{ fontSize: '12px' }} />
          <YAxis tickFormatter={(v)=>`$${v.toFixed(2)}`} stroke="#F59E0B" style={{ fontSize: '12px' }} label={{ value: 'Option Price', angle: -90, position: 'insideLeft', style: { fill: '#F59E0B' } }} />
          <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8, color: '#F9FAFB' }} formatter={(v)=>[`$${(v as number).toFixed(2)}`, 'Option Price']} />
          <Legend wrapperStyle={{ paddingTop: 8 }} />
          <Line type="monotone" dataKey="optionPrice" stroke="#F59E0B" strokeWidth={2} dot={{ r: 2, fill: '#F59E0B' }} name="Synthetic Option Price (avg/minute)" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}


