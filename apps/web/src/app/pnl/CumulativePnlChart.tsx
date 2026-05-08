"use client";

import { useEffect, useRef } from "react";
import {
  ColorType,
  CrosshairMode,
  createChart,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import type { DailyPnl } from "@/types/api";

interface Props {
  rows: ReadonlyArray<DailyPnl>;   // oldest -> newest
}

/**
 * Cumulative realized P&L plotted as a true time-series line. Mirrors the
 * ``createChart`` pattern from src/app/charts/PriceChart.tsx so the panels
 * feel consistent across the app.
 */
export default function CumulativePnlChart({ rows }: Props) {
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
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: {
        borderColor: "#e5e7eb",
        timeVisible: false,
        secondsVisible: false,
      },
    });
    chartRef.current = chart;

    chart.priceScale("right").applyOptions({
      borderColor: "#e5e7eb",
      scaleMargins: { top: 0.1, bottom: 0.1 },
    });

    const cumLine = chart.addLineSeries({
      color: "#2563eb",
      lineWidth: 2,
      priceLineVisible: true,
      lastValueVisible: true,
      title: "Cumulative $",
      priceScaleId: "right",
    });

    if (rows.length > 0) {
      let running = 0;
      const points = rows.map((r) => {
        const v = Number(r.realizedUsd);
        if (Number.isFinite(v)) running += v;
        return { time: r.tradingDay as Time, value: running };
      });
      cumLine.setData(points);
      chart.timeScale().fitContent();
    }

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [rows]);

  return <div ref={containerRef} className="h-[220px] w-full" />;
}
