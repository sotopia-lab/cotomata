"use client"

import React, { useState, useEffect, useRef } from 'react';
import { Socket } from 'socket.io-client';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { MessageCircle, Send } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  text: string;
  type: 'message' | 'status';
  agentName: string;
}

interface ChatInterfaceProps {
  messages: Array<{ text: string; type: 'message' | 'status' }>;
  socket: Socket | null;
  onSendMessage: (text: string) => void;
}

export const ChatInterface = ({ messages, socket, onSendMessage }: ChatInterfaceProps) => {
  const [input, setInput] = useState('');
  const [showIndicator, setShowIndicator] = useState(false);
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
  }, [messages]);

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
      socket && socket.emit('chat_message', input.trim());
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

  return (
    <Card className="flex h-full w-full flex-col overflow-hidden border-none rounded-none bg-background">
      <CardHeader className="border-b px-4 py-3 space-y-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageCircle className="h-4 w-4" />
            <CardTitle className="text-sm font-medium">Chat</CardTitle>
          </div>
          {showIndicator && (
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-[calc(100vh-8rem)] w-full">
          <div className="flex flex-col gap-4 p-4">
            {messages.map((message, index) => {
              const parsedMessage = parseMessage(message);
              
              if (parsedMessage.type === 'status') {
                return (
                  <div key={index} className="text-center text-xs text-muted-foreground italic">
                    {parsedMessage.text}
                  </div>
                );
              }

              const isUser = parsedMessage.agentName === 'user';
              
              return (
                <div
                  key={index}
                  className={cn(
                    "flex gap-3 w-full",
                    isUser ? "flex-row-reverse" : "flex-row"
                  )}
                >
                  <Avatar className="h-8 w-8 flex-shrink-0">
                    <AvatarFallback className={cn(
                      "text-xs",
                      isUser ? "bg-primary text-primary-foreground" : "bg-muted"
                    )}>
                      {parsedMessage.agentName[0].toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  
                  <div className={cn(
                    "flex flex-col gap-1",
                    isUser ? "items-end" : "items-start"
                  )}>
                    <span className="text-xs text-muted-foreground">
                      {parsedMessage.agentName}
                    </span>
                    <div className={cn(
                      "rounded-lg px-4 py-2 max-w-[80%]",
                      isUser ? 
                        "bg-primary text-primary-foreground" : 
                        "bg-muted text-muted-foreground"
                    )}>
                      {parsedMessage.text}
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </CardContent>

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
    </Card>
  );
};