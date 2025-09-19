import { useEffect, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { ArrowLeft, RefreshCw, AlertTriangle } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { useRevenueCat } from '@/providers/RevenueCatProvider';
import { PricingCard } from '@/components/PricingCard';
import { MOBILE_PRODUCTS, MobilePlan } from '@/lib/revenuecat';
import RevenueCatService from '@/lib/revenuecat';
import { PurchasesPackage, PurchasesOffering } from 'react-native-purchases';

export default function SubscriptionScreen() {
  const { 
    customerInfo, 
    isLoading: contextLoading,
    error: contextError,
    refreshCustomerInfo,
    hasActiveSubscription,
    activeSubscription 
  } = useRevenueCat();
  
  const [offerings, setOfferings] = useState<PurchasesOffering | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadOfferings();
  }, []);

  const loadOfferings = async () => {
    try {
      setLoading(true);
      setError(null);
      const offerings = await RevenueCatService.getOfferings();
      setOfferings(offerings);
    } catch (err: any) {
      setError(err.message || 'Failed to load pricing');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (plan: MobilePlan, pkg?: PurchasesPackage) => {
    try {
      if (!pkg) {
        throw new Error('Package not available for purchase');
      }

      const customerInfo = await RevenueCatService.purchasePackage(pkg);
      
      Alert.alert(
        'Purchase Successful!',
        `Welcome to ${MOBILE_PRODUCTS[plan].name}! Your subscription is now active.`,
        [
          {
            text: 'OK',
            onPress: () => {
              refreshCustomerInfo();
              router.back();
            }
          }
        ]
      );
    } catch (err: any) {
      // Handle user cancellation gracefully
      if (!err.message.includes('cancelled') && !err.message.includes('canceled')) {
        throw err;
      }
    }
  };

  const handleRestorePurchases = async () => {
    try {
      setLoading(true);
      const customerInfo = await RevenueCatService.restorePurchases();
      await refreshCustomerInfo();
      
      const hasSubscriptions = Object.keys(customerInfo.entitlements.active).length > 0;
      
      Alert.alert(
        'Restore Complete',
        hasSubscriptions 
          ? 'Your purchases have been restored successfully!'
          : 'No previous purchases found.',
        [{ text: 'OK' }]
      );
    } catch (err: any) {
      Alert.alert(
        'Restore Failed',
        err.message || 'Unable to restore purchases. Please try again.',
        [{ text: 'OK' }]
      );
    } finally {
      setLoading(false);
    }
  };

  const getCurrentPlan = (): MobilePlan | null => {
    if (!hasActiveSubscription || !activeSubscription) return null;
    
    // Map entitlement IDs to plans (this would need to match your RevenueCat configuration)
    const entitlementToPlan: Record<string, MobilePlan> = {
      'starter_plan': 'starter',
      'pro_plan': 'pro',
    };
    
    return entitlementToPlan[activeSubscription] || null;
  };

  const getPackageForPlan = (plan: MobilePlan): PurchasesPackage | undefined => {
    if (!offerings) return undefined;
    
    // Map plan to package identifier (this would need to match your RevenueCat configuration)
    const planToIdentifier: Record<MobilePlan, string> = {
      'starter': 'starter_monthly',
      'pro': 'pro_monthly',
    };
    
    const identifier = planToIdentifier[plan];
    return offerings.availablePackages.find(pkg => pkg.identifier === identifier);
  };

  if (contextLoading || loading) {
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
            Loading subscription options...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (contextError || error) {
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
            Unable to Load Subscriptions
          </Text>
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textBase,
            textAlign: 'center',
          }}>
            {contextError || error}
          </Text>
          <TouchableOpacity 
            onPress={() => {
              refreshCustomerInfo();
              loadOfferings();
            }}
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

  const currentPlan = getCurrentPlan();

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
          Subscription Plans
        </Text>
      </View>

      <ScrollView 
        style={{ flex: 1 }}
        contentContainerStyle={{ 
          padding: Spacing.space4, 
          gap: Spacing.space6 
        }}
      >
        {/* Current Status */}
        {hasActiveSubscription && currentPlan && (
          <View style={{
            backgroundColor: Colors.verdictSupported + '20',
            borderRadius: BorderRadius.radiusLg,
            padding: Spacing.space4,
            borderLeftWidth: 4,
            borderLeftColor: Colors.verdictSupported,
            marginBottom: Spacing.space4,
          }}>
            <Text style={{
              color: Colors.verdictSupported,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightBold,
              marginBottom: Spacing.space1,
            }}>
              Active Subscription
            </Text>
            <Text style={{
              color: Colors.lightGrey,
              fontSize: Typography.textSm,
            }}>
              You're currently subscribed to {MOBILE_PRODUCTS[currentPlan].name}
            </Text>
          </View>
        )}

        {/* Pricing Cards */}
        <View style={{ gap: Spacing.space4 }}>
          <PricingCard
            plan="starter"
            isCurrentPlan={currentPlan === 'starter'}
            onUpgrade={handleUpgrade}
            package={getPackageForPlan('starter')}
          />
          
          <PricingCard
            plan="pro"
            isCurrentPlan={currentPlan === 'pro'}
            isPopular={true}
            onUpgrade={handleUpgrade}
            package={getPackageForPlan('pro')}
          />
        </View>

        {/* Restore Purchases */}
        <TouchableOpacity
          onPress={handleRestorePurchases}
          style={{
            alignItems: 'center',
            paddingVertical: Spacing.space4,
            marginTop: Spacing.space4,
          }}
        >
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textBase,
            textDecorationLine: 'underline',
          }}>
            Restore Previous Purchases
          </Text>
        </TouchableOpacity>

        {/* Footer Info */}
        <View style={{
          backgroundColor: Colors.deepPurpleGrey + '80',
          borderRadius: BorderRadius.radiusLg,
          padding: Spacing.space4,
          marginTop: Spacing.space6,
        }}>
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textSm,
            textAlign: 'center',
            lineHeight: Typography.textSm * 1.4,
          }}>
            Subscriptions are managed through your Apple App Store or Google Play Store account. 
            You can cancel or modify your subscription at any time through your device settings.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}