'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Database,
  FolderSync,
  FileSpreadsheet,
  FileText,
  FileType,
  Cloud,
  HardDrive,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Plus,
  ChevronRight,
  Layers,
  Hash,
  Clock,
  Wifi,
  WifiOff,
  Sparkles,
  ExternalLink,
  X,
  Link,
  ArrowLeft,
  Check,
  Upload
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { DataSource, DataSourceType, DataSourceStatus } from '@/lib/types';
import { api } from '@/services/api';

interface DataSourcesPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onAddSource?: () => void;
  onRefresh?: () => void;
}

// Source type configuration
const SOURCE_CONFIG: Record<DataSourceType, {
  icon: React.ElementType;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  description: string;
}> = {
  google_sheets: {
    icon: FileSpreadsheet,
    label: 'Google Sheets',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/30',
    description: 'Connect to a Google Spreadsheet',
  },
  google_drive_folder: {
    icon: FolderSync,
    label: 'Drive Folder',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
    description: 'Sync all files from a Drive folder',
  },
  google_drive_file: {
    icon: Cloud,
    label: 'Drive File',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
    description: 'Load a single file from Drive',
  },
  csv: {
    icon: FileText,
    label: 'CSV File',
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/20',
    borderColor: 'border-amber-500/30',
    description: 'Import comma-separated data',
  },
  excel: {
    icon: FileType,
    label: 'Excel File',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/20',
    borderColor: 'border-emerald-500/30',
    description: 'Import Excel spreadsheet',
  },
  dropbox: {
    icon: Cloud,
    label: 'Dropbox',
    color: 'text-sky-400',
    bgColor: 'bg-sky-500/20',
    borderColor: 'border-sky-500/30',
    description: 'Connect to Dropbox files',
  },
  onedrive: {
    icon: Cloud,
    label: 'OneDrive',
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-500/20',
    borderColor: 'border-indigo-500/30',
    description: 'Connect to OneDrive/SharePoint',
  },
  local: {
    icon: HardDrive,
    label: 'Local File',
    color: 'text-zinc-400',
    bgColor: 'bg-zinc-500/20',
    borderColor: 'border-zinc-500/30',
    description: 'Load from local filesystem',
  },
};

// Status configuration
const STATUS_CONFIG: Record<DataSourceStatus, {
  icon: React.ElementType;
  label: string;
  color: string;
  animate?: boolean;
}> = {
  connected: {
    icon: CheckCircle2,
    label: 'Connected',
    color: 'text-green-400',
  },
  syncing: {
    icon: Loader2,
    label: 'Syncing',
    color: 'text-blue-400',
    animate: true,
  },
  error: {
    icon: AlertCircle,
    label: 'Error',
    color: 'text-red-400',
  },
  disconnected: {
    icon: WifiOff,
    label: 'Disconnected',
    color: 'text-zinc-500',
  },
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function SourceCard({ source, index }: { source: DataSource; index: number }) {
  const config = SOURCE_CONFIG[source.type];
  const statusConfig = STATUS_CONFIG[source.status];
  const Icon = config.icon;
  const StatusIcon = statusConfig.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className={`
        relative overflow-hidden rounded-2xl border ${config.borderColor}
        bg-gradient-to-br from-zinc-900/80 to-zinc-900/40
        hover:border-opacity-60 transition-all duration-300
        group cursor-default
      `}
    >
      {/* Glow effect */}
      <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 ${config.bgColor} blur-xl`} />

      <div className="relative p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`
              w-12 h-12 rounded-xl ${config.bgColor} border ${config.borderColor}
              flex items-center justify-center
            `}>
              <Icon className={`w-6 h-6 ${config.color}`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-lg">{source.name}</span>
                {source.isAutoSync && (
                  <Badge className="bg-violet-500/20 text-violet-400 border-violet-500/30 text-[10px] px-1.5">
                    AUTO
                  </Badge>
                )}
              </div>
              <span className={`text-xs ${config.color} font-medium`}>{config.label}</span>
            </div>
          </div>

          {/* Status indicator */}
          <div className={`flex items-center gap-1.5 ${statusConfig.color}`}>
            <StatusIcon className={`w-4 h-4 ${statusConfig.animate ? 'animate-spin' : ''}`} />
            <span className="text-xs font-medium">{statusConfig.label}</span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Layers className="w-3.5 h-3.5 text-violet-400" />
            </div>
            <div className="text-xl font-bold text-white font-display">{source.tableCount}</div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Tables</div>
          </div>

          <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Hash className="w-3.5 h-3.5 text-blue-400" />
            </div>
            <div className="text-xl font-bold text-white font-display">
              {source.recordCount >= 1000
                ? `${(source.recordCount / 1000).toFixed(1)}K`
                : source.recordCount}
            </div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Records</div>
          </div>

          <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Clock className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-sm font-bold text-white">
              {source.lastSync ? formatTimeAgo(source.lastSync) : 'N/A'}
            </div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Last Sync</div>
          </div>
        </div>

        {/* URL preview */}
        {source.url && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-zinc-800/30 border border-white/5">
            <span className="text-xs text-zinc-500 truncate flex-1 font-mono">
              {source.url.length > 50 ? source.url.slice(0, 50) + '...' : source.url}
            </span>
            {source.url && (
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 rounded hover:bg-white/10 transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="w-3.5 h-3.5 text-zinc-500 hover:text-white" />
              </a>
            )}
          </div>
        )}

        {/* Error message */}
        {source.error && (
          <div className="mt-3 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-xs text-red-400">{source.error}</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// Add Source Dialog Component
function AddSourceDialog({
  onBack,
  onSuccess,
}: {
  onBack: () => void;
  onSuccess: () => void;
}) {
  const [mode, setMode] = useState<'url' | 'upload'>('url');
  const [url, setUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [detectedType, setDetectedType] = useState<DataSourceType | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loadedStats, setLoadedStats] = useState<{ tables: number; records: number } | null>(null);

  // Auto-detect source type from URL
  useEffect(() => {
    if (mode === 'url' && url.trim()) {
      const type = api.detectSourceType(url.trim());
      setDetectedType(type);
      setError(null);
    } else if (mode === 'upload' && selectedFile) {
      // Detect type from file extension
      const filename = selectedFile.name.toLowerCase();
      if (filename.endsWith('.csv')) {
        setDetectedType('csv');
      } else if (filename.endsWith('.xlsx') || filename.endsWith('.xls') || filename.endsWith('.xlsm')) {
        setDetectedType('excel');
      } else {
        setDetectedType('local');
      }
      setError(null);
    } else {
      setDetectedType(null);
    }
  }, [url, selectedFile, mode]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleConnect = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(false);

    try {
      let result;

      if (mode === 'upload' && selectedFile) {
        // Upload local file (replace existing data)
        result = await api.uploadFile(selectedFile, false);
      } else if (mode === 'url' && url.trim() && detectedType) {
        // Route to appropriate API based on source type (replace existing data)
        if (detectedType === 'google_drive_folder') {
          result = await api.syncDriveFolder(url.trim(), false);
        } else {
          result = await api.loadSource(url.trim(), false);
        }
      } else {
        setError('Please provide a URL or select a file');
        setIsLoading(false);
        return;
      }

      if (result.success) {
        setSuccess(true);
        setLoadedStats({
          tables: result.stats?.totalTables || 0,
          records: result.stats?.totalRecords || 0,
        });
        // Wait a moment to show success state, then callback
        setTimeout(() => {
          onSuccess();
        }, 1500);
      } else {
        setError(result.error || 'Failed to connect to data source');
      }
    } catch (e: any) {
      console.error('Connect error:', e);
      setError(e.message || 'Failed to connect to data source');
    } finally {
      setIsLoading(false);
    }
  };

  const config = detectedType ? SOURCE_CONFIG[detectedType] : null;
  const Icon = config?.icon || Link;
  const canConnect = mode === 'upload' ? !!selectedFile : (!!url.trim() && !!detectedType);

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="p-6"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          className="hover:bg-white/5"
          disabled={isLoading}
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h3 className="text-lg font-bold text-white">Add Data Source</h3>
          <p className="text-sm text-zinc-400">Paste any URL to connect</p>
        </div>
      </div>

      {/* Success State */}
      {success && loadedStats && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center justify-center py-12 text-center"
        >
          <div className="w-20 h-20 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center mb-6">
            <Check className="w-10 h-10 text-emerald-400" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Connected Successfully!</h3>
          <p className="text-zinc-400 mb-4">
            Loaded {loadedStats.tables} tables with {loadedStats.records.toLocaleString()} records
          </p>
        </motion.div>
      )}

      {/* Input Form */}
      {!success && (
        <>
          {/* Mode Tabs */}
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => { setMode('url'); setSelectedFile(null); }}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all ${
                mode === 'url'
                  ? 'bg-violet-500/20 text-violet-400 border border-violet-500/30'
                  : 'bg-zinc-800/50 text-zinc-400 border border-white/5 hover:border-white/10'
              }`}
              disabled={isLoading}
            >
              <Link className="w-4 h-4" />
              Paste URL
            </button>
            <button
              onClick={() => { setMode('upload'); setUrl(''); }}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all ${
                mode === 'upload'
                  ? 'bg-violet-500/20 text-violet-400 border border-violet-500/30'
                  : 'bg-zinc-800/50 text-zinc-400 border border-white/5 hover:border-white/10'
              }`}
              disabled={isLoading}
            >
              <Upload className="w-4 h-4" />
              Upload File
            </button>
          </div>

          {/* URL Input (when mode === 'url') */}
          {mode === 'url' && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-zinc-400 mb-2">
                Data Source URL
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2">
                  <Icon className={`w-5 h-5 ${config?.color || 'text-zinc-500'}`} />
                </div>
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://docs.google.com/spreadsheets/d/... or any URL"
                  className="w-full pl-11 pr-4 py-3 bg-zinc-800/50 border border-white/10 rounded-xl text-white placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20 transition-all"
                  disabled={isLoading}
                />
              </div>
            </div>
          )}

          {/* File Upload (when mode === 'upload') */}
          {mode === 'upload' && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-zinc-400 mb-2">
                Select File
              </label>
              <label
                className={`
                  flex flex-col items-center justify-center p-8 rounded-xl border-2 border-dashed
                  transition-all cursor-pointer
                  ${selectedFile
                    ? 'border-violet-500/50 bg-violet-500/5'
                    : 'border-white/10 hover:border-violet-500/30 hover:bg-violet-500/5'
                  }
                  ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
                `}
              >
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls,.xlsm,.pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                  disabled={isLoading}
                />
                {selectedFile ? (
                  <>
                    <div className={`w-12 h-12 rounded-xl ${config?.bgColor || 'bg-zinc-800'} flex items-center justify-center mb-3`}>
                      <Icon className={`w-6 h-6 ${config?.color || 'text-zinc-400'}`} />
                    </div>
                    <p className="text-white font-medium">{selectedFile.name}</p>
                    <p className="text-xs text-zinc-500 mt-1">
                      {(selectedFile.size / 1024).toFixed(1)} KB • Click to change
                    </p>
                  </>
                ) : (
                  <>
                    <Upload className="w-10 h-10 text-zinc-500 mb-3" />
                    <p className="text-zinc-400 font-medium">Click to select file</p>
                    <p className="text-xs text-zinc-500 mt-1">CSV, Excel, or PDF files supported</p>
                  </>
                )}
              </label>
            </div>
          )}

          {/* Detected Type Indicator */}
          {detectedType && config && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`mb-6 p-4 rounded-xl ${config.bgColor} border ${config.borderColor}`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg bg-zinc-900/50 flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${config.color}`} />
                </div>
                <div>
                  <div className={`font-semibold ${config.color}`}>{config.label}</div>
                  <div className="text-xs text-zinc-400">{config.description}</div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Supported Sources (only show for URL mode) */}
          {mode === 'url' && (
            <div className="mb-6">
              <p className="text-xs text-zinc-500 mb-3">Supported sources:</p>
              <div className="flex flex-wrap gap-2">
                {(['google_sheets', 'google_drive_folder', 'excel', 'csv', 'dropbox', 'onedrive'] as DataSourceType[]).map((type) => {
                  const typeConfig = SOURCE_CONFIG[type];
                  const TypeIcon = typeConfig.icon;
                  return (
                    <div
                      key={type}
                      className={`flex items-center gap-1.5 px-2 py-1 rounded-lg ${typeConfig.bgColor} border ${typeConfig.borderColor} opacity-60`}
                    >
                      <TypeIcon className={`w-3 h-3 ${typeConfig.color}`} />
                      <span className={`text-xs ${typeConfig.color}`}>{typeConfig.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20"
            >
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-red-400 font-medium">Connection Failed</p>
                  <p className="text-xs text-red-400/80 mt-1">{error}</p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Connect Button */}
          <Button
            onClick={handleConnect}
            disabled={!canConnect || isLoading}
            className="w-full bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white font-bold py-3 rounded-xl shadow-lg shadow-violet-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                {mode === 'upload' ? 'Uploading...' : 'Connecting...'}
              </>
            ) : (
              <>
                {mode === 'upload' ? <Upload className="w-4 h-4 mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
                {mode === 'upload' ? 'Upload & Connect' : 'Connect Data Source'}
              </>
            )}
          </Button>

          {/* Help Text */}
          <p className="text-xs text-zinc-500 text-center mt-4">
            {mode === 'upload'
              ? 'Files are processed securely and stored in your local database'
              : 'Make sure the file/folder is publicly accessible or shared with "Anyone with the link"'
            }
          </p>
        </>
      )}
    </motion.div>
  );
}

export function DataSourcesPanel({ isOpen, onClose, onAddSource, onRefresh }: DataSourcesPanelProps) {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalTables, setTotalTables] = useState(0);
  const [totalRecords, setTotalRecords] = useState(0);
  const [demoMode, setDemoMode] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);

  const fetchSources = useCallback(async () => {
    try {
      setIsLoading(true);
      const result = await api.getDataSources();
      if (result.success) {
        setSources(result.sources);
        setTotalTables(result.totalTables);
        setTotalRecords(result.totalRecords);
        setDemoMode(result.demoMode);
      }
    } catch (e) {
      console.error('Failed to fetch sources:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchSources();
    onRefresh?.();
    setIsRefreshing(false);
  };

  const handleAddSuccess = () => {
    setShowAddDialog(false);
    fetchSources();
    onRefresh?.();
  };

  useEffect(() => {
    if (isOpen) {
      fetchSources();
      setShowAddDialog(false);
    }
  }, [isOpen, fetchSources]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="relative w-full max-w-2xl max-h-[85vh] bg-zinc-900 border border-white/10 rounded-3xl shadow-2xl overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Show Add Dialog or Main Panel */}
          <AnimatePresence mode="wait">
            {showAddDialog ? (
              <motion.div
                key="add-dialog"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <AddSourceDialog
                  onBack={() => setShowAddDialog(false)}
                  onSuccess={handleAddSuccess}
                />
              </motion.div>
            ) : (
              <motion.div
                key="main-panel"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                {/* Header */}
                <div className="sticky top-0 z-10 bg-zinc-900/95 backdrop-blur-xl border-b border-white/5 p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
                        <Database className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h2 className="text-xl font-bold text-white font-display">Data Sources</h2>
                        <p className="text-sm text-zinc-400">
                          {sources.length} source{sources.length !== 1 ? 's' : ''} connected
                          {demoMode && <span className="text-violet-400 ml-2">• Demo Mode</span>}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefresh}
                        disabled={isRefreshing}
                        className="border-white/10 hover:bg-white/5"
                      >
                        <RefreshCw className={`w-4 h-4 mr-1.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                        Refresh
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={onClose}
                        className="hover:bg-white/5"
                      >
                        <X className="w-5 h-5" />
                      </Button>
                    </div>
                  </div>

                  {/* Global Stats */}
                  {!isLoading && sources.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-4 grid grid-cols-3 gap-3"
                    >
                      <div className="bg-gradient-to-br from-violet-500/10 to-purple-500/5 rounded-xl p-3 border border-violet-500/20">
                        <div className="flex items-center gap-2">
                          <Layers className="w-4 h-4 text-violet-400" />
                          <span className="text-xs text-zinc-400">Total Tables</span>
                        </div>
                        <div className="text-2xl font-bold text-white font-display mt-1">{totalTables}</div>
                      </div>

                      <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/5 rounded-xl p-3 border border-blue-500/20">
                        <div className="flex items-center gap-2">
                          <Hash className="w-4 h-4 text-blue-400" />
                          <span className="text-xs text-zinc-400">Total Records</span>
                        </div>
                        <div className="text-2xl font-bold text-white font-display mt-1">
                          {totalRecords >= 1000000
                            ? `${(totalRecords / 1000000).toFixed(1)}M`
                            : totalRecords >= 1000
                              ? `${(totalRecords / 1000).toFixed(1)}K`
                              : totalRecords}
                        </div>
                      </div>

                      <div className="bg-gradient-to-br from-emerald-500/10 to-green-500/5 rounded-xl p-3 border border-emerald-500/20">
                        <div className="flex items-center gap-2">
                          <Wifi className="w-4 h-4 text-emerald-400" />
                          <span className="text-xs text-zinc-400">Status</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                          <span className="text-lg font-bold text-emerald-400">Live</span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>

                {/* Content */}
                <ScrollArea className="h-[calc(85vh-200px)] p-6">
                  {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-12">
                      <Loader2 className="w-8 h-8 text-violet-500 animate-spin mb-4" />
                      <p className="text-zinc-400">Loading data sources...</p>
                    </div>
                  ) : sources.length === 0 ? (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex flex-col items-center justify-center py-12 text-center"
                    >
                      <div className="w-20 h-20 rounded-3xl bg-zinc-800 border border-white/10 flex items-center justify-center mb-6">
                        <Database className="w-10 h-10 text-zinc-600" />
                      </div>
                      <h3 className="text-xl font-bold text-white mb-2">No Data Sources</h3>
                      <p className="text-zinc-400 mb-6 max-w-sm">
                        Connect your first data source to start analyzing with AI-powered insights.
                      </p>
                      <Button
                        onClick={() => setShowAddDialog(true)}
                        className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white font-bold px-6 py-3 rounded-xl shadow-lg shadow-violet-500/25"
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        Add Data Source
                      </Button>
                    </motion.div>
                  ) : (
                    <div className="space-y-4">
                      {sources.map((source, idx) => (
                        <SourceCard key={source.id} source={source} index={idx} />
                      ))}

                      {/* Add more sources */}
                      <motion.button
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: sources.length * 0.1 }}
                        onClick={() => setShowAddDialog(true)}
                        className="w-full p-5 rounded-2xl border-2 border-dashed border-white/10 hover:border-violet-500/50 hover:bg-violet-500/5 transition-all duration-300 group"
                      >
                        <div className="flex items-center justify-center gap-3 text-zinc-500 group-hover:text-violet-400">
                          <Plus className="w-5 h-5" />
                          <span className="font-medium">Add Another Data Source</span>
                        </div>
                      </motion.button>
                    </div>
                  )}
                </ScrollArea>

                {/* Footer */}
                <div className="sticky bottom-0 bg-zinc-900/95 backdrop-blur-xl border-t border-white/5 p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                      <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                      <span>Plug-and-play data architecture</span>
                    </div>
                    <Button
                      onClick={onClose}
                      variant="ghost"
                      className="hover:bg-white/5"
                    >
                      Close
                    </Button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
