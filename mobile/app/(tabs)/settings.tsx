import { useState, useEffect } from 'react';
import { View, Text, ScrollView, TouchableOpacity, Switch, Alert, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { 
  ArrowLeft, 
  Bell, 
  Shield, 
  Trash2, 
  Info, 
  ExternalLink,
  Moon,
  Globe,
  Database,
  AlertTriangle 
} from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth } from '@clerk/clerk-expo';

interface SettingsState {
  notifications: boolean;
  deepMode: boolean;
  autoCache: boolean;
  analyticsOptOut: boolean;
}

export default function SettingsScreen() {
  const { getToken } = useAuth();
  const [settings, setSettings] = useState<SettingsState>({
    notifications: true,
    deepMode: false,
    autoCache: true,
    analyticsOptOut: false,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const stored = await AsyncStorage.getItem('app_settings');
      if (stored) {
        const parsed = JSON.parse(stored);
        setSettings(prev => ({ ...prev, ...parsed }));
      }
      
      // Also check environment variable for deep mode
      const envDeepMode = process.env.EXPO_PUBLIC_ENABLE_DEEP_MODE === 'true';
      setSettings(prev => ({ ...prev, deepMode: envDeepMode }));
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const syncNotificationPreferences = async (enabled: boolean) => {
    try {
      const token = await getToken();
      if (!token) return;

      const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/v1/users/notification-preferences`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          notifications: enabled,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to sync notification preferences');
      }
    } catch (error) {
      console.error('Failed to sync notification preferences:', error);
      // Don't show error to user as this is a background sync
    }
  };

  const saveSettings = async (newSettings: Partial<SettingsState>) => {
    try {
      const updated = { ...settings, ...newSettings };
      setSettings(updated);
      await AsyncStorage.setItem('app_settings', JSON.stringify(updated));

      // Sync notification preferences with backend
      if ('notifications' in newSettings) {
        await syncNotificationPreferences(newSettings.notifications!);
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      Alert.alert('Error', 'Failed to save settings');
    }
  };

  const handleClearCache = () => {
    Alert.alert(
      'Clear Cache',
      'This will remove all cached fact-check results and temporary data. Are you sure?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            try {
              // Clear specific cache keys (not all AsyncStorage)
              const keysToRemove = [
                'cached_checks',
                'cached_results',
                'offline_queue',
                'temp_files',
              ];
              
              await AsyncStorage.multiRemove(keysToRemove);
              Alert.alert('Success', 'Cache cleared successfully');
            } catch (error) {
              Alert.alert('Error', 'Failed to clear cache');
            }
          }
        }
      ]
    );
  };

  const openURL = async (url: string) => {
    try {
      const canOpen = await Linking.canOpenURL(url);
      if (canOpen) {
        await Linking.openURL(url);
      } else {
        Alert.alert('Error', 'Unable to open link');
      }
    } catch (error) {
      Alert.alert('Error', 'Unable to open link');
    }
  };

  const SettingRow = ({ 
    icon: Icon, 
    title, 
    description, 
    value, 
    onToggle, 
    onPress, 
    showArrow = false,
    destructive = false 
  }: {
    icon: any;
    title: string;
    description?: string;
    value?: boolean;
    onToggle?: (value: boolean) => void;
    onPress?: () => void;
    showArrow?: boolean;
    destructive?: boolean;
  }) => (
    <TouchableOpacity
      onPress={onPress}
      disabled={!onPress && !onToggle}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        padding: Spacing.space4,
        borderBottomWidth: 1,
        borderBottomColor: Colors.coolGrey + '20',
      }}
    >
      <Icon 
        size={20} 
        color={destructive ? Colors.verdictContradicted : Colors.lightGrey} 
        style={{ marginRight: Spacing.space3 }} 
      />
      
      <View style={{ flex: 1 }}>
        <Text style={{
          color: destructive ? Colors.verdictContradicted : Colors.lightGrey,
          fontSize: Typography.textBase,
          fontWeight: Typography.fontWeightMedium,
          marginBottom: description ? Spacing.space1 : 0,
        }}>
          {title}
        </Text>
        {description && (
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textSm,
            lineHeight: Typography.textSm * 1.3,
          }}>
            {description}
          </Text>
        )}
      </View>

      {onToggle && value !== undefined && (
        <Switch
          value={value}
          onValueChange={onToggle}
          trackColor={{ false: Colors.coolGrey + '40', true: Colors.verdictSupported + '60' }}
          thumbColor={value ? Colors.verdictSupported : Colors.coolGrey}
          ios_backgroundColor={Colors.coolGrey + '40'}
        />
      )}

      {showArrow && (
        <ExternalLink size={16} color={Colors.coolGrey} />
      )}
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.darkIndigo }}>
        <View style={{ 
          flex: 1, 
          justifyContent: 'center', 
          alignItems: 'center' 
        }}>
          <Text style={{
            color: Colors.lightGrey,
            fontSize: Typography.textLg,
          }}>
            Loading settings...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.darkIndigo }}>
      {/* Header */}
      <View style={{
        flexDirection: 'row',
        alignItems: 'center',
        padding: Spacing.space4,
        borderBottomWidth: 1,
        borderBottomColor: Colors.deepPurpleGrey,
      }}>
        <TouchableOpacity 
          onPress={() => router.back()}
          style={{ marginRight: Spacing.space4 }}
        >
          <ArrowLeft size={24} color={Colors.lightGrey} />
        </TouchableOpacity>
        <Text style={{
          flex: 1,
          color: Colors.lightGrey,
          fontSize: Typography.textLg,
          fontWeight: Typography.fontWeightSemibold,
        }}>
          Settings
        </Text>
      </View>

      <ScrollView style={{ flex: 1 }}>
        {/* Preferences Section */}
        <View style={{
          backgroundColor: Colors.deepPurpleGrey,
          marginTop: Spacing.space4,
          marginHorizontal: Spacing.space4,
          borderRadius: BorderRadius.radiusLg,
          overflow: 'hidden',
        }}>
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textSm,
            fontWeight: Typography.fontWeightMedium,
            padding: Spacing.space4,
            paddingBottom: Spacing.space2,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
          }}>
            Preferences
          </Text>

          <SettingRow
            icon={Bell}
            title="Push Notifications"
            description="Get notified when fact-checks are complete"
            value={settings.notifications}
            onToggle={(value) => saveSettings({ notifications: value })}
          />

          <SettingRow
            icon={Globe}
            title="Deep Mode"
            description="Enhanced analysis with additional sources (Pro plan required)"
            value={settings.deepMode}
            onToggle={(value) => saveSettings({ deepMode: value })}
          />

          <SettingRow
            icon={Database}
            title="Auto-Cache Results"
            description="Save results for offline viewing"
            value={settings.autoCache}
            onToggle={(value) => saveSettings({ autoCache: value })}
          />

          <SettingRow
            icon={Shield}
            title="Opt-out of Analytics"
            description="Disable usage analytics and crash reporting"
            value={settings.analyticsOptOut}
            onToggle={(value) => saveSettings({ analyticsOptOut: value })}
          />
        </View>

        {/* Data & Privacy Section */}
        <View style={{
          backgroundColor: Colors.deepPurpleGrey,
          marginTop: Spacing.space6,
          marginHorizontal: Spacing.space4,
          borderRadius: BorderRadius.radiusLg,
          overflow: 'hidden',
        }}>
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textSm,
            fontWeight: Typography.fontWeightMedium,
            padding: Spacing.space4,
            paddingBottom: Spacing.space2,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
          }}>
            Data & Privacy
          </Text>

          <SettingRow
            icon={Trash2}
            title="Clear Cache"
            description="Remove cached data and temporary files"
            onPress={handleClearCache}
            destructive={true}
          />
        </View>

        {/* Legal & Support Section */}
        <View style={{
          backgroundColor: Colors.deepPurpleGrey,
          marginTop: Spacing.space6,
          marginHorizontal: Spacing.space4,
          borderRadius: BorderRadius.radiusLg,
          overflow: 'hidden',
        }}>
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textSm,
            fontWeight: Typography.fontWeightMedium,
            padding: Spacing.space4,
            paddingBottom: Spacing.space2,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
          }}>
            Legal & Support
          </Text>

          <SettingRow
            icon={Info}
            title="Privacy Policy"
            onPress={() => openURL('https://tru8.app/privacy')}
            showArrow={true}
          />

          <SettingRow
            icon={Info}
            title="Terms of Service"
            onPress={() => openURL('https://tru8.app/terms')}
            showArrow={true}
          />

          <SettingRow
            icon={Info}
            title="Support Center"
            onPress={() => openURL('https://tru8.app/support')}
            showArrow={true}
          />
        </View>

        {/* Warning Section */}
        <View style={{
          backgroundColor: Colors.verdictUncertain + '20',
          marginTop: Spacing.space6,
          marginHorizontal: Spacing.space4,
          borderRadius: BorderRadius.radiusLg,
          padding: Spacing.space4,
          borderLeftWidth: 4,
          borderLeftColor: Colors.verdictUncertain,
          marginBottom: Spacing.space6,
        }}>
          <View style={{
            flexDirection: 'row',
            alignItems: 'flex-start',
            gap: Spacing.space3,
          }}>
            <AlertTriangle size={20} color={Colors.verdictUncertain} style={{ marginTop: 2 }} />
            <View style={{ flex: 1 }}>
              <Text style={{
                color: Colors.lightGrey,
                fontSize: Typography.textSm,
                fontWeight: Typography.fontWeightMedium,
                marginBottom: Spacing.space1,
              }}>
                Data Usage Notice
              </Text>
              <Text style={{
                color: Colors.coolGrey,
                fontSize: Typography.textSm,
                lineHeight: Typography.textSm * 1.4,
              }}>
                Fact-checking requires internet connectivity and may consume significant data when processing images, videos, or large amounts of text.
              </Text>
            </View>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}