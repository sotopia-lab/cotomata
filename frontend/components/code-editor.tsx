"use client"

import React, { useState } from 'react';
import { Socket } from 'socket.io-client';
import CodeMirror from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { html } from '@codemirror/lang-html';
import { css } from '@codemirror/lang-css';
import { python } from '@codemirror/lang-python';
import { githubDark } from '@uiw/codemirror-theme-github';
import { EditorView } from '@codemirror/view';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, Save, FileCode } from 'lucide-react';
import { cn } from "@/lib/utils";
import { useWebSocket } from "@/hooks/useWebSocket";

interface OpenFile {
  path: string;
  content: string;
}

interface CodeEditorProps {
  openFiles: OpenFile[];
  activeFile?: string;
  onFileClose: (path: string) => void;
  onFileSelect: (path: string) => void;
  onChange: (path: string, content: string) => void;
  socket: WebSocket | null;
  sessionId: string | null;
}

const getFileLanguage = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'js':
      return [javascript({ jsx: true })];
    case 'html':
      return [html()];
    case 'css':
      return [css()];
    case 'py':
      return [python()];
    default:
      return [javascript()];
  }
};

const getFileName = (path: string) => path.split('/').pop() || path;


export const CodeEditor = ({
  openFiles,
  activeFile,
  socket,
  sessionId,
  onFileClose,
  onFileSelect,
  onChange,
}: CodeEditorProps) => {
  const [unsavedChanges, setUnsavedChanges] = useState<{ [key: string]: boolean }>({});
  const activeFileContent = openFiles.find(f => f.path === activeFile)?.content;
  const { saveFile } = useWebSocket();

  const handleSave = async () => {
    try {
      if (activeFile && activeFileContent) {
        await saveFile(activeFile, activeFileContent);
        setUnsavedChanges(prev => ({ ...prev, [activeFile]: false }));
      }
    } catch (error) {
      console.error('Error saving file:', error);
    }
  };

  const handleChange = (value: string) => {
    if (activeFile) {
      onChange(activeFile, value);
      setUnsavedChanges(prev => ({ ...prev, [activeFile]: true }));
    }
  };

  return (
    <Card className="flex h-full w-full flex-col overflow-hidden rounded-none border-none bg-background">
      <CardHeader className="border-b px-0 py-0">
        <div className="flex items-center w-full justify-between">
          <ScrollArea className="flex-1">
            <div className="flex min-w-max gap-1 px-2">
              {openFiles.map((file) => (
                <div
                  key={file.path}
                  className="group relative flex h-9 items-center rounded-none"
                >
                  <Button
                    variant={file.path === activeFile ? "secondary" : "ghost"}
                    className={cn(
                      "h-full w-full justify-start rounded-none border-b-2 px-4",
                      file.path === activeFile
                        ? "border-primary"
                        : "border-transparent"
                    )}
                    onClick={() => onFileSelect(file.path)}
                  >
                    <FileCode className="mr-2 h-4 w-4" />
                    <span className="max-w-[150px] truncate">
                      {unsavedChanges[file.path] ? `• ${getFileName(file.path)}` : getFileName(file.path)}
                    </span>
                  </Button>
                  
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-1 top-1/2 h-6 w-6 -translate-y-1/2 opacity-0 group-hover:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      onFileClose(file.path);
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </ScrollArea>
          
          <div className="flex-none">
            <Button
              variant="ghost"
              size="sm"
              className="h-9 px-3 flex items-center gap-2 min-w-[80px] border-l border-border"
              onClick={handleSave}
            >
              <Save className="h-4 w-4" />
              Save
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden p-0">
        {activeFile && (
          <div className="h-full overflow-auto">
            <CodeMirror
              value={activeFileContent || ''}
              height="100%"
              theme={githubDark}
              extensions={[
                ...getFileLanguage(activeFile),
                EditorView.lineWrapping,
              ]}
              onChange={handleChange}
              className="h-full"
              basicSetup={{
                lineNumbers: true,
                highlightActiveLineGutter: true,
                highlightSpecialChars: true,
                foldGutter: true,
                drawSelection: true,
                dropCursor: true,
                allowMultipleSelections: true,
                indentOnInput: true,
                bracketMatching: true,
                closeBrackets: true,
                autocompletion: true,
                rectangularSelection: true,
                crosshairCursor: true,
                highlightActiveLine: true,
                highlightSelectionMatches: true,
                closeBracketsKeymap: true,
                defaultKeymap: true,
                searchKeymap: true,
                historyKeymap: true,
                foldKeymap: true,
                completionKeymap: true,
                lintKeymap: true
              }}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
};