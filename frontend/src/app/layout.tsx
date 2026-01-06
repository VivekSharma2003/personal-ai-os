import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';
import { Sidebar } from '@/components/layout/Sidebar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
    title: 'Personal AI OS',
    description: 'An AI assistant that learns your preferences',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="dark">
            <body className={inter.className}>
                <div className="flex h-screen">
                    <Sidebar />
                    <main className="flex-1 overflow-hidden">
                        {children}
                    </main>
                </div>
                <Toaster />
            </body>
        </html>
    );
}
