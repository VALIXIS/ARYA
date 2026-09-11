import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useWebSocket Hook
 * Persistent streaming connection to ARYA's agent core.
 */
export function useWebSocket({ onStateChange, onAgentExecution, onChatReply }) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectedDevices, setConnectedDevices] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);

  const callbacksRef = useRef({ onStateChange, onAgentExecution, onChatReply });
  useEffect(() => {
    callbacksRef.current = { onStateChange, onAgentExecution, onChatReply };
  });

  const isUnmountedRef = useRef(false);
  const pingIntervalRef = useRef(null);

  const connect = useCallback(() => {
    if (isUnmountedRef.current) return;

    // Determine WS URL based on current host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/agent`;

    try {
      if (wsRef.current) {
        try {
          wsRef.current.onclose = null;
          wsRef.current.onerror = null;
          wsRef.current.close();
        } catch (e) {}
      }

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isUnmountedRef.current) return;
        setIsConnected(true);
        console.log('[WS] Connected to ARYA Core');

        // Start ping heartbeat every 15s to keep connection alive
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 15000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const type = data.type;

          if (type === 'system_status') {
            if (data.connected_devices) setConnectedDevices(data.connected_devices);
          } else if (type === 'state_change') {
            callbacksRef.current.onStateChange?.(data.state);
          } else if (type === 'agent_execution') {
            callbacksRef.current.onAgentExecution?.(data);
          } else if (type === 'chat_response') {
            callbacksRef.current.onChatReply?.(data.reply);
          } else if (type === 'device_status_change') {
            setConnectedDevices((prev) => {
              if (data.status === 'online') {
                return Array.from(new Set([...prev, data.node_id]));
              } else {
                return prev.filter((id) => id !== data.node_id);
              }
            });
          }
        } catch (e) {
          console.error('[WS] Error parsing frame:', e);
        }
      };

      ws.onclose = () => {
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        setIsConnected(false);
        wsRef.current = null;
        if (!isUnmountedRef.current) {
          if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch (err) {
      setIsConnected(false);
      if (!isUnmountedRef.current) {
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(connect, 4000);
      }
    }
  }, []);

  useEffect(() => {
    isUnmountedRef.current = false;
    connect();
    return () => {
      isUnmountedRef.current = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (wsRef.current) {
        try {
          wsRef.current.onclose = null;
          wsRef.current.onerror = null;
          wsRef.current.close();
        } catch (e) {}
      }
    };
  }, [connect]);

  const sendMessage = useCallback((text, responseLength = 'Normal') => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'user_message',
          message: text,
          response_length: responseLength,
        })
      );
      return true;
    }
    return false;
  }, []);

  const sendDeviceCommand = useCallback((nodeId, action, params = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'device_command',
          node_id: nodeId,
          action: action,
          params: params,
        })
      );
      return true;
    }
    return false;
  }, []);


  return {
    isConnected,
    connectedDevices,
    sendMessage,
    sendDeviceCommand,
  };
}
