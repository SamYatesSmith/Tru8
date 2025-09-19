import { useEffect, useState } from 'react';
import { View, Text, Animated } from 'react-native';
import { Colors, Spacing, Typography } from '@/lib/design-system';
import type { VerdictType } from '@shared/types';

interface ConfidenceBarProps {
  confidence: number; // 0-100
  verdict?: VerdictType;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
}

export function ConfidenceBar({
  confidence,
  verdict,
  showLabel = true,
  size = 'md',
  animated = true
}: ConfidenceBarProps) {
  const [animatedWidth] = useState(new Animated.Value(0));

  useEffect(() => {
    if (animated) {
      Animated.timing(animatedWidth, {
        toValue: confidence,
        duration: 1000,
        useNativeDriver: false,
      }).start();
    } else {
      animatedWidth.setValue(confidence);
    }
  }, [confidence, animated]);

  const sizeConfig = {
    sm: {
      height: 4,
      fontSize: Typography.textXs,
    },
    md: {
      height: 6,
      fontSize: Typography.textSm,
    },
    lg: {
      height: 8,
      fontSize: Typography.textBase,
    },
  };

  const getBarColor = () => {
    if (!verdict) {
      return Colors.primary;
    }
    
    switch (verdict) {
      case 'supported':
        return Colors.verdictSupported;
      case 'contradicted':
        return Colors.verdictContradicted;
      case 'uncertain':
        return Colors.verdictUncertain;
      default:
        return Colors.primary;
    }
  };

  const styles = sizeConfig[size];
  const barColor = getBarColor();

  return (
    <View style={{ gap: Spacing.space2 }}>
      <View style={{
        height: styles.height,
        backgroundColor: Colors.gray200,
        borderRadius: styles.height / 2,
        overflow: 'hidden',
      }}>
        <Animated.View
          style={{
            height: '100%',
            backgroundColor: barColor,
            borderRadius: styles.height / 2,
            width: animatedWidth.interpolate({
              inputRange: [0, 100],
              outputRange: ['0%', '100%'],
              extrapolate: 'clamp',
            }),
          }}
        />
      </View>
      
      {showLabel && (
        <View style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <Text style={{
            color: Colors.gray600,
            fontSize: styles.fontSize,
            fontWeight: Typography.fontWeightMedium,
          }}>
            Confidence
          </Text>
          <Text style={{
            color: Colors.gray800,
            fontSize: styles.fontSize,
            fontWeight: Typography.fontWeightSemibold,
          }}>
            {Math.round(confidence)}%
          </Text>
        </View>
      )}
    </View>
  );
}