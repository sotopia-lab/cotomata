import React, { useState } from 'react';
import { Socket } from 'socket.io-client';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  ChevronRight,
  ChevronDown,
  File,
  FolderClosed,
  FolderOpen,
  RefreshCw,
  Plus,
  Check,
  X
} from 'lucide-react';
import { cn } from "@/lib/utils";
import { FileNode } from '@/types/FileSystem';
import { TooltipProvider } from '@radix-ui/react-tooltip';

interface FileSystemProps {
  fileSystem: FileNode[];
  onFileSelect: (path: string) => void;
  socket: Socket | null;
}

// Utility function to get appropriate icon and color for file types
const getFileIcon = (fileName: string) => {
  const ext = fileName.split('.').pop()?.toLowerCase();
  const baseClasses = "h-4 w-4";
  
  let iconColor = "text-muted-foreground";
  switch (ext) {
    case 'html': iconColor = "text-orange-400"; break;
    case 'css': iconColor = "text-blue-400"; break;
    case 'js': iconColor = "text-yellow-400"; break;
    case 'ts': 
    case 'tsx': iconColor = "text-blue-600"; break;
    case 'py': iconColor = "text-green-400"; break;
    case 'json': iconColor = "text-yellow-300"; break;
    case 'md': iconColor = "text-purple-400"; break;
  }

  return <File className={cn(baseClasses, iconColor)} />;
};

// Sort function for file system nodes
const sortNodes = (a: FileNode, b: FileNode): number => {
  // Folders come before files
  if (a.type !== b.type) {
    return a.type === 'folder' ? -1 : 1;
  }
  // Alphabetical sort within same type
  return a.name.localeCompare(b.name);
};

export const FileSystem = ({ fileSystem, onFileSelect, socket }: FileSystemProps) => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['/workspace']));
  const [newFileName, setNewFileName] = useState('');
  const [isInputVisible, setInputVisible] = useState(false);
  const [contextMenuState, setContextMenuState] = useState<{
    visible: boolean;
    x: number;
    y: number;
    node: FileNode | null;
  }>({
    visible: false,
    x: 0,
    y: 0,
    node: null,
  });

  const handleRefresh = () => {
    socket && socket.emit('terminal_command', "echo '**FILE_SYSTEM_REFRESH**' && find -L /workspace -type f");
  };

  const toggleFolder = (folderName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedFolders(prev => {
      const next = new Set(prev);
      if (next.has(folderName)) {
        next.delete(folderName);
      } else {
        next.add(folderName);
      }
      return next;
    });
  };

  const handleFileDoubleClick = (path: string) => {
    socket && socket.emit('terminal_command', `echo '**FILE_CONTENT**' && echo '${path}' && cat ${path}`);
  };

  const handleAddFile = () => {
    if (newFileName) {
      socket && socket.emit('terminal_command', `touch /workspace/${newFileName}`);
      handleRefresh();
      setNewFileName('');
      setInputVisible(false);
    }
  };

  const handleContextMenu = (e: React.MouseEvent, node: FileNode) => {
    e.preventDefault();
    setContextMenuState({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      node,
    });
  };

  const handleDeleteFile = (path: string) => {
    socket && socket.emit('terminal_command', `rm "${path}"`);
    handleRefresh();
    setContextMenuState({ visible: false, x: 0, y: 0, node: null });
  };

  const renderContextMenu = () => {
    if (!contextMenuState.visible || !contextMenuState.node) return null;

    return (
      <div
        className="fixed z-50 min-w-[160px] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md"
        style={{ top: contextMenuState.y, left: contextMenuState.x }}
      >
        <div className="flex flex-col">
          {contextMenuState.node.type === 'file' && (
            <Button
              variant="ghost"
              className="justify-start px-3 py-2 text-sm hover:bg-accent"
              onClick={() => handleDeleteFile(contextMenuState.node!.path)}
            >
              Delete
            </Button>
          )}
        </div>
      </div>
    );
  };

  const renderItem = (item: FileNode, depth: number = 0) => {
    const isExpanded = item.type === 'folder' && expandedFolders.has(item.path);
    const paddingLeft = depth * 16;

    return (
      <div key={item.path}>
        <Button
          variant="ghost"
          className={cn(
            "group w-full justify-start gap-2 rounded-none px-2 py-1.5 hover:bg-accent",
            item.type === 'file' ? "pl-8" : ""
          )}
          style={{ paddingLeft: `${paddingLeft}px` }}
          onClick={() => item.type === 'file' && onFileSelect(item.path)}
          onDoubleClick={() => item.type === 'file' && handleFileDoubleClick(item.path)}
          onContextMenu={(e) => handleContextMenu(e, item)}
        >
          {item.type === 'folder' && (
            <span
              className="flex items-center"
              onClick={(e) => toggleFolder(item.path, e)}
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
              {isExpanded ? (
                <FolderOpen className="h-4 w-4 text-yellow-400" />
              ) : (
                <FolderClosed className="h-4 w-4 text-yellow-400" />
              )}
            </span>
          )}
          {item.type === 'file' && getFileIcon(item.name)}
          <span className="truncate text-sm">{item.name}</span>
        </Button>
        
        {item.type === 'folder' && isExpanded && item.children && (
          <div className="flex flex-col">
            {item.children.sort(sortNodes).map((child) =>
              renderItem(child, depth + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  // Close context menu when clicking outside
  React.useEffect(() => {
    const handleClickOutside = () => {
      setContextMenuState({ visible: false, x: 0, y: 0, node: null });
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  return (
    <Card className="h-full rounded-none border-none bg-background">
      <CardHeader className="border-b px-4 py-2 space-y-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Files</CardTitle>
          <div className="flex gap-1">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setInputVisible(true)}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>New File</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={handleRefresh}
                  >
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Refresh</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {isInputVisible && (
          <div className="border-b p-2">
            <div className="flex gap-1">
              <Input
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                placeholder="File name"
                className="h-8"
                autoFocus
              />
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0"
                onClick={handleAddFile}
              >
                <Check className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0"
                onClick={() => setInputVisible(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        <ScrollArea className="h-[calc(100vh-6rem)]">
          <div className="flex flex-col py-2">
            {fileSystem.sort(sortNodes).map((node) => renderItem(node))}
          </div>
        </ScrollArea>

        {/* Render context menu */}
        {renderContextMenu()}
      </CardContent>
    </Card>
  );
};