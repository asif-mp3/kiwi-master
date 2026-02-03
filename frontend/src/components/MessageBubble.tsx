'use client';

import { motion } from 'framer-motion';
import { Message } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Square, Copy, Check, Volume2, Database, TableIcon, ChevronDown, ChevronUp, FileSpreadsheet, FileText } from 'lucide-react';
import { useState, useEffect, useRef, useCallback } from 'react';
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
}

export function MessageBubble({ message, onPlay, onStop }: MessageBubbleProps) {
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
  const dataColumns = hasData ? Object.keys(dataRows[0]) : [];

  // Auto-show data table for "list" type queries (user asked to "list" or "show all")
  const queryType = message.metadata?.plan?.query_type;
  const isListQuery = queryType === 'list' || queryType === 'filter' || queryType === 'rank';
  const shouldAutoShowData = hasData && isListQuery && dataRows.length > 1;

  const [showDataTable, setShowDataTable] = useState(false);
  const hasAutoShown = useRef(false);

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

  // Export to Excel function
  const handleExportExcel = useCallback(() => {
    if (!hasData) return;

    const worksheet = XLSX.utils.json_to_sheet(dataRows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Data');

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(workbook, `thara_export_${timestamp}.xlsx`);
  }, [hasData, dataRows]);

  // Export to PDF function
  const handleExportPDF = useCallback(() => {
    if (!hasData) return;

    const doc = new jsPDF();

    // Add title
    doc.setFontSize(16);
    doc.text('Thara.ai - Data Export', 14, 15);

    // Add timestamp
    doc.setFontSize(10);
    doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 22);

    // Create table
    autoTable(doc, {
      head: [dataColumns],
      body: dataRows.map(row => dataColumns.map(col =>
        row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'
      )),
      startY: 28,
      styles: { fontSize: 8 },
      headStyles: { fillColor: [139, 92, 246] }, // Violet color
    });

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().slice(0, 10);
    doc.save(`thara_export_${timestamp}.pdf`);
  }, [hasData, dataRows, dataColumns]);

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
          </motion.div>
        )}

        {/* Data Visualization Chart */}
        {isAssistant && message.metadata?.visualization && (
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
                      {dataColumns.map((col, i) => (
                        <TableHead
                          key={i}
                          className="text-xs font-semibold text-zinc-300 bg-zinc-800/50"
                        >
                          {col}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dataRows.map((row: Record<string, unknown>, rowIdx: number) => (
                      <TableRow key={rowIdx} className="border-zinc-800 hover:bg-zinc-800/30">
                        {dataColumns.map((col, colIdx) => (
                          <TableCell
                            key={colIdx}
                            className="text-xs text-zinc-300 py-2"
                          >
                            {row[col] !== null && row[col] !== undefined
                              ? String(row[col])
                              : '-'}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
