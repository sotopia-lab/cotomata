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
import { Browser } from '@/components/browser';
import { SceneContext } from '@/components/scene-context';
import { ChatInterface } from '@/components/chat-interface';
import { Terminal } from '@/components/terminal';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { SidebarTrigger } from '@/components/ui/sidebar';

type PanelOption = 'fileSystem' | 'sceneContext';

// need for run-dataflow post req 
 
// async function runPythonCommand() {
//   const response = await fetch('/api/run-agent', {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/json' },
//     body: JSON.stringify({ command: 'print("Hello, Python!")' }),
//   });
//   const result = await response.json();
//   console.log(result);
// }

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
  const [activeTab, setActiveTab] = useState<'editor' | 'browser'>('editor');
  const [browserUrl, setBrowserUrl] = useState('https://example.com');
  const [messages, setMessages] = useState<Array<{text: string, type: 'message' | 'status'}>>([]);
  const [terminalMessages, setTerminalMessages] = useState<string[]>([]);
  const [sceneMessages, setSceneMessages] = useState<{ text: string, agentName: string }[]>([]);

  useEffect(() => {

    // Initialize socket connection to the server
    const socketInstance = io('http://localhost:3000', {
      transports: ['websocket'],
      reconnection: true
    });

    // Log connection status
    socketInstance.on('connect', () => {
      console.log('Connected to server with ID:', socketInstance.id);
      // runPythonCommand();
    });
    console.log('socket connect', socketInstance)

    // Log connection errors
    socketInstance.on('connect_error', (error) => {
      console.error('Connection error:', error);
    });

    socketInstance.emit('init_process');
    socketInstance.on('init_process_result', (result) => {
      if (result.status === 'error') {
        console.error('Process initialization failed:', result.error);
      } else {
        console.log('Process started successfully');
      }
    });


    setSocket(socketInstance);

    // Cleanup on component unmount
    return () => {
      if (socketInstance) {
        socketInstance.disconnect();
      }
    };
  }, []);

  useEffect(() => {
    // Function to handle new messages received from the socket
    const handleNewMessage = (data: any) => {
      try {
        // Parse the incoming message data
        const messageData = JSON.parse(data.message);

        // Log the entire messageData for debugging
        console.log('Received message data:', messageData);

        // Check if messageData.data is defined
        if (!messageData.data) {
          console.error('messageData.data is undefined:', messageData);
          return; // Exit if data is not present
        }

        // Handle Scene context messages
        if (data.channel.startsWith('Scene:')) {
          if (messageData.data.data_type === "text") {
            // Update scene messages and set active panel to scene context
            setSceneMessages(prev => [...prev, { text: messageData.data.text, agentName: data.channel }]);
            setActivePanel('sceneContext');
          }
          return;
        }

        // Check if it's an agent action
        if (messageData.data.data_type === "agent_action") {
          handleAgentAction(messageData);
        }
        // Check if it's a command output
        else if (messageData.data.data_type === "text" &&
                 messageData.data.text.includes("CmdOutputObservation") &&
                 !messageData.data.text.includes("**FILE_SYSTEM_REFRESH**")) {
          // Try to extract output from success case (exit code=0)
          let parts = messageData.data.text.split("**CmdOutputObservation (source=None, exit code=0)**");

          // If not found, try to extract from error case (exit code=1)
          if (parts.length === 1) {
            parts = messageData.data.text.split("**CmdOutputObservation (source=None, exit code=1)**");
          }

          // If we found output in either case, add it to terminal messages
          if (parts.length > 1) {
            const outputText = parts[1].trim();
            // Update terminal messages with the command output
            setTerminalMessages(prev => [...prev, outputText]);
          }
        }

        // Handle file structure refresh response
        if (messageData.data.data_type === "text" &&
            messageData.data.text.includes("CmdOutputObservation") &&
            messageData.data.text.includes("**FILE_SYSTEM_REFRESH**")) {
          const parts = messageData.data.text.split("**CmdOutputObservation (source=None, exit code=0)**");
          if (parts.length > 1) {
            const fileList = parts[1].trim().split('\n').filter(Boolean).slice(1);
            updateFileSystemFromList(fileList);
          }
        }

        // Handle file content response
        if (messageData.data.data_type === "text" &&
          messageData.data.text.includes("**FILE_CONTENT**")) {
        // Split the response by new lines
        const lines = messageData.data.text.split('\n').slice(1);
        console.log('lines', lines);

        // Check if the response has at least 3 parts
        if (lines.length >= 3) {
          const filePath = lines[1].trim(); // The second line contains the file path
          console.log('filePath', filePath);
          const fileContent = lines.slice(2).join('\n').trim(); // The rest is the file content
          console.log('fileContent', fileContent);
          // Update the file content using the handleFileChange function
          handleFileChange(filePath, fileContent); // Update the file content
          }
        }

      } catch (error) {
        // Log any errors that occur during message parsing
        console.error('Error parsing message:', error);
      }
    };

    // Listen for new messages from the socket
    socket?.on('new_message', handleNewMessage);
    return () => {
      // Clean up the listener on component unmount
      socket?.off('new_message', handleNewMessage);
    };
  }, [updateFileSystemFromList]);

  // Function to handle actions from agents
  const handleAgentAction = (messageData: any) => {
    // Check if messageData.data is defined
    if (!messageData.data) {
      console.error('messageData.data is undefined:', messageData);
      return; // Exit if data is not present
    }

    const actionType = messageData.data.action_type; // Get the action type from the message
    const agentName = messageData.data.agent_name; // Get the agent's name

    console.log('Processing agent action:', actionType, 'from', agentName);

    switch (actionType) {
      case "speak":
        // Handle agent speaking
        const newMessage = {
          text: `${agentName}: ${messageData.data.argument}`,
          type: 'message' as const
        };
        // Update messages state with the new message
        setMessages(prev => [...prev, newMessage]);
        break;

      case "thought":
        // Handle agent's thoughts
        setMessages(prev => [...prev, {
          text: `💭 ${agentName} is thinking: ${messageData.data.argument}`,
          type: 'status' as const
        }]);
        break;

      case "write":
        // Handle file writing
        const filePath = messageData.data.path; // Get the file path
        const fileContent = messageData.data.argument; // Get the file content

        // Check if file already exists in openFiles
        const existingFileIndex = openFiles.findIndex(f => f.path === filePath);

        if (existingFileIndex !== -1) {
          // Update existing file content
          handleFileChange(filePath, fileContent);
        } else {
          // Add new file
          addFile(filePath, fileContent);
        }

        // Set the active file and update the UI
        setActiveFile(filePath);
        setActiveTab('editor');
        setActivePanel('fileSystem');
        setMessages(prev => [...prev, {
          text: `${agentName} is writing code...`,
          type: 'status' as const
        }]);
        break;

        case "read":
          // Check if messageData.data.text is defined
            setMessages(prev => [...prev, {
              text: `${agentName} is reading file ${messageData.data.path}`,
              type: 'status' as const
            }]);
          break;

      case "run":
        // Check if messageData.data.text is defined
          // Handle command execution
          setTerminalMessages(prev => [...prev, `$ ${messageData.data.argument}`]);
          setMessages(prev => [...prev, {
            text: `${agentName} is executing a command...`,
            type: 'status' as const
          }]);
        break;

      case "browse":
        // Handle browsing action
        const url = messageData.data.argument; // Get the URL to browse
        setBrowserUrl(url);
        setActiveTab('browser');
        setMessages(prev => [...prev, {
          text: `${agentName} is browsing ${url}`,
          type: 'status' as const
        }]);
        break;

      default:
        // Log unknown action types for debugging
        console.log('Unknown action type:', actionType);
    }
  };

  // Listen for chat messages from the socket
  socket?.on('chat_message', (message: string) => {
    // Update messages state with the new chat message
    setMessages(prev => [...prev, {
      text: message,
      type: 'message' as const
    }]);
  });

  return (
    <div className="flex h-screen w-full">
      <div className="w-64 border-r">
        {/* <SidebarTrigger onClick={() => setActivePanel('fileSystem')}>
          File System
        </SidebarTrigger>
        <SidebarTrigger onClick={() => setActivePanel('sceneContext')}>
          Scene Context
        </SidebarTrigger> */}
        {activePanel === 'fileSystem' ? (
          <FileSystem
            fileSystem={fileSystem.tree}
            onFileSelect={handleFileSelect}
            socket={socket}
          />
        ) : (
          <SceneContext messages={sceneMessages} />
        )}
      </div>
      <div className="flex-1 h-screen flex flex-col overflow-hidden">
        <ResizablePanelGroup 
          direction='vertical'
          className="flex-1 overflow-hidden"
        >
          <ResizablePanel 
            defaultSize={75} 
            minSize={30}
            maxSize={90}
            className="overflow-hidden"
          >
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
                <Browser url={browserUrl}/>
              </TabsContent>
            </Tabs>
          </ResizablePanel>
          <ResizableHandle/>
          <ResizablePanel 
            defaultSize={25}
            minSize={15}
            maxSize={45}
            className="overflow-hidden"
          >
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
  );
}