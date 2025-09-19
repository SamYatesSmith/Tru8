'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';

interface UseIdleTimeoutProps {
  /** Idle timeout in milliseconds (default: 30 minutes) */
  timeoutMs?: number;
  /** Warning time before logout in milliseconds (default: 5 minutes) */
  warningMs?: number;
  /** Callback when user becomes idle */
  onIdle?: () => void;
  /** Callback when warning should be shown */
  onWarning?: () => void;
  /** Whether idle timeout is enabled */
  enabled?: boolean;
}

interface UseIdleTimeoutReturn {
  /** Whether user is currently idle */
  isIdle: boolean;
  /** Whether warning should be shown */
  showWarning: boolean;
  /** Time remaining until logout (in seconds) */
  timeRemaining: number;
  /** Reset the idle timer (user activity) */
  resetTimer: () => void;
  /** Manually trigger logout */
  logout: () => void;
  /** Extend session (dismiss warning) */
  extendSession: () => void;
}

const DEFAULT_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const DEFAULT_WARNING_MS = 5 * 60 * 1000;  // 5 minutes before timeout

export function useIdleTimeout({
  timeoutMs = DEFAULT_TIMEOUT_MS,
  warningMs = DEFAULT_WARNING_MS,
  onIdle,
  onWarning,
  enabled = true
}: UseIdleTimeoutProps = {}): UseIdleTimeoutReturn {
  const { signOut } = useAuth();
  
  const [isIdle, setIsIdle] = useState(false);
  const [showWarning, setShowWarning] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(0);
  
  const timeoutRef = useRef<NodeJS.Timeout>();
  const warningTimeoutRef = useRef<NodeJS.Timeout>();
  const countdownRef = useRef<NodeJS.Timeout>();
  const startTimeRef = useRef<number>(Date.now());

  const cleanup = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = undefined;
    }
    if (warningTimeoutRef.current) {
      clearTimeout(warningTimeoutRef.current);
      warningTimeoutRef.current = undefined;
    }
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = undefined;
    }
  }, []);

  const logout = useCallback(async () => {
    cleanup();
    setIsIdle(true);
    setShowWarning(false);
    
    try {
      await signOut();
      onIdle?.();
    } catch (error) {
      console.error('Failed to sign out:', error);
    }
  }, [signOut, onIdle, cleanup]);

  const startWarningCountdown = useCallback(() => {
    const warningDurationMs = warningMs;
    setTimeRemaining(Math.ceil(warningDurationMs / 1000));
    
    countdownRef.current = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          logout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, [warningMs, logout]);

  const resetTimer = useCallback(() => {
    if (!enabled) return;
    
    cleanup();
    setIsIdle(false);
    setShowWarning(false);
    setTimeRemaining(0);
    startTimeRef.current = Date.now();

    // Set warning timeout
    warningTimeoutRef.current = setTimeout(() => {
      setShowWarning(true);
      startWarningCountdown();
      onWarning?.();
    }, timeoutMs - warningMs);

    // Set logout timeout
    timeoutRef.current = setTimeout(() => {
      logout();
    }, timeoutMs);
  }, [enabled, timeoutMs, warningMs, onWarning, startWarningCountdown, logout, cleanup]);

  const extendSession = useCallback(() => {
    resetTimer();
  }, [resetTimer]);

  // Activity event listeners
  useEffect(() => {
    if (!enabled) return;

    const activityEvents = [
      'mousedown',
      'keydown', 
      'scroll',
      'touchstart',
      'click',
      // Removed 'mousemove' as it's too sensitive and causes spam
    ];

    const handleActivity = () => {
      resetTimer();
    };

    // Add event listeners
    activityEvents.forEach(event => {
      document.addEventListener(event, handleActivity, { passive: true, capture: true });
    });

    // Start initial timer
    resetTimer();

    // Cleanup on unmount or when disabled
    return () => {
      activityEvents.forEach(event => {
        document.removeEventListener(event, handleActivity, true);
      });
      cleanup();
    };
  }, [enabled, resetTimer, cleanup]);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    isIdle,
    showWarning,
    timeRemaining,
    resetTimer,
    logout,
    extendSession,
  };
}