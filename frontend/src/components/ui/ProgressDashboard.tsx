'use client';

import { useState, useEffect, useMemo } from 'react';
import { X, TrendingUp, MessageSquare, Brain, Zap, Calendar, Award } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ProgressDashboard() {
    const [open, setOpen] = useState(false);

    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('ai-os:open-progress', handler);
        return () => window.removeEventListener('ai-os:open-progress', handler);
    }, []);

    // Aggregate stats from various localStorage sources
    const stats = useMemo(() => {
        if (!open) return null;

        // Conversations
        let totalMessages = 0;
        let totalConversations = 0;
        try {
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key?.startsWith('ai-os-conversation-')) {
                    totalConversations++;
                    const data = JSON.parse(localStorage.getItem(key) || '[]');
                    totalMessages += Array.isArray(data) ? data.length : 0;
                }
            }
        } catch {}

        // Streak
        let currentStreak = 0;
        try {
            const streakData = JSON.parse(localStorage.getItem('ai-os-daily-streak') || '{}');
            currentStreak = streakData.currentStreak || 0;
        } catch {}

        // Achievements
        let unlockedBadges = 0;
        try {
            const achievements = JSON.parse(localStorage.getItem('ai-os-achievements') || '{}');
            unlockedBadges = Object.values(achievements).filter(Boolean).length;
        } catch {}

        // Snippets
        let snippetCount = 0;
        try {
            const snippets = JSON.parse(localStorage.getItem('ai-os-snippets') || '[]');
            snippetCount = snippets.length;
        } catch {}

        // Bookmarks
        let bookmarkCount = 0;
        try {
            const bookmarks = JSON.parse(localStorage.getItem('ai-os-bookmarks') || '[]');
            bookmarkCount = bookmarks.length;
        } catch {}

        // Mood entries
        let moodEntries = 0;
        try {
            const moods = JSON.parse(localStorage.getItem('ai-os-mood-journal') || '[]');
            moodEntries = moods.length;
        } catch {}

        // Focus minutes
        let focusMinutes = 0;
        let focusSessions = 0;
        try {
            const focus = JSON.parse(localStorage.getItem('ai-os-focus-stats') || '{}');
            focusMinutes = focus.totalMinutes || 0;
            focusSessions = focus.sessionsCompleted || 0;
        } catch {}

        // Flashcards
        let flashcardCount = 0;
        try {
            const cards = JSON.parse(localStorage.getItem('ai-os-flashcards') || '[]');
            flashcardCount = cards.length;
        } catch {}

        // Habits
        let habitCount = 0;
        try {
            const habits = JSON.parse(localStorage.getItem('ai-os-habits') || '[]');
            habitCount = habits.length;
        } catch {}

        // Reading list
        let readingCount = 0;
        try {
            const items = JSON.parse(localStorage.getItem('ai-os-reading-list') || '[]');
            readingCount = items.length;
        } catch {}

        // Pins
        let pinCount = 0;
        try {
            const pins = JSON.parse(localStorage.getItem('ai-os-pinboard') || '[]');
            pinCount = pins.length;
        } catch {}

        return {
            totalMessages, totalConversations, currentStreak, unlockedBadges,
            snippetCount, bookmarkCount, moodEntries, focusMinutes, focusSessions,
            flashcardCount, habitCount, readingCount, pinCount,
        };
    }, [open]);

    if (!open || !stats) return null;

    const cards = [
        { icon: MessageSquare, label: 'Messages', value: stats.totalMessages, sub: `${stats.totalConversations} conversations`, color: 'from-blue-500/20 to-blue-500/5', iconColor: 'text-blue-400' },
        { icon: Zap, label: 'Streak', value: `${stats.currentStreak}d`, sub: 'Current daily streak', color: 'from-orange-500/20 to-orange-500/5', iconColor: 'text-orange-400' },
        { icon: Award, label: 'Badges', value: stats.unlockedBadges, sub: 'Achievements unlocked', color: 'from-amber-500/20 to-amber-500/5', iconColor: 'text-amber-400' },
        { icon: Brain, label: 'Focus', value: `${stats.focusMinutes}m`, sub: `${stats.focusSessions} sessions`, color: 'from-emerald-500/20 to-emerald-500/5', iconColor: 'text-emerald-400' },
    ];

    const miniStats = [
        { label: 'Snippets', value: stats.snippetCount },
        { label: 'Bookmarks', value: stats.bookmarkCount },
        { label: 'Pins', value: stats.pinCount },
        { label: 'Flashcards', value: stats.flashcardCount },
        { label: 'Habits', value: stats.habitCount },
        { label: 'Reading', value: stats.readingCount },
        { label: 'Moods', value: stats.moodEntries },
    ];

    // Level calculation
    const xp = stats.totalMessages * 10 + stats.currentStreak * 50 + stats.unlockedBadges * 100 + stats.focusMinutes * 5 + stats.snippetCount * 20;
    const level = Math.floor(xp / 500) + 1;
    const xpInLevel = xp % 500;
    const xpPct = (xpInLevel / 500) * 100;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" onClick={() => setOpen(false)} />

            <div className="relative max-w-md mx-auto mt-[8vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                style={{ animation: 'slideUp 200ms ease-out' }}>

                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-emerald-500/10 flex items-center justify-center">
                            <TrendingUp className="w-4 h-4 text-primary" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-foreground">Your Progress</h2>
                            <p className="text-[10px] text-muted-foreground">Level {level} · {xpInLevel}/500 XP</p>
                        </div>
                    </div>
                    <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="p-5 max-h-[70vh] overflow-y-auto space-y-5">
                    {/* XP Bar */}
                    <div>
                        <div className="flex items-center justify-between mb-1.5">
                            <span className="text-xs font-bold text-foreground">Level {level}</span>
                            <span className="text-[10px] text-muted-foreground">{xpInLevel}/500 XP</span>
                        </div>
                        <div className="h-2.5 rounded-full bg-secondary overflow-hidden">
                            <div
                                className="h-full rounded-full bg-gradient-to-r from-primary to-emerald-400 transition-all duration-700"
                                style={{ width: `${xpPct}%` }}
                            />
                        </div>
                        <p className="text-[10px] text-muted-foreground/60 mt-1">{xp} total XP earned</p>
                    </div>

                    {/* Main stat cards */}
                    <div className="grid grid-cols-2 gap-2">
                        {cards.map(card => {
                            const Icon = card.icon;
                            return (
                                <div key={card.label} className={cn('p-3 rounded-xl bg-gradient-to-br border border-border', card.color)}>
                                    <Icon className={cn('w-5 h-5 mb-2', card.iconColor)} />
                                    <p className="text-xl font-bold text-foreground tabular-nums">{card.value}</p>
                                    <p className="text-xs font-medium text-foreground mt-0.5">{card.label}</p>
                                    <p className="text-[10px] text-muted-foreground">{card.sub}</p>
                                </div>
                            );
                        })}
                    </div>

                    {/* Mini stats grid */}
                    <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">Collection Stats</p>
                        <div className="grid grid-cols-4 gap-1.5">
                            {miniStats.map(s => (
                                <div key={s.label} className="text-center p-2 rounded-lg bg-secondary/50 border border-border">
                                    <p className="text-base font-bold text-foreground tabular-nums">{s.value}</p>
                                    <p className="text-[9px] text-muted-foreground">{s.label}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            <style jsx>{`
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                @keyframes slideUp { from { opacity: 0; transform: translateY(10px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
            `}</style>
        </div>
    );
}
