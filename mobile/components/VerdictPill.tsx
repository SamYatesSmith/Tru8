import { View, Text } from 'react-native';
import { CheckCircle, AlertTriangle, Clock, HelpCircle, Scale } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import type { VerdictType } from '@shared/constants';

interface VerdictPillProps {
  verdict: VerdictType;
  confidence?: number;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export function VerdictPill({ 
  verdict, 
  confidence, 
  size = 'md',
  showIcon = true 
}: VerdictPillProps) {
  const sizeConfig = {
    sm: {
      padding: Spacing.space2,
      fontSize: Typography.textSm,
      iconSize: 14,
      gap: Spacing.space1,
    },
    md: {
      padding: Spacing.space3,
      fontSize: Typography.textBase,
      iconSize: 16,
      gap: Spacing.space2,
    },
    lg: {
      padding: Spacing.space4,
      fontSize: Typography.textLg,
      iconSize: 20,
      gap: Spacing.space3,
    },
  };

  const getVerdictConfig = () => {
    switch (verdict) {
      case 'supported':
        return {
          backgroundColor: Colors.verdictSupportedBg,
          borderColor: Colors.verdictSupportedBorder,
          textColor: Colors.verdictSupported,
          icon: CheckCircle,
          label: 'Supported',
        };
      case 'contradicted':
        return {
          backgroundColor: Colors.verdictContradictedBg,
          borderColor: Colors.verdictContradictedBorder,
          textColor: Colors.verdictContradicted,
          icon: AlertTriangle,
          label: 'Contradicted',
        };
      case 'uncertain':
        return {
          backgroundColor: Colors.verdictUncertainBg,
          borderColor: Colors.verdictUncertainBorder,
          textColor: Colors.verdictUncertain,
          icon: Clock,
          label: 'Uncertain',
        };
      case 'insufficient_evidence':
        return {
          backgroundColor: Colors.gray100,
          borderColor: Colors.gray400,
          textColor: Colors.gray700,
          icon: HelpCircle,
          label: 'Insufficient Evidence',
        };
      case 'conflicting_expert_opinion':
        return {
          backgroundColor: '#F3E8FF',
          borderColor: '#C084FC',
          textColor: '#7C3AED',
          icon: Scale,
          label: 'Conflicting Opinions',
        };
      case 'outdated_claim':
        return {
          backgroundColor: '#F1F5F9',
          borderColor: '#94A3B8',
          textColor: '#475569',
          icon: Clock,
          label: 'Outdated',
        };
      default:
        return {
          backgroundColor: Colors.gray100,
          borderColor: Colors.gray300,
          textColor: Colors.gray600,
          icon: Clock,
          label: 'Unknown',
        };
    }
  };

  const config = getVerdictConfig();
  const sizeStyles = sizeConfig[size];
  const Icon = config.icon;

  return (
    <View style={{
      flexDirection: 'row',
      alignItems: 'center',
      gap: sizeStyles.gap,
    }}>
      <View style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: sizeStyles.gap,
        backgroundColor: config.backgroundColor,
        borderWidth: 1,
        borderColor: config.borderColor,
        borderRadius: BorderRadius.radiusFull,
        paddingHorizontal: sizeStyles.padding,
        paddingVertical: sizeStyles.padding / 2,
      }}>
        {showIcon && (
          <Icon 
            size={sizeStyles.iconSize} 
            color={config.textColor} 
          />
        )}
        <Text style={{
          color: config.textColor,
          fontSize: sizeStyles.fontSize,
          fontWeight: Typography.fontWeightSemibold,
        }}>
          {config.label}
        </Text>
      </View>
      
      {confidence !== undefined && (
        <Text style={{
          color: Colors.gray600,
          fontSize: sizeStyles.fontSize,
          fontWeight: Typography.fontWeightMedium,
        }}>
          {Math.round(confidence)}%
        </Text>
      )}
    </View>
  );
}