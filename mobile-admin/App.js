import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Dashboard from './screens/Dashboard';
import SystemStatus from './screens/SystemStatus';
import Logs from './screens/Logs';
import ControlPanel from './screens/ControlPanel';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator screenOptions={{ headerShown: false, tabBarStyle: { backgroundColor: '#000' }, tabBarActiveTintColor: '#fff' }}>
        <Tab.Screen name="Dashboard" component={Dashboard} />
        <Tab.Screen name="SystemStatus" component={SystemStatus} />
        <Tab.Screen name="Logs" component={Logs} />
        <Tab.Screen name="ControlPanel" component={ControlPanel} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
