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
  apiKey: "AIzaSyD2OnFh0QTuA9rLjWeW1Wy7JdiRdnRC_HU",
  authDomain: "paisaflow06.firebaseapp.com",
  projectId: "paisaflow06",
  storageBucket: "paisaflow06.firebasestorage.app",
  messagingSenderId: "153521870367",
  appId: "1:153521870367:web:964432907eaad7079b272a",
};

// Initialize Firebase safely in Next.js (SSR / HMR safe)
const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: "select_account",
});

export async function loginWithGoogle(): Promise<FirebaseUser> {
  const result = await signInWithPopup(auth, googleProvider);
  return result.user;
}

export async function logoutFirebase(): Promise<void> {
  await signOut(auth);
}

export { app, auth, googleProvider, onAuthStateChanged };
export type { FirebaseUser };

