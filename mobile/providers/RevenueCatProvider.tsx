import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { CustomerInfo } from 'react-native-purchases';
import { useAuth, useUser } from '@clerk/clerk-expo';
import RevenueCatService from '@/lib/revenuecat';

interface RevenueCatContextType {
  customerInfo: CustomerInfo | null;
  isLoading: boolean;
  error: string | null;
  refreshCustomerInfo: () => Promise<void>;
  hasActiveSubscription: boolean;
  activeSubscription: string | null;
}

const RevenueCatContext = createContext<RevenueCatContextType | undefined>(undefined);

interface RevenueCatProviderProps {
  children: ReactNode;
}

export function RevenueCatProvider({ children }: RevenueCatProviderProps) {
  const [customerInfo, setCustomerInfo] = useState<CustomerInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { isSignedIn } = useAuth();
  const { user } = useUser();

  const refreshCustomerInfo = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const info = await RevenueCatService.getCustomerInfo();
      setCustomerInfo(info);
    } catch (err: any) {
      console.error('Failed to refresh customer info:', err);
      setError(err.message || 'Failed to load subscription info');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const initializeRevenueCat = async () => {
      try {
        if (isSignedIn && user?.id) {
          // Initialize RevenueCat with user ID
          await RevenueCatService.initialize(user.id);
          await refreshCustomerInfo();
        } else {
          // Initialize without user ID (anonymous)
          await RevenueCatService.initialize();
          setIsLoading(false);
        }
      } catch (err: any) {
        console.error('RevenueCat initialization failed:', err);
        setError(err.message || 'Failed to initialize payments');
        setIsLoading(false);
      }
    };

    initializeRevenueCat();
  }, [isSignedIn, user?.id]);

  // Calculate derived state
  const activeSubscription = customerInfo 
    ? RevenueCatService.getActiveSubscription(customerInfo)
    : null;
    
  const hasActiveSubscription = activeSubscription !== null;

  const contextValue: RevenueCatContextType = {
    customerInfo,
    isLoading,
    error,
    refreshCustomerInfo,
    hasActiveSubscription,
    activeSubscription,
  };

  return (
    <RevenueCatContext.Provider value={contextValue}>
      {children}
    </RevenueCatContext.Provider>
  );
}

export function useRevenueCat(): RevenueCatContextType {
  const context = useContext(RevenueCatContext);
  if (context === undefined) {
    throw new Error('useRevenueCat must be used within a RevenueCatProvider');
  }
  return context;
}