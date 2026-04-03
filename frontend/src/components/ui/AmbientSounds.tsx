'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Volume2, VolumeX, X } from 'lucide-react';
import { cn } from '@/lib/utils';

type SoundType = 'rain' | 'cafe' | 'whitenoise' | 'fireplace';

interface SoundOption {
    id: SoundType;
    label: string;
    emoji: string;
}

const SOUND_OPTIONS: SoundOption[] = [
    { id: 'rain', label: 'Rain', emoji: '🌧️' },
    { id: 'cafe', label: 'Café', emoji: '☕' },
    { id: 'whitenoise', label: 'White Noise', emoji: '📻' },
    { id: 'fireplace', label: 'Fireplace', emoji: '🔥' },
];

function createNoiseGenerator(audioCtx: AudioContext, type: SoundType): { node: AudioNode; stop: () => void } {
    const bufferSize = 2 * audioCtx.sampleRate;
    const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    const data = buffer.getChannelData(0);

    // Generate different noise profiles
    if (type === 'rain' || type === 'whitenoise') {
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }
    } else if (type === 'cafe') {
        let prev = 0;
        for (let i = 0; i < bufferSize; i++) {
            const white = Math.random() * 2 - 1;
            data[i] = (prev + 0.02 * white) / 1.02;
            prev = data[i];
        }
    } else if (type === 'fireplace') {
        let prev = 0;
        for (let i = 0; i < bufferSize; i++) {
            const white = Math.random() * 2 - 1;
            data[i] = (prev + 0.1 * white) / 1.1;
            prev = data[i];
            // Add crackle
            if (Math.random() > 0.9998) {
                data[i] += (Math.random() - 0.5) * 0.5;
            }
        }
    }

    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.loop = true;

    // Apply filters based on type
    const filter = audioCtx.createBiquadFilter();
    if (type === 'rain') {
        filter.type = 'highpass';
        filter.frequency.value = 400;
    } else if (type === 'cafe') {
        filter.type = 'lowpass';
        filter.frequency.value = 800;
    } else if (type === 'fireplace') {
        filter.type = 'lowpass';
        filter.frequency.value = 600;
    } else {
        filter.type = 'lowpass';
        filter.frequency.value = 4000;
    }

    source.connect(filter);
    source.start();

    return {
        node: filter,
        stop: () => source.stop(),
    };
}

export function AmbientSounds() {
    const [open, setOpen] = useState(false);
    const [playing, setPlaying] = useState<SoundType | null>(null);
    const [volume, setVolume] = useState(0.3);
    const audioCtxRef = useRef<AudioContext | null>(null);
    const gainRef = useRef<GainNode | null>(null);
    const sourceRef = useRef<{ node: AudioNode; stop: () => void } | null>(null);

    // Open via ⌘M or custom event
    useEffect(() => {
        const handleKey = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'm') {
                e.preventDefault();
                setOpen((prev) => !prev);
            }
        };
        const handleCustom = () => setOpen(true);
        window.addEventListener('keydown', handleKey);
        window.addEventListener('ai-os:open-ambient', handleCustom);
        return () => {
            window.removeEventListener('keydown', handleKey);
            window.removeEventListener('ai-os:open-ambient', handleCustom);
        };
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            sourceRef.current?.stop();
            audioCtxRef.current?.close();
        };
    }, []);

    const startSound = useCallback((type: SoundType) => {
        // Stop existing
        sourceRef.current?.stop();

        if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
            audioCtxRef.current = new AudioContext();
        }

        const ctx = audioCtxRef.current;
        const gain = ctx.createGain();
        gain.gain.value = volume;
        gain.connect(ctx.destination);
        gainRef.current = gain;

        const source = createNoiseGenerator(ctx, type);
        source.node.connect(gain);
        sourceRef.current = source;
        setPlaying(type);
    }, [volume]);

    const stopSound = useCallback(() => {
        sourceRef.current?.stop();
        sourceRef.current = null;
        setPlaying(null);
    }, []);

    const handleVolumeChange = (v: number) => {
        setVolume(v);
        if (gainRef.current) {
            gainRef.current.gain.value = v;
        }
    };

    if (!open) return null;

    return (
        <div
            className="fixed bottom-12 left-4 z-40 w-64 bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
            style={{ animation: 'ambientIn 200ms ease-out' }}
        >
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
                <div className="flex items-center gap-2">
                    {playing ? <Volume2 className="w-4 h-4 text-primary" /> : <VolumeX className="w-4 h-4 text-muted-foreground" />}
                    <span className="text-xs font-semibold text-foreground">Ambient Sounds</span>
                </div>
                <button onClick={() => setOpen(false)} className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors">
                    <X className="w-3.5 h-3.5" />
                </button>
            </div>

            <div className="p-3 space-y-1">
                {SOUND_OPTIONS.map((sound) => (
                    <button
                        key={sound.id}
                        onClick={() => playing === sound.id ? stopSound() : startSound(sound.id)}
                        className={cn(
                            'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                            playing === sound.id ? 'bg-primary/10 text-primary' : 'hover:bg-accent text-foreground'
                        )}
                    >
                        <span className="text-base">{sound.emoji}</span>
                        <span className="flex-1 text-left text-xs font-medium">{sound.label}</span>
                        {playing === sound.id && (
                            <div className="flex gap-0.5">
                                {[1, 2, 3].map((i) => (
                                    <div
                                        key={i}
                                        className="w-0.5 bg-primary rounded-full"
                                        style={{
                                            height: '12px',
                                            animation: `soundBar 0.8s ease-in-out ${i * 0.15}s infinite alternate`,
                                        }}
                                    />
                                ))}
                            </div>
                        )}
                    </button>
                ))}
            </div>

            {/* Volume Slider */}
            <div className="px-4 pb-3">
                <div className="flex items-center gap-3">
                    <VolumeX className="w-3 h-3 text-muted-foreground" />
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={volume}
                        onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                        className="flex-1 h-1 accent-primary cursor-pointer"
                    />
                    <Volume2 className="w-3 h-3 text-muted-foreground" />
                </div>
            </div>

            <div className="px-4 py-2 border-t border-border text-center">
                <p className="text-[10px] text-muted-foreground">
                    <kbd className="px-1 py-0.5 bg-muted rounded font-mono">⌘M</kbd> to toggle
                </p>
            </div>

            <style jsx>{`
                @keyframes ambientIn {
                    from { opacity: 0; transform: translateY(10px) scale(0.95); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
                @keyframes soundBar {
                    from { height: 4px; }
                    to { height: 12px; }
                }
            `}</style>
        </div>
    );
}
