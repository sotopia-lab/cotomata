import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="max-w-md p-6 text-center space-y-4">
        <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
        <h2 className="text-xl font-semibold">Initializing OpenHands...</h2>
        <p className="text-muted-foreground">
          This may take up to 5 minutes. Please wait while we set up your environment.
        </p>
      </div>
    </div>
  );
}