import React, { useRef, useEffect } from 'react';
import { Terminal, CheckCircle2, AlertCircle, Cpu, Radio, Trash2 } from 'lucide-react';

export default function ExecutionTerminal({ logs = [], onClear }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="flex flex-col h-full bg-arya-card/90 rounded-2xl border border-slate-800 shadow-2xl backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-amber-500" />
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            Real-Time Agent Execution Terminal
          </span>
          <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            STREAM ACTIVE
          </span>
        </div>

        <button
          onClick={onClear}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Clear Terminal Logs"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Terminal Output Area */}
      <div
        ref={scrollRef}
        className="flex-1 p-4 font-['JetBrains_Mono',monospace] text-xs leading-relaxed space-y-2.5 overflow-y-auto"
      >
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-center py-12">
            <Cpu className="w-8 h-8 mb-2 opacity-40 text-amber-500 animate-pulse" />
            <p>Agent reasoning & tool execution telemetry will stream live here.</p>
            <p className="text-[11px] text-slate-600 mt-1">
              Try saying: "Lock my laptop", "Turn on living room lights", or "What time is it?"
            </p>
          </div>
        ) : (
          logs.map((log, idx) => {
            const time = log.timestamp || new Date().toLocaleTimeString();

            if (log.stage === 'step_start') {
              return (
                <div key={idx} className="flex items-start gap-2 text-amber-500 bg-cyan-950/20 p-2 rounded-lg border border-cyan-900/40">
                  <span className="text-slate-500 text-[10px]">{time}</span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-cyan-300 text-[10px] font-bold">
                    STEP {log.step}/{log.total}
                  </span>
                  <div>
                    <span className="font-semibold text-white">Calling Tool: </span>
                    <code>{log.tool}</code>
                    {log.params && (
                      <span className="text-slate-400 text-[11px] ml-2">
                        {JSON.stringify(log.params)}
                      </span>
                    )}
                  </div>
                </div>
              );
            }

            if (log.stage === 'step_success') {
              return (
                <div key={idx} className="flex items-start gap-2 text-emerald-400 pl-4 border-l-2 border-emerald-500/40">
                  <span className="text-slate-500 text-[10px]">{time}</span>
                  <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 text-emerald-400 shrink-0" />
                  <span className="text-slate-200">{log.message}</span>
                </div>
              );
            }

            if (log.stage === 'step_failed') {
              return (
                <div key={idx} className="flex items-start gap-2 text-rose-400 pl-4 border-l-2 border-rose-500/40">
                  <span className="text-slate-500 text-[10px]">{time}</span>
                  <AlertCircle className="w-3.5 h-3.5 mt-0.5 text-rose-400 shrink-0" />
                  <span>{log.error}</span>
                </div>
              );
            }

            if (log.stage === 'device_command') {
              return (
                <div key={idx} className="flex items-start gap-2 text-purple-400 bg-purple-950/20 p-2 rounded-lg border border-purple-900/40">
                  <span className="text-slate-500 text-[10px]">{time}</span>
                  <Radio className="w-3.5 h-3.5 mt-0.5 text-purple-400 animate-pulse shrink-0" />
                  <div>
                    <span className="font-semibold text-purple-200">Device Relay [{log.node_id}]: </span>
                    <span className="text-white font-mono">{log.action}</span>
                    <span className="text-[10px] ml-2 uppercase px-1.5 py-0.5 rounded bg-purple-900/60 text-purple-300">
                      {log.status}
                    </span>
                  </div>
                </div>
              );
            }

            if (log.stage === 'execution_complete') {
              return (
                <div key={idx} className="flex items-center gap-2 text-[11px] font-mono py-1.5 px-3 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300">
                  <span className="text-slate-500 text-[10px]">{time}</span>
                  <span className="font-semibold text-slate-200">Execution Plan Finished:</span>
                  <span className="text-emerald-400 font-bold">{log.ok || 0} passed</span>
                  {(log.failed || 0) > 0 && (
                    <span className="text-rose-400 font-bold">{log.failed} failed</span>
                  )}
                </div>
              );
            }

            // Generic log
            return (
              <div key={idx} className="flex items-start gap-2 text-slate-300">
                <span className="text-slate-500 text-[10px]">{time}</span>
                <span className="text-amber-500 font-bold">›</span>
                <span>{log.text || JSON.stringify(log)}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
