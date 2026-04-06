'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { X, Heart, TrendingUp, Calendar } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MoodEntry {
    date: string; // YYYY-MM-DD
    mood: number; // 1-5
    note?: string;
    timestamp: number;
}

const MOODS = [
    { value: 1, emoji: '😞', label: 'Terrible', color: 'from-red-500 to-rose-400' },
    { value: 2, emoji: '😐', label: 'Meh', color: 'from-orange-500 to-amber-400' },
    { value: 3, emoji: '🙂', label: 'Okay', color: 'from-yellow-500 to-yellow-400' },
    { value: 4, emoji: '😊', label: 'Good', color: 'from-emerald-500 to-green-400' },
    { value: 5, emoji: '🤩', label: 'Amazing', color: 'from-violet-500 to-purple-400' },
];

const STORAGE_KEY = 'ai-os-mood-journal';

function getToday(): string {
    return new Date().toISOString().split('T')[0];
}

function loadEntries(): MoodEntry[] {
    if (typeof window === 'undefined') return [];
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch {
        return [];
    }
}

function saveEntries(entries: MoodEntry[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

// Mini sparkline SVG
function Sparkline({ data, width = 160, height = 40 }: { data: number[]; width?: number; height?: number }) {
    if (data.length < 2) return null;

    const max = 5;
    const min = 1;
    const range = max - min || 1;
    const stepX = width / (data.length - 1);

    const points = data.map((v, i) => ({
        x: i * stepX,
        y: height - ((v - min) / range) * (height - 8) - 4,
    }));

    const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');

    // Area under curve
    const areaPath = `${linePath} L${points[points.length - 1].x},${height} L${points[0].x},${height} Z`;

    return (
        <svg width={width} height={height} className="overflow-visible">
            <defs>
                <linearGradient id="sparkline-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="hsl(160 84% 60%)" stopOpacity="0.8" />
                </linearGradient>
                <linearGradient id="sparkline-area" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.2" />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
                </linearGradient>
            </defs>
            <path d={areaPath} fill="url(#sparkline-area)" />
            <path d={linePath} fill="none" stroke="url(#sparkline-grad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            {points.map((p, i) => (
                <circle key={i} cx={p.x} cy={p.y} r="3" fill="hsl(var(--primary))" stroke="hsl(var(--card))" strokeWidth="1.5" />
            ))}
        </svg>
    );
}

export function MoodJournal() {
    const [open, setOpen] = useState(false);
    const [entries, setEntries] = useState<MoodEntry[]>([]);
    const [selectedMood, setSelectedMood] = useState<number | null>(null);
    const [note, setNote] = useState('');
    const [bouncing, setBouncing] = useState<number | null>(null);

    useEffect(() => {
        setEntries(loadEntries());
    }, []);

    // Keyboard shortcut ⌘E
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
                e.preventDefault();
                setOpen(prev => !prev);
            }
        };
        const handleCustom = () => setOpen(true);
        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('ai-os:open-mood', handleCustom);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('ai-os:open-mood', handleCustom);
        };
    }, []);

    const todayEntry = useMemo(
        () => entries.find(e => e.date === getToday()),
        [entries]
    );

    const last7Days = useMemo(() => {
        const days: number[] = [];
        for (let i = 6; i >= 0; i--) {
            const d = new Date();
            d.setDate(d.getDate() - i);
            const key = d.toISOString().split('T')[0];
            const entry = entries.find(e => e.date === key);
            if (entry) days.push(entry.mood);
        }
        return days;
    }, [entries]);

    const averageMood = useMemo(() => {
        if (entries.length === 0) return 0;
        const recent = entries.slice(-7);
        return recent.reduce((sum, e) => sum + e.mood, 0) / recent.length;
    }, [entries]);

    const handleSaveMood = useCallback(() => {
        if (selectedMood === null) return;

        const today = getToday();
        const newEntry: MoodEntry = {
            date: today,
            mood: selectedMood,
            note: note.trim() || undefined,
            timestamp: Date.now(),
        };

        const updated = entries.filter(e => e.date !== today);
        updated.push(newEntry);
        updated.sort((a, b) => a.date.localeCompare(b.date));

        setEntries(updated);
        saveEntries(updated);
        setSelectedMood(null);
        setNote('');
    }, [selectedMood, note, entries]);

    const handleEmojiClick = (value: number) => {
        setSelectedMood(value);
        setBouncing(value);
        setTimeout(() => setBouncing(null), 400);
    };

    if (!open) return null;

    return (
        <div
            className="fixed bottom-12 left-4 z-40 w-72 bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
            style={{ animation: 'moodIn 250ms cubic-bezier(0.34,1.56,0.64,1)' }}
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-gradient-to-r from-violet-500/10 to-pink-500/10">
                <div className="flex items-center gap-2">
                    <Heart className="w-4 h-4 text-pink-500" />
                    <span className="text-xs font-semibold text-foreground">Mood Journal</span>
                </div>
                <button
                    onClick={() => setOpen(false)}
                    className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors"
                >
                    <X className="w-3.5 h-3.5" />
                </button>
            </div>

            {/* Today's Mood */}
            <div className="px-4 py-4">
                {todayEntry ? (
                    <div className="text-center space-y-1">
                        <p className="text-xs text-muted-foreground">Today you feel</p>
                        <span className="text-4xl block" style={{ animation: 'moodPop 300ms ease-out' }}>
                            {MOODS.find(m => m.value === todayEntry.mood)?.emoji}
                        </span>
                        <p className="text-sm font-medium text-foreground">
                            {MOODS.find(m => m.value === todayEntry.mood)?.label}
                        </p>
                        {todayEntry.note && (
                            <p className="text-xs text-muted-foreground italic mt-1">"{todayEntry.note}"</p>
                        )}
                    </div>
                ) : (
                    <div className="space-y-3">
                        <p className="text-xs text-muted-foreground text-center">How are you feeling right now?</p>
                        <div className="flex items-center justify-center gap-2">
                            {MOODS.map(mood => (
                                <button
                                    key={mood.value}
                                    onClick={() => handleEmojiClick(mood.value)}
                                    className={cn(
                                        'w-10 h-10 rounded-xl flex items-center justify-center text-xl transition-all duration-200',
                                        selectedMood === mood.value
                                            ? `bg-gradient-to-br ${mood.color} scale-110 shadow-lg`
                                            : 'hover:bg-muted hover:scale-105',
                                        bouncing === mood.value && 'animate-mood-bounce'
                                    )}
                                    title={mood.label}
                                >
                                    {mood.emoji}
                                </button>
                            ))}
                        </div>

                        {selectedMood !== null && (
                            <div className="space-y-2" style={{ animation: 'moodSlideUp 200ms ease-out' }}>
                                <input
                                    type="text"
                                    value={note}
                                    onChange={(e) => setNote(e.target.value)}
                                    placeholder="Add a note (optional)..."
                                    className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-xs focus:outline-none focus:ring-2 focus:ring-primary/30 placeholder:text-muted-foreground"
                                    onKeyDown={(e) => e.key === 'Enter' && handleSaveMood()}
                                />
                                <button
                                    onClick={handleSaveMood}
                                    className="w-full py-2 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
                                >
                                    Save Mood
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Sparkline */}
            {last7Days.length >= 2 && (
                <div className="px-4 pb-3 space-y-2">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <TrendingUp className="w-3 h-3" />
                            <span>Last 7 days</span>
                        </div>
                        <span className="text-xs font-medium text-foreground">
                            Avg: {MOODS.find(m => m.value === Math.round(averageMood))?.emoji}
                        </span>
                    </div>
                    <div className="bg-secondary/50 rounded-lg p-3 flex justify-center">
                        <Sparkline data={last7Days} />
                    </div>
                </div>
            )}

            {/* Stats */}
            <div className="px-4 py-2.5 border-t border-border flex items-center justify-between text-[10px] text-muted-foreground">
                <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    <span>{entries.length} entries total</span>
                </div>
                <kbd className="px-1 py-0.5 bg-muted rounded font-mono">⌘E</kbd>
            </div>

            <style jsx>{`
                @keyframes moodIn {
                    from { opacity: 0; transform: translateY(10px) scale(0.95); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
                @keyframes moodPop {
                    0% { transform: scale(0.5); opacity: 0; }
                    60% { transform: scale(1.2); }
                    100% { transform: scale(1); opacity: 1; }
                }
                @keyframes moodSlideUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .animate-mood-bounce {
                    animation: moodBounce 400ms cubic-bezier(0.34, 1.56, 0.64, 1);
                }
                @keyframes moodBounce {
                    0% { transform: scale(1); }
                    30% { transform: scale(0.85); }
                    60% { transform: scale(1.15); }
                    100% { transform: scale(1.1); }
                }
            `}</style>
        </div>
    );
}
