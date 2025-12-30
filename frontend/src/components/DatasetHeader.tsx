/**
 * Dataset Header - Persistent header showing dataset info
 */

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { DatasetMetadata } from "@/lib/dataset-types";

interface DatasetHeaderProps {
  metadata: DatasetMetadata;
  locked: boolean;
  onAnalyze: () => void;
  onNewChat: () => void;
}

export function DatasetHeader({ metadata, locked, onAnalyze, onNewChat }: DatasetHeaderProps) {
  const lastSyncDate = new Date(metadata.last_sync);
  const totalTables = metadata.sheets.reduce((sum, sheet) => sum + sheet.tables.length, 0);

  return (
    <div className="flex items-center justify-between p-4 bg-black/40 backdrop-blur-xl border-b border-white/10">
      <div className="flex items-center gap-4">
        <div className="flex flex-col">
          <div className="text-sm font-medium text-white">{metadata.spreadsheet_name}</div>
          <div className="text-xs text-white/60">
            Last synced: {lastSyncDate.toLocaleString()} • {totalTables} table{totalTables !== 1 ? 's' : ''}
          </div>
        </div>
        {locked && <Badge variant="outline" className="text-xs text-emerald-400 border-emerald-400/30">🔒 Locked</Badge>}
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={onAnalyze}
          className="text-teal-400 border-teal-400/30 hover:bg-teal-400/10">
          📊 Analyze Sheet
        </Button>
        <Button variant="outline" size="sm" onClick={onNewChat}
          className="text-white/60 border-white/10 hover:bg-white/5">
          ✨ New Chat
        </Button>
      </div>
    </div>
  );
}
