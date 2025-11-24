"use client";

import { Ship, User } from "lucide-react";

interface HeaderProps {
  yachtName?: string;
  userName?: string;
  userRole?: string;
}

export function Header({
  yachtName = "M/Y Celeste",
  userName = "Captain",
  userRole = "HOD",
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Ship className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">CelesteOS</h1>
            <p className="text-xs text-muted-foreground">{yachtName}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-medium">{userName}</p>
            <p className="text-xs text-muted-foreground">{userRole}</p>
          </div>
          <div className="p-2 rounded-full bg-muted">
            <User className="h-5 w-5 text-muted-foreground" />
          </div>
        </div>
      </div>
    </header>
  );
}
