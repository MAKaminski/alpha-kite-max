'use client';

import { useState, useEffect } from 'react';
import { formatESTClock } from '@/lib/timezone';

export default function ESTClock() {
  const [time, setTime] = useState('--:--:--:--');

  useEffect(() => {
    const updateClock = () => {
      setTime(formatESTClock());
    };

    // Update immediately
    updateClock();

    // Update every 10ms for smooth millisecond display
    const interval = setInterval(updateClock, 10);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-gray-900 dark:bg-gray-950 rounded-lg px-6 py-3 border border-gray-700">
      <div className="text-xs font-medium text-gray-400 mb-1">EST Time</div>
      <div className="text-2xl font-mono font-bold text-green-400 tabular-nums">
        {time}
      </div>
    </div>
  );
}

