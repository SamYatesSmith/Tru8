import { View, Text, StyleSheet } from 'react-native';
import { Colors, Fonts } from '@/lib/design-system';

interface OrientationLineProps {
  orientation: string | null;
}

export function OrientationLine({ orientation }: OrientationLineProps) {
  if (orientation === null) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.label}>ORIENTATION</Text>
      <Text style={styles.text}>{orientation}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 4,
  },
  label: {
    fontFamily: Fonts.mono,
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 3,
    textTransform: 'uppercase',
    color: Colors.gray500,
  },
  text: {
    fontSize: 18,
    fontWeight: '700',
    lineHeight: 24,
    color: Colors.gray900,
  },
});
