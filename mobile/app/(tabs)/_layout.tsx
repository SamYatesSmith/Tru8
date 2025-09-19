import { useEffect } from 'react';
import { Tabs } from 'expo-router';
import { Home, History, User } from 'lucide-react-native';
import { Colors } from '@/lib/design-system';
import { useAuth } from '@clerk/clerk-expo';
import { useNotifications } from '@/services/notifications';

export default function TabsLayout() {
  const { isSignedIn, userId } = useAuth();
  const { initializeNotifications, registerDevice } = useNotifications();

  // Initialize notifications when user is signed in
  useEffect(() => {
    if (isSignedIn && userId) {
      const setupNotifications = async () => {
        try {
          await initializeNotifications();
          await registerDevice();
        } catch (error) {
          console.error('Failed to setup notifications:', error);
        }
      };
      
      setupNotifications();
    }
  }, [isSignedIn, userId]); // Remove function deps to prevent infinite loops

  return (
    <Tabs
      screenOptions={{
        tabBarStyle: {
          backgroundColor: Colors.deepPurpleGrey,
          borderTopColor: Colors.coolGrey,
          borderTopWidth: 1,
        },
        tabBarActiveTintColor: Colors.lightGrey,
        tabBarInactiveTintColor: Colors.coolGrey,
        headerStyle: {
          backgroundColor: Colors.darkIndigo,
        },
        headerTintColor: Colors.lightGrey,
        headerTitleStyle: {
          fontWeight: '600',
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Fact Check',
          headerTitle: 'Tru8',
          tabBarIcon: ({ color, size }) => <Home size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: 'History',
          tabBarIcon: ({ color, size }) => <History size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="account"
        options={{
          title: 'Account',
          tabBarIcon: ({ color, size }) => <User size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="check"
        options={{
          href: null, // Hide from tab bar - this is for navigation only
        }}
      />
      <Tabs.Screen
        name="subscription"
        options={{
          href: null, // Hide from tab bar - this is for navigation only
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          href: null, // Hide from tab bar - this is for navigation only
        }}
      />
      <Tabs.Screen
        name="progress"
        options={{
          href: null, // Hide from tab bar - this is for navigation only
        }}
      />
    </Tabs>
  );
}