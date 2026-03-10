'use client';

import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';

const EMOJI_OPTIONS = ['👍', '❤️', '😂', '🎯', '🔥', '💡'];
const STORAGE_KEY = 'ai-os-reactions';

interface Reaction {
    emoji: string;
    count: number;
    reacted: boolean;
}

interface ReactionsMap {
    [messageId: string]: { [emoji: string]: boolean };
}

function getStoredReactions(): ReactionsMap {
    if (typeof window === 'undefined') return {};
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : {};
    } catch {
        return {};
    }
}

function saveReactions(reactions: ReactionsMap) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(reactions));
}

interface MessageReactionsProps {
    messageId: string;
}

export function MessageReactions({ messageId }: MessageReactionsProps) {
    const [reactions, setReactions] = useState<{ [emoji: string]: boolean }>({});
    const [showPicker, setShowPicker] = useState(false);

    // Load reactions for this message
    useEffect(() => {
        const stored = getStoredReactions();
        setReactions(stored[messageId] || {});
    }, [messageId]);

    const toggleReaction = useCallback((emoji: string) => {
        setReactions((prev) => {
            const updated = { ...prev };
            if (updated[emoji]) {
                delete updated[emoji];
            } else {
                updated[emoji] = true;
            }

            // Save to localStorage
            const allReactions = getStoredReactions();
            if (Object.keys(updated).length === 0) {
                delete allReactions[messageId];
            } else {
                allReactions[messageId] = updated;
            }
            saveReactions(allReactions);

            return updated;
        });
    }, [messageId]);

    const activeEmojis = Object.keys(reactions);

    return (
        <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
            {/* Active reactions */}
            {activeEmojis.map((emoji) => (
                <button
                    key={emoji}
                    onClick={() => toggleReaction(emoji)}
                    className={cn(
                        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs transition-all duration-200',
                        'bg-primary/10 border border-primary/20 hover:bg-primary/20',
                        'scale-100 hover:scale-105 active:scale-95'
                    )}
                    style={{ animation: 'reactionPop 200ms ease-out' }}
                >
                    <span>{emoji}</span>
                </button>
            ))}

            {/* Add reaction button */}
            <div className="relative">
                <button
                    onClick={() => setShowPicker(!showPicker)}
                    className={cn(
                        'inline-flex items-center justify-center w-6 h-6 rounded-full text-xs transition-all duration-200',
                        'text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted',
                        'opacity-0 group-hover:opacity-100',
                        (showPicker || activeEmojis.length > 0) && 'opacity-100'
                    )}
                    title="Add reaction"
                >
                    +
                </button>

                {showPicker && (
                    <>
                        <div
                            className="fixed inset-0 z-40"
                            onClick={() => setShowPicker(false)}
                        />
                        <div
                            className="absolute bottom-full left-0 mb-1 flex items-center gap-0.5 p-1.5 bg-card border border-border rounded-xl shadow-xl z-50"
                            style={{ animation: 'reactionPop 150ms ease-out' }}
                        >
                            {EMOJI_OPTIONS.map((emoji) => (
                                <button
                                    key={emoji}
                                    onClick={() => {
                                        toggleReaction(emoji);
                                        setShowPicker(false);
                                    }}
                                    className={cn(
                                        'w-8 h-8 rounded-lg flex items-center justify-center text-base hover:bg-accent transition-all duration-150',
                                        'hover:scale-125 active:scale-95',
                                        reactions[emoji] && 'bg-primary/10'
                                    )}
                                >
                                    {emoji}
                                </button>
                            ))}
                        </div>
                    </>
                )}
            </div>

            <style jsx>{`
                @keyframes reactionPop {
                    from { opacity: 0; transform: scale(0.8); }
                    to { opacity: 1; transform: scale(1); }
                }
            `}</style>
        </div>
    );
}
