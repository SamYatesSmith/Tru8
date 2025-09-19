import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth } from '@clerk/clerk-expo';
import { router } from 'expo-router';

export interface NotificationService {
  initialize: () => Promise<void>;
  requestPermissions: () => Promise<boolean>;
  registerForPushNotifications: () => Promise<string | null>;
  scheduleLocalNotification: (title: string, body: string, data?: any) => Promise<void>;
  getPermissionStatus: () => Promise<Notifications.NotificationPermissionsStatus>;
  isEnabled: () => Promise<boolean>;
}

// Configure notification handler
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

class ExpoNotificationService implements NotificationService {
  private pushToken: string | null = null;
  private isInitialized: boolean = false;

  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Configure notification categories
      await this.setupNotificationCategories();
      
      // Load cached push token
      const cachedToken = await AsyncStorage.getItem('push_token');
      if (cachedToken) {
        this.pushToken = cachedToken;
      }

      this.isInitialized = true;
    } catch (error) {
      console.error('Failed to initialize notification service:', error);
      throw error;
    }
  }

  async requestPermissions(): Promise<boolean> {
    if (!Constants.deviceName) {
      console.warn('Push notifications require a physical device');
      return false;
    }

    try {
      const { status: existingStatus } = await Notifications.getPermissionsAsync();
      let finalStatus = existingStatus;

      if (existingStatus !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }

      if (finalStatus !== 'granted') {
        console.warn('Push notification permissions not granted');
        return false;
      }

      // Configure notification channel for Android
      if (Platform.OS === 'android') {
        await Notifications.setNotificationChannelAsync('default', {
          name: 'Fact-Check Notifications',
          importance: Notifications.AndroidImportance.HIGH,
          vibrationPattern: [0, 250, 250, 250],
          lightColor: '#2C2C54',
          sound: 'default',
          showBadge: true,
          enableVibrate: true,
          enableLights: true,
        });

        await Notifications.setNotificationChannelAsync('check_complete', {
          name: 'Check Complete',
          importance: Notifications.AndroidImportance.HIGH,
          description: 'Notifications when fact-checks are complete',
          vibrationPattern: [0, 250, 250, 250],
          lightColor: '#059669', // verdictSupported color
          sound: 'default',
        });
      }

      return true;
    } catch (error) {
      console.error('Error requesting notification permissions:', error);
      return false;
    }
  }

  async registerForPushNotifications(): Promise<string | null> {
    try {
      if (!await this.requestPermissions()) {
        return null;
      }

      // Get Expo push token
      const tokenData = await Notifications.getExpoPushTokenAsync();

      const token = tokenData.data;
      this.pushToken = token;

      // Cache the token
      await AsyncStorage.setItem('push_token', token);

      return token;
    } catch (error) {
      console.error('Failed to get push token:', error);
      return null;
    }
  }

  async scheduleLocalNotification(
    title: string, 
    body: string, 
    data?: any
  ): Promise<void> {
    try {
      const isEnabled = await this.isEnabled();
      if (!isEnabled) return;

      await Notifications.scheduleNotificationAsync({
        content: {
          title,
          body,
          data: data || {},
          sound: 'default',
          badge: 1,
          categoryIdentifier: data?.category || 'default',
        },
        trigger: null, // Show immediately
      });
    } catch (error) {
      console.error('Failed to schedule notification:', error);
    }
  }

  async getPermissionStatus(): Promise<Notifications.NotificationPermissionsStatus> {
    return await Notifications.getPermissionsAsync();
  }

  async isEnabled(): Promise<boolean> {
    try {
      // Check if notifications are enabled in app settings
      const appSettings = await AsyncStorage.getItem('app_settings');
      if (appSettings) {
        const settings = JSON.parse(appSettings);
        if (settings.notifications === false) {
          return false;
        }
      }

      // Check system permissions
      const { status } = await Notifications.getPermissionsAsync();
      return status === 'granted';
    } catch (error) {
      console.error('Error checking notification status:', error);
      return false;
    }
  }

  private async setupNotificationCategories(): Promise<void> {
    try {
      await Notifications.setNotificationCategoryAsync('check_complete', [
        {
          identifier: 'view_results',
          buttonTitle: 'View Results',
          options: {
            opensAppToForeground: true,
          },
        },
        {
          identifier: 'share_results',
          buttonTitle: 'Share',
          options: {
            opensAppToForeground: false,
          },
        },
      ]);

      await Notifications.setNotificationCategoryAsync('check_failed', [
        {
          identifier: 'retry_check',
          buttonTitle: 'Try Again',
          options: {
            opensAppToForeground: true,
          },
        },
      ]);
    } catch (error) {
      console.error('Failed to setup notification categories:', error);
    }
  }

  // Get the current push token
  getPushToken(): string | null {
    return this.pushToken;
  }
}

// Singleton instance
export const notificationService = new ExpoNotificationService();

// Hook for using notification service in components
export function useNotifications() {
  const { getToken, userId } = useAuth();

  const initializeNotifications = async () => {
    await notificationService.initialize();
  };

  const registerDevice = async () => {
    try {
      const pushToken = await notificationService.registerForPushNotifications();
      
      if (pushToken && userId) {
        // Send token to backend
        const token = await getToken();
        if (token) {
          await registerPushToken(pushToken, token);
        }
      }

      return pushToken;
    } catch (error) {
      console.error('Failed to register device:', error);
      return null;
    }
  };

  const scheduleNotification = async (title: string, body: string, data?: any) => {
    await notificationService.scheduleLocalNotification(title, body, data);
  };

  const checkPermissions = async () => {
    return await notificationService.getPermissionStatus();
  };

  const isNotificationEnabled = async () => {
    return await notificationService.isEnabled();
  };

  return {
    initializeNotifications,
    registerDevice,
    scheduleNotification,
    checkPermissions,
    isNotificationEnabled,
    pushToken: notificationService.getPushToken(),
  };
}

// API call to register push token with backend
async function registerPushToken(pushToken: string, authToken: string): Promise<void> {
  try {
    const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';
    
    const response = await fetch(`${API_URL}/api/v1/users/push-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        push_token: pushToken,
        platform: Platform.OS,
        device_id: Constants.sessionId || 'unknown',
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to register push token: ${response.status}`);
    }

    console.log('Push token registered successfully');
  } catch (error) {
    console.error('Failed to register push token:', error);
    // Don't throw - this shouldn't break the app
  }
}

// Notification event handlers
export const setupNotificationHandlers = () => {
  // Handle notification received while app is foregrounded
  const notificationListener = Notifications.addNotificationReceivedListener(notification => {
    console.log('Notification received:', notification);
  });

  // Handle notification tapped
  const responseListener = Notifications.addNotificationResponseReceivedListener(response => {
    const { notification, actionIdentifier } = response;
    const data = notification.request.content.data;

    console.log('Notification response:', { actionIdentifier, data });

    // Handle different action identifiers
    switch (actionIdentifier) {
      case 'view_results':
        if (data.checkId) {
          // Navigate to check results
          router.push(`/check/${data.checkId}`);
        }
        break;
      case 'share_results':
        if (data.checkId) {
          // Navigate to check and trigger share
          router.push({
            pathname: "/check/[id]", params: { id: data.checkId },
            params: { action: 'share' }
          });
        }
        break;
      case 'retry_check':
        if (data.checkId) {
          // Navigate to home to retry
          router.push('/');
        }
        break;
      default:
        // Default tap action
        if (data.checkId) {
          router.push(`/check/${data.checkId}`);
        } else {
          // Navigate to home if no specific check
          router.push('/');
        }
        break;
    }
  });

  return () => {
    Notifications.removeNotificationSubscription(notificationListener);
    Notifications.removeNotificationSubscription(responseListener);
  };
};