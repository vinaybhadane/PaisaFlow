import type { Metadata } from "next";
import SmoothScrollProvider from "@/components/smooth-scroll";
import CookieConsent from "@/components/cookie-consent";
import "./globals.css";

export const metadata: Metadata = {
  title: "PaisaFlow — Your Money. Your Flow. Your Future.",
  description: "AI-powered personal finance coach with a Living Money Model.",
  icons: {
    icon: "/PaisaFlow.png",
    apple: "/PaisaFlow.png",
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
