import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '../utils/colors';

interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string;
  color?: string;
  size?: 'small' | 'medium' | 'large';
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  unit,
  color = COLORS.primary,
  size = 'medium',
}) => {
  const getFontSize = () => {
    switch (size) {
      case 'small': return 18;
      case 'large': return 32;
      default: return 24;
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.valueContainer}>
        <Text style={[styles.value, { fontSize: getFontSize(), color }]}>{value}</Text>
        {unit && <Text style={[styles.unit, { color }]}>{unit}</Text>}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  label: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginBottom: 4,
    textAlign: 'center',
  },
  valueContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  value: {
    fontWeight: '700',
  },
  unit: {
    fontSize: 14,
    fontWeight: '500',
    marginLeft: 4,
  },
});
