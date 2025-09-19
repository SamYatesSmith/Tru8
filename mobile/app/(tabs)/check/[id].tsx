import { useEffect, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { useAuth } from '@clerk/clerk-expo';
import { ArrowLeft, ExternalLink, Clock, CheckCircle, AlertTriangle, Share2 } from 'lucide-react-native';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { getCheck } from '@/lib/api';
import { ClaimCard } from '@/components/ClaimCard';
import { ScreenErrorBoundary } from '@/components/ErrorBoundary';
import { useApiError } from '@/contexts/ErrorContext';
import { useErrorReporting } from '@/services/error-reporting';
import type { Check } from '@shared/types';

// Using shared types - no need to redeclare
// Check interface is imported from @shared/types

function CheckResultsContent() {
  const { id, action } = useLocalSearchParams<{ id: string; action?: string }>();
  const { getToken } = useAuth();
  const { handleError } = useApiError();
  const { trackUserAction, reportAPIError } = useErrorReporting();
  const [check, setCheck] = useState<Check | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCheck();
  }, [id]);

  // Trigger share if action=share from notification
  useEffect(() => {
    if (action === 'share' && check && check.status === 'completed') {
      handleShare();
    }
  }, [action, check]);

  // Poll for updates if check is processing
  useEffect(() => {
    if (!check || check.status !== 'processing') return;

    const pollInterval = setInterval(() => {
      fetchCheck();
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(pollInterval);
  }, [check?.status]);

  const fetchCheck = async () => {
    if (!id) return;
    
    try {
      setLoading(true);
      const token = await getToken();
      if (!token) {
        handleError('authentication', 'Please sign in to continue');
        return;
      }
      
      trackUserAction('check_fetch_started', { checkId: id });
      const result = await getCheck(id, token);
      setCheck(result);
      setError(null); // Clear any previous errors
      trackUserAction('check_fetch_success', { checkId: id });
    } catch (err: any) {
      console.error('Failed to fetch check:', err);
      trackUserAction('check_fetch_failed', { checkId: id, error: err.message });
      
      if (err.name === 'ApiError') {
        reportAPIError(err.status, err.message, `/checks/${id}`);
      } else if (err.name === 'NetworkError') {
        handleError('network', err.message, true, () => fetchCheck());
        return;
      } else {
        handleError('api', err.message || 'Failed to load check', true, () => fetchCheck());
        return;
      }
      
      setError(err.message || 'Failed to load check');
    } finally {
      setLoading(false);
    }
  };

  const getVerdictColor = (verdict?: string) => {
    switch (verdict) {
      case 'supported': return Colors.verdictSupported;
      case 'contradicted': return Colors.verdictContradicted;
      case 'uncertain': return Colors.verdictUncertain;
      default: return Colors.coolGrey;
    }
  };

  const getVerdictIcon = (verdict?: string) => {
    switch (verdict) {
      case 'supported': return <CheckCircle size={20} color={Colors.verdictSupported} />;
      case 'contradicted': return <AlertTriangle size={20} color={Colors.verdictContradicted} />;
      case 'uncertain': return <Clock size={20} color={Colors.verdictUncertain} />;
      default: return <Clock size={20} color={Colors.coolGrey} />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'processing': return 'Processing...';
      case 'completed': return 'Completed';
      case 'failed': return 'Failed';
      default: return status;
    }
  };

  const handleShare = async () => {
    if (!check) return;
    
    let shareText = `Fact-Check Results from Tru8\n\n`;
    
    try {
      trackUserAction('check_share_started', { checkId: check.id });
      
      // Add original content
      if (check.inputType === 'url' && check.inputUrl) {
        shareText += `Original: ${check.inputUrl}\n\n`;
      } else if (check.inputContent) {
        const content = typeof check.inputContent === 'string' 
          ? check.inputContent 
          : check.inputContent?.content || 'Content not available';
        shareText += `Original: ${content.slice(0, 200)}...\n\n`;
      }
      
      // Add claims and verdicts if available
      if (check.claims && check.claims.length > 0) {
        shareText += `Claims Analyzed: ${check.claims.length}\n\n`;
        
        check.claims.forEach((claim, index) => {
          shareText += `Claim ${index + 1}: ${claim.text}\n`;
          shareText += `Verdict: ${claim.verdict.toUpperCase()} (${Math.round(claim.confidence)}% confidence)\n`;
          if (claim.rationale) {
            shareText += `Rationale: ${claim.rationale}\n`;
          }
          shareText += `\n`;
        });
      }
      
      shareText += `Verified by Tru8 - Instant fact-checking with dated evidence`;
      
      if (await Sharing.isAvailableAsync()) {
        // Create a temporary text file to share
        const filename = `fact-check-${check.id.slice(0, 8)}.txt`;
        const fileUri = `${FileSystem.documentDirectory}${filename}`;
        
        await FileSystem.writeAsStringAsync(fileUri, shareText, {
          encoding: FileSystem.EncodingType.UTF8,
        });
        
        await Sharing.shareAsync(fileUri, {
          mimeType: 'text/plain',
          dialogTitle: 'Share Fact-Check Results',
        });
        
        trackUserAction('check_share_success', { checkId: check.id, method: 'file' });
      } else {
        // Fallback to system share if Expo sharing not available
        Alert.alert('Share', shareText);
        trackUserAction('check_share_success', { checkId: check.id, method: 'alert' });
      }
    } catch (error) {
      console.error('Share failed:', error);
      trackUserAction('check_share_failed', { checkId: check.id, error: error instanceof Error ? error.message : String(error) });
      handleError('system', 'Failed to share results. Please try again.');
      
      // Fallback to copy to clipboard or alert
      Alert.alert('Share Results', shareText);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.darkIndigo }}>
        <View style={{ 
          flex: 1, 
          justifyContent: 'center', 
          alignItems: 'center',
          gap: Spacing.space4 
        }}>
          <ActivityIndicator size="large" color={Colors.lightGrey} />
          <Text style={{
            color: Colors.lightGrey,
            fontSize: Typography.textLg,
            fontWeight: Typography.fontWeightMedium,
          }}>
            Loading check results...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error || !check) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.darkIndigo }}>
        <View style={{ 
          flex: 1, 
          justifyContent: 'center', 
          alignItems: 'center',
          gap: Spacing.space4,
          padding: Spacing.space6,
        }}>
          <AlertTriangle size={48} color={Colors.verdictContradicted} />
          <Text style={{
            color: Colors.lightGrey,
            fontSize: Typography.textXl,
            fontWeight: Typography.fontWeightBold,
            textAlign: 'center',
          }}>
            Failed to Load Check
          </Text>
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textBase,
            textAlign: 'center',
          }}>
            {error || 'Check not found'}
          </Text>
          <TouchableOpacity 
            onPress={() => router.back()}
            style={{
              backgroundColor: Colors.lightGrey,
              paddingVertical: Spacing.space3,
              paddingHorizontal: Spacing.space6,
              borderRadius: BorderRadius.radiusLg,
              marginTop: Spacing.space4,
            }}
          >
            <Text style={{
              color: Colors.darkIndigo,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightSemibold,
            }}>
              Go Back
            </Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.darkIndigo }}>
      {/* Header */}
      <View style={{
        flexDirection: 'row',
        alignItems: 'center',
        padding: Spacing.space4,
        borderBottomWidth: 1,
        borderBottomColor: Colors.deepPurpleGrey,
      }}>
        <TouchableOpacity 
          onPress={() => router.back()}
          style={{ marginRight: Spacing.space4 }}
        >
          <ArrowLeft size={24} color={Colors.lightGrey} />
        </TouchableOpacity>
        <Text style={{
          flex: 1,
          color: Colors.lightGrey,
          fontSize: Typography.textLg,
          fontWeight: Typography.fontWeightSemibold,
        }}>
          Fact-Check Results
        </Text>
        
        {check.status === 'completed' && (
          <TouchableOpacity 
            onPress={handleShare}
            style={{ marginLeft: Spacing.space2 }}
          >
            <Share2 size={24} color={Colors.lightGrey} />
          </TouchableOpacity>
        )}
      </View>

      <ScrollView 
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: Spacing.space4, gap: Spacing.space6 }}
      >
        {/* Status & Verdict */}
        <View style={{
          backgroundColor: Colors.deepPurpleGrey,
          borderRadius: BorderRadius.radiusLg,
          padding: Spacing.space4,
        }}>
          <View style={{
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: Spacing.space3,
          }}>
            <Text style={{
              color: Colors.lightGrey,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightMedium,
            }}>
              Status: {getStatusText(check.status)}
            </Text>
            {check.status === 'processing' && (
              <ActivityIndicator size="small" color={Colors.lightGrey} />
            )}
          </View>

          {check.claims && check.claims.length > 0 && (
            <View style={{
              flexDirection: 'row',
              alignItems: 'center',
              gap: Spacing.space2,
            }}>
              {getVerdictIcon(check.claims[0].verdict)}
              <Text style={{
                color: getVerdictColor(check.claims[0].verdict),
                fontSize: Typography.textLg,
                fontWeight: Typography.fontWeightBold,
                textTransform: 'capitalize',
              }}>
                {check.claims[0].verdict}
              </Text>
              <Text style={{
                color: Colors.coolGrey,
                fontSize: Typography.textSm,
              }}>
                ({Math.round(check.claims[0].confidence)}% confidence)
              </Text>
              {check.claims.length > 1 && (
                <Text style={{
                  color: Colors.coolGrey,
                  fontSize: Typography.textSm,
                }}>
                  +{check.claims.length - 1} more claims
                </Text>
              )}
            </View>
          )}
        </View>

        {/* Original Content */}
        <View>
          <Text style={{
            color: Colors.lightGrey,
            fontSize: Typography.textLg,
            fontWeight: Typography.fontWeightBold,
            marginBottom: Spacing.space3,
          }}>
            Original {check.inputType === 'url' ? 'Link' : check.inputType}
          </Text>
          
          <View style={{
            backgroundColor: Colors.deepPurpleGrey,
            borderRadius: BorderRadius.radiusLg,
            padding: Spacing.space4,
          }}>
            {check.inputType === 'url' && check.inputUrl ? (
              <TouchableOpacity 
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: Spacing.space2,
                }}
              >
                <ExternalLink size={16} color={Colors.coolGrey} />
                <Text style={{
                  flex: 1,
                  color: Colors.lightGrey,
                  fontSize: Typography.textBase,
                }}>
                  {check.inputUrl}
                </Text>
              </TouchableOpacity>
            ) : (
              <Text style={{
                color: Colors.lightGrey,
                fontSize: Typography.textBase,
                lineHeight: Typography.textBase * 1.5,
              }}>
                {typeof check.inputContent === 'string' 
                  ? check.inputContent 
                  : check.inputContent?.content || 'Content not available'}
              </Text>
            )}
          </View>
        </View>

        {/* Claims */}
        {check.claims && check.claims.length > 0 && (
          <View>
            <Text style={{
              color: Colors.lightGrey,
              fontSize: Typography.textLg,
              fontWeight: Typography.fontWeightBold,
              marginBottom: Spacing.space4,
            }}>
              Claims Analyzed ({check.claims.length})
            </Text>
            
            <View>
              {check.claims.map((claim, index) => (
                <ClaimCard
                  key={claim.id}
                  claim={claim}
                  index={index}
                />
              ))}
            </View>
          </View>
        )}

        {/* Evidence - Show evidence from all claims */}
        {check.claims && check.claims.some(claim => claim.evidence.length > 0) && (
          <View>
            <Text style={{
              color: Colors.lightGrey,
              fontSize: Typography.textLg,
              fontWeight: Typography.fontWeightBold,
              marginBottom: Spacing.space3,
            }}>
              Supporting Evidence
            </Text>
            
            <View style={{ gap: Spacing.space3 }}>
              {check.claims.map((claim) => 
                claim.evidence.map((evidence, evidenceIndex) => (
                  <TouchableOpacity
                    key={`${claim.id}-${evidenceIndex}`}
                    style={{
                      backgroundColor: Colors.deepPurpleGrey,
                      borderRadius: BorderRadius.radiusLg,
                      padding: Spacing.space4,
                      borderLeftWidth: 3,
                      borderLeftColor: Colors.lightGrey,
                    }}
                  >
                    <View style={{
                      flexDirection: 'row',
                      alignItems: 'flex-start',
                      gap: Spacing.space2,
                      marginBottom: Spacing.space2,
                    }}>
                      <ExternalLink size={14} color={Colors.coolGrey} />
                      <Text style={{
                        flex: 1,
                        color: Colors.lightGrey,
                        fontSize: Typography.textBase,
                        fontWeight: Typography.fontWeightMedium,
                      }}>
                        {evidence.title}
                      </Text>
                    </View>
                    
                    <Text style={{
                      color: Colors.coolGrey,
                      fontSize: Typography.textSm,
                      marginBottom: Spacing.space1,
                    }}>
                      {evidence.source}
                    </Text>
                    
                    {evidence.publishedDate && (
                      <Text style={{
                        color: Colors.coolGrey,
                        fontSize: Typography.textSm,
                        marginBottom: Spacing.space2,
                      }}>
                        {new Date(evidence.publishedDate).toLocaleDateString()}
                      </Text>
                    )}
                    
                    <Text style={{
                      color: Colors.coolGrey,
                      fontSize: Typography.textSm,
                      lineHeight: Typography.textSm * 1.4,
                    }}>
                      {evidence.snippet}
                    </Text>
                    
                    <Text style={{
                      color: Colors.coolGrey,
                      fontSize: Typography.textXs,
                      marginTop: Spacing.space1,
                    }}>
                      Relevance: {Math.round(evidence.relevanceScore * 100)}%
                    </Text>
                  </TouchableOpacity>
                ))
              )}
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

export default function CheckResults() {
  return (
    <ScreenErrorBoundary>
      <CheckResultsContent />
    </ScreenErrorBoundary>
  );
}