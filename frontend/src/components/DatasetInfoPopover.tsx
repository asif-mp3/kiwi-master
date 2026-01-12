'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Info,
  Database,
  FileSpreadsheet,
  Table,
  Hash,
  CheckCircle2,
  Layers,
  ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DetectedTable } from '@/lib/types';

export interface DatasetInfo {
  totalTables: number;
  totalRecords: number;
  sheetCount: number;
  sheets: string[];
  detectedTables?: DetectedTable[];
}

interface DatasetInfoPopoverProps {
  datasetInfo: DatasetInfo | null;
  isConnected: boolean;
}

export function DatasetInfoPopover({ datasetInfo, isConnected }: DatasetInfoPopoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedSheet, setExpandedSheet] = useState<string | null>(null);

  // Group tables by sheet name
  const tablesBySheet = datasetInfo?.detectedTables?.reduce((acc: Record<string, DetectedTable[]>, table) => {
    if (!acc[table.sheet_name]) acc[table.sheet_name] = [];
    acc[table.sheet_name].push(table);
    return acc;
  }, {}) || {};

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            "h-9 w-9 sm:h-11 sm:w-11 rounded-xl glass border transition-all",
            isConnected
              ? "border-violet-500/50 bg-violet-500/10 hover:bg-violet-500/20"
              : "border-border hover:border-violet-500/30 hover:bg-accent"
          )}
        >
          <Info className={cn(
            "w-4 h-4 sm:w-5 sm:h-5",
            isConnected ? "text-violet-400" : "text-zinc-400"
          )} />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-80 sm:w-96 p-0 bg-card border-border shadow-xl"
        align="end"
        sideOffset={8}
      >
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="overflow-hidden"
          >
            {/* Header */}
            <div className="p-4 border-b border-border bg-gradient-to-r from-violet-500/10 to-transparent">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center border border-violet-500/30">
                  <Database className="w-5 h-5 text-violet-400" />
                </div>
                <div>
                  <h3 className="font-bold text-foreground flex items-center gap-2">
                    Dataset Info
                    {isConnected && (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    )}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {isConnected ? 'Demo data loaded' : 'No data connected'}
                  </p>
                </div>
              </div>
            </div>

            {datasetInfo ? (
              <>
                {/* Quick Stats */}
                <div className="p-4 grid grid-cols-3 gap-3">
                  <div className="text-center p-3 rounded-xl bg-violet-500/10 border border-violet-500/20">
                    <Layers className="w-4 h-4 text-violet-400 mx-auto mb-1" />
                    <div className="text-lg font-bold text-foreground">{datasetInfo.sheetCount}</div>
                    <div className="text-[10px] text-muted-foreground uppercase">Sheets</div>
                  </div>
                  <div className="text-center p-3 rounded-xl bg-blue-500/10 border border-blue-500/20">
                    <Table className="w-4 h-4 text-blue-400 mx-auto mb-1" />
                    <div className="text-lg font-bold text-foreground">{datasetInfo.totalTables}</div>
                    <div className="text-[10px] text-muted-foreground uppercase">Tables</div>
                  </div>
                  <div className="text-center p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                    <Hash className="w-4 h-4 text-emerald-400 mx-auto mb-1" />
                    <div className="text-lg font-bold text-foreground">
                      {datasetInfo.totalRecords > 1000
                        ? `${(datasetInfo.totalRecords / 1000).toFixed(1)}k`
                        : datasetInfo.totalRecords}
                    </div>
                    <div className="text-[10px] text-muted-foreground uppercase">Records</div>
                  </div>
                </div>

                {/* Sheets List */}
                <div className="px-4 pb-4">
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                    Loaded Sheets
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {datasetInfo.sheets.length > 0 ? (
                      datasetInfo.sheets.map((sheet, idx) => {
                        const sheetTables = tablesBySheet[sheet] || [];
                        const isExpanded = expandedSheet === sheet;
                        const totalRows = sheetTables.reduce((sum, t) => sum + (t.total_rows || 0), 0);

                        return (
                          <div key={idx} className="rounded-lg border border-border overflow-hidden">
                            <button
                              onClick={() => setExpandedSheet(isExpanded ? null : sheet)}
                              className="w-full flex items-center gap-3 p-3 hover:bg-accent/50 transition-colors text-left"
                            >
                              <FileSpreadsheet className="w-4 h-4 text-violet-400 flex-shrink-0" />
                              <div className="flex-1 min-w-0">
                                <span className="text-sm font-medium text-foreground truncate block">
                                  {sheet}
                                </span>
                                <span className="text-xs text-muted-foreground">
                                  {sheetTables.length} table{sheetTables.length !== 1 ? 's' : ''}
                                  {totalRows > 0 && ` • ${totalRows.toLocaleString()} rows`}
                                </span>
                              </div>
                              <motion.div
                                animate={{ rotate: isExpanded ? 90 : 0 }}
                                transition={{ duration: 0.2 }}
                              >
                                <ChevronRight className="w-4 h-4 text-muted-foreground" />
                              </motion.div>
                            </button>

                            {/* Expanded table details */}
                            <AnimatePresence>
                              {isExpanded && sheetTables.length > 0 && (
                                <motion.div
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  transition={{ duration: 0.2 }}
                                  className="overflow-hidden border-t border-border"
                                >
                                  <div className="p-2 bg-muted/30 space-y-1">
                                    {sheetTables.map((table, tIdx) => (
                                      <div
                                        key={tIdx}
                                        className="flex items-center justify-between px-3 py-2 rounded-md bg-background/50 text-xs"
                                      >
                                        <span className="font-medium text-foreground truncate">
                                          {table.title || table.table_id}
                                        </span>
                                        <div className="flex items-center gap-2 flex-shrink-0">
                                          <span className="text-emerald-400">
                                            {table.total_rows || 0} rows
                                          </span>
                                          <span className="text-blue-400">
                                            {table.columns?.length || 0} cols
                                          </span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        );
                      })
                    ) : (
                      <div className="text-center py-4 text-muted-foreground text-sm">
                        No sheets detected
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="p-8 text-center">
                <Database className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">
                  No dataset information available
                </p>
              </div>
            )}

            {/* Footer */}
            <div className="px-4 py-3 border-t border-border bg-muted/30">
              <p className="text-[10px] text-muted-foreground text-center">
                {isConnected
                  ? 'Demo data is pre-loaded and ready for queries'
                  : 'Connect a dataset to start analyzing'
                }
              </p>
            </div>
          </motion.div>
        </AnimatePresence>
      </PopoverContent>
    </Popover>
  );
}
