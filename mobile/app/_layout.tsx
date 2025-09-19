import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { ClerkProvider } from '@clerk/clerk-expo';
import * as SecureStore from 'expo-secure-store';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import { View } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';
import { useFonts } from 'expo-font';
import { Colors } from '@/lib/design-system';
import { RevenueCatProvider } from '@/providers/RevenueCatProvider';
import { setupNotificationHandlers } from '@/services/notifications';
import { ErrorProvider } from '@/contexts/ErrorContext';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { ErrorToastContainer } from '@/components/ErrorToast';
import { setupGlobalErrorHandlers, errorReporting } from '@/services/error-reporting';
import '../global.css';

// Prevent splash screen from auto-hiding
SplashScreen.preventAutoHideAsync();

// Token cache for Clerk
const tokenCache = {
  async getToken(key: string) {
    try {
      return await SecureStore.getItemAsync(key);
    } catch (err) {
      console.error('Error getting token from SecureStore:', err);
      return null;
    }
  },
  async saveToken(key: string, value: string) {
    try {
      await SecureStore.setItemAsync(key, value);
    } catch (err) {
      console.error('Error saving token to SecureStore:', err);
    }
  },
  async deleteToken(key: string) {
    try {
      await SecureStore.deleteItemAsync(key);
    } catch (err) {
      console.error('Error deleting token from SecureStore:', err);
    }
  },
};

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 2,
    },
  },
});

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    // Add Inter font if needed, or use system fonts
  });

  useEffect(() => {
    if (fontsLoaded) {
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded]);

  // Setup notification handlers and error reporting
  useEffect(() => {
    const cleanup = setupNotificationHandlers();
    setupGlobalErrorHandlers();
    return cleanup;
  }, []);

  if (!fontsLoaded) {
    return null;
  }

  const clerkPublishableKey = process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY;

  if (!clerkPublishableKey) {
    throw new Error('Missing Clerk Publishable Key. Please set EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY in your .env');
  }

  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        errorReporting.reportCrash(error);
      }}
    >
      <ClerkProvider 
        publishableKey={clerkPublishableKey}
        tokenCache={tokenCache}
      >
        <QueryClientProvider client={queryClient}>
          <RevenueCatProvider>
            <ErrorProvider>
              <View style={{ flex: 1, backgroundColor: Colors.darkIndigo }}>
                <StatusBar style="light" />
                <Stack
                  screenOptions={{
                    headerShown: false,
                    contentStyle: { backgroundColor: Colors.darkIndigo },
                    animation: 'slide_from_right',
                  }}
                >
                  <Stack.Screen 
                    name="(tabs)" 
                    options={{ headerShown: false }} 
                  />
                  <Stack.Screen 
                    name="(auth)" 
                    options={{ 
                      headerShown: false,
                      presentation: 'modal',
                    }} 
                  />
                </Stack>
                <ErrorToastContainer />
              </View>
            </ErrorProvider>
          </RevenueCatProvider>
        </QueryClientProvider>
      </ClerkProvider>
    </ErrorBoundary>
  );
}