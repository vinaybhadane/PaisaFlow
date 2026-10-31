import { initializeApp, getApps, getApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  type User as FirebaseUser,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "paisaflow06.firebaseapp.com",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "paisaflow06",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "paisaflow06.firebasestorage.app",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "153521870367",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:153521870367:web:964432907eaad7079b272a",
};

// Initialize Firebase safely in Next.js (SSR / HMR safe)
const app =
  getApps().length > 0
    ? getApp()
    : firebaseConfig.apiKey
    ? initializeApp(firebaseConfig)
    : (null as unknown as ReturnType<typeof initializeApp>);

const auth = app ? getAuth(app) : (null as unknown as ReturnType<typeof getAuth>);
const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: "select_account",
});

export async function loginWithGoogle(): Promise<FirebaseUser> {
  if (!auth) {
    throw new Error(
      "Firebase Auth is not initialized. Please ensure NEXT_PUBLIC_FIREBASE_API_KEY is configured in your environment."
    );
  }
  const result = await signInWithPopup(auth, googleProvider);
  return result.user;
}

export async function logoutFirebase(): Promise<void> {
  if (auth) {
    await signOut(auth);
  }
}

export { app, auth, googleProvider, onAuthStateChanged };
export type { FirebaseUser };
