// /**
//  * Sidebar.tsx
//  *
//  * This component represents a sidebar navigation interface within the application. It allows
//  * users to switch between different panels, such as the file system and scene context. The
//  * sidebar contains buttons that trigger the selection of these panels.
//  *
//  * Key Features:
//  * - Provides buttons for navigating to the file system and scene context.
//  * - Uses icons to visually represent each option.
//  *
//  * Props:
//  * - onSelect: A callback function that is called when a button is clicked, passing the selected option.
//  *
//  */
"use client"

import React, { useState } from 'react';
import { Cog, FolderOpen, RefreshCcw } from 'lucide-react';
import Link from 'next/link';

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { useRouter } from "next/navigation";
import { Button } from './ui/button';
import { AlertDialog, AlertDialogAction, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog';
import { useWebSocket } from '@/hooks/useWebSocket';

// Menu items.
const items = [
  {
    title: "FileSystem",
    url: "#",
    icon: FolderOpen,
  },
  {
    title: "SceneContext",
    url: "#",
    icon: Cog,
  },
]

interface AppSidebarProps {
  socket: WebSocket | null;
  sessionId: string | null;
}

export function AppSidebar({ socket, sessionId }: AppSidebarProps) {
  const router = useRouter();
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const { killSession } = useWebSocket();

  const handleEndSession = async () => {
    const storedSessionId = localStorage.getItem('cotomata-sessionId');

    if (!sessionId || !storedSessionId || sessionId !== storedSessionId) {
      return;
    }

    try {
      await killSession(sessionId);
      localStorage.removeItem('cotomata-sessionId');
      router.push("/");
    } catch (err) {
      console.error("Failed to end session:", err);
      setErrorMessage('Failed to end session');
      setErrorDialogOpen(true);
    }
  }

  return (
    <>
    <Sidebar>
      <SidebarContent className="flex flex-col h-full">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <a href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        {/* Refresh button at the bottom */}
        <div className="mt-auto mb-4">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton asChild>
                <Button
                  onClick={handleEndSession}
                  className="flex items-center justify-center gap-2 outline-none bg-transparent"
                >
                  <RefreshCcw className='text-white'/>
                </Button>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </div>
      </SidebarContent>
    </Sidebar>

    <AlertDialog open={errorDialogOpen} onOpenChange={setErrorDialogOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Error Ending Session</AlertDialogTitle>
          <AlertDialogDescription>
            {errorMessage}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogAction onClick={() => setErrorDialogOpen(false)}>
            OK
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
    </>
  )
}
