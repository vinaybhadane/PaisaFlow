import type { Metadata } from "next";
import SmoothScrollProvider from "@/components/smooth-scroll";
import CookieConsent from "@/components/cookie-consent";
import "./globals.css";

export const metadata: Metadata = {
  title: "PaisaFlow — Your Money. Your Flow. Your Future.",
  description: "AI-powered personal finance coach with a Living Money Model.",
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/favicon.png", type: "image/png" },
      { url: "/PaisaFlow-white.png", type: "image/png" },
    ],
    apple: [
      { url: "/apple-touch-icon.png" },
      { url: "/PaisaFlow-white.png" },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <SmoothScrollProvider>
          {children}
          <CookieConsent />
        </SmoothScrollProvider>
      </body>
    </html>
  );
}
