'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Tag } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-conversation-tags';

const TAG_COLORS = [
    { id: 'red', label: 'Red', dot: 'bg-red-500', bg: 'bg-red-500/10', border: 'border-red-500/30' },
    { id: 'yellow', label: 'Yellow', dot: 'bg-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/30' },
    { id: 'green', label: 'Green', dot: 'bg-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
    { id: 'blue', label: 'Blue', dot: 'bg-blue-500', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
    { id: 'purple', label: 'Purple', dot: 'bg-purple-500', bg: 'bg-purple-500/10', border: 'border-purple-500/30' },
];

interface TagsMap {
    [conversationId: string]: string; // color id
}

function getStoredTags(): TagsMap {
    if (typeof window === 'undefined') return {};
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : {};
    } catch {
        return {};
    }
}

function saveTags(tags: TagsMap) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tags));
}

// Hook for accessing tags
export function useConversationTags() {
    const [tags, setTags] = useState<TagsMap>({});

    useEffect(() => {
        setTags(getStoredTags());
    }, []);

    const setTag = useCallback((conversationId: string, colorId: string | null) => {
        setTags((prev) => {
            const updated = { ...prev };
            if (colorId === null) {
                delete updated[conversationId];
            } else {
                updated[conversationId] = colorId;
            }
            saveTags(updated);
            return updated;
        });
    }, []);

    const getTag = useCallback((conversationId: string) => {
        const colorId = tags[conversationId];
        return colorId ? TAG_COLORS.find((c) => c.id === colorId) || null : null;
    }, [tags]);

    return { tags, setTag, getTag };
}

// Tag dot indicator
export function TagDot({ conversationId }: { conversationId: string }) {
    const { getTag } = useConversationTags();
    const tag = getTag(conversationId);

    if (!tag) return null;

    return (
        <span
            className={cn('w-2 h-2 rounded-full flex-shrink-0', tag.dot)}
            style={{ animation: 'tagPop 200ms ease-out' }}
        />
    );
}

// Tag picker dropdown
export function TagPicker({
    conversationId,
    onClose,
}: {
    conversationId: string;
    onClose: () => void;
}) {
    const { getTag, setTag } = useConversationTags();
    const currentTag = getTag(conversationId);
    const pickerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
                onClose();
            }
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [onClose]);

    return (
        <div
            ref={pickerRef}
            className="absolute right-0 top-full mt-1 bg-card border border-border rounded-xl shadow-xl z-50 p-2 w-36"
            style={{ animation: 'tagPop 150ms ease-out' }}
        >
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-2 py-1 mb-1">
                Tag Color
            </p>
            {TAG_COLORS.map((color) => (
                <button
                    key={color.id}
                    onClick={() => {
                        setTag(conversationId, currentTag?.id === color.id ? null : color.id);
                        onClose();
                    }}
                    className={cn(
                        'w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-xs transition-colors',
                        'hover:bg-accent',
                        currentTag?.id === color.id && 'bg-accent'
                    )}
                >
                    <span className={cn('w-3 h-3 rounded-full', color.dot)} />
                    <span className="text-foreground">{color.label}</span>
                </button>
            ))}
            {currentTag && (
                <>
                    <div className="h-px bg-border my-1" />
                    <button
                        onClick={() => {
                            setTag(conversationId, null);
                            onClose();
                        }}
                        className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                    >
                        <Tag className="w-3 h-3" />
                        Remove tag
                    </button>
                </>
            )}

            <style jsx>{`
                @keyframes tagPop {
                    from { opacity: 0; transform: scale(0.9); }
                    to { opacity: 1; transform: scale(1); }
                }
            `}</style>
        </div>
    );
}
