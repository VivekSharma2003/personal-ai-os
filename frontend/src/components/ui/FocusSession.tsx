'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Timer, X, Play, Pause, RotateCcw, Coffee, Brain, ChevronDown, Minimize2, Maximize2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-focus-stats';

interface FocusStats {
    totalMinutes: number;
    sessionsCompleted: number;
    lastSessionDate: string;
}

const PRESETS = [
    { label: '15 min', work: 15, break: 3, icon: '⚡' },
    { label: '25 min', work: 25, break: 5, icon: '🎯' },
    { label: '45 min', work: 45, break: 10, icon: '🔥' },
    { label: '60 min', work: 60, break: 15, icon: '💎' },
];

function loadStats(): FocusStats {
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : { totalMinutes: 0, sessionsCompleted: 0, lastSessionDate: '' };
    } catch {
        return { totalMinutes: 0, sessionsCompleted: 0, lastSessionDate: '' };
    }
}

function saveStats(stats: FocusStats) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stats));
}

// Simple beep using Web Audio API
function playBeep() {
    try {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 800;
        osc.type = 'sine';
        gain.gain.value = 0.3;
        osc.start();
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
        osc.stop(ctx.currentTime + 0.5);
    } catch {
        // Web Audio not available
    }
}

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

export function FocusSession() {
    const [open, setOpen] = useState(false);
    const [minimized, setMinimized] = useState(false);
    const [state, setState] = useState<'idle' | 'work' | 'break' | 'done'>('idle');
    const [preset, setPreset] = useState(PRESETS[1]); // default 25 min
    const [secondsLeft, setSecondsLeft] = useState(PRESETS[1].work * 60);
    const [totalSeconds, setTotalSeconds] = useState(PRESETS[1].work * 60);
    const [paused, setPaused] = useState(false);
    const [stats, setStats] = useState<FocusStats>(loadStats());
    const [showBreakOverlay, setShowBreakOverlay] = useState(false);

    const intervalRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('ai-os:open-focus-session', handler);
        return () => window.removeEventListener('ai-os:open-focus-session', handler);
    }, []);

    // Timer logic
    useEffect(() => {
        if (state === 'idle' || state === 'done' || paused) {
            if (intervalRef.current) clearInterval(intervalRef.current);
            return;
        }

        intervalRef.current = setInterval(() => {
            setSecondsLeft(prev => {
                if (prev <= 1) {
                    // Timer complete
                    playBeep();
                    if (state === 'work') {
                        // Work session done — show break
                        const newStats = {
                            ...stats,
                            totalMinutes: stats.totalMinutes + preset.work,
                            sessionsCompleted: stats.sessionsCompleted + 1,
                            lastSessionDate: new Date().toISOString(),
                        };
                        setStats(newStats);
                        saveStats(newStats);
                        setState('break');
                        setTotalSeconds(preset.break * 60);
                        setShowBreakOverlay(true);
                        setTimeout(() => setShowBreakOverlay(false), 5000);
                        return preset.break * 60;
                    } else {
                        // Break done
                        setState('done');
                        return 0;
                    }
                }
                return prev - 1;
            });
        }, 1000);

        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [state, paused, preset, stats]);

    const handleStart = useCallback((p: typeof PRESETS[0]) => {
        setPreset(p);
        setSecondsLeft(p.work * 60);
        setTotalSeconds(p.work * 60);
        setState('work');
        setPaused(false);
        setMinimized(true);
    }, []);

    const handleReset = useCallback(() => {
        setState('idle');
        setSecondsLeft(preset.work * 60);
        setTotalSeconds(preset.work * 60);
        setPaused(false);
        setMinimized(false);
    }, [preset]);

    const progress = totalSeconds > 0 ? ((totalSeconds - secondsLeft) / totalSeconds) * 100 : 0;

    // SVG ring dimensions
    const ringSize = 140;
    const strokeWidth = 6;
    const radius = (ringSize - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (progress / 100) * circumference;

    if (!open) return null;

    // Minimized floating widget
    if (minimized && (state === 'work' || state === 'break')) {
        return (
            <>
                {/* Break overlay */}
                {showBreakOverlay && (
                    <div className="fixed inset-0 z-[55] flex items-center justify-center" style={{ animation: 'fadeIn 300ms ease-out' }}>
                        <div className="absolute inset-0 bg-background/80 backdrop-blur-md" />
                        <div className="relative text-center z-10" style={{ animation: 'breakBounce 600ms cubic-bezier(0.34,1.56,0.64,1)' }}>
                            <Coffee className="w-16 h-16 text-amber-400 mx-auto mb-4" />
                            <h2 className="text-2xl font-bold text-foreground mb-2">Time for a Break!</h2>
                            <p className="text-muted-foreground">Take {preset.break} minutes to rest.</p>
                            <p className="text-sm text-muted-foreground/60 mt-3">Stretch, hydrate, breathe deeply 🧘</p>
                        </div>
                    </div>
                )}

                {/* Floating mini widget */}
                <div
                    className="fixed bottom-20 right-6 z-50 cursor-pointer group"
                    onClick={() => setMinimized(false)}
                    title="Click to expand"
                >
                    <div className={cn(
                        'relative w-14 h-14 rounded-full border-2 flex items-center justify-center bg-card shadow-xl transition-all',
                        state === 'work' ? 'border-primary/50' : 'border-amber-500/50',
                        'hover:scale-110 hover:shadow-2xl'
                    )}>
                        {/* Progress ring */}
                        <svg className="absolute inset-0 -rotate-90" width="56" height="56" viewBox="0 0 56 56">
                            <circle cx="28" cy="28" r="24" fill="none" stroke="currentColor" strokeWidth="3" className="text-border" />
                            <circle
                                cx="28" cy="28" r="24" fill="none"
                                strokeWidth="3"
                                strokeLinecap="round"
                                className={state === 'work' ? 'text-primary' : 'text-amber-400'}
                                style={{
                                    strokeDasharray: 2 * Math.PI * 24,
                                    strokeDashoffset: (2 * Math.PI * 24) - (progress / 100) * (2 * Math.PI * 24),
                                    transition: 'stroke-dashoffset 1s linear',
                                    stroke: 'currentColor',
                                }}
                            />
                        </svg>
                        <span className="text-[10px] font-bold tabular-nums text-foreground z-10">
                            {formatTime(secondsLeft)}
                        </span>
                    </div>
                </div>
            </>
        );
    }

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div
                className="absolute inset-0 bg-background/60 backdrop-blur-sm"
                onClick={() => { if (state === 'idle' || state === 'done') setOpen(false); }}
            />

            <div
                className="relative max-w-sm mx-auto mt-[15vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                style={{ animation: 'slideUp 200ms ease-out' }}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500/20 to-red-500/10 flex items-center justify-center">
                            <Brain className="w-4 h-4 text-orange-400" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-foreground">Focus Session</h2>
                            <p className="text-[10px] text-muted-foreground">
                                {stats.totalMinutes > 0
                                    ? `${Math.round(stats.totalMinutes / 60)}h ${stats.totalMinutes % 60}m total deep work`
                                    : 'Start your first session'
                                }
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-1">
                        {(state === 'work' || state === 'break') && (
                            <button
                                onClick={() => setMinimized(true)}
                                className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                                title="Minimize"
                            >
                                <Minimize2 className="w-4 h-4" />
                            </button>
                        )}
                        <button
                            onClick={() => { handleReset(); setOpen(false); }}
                            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {/* Timer */}
                <div className="flex flex-col items-center py-8 px-5">
                    {state === 'idle' ? (
                        <>
                            {/* Preset picker */}
                            <p className="text-xs text-muted-foreground mb-4 uppercase tracking-wider font-medium">Choose duration</p>
                            <div className="grid grid-cols-2 gap-2 w-full mb-6">
                                {PRESETS.map(p => (
                                    <button
                                        key={p.label}
                                        onClick={() => handleStart(p)}
                                        className={cn(
                                            'flex items-center gap-3 px-4 py-3 rounded-xl border text-left transition-all duration-200',
                                            'hover:bg-accent hover:border-primary/30 hover:shadow-md',
                                            'bg-secondary/50 border-border'
                                        )}
                                    >
                                        <span className="text-xl">{p.icon}</span>
                                        <div>
                                            <p className="text-sm font-semibold text-foreground">{p.label}</p>
                                            <p className="text-[10px] text-muted-foreground">{p.break}m break</p>
                                        </div>
                                    </button>
                                ))}
                            </div>

                            {/* Stats */}
                            {stats.sessionsCompleted > 0 && (
                                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                    <span className="flex items-center gap-1">
                                        <Timer className="w-3 h-3" />
                                        {stats.sessionsCompleted} sessions
                                    </span>
                                    <span className="w-px h-3 bg-border" />
                                    <span>{stats.totalMinutes} min total</span>
                                </div>
                            )}
                        </>
                    ) : (
                        <>
                            {/* Progress Ring */}
                            <div className="relative mb-6">
                                <svg width={ringSize} height={ringSize} className="-rotate-90">
                                    <circle
                                        cx={ringSize / 2}
                                        cy={ringSize / 2}
                                        r={radius}
                                        fill="none"
                                        stroke="hsl(var(--border))"
                                        strokeWidth={strokeWidth}
                                    />
                                    <circle
                                        cx={ringSize / 2}
                                        cy={ringSize / 2}
                                        r={radius}
                                        fill="none"
                                        strokeWidth={strokeWidth}
                                        strokeLinecap="round"
                                        className={state === 'work' ? 'text-primary' : 'text-amber-400'}
                                        style={{
                                            strokeDasharray: circumference,
                                            strokeDashoffset,
                                            transition: 'stroke-dashoffset 1s linear',
                                            stroke: 'currentColor',
                                        }}
                                    />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-3xl font-bold tabular-nums text-foreground">{formatTime(secondsLeft)}</span>
                                    <span className={cn(
                                        'text-[10px] font-medium uppercase tracking-wider mt-1',
                                        state === 'work' ? 'text-primary' : 'text-amber-400'
                                    )}>
                                        {state === 'work' ? 'Focus' : state === 'break' ? 'Break' : 'Done!'}
                                    </span>
                                </div>
                            </div>

                            {/* Controls */}
                            <div className="flex items-center gap-3">
                                <button
                                    onClick={() => setPaused(!paused)}
                                    className={cn(
                                        'w-12 h-12 rounded-full flex items-center justify-center transition-all',
                                        paused
                                            ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                                            : 'bg-secondary text-foreground hover:bg-accent'
                                    )}
                                >
                                    {paused ? <Play className="w-5 h-5 ml-0.5" /> : <Pause className="w-5 h-5" />}
                                </button>
                                <button
                                    onClick={handleReset}
                                    className="w-10 h-10 rounded-full bg-secondary text-muted-foreground hover:text-foreground hover:bg-accent flex items-center justify-center transition-colors"
                                    title="Reset"
                                >
                                    <RotateCcw className="w-4 h-4" />
                                </button>
                            </div>

                            {state === 'done' && (
                                <div className="mt-6 text-center" style={{ animation: 'slideUp 300ms ease-out' }}>
                                    <p className="text-lg font-bold text-foreground">🎉 Well done!</p>
                                    <p className="text-sm text-muted-foreground mt-1">Session complete. You&apos;ve earned a rest.</p>
                                    <button
                                        onClick={handleReset}
                                        className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                                    >
                                        Start Another
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>

            <style jsx>{`
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(10px) scale(0.98); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
                @keyframes breakBounce {
                    from { opacity: 0; transform: scale(0.5); }
                    to { opacity: 1; transform: scale(1); }
                }
            `}</style>
        </div>
    );
}
