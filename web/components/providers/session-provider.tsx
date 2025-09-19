'use client';

import { createContext, useContext, ReactNode } from 'react';
import { useUser } from '@clerk/nextjs';
import { useIdleTimeout } from '@/hooks/use-idle-timeout';
import { IdleTimeoutModal } from '@/components/session/idle-timeout-modal';

interface SessionContextValue {
  /** Reset the idle timer manually */
  resetIdleTimer: () => void;
  /** Whether user is currently idle */
  isIdle: boolean;
  /** Time remaining until logout (in seconds) */
  timeRemaining: number;
  /** Manually extend the session */
  extendSession: () => void;
  /** Manually logout */
  logout: () => void;
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

interface SessionProviderProps {
  children: ReactNode;
  /** Idle timeout in minutes (default: 30) */
  idleTimeoutMinutes?: number;
  /** Warning time before logout in minutes (default: 5) */
  warningMinutes?: number;
  /** Whether idle timeout is enabled (default: true in production) */
  enabled?: boolean;
}

export function SessionProvider({
  children,
  idleTimeoutMinutes = 30, // 30 minutes idle timeout
  warningMinutes = 5, // 5 minute warning before logout
  enabled = true, // Always enabled for security
}: SessionProviderProps) {
  const { isSignedIn } = useUser();

  const {
    isIdle,
    showWarning,
    timeRemaining,
    resetTimer,
    logout,
    extendSession,
  } = useIdleTimeout({
    timeoutMs: idleTimeoutMinutes * 60 * 1000,
    warningMs: warningMinutes * 60 * 1000,
    enabled: enabled && isSignedIn, // Only enable for signed-in users
  });

  const contextValue: SessionContextValue = {
    resetIdleTimer: resetTimer,
    isIdle,
    timeRemaining,
    extendSession,
    logout,
  };

  return (
    <SessionContext.Provider value={contextValue}>
      {children}
      
      {/* Only show modal for signed-in users */}
      {isSignedIn && (
        <IdleTimeoutModal
          open={showWarning}
          timeRemaining={timeRemaining}
          onExtendSession={extendSession}
          onLogout={logout}
        />
      )}
    </SessionContext.Provider>
  );
}

/**
 * Hook to access session management functions
 * @returns SessionContextValue
 */
export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}

/**
 * Optional hook that safely returns session context or null
 * Use this if SessionProvider might not be available
 */
export function useSessionOptional(): SessionContextValue | null {
  const context = useContext(SessionContext);
  return context || null;
}