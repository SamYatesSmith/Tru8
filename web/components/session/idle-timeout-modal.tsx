'use client';

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { AlertTriangle, LogOut, RefreshCw } from "lucide-react";

interface IdleTimeoutModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Time remaining until logout (in seconds) */
  timeRemaining: number;
  /** Callback to extend the session */
  onExtendSession: () => void;
  /** Callback to logout immediately */
  onLogout: () => void;
}

export function IdleTimeoutModal({
  open,
  timeRemaining,
  onExtendSession,
  onLogout,
}: IdleTimeoutModalProps) {
  const minutes = Math.floor(timeRemaining / 60);
  const seconds = timeRemaining % 60;
  
  const formatTime = () => {
    if (minutes > 0) {
      return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${seconds}`;
  };

  const getTimeColor = () => {
    if (timeRemaining <= 60) return "text-red-600 font-bold"; // Last minute - red
    if (timeRemaining <= 120) return "text-orange-600 font-semibold"; // Last 2 minutes - orange
    return "text-amber-600"; // Default - amber
  };

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent
        className="sm:max-w-[425px] [&>button]:hidden"
        onInteractOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Session Timeout Warning
          </DialogTitle>
          <DialogDescription className="pt-2">
            You've been inactive for a while. For security reasons, your session will expire automatically.
          </DialogDescription>
        </DialogHeader>

        <div className="py-6">
          <div className="text-center">
            <div className="text-sm text-muted-foreground mb-2">
              Session expires in:
            </div>
            <div className={`text-3xl font-mono tabular-nums ${getTimeColor()}`}>
              {formatTime()}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {minutes > 0 ? "minutes" : "seconds"}
            </div>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button
            variant="outline"
            onClick={onLogout}
            className="flex items-center gap-2"
          >
            <LogOut className="h-4 w-4" />
            Logout Now
          </Button>
          <Button
            onClick={onExtendSession}
            className="flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Stay Logged In
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}