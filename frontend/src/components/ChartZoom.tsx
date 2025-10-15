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

  return (
    <div className="flex items-center gap-4 mb-4">
      <div className="text-sm text-gray-600 dark:text-gray-400">
        <span className="font-medium">Chart Controls:</span>
        <span className="ml-2">
          {isZoomed ? 'Zoomed view active' : 'Drag to zoom into a time range'}
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
        💡 Tip: Click and drag across the chart to zoom into a specific time range
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
