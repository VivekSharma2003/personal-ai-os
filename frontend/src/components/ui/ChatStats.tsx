'use client';

import { useState, useEffect, useMemo } from 'react';
import { MessageSquare, Type, Clock, ChevronUp, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatStatsProps {
    messages: { role: string; content: string }[];
    sessionStart: number;
}

export function ChatStats({ messages, sessionStart }: ChatStatsProps) {
    const [expanded, setExpanded] = useState(false);
    const [elapsed, setElapsed] = useState(0);

    // Update elapsed time every second
    useEffect(() => {
        if (messages.length === 0) return;
        const interval = setInterval(() => {
            setElapsed(Math.floor((Date.now() - sessionStart) / 1000));
        }, 1000);
        return () => clearInterval(interval);
    }, [sessionStart, messages.length]);

    const stats = useMemo(() => {
        const totalMessages = messages.length;
        const userMessages = messages.filter((m) => m.role === 'user').length;
        const aiMessages = messages.filter((m) => m.role === 'assistant').length;
        const totalWords = messages.reduce((acc, m) => {
            return acc + (m.content.trim() ? m.content.trim().split(/\s+/).length : 0);
        }, 0);

        return { totalMessages, userMessages, aiMessages, totalWords };
    }, [messages]);

    const formatTime = (seconds: number) => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return m > 0 ? `${m}m ${s}s` : `${s}s`;
    };

    if (messages.length === 0) return null;

    return (
        <div
            className={cn(
                'border-b border-border bg-card/50 backdrop-blur-sm transition-all duration-300 overflow-hidden',
                expanded ? 'max-h-20' : 'max-h-8'
            )}
        >
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center justify-center gap-4 px-4 h-8 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
            >
                <span className="flex items-center gap-1.5">
                    <MessageSquare className="w-3 h-3" />
                    {stats.totalMessages} message{stats.totalMessages !== 1 ? 's' : ''}
                </span>
                <span className="flex items-center gap-1.5">
                    <Type className="w-3 h-3" />
                    {stats.totalWords.toLocaleString()} words
                </span>
                <span className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3" />
                    {formatTime(elapsed)}
                </span>
                {expanded ? (
                    <ChevronUp className="w-3 h-3 ml-auto" />
                ) : (
                    <ChevronDown className="w-3 h-3 ml-auto" />
                )}
            </button>

            {expanded && (
                <div
                    className="flex items-center justify-center gap-6 px-4 pb-2 text-[10px] text-muted-foreground/70"
                    style={{ animation: 'statsIn 200ms ease-out' }}
                >
                    <span>You: {stats.userMessages} messages</span>
                    <span className="w-px h-3 bg-border" />
                    <span>AI: {stats.aiMessages} messages</span>
                    <span className="w-px h-3 bg-border" />
                    <span>~{stats.totalWords > 0 ? Math.round(stats.totalWords / stats.totalMessages) : 0} words/msg</span>
                </div>
            )}

            <style jsx>{`
                @keyframes statsIn {
                    from { opacity: 0; transform: translateY(-4px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
