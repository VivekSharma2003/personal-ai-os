'use client';

import { useState, useEffect, useMemo } from 'react';
import { Cloud, X, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';

const STOP_WORDS = new Set([
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
    'with', 'by', 'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall', 'should',
    'may', 'might', 'must', 'can', 'could', 'i', 'you', 'he', 'she', 'it', 'we',
    'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our',
    'their', 'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom',
    'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'not', 'only', 'same', 'so', 'than',
    'too', 'very', 'just', 'because', 'as', 'if', 'then', 'about', 'up', 'out',
    'into', 'through', 'from', 'after', 'before', 'between', 'under', 'over',
    'again', 'further', 'once', 'here', 'there', 'also', 'like', 'well', 'back',
    'still', 'even', 'way', 'much', 'get', 'got', 'make', 'made',
]);

const GRADIENT_COLORS = [
    'from-emerald-400 to-teal-500',
    'from-blue-400 to-indigo-500',
    'from-violet-400 to-purple-500',
    'from-rose-400 to-pink-500',
    'from-amber-400 to-orange-500',
    'from-cyan-400 to-sky-500',
    'from-fuchsia-400 to-pink-500',
    'from-lime-400 to-green-500',
];

interface WordEntry {
    word: string;
    count: number;
    size: number;
    color: string;
    rotation: number;
    delay: number;
    x: number;
    y: number;
}

function getAllWords(): Record<string, number> {
    const wordFreq: Record<string, number> = {};
    try {
        const data = localStorage.getItem('ai-os-conversations');
        if (!data) return wordFreq;
        const convos = JSON.parse(data);
        for (const convo of convos) {
            for (const msg of convo.messages || []) {
                const words = (msg.content || '')
                    .replace(/```[\s\S]*?```/g, '') // Remove code blocks
                    .replace(/`[^`]+`/g, '') // Remove inline code
                    .replace(/[^a-zA-Z\s]/g, '') // Remove non-alpha
                    .toLowerCase()
                    .split(/\s+/)
                    .filter((w: string) => w.length > 2 && !STOP_WORDS.has(w));

                for (const word of words) {
                    wordFreq[word] = (wordFreq[word] || 0) + 1;
                }
            }
        }
    } catch {
        // No conversations yet
    }
    return wordFreq;
}

export function WordCloud() {
    const [open, setOpen] = useState(false);
    const [tab, setTab] = useState<'cloud' | 'top'>('cloud');

    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('ai-os:open-wordcloud', handler);
        return () => window.removeEventListener('ai-os:open-wordcloud', handler);
    }, []);

    const wordEntries: WordEntry[] = useMemo(() => {
        if (!open) return [];
        const words = getAllWords();
        const sorted = Object.entries(words)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 60);

        if (sorted.length === 0) return [];

        const maxCount = sorted[0][1];
        const minCount = sorted[sorted.length - 1][1];
        const range = maxCount - minCount || 1;

        return sorted.map(([word, count], i) => {
            const normalized = (count - minCount) / range;
            const size = 14 + normalized * 36; // 14px to 50px
            const color = GRADIENT_COLORS[i % GRADIENT_COLORS.length];
            const rotation = (Math.random() - 0.5) * 30; // -15 to 15 degrees
            const delay = Math.random() * 2;
            // Distribute in a somewhat circular pattern
            const angle = (i / sorted.length) * Math.PI * 2;
            const radius = 20 + (1 - normalized) * 35;
            const x = 50 + Math.cos(angle) * radius;
            const y = 50 + Math.sin(angle) * radius;

            return { word, count, size, color, rotation, delay, x, y };
        });
    }, [open]);

    const topWords = useMemo(() => {
        return wordEntries.slice(0, 20);
    }, [wordEntries]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div
                className="absolute inset-0 bg-background/60 backdrop-blur-sm"
                onClick={() => setOpen(false)}
            />

            <div
                className="relative max-w-2xl mx-auto mt-[8vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden max-h-[80vh] flex flex-col"
                style={{ animation: 'slideUp 200ms ease-out' }}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-violet-500/10 flex items-center justify-center">
                            <Cloud className="w-5 h-5 text-blue-400" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-foreground">Word Cloud</h2>
                            <p className="text-xs text-muted-foreground">{wordEntries.length} unique words analyzed</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {/* Tabs */}
                        <div className="flex bg-secondary rounded-lg p-0.5">
                            <button
                                onClick={() => setTab('cloud')}
                                className={cn(
                                    'px-3 py-1 rounded-md text-xs font-medium transition-colors',
                                    tab === 'cloud' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'
                                )}
                            >
                                Cloud
                            </button>
                            <button
                                onClick={() => setTab('top')}
                                className={cn(
                                    'px-3 py-1 rounded-md text-xs font-medium transition-colors',
                                    tab === 'top' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'
                                )}
                            >
                                Top 20
                            </button>
                        </div>
                        <button
                            onClick={() => setOpen(false)}
                            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden">
                    {wordEntries.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-80 text-center">
                            <Cloud className="w-12 h-12 text-muted-foreground/20 mb-3" />
                            <p className="text-sm text-muted-foreground">No conversation data yet</p>
                            <p className="text-xs text-muted-foreground/60 mt-1">Start chatting to see your word cloud</p>
                        </div>
                    ) : tab === 'cloud' ? (
                        <div className="relative h-[400px] overflow-hidden">
                            {wordEntries.map((entry, i) => (
                                <span
                                    key={entry.word}
                                    className={cn(
                                        'absolute inline-block cursor-default select-none font-bold',
                                        'bg-clip-text text-transparent bg-gradient-to-r',
                                        entry.color,
                                        'hover:scale-125 transition-transform duration-300'
                                    )}
                                    style={{
                                        fontSize: `${entry.size}px`,
                                        left: `${entry.x}%`,
                                        top: `${entry.y}%`,
                                        transform: `translate(-50%, -50%) rotate(${entry.rotation}deg)`,
                                        animation: `wordFloat ${3 + entry.delay}s ease-in-out ${entry.delay}s infinite alternate`,
                                        opacity: 0.7 + (entry.size - 14) / 50 * 0.3,
                                    }}
                                    title={`"${entry.word}" — used ${entry.count} time${entry.count !== 1 ? 's' : ''}`}
                                >
                                    {entry.word}
                                </span>
                            ))}
                        </div>
                    ) : (
                        <div className="p-4 overflow-y-auto max-h-[400px]">
                            <div className="space-y-1.5">
                                {topWords.map((entry, i) => {
                                    const maxWidth = topWords[0]?.count || 1;
                                    const pct = (entry.count / maxWidth) * 100;
                                    return (
                                        <div
                                            key={entry.word}
                                            className="flex items-center gap-3 group"
                                            style={{ animation: `wordListIn 300ms ease-out ${i * 30}ms backwards` }}
                                        >
                                            <span className="w-5 text-right text-xs text-muted-foreground/50 tabular-nums font-mono">{i + 1}</span>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-0.5">
                                                    <span className="text-sm font-medium text-foreground truncate">{entry.word}</span>
                                                    <span className="text-[10px] text-muted-foreground tabular-nums">{entry.count}×</span>
                                                </div>
                                                <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                                                    <div
                                                        className={cn('h-full rounded-full bg-gradient-to-r', entry.color)}
                                                        style={{
                                                            width: `${pct}%`,
                                                            transition: 'width 700ms cubic-bezier(0.34,1.56,0.64,1)',
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
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
                @keyframes wordFloat {
                    from { transform: translate(-50%, -50%) translateY(0) rotate(var(--rot, 0deg)); }
                    to { transform: translate(-50%, -50%) translateY(-8px) rotate(var(--rot, 0deg)); }
                }
                @keyframes wordListIn {
                    from { opacity: 0; transform: translateX(-10px); }
                    to { opacity: 1; transform: translateX(0); }
                }
            `}</style>
        </div>
    );
}
