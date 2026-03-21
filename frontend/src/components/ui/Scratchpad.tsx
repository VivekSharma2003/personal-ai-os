'use client';

import { useState, useEffect, useRef } from 'react';
import { StickyNote, X, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-scratchpad';

function getStoredNotes(): string {
    if (typeof window === 'undefined') return '';
    return localStorage.getItem(STORAGE_KEY) || '';
}

export function Scratchpad() {
    const [open, setOpen] = useState(false);
    const [content, setContent] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const saveTimeout = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        setContent(getStoredNotes());
    }, []);

    // Keyboard shortcut ⌘J
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'j') {
                e.preventDefault();
                setOpen((prev) => !prev);
            }
            if (e.key === 'Escape' && open) {
                setOpen(false);
            }
        };

        const handleCustom = () => setOpen(true);

        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('ai-os:open-scratchpad', handleCustom);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('ai-os:open-scratchpad', handleCustom);
        };
    }, [open]);

    // Focus textarea when opening
    useEffect(() => {
        if (open) {
            setTimeout(() => textareaRef.current?.focus(), 100);
        }
    }, [open]);

    const handleChange = (value: string) => {
        setContent(value);
        // Debounced save
        if (saveTimeout.current) clearTimeout(saveTimeout.current);
        saveTimeout.current = setTimeout(() => {
            localStorage.setItem(STORAGE_KEY, value);
        }, 300);
    };

    const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div
                className="absolute inset-0 bg-background/40 backdrop-blur-sm"
                onClick={() => setOpen(false)}
            />

            <div
                className="absolute right-4 top-16 bottom-16 w-80 bg-card border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden"
                style={{ animation: 'slideRight 200ms ease-out' }}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                    <div className="flex items-center gap-2">
                        <StickyNote className="w-4 h-4 text-amber-400" />
                        <h3 className="text-sm font-semibold text-foreground">Scratchpad</h3>
                    </div>
                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => {
                                setContent('');
                                localStorage.setItem(STORAGE_KEY, '');
                            }}
                            className="p-1.5 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-smooth"
                            title="Clear all"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                            onClick={() => setOpen(false)}
                            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-smooth"
                        >
                            <X className="w-3.5 h-3.5" />
                        </button>
                    </div>
                </div>

                {/* Editor */}
                <textarea
                    ref={textareaRef}
                    value={content}
                    onChange={(e) => handleChange(e.target.value)}
                    placeholder="Jot down quick notes while chatting..."
                    className="flex-1 w-full p-4 bg-transparent text-sm text-foreground resize-none focus:outline-none placeholder:text-muted-foreground/40 leading-relaxed"
                />

                {/* Footer */}
                <div className="flex items-center justify-between px-4 py-2 border-t border-border text-[10px] text-muted-foreground">
                    <span>{wordCount} word{wordCount !== 1 ? 's' : ''} · {content.length} char{content.length !== 1 ? 's' : ''}</span>
                    <span>
                        <kbd className="px-1 py-0.5 bg-muted rounded font-mono">⌘J</kbd> to toggle
                    </span>
                </div>
            </div>

            <style jsx>{`
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes slideRight {
                    from { opacity: 0; transform: translateX(20px); }
                    to { opacity: 1; transform: translateX(0); }
                }
            `}</style>
        </div>
    );
}
