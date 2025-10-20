'use client';

import React from 'react';
import { CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type OptionRow = {
  timestamp: string;
  market_price: number;
  option_symbol: string;
  option_type: 'CALL' | 'PUT';
  strike_price: number;
};
type ChartPoint = {
  timestamp: string;
  [series: string]: string | number;
};

export default function OptionsChartStandalone() {
  const [data, setData] = React.useState<ChartPoint[]>([]);
  const [date, setDate] = React.useState<string>(new Date('2025-10-17').toISOString().slice(0,10));
  const [showCalls, setShowCalls] = React.useState(true);
  const [showPuts, setShowPuts] = React.useState(true);
  const [strikeMin, setStrikeMin] = React.useState<number | null>(null);
  const [strikeMax, setStrikeMax] = React.useState<number | null>(null);
  const [seriesKeys, setSeriesKeys] = React.useState<string[]>([]);
  const ticker = 'QQQ';

  React.useEffect(() => {
    const load = async () => {
      const res = await fetch(`/api/get-options-for-chart?ticker=${ticker}&date=${date}`);
      const json = await res.json();
      const rows: OptionRow[] = (json.data || []).map((r: { timestamp: string; market_price: number; option_symbol: string; option_type: 'CALL'|'PUT'; strike_price: number }) => ({
        timestamp: r.timestamp,
        market_price: Number(r.market_price),
        option_symbol: r.option_symbol,
        option_type: r.option_type,
        strike_price: Number(r.strike_price)
      }));

      if (!rows.length) { console.log('OptionsChart: no rows'); setData([]); setSeriesKeys([]); return; }

      // Determine strike bounds
      const strikes = rows.map(r => r.strike_price).sort((a,b)=>a-b);
      const minStrike = strikes[0];
      const maxStrike = strikes[strikes.length-1];
      setStrikeMin(prev => prev ?? minStrike);
      setStrikeMax(prev => prev ?? maxStrike);

      // Filter by type and strike range
      const filtered = rows.filter(r =>
        (showCalls && r.option_type==='CALL' || showPuts && r.option_type==='PUT') &&
        (strikeMin === null || r.strike_price >= strikeMin) &&
        (strikeMax === null || r.strike_price <= strikeMax)
      );

      // Choose up to 10 symbols centered around median strike
      const uniqueBySymbol: Record<string, number> = {};
      filtered.forEach(r => { uniqueBySymbol[r.option_symbol] = r.strike_price; });
      const selectedSymbols = Object.entries(uniqueBySymbol)
        .sort((a,b)=>a[1]-b[1])
        .slice(0, 10)
        .map(([sym])=>sym);
      setSeriesKeys(selectedSymbols);

      // Build wide table: minute bucket -> { timestamp, [symbol]: avg }
      const bucket: Record<string, Record<string, { sum:number; count:number }>> = {};
      for (const r of filtered) {
        if (!selectedSymbols.includes(r.option_symbol)) continue;
        const minute = r.timestamp.slice(0,16)+':00';
        bucket[minute] = bucket[minute] || {};
        bucket[minute][r.option_symbol] = bucket[minute][r.option_symbol] || { sum:0, count:0 };
        bucket[minute][r.option_symbol].sum += r.market_price;
        bucket[minute][r.option_symbol].count += 1;
      }
      const rowsWide: ChartPoint[] = Object.entries(bucket).map(([ts, symbols]) => {
        const row: ChartPoint = { timestamp: ts } as ChartPoint;
        Object.keys(symbols).forEach((sym) => {
          const agg = symbols[sym];
          (row as Record<string, number | string>)[sym] = agg.sum / agg.count;
        });
        return row;
      }).sort((a,b)=> (a.timestamp as string).localeCompare(b.timestamp as string));

      console.log('OptionsChart: symbols', selectedSymbols.length, selectedSymbols.slice(0,5));
      console.log('OptionsChart: rowsWide', rowsWide.length);
      // Fallback: if no symbol-specific data made it into rowsWide, show overall average
      if (selectedSymbols.length === 0 || rowsWide.every(r => Object.keys(r).length === 1)) {
        const byMinute: Record<string, { sum:number; count:number }> = {};
        for (const r of filtered) {
          const minute = r.timestamp.slice(0,16)+':00';
          byMinute[minute] = byMinute[minute] || { sum:0, count:0 };
          byMinute[minute].sum += r.market_price;
          byMinute[minute].count += 1;
        }
        const avgSeries: ChartPoint[] = Object.entries(byMinute).map(([ts, agg]) => ({ timestamp: ts, Average: agg.sum/agg.count }))
          .sort((a,b)=> (a.timestamp as string).localeCompare(b.timestamp as string));
        setSeriesKeys(['Average']);
        setData(avgSeries);
        return;
      }
      setData(rowsWide);
    };
    load();
  }, [date, showCalls, showPuts, strikeMin, strikeMax]);

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour: 'numeric', minute: '2-digit' });
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 text-sm flex-wrap">
        <label className="text-gray-700 dark:text-gray-200">Date</label>
        <input className="bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded px-2 py-1" type="date" value={date} onChange={(e)=>setDate(e.target.value)} />
        <label className="flex items-center gap-1 text-gray-700 dark:text-gray-200"><input type="checkbox" checked={showCalls} onChange={e=>setShowCalls(e.target.checked)} /> CALL</label>
        <label className="flex items-center gap-1 text-gray-700 dark:text-gray-200"><input type="checkbox" checked={showPuts} onChange={e=>setShowPuts(e.target.checked)} /> PUT</label>
        {strikeMin!==null && strikeMax!==null && (
          <div className="flex items-center gap-2">
            <span className="text-gray-700 dark:text-gray-200">Strikes:</span>
            <input className="bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded px-2 py-1 w-24" type="number" step="0.01" value={strikeMin} onChange={e=>setStrikeMin(Number(e.target.value))} />
            <span className="text-gray-500">to</span>
            <input className="bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded px-2 py-1 w-24" type="number" step="0.01" value={strikeMax} onChange={e=>setStrikeMax(Number(e.target.value))} />
          </div>
        )}
      </div>
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
          <XAxis dataKey="timestamp" tickFormatter={formatTime} stroke="#6B7280" style={{ fontSize: '12px' }} />
          <YAxis tickFormatter={(v)=>`$${v.toFixed(2)}`} stroke="#F59E0B" style={{ fontSize: '12px' }} label={{ value: 'Option Price', angle: -90, position: 'insideLeft', style: { fill: '#F59E0B' } }} />
          <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8, color: '#F9FAFB' }} formatter={(v)=>[`$${(v as number).toFixed(2)}`, 'Option Price']} />
          <Legend wrapperStyle={{ paddingTop: 8 }} />
          {seriesKeys.map((key, idx) => (
            <Line key={key} type="monotone" dataKey={key} stroke={palette[idx % palette.length]} strokeWidth={2} dot={false} name={key} isAnimationActive={false} />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

const palette = [
  '#F59E0B', '#EF4444', '#10B981', '#3B82F6', '#A855F7', '#F97316', '#22C55E', '#06B6D4', '#E11D48', '#8B5CF6'
];

