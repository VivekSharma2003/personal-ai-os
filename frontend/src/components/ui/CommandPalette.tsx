'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Search, MessageSquare, BookOpen, Clock, Sun, Moon, Zap, X } from 'lucide-react';
import { useTheme } from '@/components/layout/ThemeProvider';
import { cn } from '@/lib/utils';

interface Command {
    id: string;
    label: string;
    description: string;
    icon: React.ElementType;
    action: () => void;
    shortcut?: string;
    category: string;
}

export function CommandPalette() {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [selectedIndex, setSelectedIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);
    const router = useRouter();
    const pathname = usePathname();
    const { theme, setTheme } = useTheme();

    const commands: Command[] = [
        {
            id: 'new-chat',
            label: 'New Chat',
            description: 'Start a new conversation',
            icon: MessageSquare,
            action: () => {
                // Dispatch custom event for the chat page to handle
                window.dispatchEvent(new CustomEvent('ai-os:new-chat'));
                if (pathname !== '/') router.push('/');
            },
            shortcut: '⌘N',
            category: 'Chat',
        },
        {
            id: 'go-chat',
            label: 'Go to Chat',
            description: 'Navigate to the chat interface',
            icon: MessageSquare,
            action: () => router.push('/'),
            category: 'Navigation',
        },
        {
            id: 'go-rules',
            label: 'Go to Rules',
            description: 'View and manage learned rules',
            icon: BookOpen,
            action: () => router.push('/rules'),
            category: 'Navigation',
        },
        {
            id: 'go-timeline',
            label: 'Go to Timeline',
            description: 'View activity timeline',
            icon: Clock,
            action: () => router.push('/timeline'),
            category: 'Navigation',
        },
        {
            id: 'toggle-theme',
            label: 'Toggle Theme',
            description: `Currently: ${theme}. Click to switch.`,
            icon: theme === 'dark' ? Moon : Sun,
            action: () => {
                const next = theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark';
                setTheme(next);
            },
            shortcut: '⌘⇧T',
            category: 'Settings',
        },
        {
            id: 'focus-input',
            label: 'Focus Chat Input',
            description: 'Jump to the chat input field',
            icon: Zap,
            action: () => {
                if (pathname !== '/') router.push('/');
                setTimeout(() => {
                    const input = document.querySelector('textarea[placeholder*="Message"]') as HTMLTextAreaElement;
                    input?.focus();
                }, 100);
            },
            shortcut: '/',
            category: 'Chat',
        },
    ];

    const filteredCommands = commands.filter(
        (cmd) =>
            cmd.label.toLowerCase().includes(query.toLowerCase()) ||
            cmd.description.toLowerCase().includes(query.toLowerCase()) ||
            cmd.category.toLowerCase().includes(query.toLowerCase())
    );

    // Group by category
    const grouped = filteredCommands.reduce((acc, cmd) => {
        if (!acc[cmd.category]) acc[cmd.category] = [];
        acc[cmd.category].push(cmd);
        return acc;
    }, {} as Record<string, Command[]>);

    const flatFiltered = filteredCommands;

    // Keyboard shortcut to open
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                setOpen((prev) => !prev);
                setQuery('');
                setSelectedIndex(0);
            }
            if (e.key === 'Escape' && open) {
                setOpen(false);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [open]);

    // Focus input when opened
    useEffect(() => {
        if (open) {
            setTimeout(() => inputRef.current?.focus(), 50);
        }
    }, [open]);

    // Keyboard navigation
    const handleKeyDown = useCallback(
        (e: React.KeyboardEvent) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex((prev) => Math.min(prev + 1, flatFiltered.length - 1));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex((prev) => Math.max(prev - 1, 0));
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (flatFiltered[selectedIndex]) {
                    flatFiltered[selectedIndex].action();
                    setOpen(false);
                }
            }
        },
        [flatFiltered, selectedIndex]
    );

    // Reset selection when query changes
    useEffect(() => {
        setSelectedIndex(0);
    }, [query]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-background/60 backdrop-blur-sm animate-fade-in"
                onClick={() => setOpen(false)}
            />

            {/* Dialog */}
            <div className="relative max-w-lg mx-auto mt-[20vh] animate-slide-up">
                <div className="bg-card border border-border rounded-xl shadow-2xl overflow-hidden">
                    {/* Search input */}
                    <div className="flex items-center gap-3 px-4 border-b border-border">
                        <Search className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                        <input
                            ref={inputRef}
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Type a command or search..."
                            className="flex-1 py-3.5 bg-transparent text-foreground placeholder:text-muted-foreground text-sm focus:outline-none"
                        />
                        <kbd className="hidden sm:flex items-center gap-1 px-1.5 py-0.5 bg-muted rounded text-2xs text-muted-foreground font-mono">
                            ESC
                        </kbd>
                    </div>

                    {/* Results */}
                    <div className="max-h-[300px] overflow-y-auto p-2">
                        {flatFiltered.length === 0 ? (
                            <div className="py-8 text-center text-sm text-muted-foreground">
                                No commands found
                            </div>
                        ) : (
                            Object.entries(grouped).map(([category, cmds]) => (
                                <div key={category}>
                                    <p className="px-3 py-1.5 text-2xs font-medium text-muted-foreground uppercase tracking-wider">
                                        {category}
                                    </p>
                                    {cmds.map((cmd) => {
                                        const idx = flatFiltered.indexOf(cmd);
                                        const Icon = cmd.icon;
                                        return (
                                            <button
                                                key={cmd.id}
                                                onClick={() => {
                                                    cmd.action();
                                                    setOpen(false);
                                                }}
                                                onMouseEnter={() => setSelectedIndex(idx)}
                                                className={cn(
                                                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors',
                                                    idx === selectedIndex
                                                        ? 'bg-primary/10 text-foreground'
                                                        : 'text-muted-foreground hover:bg-accent'
                                                )}
                                            >
                                                <Icon
                                                    className={cn(
                                                        'w-4 h-4 flex-shrink-0',
                                                        idx === selectedIndex
                                                            ? 'text-primary'
                                                            : 'text-muted-foreground'
                                                    )}
                                                />
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-sm font-medium truncate">{cmd.label}</p>
                                                    <p className="text-xs text-muted-foreground truncate">
                                                        {cmd.description}
                                                    </p>
                                                </div>
                                                {cmd.shortcut && (
                                                    <kbd className="px-1.5 py-0.5 bg-muted rounded text-2xs text-muted-foreground font-mono">
                                                        {cmd.shortcut}
                                                    </kbd>
                                                )}
                                            </button>
                                        );
                                    })}
                                </div>
                            ))
                        )}
                    </div>

                    {/* Footer */}
                    <div className="px-4 py-2 border-t border-border flex items-center gap-4 text-2xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                            <kbd className="px-1 py-0.5 bg-muted rounded font-mono">↑↓</kbd> navigate
                        </span>
                        <span className="flex items-center gap-1">
                            <kbd className="px-1 py-0.5 bg-muted rounded font-mono">↵</kbd> select
                        </span>
                        <span className="flex items-center gap-1">
                            <kbd className="px-1 py-0.5 bg-muted rounded font-mono">esc</kbd> close
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
