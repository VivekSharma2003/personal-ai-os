'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Flame, X, Trophy, Calendar, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StreakData {
    activeDays: string[]; // YYYY-MM-DD
    currentStreak: number;
    longestStreak: number;
    lastActiveDate: string;
}

const STORAGE_KEY = 'ai-os-streak-data';
const DAY_MS = 86400000;

const MILESTONES = [
    { days: 3, emoji: '🌱', label: 'Seedling' },
    { days: 7, emoji: '🌿', label: 'Sprout' },
    { days: 14, emoji: '🌳', label: 'Growing' },
    { days: 30, emoji: '⭐', label: 'Star' },
    { days: 60, emoji: '🔥', label: 'On Fire' },
    { days: 100, emoji: '💎', label: 'Diamond' },
    { days: 365, emoji: '👑', label: 'Legend' },
];

function getToday(): string {
    return new Date().toISOString().split('T')[0];
}

function loadStreak(): StreakData {
    if (typeof window === 'undefined') {
        return { activeDays: [], currentStreak: 0, longestStreak: 0, lastActiveDate: '' };
    }
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) return JSON.parse(stored);
    } catch {}
    return { activeDays: [], currentStreak: 0, longestStreak: 0, lastActiveDate: '' };
}

function calcStreak(activeDays: string[]): { currentStreak: number; longestStreak: number } {
    if (activeDays.length === 0) return { currentStreak: 0, longestStreak: 0 };

    const sorted = Array.from(new Set(activeDays)).sort();
    const today = getToday();
    const yesterday = new Date(Date.now() - DAY_MS).toISOString().split('T')[0];

    let currentStreak = 0;
    let longestStreak = 0;
    let streak = 1;

    // Calculate longest
    for (let i = 1; i < sorted.length; i++) {
        const prev = new Date(sorted[i - 1]).getTime();
        const curr = new Date(sorted[i]).getTime();
        if (curr - prev === DAY_MS) {
            streak++;
        } else {
            longestStreak = Math.max(longestStreak, streak);
            streak = 1;
        }
    }
    longestStreak = Math.max(longestStreak, streak);

    // Calculate current streak (must include today or yesterday)
    const lastDay = sorted[sorted.length - 1];
    if (lastDay === today || lastDay === yesterday) {
        currentStreak = 1;
        for (let i = sorted.length - 2; i >= 0; i--) {
            const curr = new Date(sorted[i + 1]).getTime();
            const prev = new Date(sorted[i]).getTime();
            if (curr - prev === DAY_MS) {
                currentStreak++;
            } else {
                break;
            }
        }
    }

    return { currentStreak, longestStreak: Math.max(longestStreak, currentStreak) };
}

function saveStreak(data: StreakData) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

// Heatmap cell color based on activity
function getHeatColor(isActive: boolean, isToday: boolean): string {
    if (isToday && isActive) return 'bg-primary shadow-[0_0_6px_hsl(var(--primary)/0.5)]';
    if (isActive) return 'bg-primary/70';
    if (isToday) return 'bg-muted ring-1 ring-primary/40';
    return 'bg-muted/50';
}

// Compact sidebar badge
export function StreakBadge() {
    const [streak, setStreak] = useState(0);

    useEffect(() => {
        const data = loadStreak();
        const today = getToday();

        // Auto-record today
        if (!data.activeDays.includes(today)) {
            data.activeDays.push(today);
            data.lastActiveDate = today;
            const calc = calcStreak(data.activeDays);
            data.currentStreak = calc.currentStreak;
            data.longestStreak = calc.longestStreak;
            saveStreak(data);
        }
        setStreak(data.currentStreak);
    }, []);

    if (streak === 0) return null;

    return (
        <div className="flex items-center gap-1 px-2 py-1 rounded-md bg-orange-500/10 text-orange-500">
            <Flame className="w-3 h-3 animate-flame" />
            <span className="text-[10px] font-bold">{streak}</span>
        </div>
    );
}

// Full heatmap panel
export function DailyStreak() {
    const [open, setOpen] = useState(false);
    const [data, setData] = useState<StreakData>(loadStreak);

    useEffect(() => {
        const handleOpen = () => setOpen(true);
        window.addEventListener('ai-os:open-streak', handleOpen);
        return () => window.removeEventListener('ai-os:open-streak', handleOpen);
    }, []);

    // Record today on mount
    useEffect(() => {
        const today = getToday();
        setData(prev => {
            if (prev.activeDays.includes(today)) return prev;
            const updated = {
                ...prev,
                activeDays: [...prev.activeDays, today],
                lastActiveDate: today,
            };
            const calc = calcStreak(updated.activeDays);
            updated.currentStreak = calc.currentStreak;
            updated.longestStreak = calc.longestStreak;
            saveStreak(updated);
            return updated;
        });
    }, []);

    // Build 12-week grid (84 days)
    const heatmapDays = useMemo(() => {
        const days: { date: string; isActive: boolean; isToday: boolean; dayOfWeek: number }[] = [];
        const today = new Date();
        const todayStr = getToday();

        for (let i = 83; i >= 0; i--) {
            const d = new Date(today.getTime() - i * DAY_MS);
            const dateStr = d.toISOString().split('T')[0];
            days.push({
                date: dateStr,
                isActive: data.activeDays.includes(dateStr),
                isToday: dateStr === todayStr,
                dayOfWeek: d.getDay(),
            });
        }
        return days;
    }, [data.activeDays]);

    // Organize into weeks (columns)
    const weeks = useMemo(() => {
        const w: typeof heatmapDays[] = [];
        let current: typeof heatmapDays = [];
        heatmapDays.forEach((day, i) => {
            current.push(day);
            if (current.length === 7 || i === heatmapDays.length - 1) {
                w.push(current);
                current = [];
            }
        });
        return w;
    }, [heatmapDays]);

    const currentMilestone = useMemo(() => {
        return [...MILESTONES].reverse().find(m => data.currentStreak >= m.days);
    }, [data.currentStreak]);

    const nextMilestone = useMemo(() => {
        return MILESTONES.find(m => m.days > data.currentStreak);
    }, [data.currentStreak]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50">
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm animate-fade-in" onClick={() => setOpen(false)} />
            <div className="relative max-w-md mx-auto mt-[15vh]" style={{ animation: 'streakIn 250ms cubic-bezier(0.34,1.56,0.64,1)' }}>
                <div className="bg-card border border-border rounded-xl shadow-2xl overflow-hidden">
                    {/* Header */}
                    <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-gradient-to-r from-orange-500/10 to-red-500/10">
                        <div className="flex items-center gap-2">
                            <Flame className="w-5 h-5 text-orange-500 animate-flame" />
                            <span className="font-semibold text-foreground text-sm">Daily Streak</span>
                        </div>
                        <button onClick={() => setOpen(false)} className="p-1 rounded hover:bg-muted text-muted-foreground">
                            <X className="w-4 h-4" />
                        </button>
                    </div>

                    {/* Streak Counter */}
                    <div className="px-5 py-6 text-center">
                        <div className="relative inline-block">
                            <span className="text-5xl font-bold text-foreground tabular-nums">{data.currentStreak}</span>
                            <Flame className="absolute -top-2 -right-5 w-6 h-6 text-orange-500 animate-flame" />
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">day streak</p>
                        {currentMilestone && (
                            <div className="mt-2 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gradient-to-r from-orange-500/10 to-amber-500/10 border border-orange-500/20">
                                <span>{currentMilestone.emoji}</span>
                                <span className="text-xs font-medium text-orange-400">{currentMilestone.label}</span>
                            </div>
                        )}
                    </div>

                    {/* Heatmap */}
                    <div className="px-5 pb-4">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs text-muted-foreground flex items-center gap-1">
                                <Calendar className="w-3 h-3" /> Last 12 weeks
                            </span>
                            <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                                <span>Less</span>
                                <div className="w-2.5 h-2.5 rounded-[3px] bg-muted/50" />
                                <div className="w-2.5 h-2.5 rounded-[3px] bg-primary/40" />
                                <div className="w-2.5 h-2.5 rounded-[3px] bg-primary/70" />
                                <div className="w-2.5 h-2.5 rounded-[3px] bg-primary" />
                                <span>More</span>
                            </div>
                        </div>
                        <div className="flex gap-[3px] justify-center">
                            {weeks.map((week, wi) => (
                                <div key={wi} className="flex flex-col gap-[3px]">
                                    {week.map(day => (
                                        <div
                                            key={day.date}
                                            className={cn(
                                                'w-3 h-3 rounded-[3px] transition-all duration-300',
                                                getHeatColor(day.isActive, day.isToday)
                                            )}
                                            title={`${day.date}${day.isActive ? ' ✓' : ''}`}
                                            style={{ animationDelay: `${wi * 30}ms` }}
                                        />
                                    ))}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-3 gap-px bg-border">
                        <div className="bg-card px-3 py-3 text-center">
                            <p className="text-lg font-bold text-foreground">{data.currentStreak}</p>
                            <p className="text-[10px] text-muted-foreground">Current</p>
                        </div>
                        <div className="bg-card px-3 py-3 text-center">
                            <p className="text-lg font-bold text-foreground">{data.longestStreak}</p>
                            <p className="text-[10px] text-muted-foreground">Longest</p>
                        </div>
                        <div className="bg-card px-3 py-3 text-center">
                            <p className="text-lg font-bold text-foreground">{data.activeDays.length}</p>
                            <p className="text-[10px] text-muted-foreground">Total Days</p>
                        </div>
                    </div>

                    {/* Next milestone */}
                    {nextMilestone && (
                        <div className="px-5 py-3 border-t border-border flex items-center gap-2">
                            <Trophy className="w-3.5 h-3.5 text-amber-400" />
                            <p className="text-xs text-muted-foreground flex-1">
                                Next: <span className="font-medium text-foreground">{nextMilestone.emoji} {nextMilestone.label}</span> in{' '}
                                <span className="text-primary font-medium">{nextMilestone.days - data.currentStreak}</span> days
                            </p>
                            <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                                <div
                                    className="h-full rounded-full bg-gradient-to-r from-orange-500 to-amber-400 transition-all"
                                    style={{ width: `${Math.min(100, (data.currentStreak / nextMilestone.days) * 100)}%` }}
                                />
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <style jsx>{`
                @keyframes streakIn {
                    from { opacity: 0; transform: translateY(-20px) scale(0.95); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
                .animate-flame {
                    animation: flameFlicker 1s ease-in-out infinite alternate;
                }
                @keyframes flameFlicker {
                    0% { transform: scale(1) rotate(-2deg); opacity: 0.9; }
                    50% { transform: scale(1.1) rotate(1deg); opacity: 1; }
                    100% { transform: scale(1) rotate(-1deg); opacity: 0.85; }
                }
            `}</style>
        </div>
    );
}
