import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Home from './screens/Home';
import VideoFeed from './screens/VideoFeed';
import Timeline from './screens/Timeline';
import AIChat from './screens/AIChat';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator screenOptions={{ headerShown: false, tabBarStyle: { backgroundColor: '#000' }, tabBarActiveTintColor: '#fff' }}>
        <Tab.Screen name="Home" component={Home} />
        <Tab.Screen name="VideoFeed" component={VideoFeed} />
        <Tab.Screen name="Timeline" component={Timeline} />
        <Tab.Screen name="AIChat" component={AIChat} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
