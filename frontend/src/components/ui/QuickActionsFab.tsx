'use client';

import { useState, useEffect, useRef } from 'react';
import { Plus, X, MessageSquare, Pin, Heart, Timer, Command } from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePathname, useRouter } from 'next/navigation';

interface FabAction {
    id: string;
    label: string;
    icon: React.ElementType;
    color: string;
    action: () => void;
}

export function QuickActionsFab() {
    const [expanded, setExpanded] = useState(false);
    const router = useRouter();
    const pathname = usePathname();
    const fabRef = useRef<HTMLDivElement>(null);

    const actions: FabAction[] = [
        {
            id: 'new-chat',
            label: 'New Chat',
            icon: MessageSquare,
            color: 'from-emerald-500 to-teal-600',
            action: () => {
                window.dispatchEvent(new CustomEvent('ai-os:new-chat'));
                if (pathname !== '/') router.push('/');
            },
        },
        {
            id: 'pinboard',
            label: 'Pinboard',
            icon: Pin,
            color: 'from-blue-500 to-indigo-600',
            action: () => window.dispatchEvent(new CustomEvent('ai-os:open-pinboard')),
        },
        {
            id: 'mood',
            label: 'Mood',
            icon: Heart,
            color: 'from-rose-500 to-pink-600',
            action: () => window.dispatchEvent(new CustomEvent('ai-os:open-mood')),
        },
        {
            id: 'focus',
            label: 'Focus',
            icon: Timer,
            color: 'from-orange-500 to-red-600',
            action: () => window.dispatchEvent(new CustomEvent('ai-os:open-focus-session')),
        },
        {
            id: 'commands',
            label: 'Commands',
            icon: Command,
            color: 'from-violet-500 to-purple-600',
            action: () => {
                const e = new KeyboardEvent('keydown', { key: 'k', metaKey: true, bubbles: true });
                window.dispatchEvent(e);
            },
        },
    ];

    // Close on outside click
    useEffect(() => {
        if (!expanded) return;
        const handler = (e: MouseEvent) => {
            if (fabRef.current && !fabRef.current.contains(e.target as Node)) {
                setExpanded(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [expanded]);

    // Close on Escape
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && expanded) setExpanded(false);
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [expanded]);

    return (
        <div ref={fabRef} className="fixed bottom-12 right-6 z-40">
            {/* Action buttons - arranged in an arc */}
            {expanded && (
                <div className="absolute bottom-16 right-0" style={{ animation: 'fabContainerIn 200ms ease-out' }}>
                    {actions.map((action, i) => {
                        const total = actions.length;
                        // Arc from bottom-right upward
                        const angle = (Math.PI / 2) * (i / (total - 1)); // 0 to 90 degrees
                        const radius = 80;
                        const x = -Math.cos(angle) * radius;
                        const y = -Math.sin(angle) * radius;
                        const Icon = action.icon;

                        return (
                            <div
                                key={action.id}
                                className="absolute"
                                style={{
                                    right: -x,
                                    bottom: -y,
                                    animation: `fabItemIn 300ms cubic-bezier(0.34,1.56,0.64,1) ${i * 50}ms backwards`,
                                }}
                            >
                                {/* Tooltip */}
                                <div className="absolute right-full mr-2 top-1/2 -translate-y-1/2 whitespace-nowrap">
                                    <span className="px-2 py-1 rounded-md bg-card border border-border text-xs text-foreground shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none"
                                        style={{ opacity: 1 }}
                                    >
                                        {action.label}
                                    </span>
                                </div>

                                <button
                                    onClick={() => {
                                        action.action();
                                        setExpanded(false);
                                    }}
                                    className={cn(
                                        'w-10 h-10 rounded-full flex items-center justify-center shadow-lg',
                                        'bg-gradient-to-br text-white',
                                        'hover:scale-110 hover:shadow-xl active:scale-95 transition-all duration-200',
                                        action.color
                                    )}
                                    title={action.label}
                                >
                                    <Icon className="w-4 h-4" />
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Main FAB button */}
            <button
                onClick={() => setExpanded(!expanded)}
                className={cn(
                    'w-12 h-12 rounded-full flex items-center justify-center shadow-xl',
                    'bg-gradient-to-br from-primary to-emerald-600 text-white',
                    'hover:shadow-2xl active:scale-95 transition-all duration-300',
                    expanded && 'rotate-45'
                )}
                style={{
                    animation: expanded ? undefined : 'fabPulse 3s ease-in-out infinite',
                }}
                title="Quick actions"
            >
                {expanded ? (
                    <X className="w-5 h-5 transition-transform duration-300" />
                ) : (
                    <Plus className="w-5 h-5 transition-transform duration-300" />
                )}
            </button>

            <style jsx>{`
                @keyframes fabPulse {
                    0%, 100% { box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); }
                    50% { box-shadow: 0 4px 24px rgba(16, 185, 129, 0.5); }
                }
                @keyframes fabContainerIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes fabItemIn {
                    from { opacity: 0; transform: scale(0) translateY(20px); }
                    to { opacity: 1; transform: scale(1) translateY(0); }
                }
            `}</style>
        </div>
    );
}
