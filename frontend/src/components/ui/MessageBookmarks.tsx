'use client';

import { useState, useEffect, useCallback } from 'react';
import { Bookmark, BookmarkCheck, X, MessageSquare, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-bookmarks';

interface BookmarkData {
    messageId: string;
    conversationId: string;
    conversationTitle: string;
    content: string;
    role: 'user' | 'assistant';
    createdAt: string;
}

function getStoredBookmarks(): BookmarkData[] {
    if (typeof window === 'undefined') return [];
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    } catch {
        return [];
    }
}

function saveBookmarks(bookmarks: BookmarkData[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(bookmarks));
}

// Hook for use in message components
export function useBookmarks() {
    const [bookmarks, setBookmarks] = useState<BookmarkData[]>([]);

    useEffect(() => {
        setBookmarks(getStoredBookmarks());
    }, []);

    const toggleBookmark = useCallback((data: Omit<BookmarkData, 'createdAt'>) => {
        setBookmarks((prev) => {
            const exists = prev.find((b) => b.messageId === data.messageId);
            let updated: BookmarkData[];
            if (exists) {
                updated = prev.filter((b) => b.messageId !== data.messageId);
            } else {
                updated = [...prev, { ...data, createdAt: new Date().toISOString() }];
            }
            saveBookmarks(updated);
            return updated;
        });
    }, []);

    const isBookmarked = useCallback((messageId: string) => {
        return bookmarks.some((b) => b.messageId === messageId);
    }, [bookmarks]);

    return { bookmarks, toggleBookmark, isBookmarked };
}

// Bookmark button for individual messages
export function BookmarkButton({
    messageId,
    conversationId,
    conversationTitle,
    content,
    role,
}: {
    messageId: string;
    conversationId: string;
    conversationTitle: string;
    content: string;
    role: 'user' | 'assistant';
}) {
    const { toggleBookmark, isBookmarked } = useBookmarks();
    const bookmarked = isBookmarked(messageId);

    return (
        <button
            onClick={() =>
                toggleBookmark({
                    messageId,
                    conversationId,
                    conversationTitle,
                    content: content.slice(0, 200),
                    role,
                })
            }
            className={cn(
                'p-1.5 rounded-md transition-smooth',
                bookmarked
                    ? 'text-amber-500 hover:bg-amber-500/10'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            )}
            title={bookmarked ? 'Remove bookmark' : 'Bookmark message'}
        >
            {bookmarked ? (
                <BookmarkCheck className="w-3.5 h-3.5" />
            ) : (
                <Bookmark className="w-3.5 h-3.5" />
            )}
        </button>
    );
}

// Bookmarks panel (can be used in sidebar or standalone)
export function BookmarksPanel({ onClose }: { onClose?: () => void }) {
    const { bookmarks, toggleBookmark } = useBookmarks();

    const handleJump = (bookmark: BookmarkData) => {
        window.dispatchEvent(
            new CustomEvent('ai-os:load-chat', { detail: { id: bookmark.conversationId } })
        );
        onClose?.();
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <div className="flex items-center gap-2">
                    <Bookmark className="w-4 h-4 text-amber-500" />
                    <h3 className="text-sm font-semibold text-foreground">Bookmarks</h3>
                    {bookmarks.length > 0 && (
                        <span className="text-xs text-muted-foreground">({bookmarks.length})</span>
                    )}
                </div>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-smooth"
                    >
                        <X className="w-4 h-4" />
                    </button>
                )}
            </div>

            {/* Bookmarks list */}
            <div className="flex-1 overflow-y-auto p-2">
                {bookmarks.length === 0 ? (
                    <div className="py-12 text-center">
                        <Bookmark className="w-8 h-8 text-muted-foreground/20 mx-auto mb-2" />
                        <p className="text-sm text-muted-foreground">No bookmarks yet</p>
                        <p className="text-xs text-muted-foreground/60 mt-1">
                            Hover a message and click the bookmark icon
                        </p>
                    </div>
                ) : (
                    bookmarks.map((bookmark) => (
                        <div
                            key={bookmark.messageId}
                            className="group flex items-start gap-3 px-3 py-3 rounded-lg hover:bg-accent/50 cursor-pointer transition-colors"
                            onClick={() => handleJump(bookmark)}
                        >
                            <div className={cn(
                                'w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5',
                                bookmark.role === 'user' ? 'bg-foreground/10' : 'bg-primary/10'
                            )}>
                                {bookmark.role === 'user' ? (
                                    <span className="text-[10px] font-medium">U</span>
                                ) : (
                                    <MessageSquare className="w-3 h-3 text-primary" />
                                )}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-xs font-medium text-primary/70 mb-0.5 flex items-center gap-1">
                                    {bookmark.conversationTitle}
                                    <ExternalLink className="w-2.5 h-2.5" />
                                </p>
                                <p className="text-xs text-foreground line-clamp-2 leading-relaxed">
                                    {bookmark.content}
                                </p>
                            </div>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    toggleBookmark(bookmark);
                                }}
                                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-amber-500/10 rounded transition-all flex-shrink-0"
                                title="Remove bookmark"
                            >
                                <X className="w-3 h-3 text-muted-foreground" />
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
