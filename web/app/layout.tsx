import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import CoPilotPanel from "./components/CoPilotPanel";
import { getToken } from "./lib/auth";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Job pipeline",
  description: "Track applications, draft letters",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  // The copilot belongs to a signed-in session, so it stays off the sign-in
  // and create-account pages.
  const signedIn = (await getToken()) !== null;

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <div className="flex min-h-screen">
          <div className="min-w-0 flex-1">{children}</div>
          {signedIn && <CoPilotPanel />}
        </div>
      </body>
    </html>
  );
}
