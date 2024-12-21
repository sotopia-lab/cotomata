// /**
//  * app/page.tsx
//  *
//  * This file serves as the main entry point for the React application. It manages the overall
//  * application state, handles socket connections for real-time communication, and coordinates
//  * interactions between various components such as the code editor, terminal, chat interface,
//  * and file system.
//  *
//  * Key Features:
//  * - Establishes a WebSocket connection to the server for real-time updates.
//  * - Manages application state using React hooks, including messages, terminal output,
//  *   and active panels.
//  * - Handles incoming messages from the server, including agent actions and chat messages.
//  * - Provides a user interface for code editing, browsing, and terminal commands.
//  *
//  * Components Used:
//  * - CodeEditor: For editing code files.
//  * - FileSystem: For displaying and managing files.
//  * - Terminal: For executing commands and displaying output.
//  * - ChatInterface: For user interaction and messaging.
//  * - Browser: For displaying web content.
//  * - Sidebar: For navigation between different application panels.
//  * - SceneContext: For displaying context messages from agents.
//  *
//  */
"use client"

import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { useLoading } from "../context/loading-provider";
import Loading from "./loading";
import Error from "./error";

export default function LandingPage() {
  const router = useRouter();
  const { isReady, error } = useLoading();

  if (error) {
    return <Error error={error} reset={() => router.refresh()} />;
  }

  if (isReady) {
    router.push('/workspace');
    return null;
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      <div className="max-w-2xl text-center space-y-8">
        <h1 className="text-4xl font-bold tracking-tight">Welcome to OpenHands</h1>
        <p className="text-xl text-muted-foreground">
          Initializing your development environment...
        </p>
        <Loading />
      </div>
    </div>
  );
}