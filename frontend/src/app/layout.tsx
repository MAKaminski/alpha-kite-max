import { DarkModeProvider } from "@/contexts/DarkModeContext";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Alpha Kite Max - Trading Dashboard",
  description: "Real-time trading dashboard with SMA9/VWAP analysis and options trading",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = typeof window !== 'undefined' ? window.location.pathname : '/';
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <DarkModeProvider>
          {/* Sticky top navigation */}
          <div className="sticky top-0 z-40 bg-white/80 dark:bg-gray-900/80 backdrop-blur border-b border-gray-200 dark:border-gray-800">
            <div className="max-w-7xl mx-auto px-4 py-2 flex items-center gap-3 text-sm">
              <Link href="/" className={`px-3 py-1 rounded ${pathname==='/' ? 'bg-blue-600 text-white' : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>Dashboard</Link>
              <Link href="/admin/tokens" className={`px-3 py-1 rounded ${pathname.startsWith('/admin') ? 'bg-blue-600 text-white' : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>Admin</Link>
              <span className="px-3 py-1 rounded text-gray-400 cursor-not-allowed" title="Temporarily disabled">Options</span>
            </div>
          </div>
          {children}
        </DarkModeProvider>
      </body>
    </html>
  );
}
