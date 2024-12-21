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

import React from 'react';
import { Cog, FolderOpen, Home, RefreshCcw } from 'lucide-react';
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

export function AppSidebar() {
  return (
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
                <Link href="/" className="flex items-center justify-center gap-2">
                  <RefreshCcw />
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </div>
      </SidebarContent>
    </Sidebar>
  )
}
