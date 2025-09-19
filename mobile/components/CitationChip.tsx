import { TouchableOpacity, Text, View, Linking, Alert } from 'react-native';
import { ExternalLink, Shield, AlertCircle, Info } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import type { Evidence } from '@shared/types';

interface CitationChipProps {
  evidence: Evidence;
  showCredibility?: boolean;
  compact?: boolean;
}

export function CitationChip({ 
  evidence, 
  showCredibility = false, 
  compact = false 
}: CitationChipProps) {
  const handlePress = async () => {
    try {
      const canOpen = await Linking.canOpenURL(evidence.url);
      if (canOpen) {
        await Linking.openURL(evidence.url);
      } else {
        Alert.alert('Error', 'Unable to open link');
      }
    } catch (error) {
      Alert.alert('Error', 'Unable to open link');
    }
  };

  // Determine credibility based on source reputation
  const getCredibilityIndicator = () => {
    const trustedSources = [
      'bbc', 'reuters', 'ap', 'guardian', 'nytimes', 'washingtonpost', 
      'nature', 'science', 'cnn', 'npr', 'pbs', 'economist'
    ];
    const sourceLower = evidence.source.toLowerCase();
    
    if (trustedSources.some(trusted => sourceLower.includes(trusted))) {
      return { 
        icon: Shield, 
        color: Colors.verdictSupported, 
        label: 'Trusted',
        backgroundColor: Colors.verdictSupportedBg 
      };
    }
    
    if (evidence.relevanceScore > 0.7) {
      return { 
        icon: Info, 
        color: Colors.primary, 
        label: 'Relevant',
        backgroundColor: Colors.gray100 
      };
    }
    
    return { 
      icon: AlertCircle, 
      color: Colors.gray500, 
      label: 'Unverified',
      backgroundColor: Colors.gray100 
    };
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return null;
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return null;
    }
  };

  const credibility = showCredibility ? getCredibilityIndicator() : null;
  const CredIcon = credibility?.icon;
  const formattedDate = formatDate(evidence.publishedDate);

  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.space2 }}>
      <TouchableOpacity
        onPress={handlePress}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: Spacing.space2,
          backgroundColor: Colors.white,
          borderWidth: 1,
          borderColor: Colors.gray300,
          borderRadius: BorderRadius.radiusMd,
          paddingHorizontal: compact ? Spacing.space2 : Spacing.space3,
          paddingVertical: compact ? Spacing.space1 : Spacing.space2,
          maxWidth: showCredibility ? 280 : 240,
        }}
      >
        {showCredibility && CredIcon && (
          <CredIcon 
            size={12} 
            color={credibility.color} 
          />
        )}
        
        <View style={{ flex: 1, minWidth: 0 }}>
          <Text 
            style={{
              color: Colors.gray800,
              fontSize: compact ? Typography.textXs : Typography.textSm,
              fontWeight: Typography.fontWeightMedium,
            }}
            numberOfLines={1}
            ellipsizeMode="tail"
          >
            {evidence.source}
          </Text>
          
          {!compact && formattedDate && (
            <Text 
              style={{
                color: Colors.gray500,
                fontSize: Typography.textXs,
                marginTop: Spacing.space0_5,
              }}
            >
              {formattedDate}
            </Text>
          )}
        </View>

        {!compact && evidence.relevanceScore && (
          <Text style={{
            color: Colors.gray500,
            fontSize: Typography.textXs,
            marginLeft: Spacing.space1,
          }}>
            {Math.round(evidence.relevanceScore * 100)}%
          </Text>
        )}

        <ExternalLink 
          size={compact ? 10 : 12} 
          color={Colors.gray400} 
        />
      </TouchableOpacity>

      {showCredibility && credibility && (
        <View style={{
          backgroundColor: credibility.backgroundColor,
          borderRadius: BorderRadius.radiusSm,
          paddingHorizontal: Spacing.space2,
          paddingVertical: Spacing.space0_5,
        }}>
          <Text style={{
            color: credibility.color,
            fontSize: Typography.textXs,
            fontWeight: Typography.fontWeightMedium,
          }}>
            {credibility.label}
          </Text>
        </View>
      )}
    </View>
  );
}