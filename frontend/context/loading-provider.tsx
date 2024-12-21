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

  useEffect(() => {
    let initTimeout: NodeJS.Timeout;
    let socketInstance: Socket;

    const initialize = async () => {
      try {
        socketInstance = io('http://localhost:3000', {
          transports: ['websocket'],
          reconnection: true,
        });

        initTimeout = setTimeout(() => {
          setError('Initialization timed out after 5 minutes');
          socketInstance?.disconnect();
        }, 5 * 60 * 1000);

        socketInstance.on('connect', () => {
          console.log('Connected to server with ID:', socketInstance.id);
          socketInstance.emit('init_process');
        });

        socketInstance.on('connect_error', (error) => {
          setError(`Connection failed: ${error.message}`);
        });

        socketInstance.on('init_process_result', (result) => {
          clearTimeout(initTimeout);
          if (result.success) {
            setSocket(socketInstance);
            setIsReady(true);
          } else {
            setError(result.error || 'Failed to initialize OpenHands');
            socketInstance.disconnect();
          }
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      }
    };

    initialize();

    return () => {
      clearTimeout(initTimeout);
      socketInstance?.disconnect();
    };
  }, []);

  return (
    <LoadingContext.Provider value={{ isReady, error, socket }}>
      {children}
    </LoadingContext.Provider>
  );
}
