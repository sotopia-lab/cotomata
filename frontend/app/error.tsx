"use client"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: string;
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="max-w-md w-full p-6">
        <Alert variant="destructive">
          <AlertTitle>Initialization Failed</AlertTitle>
          <AlertDescription className="mt-2 space-y-4">
            <p>{error}</p>
            <Button 
              variant="outline" 
              onClick={reset}
              className="w-full"
            >
              Try Again
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    </div>
  );
}