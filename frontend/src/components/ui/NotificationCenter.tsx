'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Bell, Check, Sparkles, Zap, TrendingUp, Shield, Activity } from 'lucide-react';
import { api, AuditEvent } from '@/lib/api';
import { cn, formatRelativeTime } from '@/lib/utils';

const READ_KEY = 'ai-os-notifications-read';

function getReadIds(): Set<string> {
    if (typeof window === 'undefined') return new Set();
    try {
        const data = localStorage.getItem(READ_KEY);
        return data ? new Set(JSON.parse(data)) : new Set();
    } catch {
        return new Set();
    }
}

function saveReadIds(ids: Set<string>) {
    localStorage.setItem(READ_KEY, JSON.stringify(Array.from(ids)));
}

function getEventMeta(type: string) {
    if (type.includes('created')) return { icon: Sparkles, color: 'text-green-400 bg-green-500/10', label: 'Rule created' };
    if (type.includes('applied')) return { icon: Zap, color: 'text-blue-400 bg-blue-500/10', label: 'Rule applied' };
    if (type.includes('reinforced')) return { icon: TrendingUp, color: 'text-amber-400 bg-amber-500/10', label: 'Rule reinforced' };
    if (type.includes('archived')) return { icon: Shield, color: 'text-red-400 bg-red-500/10', label: 'Rule archived' };
    return { icon: Activity, color: 'text-muted-foreground bg-muted', label: type.replace(/_/g, ' ') };
}

export function NotificationCenter() {
    const [open, setOpen] = useState(false);
    const [events, setEvents] = useState<AuditEvent[]>([]);
    const [readIds, setReadIds] = useState<Set<string>>(new Set());
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Load events
    useEffect(() => {
        setReadIds(getReadIds());
        async function load() {
            try {
                const res = await api.getAuditLog(undefined, undefined, 15);
                setEvents(res.events);
            } catch {
                // API not running
            }
        }
        load();
        // Poll every 30s
        const interval = setInterval(load, 30000);
        return () => clearInterval(interval);
    }, []);

    // Close on outside click
    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        if (open) document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [open]);

    const unreadCount = events.filter((e) => !readIds.has(e.id)).length;

    const markAllRead = useCallback(() => {
        const newReadIds = new Set(readIds);
        events.forEach((e) => newReadIds.add(e.id));
        setReadIds(newReadIds);
        saveReadIds(newReadIds);
    }, [events, readIds]);

    return (
        <div ref={dropdownRef} className="relative">
            <button
                onClick={() => setOpen(!open)}
                className={cn(
                    'relative p-2 rounded-lg transition-smooth',
                    'hover:bg-accent text-muted-foreground hover:text-foreground',
                    open && 'bg-accent text-foreground'
                )}
                title="Notifications"
            >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                    <span
                        className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-primary text-primary-foreground text-[10px] font-bold rounded-full flex items-center justify-center"
                        style={{ animation: 'badgePop 300ms ease-out' }}
                    >
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {open && (
                <div
                    className="absolute bottom-full left-0 mb-2 w-80 bg-card border border-border rounded-xl shadow-2xl overflow-hidden z-50"
                    style={{ animation: 'notifSlide 150ms ease-out' }}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                        <h3 className="text-sm font-semibold text-foreground">Notifications</h3>
                        {unreadCount > 0 && (
                            <button
                                onClick={markAllRead}
                                className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
                            >
                                <Check className="w-3 h-3" />
                                Mark all read
                            </button>
                        )}
                    </div>

                    {/* Events */}
                    <div className="max-h-[300px] overflow-y-auto">
                        {events.length === 0 ? (
                            <div className="py-10 text-center">
                                <Bell className="w-8 h-8 text-muted-foreground/20 mx-auto mb-2" />
                                <p className="text-sm text-muted-foreground">No notifications yet</p>
                            </div>
                        ) : (
                            events.map((event) => {
                                const meta = getEventMeta(event.event_type);
                                const Icon = meta.icon;
                                const isUnread = !readIds.has(event.id);
                                const ruleContent = event.event_data?.rule_content
                                    ? String(event.event_data.rule_content)
                                    : null;

                                return (
                                    <div
                                        key={event.id}
                                        className={cn(
                                            'flex items-start gap-3 px-4 py-3 transition-colors hover:bg-accent/50',
                                            isUnread && 'bg-primary/[0.03]'
                                        )}
                                    >
                                        <div className={cn('w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5', meta.color)}>
                                            <Icon className="w-3.5 h-3.5" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <p className="text-sm text-foreground font-medium capitalize">
                                                    {meta.label}
                                                </p>
                                                {isUnread && (
                                                    <span className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                                                )}
                                            </div>
                                            {ruleContent && (
                                                <p className="text-xs text-muted-foreground truncate mt-0.5">
                                                    {ruleContent}
                                                </p>
                                            )}
                                            <p className="text-[10px] text-muted-foreground/60 mt-1">
                                                {formatRelativeTime(event.created_at)}
                                            </p>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>

                    <style jsx>{`
                        @keyframes badgePop {
                            from { transform: scale(0); }
                            50% { transform: scale(1.3); }
                            to { transform: scale(1); }
                        }
                        @keyframes notifSlide {
                            from { opacity: 0; transform: translateY(4px) scale(0.97); }
                            to { opacity: 1; transform: translateY(0) scale(1); }
                        }
                    `}</style>
                </div>
            )}
        </div>
    );
}
