'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, MessageSquare, X, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ConversationMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
}

interface SearchResult {
    conversationId: string;
    title: string;
    message: ConversationMessage;
    matchIndex: number;
}

export function SpotlightSearch() {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);

    // Listen for open event
    useEffect(() => {
        const handleOpen = () => {
            setOpen(true);
            setQuery('');
            setResults([]);
            setSelectedIndex(0);
        };

        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'f') {
                e.preventDefault();
                handleOpen();
            }
            if (e.key === 'Escape' && open) {
                setOpen(false);
            }
        };

        window.addEventListener('ai-os:open-spotlight', handleOpen);
        window.addEventListener('keydown', handleKeyDown);
        return () => {
            window.removeEventListener('ai-os:open-spotlight', handleOpen);
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [open]);

    // Focus input when opened
    useEffect(() => {
        if (open) setTimeout(() => inputRef.current?.focus(), 50);
    }, [open]);

    // Search through localStorage conversations
    const performSearch = useCallback((q: string) => {
        if (q.length < 2) { setResults([]); return; }

        const stored = localStorage.getItem('ai-os-conversations');
        if (!stored) { setResults([]); return; }

        try {
            const convos: Record<string, { messages: ConversationMessage[]; title: string }> = JSON.parse(stored);
            const found: SearchResult[] = [];
            const lowerQ = q.toLowerCase();

            Object.entries(convos).forEach(([id, conv]) => {
                conv.messages.forEach((msg) => {
                    const idx = msg.content.toLowerCase().indexOf(lowerQ);
                    if (idx !== -1 && found.length < 20) {
                        found.push({
                            conversationId: id,
                            title: conv.title || 'Untitled Conversation',
                            message: msg,
                            matchIndex: idx,
                        });
                    }
                });
            });

            setResults(found);
            setSelectedIndex(0);
        } catch {
            setResults([]);
        }
    }, []);

    useEffect(() => {
        const timer = setTimeout(() => performSearch(query), 150);
        return () => clearTimeout(timer);
    }, [query, performSearch]);

    const handleSelect = (result: SearchResult) => {
        window.dispatchEvent(
            new CustomEvent('ai-os:load-chat', { detail: { id: result.conversationId } })
        );
        setOpen(false);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setSelectedIndex((prev) => Math.max(prev - 1, 0));
        } else if (e.key === 'Enter' && results[selectedIndex]) {
            e.preventDefault();
            handleSelect(results[selectedIndex]);
        }
    };

    // Highlight matching text
    const highlightMatch = (text: string, matchIdx: number, queryLen: number) => {
        const start = Math.max(0, matchIdx - 40);
        const end = Math.min(text.length, matchIdx + queryLen + 40);
        const snippet = (start > 0 ? '...' : '') + text.slice(start, end) + (end < text.length ? '...' : '');

        const relativeIdx = matchIdx - start + (start > 0 ? 3 : 0);
        const before = snippet.slice(0, relativeIdx);
        const match = snippet.slice(relativeIdx, relativeIdx + queryLen);
        const after = snippet.slice(relativeIdx + queryLen);

        return (
            <span className="text-xs text-muted-foreground">
                {before}
                <span className="bg-primary/20 text-primary font-medium rounded px-0.5">{match}</span>
                {after}
            </span>
        );
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50">
            <div
                className="absolute inset-0 bg-background/60 backdrop-blur-sm"
                onClick={() => setOpen(false)}
                style={{ animation: 'fadeIn 150ms ease-out' }}
            />

            <div className="relative max-w-2xl mx-auto mt-[15vh]" style={{ animation: 'slideUp 200ms ease-out' }}>
                <div className="bg-card border border-border rounded-xl shadow-2xl overflow-hidden">
                    {/* Search Input */}
                    <div className="flex items-center gap-3 px-4 border-b border-border">
                        <Search className="w-4 h-4 text-primary flex-shrink-0" />
                        <input
                            ref={inputRef}
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Search conversations..."
                            className="flex-1 py-3.5 bg-transparent text-foreground placeholder:text-muted-foreground text-sm focus:outline-none"
                        />
                        <button
                            onClick={() => setOpen(false)}
                            className="p-1 rounded hover:bg-muted transition-colors"
                        >
                            <X className="w-4 h-4 text-muted-foreground" />
                        </button>
                    </div>

                    {/* Results */}
                    <div className="max-h-[400px] overflow-y-auto p-2">
                        {query.length < 2 ? (
                            <div className="py-12 text-center">
                                <Search className="w-8 h-8 text-muted-foreground/30 mx-auto mb-3" />
                                <p className="text-sm text-muted-foreground">
                                    Type at least 2 characters to search
                                </p>
                                <p className="text-xs text-muted-foreground/60 mt-1">
                                    Searches through all conversation messages
                                </p>
                            </div>
                        ) : results.length === 0 ? (
                            <div className="py-12 text-center">
                                <p className="text-sm text-muted-foreground">No results found</p>
                                <p className="text-xs text-muted-foreground/60 mt-1">
                                    Try different keywords
                                </p>
                            </div>
                        ) : (
                            results.map((result, idx) => (
                                <button
                                    key={`${result.conversationId}-${result.message.id}`}
                                    onClick={() => handleSelect(result)}
                                    onMouseEnter={() => setSelectedIndex(idx)}
                                    className={cn(
                                        'w-full flex items-start gap-3 px-3 py-3 rounded-lg text-left transition-colors',
                                        idx === selectedIndex
                                            ? 'bg-primary/10'
                                            : 'hover:bg-accent/50'
                                    )}
                                >
                                    <div className={cn(
                                        'w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5',
                                        result.message.role === 'user'
                                            ? 'bg-foreground/10'
                                            : 'bg-primary/10'
                                    )}>
                                        {result.message.role === 'user' ? (
                                            <span className="text-[10px] font-medium text-foreground">U</span>
                                        ) : (
                                            <MessageSquare className="w-3 h-3 text-primary" />
                                        )}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-medium text-foreground mb-1 flex items-center gap-1.5">
                                            {result.title}
                                            <ArrowRight className="w-3 h-3 text-muted-foreground/40" />
                                        </p>
                                        {highlightMatch(result.message.content, result.matchIndex, query.length)}
                                    </div>
                                </button>
                            ))
                        )}
                    </div>

                    {/* Footer */}
                    <div className="px-4 py-2 border-t border-border flex items-center gap-4 text-[10px] text-muted-foreground">
                        <span className="flex items-center gap-1">
                            <kbd className="px-1 py-0.5 bg-muted rounded font-mono">↑↓</kbd> navigate
                        </span>
                        <span className="flex items-center gap-1">
                            <kbd className="px-1 py-0.5 bg-muted rounded font-mono">↵</kbd> open
                        </span>
                        <span className="flex items-center gap-1">
                            <kbd className="px-1 py-0.5 bg-muted rounded font-mono">esc</kbd> close
                        </span>
                        {results.length > 0 && (
                            <span className="ml-auto">{results.length} results</span>
                        )}
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
