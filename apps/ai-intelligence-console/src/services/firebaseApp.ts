import { getApp, getApps, initializeApp } from 'firebase/app';

const env = import.meta.env;

const firebaseConfig = {
  apiKey: env.VITE_FIREBASE_API_KEY?.trim() || '',
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN?.trim() || '',
  projectId: env.VITE_FIREBASE_PROJECT_ID?.trim() || '',
  storageBucket: env.VITE_FIREBASE_STORAGE_BUCKET?.trim() || '',
  messagingSenderId: env.VITE_FIREBASE_MESSAGING_SENDER_ID?.trim() || '',
  appId: env.VITE_FIREBASE_APP_ID?.trim() || '',
};

const explicitlyEnabled = env.VITE_FIREBASE_ENABLED === 'true';
const requiredConfig = Object.values(firebaseConfig);

export const isFirebaseConfigured =
  explicitlyEnabled && requiredConfig.every((value) => value.length > 0);

export const firestoreDatabaseId = env.VITE_FIRESTORE_DATABASE_ID?.trim() || '';

export const firebaseApp = isFirebaseConfigured
  ? getApps().length > 0
    ? getApp()
    : initializeApp(firebaseConfig)
  : null;
