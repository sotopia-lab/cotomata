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

import React, { useEffect, useMemo, useState } from 'react';
import { useFileSystem } from "@/hooks/useFileSystem";
import { FileSystem } from "@/components/file-system";
import { CodeEditor } from '@/components/code-editor';
import { Browser } from '@/components/browser';
import { SceneContext } from '@/components/scene-context';
import { ChatInterface } from '@/components/chat-interface';
import { Terminal } from '@/components/terminal';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { redirect, useParams } from "next/navigation";
import { useRouter } from "next/navigation";
import { AppSidebar } from '@/components/sidebar';
import { useWebSocket } from '@/hooks/useWebSocket';

type PanelOption = 'fileSystem' | 'sceneContext';

export default function App() {
  const router = useRouter();
  const { id: currentId } = useParams();
  const { socket, connected } = useWebSocket();
  
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

  const [activePanel, setActivePanel] = useState<PanelOption>('fileSystem');
  const [activeTab, setActiveTab] = useState<'editor' | 'browser'>('editor');
  const [browserUrl, setBrowserUrl] = useState('https://example.com');
  const [messages, setMessages] = useState<Record<string, { text: string, type: 'message' | 'status' }[]>>({});
  const [terminalMessages, setTerminalMessages] = useState<string[]>([]);
  const [sceneMessages, setSceneMessages] = useState<Record<string, Array<{ text: string, agentName: string }>>>({});
  const [sessionId, setSessionId] = useState<string | null>(null);
  

  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedSessionId = localStorage.getItem("cotomata-sessionId");
      if (storedSessionId) {
        setSessionId(storedSessionId);
      }
    }
  }, []);

  // Memoize session logic to avoid multiple checks
  useMemo(() => {
    if (!connected || (sessionId && sessionId !== currentId)) {
      router.push("/");
    }
  }, [connected, sessionId, currentId, router]);

  useEffect(() => {
    if (sessionId) {
      router.push(`/workspace/${sessionId}`); // Keep user on the same page if sessionId exists
    }
  }, [sessionId, router]);

  useEffect(() => {
    // Function to handle new messages received from the socket
    const handleNewMessage = (event: MessageEvent) => {
      try {
        // Parse the incoming message data
        const parsedData = JSON.parse(event.data);
        console.log("Received data:", parsedData);

        if (!parsedData.message) {
          console.error("Missing 'message' field in received data.");
          return;
        }
    
        // Parse the inner JSON string (since it's a nested JSON string)
        const messageData = JSON.parse(parsedData.message);

        // Check if messageData.data is defined
        if (!messageData.data) {
          console.error('messageData.data is undefined:', messageData);
          return; // Exit if data is not present
        }

        // Handle Scene context messages
        if (parsedData.channel && parsedData.channel.startsWith('Scene:') && parsedData.channel.endsWith(`:${sessionId}`)) {
          if (messageData.data.data_type === "text") {
            setSceneMessages(prev => ({
              ...prev,
              [sessionId!]: [
                ...(prev[sessionId!] || []),
                { 
                  text: messageData.data.text, 
                  agentName: parsedData.channel.split(':')[1] 
                }
              ]
            }));
            // setActivePanel('sceneContext');
          }
          return;
        }

        // Check if it's an agent action
        if (messageData.data.data_type === "agent_action") {
          console.log("here1");
          handleAgentAction(messageData, sessionId!);
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
          console.log('parts', parts);
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
    socket?.addEventListener('message', handleNewMessage);
    return () => {
      // Clean up the listener on component unmount
      socket?.removeEventListener('message', handleNewMessage);
    };
  }, [updateFileSystemFromList]);

  // Function to handle actions from agents
  const handleAgentAction = (messageData: any, currentSessionId: string) => {
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
        setMessages(prev => ({
          ...prev,
          [currentSessionId]: [
            ...(prev[currentSessionId] || []),
            newMessage,
          ],
        }));
        break;

      case "thought":
        setMessages(prev => ({
          ...prev,
          [currentSessionId]: [
            ...(prev[currentSessionId] || []),
            {
              text: `💭 ${agentName} is thinking: ${messageData.data.argument}`,
              type: 'status' as const,
            },
          ],
        }));
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
        setMessages(prev => ({
          ...prev,
          [currentSessionId]: [
            ...(prev[currentSessionId] || []),
            {
              text: `${agentName} is writing code...`,
              type: 'status' as const,
            },
          ],
        }));
        break;

        case "read":
          // Check if messageData.data.text is defined
          setMessages(prev => ({
            ...prev,
            [currentSessionId]: [
              ...(prev[currentSessionId] || []),
              {
                text: `${agentName} is reading file ${messageData.data.path}`,
                type: 'status' as const,
              },
            ],
          }));
          break;

      case "run":
        // Check if messageData.data.text is defined
          // Handle command execution
          setTerminalMessages(prev => [...prev, `$ ${messageData.data.argument}`]);
          setMessages(prev => ({
            ...prev,
            [currentSessionId]: [
              ...(prev[currentSessionId] || []),
              {
                text: `${agentName} is executing a command...`,
                type: 'status' as const,
              },
            ],
          }));
        break;

      case "browse":
        // Handle browsing action
        const url = messageData.data.argument; // Get the URL to browse
        setBrowserUrl(url);
        setActiveTab('browser');
        setMessages(prev => ({
          ...prev,
          [currentSessionId]: [
            ...(prev[currentSessionId] || []),
            { text: `${agentName} is browsing ${url}`, type: 'status' as const },
          ],
        }));
        break;

      default:
        // Log unknown action types for debugging
        console.log('Unknown action type:', actionType);
    }
  };


  // Listen for chat messages from the socket
  socket?.addEventListener("message", (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data); // Parse the incoming JSON message
  
      if (data.type === "chat_message") { // Check if it's a chat message
        setMessages(prev => ({
          ...prev,
          [data.sessionId]: [
            ...(prev[data.sessionId] || []),
            {
              text: data.message,
              type: "message" as const,
            },
          ],
        }));
      }
    } catch (error) {
      console.error("Error parsing WebSocket message:", error);
    }
  });

  return (
    <div className="flex h-screen w-full">
      <AppSidebar socket={socket} sessionId={sessionId} />
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
            sessionId={sessionId}
          />
        ) : (
          <SceneContext messages={sceneMessages[sessionId!]} />
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
                  sessionId={sessionId}
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
            <Terminal externalMessages={terminalMessages} socket={socket} sessionId={sessionId}/>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
      <div className="w-80 border-l">
        <ChatInterface
          messages={messages[sessionId!] || []}
          sceneMessages={sceneMessages[sessionId!] || []}
          socket={socket}
          sessionId={sessionId}
          onSendMessage={(text: string) => {
            // Update messages state with the user's message
            setMessages(prev => ({
              ...prev,
              [sessionId!]: [
                ...(prev[sessionId!] || []), // Get existing messages for the session
                {
                  text: `User: ${text}`,
                  type: 'message' as const,
                }
              ]
            }));
          }}
        />
      </div>
    </div>
  );
}