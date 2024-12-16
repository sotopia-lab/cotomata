/**
 * app/page.tsx
 *
 * This file serves as the main entry point for the React application. It manages the overall
 * application state, handles socket connections for real-time communication, and coordinates
 * interactions between various components such as the code editor, terminal, chat interface,
 * and file system.
 *
 * Key Features:
 * - Establishes a WebSocket connection to the server for real-time updates.
 * - Manages application state using React hooks, including messages, terminal output,
 *   and active panels.
 * - Handles incoming messages from the server, including agent actions and chat messages.
 * - Provides a user interface for code editing, browsing, and terminal commands.
 *
 * Components Used:
 * - CodeEditor: For editing code files.
 * - FileSystem: For displaying and managing files.
 * - Terminal: For executing commands and displaying output.
 * - ChatInterface: For user interaction and messaging.
 * - Browser: For displaying web content.
 * - Sidebar: For navigation between different application panels.
 * - SceneContext: For displaying context messages from agents.
 *
 */
"use client"

import React, { useEffect, useState } from 'react';
// import io from 'socket.io-client';
// import { CodeEditor } from '@/components/CodeEditor/CodeEditor';
// import { FileSystem } from '@/components/CodeEditor/FileSystem';
// import { Terminal } from '@/components/Terminal/Terminal';
// import { ChatInterface } from '@/components/ChatInterface/ChatInterface';
// import { Browser } from '@/components/Browser/Browser';
// import { Sidebar } from '@/components/Sidebar/Sidebar';
// import { SceneContext } from '@/components/Sidebar/SceneContext';
import { useFileSystem } from "@/hooks/useFileSystem";
import { FileSystem } from "@/components/file-system";
import { io, Socket } from 'socket.io-client';
import { CodeEditor } from '@/components/code-editor';
import { ChatInterface } from '@/components/chat-interface';
import { Terminal } from '@/components/terminal';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';

type PanelOption = 'fileSystem' | 'sceneContext';

export default function App() {
  const {
    fileSystem,
    openFiles,
    activeFile,
    handleFileSelect,
    handleFileClose,
    handleFileChange,
    addFile,
    setActiveFile,
    updateFileSystemFromList
  } = useFileSystem();

  const [socket, setSocket] = useState<Socket | null>(null);
  const [activePanel, setActivePanel] = useState<PanelOption>('fileSystem');
  const [messages, setMessages] = useState<Array<{text: string, type: 'message' | 'status'}>>([]);
  const [terminalMessages, setTerminalMessages] = useState<string[]>([]);

  useEffect(() => {

    // Initialize socket connection to the server
    const socketInstance = io('http://localhost:3000', {
      transports: ['websocket'],
      reconnection: true
    });

    // Log connection status
    socketInstance.on('connect', () => {
      console.log('Connected to server with ID:', socketInstance.id);
    });

    // Log connection errors
    socketInstance.on('connect_error', (error) => {
      console.error('Connection error:', error);
    });

    setSocket(socketInstance);

    // Cleanup on component unmount
    return () => {
      if (socketInstance) {
        socketInstance.disconnect();
      }
    };
  }, []);

  const handleSidebarSelect = (option: PanelOption) => {
    setActivePanel(option); // Update the active panel based on user selection
  };

  return (
    <>
    <div className="flex h-screen w-full">
      <div className="w-64 border-r">
        <FileSystem
          fileSystem={fileSystem.tree}
          onFileSelect={handleFileSelect}
          socket={socket}
        />
      </div>
      <div className="flex-1 h-screen flex flex-col">
        <ResizablePanelGroup direction='vertical'>
          <ResizablePanel defaultSize={75}>
            <Tabs defaultValue="editor" className="h-full flex flex-col">
              <TabsList className='mx-2 mt-2'>
                <TabsTrigger value="editor">Editor</TabsTrigger>
                <TabsTrigger value="browser">Browser</TabsTrigger>
              </TabsList>
              <TabsContent value="editor" className='flex-1 min-h-0 overflow-hidden'>
                <CodeEditor
                  openFiles={openFiles}
                  activeFile={activeFile}
                  onFileClose={handleFileClose}
                  onFileSelect={setActiveFile}
                  onChange={handleFileChange}
                  socket={socket}
                />
              </TabsContent>
              <TabsContent value="browser" className='flex-1'>
              </TabsContent>
            </Tabs>
          </ResizablePanel>
          <ResizableHandle />
          <ResizablePanel defaultSize={25}>
            <Terminal externalMessages={terminalMessages} socket={socket}/>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
      <div className="w-64 border-l">
        <ChatInterface
          messages={messages}
          socket={socket}
          onSendMessage={(text: string) => {
            // Update messages state with the user's message
            setMessages(prev => [...prev, {
              text: `User: ${text}`,
              type: 'message' as const
            }]);
          }}
        />
      </div>
    </div>
    </>
  );
}