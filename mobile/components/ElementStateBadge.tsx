import { View, Text, StyleSheet } from 'react-native';
import { Fonts, getElementStateStyle } from '@/lib/design-system';
import { ELEMENT_STATE_LABELS } from '@shared/constants';
import type { ElementState } from '@shared/types';

interface ElementStateBadgeProps {
  state: ElementState;
  size?: 'sm' | 'md';
}

const ICONS: Record<ElementState, string> = {
  supported: '\u2713',
  disputed: '\u26A0',
  unresolved: '\u25CB',
};

export function ElementStateBadge({ state, size = 'md' }: ElementStateBadgeProps) {
  const style = getElementStateStyle(state);
  const fontSize = size === 'sm' ? 8 : 10;

  return (
    <View
      style={[
        styles.pill,
        {
          backgroundColor: style.bg,
          borderColor: style.border,
          paddingHorizontal: size === 'sm' ? 6 : 8,
          paddingVertical: size === 'sm' ? 2 : 3,
        },
      ]}
    >
      <Text
        style={[
          styles.label,
          {
            color: style.color,
            fontSize,
          },
        ]}
      >
        {ICONS[state]} {ELEMENT_STATE_LABELS[state]}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderRadius: 9999,
  },
  label: {
    fontFamily: Fonts.mono,
    fontWeight: '700',
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
});
