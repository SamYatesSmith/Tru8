import { useState, useEffect } from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth, useUser } from '@clerk/clerk-expo';
import { router } from 'expo-router';
import { LogOut, CreditCard, Settings, HelpCircle, User as UserIcon } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { getCurrentUser } from '@/lib/api';
import { useRevenueCat } from '@/providers/RevenueCatProvider';
import { MOBILE_PRODUCTS } from '@/lib/revenuecat';

interface UserStats {
  credits: number;
  totalCreditsUsed: number;
  totalChecks: number;
  completedChecks: number;
}

export default function AccountScreen() {
  const { signOut, getToken } = useAuth();
  const { user } = useUser();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);
  
  const { hasActiveSubscription, activeSubscription, customerInfo } = useRevenueCat();

  useEffect(() => {
    fetchUserStats();
  }, []);

  const fetchUserStats = async () => {
    try {
      const token = await getToken();
      if (!token) return;
      
      const userData = await getCurrentUser(token);
      setStats({
        credits: userData.credits || 0,
        totalCreditsUsed: userData.totalCreditsUsed || 0,
        totalChecks: userData.stats?.totalChecks || 0,
        completedChecks: userData.stats?.completedChecks || 0,
      });
    } catch (error) {
      console.error('Failed to fetch user stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = () => {
    Alert.alert(
      'Sign Out',
      'Are you sure you want to sign out?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Sign Out', 
          style: 'destructive',
          onPress: () => signOut()
        },
      ]
    );
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
            Loading account...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.darkIndigo }}>
      <ScrollView 
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: Spacing.space4, gap: Spacing.space6 }}
      >
        {/* Profile Section */}
        <View style={{
          backgroundColor: Colors.deepPurpleGrey,
          borderRadius: BorderRadius.radiusLg,
          padding: Spacing.space6,
          alignItems: 'center',
          gap: Spacing.space4,
        }}>
          <View style={{
            width: 80,
            height: 80,
            borderRadius: 40,
            backgroundColor: Colors.lightGrey,
            justifyContent: 'center',
            alignItems: 'center',
          }}>
            <UserIcon size={40} color={Colors.darkIndigo} />
          </View>
          
          <View style={{ alignItems: 'center', gap: Spacing.space1 }}>
            <Text style={{
              color: Colors.lightGrey,
              fontSize: Typography.textXl,
              fontWeight: Typography.fontWeightBold,
            }}>
              {user?.fullName || user?.firstName || 'User'}
            </Text>
            <Text style={{
              color: Colors.coolGrey,
              fontSize: Typography.textBase,
            }}>
              {user?.primaryEmailAddress?.emailAddress}
            </Text>
          </View>
        </View>

        {/* Stats Section */}
        {stats && (
          <View style={{
            backgroundColor: Colors.deepPurpleGrey,
            borderRadius: BorderRadius.radiusLg,
            padding: Spacing.space4,
          }}>
            <Text style={{
              color: Colors.lightGrey,
              fontSize: Typography.textLg,
              fontWeight: Typography.fontWeightBold,
              marginBottom: Spacing.space4,
            }}>
              Your Statistics
            </Text>

            <View style={{
              flexDirection: 'row',
              justifyContent: 'space-between',
            }}>
              <View style={{ alignItems: 'center', flex: 1 }}>
                <Text style={{
                  color: Colors.lightGrey,
                  fontSize: Typography.text2xl,
                  fontWeight: Typography.fontWeightBold,
                }}>
                  {stats.credits}
                </Text>
                <Text style={{
                  color: Colors.coolGrey,
                  fontSize: Typography.textSm,
                  textAlign: 'center',
                }}>
                  Credits Left
                </Text>
              </View>

              <View style={{ alignItems: 'center', flex: 1 }}>
                <Text style={{
                  color: Colors.lightGrey,
                  fontSize: Typography.text2xl,
                  fontWeight: Typography.fontWeightBold,
                }}>
                  {stats.totalChecks}
                </Text>
                <Text style={{
                  color: Colors.coolGrey,
                  fontSize: Typography.textSm,
                  textAlign: 'center',
                }}>
                  Total Checks
                </Text>
              </View>

              <View style={{ alignItems: 'center', flex: 1 }}>
                <Text style={{
                  color: Colors.lightGrey,
                  fontSize: Typography.text2xl,
                  fontWeight: Typography.fontWeightBold,
                }}>
                  {stats.completedChecks}
                </Text>
                <Text style={{
                  color: Colors.coolGrey,
                  fontSize: Typography.textSm,
                  textAlign: 'center',
                }}>
                  Completed
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* Menu Section */}
        <View style={{
          backgroundColor: Colors.deepPurpleGrey,
          borderRadius: BorderRadius.radiusLg,
          overflow: 'hidden',
        }}>
          <TouchableOpacity
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              padding: Spacing.space4,
              gap: Spacing.space3,
              borderBottomWidth: 1,
              borderBottomColor: Colors.coolGrey + '30',
            }}
            onPress={() => {
              router.push('/(tabs)/subscription');
            }}
          >
            <CreditCard size={20} color={Colors.lightGrey} />
            <Text style={{
              flex: 1,
              color: Colors.lightGrey,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightMedium,
            }}>
              {hasActiveSubscription ? 'Manage Subscription' : 'Upgrade Plan'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              padding: Spacing.space4,
              gap: Spacing.space3,
              borderBottomWidth: 1,
              borderBottomColor: Colors.coolGrey + '30',
            }}
            onPress={() => {
              router.push('/(tabs)/settings');
            }}
          >
            <Settings size={20} color={Colors.lightGrey} />
            <Text style={{
              flex: 1,
              color: Colors.lightGrey,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightMedium,
            }}>
              Settings
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              padding: Spacing.space4,
              gap: Spacing.space3,
              borderBottomWidth: 1,
              borderBottomColor: Colors.coolGrey + '30',
            }}
            onPress={() => {
              Alert.alert('Coming Soon', 'Help & Support will be available soon!');
            }}
          >
            <HelpCircle size={20} color={Colors.lightGrey} />
            <Text style={{
              flex: 1,
              color: Colors.lightGrey,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightMedium,
            }}>
              Help & Support
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              padding: Spacing.space4,
              gap: Spacing.space3,
            }}
            onPress={handleSignOut}
          >
            <LogOut size={20} color={Colors.verdictContradicted} />
            <Text style={{
              flex: 1,
              color: Colors.verdictContradicted,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightMedium,
            }}>
              Sign Out
            </Text>
          </TouchableOpacity>
        </View>

        {/* App Version */}
        <Text style={{
          color: Colors.coolGrey,
          fontSize: Typography.textSm,
          textAlign: 'center',
          marginTop: Spacing.space4,
        }}>
          Tru8 v1.0.0
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}