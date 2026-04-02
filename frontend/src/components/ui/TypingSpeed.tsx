'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { cn } from '@/lib/utils';

interface TypingSpeedProps {
    isTyping: boolean;
}

export function TypingSpeed({ isTyping }: TypingSpeedProps) {
    const [wpm, setWpm] = useState(0);
    const [visible, setVisible] = useState(false);
    const keyTimestamps = useRef<number[]>([]);
    const fadeTimeout = useRef<NodeJS.Timeout | null>(null);

    const handleKeyPress = useCallback(() => {
        const now = Date.now();
        keyTimestamps.current.push(now);

        // Keep only last 10 seconds of keystrokes
        const cutoff = now - 10000;
        keyTimestamps.current = keyTimestamps.current.filter((t) => t > cutoff);

        const timestamps = keyTimestamps.current;
        if (timestamps.length >= 2) {
            const duration = (timestamps[timestamps.length - 1] - timestamps[0]) / 1000; // seconds
            if (duration > 0) {
                // Average 5 chars per word
                const chars = timestamps.length;
                const wordsPerMinute = Math.round((chars / 5) / (duration / 60));
                setWpm(Math.min(wordsPerMinute, 200));
            }
        }

        setVisible(true);

        // Hide after 3 seconds of inactivity
        if (fadeTimeout.current) clearTimeout(fadeTimeout.current);
        fadeTimeout.current = setTimeout(() => {
            setVisible(false);
            setWpm(0);
            keyTimestamps.current = [];
        }, 3000);
    }, []);

    useEffect(() => {
        if (!isTyping) return;

        const handler = (e: KeyboardEvent) => {
            // Only count regular character keys
            if (e.key.length === 1 && !e.metaKey && !e.ctrlKey) {
                handleKeyPress();
            }
        };

        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [isTyping, handleKeyPress]);

    if (!visible || wpm === 0) return null;

    const getColor = () => {
        if (wpm < 30) return 'text-muted-foreground';
        if (wpm < 60) return 'text-amber-400';
        if (wpm < 90) return 'text-emerald-400';
        return 'text-primary';
    };

    return (
        <span
            className={cn('text-[10px] font-mono tabular-nums transition-colors', getColor())}
            style={{ animation: 'wpmIn 200ms ease-out' }}
        >
            {wpm} WPM
            <style jsx>{`
                @keyframes wpmIn {
                    from { opacity: 0; transform: translateY(2px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </span>
    );
}
