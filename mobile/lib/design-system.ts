/**
 * Tru8 Design System - React Native
 * Ported from DESIGN_SYSTEM.md to maintain consistency across platforms
 */

// Colors - MUST match DESIGN_SYSTEM.md exactly
export const Colors = {
  // Primary brand colors
  primary: '#1E40AF',        // Deep Blue - main brand
  primaryLight: '#3B82F6',   // Bright Blue - CTAs, links
  primaryDark: '#1E3A8A',    // Navy - headings, emphasis
  
  // Semantic verdict colors - HIGH CONTRAST
  verdictSupported: '#059669',      // Emerald Green
  verdictContradicted: '#DC2626',   // Strong Red
  verdictUncertain: '#D97706',      // Warning Amber
  
  // Verdict backgrounds
  verdictSupportedBg: '#ECFDF5',
  verdictSupportedBorder: '#A7F3D0',
  verdictContradictedBg: '#FEF2F2',
  verdictContradictedBorder: '#FECACA',
  verdictUncertainBg: '#FFFBEB',
  verdictUncertainBorder: '#FDE68A',
  
  // Neutral palette (Information Hierarchy)
  gray900: '#111827',  // Primary headings
  gray800: '#1F2937',  // Body text
  gray700: '#374151',  // Secondary text
  gray600: '#4B5563',  // Muted text
  gray500: '#6B7280',  // Placeholder
  gray400: '#9CA3AF',  // Disabled
  gray300: '#D1D5DB',  // Borders
  gray200: '#E5E7EB',  // Light borders
  gray100: '#F3F4F6',  // Section backgrounds
  gray50: '#F9FAFB',   // Page background
  white: '#FFFFFF',    // Card backgrounds
  black: '#000000',    // Shadow colors, high contrast text
  
  // Legacy colors (for compatibility with existing components)
  darkIndigo: '#2C2C54',    // Base surface / header
  deepPurpleGrey: '#474787', // Cards / secondary surface
  coolGrey: '#AAABB8',      // Muted text, borders
  lightGrey: '#ECECEC',     // Background / contrast
} as const;

// Spacing System (4pt Grid) - All spacing must be multiples of 4px
export const Spacing = {
  space0_5: 2,  // 2px (for very fine spacing)
  space1: 4,    // 4px
  space2: 8,    // 8px
  space3: 12,   // 12px
  space4: 16,   // 16px
  space5: 20,   // 20px
  space6: 24,   // 24px
  space8: 32,   // 32px
  space10: 40,  // 40px
  space12: 48,  // 48px
  space16: 64,  // 64px
  space20: 80,  // 80px
  space24: 96,  // 96px
  space32: 128, // 128px
} as const;

// Typography System
export const Typography = {
  // Font weights
  fontWeightNormal: '400',
  fontWeightMedium: '500',
  fontWeightSemibold: '600',
  fontWeightBold: '700',
  fontWeightBlack: '900',
  
  // Font sizes (responsive equivalents for mobile)
  text5xl: 48,    // Hero titles (clamp equivalent)
  text4xl: 36,    // Page titles
  text3xl: 30,    // Section headers
  text2xl: 24,    // Card titles
  textXl: 20,     // Large text
  textLg: 18,     // Prominent body
  textBase: 16,   // Standard body
  textSm: 14,     // Secondary text
  textXs: 12,     // Captions, labels
  
  // Line heights
  lineHeightTight: 1.2,
  lineHeightNormal: 1.6,
  lineHeightRelaxed: 1.8,
} as const;

// Border Radius System (4pt Based)
export const BorderRadius = {
  radiusSm: 4,   // 4px - small elements
  radiusMd: 8,   // 8px - buttons, inputs
  radiusLg: 12,  // 12px - cards
  radiusXl: 16,  // 16px - modals
  radius2xl: 24, // 24px - hero cards
  radiusFull: 9999, // Pills, avatars
} as const;

// Shadow System
export const Shadows = {
  shadowSm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 1,
  },
  shadowMd: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
    elevation: 3,
  },
  shadowLg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.15,
    shadowRadius: 15,
    elevation: 6,
  },
} as const;

// Component-specific styles
export const ComponentStyles = {
  // Button styles
  buttonPrimary: {
    backgroundColor: Colors.primary,
    paddingVertical: Spacing.space3,
    paddingHorizontal: Spacing.space6,
    borderRadius: BorderRadius.radiusMd,
    ...Shadows.shadowSm,
  },
  
  buttonSecondary: {
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: Colors.gray300,
    paddingVertical: Spacing.space3,
    paddingHorizontal: Spacing.space6,
    borderRadius: BorderRadius.radiusMd,
  },
  
  // Card styles
  card: {
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: Colors.gray200,
    borderRadius: BorderRadius.radiusLg,
    padding: Spacing.space6,
    ...Shadows.shadowSm,
  },
  
  cardFeatured: {
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: Colors.primary,
    borderRadius: BorderRadius.radiusLg,
    padding: Spacing.space6,
    ...Shadows.shadowMd,
  },
  
  // Input styles
  input: {
    backgroundColor: Colors.deepPurpleGrey,
    color: Colors.lightGrey,
    paddingVertical: Spacing.space4,
    paddingHorizontal: Spacing.space4,
    borderRadius: BorderRadius.radiusLg,
    fontSize: Typography.textBase,
    borderWidth: 1,
    borderColor: Colors.coolGrey,
  },
  
  // Container styles
  container: {
    maxWidth: 1024,
    marginHorizontal: 'auto',
    paddingHorizontal: Spacing.space4,
  },
} as const;

// Verdict-specific styles
export const VerdictStyles = {
  pillSupported: {
    backgroundColor: Colors.verdictSupportedBg,
    borderColor: Colors.verdictSupportedBorder,
    borderWidth: 1,
  },
  pillContradicted: {
    backgroundColor: Colors.verdictContradictedBg,
    borderColor: Colors.verdictContradictedBorder,
    borderWidth: 1,
  },
  pillUncertain: {
    backgroundColor: Colors.verdictUncertainBg,
    borderColor: Colors.verdictUncertainBorder,
    borderWidth: 1,
  },
  
  textSupported: {
    color: Colors.verdictSupported,
  },
  textContradicted: {
    color: Colors.verdictContradicted,
  },
  textUncertain: {
    color: Colors.verdictUncertain,
  },
} as const;

// Utility functions
export const getVerdictStyle = (verdict: 'supported' | 'contradicted' | 'uncertain') => {
  switch (verdict) {
    case 'supported':
      return {
        pill: VerdictStyles.pillSupported,
        text: VerdictStyles.textSupported,
        color: Colors.verdictSupported,
      };
    case 'contradicted':
      return {
        pill: VerdictStyles.pillContradicted,
        text: VerdictStyles.textContradicted,
        color: Colors.verdictContradicted,
      };
    case 'uncertain':
      return {
        pill: VerdictStyles.pillUncertain,
        text: VerdictStyles.textUncertain,
        color: Colors.verdictUncertain,
      };
    default:
      return {
        pill: VerdictStyles.pillUncertain,
        text: VerdictStyles.textUncertain,
        color: Colors.verdictUncertain,
      };
  }
};

// Export everything as default for convenience
export default {
  Colors,
  Spacing,
  Typography,
  BorderRadius,
  Shadows,
  ComponentStyles,
  VerdictStyles,
  getVerdictStyle,
};