"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import type { DayPnl } from "@/lib/queries";

interface Props {
  rows: DayPnl[];
}

export default function DailyPnlChart({ rows }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#111827",
        fontSize: 12,
      },
      grid: {
        vertLines: { color: "#f3f4f6" },
        horzLines: { color: "#f3f4f6" },
      },
      rightPriceScale: { borderColor: "#e5e7eb" },
      timeScale: {
        borderColor: "#e5e7eb",
        timeVisible: false,
        secondsVisible: false,
      },
    });
    chartRef.current = chart;

    const histogram = chart.addHistogramSeries({
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      priceLineVisible: false,
      lastValueVisible: true,
      title: "Realized $",
    });
    const cumLine = chart.addLineSeries({
      color: "#2563eb",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      title: "Cumulative $",
    });

    if (rows.length > 0) {
      histogram.setData(
        rows.map((r) => ({
          time: r.day as Time,
          value: r.realizedUsd,
          color: r.realizedUsd >= 0 ? "#10b981" : "#ef4444",
        })),
      );
      cumLine.setData(rows.map((r) => ({ time: r.day as Time, value: r.cumulativeUsd })));
      chart.timeScale().fitContent();
    }

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [rows]);

  return (
    <div className="relative">
      <div ref={containerRef} className="h-[280px] w-full" />
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-600">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-3 bg-green-500 rounded-sm" /> winning day
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-3 bg-red-500 rounded-sm" /> losing day
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-1 w-3 bg-blue-600" /> cumulative P&amp;L
        </span>
      </div>
    </div>
  );
}
