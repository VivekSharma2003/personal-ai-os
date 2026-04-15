import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';
import { Sidebar } from '@/components/layout/Sidebar';
import { ThemeProvider } from '@/components/layout/ThemeProvider';
import { CommandPalette } from '@/components/ui/CommandPalette';
import { SpotlightSearch } from '@/components/ui/SpotlightSearch';
import { OnboardingTour } from '@/components/ui/OnboardingTour';
import { ShortcutsSheet } from '@/components/ui/ShortcutsSheet';
import { AccentPicker } from '@/components/ui/AccentPicker';
import { Scratchpad } from '@/components/ui/Scratchpad';
import { SnippetLibrary } from '@/components/ui/SnippetSaver';
import { PomodoroTimer } from '@/components/ui/PomodoroTimer';
import { AmbientSounds } from '@/components/ui/AmbientSounds';
import { ChatBackground } from '@/components/ui/ChatBackground';
import { MoodJournal } from '@/components/ui/MoodJournal';
import { Pinboard } from '@/components/ui/Pinboard';
import { DailyStreak } from '@/components/ui/DailyStreak';
import { Achievements } from '@/components/ui/Achievements';
import { WordCloud } from '@/components/ui/WordCloud';
import { FocusSession } from '@/components/ui/FocusSession';
import { QuickActionsFab } from '@/components/ui/QuickActionsFab';
import { FocusModeProvider } from '@/components/layout/FocusMode';
import { StatusBar } from '@/components/layout/StatusBar';

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
        <html lang="en" suppressHydrationWarning>
            <body className={inter.className}>
                <ThemeProvider>
                    <FocusModeProvider>
                        <div className="flex flex-col h-screen">
                            <div className="flex flex-1 overflow-hidden">
                                <Sidebar />
                                <main className="flex-1 overflow-hidden">
                                    {children}
                                </main>
                            </div>
                            <StatusBar />
                        </div>
                        <CommandPalette />
                        <SpotlightSearch />
                        <OnboardingTour />
                        <ShortcutsSheet />
                        <AccentPicker />
                        <Scratchpad />
                        <SnippetLibrary />
                        <PomodoroTimer />
                        <AmbientSounds />
                        <ChatBackground />
                        <MoodJournal />
                        <Pinboard />
                        <DailyStreak />
                        <Achievements />
                        <WordCloud />
                        <FocusSession />
                        <QuickActionsFab />
                        <Toaster />
                    </FocusModeProvider>
                </ThemeProvider>
            </body>
        </html>
    );
}
