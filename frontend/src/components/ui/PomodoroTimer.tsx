'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Timer, Play, Pause, RotateCcw, X, Coffee } from 'lucide-react';
import { cn } from '@/lib/utils';

const WORK_DURATION = 25 * 60; // 25 minutes
const BREAK_DURATION = 5 * 60; // 5 minutes

type TimerPhase = 'work' | 'break';

export function PomodoroTimer() {
    const [open, setOpen] = useState(false);
    const [running, setRunning] = useState(false);
    const [timeLeft, setTimeLeft] = useState(WORK_DURATION);
    const [phase, setPhase] = useState<TimerPhase>('work');
    const intervalRef = useRef<NodeJS.Timeout | null>(null);

    // Keyboard shortcut ⌘P
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'p') {
                e.preventDefault();
                setOpen((prev) => !prev);
            }
        };
        const handleCustom = () => setOpen(true);
        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('ai-os:open-pomodoro', handleCustom);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('ai-os:open-pomodoro', handleCustom);
        };
    }, []);

    // Timer logic
    useEffect(() => {
        if (running) {
            intervalRef.current = setInterval(() => {
                setTimeLeft((prev) => {
                    if (prev <= 1) {
                        // Phase complete
                        try {
                            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdH2JkZeWk4+LhX93cGhiXF1iaG90fIKGiYqKiYiGhIB8d3JtaGRhYGFjZmltcHR3eXp7e3t7');
                            audio.volume = 0.3;
                            audio.play().catch(() => {});
                        } catch {}
                        
                        if (phase === 'work') {
                            setPhase('break');
                            return BREAK_DURATION;
                        } else {
                            setPhase('work');
                            setRunning(false);
                            return WORK_DURATION;
                        }
                    }
                    return prev - 1;
                });
            }, 1000);
        }
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [running, phase]);

    const handleReset = useCallback(() => {
        setRunning(false);
        setPhase('work');
        setTimeLeft(WORK_DURATION);
    }, []);

    const formatTime = (seconds: number) => {
        const m = Math.floor(seconds / 60).toString().padStart(2, '0');
        const s = (seconds % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    };

    const totalDuration = phase === 'work' ? WORK_DURATION : BREAK_DURATION;
    const progress = ((totalDuration - timeLeft) / totalDuration) * 100;

    if (!open) return null;

    return (
        <div
            className="fixed bottom-12 right-4 z-40 w-64 bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
            style={{ animation: 'pomodoroIn 200ms ease-out' }}
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
                <div className="flex items-center gap-2">
                    {phase === 'work' ? (
                        <Timer className="w-4 h-4 text-primary" />
                    ) : (
                        <Coffee className="w-4 h-4 text-amber-400" />
                    )}
                    <span className="text-xs font-semibold text-foreground">
                        {phase === 'work' ? 'Focus Time' : 'Break Time'}
                    </span>
                </div>
                <button
                    onClick={() => setOpen(false)}
                    className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors"
                >
                    <X className="w-3.5 h-3.5" />
                </button>
            </div>

            {/* Timer */}
            <div className="px-4 py-5 text-center">
                <div className="relative w-32 h-32 mx-auto">
                    {/* Progress ring */}
                    <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                        <circle
                            cx="50" cy="50" r="44"
                            fill="none"
                            stroke="hsl(var(--muted))"
                            strokeWidth="4"
                        />
                        <circle
                            cx="50" cy="50" r="44"
                            fill="none"
                            stroke={phase === 'work' ? 'hsl(var(--primary))' : 'hsl(38 92% 50%)'}
                            strokeWidth="4"
                            strokeLinecap="round"
                            strokeDasharray={`${2 * Math.PI * 44}`}
                            strokeDashoffset={`${2 * Math.PI * 44 * (1 - progress / 100)}`}
                            className="transition-all duration-1000"
                        />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-2xl font-mono font-bold text-foreground">
                            {formatTime(timeLeft)}
                        </span>
                        <span className="text-[10px] text-muted-foreground uppercase mt-0.5">
                            {phase === 'work' ? 'focus' : 'break'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-3 px-4 pb-4">
                <button
                    onClick={handleReset}
                    className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                    title="Reset"
                >
                    <RotateCcw className="w-4 h-4" />
                </button>
                <button
                    onClick={() => setRunning(!running)}
                    className={cn(
                        'p-3 rounded-full transition-colors',
                        running
                            ? 'bg-muted hover:bg-muted/80 text-foreground'
                            : 'bg-primary hover:bg-primary/90 text-primary-foreground'
                    )}
                >
                    {running ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                </button>
                <div className="w-8" /> {/* Spacer for symmetry */}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-border text-center">
                <p className="text-[10px] text-muted-foreground">
                    <kbd className="px-1 py-0.5 bg-muted rounded font-mono">⌘P</kbd> to toggle
                </p>
            </div>

            <style jsx>{`
                @keyframes pomodoroIn {
                    from { opacity: 0; transform: translateY(10px) scale(0.95); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
            `}</style>
        </div>
    );
}
