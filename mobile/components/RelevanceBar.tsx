import { View, Text, StyleSheet } from 'react-native';
import { AccentColors, Colors, Fonts } from '@/lib/design-system';

interface RelevanceBarProps {
  score: number; // 0-1
}

export function RelevanceBar({ score }: RelevanceBarProps) {
  const percentage = Math.round(score * 100);

  return (
    <View style={styles.container}>
      <View style={styles.labelRow}>
        <Text style={styles.label}>Relevance</Text>
        <Text style={styles.percentage}>{percentage}%</Text>
      </View>
      <View style={styles.trackBackground}>
        <View
          style={[
            styles.trackFill,
            { width: `${percentage}%` },
          ]}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 4,
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    fontFamily: Fonts.mono,
    fontSize: 9,
    fontWeight: '600',
    color: Colors.gray500,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  percentage: {
    fontFamily: Fonts.mono,
    fontSize: 9,
    fontWeight: '700',
    color: Colors.gray700,
  },
  trackBackground: {
    height: 4,
    width: '100%',
    backgroundColor: Colors.gray200,
    borderRadius: 2,
    overflow: 'hidden',
  },
  trackFill: {
    height: 4,
    backgroundColor: AccentColors.relevanceBlue,
    borderRadius: 2,
  },
});
