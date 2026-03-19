import os
import json

def create_expo_app(name, screens):
    os.makedirs(name, exist_ok=True)
    os.makedirs(os.path.join(name, "screens"), exist_ok=True)
    
    # package.json
    pkg = {
        "name": name,
        "version": "1.0.0",
        "main": "node_modules/expo/AppEntry.js",
        "scripts": {
            "start": "expo start",
            "android": "expo start --android",
            "ios": "expo start --ios",
            "web": "expo start --web"
        },
        "dependencies": {
            "expo": "~50.0.14",
            "expo-status-bar": "~1.11.1",
            "react": "18.2.0",
            "react-native": "0.73.6",
            "@react-navigation/native": "^6.1.17",
            "@react-navigation/bottom-tabs": "^6.5.20",
            "axios": "^1.6.8"
        }
    }
    with open(f"{name}/package.json", "w") as f:
        json.dump(pkg, f, indent=2)
        
    # app.json
    app_json = {
        "expo": {
            "name": name,
            "slug": name,
            "version": "1.0.0",
            "orientation": "portrait",
            "userInterfaceStyle": "dark"
        }
    }
    with open(f"{name}/app.json", "w") as f:
        json.dump(app_json, f, indent=2)
        
    # App.js
    app_js = '''import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
'''
    for s in screens:
        app_js += f"import {s} from './screens/{s}';\n"
        
    app_js += '''
const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator screenOptions={{ headerShown: false, tabBarStyle: { backgroundColor: '#000' }, tabBarActiveTintColor: '#fff' }}>
'''
    for s in screens:
        app_js += f"        <Tab.Screen name=\"{s}\" component={{{s}}} />\n"
        
    app_js += '''      </Tab.Navigator>
    </NavigationContainer>
  );
}
'''
    with open(f"{name}/App.js", "w") as f:
        f.write(app_js)
        
    # Screens
    for s in screens:
        screen_code = f'''import React from 'react';
import {{ View, Text, StyleSheet }} from 'react-native';

export default function {s}() {{
  return (
    <View style={{styles.container}}>
      <Text style={{styles.text}}>{s} Screen</Text>
    </View>
  );
}}

const styles = StyleSheet.create({{
  container: {{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0a0f16' }},
  text: {{ color: '#fff', fontSize: 20, fontWeight: 'bold' }}
}});
'''
        with open(f"{name}/screens/{s}.js", "w") as f:
            f.write(screen_code)

create_expo_app("mobile-admin", ["Dashboard", "SystemStatus", "Logs", "ControlPanel"])
create_expo_app("mobile-user", ["Home", "VideoFeed", "Timeline", "AIChat"])
print("Apps scaffolded perfectly.")
