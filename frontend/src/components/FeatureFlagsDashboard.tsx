'use client';

import React, { useState } from 'react';
import { featureFlags, FeatureFlag, useFeatureFlags } from '@/lib/featureFlags';

interface FeatureFlagsDashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function FeatureFlagsDashboard({ isOpen, onClose }: FeatureFlagsDashboardProps) {
  const flags = useFeatureFlags();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<FeatureFlag['category'] | 'all'>('all');
  const [showDependencies, setShowDependencies] = useState(false);
  const [importExportOpen, setImportExportOpen] = useState(false);
  const [exportData, setExportData] = useState('');
  const [importData, setImportData] = useState('');

  const categories: Array<{ id: FeatureFlag['category'] | 'all'; name: string; icon: string }> = [
    { id: 'all', name: 'All Features', icon: '🔧' },
    { id: 'ui', name: 'User Interface', icon: '🎨' },
    { id: 'data', name: 'Data & Analytics', icon: '📊' },
    { id: 'trading', name: 'Trading Engine', icon: '💰' },
    { id: 'experimental', name: 'Experimental', icon: '🧪' },
    { id: 'debug', name: 'Debug & Dev', icon: '🐛' }
  ];

  const filteredFlags = Object.values(flags).filter(flag => {
    const matchesSearch = flag.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         flag.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || flag.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleToggleFlag = (flagId: string, enabled: boolean) => {
    featureFlags.setFlag(flagId, enabled, 'admin');
  };

  const handleResetToDefaults = () => {
    if (confirm('Are you sure you want to reset all feature flags to their default values? This cannot be undone.')) {
      featureFlags.resetToDefaults();
    }
  };

  const handleExport = () => {
    const data = featureFlags.exportFlags();
    setExportData(data);
    setImportExportOpen(true);
  };

  const handleImport = () => {
    try {
      featureFlags.importFlags(importData);
      setImportData('');
      setImportExportOpen(false);
      alert('Feature flags imported successfully!');
    } catch {
      alert('Failed to import feature flags. Please check the JSON format.');
    }
  };

  const getCategoryColor = (category: FeatureFlag['category']) => {
    const colors = {
      ui: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
      data: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
      trading: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
      experimental: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
      debug: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
    };
    return colors[category];
  };

  const getDependencyStatus = (flag: FeatureFlag) => {
    if (!flag.dependencies || flag.dependencies.length === 0) return null;
    
    const dependencyStatus = flag.dependencies.map(depId => {
      const depFlag = flags[depId];
      return {
        id: depId,
        name: depFlag?.name || depId,
        enabled: featureFlags.isEnabled(depId)
      };
    });

    return dependencyStatus;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex">
      <div className="bg-white dark:bg-gray-800 w-full max-w-4xl h-full overflow-y-auto">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Feature Flags Dashboard
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Control which features are active in the application
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-2xl"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap gap-4 items-center">
            {/* Search */}
            <div className="flex-1 min-w-64">
              <input
                type="text"
                placeholder="Search features..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
              />
            </div>

            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as FeatureFlag['category'] | 'all')}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>
                  {cat.icon} {cat.name}
                </option>
              ))}
            </select>

            {/* Show Dependencies Toggle */}
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <input
                type="checkbox"
                checked={showDependencies}
                onChange={(e) => setShowDependencies(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600"
              />
              Show Dependencies
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 mt-4">
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
            >
              Export Flags
            </button>
            <button
              onClick={() => setImportExportOpen(true)}
              className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors"
            >
              Import Flags
            </button>
            <button
              onClick={handleResetToDefaults}
              className="px-4 py-2 bg-red-600 text-white text-sm rounded-md hover:bg-red-700 transition-colors"
            >
              Reset to Defaults
            </button>
          </div>
        </div>

        {/* Feature Flags List */}
        <div className="p-6">
          <div className="space-y-4">
            {filteredFlags.map(flag => {
              const dependencies = getDependencyStatus(flag);
              const isEnabled = featureFlags.isEnabled(flag.id);
              const canToggle = !dependencies || dependencies.every(dep => dep.enabled);

              return (
                <div
                  key={flag.id}
                  className={`border rounded-lg p-4 transition-colors ${
                    isEnabled
                      ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20'
                      : 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                          {flag.name}
                        </h3>
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getCategoryColor(flag.category)}`}>
                          {flag.category}
                        </span>
                        {!canToggle && (
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300">
                            Depends on disabled features
                          </span>
                        )}
                      </div>
                      
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                        {flag.description}
                      </p>

                      {/* Dependencies */}
                      {showDependencies && dependencies && (
                        <div className="mb-3">
                          <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            Dependencies:
                          </h4>
                          <div className="flex flex-wrap gap-1">
                            {dependencies.map(dep => (
                              <span
                                key={dep.id}
                                className={`px-2 py-1 text-xs rounded ${
                                  dep.enabled
                                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
                                    : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
                                }`}
                              >
                                {dep.name} {dep.enabled ? '✓' : '✗'}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        Last modified: {new Date(flag.lastModified).toLocaleString()} by {flag.modifiedBy}
                      </div>
                    </div>

                    {/* Toggle Switch */}
                    <div className="ml-4">
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={isEnabled}
                          onChange={(e) => handleToggleFlag(flag.id, e.target.checked)}
                          disabled={!canToggle}
                          className="sr-only peer"
                        />
                        <div className={`w-11 h-6 rounded-full peer transition-colors ${
                          isEnabled
                            ? 'bg-green-600 peer-checked:bg-green-600'
                            : 'bg-gray-200 dark:bg-gray-700'
                        } ${!canToggle ? 'opacity-50 cursor-not-allowed' : ''}`}>
                          <div className={`absolute top-0.5 left-0.5 bg-white rounded-full h-5 w-5 transition-transform ${
                            isEnabled ? 'translate-x-5' : 'translate-x-0'
                          }`}></div>
                        </div>
                      </label>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {filteredFlags.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-500 dark:text-gray-400">
                No features found matching your criteria
              </div>
            </div>
          )}
        </div>

        {/* Import/Export Modal */}
        {importExportOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 z-60 flex items-center justify-center">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Import/Export Feature Flags
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Export Data:
                  </label>
                  <textarea
                    value={exportData}
                    readOnly
                    className="w-full h-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-xs"
                  />
                  <button
                    onClick={() => navigator.clipboard.writeText(exportData)}
                    className="mt-2 px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                  >
                    Copy to Clipboard
                  </button>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Import Data:
                  </label>
                  <textarea
                    value={importData}
                    onChange={(e) => setImportData(e.target.value)}
                    placeholder="Paste feature flags JSON here..."
                    className="w-full h-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-xs"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setImportExportOpen(false)}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleImport}
                  disabled={!importData.trim()}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Import
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
