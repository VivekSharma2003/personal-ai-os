'use client';

import { useState, useEffect } from 'react';
import { Palette, X, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-accent-color';

const ACCENT_COLORS = [
    { id: 'emerald', label: 'Emerald', hsl: '160 84% 39%', preview: 'bg-emerald-500' },
    { id: 'blue', label: 'Ocean Blue', hsl: '217 91% 60%', preview: 'bg-blue-500' },
    { id: 'violet', label: 'Violet', hsl: '263 70% 58%', preview: 'bg-violet-500' },
    { id: 'rose', label: 'Rose', hsl: '346 77% 55%', preview: 'bg-rose-500' },
    { id: 'amber', label: 'Amber', hsl: '38 92% 50%', preview: 'bg-amber-500' },
    { id: 'cyan', label: 'Cyan', hsl: '188 94% 43%', preview: 'bg-cyan-500' },
    { id: 'pink', label: 'Pink', hsl: '330 81% 60%', preview: 'bg-pink-500' },
    { id: 'lime', label: 'Lime', hsl: '85 78% 42%', preview: 'bg-lime-500' },
];

function getStoredAccent(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(STORAGE_KEY);
}

function applyAccent(colorId: string | null) {
    const color = colorId ? ACCENT_COLORS.find((c) => c.id === colorId) : null;
    const root = document.documentElement;

    if (color) {
        root.style.setProperty('--primary', color.hsl);
        root.style.setProperty('--ring', color.hsl);
    } else {
        // Reset to default emerald
        root.style.setProperty('--primary', '160 84% 39%');
        root.style.setProperty('--ring', '160 84% 39%');
    }
}

export function AccentPicker() {
    const [open, setOpen] = useState(false);
    const [activeId, setActiveId] = useState<string>('emerald');

    // Load and apply saved accent on mount
    useEffect(() => {
        const saved = getStoredAccent();
        if (saved) {
            setActiveId(saved);
            applyAccent(saved);
        }
    }, []);

    // Listen for open event from command palette
    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('ai-os:open-accent-picker', handler);
        return () => window.removeEventListener('ai-os:open-accent-picker', handler);
    }, []);

    const handleSelect = (colorId: string) => {
        setActiveId(colorId);
        applyAccent(colorId);
        localStorage.setItem(STORAGE_KEY, colorId);
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div
                className="absolute inset-0 bg-background/60 backdrop-blur-sm"
                onClick={() => setOpen(false)}
            />

            <div
                className="relative max-w-sm mx-auto mt-[20vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                style={{ animation: 'slideUp 200ms ease-out' }}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Palette className="w-4 h-4 text-primary" />
                        </div>
                        <h2 className="font-semibold text-foreground">Accent Color</h2>
                    </div>
                    <button
                        onClick={() => setOpen(false)}
                        className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-smooth"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Color Grid */}
                <div className="p-5">
                    <div className="grid grid-cols-4 gap-3">
                        {ACCENT_COLORS.map((color) => (
                            <button
                                key={color.id}
                                onClick={() => handleSelect(color.id)}
                                className={cn(
                                    'relative flex flex-col items-center gap-2 p-3 rounded-xl transition-all duration-200',
                                    'hover:bg-accent/50',
                                    activeId === color.id && 'bg-accent ring-2 ring-primary/30'
                                )}
                            >
                                <div className={cn('w-10 h-10 rounded-full shadow-sm relative', color.preview)}>
                                    {activeId === color.id && (
                                        <div className="absolute inset-0 flex items-center justify-center">
                                            <Check className="w-4 h-4 text-white" />
                                        </div>
                                    )}
                                </div>
                                <span className="text-[10px] text-muted-foreground font-medium">{color.label}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Preview bar */}
                <div className="px-5 pb-4">
                    <div className="bg-primary/10 rounded-lg p-3 flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-primary" />
                        <span className="text-sm text-primary font-medium">Preview — This is your accent color</span>
                    </div>
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
            `}</style>
        </div>
    );
}
