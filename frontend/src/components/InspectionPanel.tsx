/**
 * Inspection Panel - Metadata-only dataset structure display
 * NO row data, NO cell values, NO data preview
 */

import { motion } from "framer-motion";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { DatasetMetadata } from "@/lib/dataset-types";

interface InspectionPanelProps {
  metadata: DatasetMetadata;
  onClose: () => void;
}

export function InspectionPanel({ metadata, onClose }: InspectionPanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="absolute right-0 top-0 bottom-0 w-96 bg-black/90 backdrop-blur-xl border-l border-white/10 overflow-y-auto z-50"
    >
      <div className="sticky top-0 z-10 flex items-center justify-between p-4 bg-black/40 backdrop-blur-xl border-b border-white/10">
        <div>
          <h2 className="text-lg font-semibold text-white">Dataset Structure</h2>
          <p className="text-xs text-white/60">Metadata inspection (no computation)</p>
        </div>
        <button onClick={onClose} className="text-white/60 hover:text-white transition-colors">✕</button>
      </div>

      <div className="p-4 space-y-4">
        <Card className="p-4 bg-white/5 border-white/10">
          <div className="text-sm font-medium text-white mb-2">Spreadsheet</div>
          <div className="text-xs text-white/80">{metadata.spreadsheet_name}</div>
          <div className="text-xs text-white/60 mt-1">
            Last synced: {new Date(metadata.last_sync).toLocaleString()}
          </div>
        </Card>

        <Accordion type="multiple" className="space-y-2">
          {metadata.sheets.map((sheet, sheetIdx) => (
            <AccordionItem key={sheetIdx} value={`sheet-${sheetIdx}`}
              className="border border-white/10 rounded-lg overflow-hidden bg-white/5">
              <AccordionTrigger className="px-4 py-3 hover:bg-white/5">
                <div className="flex items-center justify-between w-full">
                  <span className="text-sm font-medium text-white">{sheet.sheet_name}</span>
                  <Badge variant="outline" className="ml-2 text-xs text-teal-400 border-teal-400/30">
                    {sheet.tables.length} table{sheet.tables.length !== 1 ? 's' : ''}
                  </Badge>
                </div>
              </AccordionTrigger>

              <AccordionContent className="px-4 pb-4 space-y-3">
                {sheet.tables.map((table, tableIdx) => (
                  <Card key={tableIdx} className="p-3 bg-black/40 border-white/10">
                    <div className="flex items-start justify-between mb-2">
                      <div className="text-sm font-medium text-white">{table.table_name}</div>
                      <div className="flex gap-2">
                        <Badge variant="outline" className="text-xs text-white/60 border-white/20">
                          {table.row_count} rows
                        </Badge>
                        <Badge variant="outline" className="text-xs text-white/60 border-white/20">
                          {table.column_count} cols
                        </Badge>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-xs text-white/40">Columns:</div>
                      <div className="flex flex-wrap gap-1">
                        {table.columns.map((col, colIdx) => (
                          <Badge key={colIdx} variant="secondary" className="text-xs bg-white/10 text-white/80">
                            {col}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="mt-2 text-xs text-white/30 font-mono">{table.source_id}</div>
                  </Card>
                ))}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>

        <div className="text-xs text-white/40 text-center py-4">
          This is a structural view only. No row data is displayed.
        </div>
      </div>
    </motion.div>
  );
}
