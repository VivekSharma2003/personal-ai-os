'use client';

import { useState, useEffect } from 'react';
import { Wallpaper, X, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-chat-bg';

interface BgTheme {
    id: string;
    label: string;
    style: string;
}

const BG_THEMES: BgTheme[] = [
    { id: 'default', label: 'Default', style: '' },
    {
        id: 'dots',
        label: 'Dots',
        style: 'background-image: radial-gradient(circle, hsl(var(--muted-foreground) / 0.07) 1px, transparent 1px); background-size: 20px 20px;',
    },
    {
        id: 'grid',
        label: 'Grid',
        style: 'background-image: linear-gradient(hsl(var(--border) / 0.3) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border) / 0.3) 1px, transparent 1px); background-size: 40px 40px;',
    },
    {
        id: 'gradient',
        label: 'Gradient',
        style: 'background: linear-gradient(135deg, hsl(var(--primary) / 0.03) 0%, hsl(var(--background)) 50%, hsl(var(--primary) / 0.05) 100%);',
    },
    {
        id: 'diagonal',
        label: 'Diagonal',
        style: 'background-image: repeating-linear-gradient(45deg, transparent, transparent 20px, hsl(var(--muted-foreground) / 0.03) 20px, hsl(var(--muted-foreground) / 0.03) 21px); background-size: 30px 30px;',
    },
    {
        id: 'minimal',
        label: 'Minimal',
        style: 'background-image: radial-gradient(circle at 50% 0%, hsl(var(--primary) / 0.04) 0%, transparent 60%);',
    },
];

function getStoredBg(): string {
    if (typeof window === 'undefined') return 'default';
    return localStorage.getItem(STORAGE_KEY) || 'default';
}

export function useChatBackground() {
    const [bgId, setBgId] = useState('default');

    useEffect(() => {
        setBgId(getStoredBg());
    }, []);

    const theme = BG_THEMES.find((t) => t.id === bgId) || BG_THEMES[0];
    return { bgStyle: theme.style, bgId };
}

export function ChatBackground() {
    const [open, setOpen] = useState(false);
    const [activeId, setActiveId] = useState('default');

    useEffect(() => {
        setActiveId(getStoredBg());
    }, []);

    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('ai-os:open-chat-bg', handler);
        return () => window.removeEventListener('ai-os:open-chat-bg', handler);
    }, []);

    const handleSelect = (id: string) => {
        setActiveId(id);
        localStorage.setItem(STORAGE_KEY, id);
        // Dispatch event to notify chat page
        window.dispatchEvent(new CustomEvent('ai-os:bg-changed', { detail: id }));
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
            <div
                className="relative max-w-sm mx-auto mt-[20vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                style={{ animation: 'slideUp 200ms ease-out' }}
            >
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <Wallpaper className="w-4 h-4 text-primary" />
                        <h2 className="font-semibold text-foreground text-sm">Chat Background</h2>
                    </div>
                    <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground transition-smooth">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="grid grid-cols-3 gap-3 p-5">
                    {BG_THEMES.map((theme) => (
                        <button
                            key={theme.id}
                            onClick={() => handleSelect(theme.id)}
                            className={cn(
                                'relative h-20 rounded-lg border-2 transition-all overflow-hidden',
                                activeId === theme.id ? 'border-primary shadow-md' : 'border-border hover:border-muted-foreground/30'
                            )}
                        >
                            <div
                                className="absolute inset-0 bg-background"
                                style={theme.style ? Object.fromEntries(
                                    theme.style.split(';').filter(Boolean).map(s => {
                                        const [k, ...v] = s.split(':');
                                        return [k.trim().replace(/-([a-z])/g, (_, c) => c.toUpperCase()), v.join(':').trim()];
                                    })
                                ) : undefined}
                            />
                            {activeId === theme.id && (
                                <div className="absolute top-1 right-1 w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                                    <Check className="w-2.5 h-2.5 text-primary-foreground" />
                                </div>
                            )}
                            <span className="absolute bottom-1 left-0 right-0 text-[9px] text-muted-foreground text-center font-medium">
                                {theme.label}
                            </span>
                        </button>
                    ))}
                </div>
            </div>

            <style jsx>{`
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                @keyframes slideUp { from { opacity: 0; transform: translateY(10px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
            `}</style>
        </div>
    );
}
