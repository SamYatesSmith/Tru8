import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { ElementStateColors, Fonts } from '@/lib/design-system';
import type { EvidenceRelationship } from '@shared/types';

interface EvidenceRefChipProps {
  evidenceId: string;
  relationship: EvidenceRelationship;
  onPress?: () => void;
}

const RELATIONSHIP_STYLES: Record<
  EvidenceRelationship,
  { backgroundColor: string; color: string }
> = {
  supports: {
    backgroundColor: ElementStateColors.supportedBg,
    color: ElementStateColors.supported,
  },
  challenges: {
    backgroundColor: ElementStateColors.disputedBg,
    color: ElementStateColors.disputed,
  },
  context: {
    backgroundColor: ElementStateColors.unresolvedBg,
    color: ElementStateColors.unresolved,
  },
};

export function EvidenceRefChip({ evidenceId, relationship, onPress }: EvidenceRefChipProps) {
  const colors = RELATIONSHIP_STYLES[relationship];
  const shortId = evidenceId.slice(0, 8);

  const content = (
    <View style={[styles.pill, { backgroundColor: colors.backgroundColor }]}>
      <Text style={[styles.label, { color: colors.color }]}>
        {relationship} {shortId}
      </Text>
    </View>
  );

  if (onPress) {
    return (
      <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
        {content}
      </TouchableOpacity>
    );
  }

  return content;
}

const styles = StyleSheet.create({
  pill: {
    alignSelf: 'flex-start',
    borderRadius: 9999,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  label: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    fontWeight: '600',
  },
});
