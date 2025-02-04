"use client"

import React, { useState, useEffect, useRef } from 'react';
import { Socket } from 'socket.io-client';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { MessageCircle, Send } from "lucide-react";
import { cn } from "@/lib/utils";


interface Message {
  text: string;
  type: 'message' | 'status';
  agentName: string;
}

interface ChatInterfaceProps {
  messages: Array<{ text: string; type: 'message' | 'status' }>;
  sceneMessages: Array<{ text: string; agentName: string }>;
  socket: Socket | null;
  sessionId: string | null;
  onSendMessage: (text: string) => void;
}

export const ChatInterface = ({ messages, sceneMessages, socket, sessionId, onSendMessage }: ChatInterfaceProps) => {
  const [input, setInput] = useState('');
  const [showIndicator, setShowIndicator] = useState(false);
  const [ agentStatus, setAgentStatus ] = useState(false);
  const [activeTab, setActiveTab] = useState<'chat' | 'agent'>('chat');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll effect when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    if (messages.length > 0) {
      setShowIndicator(true);
      const timer = setTimeout(() => setShowIndicator(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [messages, sceneMessages]);

  // Parse message to extract agent name and content
  const parseMessage = (message: { text: string, type: 'message' | 'status' }): Message => {
    if (message.type === 'status') {
      return {
        agentName: '',
        text: message.text,
        type: 'status'
      };
    }

    const colonIndex = message.text.indexOf(':');
    if (colonIndex === -1) {
      return {
        agentName: 'System',
        text: message.text,
        type: 'message'
      };
    }

    return {
      agentName: message.text.slice(0, colonIndex),
      text: message.text.slice(colonIndex + 1).trim(),
      type: 'message'
    };
  };

  const handleSend = () => {
    if (input.trim()) {
      socket && socket.emit('chat_message', { sessionId: sessionId, message: input.trim() });
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = '40px';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startAgentConversation = () => {
    console.log('Join Agent Session', sessionId);
    socket && socket.emit('init_agent_conversation', { sessionId: sessionId }, (response: any) => {
      console.log("here", response);
      if (response.success) {
        setAgentStatus(true);
      }
    });
  };

  const renderMessages = (messageList: Array<Message>, isScene: boolean = false) => {
    // const allMessages = [
    //   ...sceneMessages.map(msg => ({
    //     text: msg.text,
    //     agentName: msg.agentName,
    //     type: 'message' as const,
    //     isScene: true,
    //     timestamp: Date.now()
    //   })),
    //   ...messages.map(msg => ({
    //     ...parseMessage(msg),
    //     isScene: false
    //   })),
      
    // ];
    // console.log(allMessages);

    // Sort messages by timestamp if needed
    // allMessages.sort((a, b) => a.timestamp - b.timestamp);

    return messageList.map((message, index) => {
      if (message.type === 'status') {
        return (
          <div key={index} className="text-center text-xs text-muted-foreground italic">
            {message.text}
          </div>
        );
      }

      const isUser = message.agentName === 'user' || message.agentName === 'User';
      // const isScene = message.isScene;
      
      return (
        <div
          key={index}
          className={cn(
            "flex gap-3 w-full",
            isUser ? "flex-row-reverse" : "flex-row"
          )}
        >
          <Avatar className="h-6 w-6 flex-shrink-0">
            <AvatarFallback className={cn(
              "text-xs",
              isUser ? "bg-primary text-primary-foreground" : 
              isScene ? "bg-green-100 text-green-800" : "bg-muted"
            )}>
              {message.agentName[0].toUpperCase()}
            </AvatarFallback>
          </Avatar>
          
          <div className={cn(
            "flex flex-col gap-1",
            isUser ? "items-end" : "items-start"
          )}>
            <span className="text-xs text-muted-foreground">
              {message.agentName}
              {isScene && " (Scene)"}
            </span>
            <div 
              className={cn(
                "rounded-lg px-3 py-2 text-sm max-w-[75%] text-left",
                isUser ? "bg-primary text-primary-foreground" : 
                isScene ? "bg-green-100 text-green-800" : "bg-muted text-muted-foreground"
              )}
            >
              {message.text}
            </div>
          </div>
        </div>
      );
    });
  };

  return (
    // <Card className="flex h-full w-full flex-col overflow-hidden border-none rounded-none bg-background">
    //   <CardHeader className="border-b px-4 py-3 space-y-0">
    //     <div className="flex items-center justify-between">
    //       <div className="flex items-center gap-2">
    //         <MessageCircle className="h-4 w-4" />
    //         <CardTitle className="text-sm font-medium">Chat</CardTitle>
    //         {showIndicator && (
    //           <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
    //         )}
    //       </div>
    //       {!agentStatus && 
    //         <Button onClick={() => startAgentConversation()}>
    //           Start
    //         </Button>
    //       }
    //     </div>
    //   </CardHeader>

    //   <CardContent className="flex-1 p-0">
    //     <ScrollArea className="h-[calc(100vh-8rem)] w-full">
    //       <div className="flex flex-col gap-4 p-4">
    //         {renderMessages()}
    //         <div ref={messagesEndRef} />
    //       </div>
    //     </ScrollArea>
    //   </CardContent>

    //   <div className="border-t p-4">
    //     <div className="flex gap-2">
    //       <Textarea
    //         ref={textareaRef}
    //         value={input}
    //         onChange={(e) => {
    //           setInput(e.target.value);
    //           e.target.style.height = 'auto';
    //           e.target.style.height = `${e.target.scrollHeight}px`;
    //         }}
    //         onKeyDown={handleKeyDown}
    //         placeholder="Type a message..."
    //         className="min-h-[40px] max-h-[160px] resize-none"
    //         rows={1}
    //       />
    //       <Button
    //         onClick={handleSend}
    //         size="icon"
    //         className="h-10 w-10 shrink-0"
    //       >
    //         <Send className="h-4 w-4" />
    //       </Button>
    //     </div>
    //   </div>
    // </Card>
    <Tabs defaultValue="chat" className="flex h-full w-full flex-col overflow-hidden border-none rounded-none bg-background">
      <TabsList>
        <TabsTrigger value="chat">
          <div className="flex items-center gap-2">
            Chat
            {showIndicator && (
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            )}
          </div>
          </TabsTrigger>
        <TabsTrigger value="agent">Agent</TabsTrigger>
      </TabsList>
      <TabsContent value="chat">
        <ScrollArea className="h-[calc(100vh-8rem)] w-full">
            <div className="flex flex-col gap-4 p-4">
              {renderMessages(messages.map((msg) => parseMessage(msg)))}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </TabsContent>
      <TabsContent value="agent">
        <div className="h-[calc(100vh-8rem)] w-full">
          {!agentStatus ? (
            <div className="flex h-full items-center justify-center">
              <Button onClick={() => startAgentConversation()} size="lg">
                Start
              </Button>
            </div>
          ) : (
            <ScrollArea className="h-full w-full">
              <div className="flex flex-col gap-4 p-4">
                {renderMessages(
                  sceneMessages.map((msg) => ({
                    text: msg.text,
                    agentName: msg.agentName,
                    type: "message",
                  })),
                  true
                )}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>
          )}
        </div>
      </TabsContent>

      <div className="border-t p-4">
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = `${e.target.scrollHeight}px`;
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            className="min-h-[40px] max-h-[160px] resize-none"
            rows={1}
          />
          <Button
            onClick={handleSend}
            size="icon"
            className="h-10 w-10 shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Tabs>
  );
};