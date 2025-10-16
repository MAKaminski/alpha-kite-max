'use client';

import { useState, useRef, useEffect } from 'react';
import { formatToEST } from '@/lib/timezone';

interface ChartZoomProps {
  data: { timestamp: string }[];
  onZoom: (startTime: string, endTime: string) => void;
  onReset: () => void;
  isZoomed: boolean;
}

export default function ChartZoom({ data, onZoom, onReset, isZoomed }: ChartZoomProps) {
  const [isSelecting, setIsSelecting] = useState(false);
  const [selectionStart, setSelectionStart] = useState<number | null>(null);
  const [selectionEnd, setSelectionEnd] = useState<number | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!chartRef.current) return;
    
    const rect = chartRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    setIsSelecting(true);
    setSelectionStart(x);
    setSelectionEnd(x);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isSelecting || !chartRef.current) return;
    
    const rect = chartRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    setSelectionEnd(x);
  };

  const handleMouseUp = () => {
    if (!isSelecting || !selectionStart || !selectionEnd) {
      setIsSelecting(false);
      return;
    }

    // Calculate time range from pixel positions
    const startX = Math.min(selectionStart, selectionEnd);
    const endX = Math.max(selectionStart, selectionEnd);
    
    if (endX - startX < 50) { // Minimum selection width
      setIsSelecting(false);
      return;
    }

    // Convert pixel positions to time values
    const chartWidth = chartRef.current?.offsetWidth || 1;
    const dataLength = data.length;
    
    const startIndex = Math.floor((startX / chartWidth) * dataLength);
    const endIndex = Math.floor((endX / chartWidth) * dataLength);
    
    if (startIndex >= 0 && endIndex < dataLength && startIndex < endIndex) {
      const startTime = data[startIndex].timestamp;
      const endTime = data[endIndex].timestamp;
      
      onZoom(startTime, endTime);
    }

    setIsSelecting(false);
    setSelectionStart(null);
    setSelectionEnd(null);
  };

  const getSelectionStyle = () => {
    if (!isSelecting || !selectionStart || !selectionEnd) return {};
    
    const startX = Math.min(selectionStart, selectionEnd);
    const endX = Math.max(selectionStart, selectionEnd);
    
    return {
      position: 'absolute' as const,
      left: startX,
      width: endX - startX,
      top: 0,
      bottom: 0,
      backgroundColor: 'rgba(59, 130, 246, 0.2)',
      border: '1px solid rgba(59, 130, 246, 0.5)',
      pointerEvents: 'none' as const,
      zIndex: 10,
    };
  };

  return (
    <div className="flex items-center gap-4 mb-4">
      <div className="text-sm text-gray-600 dark:text-gray-400">
        <span className="font-medium">Chart Controls:</span>
        <span className="ml-2">
          {isZoomed ? 'Zoomed view active' : 'Click and drag to zoom'}
        </span>
      </div>
      
      {isZoomed && (
        <button
          onClick={onReset}
          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
        >
          Reset Zoom
        </button>
      )}
      
      <div className="text-xs text-gray-500 dark:text-gray-500">
        💡 Tip: Click and drag across the chart area to zoom into a specific time range
      </div>
      
      {/* Invisible overlay for mouse events */}
      <div
        ref={chartRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 5,
          cursor: isSelecting ? 'crosshair' : 'default'
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Selection overlay */}
        {isSelecting && (
          <div style={getSelectionStyle()} />
        )}
      </div>
    </div>
  );
}

export function useChartZoom(data: { timestamp: string }[]) {
  const [zoomedData, setZoomedData] = useState<{ timestamp: string }[]>(data);
  const [isZoomed, setIsZoomed] = useState(false);

  const handleZoom = (startTime: string, endTime: string) => {
    const filtered = data.filter(point => 
      point.timestamp >= startTime && point.timestamp <= endTime
    );
    
    if (filtered.length > 0) {
      setZoomedData(filtered);
      setIsZoomed(true);
    }
  };

  const handleReset = () => {
    setZoomedData(data);
    setIsZoomed(false);
  };

  useEffect(() => {
    setZoomedData(data);
    setIsZoomed(false);
  }, [data]);

  return {
    zoomedData,
    isZoomed,
    handleZoom,
    handleReset
  };
}
