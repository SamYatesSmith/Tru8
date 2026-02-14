import { useEffect, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useAuth } from '@clerk/clerk-expo';
import { Clock, CheckCircle, AlertTriangle, ExternalLink, FileText, Image as ImageIcon, Video, RefreshCw } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius, ElementStateColors, AccentColors } from '@/lib/design-system';
import { getChecks } from '@/lib/api';
import type { Check, ElementState } from '@shared/types';

export default function HistoryScreen() {
  const { getToken } = useAuth();
  const [checks, setChecks] = useState<Check[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchChecks();
  }, []);

  const fetchChecks = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      setError(null);
      
      const token = await getToken();
      if (!token) throw new Error('Not authenticated');
      
      const response = await getChecks(token, 0, 50); // Get first 50 checks
      setChecks(response.checks);
    } catch (err: any) {
      setError(err.message || 'Failed to load history');
    } finally {
      setLoading(false);
      if (isRefresh) setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchChecks(true);
  };

  const getInputTypeIcon = (inputType: string) => {
    switch (inputType) {
      case 'url': return <ExternalLink size={16} color={Colors.coolGrey} />;
      case 'text': return <FileText size={16} color={Colors.coolGrey} />;
      case 'image': return <ImageIcon size={16} color={Colors.coolGrey} />;
      case 'video': return <Video size={16} color={Colors.coolGrey} />;
      default: return <FileText size={16} color={Colors.coolGrey} />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} color={ElementStateColors.supported} />;
      case 'failed': return <AlertTriangle size={16} color={'#ef4444'} />;
      default: return <Clock size={16} color={Colors.coolGrey} />;
    }
  };

  const getElementStateCounts = (check: Check): Record<ElementState, number> => {
    const counts: Record<ElementState, number> = { supported: 0, disputed: 0, unresolved: 0 };
    if (!check.claims) return counts;
    for (const claim of check.claims) {
      if (claim.claimMap?.elements) {
        for (const el of claim.claimMap.elements) {
          if (el.state && el.state in counts) {
            counts[el.state]++;
          }
        }
      }
    }
    return counts;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours}h ago`;
    if (diffInHours < 48) return 'Yesterday';
    return date.toLocaleDateString();
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
            Loading your checks...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.darkIndigo }}>
        <View style={{ 
          flex: 1, 
          justifyContent: 'center', 
          alignItems: 'center',
          gap: Spacing.space4,
          padding: Spacing.space6,
        }}>
          <AlertTriangle size={48} color={'#ef4444'} />
          <Text style={{
            color: Colors.lightGrey,
            fontSize: Typography.textXl,
            fontWeight: Typography.fontWeightBold,
            textAlign: 'center',
          }}>
            Failed to Load History
          </Text>
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textBase,
            textAlign: 'center',
          }}>
            {error}
          </Text>
          <TouchableOpacity 
            onPress={() => fetchChecks()}
            style={{
              backgroundColor: Colors.lightGrey,
              paddingVertical: Spacing.space3,
              paddingHorizontal: Spacing.space6,
              borderRadius: BorderRadius.radiusLg,
              marginTop: Spacing.space4,
              flexDirection: 'row',
              alignItems: 'center',
              gap: Spacing.space2,
            }}
          >
            <RefreshCw size={16} color={Colors.darkIndigo} />
            <Text style={{
              color: Colors.darkIndigo,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightSemibold,
            }}>
              Try Again
            </Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.darkIndigo }}>
      <ScrollView 
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: Spacing.space4 }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={Colors.lightGrey}
            colors={[Colors.lightGrey]}
          />
        }
      >
        {checks.length === 0 ? (
          <View style={{
            flex: 1,
            justifyContent: 'center',
            alignItems: 'center',
            paddingVertical: Spacing.space12,
            gap: Spacing.space4,
          }}>
            <Clock size={64} color={Colors.coolGrey} />
            <Text style={{
              color: Colors.lightGrey,
              fontSize: Typography.textXl,
              fontWeight: Typography.fontWeightBold,
              textAlign: 'center',
            }}>
              No Checks Yet
            </Text>
            <Text style={{
              color: Colors.coolGrey,
              fontSize: Typography.textBase,
              textAlign: 'center',
            }}>
              Start by creating your first fact-check
            </Text>
            <TouchableOpacity 
              onPress={() => router.push('/')}
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
                Create Check
              </Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={{ gap: Spacing.space3 }}>
            {checks.map((check) => (
              <TouchableOpacity
                key={check.id}
                onPress={() => router.push(`/(tabs)/check/${check.id}`)}
                style={{
                  backgroundColor: Colors.deepPurpleGrey,
                  borderRadius: BorderRadius.radiusLg,
                  padding: Spacing.space4,
                  borderWidth: 1,
                  borderColor: Colors.coolGrey + '20',
                }}
              >
                {/* Header Row */}
                <View style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: Spacing.space2,
                }}>
                  <View style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: Spacing.space2,
                  }}>
                    {getInputTypeIcon(check.inputType)}
                    <Text style={{
                      color: Colors.lightGrey,
                      fontSize: Typography.textSm,
                      fontWeight: Typography.fontWeightMedium,
                      textTransform: 'capitalize',
                    }}>
                      {check.inputType}
                    </Text>
                  </View>
                  <Text style={{
                    color: Colors.coolGrey,
                    fontSize: Typography.textSm,
                  }}>
                    {formatDate(check.createdAt)}
                  </Text>
                </View>

                {/* Content Preview */}
                <View style={{ marginBottom: Spacing.space3 }}>
                  {check.inputUrl ? (
                    <Text 
                      style={{
                        color: Colors.lightGrey,
                        fontSize: Typography.textBase,
                        lineHeight: Typography.textBase * 1.4,
                      }}
                      numberOfLines={2}
                    >
                      {check.inputUrl}
                    </Text>
                  ) : (
                    <Text 
                      style={{
                        color: Colors.lightGrey,
                        fontSize: Typography.textBase,
                        lineHeight: Typography.textBase * 1.4,
                      }}
                      numberOfLines={2}
                    >
                      {typeof check.inputContent === 'string' 
                        ? check.inputContent 
                        : check.inputContent?.content || 'Content not available'}
                    </Text>
                  )}
                </View>

                {/* Status and Evidence Row */}
                <View style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}>
                  <View style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: Spacing.space2,
                  }}>
                    {getStatusIcon(check.status)}
                    <Text style={{
                      color: check.status === 'processing' ? AccentColors.orange : (check.status === 'completed' ? ElementStateColors.supported : Colors.coolGrey),
                      fontSize: Typography.textSm,
                    }}>
                      {check.status === 'processing' ? 'Status: Processing...' : `Status: ${check.status.charAt(0).toUpperCase() + check.status.slice(1)}`}
                    </Text>
                  </View>

                  {check.status === 'completed' && check.claims && check.claims.length > 0 && (
                    <View style={{
                      flexDirection: 'row',
                      alignItems: 'center',
                      gap: Spacing.space3,
                    }}>
                      {/* Element state summary dots */}
                      {(() => {
                        const counts = getElementStateCounts(check);
                        const items: { label: string; count: number; color: string }[] = [];
                        if (counts.supported > 0) items.push({ label: 'supported', count: counts.supported, color: ElementStateColors.supported });
                        if (counts.disputed > 0) items.push({ label: 'disputed', count: counts.disputed, color: ElementStateColors.disputed });
                        if (counts.unresolved > 0) items.push({ label: 'unresolved', count: counts.unresolved, color: ElementStateColors.unresolved });
                        return items.map((item) => (
                          <View key={item.label} style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.space1 }}>
                            <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: item.color }} />
                            <Text style={{ color: item.color, fontSize: Typography.textXs, fontWeight: Typography.fontWeightMedium }}>
                              {item.count} {item.label}
                            </Text>
                          </View>
                        ));
                      })()}
                    </View>
                  )}
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}