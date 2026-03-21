'use client';

import { useState, useEffect } from 'react';
import { Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

const THINKING_MESSAGES = [
    'Analyzing your message...',
    'Applying your preferences...',
    'Crafting a thoughtful response...',
    'Checking learned patterns...',
    'Processing context...',
    'Personalizing the answer...',
];

export function ThinkingAnimation() {
    const [messageIndex, setMessageIndex] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setMessageIndex((prev) => (prev + 1) % THINKING_MESSAGES.length);
        }, 2000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex gap-4 animate-fade-in">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center mt-1 relative">
                <Sparkles className="w-4 h-4 text-primary animate-pulse" />
                <div
                    className="absolute inset-0 rounded-lg border-2 border-primary/20"
                    style={{ animation: 'thinkingRing 2s ease-in-out infinite' }}
                />
            </div>
            <div className="bg-secondary rounded-2xl px-4 py-3 max-w-xs relative overflow-hidden">
                {/* Shimmer effect */}
                <div
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/5 to-transparent"
                    style={{ animation: 'shimmer 2s ease-in-out infinite' }}
                />

                <div className="relative space-y-2">
                    {/* Dots */}
                    <div className="flex gap-1.5">
                        <div className="typing-dot" />
                        <div className="typing-dot" />
                        <div className="typing-dot" />
                    </div>

                    {/* Status message */}
                    <p
                        key={messageIndex}
                        className="text-xs text-muted-foreground"
                        style={{ animation: 'thinkingText 2s ease-in-out' }}
                    >
                        {THINKING_MESSAGES[messageIndex]}
                    </p>
                </div>
            </div>

            <style jsx>{`
                @keyframes thinkingRing {
                    0%, 100% { transform: scale(1); opacity: 0.3; }
                    50% { transform: scale(1.15); opacity: 0.6; }
                }
                @keyframes shimmer {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(100%); }
                }
                @keyframes thinkingText {
                    0% { opacity: 0; transform: translateY(4px); }
                    15% { opacity: 1; transform: translateY(0); }
                    85% { opacity: 1; transform: translateY(0); }
                    100% { opacity: 0; transform: translateY(-4px); }
                }
            `}</style>
        </div>
    );
}
