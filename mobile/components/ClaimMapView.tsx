import { View, Text, StyleSheet } from 'react-native';
import { Colors, Spacing } from '@/lib/design-system';
import { ClaimTypeBadge } from './ClaimTypeBadge';
import { ElementList } from './ElementList';
import { OrientationLine } from './OrientationLine';
import type { Claim } from '@shared/types';

interface ClaimMapViewProps {
  claim: Claim;
}

export function ClaimMapView({ claim }: ClaimMapViewProps) {
  const claimMap = claim.claimMap;

  if (!claimMap) {
    return (
      <View style={styles.card}>
        <Text style={styles.fallback}>Claim map not available.</Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      {/* Claim type badge */}
      <ClaimTypeBadge claimType={claimMap.claimType} />

      {/* Normalised claim */}
      <Text style={styles.normalisedClaim}>{claimMap.normalisedClaim}</Text>

      {/* Separator */}
      <View style={styles.separator} />

      {/* Elements */}
      <ElementList elements={claimMap.elements} />

      {/* Separator */}
      <View style={styles.separator} />

      {/* Orientation */}
      <OrientationLine orientation={claimMap.orientation} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderColor: Colors.gray200,
    borderRadius: 12,
    padding: Spacing.space4,
    backgroundColor: Colors.white,
    gap: Spacing.space3,
  },
  normalisedClaim: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.gray900,
    lineHeight: 22,
  },
  separator: {
    height: 1,
    backgroundColor: Colors.gray200,
  },
  fallback: {
    fontSize: 14,
    color: Colors.gray400,
    fontStyle: 'italic',
  },
});
