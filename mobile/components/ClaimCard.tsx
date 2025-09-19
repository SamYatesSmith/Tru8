import { useState } from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { FileSearch } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { VerdictPill } from './VerdictPill';
import { ConfidenceBar } from './ConfidenceBar';
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
      <View style={{
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
      }}>
        {/* Header */}
        <View style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: Spacing.space3,
        }}>
          <VerdictPill 
            verdict={claim.verdict}
            confidence={claim.confidence}
            size="md"
          />
          <Text style={{
            color: Colors.gray500,
            fontSize: Typography.textSm,
            fontWeight: Typography.fontWeightMedium,
          }}>
            Claim {index !== undefined ? index + 1 : claim.position + 1}
          </Text>
        </View>

        {/* Claim Text */}
        <Text style={{
          color: Colors.gray900,
          fontSize: Typography.textBase,
          fontWeight: Typography.fontWeightMedium,
          lineHeight: Typography.textBase * 1.5,
          marginBottom: Spacing.space4,
        }}>
          {claim.text}
        </Text>

        {/* Confidence Bar */}
        <View style={{ marginBottom: Spacing.space4 }}>
          <ConfidenceBar
            confidence={claim.confidence}
            verdict={claim.verdict}
            size="md"
            animated={true}
          />
        </View>

        {/* Rationale */}
        <View style={{ marginBottom: Spacing.space4 }}>
          <Text style={{
            color: Colors.gray700,
            fontSize: Typography.textSm,
            lineHeight: Typography.textSm * 1.4,
          }}>
            {claim.rationale}
          </Text>
        </View>

        {/* Evidence Sources */}
        <View>
          <Text style={{
            color: Colors.gray800,
            fontSize: Typography.textSm,
            fontWeight: Typography.fontWeightSemibold,
            marginBottom: Spacing.space3,
          }}>
            Sources:
          </Text>
          
          <View style={{ gap: Spacing.space2 }}>
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
                style={{
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
                }}
              >
                <FileSearch size={14} color={Colors.gray600} />
                <Text style={{
                  color: Colors.gray600,
                  fontSize: Typography.textSm,
                  fontWeight: Typography.fontWeightMedium,
                }}>
                  View all {claim.evidence.length} sources
                </Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
      </View>

      {/* Evidence Drawer Modal */}
      {evidenceDrawerVisible && (
        <EvidenceDrawer
          evidence={claim.evidence}
          claimText={claim.text}
          verdict={claim.verdict}
          visible={evidenceDrawerVisible}
          onClose={() => setEvidenceDrawerVisible(false)}
        />
      )}
    </>
  );
}