import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function VideoFeed() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>VideoFeed Screen</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0a0f16' },
  text: { color: '#fff', fontSize: 20, fontWeight: 'bold' }
});
