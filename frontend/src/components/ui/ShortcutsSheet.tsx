'use client';

import { useState, useEffect } from 'react';
import { X, Keyboard } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ShortcutGroup {
    title: string;
    shortcuts: { keys: string[]; description: string }[];
}

const SHORTCUT_GROUPS: ShortcutGroup[] = [
    {
        title: 'General',
        shortcuts: [
            { keys: ['⌘', 'K'], description: 'Open Command Palette' },
            { keys: ['⌘', '/'], description: 'Show Keyboard Shortcuts' },
            { keys: ['⌘', '.'], description: 'Toggle Focus Mode' },
            { keys: ['⌘', '⇧', 'F'], description: 'Search Conversations' },
        ],
    },
    {
        title: 'Chat',
        shortcuts: [
            { keys: ['Enter'], description: 'Send message' },
            { keys: ['⇧', 'Enter'], description: 'New line' },
            { keys: ['⌘', 'N'], description: 'New conversation' },
        ],
    },
    {
        title: 'Navigation',
        shortcuts: [
            { keys: ['↑', '↓'], description: 'Navigate items (in palettes)' },
            { keys: ['Enter'], description: 'Select item' },
            { keys: ['Esc'], description: 'Close overlay / Cancel' },
        ],
    },
];

export function ShortcutsSheet() {
    const [open, setOpen] = useState(false);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === '/') {
                e.preventDefault();
                setOpen((prev) => !prev);
            }
            if (e.key === 'Escape' && open) {
                setOpen(false);
            }
        };

        const handleCustom = () => setOpen(true);

        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('ai-os:open-shortcuts', handleCustom);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('ai-os:open-shortcuts', handleCustom);
        };
    }, [open]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div
                className="absolute inset-0 bg-background/60 backdrop-blur-sm"
                onClick={() => setOpen(false)}
            />

            <div
                className="relative max-w-md mx-auto mt-[15vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                style={{ animation: 'slideUp 200ms ease-out' }}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Keyboard className="w-4 h-4 text-primary" />
                        </div>
                        <h2 className="font-semibold text-foreground">Keyboard Shortcuts</h2>
                    </div>
                    <button
                        onClick={() => setOpen(false)}
                        className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-smooth"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Shortcuts */}
                <div className="p-4 space-y-5 max-h-[400px] overflow-y-auto">
                    {SHORTCUT_GROUPS.map((group) => (
                        <div key={group.title}>
                            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2.5 px-1">
                                {group.title}
                            </p>
                            <div className="space-y-1">
                                {group.shortcuts.map((shortcut) => (
                                    <div
                                        key={shortcut.description}
                                        className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-accent/50 transition-colors"
                                    >
                                        <span className="text-sm text-foreground">{shortcut.description}</span>
                                        <div className="flex items-center gap-1">
                                            {shortcut.keys.map((key, i) => (
                                                <span key={i}>
                                                    <kbd className="px-2 py-1 min-w-[28px] text-center bg-muted border border-border/50 rounded-md text-xs font-mono text-muted-foreground shadow-sm">
                                                        {key}
                                                    </kbd>
                                                    {i < shortcut.keys.length - 1 && (
                                                        <span className="text-muted-foreground/30 mx-0.5">+</span>
                                                    )}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <div className="px-4 py-3 border-t border-border text-center">
                    <p className="text-xs text-muted-foreground">
                        Press <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">⌘/</kbd> to toggle this sheet
                    </p>
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
