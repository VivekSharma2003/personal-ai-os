'use client';

import { useState, useEffect, useCallback } from 'react';
import { ArrowDown, ArrowUp, ChevronsDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ScrollNavigatorProps {
    containerRef: React.RefObject<HTMLDivElement | null>;
    messageCount: number;
}

export function ScrollNavigator({ containerRef, messageCount }: ScrollNavigatorProps) {
    const [showScrollDown, setShowScrollDown] = useState(false);
    const [showScrollUp, setShowScrollUp] = useState(false);
    const [newMessageCount, setNewMessageCount] = useState(0);
    const [lastSeenCount, setLastSeenCount] = useState(0);

    const checkScroll = useCallback(() => {
        const el = containerRef.current;
        if (!el) return;

        const { scrollTop, scrollHeight, clientHeight } = el;
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
        const distanceFromTop = scrollTop;

        setShowScrollDown(distanceFromBottom > 150);
        setShowScrollUp(distanceFromTop > 300);

        // If at bottom, reset new message count
        if (distanceFromBottom < 50) {
            setLastSeenCount(messageCount);
            setNewMessageCount(0);
        }
    }, [containerRef, messageCount]);

    // Listen to scroll events
    useEffect(() => {
        const el = containerRef.current;
        if (!el) return;

        el.addEventListener('scroll', checkScroll, { passive: true });
        checkScroll();

        return () => el.removeEventListener('scroll', checkScroll);
    }, [containerRef, checkScroll]);

    // Track new messages when scrolled up
    useEffect(() => {
        if (showScrollDown && messageCount > lastSeenCount) {
            setNewMessageCount(messageCount - lastSeenCount);
        } else if (!showScrollDown) {
            setLastSeenCount(messageCount);
            setNewMessageCount(0);
        }
    }, [messageCount, showScrollDown, lastSeenCount]);

    const scrollToBottom = () => {
        containerRef.current?.scrollTo({
            top: containerRef.current.scrollHeight,
            behavior: 'smooth',
        });
    };

    const scrollToTop = () => {
        containerRef.current?.scrollTo({
            top: 0,
            behavior: 'smooth',
        });
    };

    return (
        <>
            {/* Scroll to top */}
            {showScrollUp && (
                <button
                    onClick={scrollToTop}
                    className={cn(
                        'absolute top-4 right-6 z-10 p-2 rounded-full',
                        'bg-card/90 border border-border shadow-lg backdrop-blur-sm',
                        'text-muted-foreground hover:text-foreground hover:bg-card',
                        'transition-all duration-200'
                    )}
                    style={{ animation: 'fabIn 200ms ease-out' }}
                    title="Scroll to top"
                >
                    <ArrowUp className="w-4 h-4" />
                </button>
            )}

            {/* Scroll to bottom */}
            {showScrollDown && (
                <button
                    onClick={scrollToBottom}
                    className={cn(
                        'absolute bottom-4 right-6 z-10 flex items-center gap-2 py-2 rounded-full',
                        'bg-card/90 border border-border shadow-lg backdrop-blur-sm',
                        'text-muted-foreground hover:text-foreground hover:bg-card',
                        'transition-all duration-200',
                        newMessageCount > 0 ? 'pl-3 pr-2' : 'px-2'
                    )}
                    style={{ animation: 'fabIn 200ms ease-out' }}
                    title="Scroll to bottom"
                >
                    {newMessageCount > 0 && (
                        <span className="text-xs font-medium text-primary">
                            {newMessageCount} new
                        </span>
                    )}
                    <div className="relative">
                        <ChevronsDown className="w-4 h-4" />
                        {newMessageCount > 0 && (
                            <span
                                className="absolute -top-1.5 -right-1.5 w-2 h-2 bg-primary rounded-full"
                                style={{ animation: 'pulse 2s ease-in-out infinite' }}
                            />
                        )}
                    </div>
                </button>
            )}

            <style jsx>{`
                @keyframes fabIn {
                    from { opacity: 0; transform: scale(0.8) translateY(8px); }
                    to { opacity: 1; transform: scale(1) translateY(0); }
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
            `}</style>
        </>
    );
}
