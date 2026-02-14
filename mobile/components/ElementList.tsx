import { View, Text, StyleSheet } from 'react-native';
import { Colors, Fonts, Spacing } from '@/lib/design-system';
import { ElementStateBadge } from './ElementStateBadge';
import { EvidenceRefChip } from './EvidenceRefChip';
import type { ClaimElement } from '@shared/types';

interface ElementListProps {
  elements: ClaimElement[];
}

export function ElementList({ elements }: ElementListProps) {
  return (
    <View style={styles.container}>
      {elements.map((element, index) => {
        const number = String(index + 1).padStart(2, '0');
        return (
          <View key={element.elementId} style={styles.elementRow}>
            {/* Number */}
            <Text style={styles.number}>{number}</Text>

            {/* Content */}
            <View style={styles.content}>
              {/* Description */}
              <Text style={styles.description}>{element.description}</Text>

              {/* State badge */}
              {element.state !== null && (
                <View style={styles.badgeRow}>
                  <ElementStateBadge state={element.state} size="sm" />
                </View>
              )}

              {/* Evidence refs */}
              {element.evidenceRefs.length > 0 && (
                <View style={styles.refsRow}>
                  {element.evidenceRefs.map((ref) => (
                    <EvidenceRefChip
                      key={`${ref.evidenceId}-${ref.relationship}`}
                      evidenceId={ref.evidenceId}
                      relationship={ref.relationship}
                    />
                  ))}
                </View>
              )}

              {/* Uncertainty note */}
              {element.uncertainty !== null && (
                <Text style={styles.uncertainty}>{element.uncertainty}</Text>
              )}
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.space3,
  },
  elementRow: {
    flexDirection: 'row',
    gap: Spacing.space2,
  },
  number: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    fontWeight: '700',
    color: Colors.gray400,
    marginTop: 2,
    width: 20,
  },
  content: {
    flex: 1,
    gap: Spacing.space2,
  },
  description: {
    fontSize: 14,
    fontWeight: '500',
    color: Colors.gray800,
    lineHeight: 20,
  },
  badgeRow: {
    flexDirection: 'row',
  },
  refsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
  },
  uncertainty: {
    fontSize: 12,
    fontStyle: 'italic',
    color: Colors.gray500,
    lineHeight: 16,
  },
});
