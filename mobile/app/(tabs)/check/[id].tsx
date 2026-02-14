import { useEffect, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator, Alert, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { useAuth } from '@clerk/clerk-expo';
import { ArrowLeft, ExternalLink, AlertTriangle, Share2 } from 'lucide-react-native';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system';
import { Colors, Spacing, Typography, BorderRadius, Fonts, ElementStateColors } from '@/lib/design-system';
import { getCheck } from '@/lib/api';
import { ClaimCard } from '@/components/ClaimCard';
import { OrientationLine } from '@/components/OrientationLine';
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

    let shareText = `Evidence Report from Tru8\n\n`;

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

      // Add claims with orientation + element count
      if (check.claims && check.claims.length > 0) {
        shareText += `Claims Analyzed: ${check.claims.length}\n\n`;

        check.claims.forEach((claim, index) => {
          shareText += `Claim ${index + 1}: ${claim.text}\n`;
          if (claim.claimMap) {
            const elementCount = claim.claimMap.elements.length;
            shareText += `Elements: ${elementCount}\n`;
            if (claim.claimMap.orientation) {
              shareText += `Orientation: ${claim.claimMap.orientation}\n`;
            }
          }
          shareText += `Sources: ${claim.evidence.length}\n`;
          shareText += `\n`;
        });
      }

      shareText += `Evidence collected by Tru8 - Thorough research with credible sources`;
      shareText += `\n\nView full report: https://tru8.app/r/${check.id}`;

      if (await Sharing.isAvailableAsync()) {
        // Create a temporary text file to share
        const filename = `evidence-report-${check.id.slice(0, 8)}.txt`;
        const fileUri = `${FileSystem.documentDirectory}${filename}`;

        await FileSystem.writeAsStringAsync(fileUri, shareText, {
          encoding: FileSystem.EncodingType.UTF8,
        });

        await Sharing.shareAsync(fileUri, {
          mimeType: 'text/plain',
          dialogTitle: 'Share Evidence Report',
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

  // Helper: compute total sources across all claims
  const getTotalSources = (): number => {
    if (!check?.claims) return 0;
    return check.claims.reduce((sum, c) => sum + c.evidence.length, 0);
  };

  // Helper: format processing time
  const formatTime = (ms?: number): string => {
    if (!ms) return '--';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <View style={styles.loadingContent}>
          <ActivityIndicator size="large" color={Colors.lightGrey} />
          <Text style={styles.loadingText}>
            Loading check results...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error || !check) {
    return (
      <SafeAreaView style={styles.errorContainer}>
        <View style={styles.errorContent}>
          <AlertTriangle size={48} color={'#ef4444'} />
          <Text style={styles.errorTitle}>
            Failed to Load Check
          </Text>
          <Text style={styles.errorMessage}>
            {error || 'Check not found'}
          </Text>
          <TouchableOpacity
            onPress={() => router.back()}
            style={styles.goBackButton}
          >
            <Text style={styles.goBackText}>
              Go Back
            </Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // Get the first claim's orientation for the summary card
  const firstClaimOrientation = check.claims?.[0]?.claimMap?.orientation ?? null;

  return (
    <SafeAreaView style={styles.screen}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={{ marginRight: Spacing.space4 }}
        >
          <ArrowLeft size={24} color={Colors.lightGrey} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>
          Evidence Report
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
        {/* Status Card */}
        <View style={styles.statusCard}>
          <View style={styles.statusRow}>
            <Text style={styles.statusText}>
              Status: {getStatusText(check.status)}
            </Text>
            {check.status === 'processing' && (
              <ActivityIndicator size="small" color={Colors.lightGrey} />
            )}
          </View>

          {check.status === 'completed' && (
            <>
              {/* Completed badge */}
              <View style={styles.completedBadge}>
                <Text style={styles.completedBadgeText}>Completed</Text>
              </View>

              {/* Monospace metadata: REF / SOURCES / TIME */}
              <View style={styles.metadataRow}>
                <View style={styles.metadataItem}>
                  <Text style={styles.metadataLabel}>REF</Text>
                  <Text style={styles.metadataValue}>{check.id.slice(0, 8)}</Text>
                </View>
                <View style={styles.metadataItem}>
                  <Text style={styles.metadataLabel}>SOURCES</Text>
                  <Text style={styles.metadataValue}>{getTotalSources()}</Text>
                </View>
                <View style={styles.metadataItem}>
                  <Text style={styles.metadataLabel}>TIME</Text>
                  <Text style={styles.metadataValue}>{formatTime(check.processingTimeMs)}</Text>
                </View>
              </View>

              {/* Orientation from first claim */}
              {firstClaimOrientation && (
                <View style={styles.orientationContainer}>
                  <OrientationLine orientation={firstClaimOrientation} />
                </View>
              )}
            </>
          )}
        </View>

        {/* Original Content */}
        <View>
          <Text style={styles.sectionHeading}>
            Original {check.inputType === 'url' ? 'Link' : check.inputType}
          </Text>

          <View style={styles.contentCard}>
            {check.inputType === 'url' && check.inputUrl ? (
              <TouchableOpacity
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: Spacing.space2,
                }}
              >
                <ExternalLink size={16} color={Colors.coolGrey} />
                <Text style={styles.urlText}>
                  {check.inputUrl}
                </Text>
              </TouchableOpacity>
            ) : (
              <Text style={styles.contentText}>
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
            <Text style={styles.sectionHeading}>
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

const styles = StyleSheet.create({
  // Loading state
  loadingContainer: {
    flex: 1,
    backgroundColor: Colors.darkIndigo,
  },
  loadingContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: Spacing.space4,
  },
  loadingText: {
    color: Colors.lightGrey,
    fontSize: Typography.textLg,
    fontWeight: Typography.fontWeightMedium,
  },
  // Error state
  errorContainer: {
    flex: 1,
    backgroundColor: Colors.darkIndigo,
  },
  errorContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: Spacing.space4,
    padding: Spacing.space6,
  },
  errorTitle: {
    color: Colors.lightGrey,
    fontSize: Typography.textXl,
    fontWeight: Typography.fontWeightBold,
    textAlign: 'center',
  },
  errorMessage: {
    color: Colors.coolGrey,
    fontSize: Typography.textBase,
    textAlign: 'center',
  },
  goBackButton: {
    backgroundColor: Colors.lightGrey,
    paddingVertical: Spacing.space3,
    paddingHorizontal: Spacing.space6,
    borderRadius: BorderRadius.radiusLg,
    marginTop: Spacing.space4,
  },
  goBackText: {
    color: Colors.darkIndigo,
    fontSize: Typography.textBase,
    fontWeight: Typography.fontWeightSemibold,
  },
  // Main screen
  screen: {
    flex: 1,
    backgroundColor: Colors.darkIndigo,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.space4,
    borderBottomWidth: 1,
    borderBottomColor: Colors.deepPurpleGrey,
  },
  headerTitle: {
    flex: 1,
    color: Colors.lightGrey,
    fontSize: Typography.textLg,
    fontWeight: Typography.fontWeightSemibold,
  },
  // Status card
  statusCard: {
    backgroundColor: Colors.deepPurpleGrey,
    borderRadius: BorderRadius.radiusLg,
    padding: Spacing.space4,
    gap: Spacing.space3,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  statusText: {
    color: Colors.lightGrey,
    fontSize: Typography.textBase,
    fontWeight: Typography.fontWeightMedium,
  },
  completedBadge: {
    alignSelf: 'flex-start',
    backgroundColor: ElementStateColors.supportedBg,
    borderRadius: BorderRadius.radiusSm,
    paddingHorizontal: Spacing.space2,
    paddingVertical: 3,
  },
  completedBadgeText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    fontWeight: '700',
    color: ElementStateColors.supported,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  metadataRow: {
    flexDirection: 'row',
    gap: Spacing.space4,
  },
  metadataItem: {
    gap: 2,
  },
  metadataLabel: {
    fontFamily: Fonts.mono,
    fontSize: 9,
    fontWeight: '600',
    color: Colors.coolGrey,
    textTransform: 'uppercase',
    letterSpacing: 2,
  },
  metadataValue: {
    fontFamily: Fonts.mono,
    fontSize: 13,
    fontWeight: '700',
    color: Colors.lightGrey,
  },
  orientationContainer: {
    marginTop: Spacing.space1,
  },
  // Sections
  sectionHeading: {
    color: Colors.lightGrey,
    fontSize: Typography.textLg,
    fontWeight: Typography.fontWeightBold,
    marginBottom: Spacing.space3,
  },
  // Content card
  contentCard: {
    backgroundColor: Colors.deepPurpleGrey,
    borderRadius: BorderRadius.radiusLg,
    padding: Spacing.space4,
  },
  urlText: {
    flex: 1,
    color: Colors.lightGrey,
    fontSize: Typography.textBase,
  },
  contentText: {
    color: Colors.lightGrey,
    fontSize: Typography.textBase,
    lineHeight: Typography.textBase * 1.5,
  },
});
