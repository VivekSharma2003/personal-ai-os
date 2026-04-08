'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { ThumbsUp, ThumbsDown, TrendingUp, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Rating {
    messageId: string;
    rating: 'up' | 'down';
    tags: string[];
    timestamp: number;
}

const STORAGE_KEY = 'ai-os-ratings';
const FEEDBACK_TAGS_UP = ['Helpful', 'Perfect', 'Creative', 'Accurate'];
const FEEDBACK_TAGS_DOWN = ['Too Long', 'Off Topic', 'Inaccurate', 'Too Short'];

function loadRatings(): Rating[] {
    if (typeof window === 'undefined') return [];
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch {
        return [];
    }
}

function saveRatings(ratings: Rating[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ratings));
}

// Inline rating buttons for each message
export function RatingButtons({ messageId }: { messageId: string }) {
    const [ratings, setRatings] = useState<Rating[]>([]);
    const [showTags, setShowTags] = useState(false);
    const [selectedRating, setSelectedRating] = useState<'up' | 'down' | null>(null);
    const [selectedTags, setSelectedTags] = useState<string[]>([]);

    useEffect(() => {
        setRatings(loadRatings());
    }, []);

    const existingRating = useMemo(
        () => ratings.find(r => r.messageId === messageId),
        [ratings, messageId]
    );

    const handleRate = useCallback((type: 'up' | 'down') => {
        if (existingRating) return; // Already rated

        setSelectedRating(type);
        setShowTags(true);
    }, [existingRating]);

    const handleSaveRating = useCallback(() => {
        if (!selectedRating) return;

        const newRating: Rating = {
            messageId,
            rating: selectedRating,
            tags: selectedTags,
            timestamp: Date.now(),
        };

        const all = loadRatings().filter(r => r.messageId !== messageId);
        all.push(newRating);
        saveRatings(all);
        setRatings(all);
        setShowTags(false);
        setSelectedTags([]);
    }, [messageId, selectedRating, selectedTags]);

    const toggleTag = (tag: string) => {
        setSelectedTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);
    };

    if (existingRating) {
        return (
            <div className="flex items-center gap-1.5">
                <div className={cn(
                    'flex items-center gap-1 px-2 py-1 rounded-md text-xs',
                    existingRating.rating === 'up'
                        ? 'bg-emerald-500/10 text-emerald-500'
                        : 'bg-red-500/10 text-red-400'
                )}>
                    {existingRating.rating === 'up' ? (
                        <ThumbsUp className="w-3 h-3" />
                    ) : (
                        <ThumbsDown className="w-3 h-3" />
                    )}
                    <span className="text-[10px] font-medium">
                        {existingRating.tags.length > 0 ? existingRating.tags[0] : (existingRating.rating === 'up' ? 'Liked' : 'Disliked')}
                    </span>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            <div className="flex items-center gap-1">
                <button
                    onClick={() => handleRate('up')}
                    className={cn(
                        'p-1.5 rounded-md transition-all duration-200',
                        selectedRating === 'up'
                            ? 'bg-emerald-500/20 text-emerald-500 scale-110'
                            : 'hover:bg-muted text-muted-foreground hover:text-emerald-500'
                    )}
                    title="Good response"
                >
                    <ThumbsUp className="w-3.5 h-3.5" />
                </button>
                <button
                    onClick={() => handleRate('down')}
                    className={cn(
                        'p-1.5 rounded-md transition-all duration-200',
                        selectedRating === 'down'
                            ? 'bg-red-500/20 text-red-400 scale-110'
                            : 'hover:bg-muted text-muted-foreground hover:text-red-400'
                    )}
                    title="Bad response"
                >
                    <ThumbsDown className="w-3.5 h-3.5" />
                </button>
            </div>

            {showTags && (
                <div className="space-y-2" style={{ animation: 'ratingSlide 200ms ease-out' }}>
                    <div className="flex flex-wrap gap-1">
                        {(selectedRating === 'up' ? FEEDBACK_TAGS_UP : FEEDBACK_TAGS_DOWN).map(tag => (
                            <button
                                key={tag}
                                onClick={() => toggleTag(tag)}
                                className={cn(
                                    'px-2 py-0.5 rounded-full text-[10px] font-medium border transition-all duration-150',
                                    selectedTags.includes(tag)
                                        ? selectedRating === 'up'
                                            ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
                                            : 'bg-red-500/20 border-red-500/40 text-red-400'
                                        : 'bg-muted/50 border-border text-muted-foreground hover:border-primary/30'
                                )}
                            >
                                {tag}
                            </button>
                        ))}
                    </div>
                    <button
                        onClick={handleSaveRating}
                        className="px-3 py-1 rounded-md bg-primary/10 text-primary text-[10px] font-medium hover:bg-primary/20 transition-colors"
                    >
                        Submit
                    </button>
                </div>
            )}

            <style jsx>{`
                @keyframes ratingSlide {
                    from { opacity: 0; transform: translateY(-4px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}

// Mini satisfaction sparkline for header
export function SatisfactionIndicator() {
    const [ratings, setRatings] = useState<Rating[]>([]);

    useEffect(() => {
        setRatings(loadRatings());

        // Poll for changes
        const interval = setInterval(() => {
            setRatings(loadRatings());
        }, 5000);
        return () => clearInterval(interval);
    }, []);

    const stats = useMemo(() => {
        if (ratings.length === 0) return null;
        const upCount = ratings.filter(r => r.rating === 'up').length;
        const total = ratings.length;
        const pct = Math.round((upCount / total) * 100);

        // Last 10 ratings as sparkline data
        const recent = ratings.slice(-10).map(r => r.rating === 'up' ? 1 : 0);

        return { upCount, total, pct, recent };
    }, [ratings]);

    if (!stats || stats.total < 2) return null;

    return (
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-secondary/50 border border-border/50">
            <BarChart3 className="w-3 h-3 text-muted-foreground" />
            <div className="flex items-center gap-1">
                {stats.recent.map((v, i) => (
                    <div
                        key={i}
                        className={cn(
                            'w-1 rounded-full transition-all',
                            v ? 'bg-emerald-500 h-3' : 'bg-red-400 h-1.5'
                        )}
                    />
                ))}
            </div>
            <span className={cn(
                'text-[10px] font-bold tabular-nums',
                stats.pct >= 70 ? 'text-emerald-500' : stats.pct >= 40 ? 'text-amber-500' : 'text-red-400'
            )}>
                {stats.pct}%
            </span>
        </div>
    );
}
