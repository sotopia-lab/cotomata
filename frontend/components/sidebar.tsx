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
import { Cog, FolderOpen } from 'lucide-react'; // Import the file icon

// Define the props for the Sidebar component
interface SidebarProps {
    onSelect: (option: 'fileSystem' | 'sceneContext') => void; // Callback for selecting a panel
}

// // Main Sidebar component definition
// export const Sidebar: React.FC<SidebarProps> = ({ onSelect }) => {
//   return (
//     <div className="sidebar">
//       {/* Button to select the file system panel */}
//       <button className="sidebar-button" onClick={() => onSelect('fileSystem')}>
//         <FolderOpen size={24} /> {/* Icon for file system */}
//       </button>
//       {/* Button to select the scene context panel */}
//       <button className="sidebar-button" onClick={() => onSelect('sceneContext')}>
//         <Cog size={24} /> {/* Icon for scene context */}
//       </button>
//       {/* Add more icons as needed */}
//     </div>
//   );
// };


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
      <SidebarContent>
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
      </SidebarContent>
    </Sidebar>
  )
}
