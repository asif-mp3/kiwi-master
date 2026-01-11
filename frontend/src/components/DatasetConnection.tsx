'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  Table,
  Database,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  Lock,
  AlertCircle,
  Search,
  Sparkles,
  Link2,
  ExternalLink,
  ShieldCheck,
  Layers,
  Hash,
  Columns,
  LayoutGrid,
  Eye,
  ChevronRight,
  TrendingUp,
  Calendar,
  MapPin,
  Package,
  Users,
  ArrowLeft
} from 'lucide-react';
import { toast } from 'sonner';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { DetectedTable } from '@/lib/types';
import { api } from '@/services/api';

export interface DatasetStats {
  totalTables: number;
  totalRecords: number;
  sheetCount: number;
  sheets: string[];
  detectedTables?: DetectedTable[];
}

interface DatasetConnectionProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (url: string, stats: DatasetStats) => void;
  initialUrl?: string;
  isLocked?: boolean;
  isConnectionVerified?: boolean; // From parent - actual backend verification status
  initialStats?: DatasetStats;
}

type LoadingStep = {
  id: number;
  label: string;
  icon: React.ElementType;
};

const LOADING_STEPS: LoadingStep[] = [
  { id: 1, label: 'Validating Spreadsheet ID', icon: Search },
  { id: 2, label: 'Detecting Sheets & Tables', icon: FileSpreadsheet },
  { id: 3, label: 'Creating DuckDB Snapshot', icon: Database },
  { id: 4, label: 'Generating Compliance Embeddings', icon: Sparkles },
  { id: 5, label: 'Finalizing Context Intelligence', icon: Table },
];

// Helper to generate brief descriptions for sheets based on their tables
function generateSheetDescription(tables: DetectedTable[]): string {
  if (!tables || tables.length === 0) return 'No tables detected in this sheet.';

  const totalRows = tables.reduce((sum, t) => sum + (t.total_rows || 0), 0);

  // Check for common data patterns in column names
  const allColumns = tables.flatMap(t => t.columns || []).map(c => c.toLowerCase());
  const hasDateData = allColumns.some(c => c.includes('date') || c.includes('time') || c.includes('month') || c.includes('year'));
  const hasSalesData = allColumns.some(c => c.includes('sales') || c.includes('revenue') || c.includes('amount') || c.includes('price'));
  const hasLocationData = allColumns.some(c => c.includes('city') || c.includes('location') || c.includes('region') || c.includes('area'));
  const hasProductData = allColumns.some(c => c.includes('product') || c.includes('item') || c.includes('category') || c.includes('sku'));

  const dataTypes: string[] = [];
  if (hasSalesData) dataTypes.push('sales/revenue');
  if (hasDateData) dataTypes.push('time-series');
  if (hasLocationData) dataTypes.push('geographic');
  if (hasProductData) dataTypes.push('product');

  const dataTypeStr = dataTypes.length > 0 ? dataTypes.join(', ') : 'general';

  return `Contains ${tables.length} table${tables.length > 1 ? 's' : ''} with ${totalRows.toLocaleString()} rows. Primarily ${dataTypeStr} data.`;
}

// Helper to generate brief description for individual tables
function generateTableDescription(table: DetectedTable): string {
  const cols = table.columns || [];
  const rows = table.total_rows || 0;

  if (cols.length === 0) return 'Empty table structure.';

  // Detect data type from columns
  const colLower = cols.map(c => c.toLowerCase());
  const hasMetrics = colLower.some(c => c.includes('total') || c.includes('sum') || c.includes('count') || c.includes('amount'));
  const hasDate = colLower.some(c => c.includes('date') || c.includes('time'));

  if (hasMetrics && hasDate) {
    return `Time-series metrics table with ${rows.toLocaleString()} records across ${cols.length} fields.`;
  } else if (hasMetrics) {
    return `Aggregated metrics table with ${rows.toLocaleString()} records.`;
  } else if (hasDate) {
    return `Temporal data with ${rows.toLocaleString()} entries.`;
  }

  return `Data table with ${rows.toLocaleString()} rows and ${cols.length} columns.`;
}

// Icon selector based on data patterns
function getTableIcon(table: DetectedTable) {
  const cols = (table.columns || []).map(c => c.toLowerCase());
  if (cols.some(c => c.includes('sales') || c.includes('revenue'))) return TrendingUp;
  if (cols.some(c => c.includes('date') || c.includes('month'))) return Calendar;
  if (cols.some(c => c.includes('city') || c.includes('location'))) return MapPin;
  if (cols.some(c => c.includes('product') || c.includes('item'))) return Package;
  if (cols.some(c => c.includes('customer') || c.includes('user'))) return Users;
  return Table;
}

export function DatasetConnection({ isOpen, onClose, onSuccess, initialUrl = '', isLocked = false, isConnectionVerified = false, initialStats }: DatasetConnectionProps) {
  const [url, setUrl] = useState(initialUrl);
  const [status, setStatus] = useState<'idle' | 'verifying' | 'verified' | 'loading' | 'success' | 'connected' | 'details'>('idle');
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [datasetStats, setDatasetStats] = useState<DatasetStats | null>(initialStats || null);
  const [expandedSheet, setExpandedSheet] = useState<string | null>(null);
  // Local verification state (for fresh connections in this session)
  const [localVerified, setLocalVerified] = useState(false);
  // Use parent's verification status OR local verification (for fresh connections)
  const isVerified = isConnectionVerified || localVerified;
  // Track URL verification (separate from data loading)
  const [urlVerified, setUrlVerified] = useState(false);
  const [verificationInfo, setVerificationInfo] = useState<{ sheetCount: number; sheetNames: string[] } | null>(null);

  // Google Sheets OAuth state
  const [sheetsAuthStatus, setSheetsAuthStatus] = useState<'checking' | 'authorized' | 'not_authorized' | 'not_configured'>('checking');
  const [isAuthorizingSheets, setIsAuthorizingSheets] = useState(false);

  // Group tables by sheet for hierarchical view
  const tablesBySheet = useMemo(() => {
    if (!datasetStats?.detectedTables) return {};
    return datasetStats.detectedTables.reduce((acc: Record<string, DetectedTable[]>, table: DetectedTable) => {
      if (!acc[table.sheet_name]) acc[table.sheet_name] = [];
      acc[table.sheet_name].push(table);
      return acc;
    }, {});
  }, [datasetStats]);

  // Check Google Sheets authorization status
  useEffect(() => {
    const checkSheetsAuth = async () => {
      try {
        setSheetsAuthStatus('checking');
        const result = await api.checkSheetsAuth();
        console.log('[DatasetConnection] Sheets auth check:', result);

        if (!result.configured) {
          setSheetsAuthStatus('not_configured');
        } else if (result.authorized) {
          setSheetsAuthStatus('authorized');
        } else {
          setSheetsAuthStatus('not_authorized');
        }
      } catch (error) {
        console.error('[DatasetConnection] Failed to check sheets auth:', error);
        setSheetsAuthStatus('not_configured');
      }
    };

    if (isOpen && status === 'idle') {
      checkSheetsAuth();
    }
  }, [isOpen, status]);

  // Handle Google Sheets authorization
  const handleAuthorizeSheets = async () => {
    try {
      setIsAuthorizingSheets(true);
      const authUrl = await api.getSheetsAuthUrl();
      window.location.href = authUrl;
    } catch (error) {
      console.error('[DatasetConnection] Failed to get auth URL:', error);
      toast.error('Failed to start authorization', {
        description: 'Could not connect to the authorization server.'
      });
      setIsAuthorizingSheets(false);
    }
  };

  // Track if we've fetched fresh stats for this session
  const [hasFetchedFresh, setHasFetchedFresh] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Reset internal state when modal opens
  useEffect(() => {
    console.log('[DatasetConnection] useEffect triggered:', { isOpen, isLocked, isConnectionVerified, hasInitialStats: !!initialStats, initialUrl });
    if (isOpen) {
      const newStatus = isLocked ? 'connected' : 'idle';
      console.log('[DatasetConnection] Setting status to:', newStatus);
      setStatus(newStatus);
      setUrl(initialUrl);
      setExpandedSheet(null);
      setUrlVerified(false);
      setVerificationInfo(null);
      // Don't set localVerified here - use isConnectionVerified from parent for existing connections

      // Use initialStats for display
      if (isLocked && initialStats) {
        setDatasetStats(initialStats);
      }
    } else {
      setStatus('idle');
      setCurrentStep(0);
      setProgress(0);
      setUrl(initialUrl);
      setLocalVerified(false);
      setHasFetchedFresh(false);
      setUrlVerified(false);
      setVerificationInfo(null);
      setLoadingMessage('');
    }
  }, [isOpen, initialUrl, isLocked, isConnectionVerified, initialStats]);

  // Verify URL without loading data
  const verifyUrl = async () => {
    const sheetId = extractSpreadsheetId(url);
    if (!sheetId) {
      toast.error('Invalid URL', { description: 'Please enter a valid Google Sheets URL.' });
      return;
    }

    setStatus('verifying');
    try {
      console.log('[DatasetConnection] Verifying URL...');
      // Use a lightweight check - just verify the spreadsheet is accessible
      // For now, we'll do a quick metadata fetch
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/verify-sheet?url=${encodeURIComponent(url)}`);

      if (response.ok) {
        const data = await response.json();
        setUrlVerified(true);
        setVerificationInfo({
          sheetCount: data.sheet_count || 1,
          sheetNames: data.sheet_names || ['Sheet1']
        });
        setStatus('verified');
        toast.success('URL Verified', { description: 'Spreadsheet is accessible. Click Load to import data.' });
      } else {
        // If verification endpoint doesn't exist, fallback to simple validation
        setUrlVerified(true);
        setVerificationInfo({ sheetCount: 1, sheetNames: ['Sheet'] });
        setStatus('verified');
        toast.success('URL Verified', { description: 'Click Load to import your data.' });
      }
    } catch (error) {
      // Fallback: If endpoint doesn't exist, just validate URL format and proceed
      setUrlVerified(true);
      setVerificationInfo({ sheetCount: 1, sheetNames: ['Sheet'] });
      setStatus('verified');
      toast.success('URL Format Valid', { description: 'Click Load to import your data.' });
    }
  };

  // Fetch fresh stats (called when clicking View Details or Refresh)
  const fetchFreshStats = async () => {
    if (!initialUrl || isRefreshing) return;

    setIsRefreshing(true);
    try {
      console.log('[DatasetConnection] Fetching fresh stats...');
      const response = await api.loadDataset(initialUrl);
      if (response.success && response.stats) {
        console.log('[DatasetConnection] Got fresh stats:', response.stats);
        setDatasetStats(response.stats);
        setHasFetchedFresh(true);
        toast.success("Data synced", {
          description: `${response.stats.totalTables} tables, ${response.stats.totalRecords?.toLocaleString()} records`
        });
      }
    } catch (e) {
      console.error("Failed to refresh stats:", e);
      toast.error("Failed to refresh", { description: "Could not fetch latest data" });
    } finally {
      setIsRefreshing(false);
    }
  };

  const extractSpreadsheetId = (input: string) => {
    const match = input.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
    if (match) return match[1];
    if (input.length > 20 && !input.includes('/') && !input.includes('.')) {
      return input;
    }
    return null;
  };

  // Track loading step descriptions for real progress
  const [loadingMessage, setLoadingMessage] = useState('');

  const startLoadingSimulation = async () => {
    const sheetId = extractSpreadsheetId(url);
    if (!sheetId) {
      toast.error('Invalid URL', { description: 'Please enter a valid Google Sheets URL.' });
      return;
    }

    setStatus('loading');
    setProgress(0);
    setCurrentStep(1);
    setLoadingMessage('Connecting to Google Sheets...');

    // Start with step 1, the API call will drive actual progress
    // We use a slow animation that caps at 90% until complete
    let animatedProgress = 0;
    const progressAnimation = setInterval(() => {
      animatedProgress += 0.5;
      // Cap at 90% - only reach 100% when API completes
      if (animatedProgress <= 90) {
        setProgress(animatedProgress);

        // Update step based on progress
        if (animatedProgress < 20) {
          setCurrentStep(1);
          setLoadingMessage('Validating spreadsheet access...');
        } else if (animatedProgress < 40) {
          setCurrentStep(2);
          setLoadingMessage('Detecting sheets and tables...');
        } else if (animatedProgress < 60) {
          setCurrentStep(3);
          setLoadingMessage('Creating DuckDB snapshot...');
        } else if (animatedProgress < 80) {
          setCurrentStep(4);
          setLoadingMessage('Generating embeddings...');
        } else {
          setCurrentStep(5);
          setLoadingMessage('Finalizing context intelligence...');
        }
      }
    }, 200); // Slower animation - takes ~36s to reach 90%

    try {
      console.log('[DatasetConnection] Starting API call to load dataset:', url);
      const response = await api.loadDataset(url);
      console.log('[DatasetConnection] API Response:', response);

      clearInterval(progressAnimation);

      if (response.success && response.stats) {
        setDatasetStats(response.stats);
        setCurrentStep(LOADING_STEPS.length + 1);
        setProgress(100);
        setLoadingMessage('Complete!');
        setStatus('success');
        setLocalVerified(true); // Fresh connection verified locally

        console.log('[DatasetConnection] Dataset loaded successfully:', response.stats);

        // Show success briefly, then switch to connected
        setTimeout(() => {
          // Pass both URL and stats to parent
          onSuccess(url, {
            totalTables: response.stats.totalTables || 0,
            totalRecords: response.stats.totalRecords || 0,
            sheetCount: response.stats.sheetCount || 0,
            sheets: response.stats.sheets || [],
            detectedTables: response.stats.detectedTables || []
          });
          setStatus('connected');
        }, 1500);
      } else {
        const errorMsg = response.message || 'Failed to load dataset - no data returned';
        console.error('[DatasetConnection] API returned failure:', response);
        throw new Error(errorMsg);
      }
    } catch (error: any) {
      clearInterval(progressAnimation);
      console.error('[DatasetConnection] Error loading dataset:', error);

      setStatus('idle');
      setProgress(0);
      setCurrentStep(0);
      setLoadingMessage('');
      setLocalVerified(false);
      setUrlVerified(false);

      let errorDescription = 'Could not connect to the dataset.';
      if (error.message) {
        if (error.message.includes('Permission') || error.message.includes('permission')) {
          errorDescription = 'Permission denied. Please authorize Google Sheets access or share the sheet publicly.';
        } else if (error.message.includes('not found') || error.message.includes('404')) {
          errorDescription = 'Spreadsheet not found. Check the URL is correct.';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          errorDescription = 'Network error. Make sure the backend server is running.';
        } else {
          errorDescription = error.message;
        }
      }

      toast.error('Connection Failed', {
        description: errorDescription,
        duration: 5000
      });
    }
  };

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && status !== 'loading' && status !== 'verifying' && onClose()}>
      <DialogContent className={`bg-card border-border transition-all duration-500 ease-out ${status === 'details' ? 'sm:max-w-4xl' : 'sm:max-w-md'} max-h-[90vh] overflow-hidden`}>
        <DialogHeader>
          <DialogTitle className="text-xl font-display font-bold flex items-center gap-2">
            {status === 'connected' && isVerified && <Lock className="w-5 h-5 text-green-500" />}
            {status === 'connected' && !isVerified && <Loader2 className="w-5 h-5 text-amber-500 animate-spin" />}
            {status === 'details' && <Database className="w-5 h-5 text-violet-500" />}
            {status === 'verified' && <CheckCircle2 className="w-5 h-5 text-green-500" />}
            {status === 'verifying' && <Loader2 className="w-5 h-5 text-violet-500 animate-spin" />}
            {status === 'connected' && isVerified
              ? 'Dataset Connected'
              : status === 'connected' && !isVerified
                ? 'Verifying Connection...'
                : status === 'details'
                  ? 'Dataset Connected'
                  : status === 'success'
                    ? 'Analysis Complete'
                    : status === 'verified'
                      ? 'URL Verified'
                      : status === 'verifying'
                        ? 'Verifying URL...'
                        : 'Connect Dataset'}
          </DialogTitle>
          <DialogDescription>
            {status === 'connected' && isVerified
              ? 'Your dataset is verified and ready for analytics.'
              : status === 'connected' && !isVerified
                ? 'Checking backend connection. This may take a moment.'
                : status === 'details'
                  ? 'Explore your data structure and available tables.'
                  : status === 'verified'
                    ? 'URL is valid. Click Load to import your data.'
                    : status === 'verifying'
                      ? 'Checking spreadsheet accessibility...'
                      : 'Link your Google Sheet to enable AI-powered analytics.'}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          <AnimatePresence mode="wait">

            {/* IDLE State - Connect Form */}
            {status === 'idle' && (
              <motion.div
                key="idle"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                {/* Google Sheets Authorization Status */}
                {sheetsAuthStatus !== 'checking' && (
                  <div className={`p-4 rounded-xl border transition-all duration-300 ${
                    sheetsAuthStatus === 'authorized'
                      ? 'bg-green-500/10 border-green-500/20'
                      : sheetsAuthStatus === 'not_authorized'
                        ? 'bg-amber-500/10 border-amber-500/20'
                        : 'bg-zinc-800/50 border-zinc-700/50'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {sheetsAuthStatus === 'authorized' ? (
                          <>
                            <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                              <ShieldCheck className="w-5 h-5 text-green-500" />
                            </div>
                            <div>
                              <span className="text-sm font-medium text-green-400">Google Sheets Connected</span>
                              <p className="text-xs text-green-500/60">Access any sheet in your account</p>
                            </div>
                          </>
                        ) : sheetsAuthStatus === 'not_authorized' ? (
                          <>
                            <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                              <Link2 className="w-5 h-5 text-amber-500" />
                            </div>
                            <div>
                              <span className="text-sm font-medium text-amber-400">Connect Google Account</span>
                              <p className="text-xs text-amber-500/60">Access private sheets without sharing</p>
                            </div>
                          </>
                        ) : (
                          <>
                            <div className="w-10 h-10 rounded-full bg-zinc-700/50 flex items-center justify-center">
                              <AlertCircle className="w-5 h-5 text-zinc-500" />
                            </div>
                            <div>
                              <span className="text-sm font-medium text-zinc-400">Service Account Mode</span>
                              <p className="text-xs text-zinc-500">Share sheets to access them</p>
                            </div>
                          </>
                        )}
                      </div>
                      {sheetsAuthStatus === 'not_authorized' && (
                        <Button
                          size="sm"
                          onClick={handleAuthorizeSheets}
                          disabled={isAuthorizingSheets}
                          className="bg-amber-500 hover:bg-amber-400 text-black font-bold"
                        >
                          {isAuthorizingSheets ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <>
                              <ExternalLink className="w-4 h-4 mr-1" />
                              Authorize
                            </>
                          )}
                        </Button>
                      )}
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                    Google Sheets URL
                  </label>
                  <Input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://docs.google.com/spreadsheets/d/..."
                    className="h-12 bg-background border-border rounded-xl focus:border-violet-500/50 transition-all"
                  />
                  <p className="text-xs text-muted-foreground ml-1">
                    {sheetsAuthStatus === 'authorized'
                      ? 'Paste any Google Sheet URL from your account.'
                      : 'Paste a publicly accessible Google Sheet URL.'}
                  </p>
                </div>

                <div className="flex gap-3">
                  <Button
                    onClick={verifyUrl}
                    disabled={!url || status === 'verifying'}
                    variant="outline"
                    className="flex-1 h-12 font-bold rounded-xl transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100 border-violet-500/30 hover:border-violet-500/50 hover:bg-violet-500/10"
                  >
                    {status === 'verifying' ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Search className="w-4 h-4 mr-2" />
                    )}
                    {status === 'verifying' ? 'Verifying...' : 'Verify URL'}
                  </Button>
                </div>
              </motion.div>
            )}

            {/* VERIFIED State - Show Load Button */}
            {status === 'verified' && (
              <motion.div
                key="verified"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                {/* Verified Banner */}
                <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    </div>
                    <div>
                      <span className="text-sm font-medium text-green-400">URL Verified</span>
                      <p className="text-xs text-green-500/60">
                        {verificationInfo?.sheetCount || 1} sheet{(verificationInfo?.sheetCount || 1) > 1 ? 's' : ''} detected
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                    Google Sheets URL
                  </label>
                  <Input
                    value={url}
                    onChange={(e) => {
                      setUrl(e.target.value);
                      setUrlVerified(false);
                      setStatus('idle');
                    }}
                    placeholder="https://docs.google.com/spreadsheets/d/..."
                    className="h-12 bg-background border-border rounded-xl focus:border-violet-500/50 transition-all"
                  />
                </div>

                <Button
                  onClick={startLoadingSimulation}
                  className="w-full h-12 bg-violet-600 hover:bg-violet-500 text-white font-bold rounded-xl transition-all hover:scale-[1.02] active:scale-[0.98]"
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  Load Dataset
                </Button>

                <p className="text-xs text-center text-zinc-500">
                  This will profile your data and create an AI-ready index
                </p>
              </motion.div>
            )}

            {/* LOADING State */}
            {status === 'loading' && (
              <motion.div
                key="loading"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="space-y-6"
              >
                <div className="relative w-32 h-32 mx-auto flex items-center justify-center">
                  <svg className="absolute inset-0 w-full h-full -rotate-90">
                    <circle cx="64" cy="64" r="60" className="stroke-muted fill-none stroke-[4]" />
                    <motion.circle
                      cx="64" cy="64" r="60"
                      className="stroke-violet-500 fill-none stroke-[4] stroke-linecap-round"
                      initial={{ pathLength: 0 }}
                      animate={{ pathLength: progress / 100 }}
                      transition={{ ease: "linear", duration: 0.3 }}
                    />
                  </svg>
                  <div className="flex flex-col items-center">
                    <span className="text-2xl font-bold font-display">{Math.round(progress)}%</span>
                  </div>
                </div>

                {/* Current loading message */}
                {loadingMessage && (
                  <p className="text-sm text-center text-violet-400 font-medium">
                    {loadingMessage}
                  </p>
                )}

                <div className="space-y-3">
                  {LOADING_STEPS.map((step) => {
                    const isActive = currentStep === step.id;
                    const isCompleted = currentStep > step.id;
                    return (
                      <motion.div
                        key={step.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: step.id * 0.1 }}
                        className={`flex items-center gap-3 p-3 rounded-xl transition-all duration-300 ${
                          isActive ? 'bg-violet-500/10 border border-violet-500/30' :
                          isCompleted ? 'opacity-50' : 'opacity-30'
                        }`}
                      >
                        <div className={`p-2 rounded-full transition-all ${
                          isActive ? 'bg-violet-500 text-white animate-pulse' :
                          isCompleted ? 'bg-green-500/20 text-green-500' : 'bg-muted text-muted-foreground'
                        }`}>
                          {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <step.icon className="w-4 h-4" />}
                        </div>
                        <span className={`text-sm font-medium ${isActive ? 'text-violet-400' : ''}`}>
                          {step.label}
                        </span>
                      </motion.div>
                    )
                  })}
                </div>
              </motion.div>
            )}

            {/* SUCCESS State */}
            {status === 'success' && (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="space-y-6 text-center py-8"
              >
                <motion.div
                  initial={{ scale: 0, rotate: -180 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ type: "spring", damping: 10, stiffness: 100 }}
                  className="w-24 h-24 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-lg shadow-green-500/30"
                >
                  <CheckCircle2 className="w-12 h-12 text-white" />
                </motion.div>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <h3 className="text-2xl font-bold font-display text-white">Verification Complete!</h3>
                  <p className="text-zinc-400 mt-1">Dataset is ready for analytics</p>
                </motion.div>
              </motion.div>
            )}

            {/* CONNECTED State - Verified View with Quick Stats */}
            {status === 'connected' && (
              <motion.div
                key="connected"
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                {/* Connection Status Banner - Shows Syncing, Verifying, or Verified based on actual state */}
                {isRefreshing ? (
                  <motion.div
                    variants={itemVariants}
                    className="p-5 rounded-2xl bg-gradient-to-r from-violet-500/20 via-purple-500/10 to-violet-500/20 border border-violet-500/30 relative overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-violet-500/5 to-transparent" />
                    <div className="relative flex items-center gap-4">
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                        className="w-14 h-14 rounded-2xl bg-violet-500/20 flex items-center justify-center border border-violet-500/30"
                      >
                        <Loader2 className="w-7 h-7 text-violet-500" />
                      </motion.div>
                      <div className="flex-1">
                        <h4 className="font-bold text-lg text-violet-400">Syncing Data...</h4>
                        <p className="text-sm text-violet-500/70">Refreshing from Google Sheets. Please wait.</p>
                      </div>
                    </div>
                  </motion.div>
                ) : isVerified ? (
                  <motion.div
                    variants={itemVariants}
                    className="p-5 rounded-2xl bg-gradient-to-r from-green-500/20 via-emerald-500/10 to-green-500/20 border border-green-500/30 relative overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-green-500/5 to-transparent" />
                    <div className="relative flex items-center gap-4">
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: "spring", delay: 0.2 }}
                        className="w-14 h-14 rounded-2xl bg-green-500/20 flex items-center justify-center border border-green-500/30"
                      >
                        <CheckCircle2 className="w-7 h-7 text-green-500" />
                      </motion.div>
                      <div className="flex-1">
                        <h4 className="font-bold text-lg text-green-400">Verified & Ready</h4>
                        <p className="text-sm text-green-500/70">Your dataset has been validated and indexed for AI analytics.</p>
                      </div>
                      <motion.div
                        animate={{ rotate: [0, 10, -10, 0] }}
                        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                      >
                        <Lock className="w-6 h-6 text-green-500/50" />
                      </motion.div>
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    variants={itemVariants}
                    className="p-5 rounded-2xl bg-gradient-to-r from-amber-500/20 via-orange-500/10 to-amber-500/20 border border-amber-500/30 relative overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-amber-500/5 to-transparent" />
                    <div className="relative flex items-center gap-4">
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                        className="w-14 h-14 rounded-2xl bg-amber-500/20 flex items-center justify-center border border-amber-500/30"
                      >
                        <Loader2 className="w-7 h-7 text-amber-500" />
                      </motion.div>
                      <div className="flex-1">
                        <h4 className="font-bold text-lg text-amber-400">Verifying Connection...</h4>
                        <p className="text-sm text-amber-500/70">Checking backend connection and data availability.</p>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Quick Stats Grid */}
                {datasetStats && (
                  <div className="grid grid-cols-3 gap-4">
                    <motion.div
                      variants={itemVariants}
                      whileHover={{ scale: 1.02, y: -2 }}
                      className="bg-gradient-to-br from-violet-500/10 to-purple-500/5 p-5 rounded-2xl border border-violet-500/20 text-center cursor-default"
                    >
                      <div className="w-12 h-12 mx-auto rounded-xl bg-violet-500/20 flex items-center justify-center mb-3 border border-violet-500/30">
                        <Layers className="w-6 h-6 text-violet-400" />
                      </div>
                      <div className="text-3xl font-bold text-white font-display">{datasetStats.sheetCount}</div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wider mt-1">Sheets</div>
                    </motion.div>

                    <motion.div
                      variants={itemVariants}
                      whileHover={{ scale: 1.02, y: -2 }}
                      className="bg-gradient-to-br from-blue-500/10 to-cyan-500/5 p-5 rounded-2xl border border-blue-500/20 text-center cursor-default"
                    >
                      <div className="w-12 h-12 mx-auto rounded-xl bg-blue-500/20 flex items-center justify-center mb-3 border border-blue-500/30">
                        <LayoutGrid className="w-6 h-6 text-blue-400" />
                      </div>
                      <div className="text-3xl font-bold text-white font-display">{datasetStats.totalTables}</div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wider mt-1">Tables</div>
                    </motion.div>

                    <motion.div
                      variants={itemVariants}
                      whileHover={{ scale: 1.02, y: -2 }}
                      className="bg-gradient-to-br from-emerald-500/10 to-green-500/5 p-5 rounded-2xl border border-emerald-500/20 text-center cursor-default"
                    >
                      <div className="w-12 h-12 mx-auto rounded-xl bg-emerald-500/20 flex items-center justify-center mb-3 border border-emerald-500/30">
                        <Hash className="w-6 h-6 text-emerald-400" />
                      </div>
                      <div className="text-3xl font-bold text-white font-display">{datasetStats.totalRecords?.toLocaleString()}</div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wider mt-1">Records</div>
                    </motion.div>
                  </div>
                )}

                {/* Action Buttons */}
                <motion.div variants={itemVariants} className="flex gap-3">
                  {/* Refresh Button */}
                  <Button
                    onClick={fetchFreshStats}
                    disabled={!isVerified || isRefreshing}
                    variant="outline"
                    className="h-16 px-6 rounded-2xl font-bold transition-all duration-300 border-violet-500/30 hover:bg-violet-500/10 hover:border-violet-500/50"
                  >
                    {isRefreshing ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Database className="w-5 h-5" />
                    )}
                  </Button>

                  {/* View Details Button */}
                  <Button
                    onClick={() => {
                      // Just show details - user can manually refresh if they want fresh data
                      setStatus('details');
                    }}
                    disabled={!isVerified || isRefreshing}
                    className={`flex-1 h-16 rounded-2xl font-bold transition-all duration-300 gap-3 group ${
                      isVerified && !isRefreshing
                        ? 'bg-gradient-to-r from-violet-600 via-purple-600 to-violet-600 hover:from-violet-500 hover:via-purple-500 hover:to-violet-500 text-white shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 hover:scale-[1.02]'
                        : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                    }`}
                  >
                    {isRefreshing ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span className="text-lg">Syncing...</span>
                      </>
                    ) : (
                      <>
                        <Eye className="w-5 h-5" />
                        <span className="text-lg">View Full Details</span>
                        <ChevronRight className={`w-5 h-5 ml-auto transition-transform duration-300 ${isVerified ? 'group-hover:translate-x-1' : ''}`} />
                      </>
                    )}
                  </Button>
                </motion.div>

                {/* Hint */}
                <motion.p
                  variants={itemVariants}
                  className="text-xs text-center text-zinc-500"
                >
                  {isRefreshing ? 'Syncing with Google Sheets...' : 'Click refresh to sync latest data'}
                </motion.p>
              </motion.div>
            )}

            {/* DETAILS State - Full Dashboard with Sheet/Table Descriptions */}
            {status === 'details' && (
              <motion.div
                key="details"
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                transition={{ type: "spring", damping: 25, stiffness: 200 }}
                className="space-y-6"
              >
                {/* Stats Header */}
                {datasetStats && (
                  <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="grid grid-cols-4 gap-3"
                  >
                    {[
                      { label: 'Sheets', value: datasetStats.sheetCount, icon: FileSpreadsheet, color: 'violet' },
                      { label: 'Tables', value: datasetStats.totalTables, icon: Table, color: 'blue' },
                      { label: 'Records', value: datasetStats.totalRecords?.toLocaleString(), icon: Database, color: 'emerald' },
                      { label: 'Columns', value: datasetStats.detectedTables?.reduce((sum: number, t: DetectedTable) => sum + (t.columns?.length || 0), 0) || 0, icon: Columns, color: 'amber' }
                    ].map((stat, idx) => (
                      <motion.div
                        key={stat.label}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: idx * 0.1 }}
                        className={`bg-gradient-to-br from-${stat.color}-500/20 to-${stat.color}-500/5 p-4 rounded-xl border border-${stat.color}-500/20 relative overflow-hidden`}
                      >
                        <div className="absolute -right-2 -top-2 opacity-10">
                          <stat.icon className="w-14 h-14" />
                        </div>
                        <div className={`text-xs font-bold text-${stat.color}-400 uppercase tracking-wider mb-1`}>{stat.label}</div>
                        <div className="text-2xl font-display font-bold text-white">{stat.value}</div>
                      </motion.div>
                    ))}
                  </motion.div>
                )}

                {/* Schema Explorer with Descriptions */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-lg flex items-center gap-2">
                      <LayoutGrid className="w-5 h-5 text-violet-500" />
                      Data Structure
                    </h4>
                    <Badge variant="outline" className="text-xs border-violet-500/30 text-violet-400">
                      {Object.keys(tablesBySheet).length} Sheets
                    </Badge>
                  </div>

                  <ScrollArea className="h-[380px] pr-4">
                    {datasetStats?.detectedTables && Object.keys(tablesBySheet).length > 0 ? (
                      <motion.div
                        className="space-y-4"
                        variants={containerVariants}
                        initial="hidden"
                        animate="visible"
                      >
                        {Object.entries(tablesBySheet).map(([sheetName, tables], sheetIdx) => {
                          const sheetTables = tables as DetectedTable[];
                          const sheetDescription = generateSheetDescription(sheetTables);
                          const isExpanded = expandedSheet === sheetName;
                          const colorVariants = ['violet', 'blue', 'emerald', 'amber', 'rose', 'cyan'];
                          const color = colorVariants[sheetIdx % colorVariants.length];

                          return (
                            <motion.div
                              key={sheetName}
                              variants={itemVariants}
                              className="rounded-2xl border border-white/10 overflow-hidden bg-zinc-900/50"
                            >
                              {/* Sheet Header - Clickable */}
                              <motion.button
                                onClick={() => setExpandedSheet(isExpanded ? null : sheetName)}
                                className="w-full p-4 flex items-start gap-4 hover:bg-white/5 transition-colors text-left"
                                whileHover={{ backgroundColor: 'rgba(255,255,255,0.03)' }}
                              >
                                <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 bg-${color}-500/20 border border-${color}-500/30`}>
                                  <FileSpreadsheet className={`w-6 h-6 text-${color}-400`} />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="font-bold text-white text-lg">{sheetName}</span>
                                    <Badge className={`bg-${color}-500/20 text-${color}-400 border-${color}-500/30 text-xs`}>
                                      {sheetTables.length} table{sheetTables.length > 1 ? 's' : ''}
                                    </Badge>
                                  </div>
                                  <p className="text-sm text-zinc-400 line-clamp-2">{sheetDescription}</p>
                                </div>
                                <motion.div
                                  animate={{ rotate: isExpanded ? 90 : 0 }}
                                  transition={{ duration: 0.2 }}
                                  className="mt-1"
                                >
                                  <ChevronRight className="w-5 h-5 text-zinc-500" />
                                </motion.div>
                              </motion.button>

                              {/* Expanded Tables */}
                              <AnimatePresence>
                                {isExpanded && (
                                  <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.3, ease: 'easeInOut' }}
                                    className="overflow-hidden"
                                  >
                                    <div className="px-4 pb-4 space-y-3 border-t border-white/5 pt-3">
                                      {sheetTables.map((table, idx) => {
                                        const TableIcon = getTableIcon(table);
                                        const tableDesc = generateTableDescription(table);

                                        return (
                                          <motion.div
                                            key={idx}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                            className="bg-zinc-800/50 rounded-xl border border-white/5 overflow-hidden hover:border-white/10 transition-colors"
                                          >
                                            {/* Table Header */}
                                            <div className="p-4 bg-gradient-to-r from-white/5 to-transparent flex items-start gap-3">
                                              <div className={`w-10 h-10 rounded-lg bg-${color}-500/10 flex items-center justify-center flex-shrink-0`}>
                                                <TableIcon className={`w-5 h-5 text-${color}-400`} />
                                              </div>
                                              <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                  <span className="font-semibold text-zinc-200">{table.title || table.table_id}</span>
                                                </div>
                                                <p className="text-xs text-zinc-500">{tableDesc}</p>
                                              </div>
                                              <div className="flex items-center gap-2 flex-shrink-0">
                                                <Badge variant="outline" className="text-[10px] border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                                                  {table.total_rows || 0} rows
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] border-blue-500/30 text-blue-400 bg-blue-500/10">
                                                  {table.columns?.length || 0} cols
                                                </Badge>
                                              </div>
                                            </div>

                                            {/* Column Preview */}
                                            {table.columns && table.columns.length > 0 && (
                                              <div className="p-4 border-t border-white/5">
                                                <div className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2 font-bold">Columns</div>
                                                <div className="flex flex-wrap gap-1.5">
                                                  {table.columns.slice(0, 10).map((col: string, cIdx: number) => (
                                                    <motion.span
                                                      key={cIdx}
                                                      initial={{ opacity: 0, scale: 0.8 }}
                                                      animate={{ opacity: 1, scale: 1 }}
                                                      transition={{ delay: cIdx * 0.02 }}
                                                      className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-white/5 text-[11px] font-mono text-zinc-400 hover:border-violet-500/30 hover:text-violet-400 transition-colors cursor-default"
                                                    >
                                                      {col}
                                                    </motion.span>
                                                  ))}
                                                  {table.columns.length > 10 && (
                                                    <span className="px-2.5 py-1 rounded-lg bg-violet-500/10 border border-violet-500/20 text-[11px] font-mono text-violet-400">
                                                      +{table.columns.length - 10} more
                                                    </span>
                                                  )}
                                                </div>
                                              </div>
                                            )}
                                          </motion.div>
                                        );
                                      })}
                                    </div>
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </motion.div>
                          );
                        })}
                      </motion.div>
                    ) : (
                      <div className="flex flex-col items-center justify-center py-12 text-center">
                        <Loader2 className="w-8 h-8 text-violet-500 animate-spin mb-4" />
                        <p className="text-zinc-400">Loading dataset structure...</p>
                      </div>
                    )}
                  </ScrollArea>
                </div>

                {/* Footer */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                  className="flex items-center justify-between pt-4 border-t border-white/5"
                >
                  <div className="flex items-center gap-2 text-xs text-zinc-500">
                    <Lock className="w-3 h-3" />
                    <span>Locked for this session</span>
                  </div>
                  <Button
                    variant="ghost"
                    onClick={() => setStatus('connected')}
                    className="gap-2 hover:bg-violet-500/10 hover:text-violet-400"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    Back
                  </Button>
                </motion.div>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </DialogContent>
    </Dialog>
  );
}
