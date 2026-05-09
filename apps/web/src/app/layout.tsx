import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "alpha-kite",
  description: "Read-only operator dashboard for alpha-kite-v2",
};

// Runs before React hydrates so the saved theme is applied before first paint —
// without it, light/dark would flash on reload for users who picked a non-auto
// preference.
const themeInitScript = `(function(){try{var t=localStorage.getItem('theme');if(t!=='light'&&t!=='dark'&&t!=='auto')t='auto';document.documentElement.dataset.theme=t;}catch(e){document.documentElement.dataset.theme='auto';}})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
