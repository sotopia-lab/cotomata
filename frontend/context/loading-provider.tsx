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

  // Function to create WebSocket connection
  const connect = useCallback(() => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket('ws://localhost:8000/ws');

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
        if (data.session_id) {
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
      if (!state.currentSessionId || !websocketRef.current) {
        reject(new Error('No active session or WebSocket not connected'));
        return;
      }

      websocketRef.current.send(JSON.stringify({
        command: 'init_process',
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



// "use client"

// import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

// interface LoadingContextType {
//   isReady: boolean;
//   error: string | null;
//   ws: WebSocket | null;
// }

// const LoadingContext = createContext<LoadingContextType>({
//   isReady: false,
//   error: null,
//   ws: null,
// });

// export const useLoading = () => useContext(LoadingContext);

// export function LoadingProvider({ children }: { children: React.ReactNode }) {
//   const [isReady, setIsReady] = useState(false);
//   const [error, setError] = useState<string | null>(null);
//   const [ws, setWs] = useState<WebSocket | null>(null);
//   const wsRef = useRef<WebSocket | null>(null);
//   const [serverUrl, setServerUrl] = useState('http://localhost:8000');

//   useEffect(() => {
//     const connectWebSocket = () => {
//       wsRef.current = new WebSocket(`${serverUrl.replace("http", "ws")}/ws`);
    
//       wsRef.current.onopen = () => {
//         console.log("WebSocket connection established");
//         setWs(wsRef.current);
//         setIsReady(true);
//         setError(null)
//       };

//       wsRef.current.onmessage = (event) => {}
    
//       wsRef.current.onerror = (event) => {
//         console.error("WebSocket error:", event);
//         setError("WebSocket connection error");
//       };
    
//       wsRef.current.onclose = (event) => {
//         console.log("WebSocket connection closed:", event);
//         setWs(null);
//         setIsReady(false);
//       };
//     }

//     connectWebSocket();
  
//     return () => {
//       console.log("Cleaning up WebSocket connection...");
//       if (wsRef.current) {
//         wsRef.current.close()
//       }
//     };
//   }, [serverUrl]);
  

//   // useEffect(() => {
//   //   const connectWebSocket = () => {
//   //       // Connect to the FastAPI WebSocket endpoint
//   //       wsRef.current = new WebSocket("ws://localhost:8000/ws");
//   //       // wsRef.current = socket;
//   //       console.log("WebSocket connection established", wsRef.current, wsRef.current);


//   //       wsRef.current.onopen = () => {
//   //         console.log("WebSocket connection established");
//   //         setWs(wsRef.current);
//   //         // Optionally, you can send an initial message here if needed:
//   //         // socket.send(JSON.stringify({ command: "init", ... }));
//   //       };

//   //       wsRef.current.onmessage = (event) => {
//   //       console.log("Received message:", event.data);
//   //       try {
//   //         const data = JSON.parse(event.data);

//   //         // Example: handle an initialization response
//   //         if (data.command === "init_process_result") {
//   //           console.log("Received init_process_result:", data);
//   //           if (data.success) {
//   //             setIsReady(true);
//   //             const storedSessionId = localStorage.getItem('cotomata-sessionId');
//   //             if (storedSessionId && storedSessionId !== data.session_id) {
//   //               setError('Session ID mismatch. Please try again.');
//   //               if (wsRef.current) {
//   //                 wsRef.current.close()
//   //               }
//   //               return;
//   //             }
//   //             localStorage.setItem('cotomata-sessionId', data.session_id);
//   //           } else {
//   //             setError(data.error || 'Failed to initialize OpenHands');
//   //             if (wsRef.current) {
//   //               wsRef.current.close()
//   //             }
//   //           }
//   //         }

//   //       } catch (err) {
//   //         console.error("Error parsing message:", err);
//   //       }
//   //     };

//   //     wsRef.current.onerror = (event) => {
//   //       console.error("WebSocket error:", event);
//   //       setError("WebSocket connection error");
//   //     };

//   //     wsRef.current.onclose = (event) => {
//   //       console.log("WebSocket connection closed:", event);
//   //       setWs(null);
//   //     };
//   //   };

//   //   connectWebSocket();

//   //   return () => {
//   //     console.log("Cleaning up WebSocket connection...");
//   //     if (wsRef.current) {
//   //       wsRef.current.close()
//   //     }
//   //   };
//   // }, []);

//   // const sendMessage = (message: any) => {
//   //   if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
//   //     wsRef.current.send(JSON.stringify(message));
//   //   } else {
//   //     console.error("WebSocket is not connected.");
//   //   }
//   // };

//   return (
//     <LoadingContext.Provider value={{ isReady, error, ws }}>
//       {children}
//     </LoadingContext.Provider>
//   );
// }
