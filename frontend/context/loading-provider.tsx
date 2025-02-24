"use client";

import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';

export interface WebSocketMessage {
  channel?: string;
  message?: string;
  type?: string;
  success?: boolean;
  session_id?: string;
  error?: string;
}

export interface WebSocketContextState {
  connected: boolean;
  messages: WebSocketMessage[];
  currentSessionId: string | null;
  sessionType: string | null;
  error: string | null;
}

export interface WebSocketContextValue extends WebSocketContextState {
  socket: WebSocket | null;
  connect: () => void;
  disconnect: () => void;
  createSession: (sessionType: string) => Promise<string>;
  joinSession: (sessionId: string) => Promise<boolean>;
  killSession: (sessionId: string) => Promise<boolean>;
  sendChatMessage: (message: string) => void;
  saveFile: (path: string, content: string) => void;
  sendTerminalCommand: (command: string) => void;
  initAgentConversation: () => Promise<boolean>;
  initProcess: () => Promise<boolean>;
  clearMessages: () => void;
}

const initialState: WebSocketContextState = {
  connected: false,
  messages: [],
  currentSessionId: null,
  sessionType: null,
  error: null,
};

// Create the context
const WebSocketContext = createContext<WebSocketContextValue | undefined>(undefined);

// Action types for the reducer
type WebSocketAction =
  | { type: 'CONNECTED' }
  | { type: 'DISCONNECTED' }
  | { type: 'MESSAGE_RECEIVED'; payload: WebSocketMessage }
  | { type: 'SET_SESSION'; payload: { sessionId: string; sessionType: string } }
  | { type: 'CLEAR_SESSION' }
  | { type: 'SET_ERROR'; payload: string }
  | { type: 'CLEAR_ERROR' }
  | { type: 'CLEAR_MESSAGES' };

// Reducer to manage state updates
function webSocketReducer(state: WebSocketContextState, action: WebSocketAction): WebSocketContextState {
  switch (action.type) {
    case 'CONNECTED':
      return { ...state, connected: true, error: null };
    case 'DISCONNECTED':
      return { ...state, connected: false };
    case 'MESSAGE_RECEIVED':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'SET_SESSION':
      return {
        ...state,
        currentSessionId: action.payload.sessionId,
        sessionType: action.payload.sessionType,
      };
    case 'CLEAR_SESSION':
      return {
        ...state,
        currentSessionId: null,
        sessionType: null,
      };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'CLEAR_ERROR':
      return { ...state, error: null };
    case 'CLEAR_MESSAGES':
      return { ...state, messages: [] };
    default:
      return state;
  }
}

// WebSocket Provider component
function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(webSocketReducer, initialState);
  const websocketRef = React.useRef<WebSocket | null>(null);
  const sessionIdRef = React.useRef<string | null>(null);

  // Function to create WebSocket connection
  const connect = useCallback(() => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) return;

    // const ws = new WebSocket('ws://localhost:8000/ws');
    const ws = new WebSocket('wss://sotopia-lab--cotomata-modalapp-serve-dev.modal.run/ws');

    ws.onopen = () => {
      dispatch({ type: 'CONNECTED' });
    };

    ws.onclose = () => {
      dispatch({ type: 'DISCONNECTED' });
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      dispatch({ type: 'MESSAGE_RECEIVED', payload: data });
    };

    ws.onerror = (error) => {
      dispatch({ type: 'SET_ERROR', payload: 'WebSocket error occurred' });
    };

    websocketRef.current = ws;
  }, []);

  // Function to disconnect WebSocket
  const disconnect = useCallback(() => {
    websocketRef.current?.close();
    websocketRef.current = null;
    dispatch({ type: 'DISCONNECTED' });
  }, []);

  // Create a new session
  const createSession = useCallback(async (sessionType: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!websocketRef.current) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      websocketRef.current.send(JSON.stringify({
        command: 'create_session',
        session_type: sessionType
      }));

      const handleMessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        console.log("handle message", data);
        if (data.session_id) {
          sessionIdRef.current = data.session_id;
          dispatch({
            type: 'SET_SESSION',
            payload: { sessionId: data.session_id, sessionType }
          });
          websocketRef.current?.removeEventListener('message', handleMessage);
          resolve(data.session_id);
        }
      };

      websocketRef.current.addEventListener('message', handleMessage);
    });
  }, []);

  // Join an existing session
  const joinSession = useCallback(async (sessionId: string): Promise<boolean> => {
    return new Promise((resolve, reject) => {
      if (!websocketRef.current) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      websocketRef.current.send(JSON.stringify({
        command: 'join_session',
        session_id: sessionId
      }));

      const handleMessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        if (data.success !== undefined) {
          if (data.success) {
            dispatch({
              type: 'SET_SESSION',
              payload: { sessionId, sessionType: state.sessionType || 'unknown' }
            });
          }
          websocketRef.current?.removeEventListener('message', handleMessage);
          resolve(data.success);
        }
      };

      websocketRef.current.addEventListener('message', handleMessage);
    });
  }, [state.sessionType]);

  // Send a chat message
  const sendChatMessage = useCallback((message: string) => {
    if (!state.currentSessionId) return;

    websocketRef.current?.send(JSON.stringify({
      command: 'chat_message',
      session_id: state.currentSessionId,
      message
    }));
  }, [state.currentSessionId]);

  // Save a file
  const saveFile = useCallback((path: string, content: string) => {
    if (!state.currentSessionId) return;

    websocketRef.current?.send(JSON.stringify({
      command: 'save_file',
      session_id: state.currentSessionId,
      path,
      content
    }));
  }, [state.currentSessionId]);

  // Send a terminal command
  const sendTerminalCommand = useCallback((input_command: string) => {
    const currentSessionId = sessionIdRef.current;
    console.log("term", currentSessionId, websocketRef.current)
    if (!state.currentSessionId) return;

    websocketRef.current?.send(JSON.stringify({
      command: 'terminal_command',
      session_id: state.currentSessionId,
      input_command
    }));
  }, [state.currentSessionId]);

  // Initialize agent conversation
  const initAgentConversation = useCallback(async (): Promise<boolean> => {
    return new Promise((resolve, reject) => {
      if (!state.currentSessionId || !websocketRef.current) {
        reject(new Error('No active session or WebSocket not connected'));
        return;
      }

      websocketRef.current.send(JSON.stringify({
        command: 'init_agent_conversation',
        session_id: state.currentSessionId
      }));

      const handleMessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        if (data.success !== undefined) {
          websocketRef.current?.removeEventListener('message', handleMessage);
          resolve(data.success);
        }
      };

      websocketRef.current.addEventListener('message', handleMessage);
    });
  }, [state.currentSessionId]);

  // Initialize process
  const initProcess = useCallback(async (): Promise<boolean> => {
    return new Promise((resolve, reject) => {
      const currentSessionId = sessionIdRef.current;
      if (!currentSessionId || !websocketRef.current) {
        reject(new Error('No active session or WebSocket not connected'));
        return;
      }

      websocketRef.current.send(JSON.stringify({
        command: 'init_process',
        session_id: currentSessionId
      }));

      const handleMessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        if (data.success !== undefined) {
          websocketRef.current?.removeEventListener('message', handleMessage);
          resolve(data.success);
        }
      };

      websocketRef.current.addEventListener('message', handleMessage);
    });
  }, []);

  // Kill a session
  const killSession = useCallback(async (sessionId: string): Promise<boolean> => {
    return new Promise((resolve, reject) => {
      if (!websocketRef.current) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      websocketRef.current.send(JSON.stringify({
        command: 'kill_session',
        session_id: sessionId
      }));

      const handleMessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        if (data.success !== undefined) {
          if (data.success) {
            dispatch({ type: 'CLEAR_SESSION' });
          }
          websocketRef.current?.removeEventListener('message', handleMessage);
          resolve(data.success);
        }
      };

      websocketRef.current.addEventListener('message', handleMessage);
    });
  }, []);

  // Clear messages
  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' });
  }, []);

  // Auto-connect when the provider mounts
  useEffect(() => {
    connect();
    return () => {
      if (websocketRef.current?.readyState === 1) {
        disconnect();
      }
    };
  }, [connect, disconnect]);

  const value: WebSocketContextValue = {
    ...state,
    socket: websocketRef.current,
    connect,
    disconnect,
    createSession,
    joinSession,
    killSession,
    sendChatMessage,
    saveFile,
    sendTerminalCommand,
    initAgentConversation,
    initProcess,
    clearMessages,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export { WebSocketContext, WebSocketProvider };