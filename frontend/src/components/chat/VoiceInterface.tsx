'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Mic, Square, Sparkles, Table, Settings, Loader2 } from 'lucide-react';
import { VoiceVisualizer } from '../VoiceVisualizer';
import { ChatTab } from '@/lib/types';

interface VoiceInterfaceProps {
  username: string;
  isRecording: boolean;
  isProcessing: boolean;
  isSpeaking: boolean;
  activeChat: ChatTab | undefined;
  onVoiceToggle: () => void;
}

export function VoiceInterface({
  username,
  isRecording,
  isProcessing,
  isSpeaking,
  activeChat,
  onVoiceToggle
}: VoiceInterfaceProps) {
  const [expandedSection, setExpandedSection] = useState<'plan' | 'data' | 'schema' | null>(null);

  return (
    <motion.div
      key="voice"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="relative z-10 w-full max-w-2xl flex flex-col items-center justify-between h-full py-8 gap-4 px-6"
    >
      <div className="flex-1 flex flex-col items-center justify-center gap-8 w-full">
        {/* Brand Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-center space-y-2"
        >
          <h1 className="text-4xl font-display font-bold tracking-tight">
            {isRecording ? (
              <span className="text-violet-400">Listening<span className="animate-pulse">...</span></span>
            ) : isSpeaking ? (
              <span className="text-purple-400">Speaking<span className="animate-pulse">...</span></span>
            ) : (
              <>Hello <span className="gradient-text">{username}</span></>
            )}
          </h1>
          <p className="text-zinc-500 text-sm font-medium max-w-md mx-auto">
            {isRecording
              ? "Your voice is being captured securely"
              : isProcessing
                ? "Processing your request..."
                : isSpeaking
                  ? "Generating intelligent response"
                  : "Tap the button below to start a voice conversation"}
          </p>
        </motion.div>

        {/* Voice Visualizer */}
        <VoiceVisualizer isRecording={isRecording} isSpeaking={isSpeaking} />

        {/* Voice Button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onVoiceToggle}
          className={`relative w-16 h-16 rounded-full transition-all duration-500 flex items-center justify-center ${isRecording
            ? 'bg-violet-500 shadow-[0_0_60px_rgba(139,92,246,0.5)]'
            : 'bg-secondary border border-border hover:border-primary/50 hover:shadow-[0_0_40px_rgba(var(--primary),0.2)]'
            }`}
        >
          <AnimatePresence mode="wait">
            {isRecording ? (
              <motion.div
                key="stop"
                initial={{ scale: 0, rotate: -90 }}
                animate={{ scale: 1, rotate: 0 }}
                exit={{ scale: 0, rotate: 90 }}
              >
                <Square className="w-6 h-6 text-white fill-current" />
              </motion.div>
            ) : isProcessing ? (
              <motion.div
                key="loading"
                initial={{ scale: 0, rotate: 90 }}
                animate={{ scale: 1, rotate: 0 }}
                exit={{ scale: 0, rotate: -90 }}
              >
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
              </motion.div>
            ) : (
              <motion.div
                key="mic"
                initial={{ scale: 0, rotate: 90 }}
                animate={{ scale: 1, rotate: 0 }}
                exit={{ scale: 0, rotate: -90 }}
              >
                <Mic className="w-6 h-6 text-muted-foreground" />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.button>
      </div>

      {/* Info Toggles */}
      <div className="w-full flex flex-col items-center gap-4">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            onClick={() => setExpandedSection(expandedSection === 'plan' ? null : 'plan')}
            className={cn("h-9 px-4 rounded-xl glass border transition-all gap-2",
              expandedSection === 'plan' ? "bg-primary/10 border-primary/50 text-primary" : "border-border hover:border-primary/30 hover:bg-accent"
            )}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">Query Plan</span>
          </Button>
          <Button
            variant="ghost"
            onClick={() => setExpandedSection(expandedSection === 'data' ? null : 'data')}
            className={cn("h-9 px-4 rounded-xl glass border transition-all gap-2",
              expandedSection === 'data' ? "bg-primary/10 border-primary/50 text-primary" : "border-border hover:border-primary/30 hover:bg-accent"
            )}
          >
            <Table className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">Data</span>
          </Button>
          <Button
            variant="ghost"
            onClick={() => setExpandedSection(expandedSection === 'schema' ? null : 'schema')}
            className={cn("h-9 px-4 rounded-xl glass border transition-all gap-2",
              expandedSection === 'schema' ? "bg-primary/10 border-primary/50 text-primary" : "border-border hover:border-primary/30 hover:bg-accent"
            )}
          >
            <Settings className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">Schema Context</span>
          </Button>
        </div>

        {/* Expanded Content Area */}
        <AnimatePresence>
          {expandedSection && (
            <motion.div
              initial={{ opacity: 0, height: 0, y: 20 }}
              animate={{ opacity: 1, height: 'auto', y: 0 }}
              exit={{ opacity: 0, height: 0, y: 20 }}
              className="w-full bg-zinc-950 rounded-xl border border-border overflow-hidden"
            >
              <div className="p-4 max-h-[250px] overflow-y-auto custom-scrollbar">
                {expandedSection === 'plan' && (
                  <div className="font-mono text-xs">
                    <div className="flex items-center gap-2 mb-2 text-primary font-bold uppercase tracking-wider">
                      <Sparkles className="w-3 h-3" /> Query Plan
                    </div>
                    <pre className="text-zinc-400 leading-relaxed whitespace-pre-wrap">
                      {(() => {
                        const messagesWithPlan = activeChat?.messages.filter(m => m.role === 'assistant' && m.metadata?.plan);
                        const latestPlan = messagesWithPlan && messagesWithPlan.length > 0 ? messagesWithPlan[messagesWithPlan.length - 1].metadata?.plan : null;
                        return latestPlan ? JSON.stringify(latestPlan, null, 2) : "No query plan available for the latest response.";
                      })()}
                    </pre>
                  </div>
                )}

                {expandedSection === 'data' && (
                  <div className="text-xs">
                    <div className="flex items-center gap-2 mb-3 text-primary font-bold uppercase tracking-wider">
                      <Table className="w-3 h-3" /> Data Preview
                    </div>
                    {(() => {
                      const messagesWithData = activeChat?.messages.filter(m => m.role === 'assistant' && m.metadata?.data && m.metadata.data.length > 0);
                      const latestData = messagesWithData && messagesWithData.length > 0 ? messagesWithData[messagesWithData.length - 1].metadata?.data : null;

                      if (!latestData || latestData.length === 0) {
                        return <div className="text-zinc-400">No data available. Ask a question to see results.</div>;
                      }

                      const columns = Object.keys(latestData[0]);
                      return (
                        <div className="overflow-x-auto">
                          <table className="w-full border-collapse">
                            <thead>
                              <tr className="border-b border-zinc-800">
                                {columns.map((col) => (
                                  <th key={col} className="text-left p-2 text-primary font-medium">{col}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {latestData.slice(0, 10).map((row: any, idx: number) => (
                                <tr key={idx} className="border-b border-zinc-800/50 hover:bg-zinc-900/50">
                                  {columns.map((col) => (
                                    <td key={col} className="p-2 text-zinc-400">{String(row[col] ?? '')}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {latestData.length > 10 && (
                            <div className="text-zinc-500 mt-2 text-center">Showing 10 of {latestData.length} rows</div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}

                {expandedSection === 'schema' && (
                  <div className="text-xs font-mono text-zinc-400 space-y-3">
                    <div className="flex items-center gap-2 mb-2 text-primary font-bold uppercase tracking-wider font-sans">
                      <Settings className="w-3 h-3" /> Schema Context
                    </div>
                    {(() => {
                      // First check for schema context from latest message
                      const messagesWithSchema = activeChat?.messages.filter(m => m.role === 'assistant' && m.metadata?.schema_context && m.metadata.schema_context.length > 0);
                      const latestSchema = messagesWithSchema && messagesWithSchema.length > 0 ? messagesWithSchema[messagesWithSchema.length - 1].metadata?.schema_context : null;

                      // Also show dataset tables if available
                      const detectedTables = activeChat?.datasetStats?.detectedTables;

                      if (!latestSchema && !detectedTables) {
                        return <div className="text-zinc-400">No schema context available. Connect a dataset to see table information.</div>;
                      }

                      return (
                        <div className="space-y-4">
                          {/* Show detected tables from dataset */}
                          {detectedTables && detectedTables.length > 0 && (
                            <div>
                              <div className="text-primary font-semibold mb-2 font-sans">Connected Tables ({detectedTables.length})</div>
                              {detectedTables.map((table, idx) => (
                                <div key={idx} className="mb-3 p-2 bg-zinc-900/50 rounded-lg">
                                  <div className="text-violet-400 font-semibold">{table.title || table.table_id}</div>
                                  <div className="text-zinc-500 text-[10px]">Sheet: {table.sheet_name} | Rows: {table.total_rows || 'N/A'}</div>
                                  {table.columns && (
                                    <div className="mt-1 text-zinc-400">
                                      <span className="text-zinc-500">Columns: </span>
                                      {table.columns.slice(0, 5).join(', ')}
                                      {table.columns.length > 5 && ` +${table.columns.length - 5} more`}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Show schema context from last query */}
                          {latestSchema && latestSchema.length > 0 && (
                            <div>
                              <div className="text-primary font-semibold mb-2 font-sans">Retrieved Context</div>
                              {latestSchema.map((ctx, idx) => (
                                <div key={idx} className="mb-2 p-2 bg-zinc-900/50 rounded-lg whitespace-pre-wrap">
                                  {ctx.text}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
