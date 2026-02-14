import { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { FileSearch } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { ClaimMapView } from '@/components/ClaimMapView';
import { CitationChip } from './CitationChip';
import { EvidenceDrawer } from './EvidenceDrawer';
import type { Claim } from '@shared/types';

interface ClaimCardProps {
  claim: Claim;
  index?: number;
}

export function ClaimCard({ claim, index }: ClaimCardProps) {
  const [evidenceDrawerVisible, setEvidenceDrawerVisible] = useState(false);

  const topEvidence = claim.evidence.slice(0, 2);
  const hasMoreEvidence = claim.evidence.length > 2;

  return (
    <>
      <View style={styles.card}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.claimLabel}>
            Claim {index !== undefined ? index + 1 : claim.position + 1}
          </Text>
        </View>

        {/* Claim Text */}
        <Text style={styles.claimText}>
          {claim.text}
        </Text>

        {/* Claim Map View */}
        <ClaimMapView claim={claim} />

        {/* Evidence Sources */}
        <View>
          {claim.evidence.length > 0 ? (
            <>
              <Text style={styles.sourcesLabel}>
                Sources:
              </Text>

              <View style={styles.sourcesContainer}>
                {/* Top evidence */}
                {topEvidence.map((evidence) => (
                  <CitationChip
                    key={evidence.id}
                    evidence={evidence}
                    showCredibility={true}
                  />
                ))}

                {/* View all sources button */}
                {hasMoreEvidence && (
                  <TouchableOpacity
                    onPress={() => setEvidenceDrawerVisible(true)}
                    style={styles.viewAllButton}
                  >
                    <FileSearch size={14} color={Colors.gray600} />
                    <Text style={styles.viewAllText}>
                      View all {claim.evidence.length} sources
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            </>
          ) : (
            /* No evidence notice */
            <View style={styles.noEvidenceNotice}>
              <Text style={styles.noEvidenceTitle}>
                No Evidence Found
              </Text>
              {claim.sourcesReviewedCount && claim.sourcesReviewedCount > 0 ? (
                <>
                  <Text style={styles.noEvidenceBody}>
                    {claim.sourcesReviewedCount} source{claim.sourcesReviewedCount !== 1 ? 's were' : ' was'} reviewed but none met the quality threshold for display.
                  </Text>
                  <Text style={styles.noEvidenceHint}>
                    View full source details on tru8.com
                  </Text>
                </>
              ) : (
                <Text style={styles.noEvidenceBody}>
                  No relevant sources were found for this claim.
                </Text>
              )}
            </View>
          )}
        </View>
      </View>

      {/* Evidence Drawer Modal */}
      {evidenceDrawerVisible && (
        <EvidenceDrawer
          evidence={claim.evidence}
          claimText={claim.text}
          claimMap={claim.claimMap ?? null}
          visible={evidenceDrawerVisible}
          onClose={() => setEvidenceDrawerVisible(false)}
        />
      )}
    </>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.radiusLg,
    borderWidth: 1,
    borderColor: Colors.gray200,
    padding: Spacing.space4,
    marginBottom: Spacing.space4,
    shadowColor: Colors.gray900,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
    gap: Spacing.space4,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'flex-start',
  },
  claimLabel: {
    color: Colors.gray500,
    fontSize: Typography.textSm,
    fontWeight: Typography.fontWeightMedium,
  },
  claimText: {
    color: Colors.gray900,
    fontSize: Typography.textBase,
    fontWeight: Typography.fontWeightMedium,
    lineHeight: Typography.textBase * 1.5,
  },
  sourcesLabel: {
    color: Colors.gray800,
    fontSize: Typography.textSm,
    fontWeight: Typography.fontWeightSemibold,
    marginBottom: Spacing.space3,
  },
  sourcesContainer: {
    gap: Spacing.space2,
  },
  viewAllButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.space2,
    backgroundColor: Colors.gray50,
    borderWidth: 1,
    borderColor: Colors.gray200,
    borderRadius: BorderRadius.radiusMd,
    paddingHorizontal: Spacing.space3,
    paddingVertical: Spacing.space2,
    marginTop: Spacing.space1,
  },
  viewAllText: {
    color: Colors.gray600,
    fontSize: Typography.textSm,
    fontWeight: Typography.fontWeightMedium,
  },
  noEvidenceNotice: {
    backgroundColor: Colors.gray50,
    borderLeftWidth: 3,
    borderLeftColor: Colors.gray400,
    borderRadius: BorderRadius.radiusMd,
    padding: Spacing.space3,
  },
  noEvidenceTitle: {
    color: Colors.gray700,
    fontSize: Typography.textSm,
    fontWeight: Typography.fontWeightSemibold,
    marginBottom: Spacing.space1,
  },
  noEvidenceBody: {
    color: Colors.gray600,
    fontSize: Typography.textXs,
    lineHeight: Typography.textXs * 1.5,
  },
  noEvidenceHint: {
    color: Colors.gray500,
    fontSize: Typography.textXs,
    fontStyle: 'italic',
    marginTop: Spacing.space2,
  },
});
