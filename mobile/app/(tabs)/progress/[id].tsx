import { useLocalSearchParams, router } from 'expo-router';
import { RealTimeProgressScreen } from '@/components/RealTimeProgressScreen';

export default function ProgressScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();

  if (!id) {
    router.replace('/');
    return null;
  }

  const handleBack = () => {
    router.back();
  };

  const handleComplete = (checkId: string) => {
    // Navigate to the completed check results
    router.replace(`/(tabs)/check/${checkId}`);
  };

  return (
    <RealTimeProgressScreen
      checkId={id}
      onBack={handleBack}
      onComplete={handleComplete}
    />
  );
}