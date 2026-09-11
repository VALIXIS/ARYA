import React, { useState, useCallback } from 'react';
import {
  Mic,
  MicOff,
  Square,
  Send,
  Cpu,
  Terminal as TerminalIcon,
  Network,
  Wifi,
  Sparkles,
  ShieldCheck,
  Volume2,
  VolumeX,
} from 'lucide-react';

import AryaCore from './components/AryaCore';
import ExecutionTerminal from './components/ExecutionTerminal';
import MemoryGraph from './components/MemoryGraph';
import DeviceManager from './components/DeviceManager';
import { useVoice } from './hooks/useVoice';
import { useWebSocket } from './hooks/useWebSocket';

export default function App() {
  const [activeTab, setActiveTab] = useState('cockpit'); // cockpit, terminal, graph, devices
  const [coreState, setCoreState] = useState('idle'); // idle, listening, thinking, executing, speaking
  const [terminalLogs, setTerminalLogs] = useState([]);
  const [inputText, setInputText] = useState('');
  const [responseLength, setResponseLength] = useState('Brief');
  const [autoVoiceReply, setAutoVoiceReply] = useState(true);

  const addTerminalLog = useCallback((log) => {
    if (!log) return;
    setTerminalLogs((prev) => [
      ...prev,
      {
        ...log,
        text: typeof log.text === 'string' ? log.text : (log.message || log.error || ''),
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
  }, []);

  // WebSocket Connection
  const { isConnected, connectedDevices, sendMessage, sendDeviceCommand } = useWebSocket({
    onStateChange: (state) => setCoreState(state),
    onAgentExecution: (event) => addTerminalLog(event),
    onChatReply: (reply) => {
      addTerminalLog({ text: `ARYA: ${reply}` });
      if (autoVoiceReply) {
        speak(reply);
      }
    },
  });

  // Voice Hook
  const {
    isListening,
    isSpeaking,
    isWakeWordActive,
    transcript,
    audioLevel,
    startListening,
    stopListening,
    toggleWakeWord,
    speak,
    stopSpeaking,
  } = useVoice({
    onTranscriptReady: (text) => {
      handleUserSubmit(text);
    },
    onStateChange: (state) => setCoreState(state),
  });

  // Handle Command Submission
  const handleUserSubmit = async (query) => {
    const text = (query || inputText).trim();
    if (!text) return;

    addTerminalLog({ text: `User: "${text}"` });
    setInputText('');

    // Check for interrupt command
    const lower = text.toLowerCase();
    if (['stop', 'stop talking', 'be quiet', 'enough', 'halt'].includes(lower)) {
      stopSpeaking();
      setCoreState('idle');
      addTerminalLog({ text: `[VOICE] Playback halted by interrupt command.` });
      return;
    }

    setCoreState('thinking');

    // Safety watchdog: reset to idle if thinking longer than 16 seconds
    const watchdogTimer = setTimeout(() => {
      setCoreState((curr) => (curr === 'thinking' ? 'idle' : curr));
    }, 16000);

    // Try WebSocket channel first
    const sent = sendMessage(text, responseLength);
    if (!sent) {
      addTerminalLog({ text: `[RELAY] WebSocket reconnecting — falling back to HTTP channel...` });
      try {
        const res = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, response_length: responseLength }),
        });
        clearTimeout(watchdogTimer);
        if (res.ok) {
          const data = await res.json();
          addTerminalLog({ text: `ARYA: ${data.reply}` });
          if (autoVoiceReply) {
            setCoreState('speaking');
            speak(data.reply);
          } else {
            setCoreState('idle');
          }
        } else {
          addTerminalLog({ text: `[ERROR] Backend responded with HTTP ${res.status}.` });
          setCoreState('idle');
        }
      } catch (err) {
        clearTimeout(watchdogTimer);
        addTerminalLog({ text: `[ERROR] Could not connect to ARYA: ${err.message}. Is backend running on port 8000?` });
        setCoreState('idle');
      }
    }
  };


  const quickPrompts = [
    'Lock my laptop',
    'Turn off the living room lights',
    'Set AC to 21 degrees',
    'What time is it?',
    'What do you know about me?',
    'Mute sound',
  ];

  return (
    <div className="min-h-screen flex flex-col hud-scanner bg-arya-dark text-slate-100 bg-grid-pattern selection:bg-amber-500 selection:text-slate-950">
      {/* Top HUD Header */}
      <header className="h-16 px-4 md:px-8 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl flex items-center justify-between z-30 sticky top-0">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-600 p-0.5 shadow-lg shadow-amber-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <span className="font-extrabold text-lg text-transparent bg-clip-text bg-gradient-to-r from-amber-500 to-orange-500">
                A
              </span>
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-slate-950 animate-pulse" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-base tracking-wider text-white">PROJECT ARYA</h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 border border-amber-800/50 text-amber-300 font-semibold">
                v3.0 JARVIS
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono tracking-wide hidden sm:block">
              Autonomous Personal AI Assistant
            </p>
          </div>
        </div>

        {/* HUD Controls */}
        <div className="flex items-center gap-3">
          {/* Response Length Selector */}
          <div className="hidden md:flex items-center gap-1 bg-slate-900/90 border border-slate-800 rounded-lg p-1 text-[11px] font-mono">
            {['Brief', 'Normal', 'Detailed'].map((len) => (
              <button
                key={len}
                onClick={() => setResponseLength(len)}
                className={`px-2 py-0.5 rounded transition-all ${
                  responseLength === len
                    ? 'bg-amber-500 text-slate-950 font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {len}
              </button>
            ))}
          </div>

          {/* Hands-Free "Hey ARYA" Wake-Word Button */}
          <button
            onClick={toggleWakeWord}
            className={`px-3 py-1 rounded-lg border text-xs font-mono flex items-center gap-2 transition-all ${
              isWakeWordActive
                ? 'bg-emerald-950/60 border-emerald-500/80 text-emerald-300 shadow-md shadow-emerald-500/20 animate-pulse'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title='Toggle Hands-Free "Hey ARYA" Voice Trigger'
          >
            <Mic className={`w-3.5 h-3.5 ${isWakeWordActive ? 'text-emerald-400 animate-spin' : ''}`} />
            <span className="hidden sm:inline">
              {isWakeWordActive ? '"Hey ARYA" Active' : 'Enable "Hey ARYA"'}
            </span>
          </button>

          {/* Voice Auto-Reply Toggle */}
          <button
            onClick={() => setAutoVoiceReply(!autoVoiceReply)}
            className={`p-2 rounded-lg border text-xs font-mono flex items-center gap-1.5 transition-colors ${
              autoVoiceReply
                ? 'bg-amber-950/40 border-amber-800/60 text-amber-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
            title="Auto Read Replies Aloud"
          >
            {autoVoiceReply ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>

          {/* WebSocket Status Indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
              }`}
            />
            <span className="hidden sm:inline text-slate-300">
              {isConnected ? 'RELAY ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Tab Navigation */}
      <nav className="flex items-center justify-center gap-1 px-4 py-2 bg-slate-950/60 border-b border-slate-800/50 text-xs font-mono">
        {[
          { id: 'cockpit', label: '3D COCKPIT', icon: Sparkles },
          { id: 'terminal', label: 'EXECUTION TERMINAL', icon: TerminalIcon },
          { id: 'graph', label: 'MEMORY GRAPH', icon: Network },
          { id: 'devices', label: 'DEVICE NODES', icon: Wifi },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                isActive
                  ? 'bg-slate-800 text-amber-500 font-bold border border-slate-700 shadow-lg'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Central Interactive Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 flex flex-col justify-between overflow-hidden">
        {activeTab === 'cockpit' && (
          <div className="flex-1 flex flex-col items-center justify-center relative my-auto space-y-4">
            {/* 3D ARYA Hologram Core */}
            <AryaCore state={coreState} audioLevel={audioLevel} />

            {/* Gemini / Siri Style Live Real-Time Voice Overlay */}
            {isListening && (
              <div className="w-full max-w-2xl px-6 py-4 rounded-3xl bg-slate-950/90 border border-amber-500/40 shadow-2xl shadow-amber-500/20 backdrop-blur-2xl flex flex-col items-center gap-3 animate-fadeIn">
                {/* Siri / Gemini Multi-Color Dynamic Waveform Bar */}
                <div className="flex items-center gap-1.5 h-6">
                  {[0.3, 0.7, 0.9, 0.5, 1.0, 0.6, 0.8, 0.4].map((multiplier, i) => (
                    <span
                      key={i}
                      className={`w-1 rounded-full transition-all duration-75 ${
                        i % 4 === 0
                          ? 'bg-amber-400 shadow-md shadow-amber-400/50'
                          : i % 4 === 1
                          ? 'bg-indigo-400 shadow-md shadow-indigo-400/50'
                          : i % 4 === 2
                          ? 'bg-purple-400 shadow-md shadow-purple-400/50'
                          : 'bg-emerald-400 shadow-md shadow-emerald-400/50'
                      }`}
                      style={{ height: `${Math.max(6, audioLevel * 36 * multiplier)}px` }}
                    />
                  ))}
                </div>

                {/* Real-time Streaming Live Text */}
                <div className="text-center font-sans">
                  {transcript ? (
                    <p className="text-lg md:text-xl font-medium tracking-wide text-white drop-shadow-md">
                      "{transcript}"<span className="text-amber-500 font-bold animate-pulse ml-0.5">|</span>
                    </p>
                  ) : (
                    <p className="text-sm font-mono text-slate-400 tracking-wider flex items-center gap-2">
                      <Mic className="w-4 h-4 text-amber-500 animate-pulse" />
                      Listening... Speak your command now <span className="text-amber-500 font-bold animate-pulse">|</span>
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Latest ARYA Reply Glassmorphic Card */}
            {!isListening && terminalLogs.length > 0 && (
              <div className="w-full max-w-2xl p-4 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-2xl backdrop-blur-xl space-y-2 transition-all">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                    <span className="text-xs font-mono font-bold text-amber-500 uppercase tracking-wider">
                      {coreState === 'thinking' ? 'ARYA THINKING...' : coreState === 'speaking' ? 'ARYA SPEAKING' : 'ARYA RESPONSE'}
                    </span>
                  </div>
                  {isSpeaking && (
                    <button
                      onClick={stopSpeaking}
                      className="text-xs font-mono px-2 py-0.5 rounded bg-rose-950/80 border border-rose-800 text-rose-300 hover:bg-rose-900 transition-colors flex items-center gap-1"
                    >
                      <Square className="w-3 h-3 fill-current" /> Stop Voice
                    </button>
                  )}
                </div>

                <div className="text-sm text-slate-200 leading-relaxed font-sans max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                  {(() => {
                    const lastLog = [...terminalLogs]
                      .reverse()
                      .find((l) => l && typeof l.text === 'string' && l.text.startsWith('ARYA:'));
                    if (!lastLog) return <span className="text-slate-500 italic">Ready for commands...</span>;
                    const replyText = (lastLog.text || '').replace(/^ARYA:\s*/, '');
                    return replyText;
                  })()}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'terminal' && (
          <div className="flex-1 h-[520px]">
            <ExecutionTerminal logs={terminalLogs} onClear={() => setTerminalLogs([])} />
          </div>
        )}

        {activeTab === 'graph' && (
          <div className="flex-1 h-[520px]">
            <MemoryGraph onSelectTab={setActiveTab} onSendMessage={handleUserSubmit} />
          </div>
        )}

        {activeTab === 'devices' && (
          <div className="flex-1 h-[520px]">
            <DeviceManager onDispatchCommand={sendDeviceCommand} />
          </div>
        )}

        {/* Action Controls & Input Deck */}
        <div className="w-full max-w-3xl mx-auto pt-4 space-y-3">
          {/* Quick Action Chips */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
            {quickPrompts.map((prompt) => (
              <button
                key={prompt}
                onClick={() => handleUserSubmit(prompt)}
                className="shrink-0 text-[11px] font-mono px-3 py-1 rounded-full bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 transition-colors"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Primary Voice & Text Bar */}
          <div className="flex items-center gap-2 p-2 rounded-2xl bg-slate-950/90 border border-slate-800 shadow-2xl backdrop-blur-2xl">
            {/* Push-to-Talk Mic Button */}
            <button
              onClick={isListening ? stopListening : startListening}
              className={`p-3.5 rounded-xl transition-all flex items-center justify-center shrink-0 ${
                isListening
                  ? 'bg-rose-500 text-white animate-pulse shadow-lg shadow-rose-500/40'
                  : 'bg-amber-500 text-slate-950 font-bold hover:bg-amber-300 shadow-lg shadow-amber-500/25'
              }`}
              title={isListening ? 'Release / Stop Listening' : 'Press to Speak'}
            >
              {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>

            {/* Stop / Interrupt Button (Visible during speech or execution) */}
            {isSpeaking && (
              <button
                onClick={stopSpeaking}
                className="p-3.5 rounded-xl bg-rose-950 border border-rose-800 text-rose-300 hover:bg-rose-900 transition-colors flex items-center justify-center shrink-0"
                title="Interrupt Speech"
              >
                <Square className="w-5 h-5 fill-current" />
              </button>
            )}

            {/* Text Input */}
            <input
              type="text"
              placeholder="Ask ARYA anything or control your devices..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleUserSubmit()}
              className="flex-1 bg-transparent px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none font-sans"
            />

            {/* Send Button */}
            <button
              onClick={() => handleUserSubmit()}
              disabled={!inputText.trim()}
              className="p-3 rounded-xl text-slate-400 hover:text-amber-500 disabled:opacity-30 disabled:hover:text-slate-400 transition-colors shrink-0"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
