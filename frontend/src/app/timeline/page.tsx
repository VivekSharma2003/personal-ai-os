'use client';

import { useState, useEffect } from 'react';
import {
    Clock,
    Plus,
    Zap,
    RefreshCw,
    Archive,
    Pencil,
    Trash2,
    ToggleLeft,
    ToggleRight,
    Filter
} from 'lucide-react';
import { api, AuditEvent } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { cn, formatDate, formatTime, formatRelativeTime } from '@/lib/utils';

const eventTypes = [
    { value: 'all', label: 'All Events' },
    { value: 'rule_created', label: 'Created', icon: Plus, color: 'text-green-500' },
    { value: 'rule_applied', label: 'Applied', icon: Zap, color: 'text-blue-500' },
    { value: 'rule_reinforced', label: 'Reinforced', icon: RefreshCw, color: 'text-purple-500' },
    { value: 'rule_decayed', label: 'Decayed', icon: Clock, color: 'text-yellow-500' },
    { value: 'rule_archived', label: 'Archived', icon: Archive, color: 'text-orange-500' },
    { value: 'rule_edited', label: 'Edited', icon: Pencil, color: 'text-cyan-500' },
    { value: 'rule_deleted', label: 'Deleted', icon: Trash2, color: 'text-red-500' },
    { value: 'rule_disabled', label: 'Disabled', icon: ToggleLeft, color: 'text-gray-500' },
    { value: 'rule_enabled', label: 'Enabled', icon: ToggleRight, color: 'text-green-500' },
];

function getEventDetails(event: AuditEvent) {
    const eventType = eventTypes.find(e => e.value === event.event_type);
    return eventType || { value: event.event_type, label: event.event_type, icon: Clock, color: 'text-muted-foreground' };
}

export default function TimelinePage() {
    const [events, setEvents] = useState<AuditEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [eventTypeFilter, setEventTypeFilter] = useState('all');
    const { toast } = useToast();

    useEffect(() => {
        fetchAuditLog();
    }, [eventTypeFilter]);

    const fetchAuditLog = async () => {
        try {
            const response = await api.getAuditLog(
                undefined,
                eventTypeFilter === 'all' ? undefined : eventTypeFilter
            );
            setEvents(response.events);
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to fetch timeline',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    // Group events by date
    const groupedEvents = events.reduce((acc, event) => {
        const date = formatDate(event.created_at);
        if (!acc[date]) {
            acc[date] = [];
        }
        acc[date].push(event);
        return acc;
    }, {} as Record<string, AuditEvent[]>);

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <header className="px-6 py-4 border-b border-border glass">
                <h1 className="text-xl font-semibold">Timeline</h1>
                <p className="text-sm text-muted-foreground">
                    Track how your AI assistant has learned over time
                </p>
            </header>

            {/* Filters */}
            <div className="px-6 py-4 flex items-center gap-4 border-b border-border">
                <Filter className="w-4 h-4 text-muted-foreground" />
                <div className="flex flex-wrap gap-2">
                    {eventTypes.map(type => (
                        <button
                            key={type.value}
                            onClick={() => setEventTypeFilter(type.value)}
                            className={cn(
                                'px-3 py-1.5 rounded-lg text-sm transition-smooth flex items-center gap-1.5',
                                eventTypeFilter === type.value
                                    ? 'bg-primary text-primary-foreground'
                                    : 'bg-muted hover:bg-muted/80'
                            )}
                        >
                            {type.value !== 'all' && (
                                <type.icon className={cn('w-3.5 h-3.5', eventTypeFilter === type.value ? '' : type.color)} />
                            )}
                            {type.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Timeline */}
            <div className="flex-1 overflow-y-auto p-6">
                {loading ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="animate-pulse text-muted-foreground">Loading timeline...</div>
                    </div>
                ) : events.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                        <Clock className="w-12 h-12 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium mb-2">No events yet</h3>
                        <p className="text-muted-foreground max-w-md">
                            {eventTypeFilter === 'all'
                                ? "Your timeline will show activity as you interact with the AI and create rules."
                                : "No events match this filter."}
                        </p>
                    </div>
                ) : (
                    <div className="space-y-8">
                        {Object.entries(groupedEvents).map(([date, dateEvents]) => (
                            <div key={date}>
                                <div className="sticky top-0 bg-background/90 backdrop-blur-sm py-2 mb-4">
                                    <h3 className="text-sm font-medium text-muted-foreground">{date}</h3>
                                </div>

                                <div className="relative pl-8 border-l-2 border-border space-y-6">
                                    {dateEvents.map((event, idx) => {
                                        const details = getEventDetails(event);
                                        const Icon = details.icon;

                                        return (
                                            <div key={event.id} className="relative animate-fade-in">
                                                {/* Timeline dot */}
                                                <div className={cn(
                                                    'absolute -left-[25px] w-4 h-4 rounded-full border-2 border-background',
                                                    details.color.replace('text-', 'bg-')
                                                )} />

                                                {/* Event card */}
                                                <div className="bg-card rounded-lg border p-4 hover:border-primary/30 transition-smooth">
                                                    <div className="flex items-start gap-3">
                                                        <div className={cn(
                                                            'w-8 h-8 rounded-lg flex items-center justify-center',
                                                            details.color.replace('text-', 'bg-') + '/20'
                                                        )}>
                                                            <Icon className={cn('w-4 h-4', details.color)} />
                                                        </div>

                                                        <div className="flex-1 min-w-0">
                                                            <div className="flex items-center gap-2 mb-1">
                                                                <span className="font-medium">{details.label}</span>
                                                                <span className="text-xs text-muted-foreground">
                                                                    {formatTime(event.created_at)}
                                                                </span>
                                                            </div>

                                                            {event.event_data && Object.keys(event.event_data).length > 0 && (
                                                                <div className="text-sm text-muted-foreground space-y-1">
                                                                    {event.event_data.content && (
                                                                        <p className="truncate">Rule: {event.event_data.content as string}</p>
                                                                    )}
                                                                    {event.event_data.old_confidence !== undefined && (
                                                                        <p>
                                                                            Confidence: {Math.round((event.event_data.old_confidence as number) * 100)}% →{' '}
                                                                            {Math.round((event.event_data.new_confidence as number) * 100)}%
                                                                        </p>
                                                                    )}
                                                                    {event.event_data.reason && (
                                                                        <p>Reason: {event.event_data.reason as string}</p>
                                                                    )}
                                                                    {event.event_data.times_applied !== undefined && (
                                                                        <p>Total applications: {event.event_data.times_applied as number}</p>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </div>

                                                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                                                            {formatRelativeTime(event.created_at)}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
