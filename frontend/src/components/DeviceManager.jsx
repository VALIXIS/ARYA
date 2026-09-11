import React, { useState, useEffect } from 'react';
import {
  Laptop,
  Smartphone,
  Lightbulb,
  Tv,
  Wind,
  Power,
  Volume2,
  Lock,
  Battery,
  Wifi,
  Sparkles,
  RefreshCw,
  Terminal,
} from 'lucide-react';

export default function DeviceManager({ onDispatchCommand }) {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/devices');
      if (res.ok) {
        const data = await res.json();
        setDevices(data);
      }
    } catch (e) {
      console.error('Failed to fetch devices:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const sendCommand = async (nodeId, action, params = {}) => {
    // 1. Optimistic update
    setDevices((prev) =>
      prev.map((d) => {
        if (d.node_id === nodeId) {
          const newState = { ...d.state_data };
          if (action === 'turn_on' || action === 'power_on') newState.power = 'on';
          if (action === 'turn_off' || action === 'power_off') newState.power = 'off';
          if (action === 'set_volume' || action === 'volume') newState.volume = params.level || params.percent;
          if (action === 'set_climate') newState.temperature = params.temperature;
          return { ...d, state_data: newState };
        }
        return d;
      })
    );

    // 2. Dispatch command via HTTP API so it always executes natively
    try {
      const res = await fetch(`/api/devices/${nodeId}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, params }),
      });
      if (res.ok) {
        const data = await res.json();
        console.log(`[DEVICE EXEC] ${nodeId} -> ${action}:`, data);
        setTimeout(fetchDevices, 1200);
      }
    } catch (e) {
      console.error('Command dispatch error:', e);
    }

    if (onDispatchCommand) {
      onDispatchCommand(nodeId, action, params);
    }
  };


  const getDeviceIcon = (type) => {
    switch (type) {
      case 'laptop':
      case 'desktop':
        return <Laptop className="w-5 h-5 text-amber-500" />;
      case 'mobile':
        return <Smartphone className="w-5 h-5 text-purple-400" />;
      case 'tv':
      case 'smart_tv':
        return <Tv className="w-5 h-5 text-blue-400" />;
      case 'light':
        return <Lightbulb className="w-5 h-5 text-amber-400" />;
      case 'ac':
        return <Wind className="w-5 h-5 text-cyan-300" />;
      default:
        return <Wifi className="w-5 h-5 text-slate-400" />;
    }
  };

  const laptopDevice = devices.find((d) => d.device_type === 'laptop' || d.device_type === 'desktop');
  const realHostIp = laptopDevice?.ip_address && !laptopDevice.ip_address.startsWith('127.')
    ? laptopDevice.ip_address
    : (typeof window !== 'undefined' && window.location.hostname !== 'localhost' ? window.location.hostname : '192.168.31.30');

  return (
    <div className="flex flex-col h-full bg-arya-card/90 rounded-2xl border border-slate-800 shadow-2xl backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Wifi className="w-5 h-5 text-amber-500" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Universal Device Node Manager
          </h2>
          <span className="text-xs text-slate-400 font-mono">
            ({devices.length} verified hardware nodes)
          </span>
        </div>

        <button
          onClick={fetchDevices}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-mono transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Status
        </button>
      </div>

      {/* Mobile Connect Banner with Real LAN & Tailscale IPs */}
      <div className="mx-4 mt-4 p-3.5 rounded-xl bg-purple-950/30 border border-purple-800/40 flex flex-col md:flex-row items-center justify-between gap-3 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-purple-900/50 text-purple-300 border border-purple-700/50">
            <Smartphone className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-semibold text-white flex items-center gap-2">
              <span>Mobile Access (Anywhere via Tailscale & LAN)</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-mono font-bold">Tailscale Active</span>
            </div>
            <p className="text-[11px] text-slate-300 mt-0.5">
              Everywhere: <span className="text-emerald-400 font-mono font-bold select-all">http://100.96.60.52:5173</span> | Home Wi-Fi: <span className="text-amber-500 font-mono font-bold select-all">http://192.168.31.30:5173</span>
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <input
            type="text"
            id="adb-ip-input"
            defaultValue="100.67.134.74:41501"
            placeholder="100.67.134.74:PORT (Tailscale / Wi-Fi)"
            className="px-2.5 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-white font-mono placeholder:text-slate-500 focus:outline-none focus:border-purple-500 w-full md:w-48"
          />
          <button
            onClick={async () => {
              const val = document.getElementById('adb-ip-input')?.value;
              try {
                const [ip, port] = val && val.includes(':') ? val.split(':') : [val || '100.67.134.74', '0'];
                const res = await fetch('/api/android/connect', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ ip, port: parseInt(port) || 0 }),
                });
                const data = await res.json();
                alert(data.message || (data.success ? 'Connected!' : 'Connection attempted.'));
                fetchDevices();
              } catch (e) {
                alert('Connection error: ' + e);
              }
            }}
            className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-mono font-medium transition-colors shrink-0 shadow-md shadow-purple-600/30"
          >
            Connect ADB
          </button>
        </div>
      </div>

      {/* Grid of Devices */}
      <div className="flex-1 p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 overflow-y-auto">

        {devices.map((device) => {
          const state = device.state_data || {};
          const isOnline = device.status === 'online';
          const isStandby = device.status === 'standby';

          return (
            <div
              key={device.node_id}
              className="flex flex-col justify-between p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all shadow-lg"
            >
              <div>
                {/* Node Header */}
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                      {getDeviceIcon(device.device_type)}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white leading-tight">
                        {device.name}
                      </h3>
                      <span className="text-[10px] font-mono text-slate-500">
                        {device.node_id} • {device.ip_address || 'Local Host'}
                      </span>
                    </div>
                  </div>

                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase font-bold tracking-wider ${
                      isOnline
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : isStandby
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                        : 'bg-slate-800 text-slate-400 border border-slate-700/50'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isOnline
                          ? 'bg-emerald-400 animate-pulse'
                          : isStandby
                          ? 'bg-amber-400'
                          : 'bg-slate-500'
                      }`}
                    />
                    {device.status}
                  </span>
                </div>

                {/* State Telemetry Badges */}
                <div className="flex flex-wrap gap-2 mb-4 text-[11px] font-mono">
                  {/* Battery - only show when online and present */}
                  {isOnline && state.battery !== undefined && state.battery !== null && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                      <Battery className="w-3.5 h-3.5 text-emerald-400" />
                      {state.battery}% {state.charging ? '⚡' : ''}
                    </span>
                  )}
                  {/* Real CPU & RAM */}
                  {isOnline && state.cpu !== undefined && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                      CPU: {state.cpu}%
                    </span>
                  )}
                  {isOnline && state.ram !== undefined && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                      RAM: {state.ram}%
                    </span>
                  )}
                  {/* Real Volume */}
                  {isOnline && state.volume !== undefined && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                      <Volume2 className="w-3.5 h-3.5 text-amber-500" />
                      {state.volume}%
                    </span>
                  )}
                  {/* Standby / WoL Badge */}
                  {isStandby && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-amber-950/30 text-amber-300 border border-amber-900/40">
                      ⚡ WoL Ready
                    </span>
                  )}
                  {/* Disconnected / Offline Badge */}
                  {!isOnline && !isStandby && (
                    <span className="px-2 py-0.5 rounded bg-slate-900/80 text-slate-400 border border-slate-800">
                      Disconnected
                    </span>
                  )}
                  {state.temperature !== undefined && (
                    <span className="px-2 py-0.5 rounded bg-slate-900 text-cyan-300 border border-slate-800">
                      🌡️ {state.temperature}°C ({state.mode || 'cool'})
                    </span>
                  )}
                </div>
              </div>

              {/* Dynamic Action Controls based on Device Type */}
              <div className="pt-3 border-t border-slate-900 space-y-2.5">
                {/* 1. Host Laptop / Desktop */}
                {(device.device_type === 'laptop' || device.device_type === 'desktop') && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span className="flex items-center gap-1 font-mono">
                        <Volume2 className="w-3.5 h-3.5 text-amber-500" />
                        Master Vol: {state.volume ?? 50}%
                      </span>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={state.volume ?? 50}
                        onChange={(e) =>
                          sendCommand(device.node_id, 'volume', {
                            percent: parseInt(e.target.value),
                          })
                        }
                        className="w-28 accent-cyan-400 cursor-pointer"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2 pt-1">
                      <button
                        onClick={() => sendCommand(device.node_id, 'lock_screen')}
                        className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-900/50 text-xs font-mono transition-colors"
                      >
                        <Lock className="w-3.5 h-3.5" />
                        Lock PC
                      </button>
                      <button
                        onClick={() => sendCommand(device.node_id, 'launch_app', { app_name: 'wt.exe' })}
                        className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-mono transition-colors"
                      >
                        <Terminal className="w-3.5 h-3.5 text-amber-500" />
                        Terminal
                      </button>
                    </div>
                  </div>
                )}

                {/* 2. Mobile Phone (Android / iOS) */}
                {device.device_type === 'mobile' && (
                  <div className="space-y-2">
                    {!isOnline ? (
                      <div className="space-y-2">
                        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800/80 text-[11px] text-slate-400 font-mono leading-relaxed">
                          {state.status_detail || 'No active ADB connection. Toggle Wireless Debugging in Developer Options or plug USB.'}
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            onClick={async () => {
                              const ipInput = document.getElementById('adb-ip-input');
                              const val = ipInput?.value || '100.67.134.74';
                              const [ip, port] = val.includes(':') ? val.split(':') : [val, '0'];
                              try {
                                const res = await fetch('/api/android/connect', {
                                  method: 'POST',
                                  headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({ ip, port: parseInt(port) || 0 }),
                                });
                                const data = await res.json();
                                alert(data.message || (data.success ? 'Connected!' : 'Connect attempted.'));
                                fetchDevices();
                              } catch (err) {
                                alert('Connect error: ' + err);
                              }
                            }}
                            className="flex items-center justify-center gap-1 py-1.5 rounded-lg bg-purple-950/50 hover:bg-purple-900/60 text-purple-300 border border-purple-800/50 text-xs font-mono transition-colors"
                          >
                            <Wifi className="w-3.5 h-3.5" />
                            Connect ADB
                          </button>
                          <button
                            onClick={async () => {
                              try {
                                const res = await fetch('/api/android/mdns-discover', { method: 'POST' });
                                const data = await res.json();
                                alert(data.message || 'Discovery complete');
                                fetchDevices();
                              } catch (err) {
                                alert('Discovery error: ' + err);
                              }
                            }}
                            className="flex items-center justify-center gap-1 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-mono transition-colors"
                          >
                            <RefreshCw className="w-3.5 h-3.5 text-amber-500" />
                            mDNS Auto
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                            <Volume2 className="w-3.5 h-3.5 text-purple-400" />
                            Phone Vol: {state.volume ?? 50}%
                          </span>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={state.volume ?? 50}
                            onChange={(e) =>
                              sendCommand(device.node_id, 'volume', {
                                percent: parseInt(e.target.value),
                              })
                            }
                            className="w-28 accent-purple-400 cursor-pointer"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            onClick={() => sendCommand(device.node_id, 'lock')}
                            className="flex items-center justify-center gap-1 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-900/50 text-xs font-mono transition-colors"
                          >
                            <Lock className="w-3.5 h-3.5" />
                            Lock Phone
                          </button>
                          <button
                            onClick={() => sendCommand(device.node_id, 'wake')}
                            className="flex items-center justify-center gap-1 py-1.5 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-900/50 text-xs font-mono transition-colors"
                          >
                            <Power className="w-3.5 h-3.5" />
                            Wake Screen
                          </button>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            onClick={() =>
                              sendCommand(device.node_id, 'open_app', { app_name: 'youtube' })
                            }
                            className="py-1 rounded bg-slate-900 hover:bg-slate-800 text-xs font-mono text-red-300 border border-red-900/40"
                          >
                            Open YouTube
                          </button>
                          <button
                            onClick={() =>
                              sendCommand(device.node_id, 'open_app', { app_name: 'whatsapp' })
                            }
                            className="py-1 rounded bg-slate-900 hover:bg-slate-800 text-xs font-mono text-emerald-300 border border-emerald-900/40"
                          >
                            Open WhatsApp
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 3. Smart TV (LG WebOS / Android TV) */}
                {(device.device_type === 'smart_tv' || device.device_type === 'tv') && (
                  <div className="space-y-2">
                    {(!isOnline || isStandby) ? (
                      <div className="space-y-2">
                        <div className="p-2.5 rounded-lg bg-amber-950/20 border border-amber-900/40 text-[11px] text-amber-300/90 font-mono">
                          <div className="font-semibold flex items-center gap-1.5 mb-1 text-amber-300">
                            <Power className="w-3.5 h-3.5" /> TV in Standby Mode
                          </div>
                          <div>Target: {device.ip_address} ({state.mac ? `MAC ${state.mac}` : 'WoL Ready'})</div>
                          <div className="text-[10px] text-slate-400 mt-1">Wake-on-LAN magic packet configured to boot display remotely.</div>
                        </div>
                        <button
                          onClick={() => sendCommand(device.node_id, 'power_on')}
                          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-mono font-medium transition-all shadow-lg shadow-amber-500/10 cursor-pointer"
                        >
                          <Power className="w-4 h-4 text-amber-400" />
                          Wake on LAN (Power On TV)
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <button
                            onClick={() => sendCommand(device.node_id, 'power_off')}
                            className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-900/50 text-xs font-mono transition-colors"
                          >
                            <Power className="w-3.5 h-3.5 text-rose-400" />
                            Turn Off
                          </button>
                          <button
                            onClick={() => sendCommand(device.node_id, 'mute')}
                            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-mono transition-colors"
                          >
                            Mute
                          </button>
                          <button
                            onClick={() => sendCommand(device.node_id, 'volume_down')}
                            className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-mono"
                          >
                            Vol -
                          </button>
                          <button
                            onClick={() => sendCommand(device.node_id, 'volume_up')}
                            className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-mono"
                          >
                            Vol +
                          </button>
                        </div>
                        <div className="grid grid-cols-3 gap-1.5 text-[11px] font-mono">
                          <button
                            onClick={() => sendCommand(device.node_id, 'launch_app', { app: 'youtube' })}
                            className="py-1 rounded bg-red-950/30 hover:bg-red-900/40 text-red-300 border border-red-900/40 text-center"
                          >
                            YouTube
                          </button>
                          <button
                            onClick={() => sendCommand(device.node_id, 'launch_app', { app: 'netflix' })}
                            className="py-1 rounded bg-red-950/30 hover:bg-red-900/40 text-red-300 border border-red-900/40 text-center"
                          >
                            Netflix
                          </button>
                          <button
                            onClick={() => sendCommand(device.node_id, 'launch_app', { app: 'hotstar' })}
                            className="py-1 rounded bg-blue-950/30 hover:bg-blue-900/40 text-blue-300 border border-blue-900/40 text-center"
                          >
                            Hotstar
                          </button>
                          <button
                            onClick={() => sendCommand(device.node_id, 'launch_app', { app: 'amazon' })}
                            className="py-1 rounded bg-cyan-950/30 hover:bg-cyan-900/40 text-cyan-300 border border-cyan-900/40 text-center"
                          >
                            Prime Video
                          </button>
                          <button
                            onClick={() => sendCommand(device.node_id, 'launch_app', { app: 'spotify' })}
                            className="py-1 rounded bg-emerald-950/30 hover:bg-emerald-900/40 text-emerald-300 border border-emerald-900/40 text-center"
                          >
                            Spotify
                          </button>
                          <button
                            onClick={() => sendCommand(device.node_id, 'switch_input', { input: 'HDMI_1' })}
                            className="py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-center"
                          >
                            HDMI 1
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 4. Smart Light Controls */}
                {device.device_type === 'light' && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() =>
                        sendCommand(
                          device.node_id,
                          state.power === 'on' ? 'turn_off' : 'turn_on'
                        )
                      }
                      className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg text-xs font-mono transition-colors border ${
                        state.power === 'on'
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          : 'bg-slate-900 text-slate-400 border-slate-800'
                      }`}
                    >
                      <Power className="w-3.5 h-3.5" />
                      {state.power === 'on' ? 'Turn Off' : 'Turn On'}
                    </button>
                    <button
                      onClick={() =>
                        sendCommand(device.node_id, 'set_color', { value: '#00f2fe' })
                      }
                      className="px-3 py-1.5 rounded-lg bg-cyan-950/50 border border-cyan-800/40 text-cyan-300 text-xs font-mono"
                    >
                      Cyan
                    </button>
                    <button
                      onClick={() =>
                        sendCommand(device.node_id, 'set_color', { value: '#7f00ff' })
                      }
                      className="px-3 py-1.5 rounded-lg bg-purple-950/50 border border-purple-800/40 text-purple-300 text-xs font-mono"
                    >
                      Purple
                    </button>
                  </div>
                )}

                {/* 5. AC Climate Controls */}
                {device.device_type === 'ac' && (
                  <div className="flex items-center justify-between gap-2">
                    <button
                      onClick={() =>
                        sendCommand(device.node_id, 'set_climate', {
                          temperature: (state.temperature || 22) - 1,
                        })
                      }
                      className="px-3 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-bold hover:bg-slate-800"
                    >
                      -
                    </button>
                    <span className="text-xs font-mono text-white">
                      Target: {state.temperature || 22}°C
                    </span>
                    <button
                      onClick={() =>
                        sendCommand(device.node_id, 'set_climate', {
                          temperature: (state.temperature || 22) + 1,
                        })
                      }
                      className="px-3 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-bold hover:bg-slate-800"
                    >
                      +
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
