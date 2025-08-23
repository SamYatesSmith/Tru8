import { ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { CreateCheckForm } from '@/components/CreateCheckForm';
import { router } from 'expo-router';

export default function HomeScreen() {
  const handleCheckCreated = (checkId: string) => {
    // Navigate to check details or history
    router.push(`/check/${checkId}`);
  };

  return (
    <SafeAreaView className="flex-1 bg-darkIndigo">
      <ScrollView className="flex-1">
        <CreateCheckForm onSuccess={handleCheckCreated} />
      </ScrollView>
    </SafeAreaView>
  );
}