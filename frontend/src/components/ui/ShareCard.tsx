'use client';

import { useState } from 'react';
import { Share2, X, Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const CARD_THEMES = [
    { id: 'dark', label: 'Dark', bg: 'bg-gradient-to-br from-gray-900 to-gray-800', text: 'text-white' },
    { id: 'ocean', label: 'Ocean', bg: 'bg-gradient-to-br from-blue-600 to-cyan-500', text: 'text-white' },
    { id: 'sunset', label: 'Sunset', bg: 'bg-gradient-to-br from-orange-500 to-pink-500', text: 'text-white' },
    { id: 'forest', label: 'Forest', bg: 'bg-gradient-to-br from-emerald-600 to-teal-500', text: 'text-white' },
    { id: 'purple', label: 'Purple', bg: 'bg-gradient-to-br from-violet-600 to-purple-500', text: 'text-white' },
    { id: 'light', label: 'Light', bg: 'bg-gradient-to-br from-gray-100 to-white', text: 'text-gray-900' },
];

interface ShareCardProps {
    content: string;
    role: 'user' | 'assistant';
}

export function ShareCardButton({ content, role }: ShareCardProps) {
    const [open, setOpen] = useState(false);
    const [activeTheme, setActiveTheme] = useState('dark');
    const [copied, setCopied] = useState(false);

    const theme = CARD_THEMES.find((t) => t.id === activeTheme) || CARD_THEMES[0];

    const handleCopy = async () => {
        const cardText = `💬 ${role === 'user' ? 'Question' : 'AI Response'}\n\n${content}\n\n— Personal AI OS`;
        await navigator.clipboard.writeText(cardText);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    return (
        <>
            <button
                onClick={() => setOpen(true)}
                className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-smooth"
                title="Share as card"
            >
                <Share2 className="w-3.5 h-3.5" />
            </button>

            {open && (
                <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
                    <div
                        className="absolute inset-0 bg-background/60 backdrop-blur-sm"
                        onClick={() => setOpen(false)}
                    />

                    <div
                        className="relative max-w-md mx-auto mt-[12vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                        style={{ animation: 'slideUp 200ms ease-out' }}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
                            <h3 className="text-sm font-semibold text-foreground">Share as Card</h3>
                            <button
                                onClick={() => setOpen(false)}
                                className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground transition-smooth"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Card Preview */}
                        <div className="p-5">
                            <div className={cn('rounded-xl p-6 shadow-lg', theme.bg, theme.text)}>
                                <div className="flex items-center gap-2 mb-3 opacity-70">
                                    <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center">
                                        <span className="text-[8px] font-bold">
                                            {role === 'user' ? 'U' : 'AI'}
                                        </span>
                                    </div>
                                    <span className="text-xs font-medium">
                                        {role === 'user' ? 'Question' : 'AI Response'}
                                    </span>
                                </div>
                                <p className="text-sm leading-relaxed line-clamp-6">
                                    {content}
                                </p>
                                <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between">
                                    <span className="text-[10px] opacity-50">Personal AI OS</span>
                                    <span className="text-[10px] opacity-50">
                                        {new Date().toLocaleDateString()}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Theme Picker */}
                        <div className="px-5 pb-3">
                            <div className="flex gap-2">
                                {CARD_THEMES.map((t) => (
                                    <button
                                        key={t.id}
                                        onClick={() => setActiveTheme(t.id)}
                                        className={cn(
                                            'w-8 h-8 rounded-lg transition-all',
                                            t.bg,
                                            activeTheme === t.id && 'ring-2 ring-primary ring-offset-2 ring-offset-card'
                                        )}
                                        title={t.label}
                                    />
                                ))}
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="px-5 pb-4">
                            <button
                                onClick={handleCopy}
                                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                            >
                                {copied ? (
                                    <>
                                        <Check className="w-4 h-4" />
                                        Copied!
                                    </>
                                ) : (
                                    <>
                                        <Copy className="w-4 h-4" />
                                        Copy to Clipboard
                                    </>
                                )}
                            </button>
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
            )}
        </>
    );
}
