"use client";

import { useContext, useEffect } from "react";
import { WebSocketContext } from "../context/loading-provider";

export function useWebSocket() {
    const context = useContext(WebSocketContext);
    if (context === undefined) {
      throw new Error('useWebSocket must be used within a WebSocketProvider');
    }
    
    return context;
  }