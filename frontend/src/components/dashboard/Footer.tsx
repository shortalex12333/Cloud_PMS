"use client";

import { Cloud, CloudOff } from "lucide-react";

interface FooterProps {
  version?: string;
  cloudConnected?: boolean;
}

export function Footer({
  version = "v0.1.0",
  cloudConnected = true,
}: FooterProps) {
  return (
    <footer className="border-t border-border bg-background">
      <div className="container mx-auto flex h-12 items-center justify-between px-4">
        <p className="text-xs text-muted-foreground">CelesteOS {version}</p>
        <div className="flex items-center gap-2">
          {cloudConnected ? (
            <>
              <Cloud className="h-4 w-4 text-risk-low" />
              <span className="text-xs text-muted-foreground">Cloud Connected</span>
            </>
          ) : (
            <>
              <CloudOff className="h-4 w-4 text-risk-critical" />
              <span className="text-xs text-muted-foreground">Offline Mode</span>
            </>
          )}
        </div>
      </div>
    </footer>
  );
}
