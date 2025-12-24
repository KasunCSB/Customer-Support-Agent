import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { RootLayoutClient } from './RootLayoutClient';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: '#2563eb',
};

export const metadata: Metadata = {
  title: 'LankaTel AI Assistant',
  description: 'Your intelligent LankaTel customer support assistant - get instant help with your mobile, broadband, and billing queries',
  keywords: ['LankaTel', 'customer support', 'AI assistant', 'Rashmi', 'telecom', 'Sri Lanka'],
  authors: [{ name: 'LankaTel' }],
  icons: {
    icon: '/favicon.svg',
    shortcut: '/favicon.svg',
    apple: '/apple-touch-icon.png',
  },
  manifest: '/manifest.json',
  openGraph: {
    title: 'LankaTel AI Assistant',
    description: 'Your intelligent LankaTel customer support assistant',
    type: 'website',
    locale: 'en_US',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans`}>
        <RootLayoutClient>{children}</RootLayoutClient>
      </body>
    </html>
  );
}
