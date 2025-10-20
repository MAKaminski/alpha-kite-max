'use client';

import React from 'react';
import dynamic from 'next/dynamic';

const OptionsChart = dynamic(() => import('@/components/OptionsChartStandalone'), { ssr: false });

export default function OptionsPage() {
  return (
    <main className="max-w-7xl mx-auto p-4 space-y-4">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Options Chart</h1>
      <OptionsChart />
    </main>
  );
}


