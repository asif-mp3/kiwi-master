'use client';

import { motion } from 'framer-motion';
import { Message } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Square, Copy, Check, Volume2, Database, TableIcon, ChevronDown, ChevronUp, FileSpreadsheet, FileText, RefreshCw, AlertCircle } from 'lucide-react';
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { QueryPlanViewer } from './QueryPlanViewer';
import { DataChart } from './DataChart';
import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface MessageBubbleProps {
  message: Message;
  onPlay?: (text: string, messageId: string) => void;
  onStop?: () => void;
  onRetry?: (originalQuery: string) => void;
}

const ROWS_PER_PAGE = 20;

/**
 * Generate a descriptive export title from message metadata.
 * Uses visualization title, or generates from plan details.
 * Examples:
 *   - "Average Sales" (from visualization.title)
 *   - "December Sales Comparison" (generated from plan)
 *   - "Monthly Revenue Trend" (generated from plan)
 */
function generateExportTitle(message: Message): string {
  const metadata = message.metadata as Record<string, unknown> | undefined;

  // Priority 1: Use visualization title if available
  const viz = metadata?.visualization as Record<string, unknown> | undefined;
  if (viz?.title && typeof viz.title === 'string') {
    return viz.title;
  }

  // Priority 2: Generate from plan
  const plan = metadata?.plan as Record<string, unknown> | undefined;
  if (plan) {
    const parts: string[] = [];

    // Add aggregation function
    const aggFunc = plan.aggregation_function as string | undefined;
    if (aggFunc) {
      const funcMap: Record<string, string> = {
        'SUM': 'Total',
        'AVG': 'Average',
        'COUNT': 'Count of',
        'MAX': 'Maximum',
        'MIN': 'Minimum'
      };
      parts.push(funcMap[aggFunc.toUpperCase()] || aggFunc);
    }

    // Add aggregation column
    const aggCol = plan.aggregation_column as string | undefined;
    if (aggCol) {
      parts.push(aggCol.replace(/_/g, ' '));
    }

    // Add filter context (e.g., "in December")
    const filters = plan.subset_filters as Array<Record<string, unknown>> | undefined;
    if (filters && filters.length > 0) {
      const filter = filters[0];
      if (filter.value && filter.column) {
        parts.push(`in ${filter.value}`);
      }
    }

    // Add query type suffix
    const queryType = plan.query_type as string | undefined;
    if (queryType === 'trend') {
      parts.push('Trend');
    } else if (queryType === 'comparison') {
      parts.push('Comparison');
    } else if (queryType === 'rank') {
      parts.push('Ranking');
    }

    if (parts.length > 0) {
      return parts.join(' ');
    }
  }

  // Priority 3: Extract from response text (first meaningful phrase)
  const content = message.content;
  const firstLine = content.split('\n')[0];
  if (firstLine.length > 10 && firstLine.length < 60) {
    return firstLine;
  }

  return 'Data Export';
}

/**
 * Format raw column names from DuckDB into human-readable labels.
 * Examples:
 *   - "Total_Sales" → "Total Sales"
 *   - "customer_name" → "Customer Name"
 *   - "SUM(sales)" → "Total Sales"
 *   - "AVG(amount)" → "Average Amount"
 *   - "COUNT(*)" → "Count"
 *   - "payment_mode" → "Payment Mode"
 */
function formatColumnName(colName: string): string {
  if (!colName) return '';

  let formatted = colName;

  // Handle SQL aggregation functions
  const aggPatterns: [RegExp, string][] = [
    [/^SUM\((\w+)\)$/i, 'Total $1'],
    [/^AVG\((\w+)\)$/i, 'Average $1'],
    [/^COUNT\(\*\)$/i, 'Count'],
    [/^COUNT\((\w+)\)$/i, 'Count of $1'],
    [/^MAX\((\w+)\)$/i, 'Maximum $1'],
    [/^MIN\((\w+)\)$/i, 'Minimum $1'],
    [/^ROUND\((.+),\s*\d+\)$/i, '$1'], // ROUND(x, 2) → x
  ];

  for (const [pattern, replacement] of aggPatterns) {
    if (pattern.test(formatted)) {
      formatted = formatted.replace(pattern, replacement);
      break;
    }
  }

  // Replace underscores with spaces
  formatted = formatted.replace(/_/g, ' ');

  // Convert to Title Case
  formatted = formatted
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');

  // Common abbreviation fixes
  const fixes: Record<string, string> = {
    'Id': 'ID',
    'Qty': 'Quantity',
    'Amt': 'Amount',
    'Num': 'Number',
    'Pct': 'Percentage',
    'Avg': 'Average',
  };

  for (const [abbr, full] of Object.entries(fixes)) {
    formatted = formatted.replace(new RegExp(`\\b${abbr}\\b`, 'g'), full);
  }

  return formatted.trim();
}

/**
 * Format cell values for display (currency, large numbers, percentages)
 */
function formatCellValue(value: unknown, colName: string): string {
  if (value === null || value === undefined) return '-';

  // Check if it's a number
  if (typeof value === 'number') {
    const lowerCol = colName.toLowerCase();

    // Percentage columns
    if (lowerCol.includes('percent') || lowerCol.includes('pct') || lowerCol.includes('rate')) {
      return `${value.toFixed(2)}%`;
    }

    // Currency/amount columns - format with Indian numbering
    if (lowerCol.includes('sales') || lowerCol.includes('amount') ||
        lowerCol.includes('revenue') || lowerCol.includes('profit') ||
        lowerCol.includes('price') || lowerCol.includes('cost') ||
        lowerCol.includes('total') || lowerCol.includes('sum')) {
      return value.toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }

    // Large numbers
    if (Math.abs(value) >= 1000) {
      return value.toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }

    // Regular numbers
    return value.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  }

  return String(value);
}

export function MessageBubble({ message, onPlay, onStop, onRetry }: MessageBubbleProps) {
  const isAssistant = message.role === 'assistant';
  const isSystem = message.role === 'system';
  const [copied, setCopied] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  // Check if this message is currently being spoken
  const isSpeaking = message.isSpeaking || false;

  const handlePlayStop = useCallback(() => {
    if (isSpeaking) {
      // Currently speaking - stop it
      onStop?.();
    } else {
      // Not speaking - start playing (will stop any other playing audio)
      onPlay?.(message.content, message.id);
    }
  }, [isSpeaking, onStop, onPlay, message.content, message.id]);

  // Check if this message has data to display
  const hasData = message.metadata?.data && Array.isArray(message.metadata.data) && message.metadata.data.length > 0;
  const dataRows = message.metadata?.data || [];

  // Filter out technical/debugging columns that aren't useful to end users
  const technicalColumns = ['row_count', 'min_value', 'max_value', 'numerator', 'denominator', 'count'];
  const dataColumns = hasData
    ? Object.keys(dataRows[0]).filter(col => !technicalColumns.includes(col.toLowerCase()))
    : [];

  // Auto-show data table for "list" type queries (user asked to "list" or "show all")
  const queryType = message.metadata?.plan?.query_type;
  const isListQuery = queryType === 'list' || queryType === 'filter' || queryType === 'rank';
  const shouldAutoShowData = hasData && isListQuery && dataRows.length > 1;

  const [showDataTable, setShowDataTable] = useState(false);
  const hasAutoShown = useRef(false);

  // Pagination state
  const [visibleRows, setVisibleRows] = useState(ROWS_PER_PAGE);
  const hasMoreRows = dataRows.length > visibleRows;
  const displayedRows = dataRows.slice(0, visibleRows);

  // Error detection - check if message indicates an error
  const metadata = message.metadata as Record<string, unknown> | undefined;
  const isError = metadata?.error ||
    (message.content.toLowerCase().includes("sorry") && message.content.toLowerCase().includes("error")) ||
    message.content.toLowerCase().includes("couldn't process") ||
    message.content.toLowerCase().includes("failed to");
  const originalQuery = metadata?.originalQuery as string | undefined;

  // Load more rows handler
  const handleLoadMore = useCallback(() => {
    setVisibleRows(prev => prev + ROWS_PER_PAGE);
  }, []);

  // Auto-expand data table for list queries (only once when message renders with data)
  useEffect(() => {
    if (shouldAutoShowData && !hasAutoShown.current) {
      setShowDataTable(true);
      hasAutoShown.current = true;
    }
  }, [shouldAutoShowData]);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  // Format columns for display and export
  const formattedColumns = useMemo(() =>
    dataColumns.map(col => ({
      raw: col,
      display: formatColumnName(col)
    })),
    [dataColumns]
  );

  // Export to Excel function with formatted headers, title, and values
  const handleExportExcel = useCallback(() => {
    if (!hasData) return;

    // Generate descriptive title from query context
    const exportTitle = generateExportTitle(message);

    // Create formatted data with human-readable column names
    const formattedData = dataRows.map(row => {
      const formattedRow: Record<string, string> = {};
      for (const col of dataColumns) {
        const displayName = formatColumnName(col);
        formattedRow[displayName] = formatCellValue(row[col], col);
      }
      return formattedRow;
    });

    // Create worksheet with descriptive title
    const worksheet = XLSX.utils.json_to_sheet([]);

    // Add descriptive header at top
    XLSX.utils.sheet_add_aoa(worksheet, [
      [`Thara.ai - ${exportTitle}`],
      [`Generated: ${new Date().toLocaleString()}`],
      [], // Empty row
    ], { origin: 'A1' });

    // Add data starting at row 4
    XLSX.utils.sheet_add_json(worksheet, formattedData, { origin: 'A4' });

    // Auto-size columns based on content
    const colWidths = formattedColumns.map(col => ({
      wch: Math.max(col.display.length, 15)
    }));
    worksheet['!cols'] = colWidths;

    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, exportTitle.slice(0, 31)); // Excel sheet names max 31 chars

    // Generate filename with descriptive name and timestamp
    const timestamp = new Date().toISOString().slice(0, 10);
    const safeTitle = exportTitle.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 30);
    XLSX.writeFile(workbook, `thara_${safeTitle}_${timestamp}.xlsx`);
  }, [hasData, dataRows, dataColumns, formattedColumns, message]);

  // Export to PDF function with formatted headers and values
  const handleExportPDF = useCallback(() => {
    if (!hasData) return;

    // Generate descriptive title from query context
    const exportTitle = generateExportTitle(message);

    const doc = new jsPDF();

    // Add descriptive title
    doc.setFontSize(16);
    doc.text(`Thara.ai - ${exportTitle}`, 14, 15);

    // Add timestamp
    doc.setFontSize(10);
    doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 22);

    // Use formatted column headers
    const formattedHeaders = formattedColumns.map(col => col.display);

    // Create table with formatted headers and values
    autoTable(doc, {
      head: [formattedHeaders],
      body: dataRows.map(row => dataColumns.map(col =>
        formatCellValue(row[col], col)
      )),
      startY: 28,
      styles: { fontSize: 8 },
      headStyles: {
        fillColor: [139, 92, 246], // Violet color
        fontStyle: 'bold'
      },
      alternateRowStyles: {
        fillColor: [245, 245, 250]
      }
    });

    // Generate filename with descriptive name and timestamp
    const timestamp = new Date().toISOString().slice(0, 10);
    const safeTitle = exportTitle.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 30);
    doc.save(`thara_${safeTitle}_${timestamp}.pdf`);
  }, [hasData, dataRows, dataColumns, formattedColumns, message]);

  if (isSystem) {
    return (
      <div className="flex justify-center w-full my-6">
        <span className="text-[10px] uppercase tracking-[0.3em] text-zinc-600 font-bold">
          {message.content}
        </span>
      </div>
    );
  }

  const hasTamil = /[\u0B80-\u0BFF]/.test(message.content);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      className={cn(
        "flex w-full group",
        isAssistant ? "justify-start" : "justify-end"
      )}
    >
      <div
        className={cn(
          "max-w-[85%] md:max-w-[75%] relative",
          isAssistant ? "items-start" : "items-end flex flex-col"
        )}
      >
        {/* Avatar for Assistant */}
        {isAssistant && (
          <div className="flex items-center gap-3 mb-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center text-[10px] font-black text-white">
              T
            </div>
            <span className="text-xs font-semibold text-zinc-400">Thara</span>
          </div>
        )}

        <motion.div
          animate={{
            scale: isHovered ? 1.01 : 1,
            boxShadow: isHovered
              ? isAssistant
                ? '0 10px 40px rgba(139, 92, 246, 0.1)'
                : '0 10px 40px rgba(0, 0, 0, 0.3)'
              : '0 4px 20px rgba(0, 0, 0, 0.1)'
          }}
          transition={{ duration: 0.2 }}
          className={cn(
            "px-3 py-3 sm:px-5 sm:py-4 rounded-xl sm:rounded-2xl text-sm sm:text-[15px] leading-relaxed transition-all duration-300",
            isAssistant
              ? "bg-card/80 backdrop-blur-xl text-card-foreground border border-border rounded-tl-md"
              : "bg-gradient-to-br from-violet-600 to-violet-700 text-white shadow-lg rounded-tr-md"
          )}
        >
          <div className={cn(
            "whitespace-pre-wrap font-medium",
            hasTamil ? "leading-[1.9]" : "leading-relaxed"
          )}>
            {message.content}
          </div>

          <div className={cn(
            "mt-2 text-[10px] font-medium tracking-wide opacity-50",
            isAssistant ? "text-muted-foreground" : "text-violet-100"
          )}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </motion.div>

        {/* Action Buttons for User Messages - Copy only */}
        {!isAssistant && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-1.5 sm:mt-2 flex items-center gap-1 sm:gap-2"
          >
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleCopy}
              aria-label="Copy message"
              className={cn(
                "flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md sm:rounded-lg text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider transition-all",
                copied
                  ? "bg-green-500/20 text-green-400"
                  : "bg-white/10 text-violet-100 hover:bg-white/20 hover:text-white"
              )}
            >
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              <span className="hidden sm:inline">{copied ? 'Copied!' : 'Copy'}</span>
            </motion.button>
          </motion.div>
        )}

        {/* Action Buttons for Assistant Messages */}
        {isAssistant && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-1.5 sm:mt-2 flex items-center gap-1 sm:gap-2 flex-wrap"
          >
            {/* Play/Stop Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handlePlayStop}
              aria-label={isSpeaking ? 'Stop audio' : 'Play message audio'}
              className={cn(
                "flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md sm:rounded-lg text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider transition-all",
                isSpeaking
                  ? "bg-red-500/20 text-red-400"
                  : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {isSpeaking ? <Square className="w-3 h-3" /> : <Volume2 className="w-3 h-3" />}
              <span className="hidden sm:inline">{isSpeaking ? 'Stop' : 'Play'}</span>
            </motion.button>

            {/* Copy Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleCopy}
              aria-label="Copy message"
              className={cn(
                "flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md sm:rounded-lg text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider transition-all",
                copied
                  ? "bg-green-500/20 text-green-400"
                  : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              <span className="hidden sm:inline">{copied ? 'Copied!' : 'Copy'}</span>
            </motion.button>

            {message.metadata?.plan && (
              <Popover>
                <PopoverTrigger asChild>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    aria-label="View query plan"
                    className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md sm:rounded-lg text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider transition-all bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    <Database className="w-3 h-3" />
                    <span className="hidden sm:inline">Query Plan</span>
                  </motion.button>
                </PopoverTrigger>
                <PopoverContent className="w-[calc(100vw-2rem)] sm:w-96 max-w-96 p-3 sm:p-4 bg-zinc-950/95 backdrop-blur-xl border border-zinc-800 shadow-2xl rounded-xl">
                  <QueryPlanViewer plan={message.metadata.plan} />
                </PopoverContent>
              </Popover>
            )}

            {/* View Data Button - Show when data is available */}
            {hasData && (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowDataTable(!showDataTable)}
                aria-label={showDataTable ? "Hide data table" : "View data table"}
                className={cn(
                  "flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md sm:rounded-lg text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider transition-all",
                  showDataTable
                    ? "bg-violet-500/20 text-violet-400"
                    : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <TableIcon className="w-3 h-3" />
                <span className="hidden sm:inline">
                  {showDataTable ? 'Hide Data' : `View Data (${dataRows.length})`}
                </span>
                {showDataTable ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </motion.button>
            )}

            {/* Retry Button - Show when message is an error */}
            {isError && onRetry && originalQuery && (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => onRetry(originalQuery)}
                aria-label="Retry query"
                className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md sm:rounded-lg text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider transition-all bg-amber-500/20 text-amber-400 hover:bg-amber-500/30"
              >
                <RefreshCw className="w-3 h-3" />
                <span className="hidden sm:inline">Retry</span>
              </motion.button>
            )}
          </motion.div>
        )}

        {/* Data Visualization - Metric Card for single values */}
        {isAssistant && message.metadata?.visualization?.type === 'metric_card' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="mt-3 w-full"
          >
            <div className="bg-gradient-to-br from-violet-500/10 to-purple-500/10 dark:from-violet-950/30 dark:to-purple-950/30 border border-violet-500/20 rounded-xl p-6 text-center">
              <div className="text-sm text-muted-foreground mb-2">
                {message.metadata.visualization.title}
              </div>
              <div className="text-4xl font-bold bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
                {(() => {
                  const rawValue = message.metadata.visualization.data?.value;
                  const val = Number(rawValue);

                  // Handle NaN or invalid values - show the raw value as text
                  if (isNaN(val) || rawValue === null || rawValue === undefined) {
                    return typeof rawValue === 'string' ? rawValue : '-';
                  }

                  // Percentage display
                  if (message.metadata.visualization.data?.is_percentage) {
                    return `${val.toFixed(1)}%`;
                  }

                  // Check if this is a currency value (explicitly marked or large sales-type number)
                  const isCurrency = message.metadata.visualization.data?.is_currency === true;

                  // Currency display with Indian number formatting (only if marked as currency)
                  if (isCurrency) {
                    if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
                    if (val >= 100000) return `₹${(val / 100000).toFixed(2)} L`;
                    if (val >= 1000) return `₹${(val / 1000).toFixed(1)}K`;
                    return `₹${val.toLocaleString('en-IN')}`;
                  }

                  // Non-currency numbers (counts, quantities, etc.)
                  if (val >= 10000000) return `${(val / 10000000).toFixed(1)} Cr`;
                  if (val >= 100000) return `${(val / 100000).toFixed(1)} L`;
                  if (val >= 1000) return `${(val / 1000).toFixed(1)}K`;
                  return val.toLocaleString('en-IN');
                })()}
              </div>
              {message.metadata.visualization.data?.supporting_text && (
                <div className="text-xs text-muted-foreground mt-2">
                  {message.metadata.visualization.data.supporting_text}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Data Visualization Chart (for multi-row data) */}
        {isAssistant && message.metadata?.visualization && message.metadata.visualization.type !== 'metric_card' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="mt-3 w-full"
          >
            <DataChart visualization={message.metadata.visualization} />
          </motion.div>
        )}

        {/* Data Table - Expandable section below message */}
        {hasData && showDataTable && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="mt-3 w-full"
          >
            <div className="bg-zinc-900/90 backdrop-blur-xl border border-zinc-800 rounded-xl overflow-hidden">
              <div className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-400">
                  Data Results ({dataRows.length} rows)
                </span>
                <div className="flex items-center gap-2">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleExportExcel}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-all"
                  >
                    <FileSpreadsheet className="w-3 h-3" />
                    Excel
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleExportPDF}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-all"
                  >
                    <FileText className="w-3 h-3" />
                    PDF
                  </motion.button>
                </div>
              </div>
              <div className="max-h-80 overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent border-zinc-800">
                      {formattedColumns.map((col, i) => (
                        <TableHead
                          key={i}
                          className="text-xs font-semibold text-zinc-300 bg-zinc-800/50"
                        >
                          {col.display}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {displayedRows.map((row: Record<string, unknown>, rowIdx: number) => (
                      <TableRow key={rowIdx} className="border-zinc-800 hover:bg-zinc-800/30">
                        {formattedColumns.map((col, colIdx) => (
                          <TableCell
                            key={colIdx}
                            className="text-xs text-zinc-300 py-2"
                          >
                            {formatCellValue(row[col.raw], col.raw)}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {/* Pagination Footer */}
              <div className="px-4 py-2 border-t border-zinc-800 flex items-center justify-between">
                <span className="text-[10px] text-zinc-500">
                  Showing {displayedRows.length} of {dataRows.length} rows
                </span>
                {hasMoreRows && (
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleLoadMore}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-semibold bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 transition-all"
                  >
                    <ChevronDown className="w-3 h-3" />
                    Load More ({Math.min(ROWS_PER_PAGE, dataRows.length - visibleRows)})
                  </motion.button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
