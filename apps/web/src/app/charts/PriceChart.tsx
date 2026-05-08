"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
  CrosshairMode,
} from "lightweight-charts";
import type { ChartBar, ChartMarker } from "@/lib/queries";

interface Props {
  bars: ChartBar[];
  markers: ChartMarker[];
  smaPeriod?: number;
}

/** Trailing simple moving average over bar closes. */
function computeSma(bars: ChartBar[], period: number): { time: number; value: number }[] {
  const out: { time: number; value: number }[] = [];
  for (let i = 0; i < bars.length; i++) {
    if (i + 1 < period) continue;
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += bars[j].close;
    out.push({ time: bars[i].time, value: sum / period });
  }
  return out;
}

/**
 * Cumulative session VWAP from typical price * volume. Falls back to the
 * supplied bar.vwap field when present (engine writes it for ibkr_live).
 */
function computeVwap(bars: ChartBar[]): { time: number; value: number }[] {
  let pv = 0, v = 0;
  return bars.map((b) => {
    if (b.vwap !== null) return { time: b.time, value: b.vwap };
    const typical = (b.high + b.low + b.close) / 3;
    pv += typical * b.volume;
    v += b.volume;
    return { time: b.time, value: v > 0 ? pv / v : b.close };
  });
}

export default function PriceChart({ bars, markers, smaPeriod = 9 }: Props) {
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
      rightPriceScale: { borderColor: "#e5e7eb" },
      timeScale: {
        borderColor: "#e5e7eb",
        timeVisible: true,
        secondsVisible: false,
      },
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    }) as ISeriesApi<"Candlestick">;

    const smaSeries = chart.addLineSeries({
      color: "#2563eb",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      title: `SMA${smaPeriod}`,
    });

    const vwapSeries = chart.addLineSeries({
      color: "#f59e0b",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      title: "VWAP",
    });

    if (bars.length > 0) {
      candleSeries.setData(
        bars.map((b) => ({
          time: b.time as Time,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
        })),
      );
      const sma = computeSma(bars, smaPeriod);
      smaSeries.setData(sma.map((s) => ({ time: s.time as Time, value: s.value })));
      const vwap = computeVwap(bars);
      vwapSeries.setData(vwap.map((s) => ({ time: s.time as Time, value: s.value })));

      const tvMarkers: SeriesMarker<Time>[] = markers.map((m) => {
        switch (m.kind) {
          case "signal_up":
            return {
              time: m.time as Time,
              position: "belowBar",
              color: "#10b981",
              shape: "arrowUp",
              text: m.label,
            };
          case "signal_down":
            return {
              time: m.time as Time,
              position: "aboveBar",
              color: "#ef4444",
              shape: "arrowDown",
              text: m.label,
            };
          case "buy_fill":
            return {
              time: m.time as Time,
              position: "belowBar",
              color: "#2563eb",
              shape: "circle",
              text: m.label,
            };
          case "sell_fill":
            return {
              time: m.time as Time,
              position: "aboveBar",
              color: "#7c3aed",
              shape: "circle",
              text: m.label,
            };
        }
      });
      candleSeries.setMarkers(tvMarkers);
      chart.timeScale().fitContent();
    }

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [bars, markers, smaPeriod]);

  return (
    <div className="relative">
      <div ref={containerRef} className="h-[480px] w-full" />
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-600">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-3 bg-green-500 rounded-sm" /> bullish bar
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-3 bg-red-500 rounded-sm" /> bearish bar
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-1 w-3 bg-blue-600" /> SMA{smaPeriod}
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-1 w-3 bg-amber-500" /> VWAP
        </span>
        <span className="inline-flex items-center gap-1">▲ cross UP</span>
        <span className="inline-flex items-center gap-1">▼ cross DOWN</span>
        <span className="inline-flex items-center gap-1">● BUY/SELL fill</span>
      </div>
    </div>
  );
}
