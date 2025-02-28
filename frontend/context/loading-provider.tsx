"use client"

import { createContext, useContext, useState, useEffect } from 'react';
import { io, Socket } from 'socket.io-client';


interface LoadingContextType {
  isReady: boolean;
  error: string | null;
  socket: Socket | null;
}

const LoadingContext = createContext<LoadingContextType>({
  isReady: false,
  error: null,
  socket: null,
});

export const useLoading = () => useContext(LoadingContext);

export function LoadingProvider({ children }: { children: React.ReactNode }) {
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    let socketInstance: Socket;

    const initialize = async () => {
      try {
        console.log('Creating socket instance...');
        socketInstance = io('http://localhost:8000', {
          transports: ['websocket'],
          reconnection: true,
          autoConnect: true
        });

        // Log all incoming events for debugging
        socketInstance.onAny((eventName, ...args) => {
          console.log(`[Socket Event] ${eventName}:`, args);
        });

        socketInstance.on('connect', () => {
          console.log('Socket connected with ID:', socketInstance.id);
          setSocket(socketInstance);
        });

        socketInstance.on('connect_error', (error) => {
          console.error('Socket connection error:', error);
          setError(`Connection failed: ${error.message}`);
        });

        socketInstance.on('init_process_result', (result) => {
          console.log('Received init_process_result:', result);
          if (result.success) {
            setIsReady(true);
            // join session existing check implement after kill session
            const storedSessionId = localStorage.getItem('cotomata-sessionId');
            if (storedSessionId) {
              if (storedSessionId !== result.sessionId) {
                setError('Session ID mismatch. Please try again.');
                socketInstance.disconnect();
                return;
              }
            }
            localStorage.setItem('cotomata-sessionId', result.sessionId);
          } else {
            setError(result.error || 'Failed to initialize OpenHands');
            socketInstance.disconnect();
          }
        });
      } catch (err) {
        console.error('Socket initialization error:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      }
    };

    initialize();

    return () => {
      console.log('Cleaning up socket connection...');
      socketInstance?.disconnect();
    };
  }, []);

  return (
    <LoadingContext.Provider value={{ isReady, error, socket }}>
      {children}
    </LoadingContext.Provider>
  );
}
