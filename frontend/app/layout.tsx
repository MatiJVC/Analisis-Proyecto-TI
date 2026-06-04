import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const geistSans = Geist({ 
  subsets: ['latin'],
  variable: '--font-geist-sans',
})

const geistMono = Geist_Mono({ 
  subsets: ['latin'],
  variable: '--font-geist-mono',
})

export const metadata: Metadata = {
  title: 'Analytics Platform | Enterprise BI & Observability',
  description: 'Centralized operational analytics and BI platform for real-time monitoring and insights',
  icons: {
    icon: [
      {
        url: '/icon.light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon.light-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.light-32x32.png',
        type: 'image/svg+xml',
      },
    ],
    apple: '/icon.light-32x32.png',
  },
}

export const viewport: Viewport = {
  themeColor: '#3C6E71',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="bg-background">
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}>
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
