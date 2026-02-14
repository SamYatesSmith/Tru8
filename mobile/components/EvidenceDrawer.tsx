import { Modal, View, Text, ScrollView, TouchableOpacity, Linking, Alert, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { X, Calendar, FileText, ExternalLink } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius, ElementStateColors, Fonts, getElementStateStyle } from '@/lib/design-system';
import { RelevanceBar } from './RelevanceBar';
import { ElementStateBadge } from './ElementStateBadge';
import type { Evidence, ClaimMap, EvidenceRelationship } from '@shared/types';

interface EvidenceDrawerProps {
  evidence: Evidence[];
  claimText: string;
  claimMap: ClaimMap | null;
  visible: boolean;
  onClose: () => void;
}

const RELATIONSHIP_CHIP_STYLES: Record<EvidenceRelationship, { bg: string; color: string; label: string }> = {
  supports: { bg: ElementStateColors.supportedBg, color: ElementStateColors.supported, label: 'Supports' },
  challenges: { bg: ElementStateColors.disputedBg, color: ElementStateColors.disputed, label: 'Challenges' },
  context: { bg: ElementStateColors.unresolvedBg, color: ElementStateColors.unresolved, label: 'Context' },
};

export function EvidenceDrawer({
  evidence,
  claimText,
  claimMap,
  visible,
  onClose
}: EvidenceDrawerProps) {
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'No date';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return 'Invalid date';
    }
  };

  const handleOpenUrl = async (url: string) => {
    try {
      const canOpen = await Linking.canOpenURL(url);
      if (canOpen) {
        await Linking.openURL(url);
      } else {
        Alert.alert('Error', 'Unable to open link');
      }
    } catch {
      Alert.alert('Error', 'Unable to open link');
    }
  };

  // Build a lookup from evidenceId to Evidence item
  const evidenceById = new Map<string, Evidence>();
  for (const item of evidence) {
    if (item.evidenceId) {
      evidenceById.set(item.evidenceId, item);
    }
    // Also index by id as fallback
    evidenceById.set(item.id, item);
  }

  // Build element-grouped sections if claimMap is available
  const renderElementGrouped = () => {
    if (!claimMap || claimMap.elements.length === 0) {
      return renderFlatList();
    }

    // Collect evidence IDs that appear in any element
    const mappedEvidenceIds = new Set<string>();
    for (const element of claimMap.elements) {
      for (const ref of element.evidenceRefs) {
        mappedEvidenceIds.add(ref.evidenceId);
      }
    }

    // Find unmapped evidence (not referenced by any element)
    const unmappedEvidence = evidence.filter(
      (item) => !mappedEvidenceIds.has(item.evidenceId ?? '') && !mappedEvidenceIds.has(item.id)
    );

    return (
      <>
        {claimMap.elements.map((element, elementIndex) => {
          // Gather evidence items for this element
          const elementEvidence: { item: Evidence; relationship: EvidenceRelationship }[] = [];
          for (const ref of element.evidenceRefs) {
            const item = evidenceById.get(ref.evidenceId);
            if (item) {
              elementEvidence.push({ item, relationship: ref.relationship });
            }
          }

          const stateStyle = element.state ? getElementStateStyle(element.state) : null;
          const borderColor = stateStyle ? stateStyle.border : Colors.gray200;

          return (
            <View key={element.elementId} style={styles.elementSection}>
              {/* Section header: element description + state badge */}
              <View style={[styles.elementHeader, { borderLeftColor: borderColor }]}>
                <View style={styles.elementHeaderTop}>
                  <Text style={styles.elementNumber}>
                    {String(elementIndex + 1).padStart(2, '0')}
                  </Text>
                  <Text style={styles.elementDescription}>{element.description}</Text>
                </View>
                {element.state !== null && (
                  <View style={styles.badgeRow}>
                    <ElementStateBadge state={element.state} size="sm" />
                  </View>
                )}
              </View>

              {/* Evidence items for this element */}
              {elementEvidence.length > 0 ? (
                <View style={styles.evidenceList}>
                  {elementEvidence.map(({ item, relationship }) =>
                    renderEvidenceItem(item, relationship)
                  )}
                </View>
              ) : (
                <Text style={styles.noElementEvidence}>No evidence mapped to this element.</Text>
              )}
            </View>
          );
        })}

        {/* Unmapped evidence */}
        {unmappedEvidence.length > 0 && (
          <View style={styles.elementSection}>
            <View style={[styles.elementHeader, { borderLeftColor: Colors.gray300 }]}>
              <Text style={styles.elementDescription}>Other Evidence</Text>
            </View>
            <View style={styles.evidenceList}>
              {unmappedEvidence.map((item) => renderEvidenceItem(item, null))}
            </View>
          </View>
        )}
      </>
    );
  };

  // Flat list fallback when no claimMap
  const renderFlatList = () => (
    <View style={styles.evidenceList}>
      {evidence.map((item) => renderEvidenceItem(item, null))}
    </View>
  );

  // Render a single evidence item
  const renderEvidenceItem = (item: Evidence, relationship: EvidenceRelationship | null) => {
    const chipStyle = relationship ? RELATIONSHIP_CHIP_STYLES[relationship] : null;

    return (
      <View key={item.id} style={styles.evidenceCard}>
        {/* Title (tappable) */}
        <TouchableOpacity onPress={() => handleOpenUrl(item.url)} style={styles.titleRow}>
          <Text style={styles.evidenceTitle} numberOfLines={2}>
            {item.title}
          </Text>
          <ExternalLink size={14} color={Colors.gray400} />
        </TouchableOpacity>

        {/* Source + Date (mono) */}
        <View style={styles.metaRow}>
          <Text style={styles.metaSource}>{item.source}</Text>
          {item.publishedDate && (
            <>
              <Text style={styles.metaDot}> &middot; </Text>
              <Calendar size={10} color={Colors.gray500} />
              <Text style={styles.metaDate}>{formatDate(item.publishedDate)}</Text>
            </>
          )}
        </View>

        {/* Snippet */}
        {item.snippet ? (
          <View style={styles.snippetContainer}>
            <FileText size={12} color={Colors.gray400} style={{ marginTop: 2 }} />
            <Text style={styles.snippetText}>{item.snippet}</Text>
          </View>
        ) : null}

        {/* Relevance bar */}
        <RelevanceBar score={item.relevanceScore} />

        {/* Relationship chip */}
        {chipStyle && (
          <View style={[styles.relationshipChip, { backgroundColor: chipStyle.bg }]}>
            <Text style={[styles.relationshipLabel, { color: chipStyle.color }]}>
              {chipStyle.label}
            </Text>
          </View>
        )}
      </View>
    );
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.safeArea}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Evidence Details</Text>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <X size={20} color={Colors.gray600} />
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.scrollView}>
          {/* Claim Context */}
          <View style={styles.claimContext}>
            <Text style={styles.claimContextLabel}>Claim being analyzed:</Text>
            <Text style={styles.claimContextText}>{claimText}</Text>
          </View>

          {/* Evidence grouped by element (or flat if no claimMap) */}
          <View style={styles.evidenceContainer}>
            <Text style={styles.sectionTitle}>
              {evidence.length} Evidence Source{evidence.length !== 1 ? 's' : ''}
            </Text>

            {renderElementGrouped()}
          </View>

          {/* Bottom spacing */}
          <View style={{ height: Spacing.space6 }} />
        </ScrollView>

        {/* Footer */}
        <View style={styles.footer}>
          <TouchableOpacity onPress={onClose} style={styles.closeFooterButton}>
            <Text style={styles.closeFooterText}>Close</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.gray50,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: Spacing.space4,
    backgroundColor: Colors.white,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray200,
  },
  headerTitle: {
    flex: 1,
    color: Colors.gray900,
    fontSize: Typography.textLg,
    fontWeight: Typography.fontWeightBold,
  },
  closeButton: {
    padding: Spacing.space2,
    borderRadius: BorderRadius.radiusLg,
    backgroundColor: Colors.gray100,
  },
  scrollView: {
    flex: 1,
  },
  claimContext: {
    margin: Spacing.space4,
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.radiusLg,
    borderLeftWidth: 4,
    borderLeftColor: Colors.gray300,
    padding: Spacing.space4,
  },
  claimContextLabel: {
    color: Colors.gray600,
    fontSize: Typography.textSm,
    fontWeight: Typography.fontWeightMedium,
    marginBottom: Spacing.space2,
  },
  claimContextText: {
    color: Colors.gray900,
    fontSize: Typography.textBase,
    lineHeight: Typography.textBase * 1.4,
  },
  evidenceContainer: {
    paddingHorizontal: Spacing.space4,
  },
  sectionTitle: {
    color: Colors.gray900,
    fontSize: Typography.textBase,
    fontWeight: Typography.fontWeightBold,
    marginBottom: Spacing.space4,
  },
  // Element section
  elementSection: {
    marginBottom: Spacing.space5,
  },
  elementHeader: {
    borderLeftWidth: 3,
    paddingLeft: Spacing.space3,
    marginBottom: Spacing.space3,
    gap: Spacing.space2,
  },
  elementHeaderTop: {
    flexDirection: 'row',
    gap: Spacing.space2,
    alignItems: 'flex-start',
  },
  elementNumber: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    fontWeight: '700',
    color: Colors.gray400,
    marginTop: 2,
  },
  elementDescription: {
    flex: 1,
    fontSize: Typography.textSm,
    fontWeight: Typography.fontWeightSemibold,
    color: Colors.gray800,
    lineHeight: Typography.textSm * 1.4,
  },
  badgeRow: {
    flexDirection: 'row',
    marginLeft: Spacing.space5,
  },
  noElementEvidence: {
    color: Colors.gray400,
    fontSize: Typography.textSm,
    fontStyle: 'italic',
    marginLeft: Spacing.space3,
  },
  // Evidence list
  evidenceList: {
    gap: Spacing.space3,
  },
  evidenceCard: {
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.radiusLg,
    borderWidth: 1,
    borderColor: Colors.gray200,
    padding: Spacing.space4,
    gap: Spacing.space3,
    shadowColor: Colors.gray900,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.space2,
  },
  evidenceTitle: {
    flex: 1,
    color: Colors.gray900,
    fontSize: Typography.textBase,
    fontWeight: Typography.fontWeightSemibold,
    lineHeight: Typography.textBase * 1.3,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.space1,
  },
  metaSource: {
    fontFamily: Fonts.mono,
    fontSize: Typography.textXs,
    fontWeight: Typography.fontWeightMedium,
    color: Colors.gray600,
  },
  metaDot: {
    color: Colors.gray400,
    fontSize: Typography.textXs,
  },
  metaDate: {
    fontFamily: Fonts.mono,
    fontSize: Typography.textXs,
    color: Colors.gray500,
    marginLeft: 2,
  },
  snippetContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.space2,
    backgroundColor: Colors.gray50,
    borderRadius: BorderRadius.radiusMd,
    padding: Spacing.space3,
  },
  snippetText: {
    flex: 1,
    color: Colors.gray700,
    fontSize: Typography.textSm,
    lineHeight: Typography.textSm * 1.4,
  },
  relationshipChip: {
    alignSelf: 'flex-start',
    borderRadius: 9999,
    paddingHorizontal: Spacing.space2,
    paddingVertical: 3,
  },
  relationshipLabel: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  // Footer
  footer: {
    backgroundColor: Colors.white,
    borderTopWidth: 1,
    borderTopColor: Colors.gray200,
    padding: Spacing.space4,
  },
  closeFooterButton: {
    backgroundColor: Colors.gray100,
    borderRadius: BorderRadius.radiusLg,
    paddingVertical: Spacing.space3,
    alignItems: 'center',
  },
  closeFooterText: {
    color: Colors.gray700,
    fontSize: Typography.textBase,
    fontWeight: Typography.fontWeightSemibold,
  },
});
