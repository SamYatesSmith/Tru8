import { Modal, View, Text, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { X, Calendar, BarChart, FileText } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { ConfidenceBar } from './ConfidenceBar';
import { CitationChip } from './CitationChip';
import type { Evidence, VerdictType } from '@shared/types';

interface EvidenceDrawerProps {
  evidence: Evidence[];
  claimText: string;
  verdict: VerdictType;
  visible: boolean;
  onClose: () => void;
}

export function EvidenceDrawer({
  evidence,
  claimText,
  verdict,
  visible,
  onClose
}: EvidenceDrawerProps) {
  const getRelevanceLabel = (score: number) => {
    if (score >= 0.8) return { label: 'High', color: Colors.verdictSupported };
    if (score >= 0.5) return { label: 'Medium', color: Colors.verdictUncertain };
    return { label: 'Low', color: Colors.gray500 };
  };

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

  const getVerdictBorderColor = () => {
    switch (verdict) {
      case 'supported':
        return Colors.verdictSupported;
      case 'contradicted':
        return Colors.verdictContradicted;
      case 'uncertain':
        return Colors.verdictUncertain;
      default:
        return Colors.gray300;
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <SafeAreaView style={{ 
        flex: 1, 
        backgroundColor: Colors.gray50 
      }}>
        {/* Header */}
        <View style={{
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: Spacing.space4,
          backgroundColor: Colors.white,
          borderBottomWidth: 1,
          borderBottomColor: Colors.gray200,
        }}>
          <Text style={{
            flex: 1,
            color: Colors.gray900,
            fontSize: Typography.textLg,
            fontWeight: Typography.fontWeightBold,
          }}>
            Evidence Details
          </Text>
          <TouchableOpacity
            onPress={onClose}
            style={{
              padding: Spacing.space2,
              borderRadius: BorderRadius.radiusLg,
              backgroundColor: Colors.gray100,
            }}
          >
            <X size={20} color={Colors.gray600} />
          </TouchableOpacity>
        </View>

        <ScrollView style={{ flex: 1 }}>
          {/* Claim Context */}
          <View style={{
            margin: Spacing.space4,
            backgroundColor: Colors.white,
            borderRadius: BorderRadius.radiusLg,
            borderLeftWidth: 4,
            borderLeftColor: getVerdictBorderColor(),
            padding: Spacing.space4,
          }}>
            <Text style={{
              color: Colors.gray600,
              fontSize: Typography.textSm,
              fontWeight: Typography.fontWeightMedium,
              marginBottom: Spacing.space2,
            }}>
              Claim being analyzed:
            </Text>
            <Text style={{
              color: Colors.gray900,
              fontSize: Typography.textBase,
              lineHeight: Typography.textBase * 1.4,
            }}>
              {claimText}
            </Text>
          </View>

          {/* Evidence List */}
          <View style={{ paddingHorizontal: Spacing.space4 }}>
            <Text style={{
              color: Colors.gray900,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightBold,
              marginBottom: Spacing.space4,
            }}>
              {evidence.length} Evidence Sources
            </Text>

            {evidence.map((item, index) => {
              const relevance = getRelevanceLabel(item.relevanceScore);
              
              return (
                <View
                  key={item.id}
                  style={{
                    backgroundColor: Colors.white,
                    borderRadius: BorderRadius.radiusLg,
                    borderWidth: 1,
                    borderColor: Colors.gray200,
                    padding: Spacing.space4,
                    marginBottom: Spacing.space4,
                    shadowColor: Colors.gray900,
                    shadowOffset: { width: 0, height: 1 },
                    shadowOpacity: 0.05,
                    shadowRadius: 2,
                    elevation: 1,
                  }}
                >
                  {/* Header */}
                  <View style={{
                    flexDirection: 'row',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: Spacing.space3,
                  }}>
                    <View style={{ flex: 1, marginRight: Spacing.space3 }}>
                      <Text style={{
                        color: Colors.gray900,
                        fontSize: Typography.textBase,
                        fontWeight: Typography.fontWeightSemibold,
                        lineHeight: Typography.textBase * 1.3,
                        marginBottom: Spacing.space1,
                      }}>
                        {item.title}
                      </Text>
                      
                      <View style={{
                        flexDirection: 'row',
                        alignItems: 'center',
                        gap: Spacing.space2,
                      }}>
                        <Text style={{
                          color: Colors.gray600,
                          fontSize: Typography.textSm,
                          fontWeight: Typography.fontWeightMedium,
                        }}>
                          {item.source}
                        </Text>
                        {item.publishedDate && (
                          <>
                            <Text style={{ color: Colors.gray400 }}>·</Text>
                            <View style={{
                              flexDirection: 'row',
                              alignItems: 'center',
                              gap: Spacing.space1,
                            }}>
                              <Calendar size={12} color={Colors.gray500} />
                              <Text style={{
                                color: Colors.gray500,
                                fontSize: Typography.textSm,
                              }}>
                                {formatDate(item.publishedDate)}
                              </Text>
                            </View>
                          </>
                        )}
                      </View>
                    </View>
                    
                    <View style={{
                      backgroundColor: relevance.label === 'High' 
                        ? Colors.verdictSupportedBg
                        : relevance.label === 'Medium'
                        ? Colors.verdictUncertainBg  
                        : Colors.gray100,
                      borderRadius: BorderRadius.radiusSm,
                      paddingHorizontal: Spacing.space2,
                      paddingVertical: Spacing.space1,
                    }}>
                      <Text style={{
                        color: relevance.color,
                        fontSize: Typography.textXs,
                        fontWeight: Typography.fontWeightSemibold,
                      }}>
                        {relevance.label}
                      </Text>
                    </View>
                  </View>

                  {/* Snippet */}
                  <View style={{
                    backgroundColor: Colors.gray50,
                    borderRadius: BorderRadius.radiusMd,
                    padding: Spacing.space3,
                    marginBottom: Spacing.space3,
                  }}>
                    <View style={{
                      flexDirection: 'row',
                      alignItems: 'flex-start',
                      gap: Spacing.space2,
                    }}>
                      <FileText size={14} color={Colors.gray400} style={{ marginTop: 2 }} />
                      <Text style={{
                        flex: 1,
                        color: Colors.gray700,
                        fontSize: Typography.textSm,
                        lineHeight: Typography.textSm * 1.4,
                      }}>
                        {item.snippet}
                      </Text>
                    </View>
                  </View>

                  {/* Relevance Score */}
                  <View style={{ marginBottom: Spacing.space3 }}>
                    <View style={{
                      flexDirection: 'row',
                      alignItems: 'center',
                      gap: Spacing.space2,
                      marginBottom: Spacing.space2,
                    }}>
                      <BarChart size={14} color={Colors.gray500} />
                      <Text style={{
                        color: Colors.gray600,
                        fontSize: Typography.textSm,
                        fontWeight: Typography.fontWeightMedium,
                      }}>
                        Relevance Score
                      </Text>
                    </View>
                    <ConfidenceBar
                      confidence={item.relevanceScore * 100}
                      size="sm"
                      showLabel={false}
                      animated={true}
                    />
                  </View>

                  {/* Citation Chip */}
                  <CitationChip
                    evidence={item}
                    showCredibility={false}
                  />
                </View>
              );
            })}
          </View>

          {/* Bottom spacing for safe scrolling */}
          <View style={{ height: Spacing.space6 }} />
        </ScrollView>

        {/* Footer */}
        <View style={{
          backgroundColor: Colors.white,
          borderTopWidth: 1,
          borderTopColor: Colors.gray200,
          padding: Spacing.space4,
        }}>
          <TouchableOpacity
            onPress={onClose}
            style={{
              backgroundColor: Colors.gray100,
              borderRadius: BorderRadius.radiusLg,
              paddingVertical: Spacing.space3,
              alignItems: 'center',
            }}
          >
            <Text style={{
              color: Colors.gray700,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightSemibold,
            }}>
              Close
            </Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </Modal>
  );
}