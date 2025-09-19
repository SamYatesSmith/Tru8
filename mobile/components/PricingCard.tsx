import { useState } from 'react';
import { View, Text, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { Check, Zap, Loader2 } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { MOBILE_PRODUCTS, MobilePlan } from '@/lib/revenuecat';
import { PurchasesPackage } from 'react-native-purchases';

interface PricingCardProps {
  plan: MobilePlan;
  isCurrentPlan?: boolean;
  isPopular?: boolean;
  onUpgrade?: (plan: MobilePlan, pkg?: PurchasesPackage) => Promise<void>;
  package?: PurchasesPackage;
  disabled?: boolean;
}

export function PricingCard({ 
  plan, 
  isCurrentPlan, 
  isPopular, 
  onUpgrade, 
  package: pkg,
  disabled 
}: PricingCardProps) {
  const [isLoading, setIsLoading] = useState(false);
  const planData = MOBILE_PRODUCTS[plan];

  const handleUpgrade = async () => {
    if (isCurrentPlan || !onUpgrade || disabled) return;
    
    setIsLoading(true);
    try {
      await onUpgrade(plan, pkg);
    } catch (error: any) {
      console.error('Upgrade failed:', error);
      Alert.alert(
        'Purchase Failed',
        error.message || 'Unable to complete purchase. Please try again.',
        [{ text: 'OK' }]
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <View style={{
      backgroundColor: Colors.deepPurpleGrey,
      borderRadius: BorderRadius.radiusLg,
      padding: Spacing.space6,
      borderWidth: isPopular ? 2 : 1,
      borderColor: isPopular ? Colors.lightGrey : Colors.coolGrey + '40',
      opacity: isCurrentPlan ? 0.75 : 1,
      position: 'relative',
    }}>
      {/* Popular Badge */}
      {isPopular && (
        <View style={{
          position: 'absolute',
          top: -12,
          left: Spacing.space4,
          backgroundColor: Colors.verdictSupported,
          paddingHorizontal: Spacing.space3,
          paddingVertical: Spacing.space1,
          borderRadius: BorderRadius.radiusFull,
          flexDirection: 'row',
          alignItems: 'center',
          gap: Spacing.space1,
        }}>
          <Zap size={12} color={Colors.white} />
          <Text style={{
            color: Colors.white,
            fontSize: Typography.textXs,
            fontWeight: Typography.fontWeightBold,
          }}>
            Popular
          </Text>
        </View>
      )}

      {/* Header */}
      <View style={{ alignItems: 'center', marginBottom: Spacing.space6 }}>
        <Text style={{
          color: Colors.lightGrey,
          fontSize: Typography.text2xl,
          fontWeight: Typography.fontWeightBold,
          marginBottom: Spacing.space2,
        }}>
          {planData.name}
        </Text>
        
        <View style={{ 
          flexDirection: 'row', 
          alignItems: 'baseline',
          marginBottom: Spacing.space2,
        }}>
          <Text style={{
            color: Colors.lightGrey,
            fontSize: Typography.text4xl,
            fontWeight: Typography.fontWeightBlack,
          }}>
            {planData.price}
          </Text>
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textBase,
            marginLeft: Spacing.space2,
          }}>
            /month
          </Text>
        </View>
        
        <Text style={{
          color: Colors.coolGrey,
          fontSize: Typography.textSm,
          textAlign: 'center',
        }}>
          {planData.description}
        </Text>
      </View>

      {/* Features */}
      <View style={{ marginBottom: Spacing.space6 }}>
        {planData.features.map((feature, index) => (
          <View 
            key={index} 
            style={{
              flexDirection: 'row',
              alignItems: 'flex-start',
              gap: Spacing.space3,
              marginBottom: Spacing.space3,
            }}
          >
            <Check size={16} color={Colors.verdictSupported} style={{ marginTop: 2 }} />
            <Text style={{
              flex: 1,
              color: Colors.lightGrey,
              fontSize: Typography.textSm,
              lineHeight: Typography.textSm * 1.4,
            }}>
              {feature}
            </Text>
          </View>
        ))}
      </View>

      {/* Action Button */}
      <TouchableOpacity
        onPress={handleUpgrade}
        disabled={isCurrentPlan || isLoading || disabled}
        style={{
          backgroundColor: isCurrentPlan 
            ? Colors.coolGrey + '40'
            : isPopular 
              ? Colors.lightGrey 
              : 'transparent',
          borderWidth: isCurrentPlan || isPopular ? 0 : 1,
          borderColor: Colors.lightGrey,
          paddingVertical: Spacing.space4,
          borderRadius: BorderRadius.radiusLg,
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 56,
        }}
      >
        {isLoading ? (
          <View style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: Spacing.space2,
          }}>
            <Loader2 size={20} color={isPopular ? Colors.darkIndigo : Colors.lightGrey} />
            <Text style={{
              color: isPopular ? Colors.darkIndigo : Colors.lightGrey,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightSemibold,
            }}>
              Processing...
            </Text>
          </View>
        ) : (
          <Text style={{
            color: isCurrentPlan 
              ? Colors.coolGrey
              : isPopular 
                ? Colors.darkIndigo 
                : Colors.lightGrey,
            fontSize: Typography.textBase,
            fontWeight: Typography.fontWeightSemibold,
          }}>
            {isCurrentPlan 
              ? 'Current Plan' 
              : `Upgrade to ${planData.name}`}
          </Text>
        )}
      </TouchableOpacity>

      {/* Current Plan Note */}
      {isCurrentPlan && (
        <Text style={{
          color: Colors.coolGrey,
          fontSize: Typography.textXs,
          textAlign: 'center',
          marginTop: Spacing.space2,
        }}>
          Your current subscription
        </Text>
      )}
    </View>
  );
}