import { View, Text, StyleSheet } from 'react-native';
import { Fonts } from '@/lib/design-system';
import { CLAIM_TYPE_LABELS } from '@shared/constants';
import type { ClaimType } from '@shared/types';

interface ClaimTypeBadgeProps {
  claimType: ClaimType;
}

export function ClaimTypeBadge({ claimType }: ClaimTypeBadgeProps) {
  return (
    <View style={styles.pill}>
      <Text style={styles.label}>{CLAIM_TYPE_LABELS[claimType]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    alignSelf: 'flex-start',
    backgroundColor: '#f5f5f5',
    borderWidth: 1,
    borderColor: '#e5e5e5',
    borderRadius: 9999,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  label: {
    fontFamily: Fonts.mono,
    fontSize: 8,
    fontWeight: '700',
    letterSpacing: 2,
    textTransform: 'uppercase',
    color: '#737373',
  },
});
