import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.speakmate.app',
  appName: 'SpeakMate',
  webDir: 'dist',
  server: {
    androidScheme: 'https'
  }
};

export default config;
