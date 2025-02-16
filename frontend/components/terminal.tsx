"use client"

import React, { useState, useEffect, useRef } from 'react';
import { Socket } from 'socket.io-client';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Terminal as TerminalIcon } from 'lucide-react';
import { cn } from "@/lib/utils";
import { useWebSocket } from '@/hooks/useWebSocket';

interface TerminalState {
  user: string;
  hostname: string;
  currentPath: string;
}

interface HistoryEntry {
  prompt: string;
  command?: string;
  output?: string;
}

interface TerminalProps {
  externalMessages: string[];
  socket: WebSocket | null;
  sessionId: string | null;
}

const stripAnsiCodes = (text: string): string => {
  return text.replace(/\[\d+(?:;\d+)*m|\[\d+m|\[0m|\[1m/g, '');
};

export const Terminal = ({ externalMessages, socket, sessionId }: TerminalProps) => {
  const [terminalState, setTerminalState] = useState<TerminalState>({
    user: '',
    hostname: '',
    currentPath: ''
  });
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number | null>(null);
  const [input, setInput] = useState('');
  const historyRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const initializedRef = useRef(false);
  const { sendTerminalCommand } = useWebSocket();

  useEffect(() => {
    const initializeFileSystem = async () => {
      if (!initializedRef.current) {
        try {
          await sendTerminalCommand("whoami && hostname && pwd");
          await sendTerminalCommand("echo '**FILE_SYSTEM_REFRESH**' && find -L /workspace -type f");
          initializedRef.current = true;
        } catch (error) {
          console.error("Error initializing file system:", error);
        }
      }
    };
  
    initializeFileSystem();
  }, []);

  useEffect(() => {
    historyRef.current?.scrollTo({
      top: historyRef.current.scrollHeight,
      behavior: 'smooth'
    });
  }, [history]);

  useEffect(() => {
    if (externalMessages.length === 0) return;

    const message = externalMessages[externalMessages.length - 1];
    if (!message.trim()) return;

    if (!terminalState.user || !terminalState.hostname || !terminalState.currentPath) {
      const [user, hostname, path] = message.split('\n').map(line => line.trim());
      if (user && hostname && path) {
        setTerminalState({ user, hostname, currentPath: path });
        return;
      }
    }

    if (message.startsWith('/')) {
      setTerminalState(prev => ({
        ...prev,
        currentPath: message.trim()
      }));
      return;
    }

    setHistory(prev => {
      const lastEntry = prev[prev.length - 1];
      if (lastEntry?.command?.startsWith('cd ')) return prev;

      if (lastEntry && !lastEntry.output) {
        return [...prev.slice(0, -1), { ...lastEntry, output: message }];
      }

      return [...prev, { prompt: getPrompt(), output: message }];
    });
  }, [externalMessages]);

  const getPrompt = () => {
    const { user, hostname, currentPath } = terminalState;
    if (!user || !hostname) return '$ ';
    return `${user}@${hostname}:${currentPath}$ `;
  };

  const handleCommand = async (command: string) => {
    if (!command.trim()) return;

    const currentPrompt = getPrompt();
    setHistory(prev => [...prev, { prompt: currentPrompt, command }]);
    setHistoryIndex(null);

    if (command.startsWith('cd ')) {
      const newPath = command.slice(3).trim();
      const targetPath = newPath.startsWith('/')
        ? newPath.replace(/\/+/g, '/')
        : newPath === '..'
          ? `${terminalState.currentPath}/..`.replace(/\/+/g, '/')
          : `${terminalState.currentPath}/${newPath}`.replace(/\/+/g, '/');

      try {
        await sendTerminalCommand(`cd "${targetPath}" && pwd`);
      } catch (error) {
        console.error('Error sending terminal command:', error);
      }
    } else {
      try {
        await sendTerminalCommand(command);
      } catch (error) {
        console.error('Error sending terminal command:', error);
      }
    }

    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleCommand(input);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length > 0) {
        if (historyIndex === null) {
          setHistoryIndex(history.length - 1);
        } else if (historyIndex > 0) {
          setHistoryIndex(historyIndex - 1);
        }
        const command = history[historyIndex ?? history.length - 1]?.command;
        if (command) setInput(command);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex !== null) {
        if (historyIndex < history.length - 1) {
          setHistoryIndex(historyIndex + 1);
          setInput(history[historyIndex + 1].command || '');
        } else {
          setHistoryIndex(null);
          setInput('');
        }
      }
    }
  };

  return (
    <Card className={cn(
      "flex flex-col rounded-none border-t bg-black", 
      "h-full" // Use full parent height
    )}>
      <CardHeader className="border-b border-border/50 px-4 py-2 space-y-0">
        <div className="flex items-center gap-2">
          <TerminalIcon className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Terminal
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col flex-1 overflow-hidden p-0 font-mono">
        <ScrollArea ref={historyRef} className="flex-1 overflow-y-auto">
          <div className="p-4 space-y-2 min-h-full">
            {history.map((entry, index) => (
              <div key={index} className="space-y-1">
                {entry.command && (
                  <div className="flex">
                    <span className="text-green-500">{entry.prompt}</span>
                    <span className="text-white">{entry.command}</span>
                  </div>
                )}
                {entry.output && (
                  <div className={cn(
                    "whitespace-pre-wrap break-all",
                    entry.output.includes('error') || entry.output.includes('Error')
                      ? "text-red-400"
                      : entry.output.includes('notice')
                        ? "text-blue-400"
                        : "text-gray-300"
                  )}>
                    {stripAnsiCodes(entry.output)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>

        <div className="flex items-center px-4 py-2 border-t border-border/50">
          <span className="text-green-500 mr-2">{getPrompt()}</span>
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent border-none outline-none text-white"
            spellCheck={false}
            autoComplete="off"
            autoCapitalize="off"
          />
        </div>
      </CardContent>
    </Card>
  );
};