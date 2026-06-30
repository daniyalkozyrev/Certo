import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { AuthProvider } from "@/components/auth-provider";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

// Set the theme class before paint to avoid a flash of the wrong theme.
const NO_FLASH = `(function(){try{var t=localStorage.getItem('certo.theme')||'system';var d=t==='dark'||(t==='system'&&window.matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.toggle('dark',d);}catch(e){}})();`;

export const metadata: Metadata = {
  metadataBase: new URL(APP_URL),
  title: "Certo — Trust & security audits for AI agents",
  description:
    "Connect an AI agent, run an automated security & trust audit, get an explainable Trust Score, fixes and a shareable certificate. The benchmark, trust & optimization layer for AI agents.",
  openGraph: {
    title: "Certo — Ship AI agents you can trust",
    description: "Automated security & reliability audits, an explainable Trust Score, and a shareable certificate for AI agents.",
    url: APP_URL,
    siteName: "Certo",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Certo — Ship AI agents you can trust",
    description: "Automated security & reliability audits, an explainable Trust Score, and a shareable certificate for AI agents.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH }} />
      </head>
      <body className="min-h-screen antialiased">
        <ThemeProvider>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
