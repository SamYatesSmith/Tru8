import { ScrollView, View, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { CreateCheckForm } from '@/components/CreateCheckForm';
import { router } from 'expo-router';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { useNetwork } from '@/hooks/use-network';
import { useState, useEffect } from 'react';
import OfflineQueueManager from '@/lib/offline-queue';

export default function HomeScreen() {
  const { isOnline } = useNetwork();
  const [queueCount, setQueueCount] = useState(0);

  const handleCheckCreated = (checkId: string) => {
    // Navigate to real-time progress screen first
    router.push(`/(tabs)/progress/${checkId}`);
  };

  useEffect(() => {
    const updateQueueCount = async () => {
      const count = await OfflineQueueManager.getQueueCount();
      setQueueCount(count);
    };

    updateQueueCount();
    
    // Update queue count every 5 seconds
    const interval = setInterval(updateQueueCount, 5000);
    return () => clearInterval(interval);
  }, []);

  // Process offline queue when coming back online
  useEffect(() => {
    if (isOnline && queueCount > 0) {
      const processQueue = async () => {
        try {
          // We need a token, but can't get it here without auth context
          // This will be handled when the user tries to create a new check
          console.log('Back online, queue will be processed on next check creation');
        } catch (error) {
          console.error('Failed to process offline queue:', error);
        }
      };
      processQueue();
    }
  }, [isOnline, queueCount]);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.darkIndigo }}>
      <ScrollView style={{ flex: 1 }}>
        {/* Queue Status */}
        {queueCount > 0 && (
          <View style={{
            margin: Spacing.space4,
            marginBottom: 0,
            backgroundColor: Colors.deepPurpleGrey,
            borderRadius: BorderRadius.radiusLg,
            padding: Spacing.space4,
            borderLeftWidth: 4,
            borderLeftColor: isOnline ? Colors.verdictSupported : Colors.verdictContradicted,
          }}>
            <Text style={{
              color: Colors.lightGrey,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightMedium,
            }}>
              {queueCount} check{queueCount === 1 ? '' : 's'} queued
            </Text>
            <Text style={{
              color: Colors.coolGrey,
              fontSize: Typography.textSm,
              marginTop: Spacing.space1,
            }}>
              {isOnline 
                ? 'Will be processed when you create your next check'
                : 'Waiting for internet connection'
              }
            </Text>
          </View>
        )}
        
        <CreateCheckForm onSuccess={handleCheckCreated} />
      </ScrollView>
    </SafeAreaView>
  );
}