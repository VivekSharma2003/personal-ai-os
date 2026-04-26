'use client';

import { useState, useEffect } from 'react';
import { X, Plus, Trash2, CheckCircle2, Circle, Target } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-habits';

interface Habit {
    id: string;
    name: string;
    emoji: string;
    color: string;
    completions: Record<string, boolean>; // date string -> completed
    createdAt: string;
}

const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899', '#06b6d4', '#f97316'];
const EMOJIS = ['💪', '📚', '🏃', '💧', '🧘', '✍️', '🎯', '🌱', '💤', '🍎'];

function loadHabits(): Habit[] {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch { return []; }
}
function saveHabits(h: Habit[]) { localStorage.setItem(STORAGE_KEY, JSON.stringify(h)); }

function getDateKey(d: Date = new Date()): string {
    return d.toISOString().split('T')[0];
}

function getLast7Days(): string[] {
    const days: string[] = [];
    for (let i = 6; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        days.push(getDateKey(d));
    }
    return days;
}

function getDayLabel(dateStr: string): string {
    const d = new Date(dateStr);
    return ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()];
}

export function HabitTracker() {
    const [open, setOpen] = useState(false);
    const [habits, setHabits] = useState<Habit[]>([]);
    const [adding, setAdding] = useState(false);
    const [newName, setNewName] = useState('');
    const [newEmoji, setNewEmoji] = useState('💪');
    const [newColor, setNewColor] = useState(COLORS[0]);

    const today = getDateKey();
    const last7 = getLast7Days();

    useEffect(() => {
        const handler = () => { setOpen(true); setHabits(loadHabits()); };
        window.addEventListener('ai-os:open-habits', handler);
        return () => window.removeEventListener('ai-os:open-habits', handler);
    }, []);

    const toggleCompletion = (habitId: string, date: string) => {
        const updated = habits.map(h => {
            if (h.id !== habitId) return h;
            const completions = { ...h.completions };
            completions[date] = !completions[date];
            return { ...h, completions };
        });
        setHabits(updated);
        saveHabits(updated);
    };

    const addHabit = () => {
        if (!newName.trim()) return;
        const habit: Habit = {
            id: Date.now().toString(36),
            name: newName.trim(),
            emoji: newEmoji,
            color: newColor,
            completions: {},
            createdAt: new Date().toISOString(),
        };
        const updated = [...habits, habit];
        setHabits(updated);
        saveHabits(updated);
        setNewName('');
        setAdding(false);
    };

    const deleteHabit = (id: string) => {
        const updated = habits.filter(h => h.id !== id);
        setHabits(updated);
        saveHabits(updated);
    };

    // Stats
    const todayCompleted = habits.filter(h => h.completions[today]).length;
    const todayTotal = habits.length;
    const completionPct = todayTotal > 0 ? Math.round((todayCompleted / todayTotal) * 100) : 0;

    // SVG ring
    const ringR = 28;
    const ringC = 2 * Math.PI * ringR;
    const ringOffset = ringC - (completionPct / 100) * ringC;

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" onClick={() => setOpen(false)} />

            <div className="relative max-w-md mx-auto mt-[10vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                style={{ animation: 'slideUp 200ms ease-out' }}>

                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500/20 to-teal-500/10 flex items-center justify-center">
                            <Target className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-foreground">Habit Tracker</h2>
                            <p className="text-[10px] text-muted-foreground">{todayCompleted}/{todayTotal} done today</p>
                        </div>
                    </div>
                    <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="p-5 max-h-[65vh] overflow-y-auto">
                    {/* Today's progress ring */}
                    {habits.length > 0 && (
                        <div className="flex items-center gap-4 mb-5 p-3 rounded-xl bg-secondary/50 border border-border">
                            <div className="relative flex-shrink-0">
                                <svg width="70" height="70" className="-rotate-90">
                                    <circle cx="35" cy="35" r={ringR} fill="none" stroke="hsl(var(--border))" strokeWidth="5" />
                                    <circle cx="35" cy="35" r={ringR} fill="none" strokeWidth="5" strokeLinecap="round"
                                        className="text-emerald-500"
                                        style={{ strokeDasharray: ringC, strokeDashoffset: ringOffset, transition: 'stroke-dashoffset 500ms ease-out', stroke: 'currentColor' }}
                                    />
                                </svg>
                                <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-foreground">{completionPct}%</span>
                            </div>
                            <div>
                                <p className="text-sm font-semibold text-foreground">
                                    {completionPct === 100 ? '🎉 All done!' : completionPct >= 50 ? '💪 Halfway there!' : 'Keep going!'}
                                </p>
                                <p className="text-xs text-muted-foreground mt-0.5">{todayCompleted} of {todayTotal} habits completed today</p>
                            </div>
                        </div>
                    )}

                    {/* Habits list with 7-day grid */}
                    {habits.length === 0 ? (
                        <div className="text-center py-10">
                            <Target className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                            <p className="text-sm text-muted-foreground">No habits yet</p>
                            <p className="text-xs text-muted-foreground/60 mt-1">Start tracking your daily habits</p>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {/* Day labels */}
                            <div className="flex items-center gap-1 pl-[140px] mb-1">
                                {last7.map(d => (
                                    <div key={d} className={cn('w-7 text-center text-[9px] font-medium', d === today ? 'text-primary' : 'text-muted-foreground/60')}>
                                        {getDayLabel(d)}
                                    </div>
                                ))}
                            </div>

                            {habits.map(habit => (
                                <div key={habit.id} className="flex items-center gap-1 group">
                                    <div className="w-[130px] flex items-center gap-2 flex-shrink-0 pr-2">
                                        <span className="text-base">{habit.emoji}</span>
                                        <span className="text-xs font-medium text-foreground truncate">{habit.name}</span>
                                        <button onClick={() => deleteHabit(habit.id)} className="ml-auto p-0.5 text-muted-foreground/30 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all">
                                            <Trash2 className="w-3 h-3" />
                                        </button>
                                    </div>
                                    {last7.map(d => {
                                        const done = habit.completions[d];
                                        const isToday = d === today;
                                        return (
                                            <button
                                                key={d}
                                                onClick={() => toggleCompletion(habit.id, d)}
                                                className={cn('w-7 h-7 rounded-md flex items-center justify-center transition-all duration-200',
                                                    done ? 'scale-100' : 'hover:bg-muted',
                                                    isToday && !done && 'ring-1 ring-primary/30'
                                                )}
                                                style={done ? { backgroundColor: habit.color + '20' } : undefined}
                                            >
                                                {done ? (
                                                    <CheckCircle2 className="w-4 h-4" style={{ color: habit.color }} />
                                                ) : (
                                                    <Circle className="w-4 h-4 text-border" />
                                                )}
                                            </button>
                                        );
                                    })}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Add habit */}
                    {adding ? (
                        <div className="mt-4 p-3 rounded-xl border border-border bg-secondary/30 space-y-3" style={{ animation: 'slideUp 200ms ease-out' }}>
                            <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Habit name..."
                                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
                                autoFocus onKeyDown={e => e.key === 'Enter' && addHabit()}
                            />
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">Emoji:</span>
                                {EMOJIS.map(e => (
                                    <button key={e} onClick={() => setNewEmoji(e)}
                                        className={cn('text-base p-0.5 rounded', newEmoji === e && 'bg-primary/20 ring-1 ring-primary')}>
                                        {e}
                                    </button>
                                ))}
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">Color:</span>
                                {COLORS.map(c => (
                                    <button key={c} onClick={() => setNewColor(c)}
                                        className={cn('w-5 h-5 rounded-full transition-transform', newColor === c && 'scale-125 ring-2 ring-offset-2 ring-offset-card')}
                                        style={{ backgroundColor: c, ...(newColor === c ? { ringColor: c } : {}) }}
                                    />
                                ))}
                            </div>
                            <div className="flex gap-2">
                                <button onClick={addHabit} disabled={!newName.trim()}
                                    className="flex-1 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-40 transition-all">
                                    Add
                                </button>
                                <button onClick={() => setAdding(false)} className="px-4 py-2 rounded-lg bg-secondary text-foreground text-sm hover:bg-accent transition-colors">
                                    Cancel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <button onClick={() => setAdding(true)}
                            className="w-full mt-4 py-2 rounded-lg border border-dashed border-border text-sm text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-accent/50 transition-all flex items-center justify-center gap-2">
                            <Plus className="w-4 h-4" /> Add Habit
                        </button>
                    )}
                </div>
            </div>

            <style jsx>{`
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                @keyframes slideUp { from { opacity: 0; transform: translateY(10px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
            `}</style>
        </div>
    );
}
