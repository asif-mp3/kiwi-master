'use client';

import { useState, useMemo } from 'react';
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
  Hash,
  CheckCircle2,
  Layers,
  ChevronRight,
  BarChart3,
  Shield,
  Cloud,
  HardDrive,
  FileText,
  FileType,
  FolderSync,
  Sparkles,
  Calendar,
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { cn } from '@/lib/utils';
import { DetectedTable, TableProfileSummary } from '@/lib/types';

export interface DatasetInfo {
  totalTables: number;
  totalRecords: number;
  sheetCount: number;
  sheets: string[];
  detectedTables?: DetectedTable[];
  tableProfiles?: TableProfileSummary[];
  sourceType?: string;
  smartSuggestions?: string[];
}

interface DatasetInfoPopoverProps {
  datasetInfo: DatasetInfo | null;
  isConnected: boolean;
  onClick?: () => void;
  onSuggestionClick?: (text: string) => void;
}

// Source type display config
const SOURCE_TYPE_LABELS: Record<string, { label: string; icon: React.ElementType }> = {
  demo: { label: 'Demo Data', icon: Database },
  google_sheets: { label: 'Google Sheets', icon: FileSpreadsheet },
  google_drive_folder: { label: 'Drive Folder', icon: FolderSync },
  google_drive_file: { label: 'Drive File', icon: Cloud },
  csv: { label: 'CSV File', icon: FileText },
  excel: { label: 'Excel File', icon: FileType },
  dropbox: { label: 'Dropbox', icon: Cloud },
  onedrive: { label: 'OneDrive', icon: Cloud },
  local: { label: 'Local File', icon: HardDrive },
  unknown: { label: 'Connected', icon: Database },
};

// Table type badge colors
const TABLE_TYPE_COLORS: Record<string, string> = {
  transactional: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
  summary: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  category_breakdown: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  pivot: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  item_level: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  lookup: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
  unknown: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
};

// Donut chart colors
const ROLE_COLORS = {
  metrics: '#a78bfa',    // violet-400
  dimensions: '#60a5fa', // blue-400
  dates: '#34d399',      // emerald-400
  identifiers: '#9ca3af', // gray-400
};

function cleanTableName(name: string): string {
  // Remove common prefixes like "Dataset_2_" or "filename__"
  let clean = name;
  if (clean.includes('__')) {
    clean = clean.split('__').pop() || clean;
  }
  // Remove "Dataset_N_" prefix
  clean = clean.replace(/^Dataset_\d+_/i, '');
  return clean.replace(/_/g, ' ');
}

function formatDateRange(range: { min: string; max: string } | null): string | null {
  if (!range?.min || !range?.max) return null;
  const fmt = (d: string) => {
    const date = new Date(d);
    if (isNaN(date.getTime())) return d;
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[date.getMonth()]} ${date.getFullYear()}`;
  };
  const start = fmt(range.min);
  const end = fmt(range.max);
  return start === end ? start : `${start} – ${end}`;
}

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

// Quality score circle
function QualityCircle({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const circumference = 2 * Math.PI * 14;
  const dashOffset = circumference - (pct / 100) * circumference;
  const color = pct >= 80 ? 'text-emerald-400' : pct >= 60 ? 'text-amber-400' : 'text-red-400';
  const bgColor = pct >= 80 ? 'text-emerald-500/20' : pct >= 60 ? 'text-amber-500/20' : 'text-red-500/20';

  return (
    <div className="relative w-9 h-9">
      <svg width="36" height="36" viewBox="0 0 36 36" className="transform -rotate-90">
        <circle cx="18" cy="18" r="14" fill="none" strokeWidth="3"
          stroke="currentColor" className={bgColor} />
        <circle cx="18" cy="18" r="14" fill="none" strokeWidth="3"
          stroke="currentColor" className={color}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round" />
      </svg>
      <span className={`absolute inset-0 flex items-center justify-center text-[9px] font-bold ${color}`}>
        {pct}
      </span>
    </div>
  );
}

export function DatasetInfoPopover({ datasetInfo, isConnected, onClick, onSuggestionClick }: DatasetInfoPopoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedTable, setExpandedTable] = useState<string | null>(null);

  const profiles = datasetInfo?.tableProfiles || [];
  const hasProfiles = profiles.length > 0;

  // Aggregate column role counts across all tables
  const columnBreakdown = useMemo(() => {
    if (!hasProfiles) return [];
    const totals = { metrics: 0, dimensions: 0, dates: 0, identifiers: 0 };
    profiles.forEach(p => {
      totals.metrics += p.metrics.length;
      totals.dimensions += p.dimensions.length;
      totals.dates += p.date_columns.length;
      totals.identifiers += p.identifiers.length;
    });
    return [
      { name: 'Metrics', value: totals.metrics, color: ROLE_COLORS.metrics },
      { name: 'Dimensions', value: totals.dimensions, color: ROLE_COLORS.dimensions },
      { name: 'Dates', value: totals.dates, color: ROLE_COLORS.dates },
      { name: 'IDs', value: totals.identifiers, color: ROLE_COLORS.identifiers },
    ].filter(d => d.value > 0);
  }, [profiles, hasProfiles]);

  // Total columns across all tables
  const totalColumns = useMemo(() => {
    return profiles.reduce((sum, p) => sum + p.column_count, 0);
  }, [profiles]);

  // Average quality score
  const avgQuality = useMemo(() => {
    if (!hasProfiles) return 0;
    return profiles.reduce((sum, p) => sum + p.data_quality_score, 0) / profiles.length;
  }, [profiles, hasProfiles]);

  // Source type display
  const sourceConfig = SOURCE_TYPE_LABELS[datasetInfo?.sourceType || 'unknown'] || SOURCE_TYPE_LABELS.unknown;
  const SourceIcon = sourceConfig.icon;

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
        className="w-80 sm:w-[420px] p-0 bg-card border-border shadow-xl"
        align="end"
        sideOffset={8}
      >
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="overflow-hidden max-h-[75vh] flex flex-col"
          >
            {/* Header */}
            <div className="p-4 border-b border-border bg-gradient-to-r from-violet-500/10 to-transparent flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center border border-violet-500/30">
                  <SourceIcon className="w-5 h-5 text-violet-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-foreground flex items-center gap-2">
                    Your Data
                    {isConnected && (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    )}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {isConnected ? sourceConfig.label : 'No data connected'}
                  </p>
                </div>
              </div>
            </div>

            {datasetInfo ? (
              <div className="overflow-y-auto flex-1">
                {/* Stats Grid */}
                <div className="p-4 grid grid-cols-4 gap-2">
                  <div className="text-center p-2 rounded-xl bg-violet-500/10 border border-violet-500/20">
                    <Layers className="w-3.5 h-3.5 text-violet-400 mx-auto mb-0.5" />
                    <div className="text-base font-bold text-foreground">{datasetInfo.totalTables}</div>
                    <div className="text-[9px] text-muted-foreground uppercase">Tables</div>
                  </div>
                  <div className="text-center p-2 rounded-xl bg-blue-500/10 border border-blue-500/20">
                    <Hash className="w-3.5 h-3.5 text-blue-400 mx-auto mb-0.5" />
                    <div className="text-base font-bold text-foreground">{formatCount(datasetInfo.totalRecords)}</div>
                    <div className="text-[9px] text-muted-foreground uppercase">Records</div>
                  </div>
                  <div className="text-center p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
                    <BarChart3 className="w-3.5 h-3.5 text-cyan-400 mx-auto mb-0.5" />
                    <div className="text-base font-bold text-foreground">{totalColumns || '—'}</div>
                    <div className="text-[9px] text-muted-foreground uppercase">Columns</div>
                  </div>
                  <div className="text-center p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                    <Shield className="w-3.5 h-3.5 text-emerald-400 mx-auto mb-0.5" />
                    <div className="flex justify-center">
                      {hasProfiles ? (
                        <QualityCircle score={avgQuality} />
                      ) : (
                        <div className="text-base font-bold text-foreground">—</div>
                      )}
                    </div>
                    <div className="text-[9px] text-muted-foreground uppercase">Quality</div>
                  </div>
                </div>

                {/* Column Breakdown Donut */}
                {columnBreakdown.length > 0 && (
                  <div className="mx-4 mb-3 p-3 rounded-xl bg-muted/30 border border-border">
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">
                      Column Breakdown
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="w-[76px] h-[76px] flex-shrink-0">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={columnBreakdown}
                              dataKey="value"
                              cx="50%"
                              cy="50%"
                              innerRadius={22}
                              outerRadius={34}
                              paddingAngle={3}
                              strokeWidth={0}
                            >
                              {columnBreakdown.map((entry, i) => (
                                <Cell key={i} fill={entry.color} />
                              ))}
                            </Pie>
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="flex-1 grid grid-cols-2 gap-x-3 gap-y-1.5">
                        {columnBreakdown.map((item) => (
                          <div key={item.name} className="flex items-center gap-1.5">
                            <span
                              className="w-2 h-2 rounded-full flex-shrink-0"
                              style={{ backgroundColor: item.color }}
                            />
                            <span className="text-[11px] text-muted-foreground">
                              {item.value} {item.name}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Table Profile Cards */}
                {hasProfiles ? (
                  <div className="px-4 pb-3">
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">
                      Tables
                    </div>
                    <div className="space-y-1.5 max-h-[200px] overflow-y-auto pr-1">
                      {profiles.map((table) => {
                        const isExpanded = expandedTable === table.name;
                        const dateRange = formatDateRange(table.date_range);
                        const typeColor = TABLE_TYPE_COLORS[table.table_type] || TABLE_TYPE_COLORS.unknown;

                        return (
                          <div key={table.name} className="rounded-lg border border-border overflow-hidden">
                            <button
                              onClick={() => setExpandedTable(isExpanded ? null : table.name)}
                              className="w-full p-2.5 hover:bg-accent/50 transition-colors text-left"
                            >
                              <div className="flex items-center justify-between gap-2 mb-1">
                                <span className="text-xs font-semibold text-foreground truncate flex-1">
                                  {cleanTableName(table.name)}
                                </span>
                                <div className="flex items-center gap-1.5 flex-shrink-0">
                                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${typeColor}`}>
                                    {table.table_type}
                                  </span>
                                  <motion.div
                                    animate={{ rotate: isExpanded ? 90 : 0 }}
                                    transition={{ duration: 0.15 }}
                                  >
                                    <ChevronRight className="w-3 h-3 text-muted-foreground" />
                                  </motion.div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                                <span>{table.row_count.toLocaleString()} rows</span>
                                <span className="text-border">|</span>
                                <span>{table.column_count} cols</span>
                                {dateRange && (
                                  <>
                                    <span className="text-border">|</span>
                                    <span className="text-emerald-400 flex items-center gap-0.5">
                                      <Calendar className="w-2.5 h-2.5" />
                                      {dateRange}
                                    </span>
                                  </>
                                )}
                              </div>
                              {/* Column role dots */}
                              <div className="flex gap-1 mt-1.5">
                                {table.metrics.length > 0 && (
                                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: ROLE_COLORS.metrics }} title={`${table.metrics.length} metrics`} />
                                )}
                                {table.dimensions.length > 0 && (
                                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: ROLE_COLORS.dimensions }} title={`${table.dimensions.length} dimensions`} />
                                )}
                                {table.date_columns.length > 0 && (
                                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: ROLE_COLORS.dates }} title={`${table.date_columns.length} dates`} />
                                )}
                                {table.identifiers.length > 0 && (
                                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: ROLE_COLORS.identifiers }} title={`${table.identifiers.length} identifiers`} />
                                )}
                              </div>
                            </button>

                            {/* Expanded column details */}
                            <AnimatePresence>
                              {isExpanded && (
                                <motion.div
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  transition={{ duration: 0.2 }}
                                  className="overflow-hidden border-t border-border"
                                >
                                  <div className="p-2.5 bg-muted/30 space-y-2">
                                    {table.metrics.length > 0 && (
                                      <div>
                                        <div className="flex items-center gap-1.5 mb-1">
                                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ROLE_COLORS.metrics }} />
                                          <span className="text-[10px] font-semibold text-violet-400 uppercase">Metrics</span>
                                        </div>
                                        <div className="flex flex-wrap gap-1">
                                          {table.metrics.map(m => (
                                            <span key={m} className="px-1.5 py-0.5 text-[10px] rounded bg-violet-500/10 text-violet-300 border border-violet-500/20">
                                              {m.replace(/_/g, ' ')}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                    {table.dimensions.length > 0 && (
                                      <div>
                                        <div className="flex items-center gap-1.5 mb-1">
                                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ROLE_COLORS.dimensions }} />
                                          <span className="text-[10px] font-semibold text-blue-400 uppercase">Dimensions</span>
                                        </div>
                                        <div className="flex flex-wrap gap-1">
                                          {table.dimensions.map(d => (
                                            <span key={d} className="px-1.5 py-0.5 text-[10px] rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">
                                              {d.replace(/_/g, ' ')}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                    {table.date_columns.length > 0 && (
                                      <div>
                                        <div className="flex items-center gap-1.5 mb-1">
                                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ROLE_COLORS.dates }} />
                                          <span className="text-[10px] font-semibold text-emerald-400 uppercase">Date Columns</span>
                                        </div>
                                        <div className="flex flex-wrap gap-1">
                                          {table.date_columns.map(d => (
                                            <span key={d} className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                                              {d.replace(/_/g, ' ')}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                    {table.identifiers.length > 0 && (
                                      <div>
                                        <div className="flex items-center gap-1.5 mb-1">
                                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ROLE_COLORS.identifiers }} />
                                          <span className="text-[10px] font-semibold text-zinc-400 uppercase">Identifiers</span>
                                        </div>
                                        <div className="flex flex-wrap gap-1">
                                          {table.identifiers.map(id => (
                                            <span key={id} className="px-1.5 py-0.5 text-[10px] rounded bg-zinc-500/10 text-zinc-300 border border-zinc-500/20">
                                              {id.replace(/_/g, ' ')}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                    {table.granularity && table.granularity !== 'unknown' && (
                                      <div className="text-[10px] text-muted-foreground pt-1 border-t border-border">
                                        Granularity: <span className="text-foreground font-medium">{table.granularity}</span>
                                      </div>
                                    )}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  /* Fallback: show sheets list when no profiles available */
                  <div className="px-4 pb-3">
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">
                      Loaded Sheets
                    </div>
                    <div className="space-y-1.5 max-h-[160px] overflow-y-auto">
                      {datasetInfo.sheets.length > 0 ? (
                        datasetInfo.sheets.map((sheet, idx) => (
                          <div key={idx} className="flex items-center gap-2 p-2 rounded-lg border border-border">
                            <FileSpreadsheet className="w-3.5 h-3.5 text-violet-400 flex-shrink-0" />
                            <span className="text-xs text-foreground truncate">{sheet}</span>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-3 text-muted-foreground text-xs">
                          No sheets detected
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Smart Suggestions */}
                {datasetInfo.smartSuggestions && datasetInfo.smartSuggestions.length > 0 && (
                  <div className="px-4 pb-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Sparkles className="w-3 h-3 text-violet-400" />
                      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                        Try asking
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {datasetInfo.smartSuggestions.slice(0, 3).map((suggestion, i) => (
                        <button
                          key={i}
                          onClick={() => {
                            setIsOpen(false);
                            onSuggestionClick?.(suggestion);
                          }}
                          className="px-2.5 py-1 text-[10px] rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20 hover:bg-violet-500/20 hover:text-violet-200 transition-all text-left leading-tight"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 text-center">
                <Database className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">
                  No dataset information available
                </p>
              </div>
            )}

            {/* Footer */}
            <div className="px-4 py-3 border-t border-border bg-muted/30 flex-shrink-0">
              {onClick ? (
                <Button
                  onClick={() => {
                    setIsOpen(false);
                    onClick();
                  }}
                  variant="outline"
                  className="w-full h-9 text-xs font-medium border-violet-500/30 hover:bg-violet-500/10 hover:border-violet-500/50"
                >
                  <Database className="w-3.5 h-3.5 mr-2" />
                  Manage Data Sources
                </Button>
              ) : (
                <p className="text-[10px] text-muted-foreground text-center">
                  {isConnected
                    ? 'Data is loaded and ready for queries'
                    : 'Connect a dataset to start analyzing'
                  }
                </p>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </PopoverContent>
    </Popover>
  );
}
