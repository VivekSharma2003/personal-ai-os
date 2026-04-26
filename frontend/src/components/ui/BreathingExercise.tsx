'use client';

import { useState, useEffect, useRef } from 'react';
import { X, Play, Pause, Wind } from 'lucide-react';
import { cn } from '@/lib/utils';

const PATTERNS = [
    { name: '4-7-8 Calm', inhale: 4, hold: 7, exhale: 8, color: 'from-blue-500 to-cyan-400', description: 'Relaxation & sleep' },
    { name: 'Box Breathing', inhale: 4, hold: 4, exhale: 4, holdOut: 4, color: 'from-violet-500 to-purple-400', description: 'Focus & clarity' },
    { name: 'Energize', inhale: 6, hold: 0, exhale: 2, color: 'from-orange-500 to-amber-400', description: 'Quick energy boost' },
    { name: 'Deep Calm', inhale: 5, hold: 5, exhale: 10, color: 'from-emerald-500 to-teal-400', description: 'Deep relaxation' },
];

type Phase = 'inhale' | 'hold' | 'exhale' | 'holdOut' | 'idle';

const PHASE_LABELS: Record<Phase, string> = {
    inhale: 'Breathe In',
    hold: 'Hold',
    exhale: 'Breathe Out',
    holdOut: 'Hold',
    idle: 'Ready',
};

export function BreathingExercise() {
    const [open, setOpen] = useState(false);
    const [selectedPattern, setSelectedPattern] = useState(PATTERNS[0]);
    const [running, setRunning] = useState(false);
    const [phase, setPhase] = useState<Phase>('idle');
    const [countdown, setCountdown] = useState(0);
    const [cycles, setCycles] = useState(0);
    const [scale, setScale] = useState(1);
    const timerRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('ai-os:open-breathing', handler);
        return () => window.removeEventListener('ai-os:open-breathing', handler);
    }, []);

    useEffect(() => {
        if (!running) {
            if (timerRef.current) clearInterval(timerRef.current);
            return;
        }

        const p = selectedPattern;
        const phases: { phase: Phase; duration: number }[] = [
            { phase: 'inhale', duration: p.inhale },
            ...(p.hold > 0 ? [{ phase: 'hold' as Phase, duration: p.hold }] : []),
            { phase: 'exhale', duration: p.exhale },
            ...((p as any).holdOut > 0 ? [{ phase: 'holdOut' as Phase, duration: (p as any).holdOut }] : []),
        ];

        let phaseIdx = 0;
        let secondsLeft = phases[0].duration;

        setPhase(phases[0].phase);
        setCountdown(secondsLeft);
        updateScale(phases[0].phase, phases[0].duration, secondsLeft);

        timerRef.current = setInterval(() => {
            secondsLeft--;

            if (secondsLeft <= 0) {
                phaseIdx++;
                if (phaseIdx >= phases.length) {
                    phaseIdx = 0;
                    setCycles(prev => prev + 1);
                }
                secondsLeft = phases[phaseIdx].duration;
                setPhase(phases[phaseIdx].phase);
            }

            setCountdown(secondsLeft);
            updateScale(phases[phaseIdx].phase, phases[phaseIdx].duration, secondsLeft);
        }, 1000);

        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [running, selectedPattern]);

    function updateScale(phase: Phase, total: number, remaining: number) {
        const progress = 1 - remaining / total;
        if (phase === 'inhale') {
            setScale(1 + 0.4 * progress); // grow from 1 to 1.4
        } else if (phase === 'exhale') {
            setScale(1.4 - 0.4 * progress); // shrink from 1.4 to 1
        } else if (phase === 'hold') {
            setScale(1.4);
        } else if (phase === 'holdOut') {
            setScale(1);
        }
    }

    const handleStop = () => {
        setRunning(false);
        setPhase('idle');
        setCountdown(0);
        setScale(1);
    };

    const handleStart = (pattern: typeof PATTERNS[0]) => {
        setSelectedPattern(pattern);
        setCycles(0);
        setRunning(true);
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div className="absolute inset-0 bg-background/80 backdrop-blur-md" onClick={() => { handleStop(); setOpen(false); }} />

            <div className="relative max-w-sm mx-auto mt-[12vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                style={{ animation: 'slideUp 200ms ease-out' }}>

                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/10 flex items-center justify-center">
                            <Wind className="w-4 h-4 text-cyan-400" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-foreground">Breathing Exercise</h2>
                            <p className="text-[10px] text-muted-foreground">{running ? `${selectedPattern.name} · ${cycles} cycles` : 'Choose a pattern'}</p>
                        </div>
                    </div>
                    <button onClick={() => { handleStop(); setOpen(false); }} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="p-5">
                    {!running ? (
                        /* Pattern Selector */
                        <div className="grid grid-cols-2 gap-2">
                            {PATTERNS.map(p => (
                                <button
                                    key={p.name}
                                    onClick={() => handleStart(p)}
                                    className="text-left p-3 rounded-xl border border-border hover:border-primary/30 hover:bg-accent/50 hover:shadow-md transition-all duration-200"
                                >
                                    <div className={cn('w-6 h-6 rounded-full bg-gradient-to-br mb-2', p.color)} />
                                    <p className="text-sm font-semibold text-foreground">{p.name}</p>
                                    <p className="text-[10px] text-muted-foreground mt-0.5">{p.description}</p>
                                    <p className="text-[9px] text-muted-foreground/50 mt-1">
                                        {p.inhale}s in · {p.hold > 0 ? `${p.hold}s hold · ` : ''}{p.exhale}s out{(p as any).holdOut ? ` · ${(p as any).holdOut}s hold` : ''}
                                    </p>
                                </button>
                            ))}
                        </div>
                    ) : (
                        /* Active breathing */
                        <div className="flex flex-col items-center py-4">
                            {/* Breathing circle */}
                            <div className="relative w-48 h-48 flex items-center justify-center mb-6">
                                {/* Outer glow ring */}
                                <div
                                    className={cn('absolute rounded-full bg-gradient-to-br opacity-20', selectedPattern.color)}
                                    style={{
                                        width: `${scale * 180}px`,
                                        height: `${scale * 180}px`,
                                        transition: 'width 1s ease-in-out, height 1s ease-in-out',
                                    }}
                                />
                                {/* Inner circle */}
                                <div
                                    className={cn('rounded-full bg-gradient-to-br flex flex-col items-center justify-center shadow-2xl', selectedPattern.color)}
                                    style={{
                                        width: `${scale * 140}px`,
                                        height: `${scale * 140}px`,
                                        transition: 'width 1s ease-in-out, height 1s ease-in-out',
                                    }}
                                >
                                    <span className="text-white text-3xl font-bold tabular-nums">{countdown}</span>
                                    <span className="text-white/80 text-xs font-medium mt-1">{PHASE_LABELS[phase]}</span>
                                </div>
                            </div>

                            {/* Controls */}
                            <div className="flex items-center gap-3">
                                <button
                                    onClick={handleStop}
                                    className="w-12 h-12 rounded-full bg-secondary text-foreground hover:bg-accent flex items-center justify-center transition-colors"
                                >
                                    <Pause className="w-5 h-5" />
                                </button>
                            </div>

                            <p className="text-xs text-muted-foreground mt-4">{cycles} cycle{cycles !== 1 ? 's' : ''} completed</p>
                        </div>
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
