import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function Timeline() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Timeline Screen</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0a0f16' },
  text: { color: '#fff', fontSize: 20, fontWeight: 'bold' }
});
