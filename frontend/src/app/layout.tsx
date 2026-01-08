import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import VisualEditsMessenger from "../visual-edits/VisualEditsMessenger";
import ErrorReporter from "@/components/ErrorReporter";
import Script from "next/script";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "next-themes";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const spaceGrotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-space" });

export const metadata: Metadata = {
  title: "Thara.ai - AI Voice Assistant",
  description: "Your intelligent AI assistant for data analytics with voice",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable}`} suppressHydrationWarning>
      <body className="antialiased font-sans">
        <div className="fixed inset-0 pointer-events-none z-[9999] opacity-[0.03] mix-blend-overlay">
          <svg className="h-full w-full">
            <filter id="noise">
              <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" />
            </filter>
            <rect width="100%" height="100%" filter="url(#noise)" />
          </svg>
        </div>
        {/* External scripts - only load if environment variables are set */}
        {process.env.NEXT_PUBLIC_ORCHIDS_SCRIPT_URL && (
          <Script
            id="orchids-browser-logs"
            src={process.env.NEXT_PUBLIC_ORCHIDS_SCRIPT_URL}
            strategy="afterInteractive"
            data-orchids-project-id={process.env.NEXT_PUBLIC_ORCHIDS_PROJECT_ID || ''}
          />
        )}
        <ErrorReporter />
        {process.env.NEXT_PUBLIC_ROUTE_MESSENGER_URL && (
          <Script
            src={process.env.NEXT_PUBLIC_ROUTE_MESSENGER_URL}
            strategy="afterInteractive"
            data-target-origin="*"
            data-message-type="ROUTE_CHANGE"
            data-include-search-params="true"
            data-only-in-iframe="true"
            data-debug={process.env.NODE_ENV === 'development' ? 'true' : 'false'}
            data-custom-data={JSON.stringify({ appName: 'Thara.ai', version: '2.0.0' })}
          />
        )}
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          {children}
        </ThemeProvider>
        <Toaster position="bottom-right" expand={false} richColors />
        <VisualEditsMessenger />
      </body>
    </html>
  );
}
