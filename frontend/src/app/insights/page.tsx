'use client';

import { useState, useEffect, useRef } from 'react';
import {
    Brain,
    Sparkles,
    TrendingUp,
    BarChart3,
    Activity,
    Zap,
    Shield,
    Clock,
    ChevronRight,
} from 'lucide-react';
import { api, Rule, AuditEvent } from '@/lib/api';
import { cn, formatRelativeTime, getCategoryIcon, getCategoryColor } from '@/lib/utils';

// ─── Animated Counter ───
function AnimatedNumber({ value, duration = 1200 }: { value: number; duration?: number }) {
    const [display, setDisplay] = useState(0);
    useEffect(() => {
        if (value === 0) { setDisplay(0); return; }
        let start = 0;
        const step = value / (duration / 16);
        const interval = setInterval(() => {
            start += step;
            if (start >= value) { setDisplay(value); clearInterval(interval); }
            else setDisplay(Math.floor(start));
        }, 16);
        return () => clearInterval(interval);
    }, [value, duration]);
    return <span>{display}</span>;
}

// ─── Radial Gauge ───
function BrainHealthGauge({ score }: { score: number }) {
    const [animatedScore, setAnimatedScore] = useState(0);
    const circumference = 2 * Math.PI * 54;
    const offset = circumference - (animatedScore / 100) * circumference;

    useEffect(() => {
        const timer = setTimeout(() => setAnimatedScore(score), 300);
        return () => clearTimeout(timer);
    }, [score]);

    const getColor = (s: number) => {
        if (s >= 75) return { stroke: 'url(#gaugeGradientHigh)', text: 'text-emerald-400', label: 'Excellent' };
        if (s >= 50) return { stroke: 'url(#gaugeGradientMid)', text: 'text-amber-400', label: 'Growing' };
        if (s >= 25) return { stroke: 'url(#gaugeGradientLow)', text: 'text-orange-400', label: 'Learning' };
        return { stroke: 'url(#gaugeGradientNew)', text: 'text-blue-400', label: 'New' };
    };
    const color = getColor(animatedScore);

    return (
        <div className="relative flex flex-col items-center">
            <svg width="140" height="140" className="transform -rotate-90">
                <defs>
                    <linearGradient id="gaugeGradientHigh" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#10b981" />
                        <stop offset="100%" stopColor="#34d399" />
                    </linearGradient>
                    <linearGradient id="gaugeGradientMid" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#f59e0b" />
                        <stop offset="100%" stopColor="#fbbf24" />
                    </linearGradient>
                    <linearGradient id="gaugeGradientLow" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#f97316" />
                        <stop offset="100%" stopColor="#fb923c" />
                    </linearGradient>
                    <linearGradient id="gaugeGradientNew" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#3b82f6" />
                        <stop offset="100%" stopColor="#60a5fa" />
                    </linearGradient>
                </defs>
                <circle
                    cx="70" cy="70" r="54"
                    stroke="currentColor"
                    className="text-border"
                    strokeWidth="10"
                    fill="none"
                />
                <circle
                    cx="70" cy="70" r="54"
                    stroke={color.stroke}
                    strokeWidth="10"
                    fill="none"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)' }}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={cn('text-3xl font-bold tabular-nums', color.text)}>
                    {Math.round(animatedScore)}
                </span>
                <span className="text-xs text-muted-foreground mt-0.5">{color.label}</span>
            </div>
        </div>
    );
}

// ─── Category Bar ───
function CategoryBar({ category, count, total, index }: { category: string; count: number; total: number; index: number }) {
    const [width, setWidth] = useState(0);
    const pct = total > 0 ? (count / total) * 100 : 0;

    useEffect(() => {
        const timer = setTimeout(() => setWidth(pct), 200 + index * 100);
        return () => clearTimeout(timer);
    }, [pct, index]);

    const colorMap: Record<string, string> = {
        style: 'bg-purple-500',
        tone: 'bg-blue-500',
        formatting: 'bg-green-500',
        logic: 'bg-orange-500',
        safety: 'bg-red-500',
    };

    return (
        <div className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                    <span>{getCategoryIcon(category)}</span>
                    <span className="capitalize font-medium text-foreground">{category}</span>
                </span>
                <span className="text-muted-foreground text-xs tabular-nums">{count} rules</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                    className={cn('h-full rounded-full transition-all duration-1000 ease-out', colorMap[category] || 'bg-gray-500')}
                    style={{ width: `${width}%` }}
                />
            </div>
        </div>
    );
}

// ─── Main Page ───
export default function InsightsPage() {
    const [rules, setRules] = useState<Rule[]>([]);
    const [events, setEvents] = useState<AuditEvent[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function load() {
            try {
                const [rulesRes, auditRes] = await Promise.all([
                    api.getRules(),
                    api.getAuditLog(undefined, undefined, 20),
                ]);
                setRules(rulesRes.rules);
                setEvents(auditRes.events);
            } catch {
                // API may not be running — show empty state
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    const activeRules = rules.filter((r) => r.status === 'active');
    const avgConfidence = activeRules.length
        ? activeRules.reduce((sum, r) => sum + r.confidence, 0) / activeRules.length
        : 0;
    const totalApplied = rules.reduce((sum, r) => sum + r.times_applied, 0);
    const brainScore = Math.round(
        Math.min(100, (activeRules.length * 15 + avgConfidence * 40 + Math.min(totalApplied, 50)))
    );

    // Category distribution
    const categories: Record<string, number> = {};
    rules.forEach((r) => {
        categories[r.category] = (categories[r.category] || 0) + 1;
    });
    const sortedCategories = Object.entries(categories).sort((a, b) => b[1] - a[1]);

    const stats = [
        {
            label: 'Total Rules Learned',
            value: rules.length,
            icon: Brain,
            color: 'from-violet-500/20 to-purple-500/20',
            iconColor: 'text-violet-400',
        },
        {
            label: 'Active Rules',
            value: activeRules.length,
            icon: Zap,
            color: 'from-emerald-500/20 to-green-500/20',
            iconColor: 'text-emerald-400',
        },
        {
            label: 'Avg Confidence',
            value: Math.round(avgConfidence * 100),
            suffix: '%',
            icon: TrendingUp,
            color: 'from-amber-500/20 to-yellow-500/20',
            iconColor: 'text-amber-400',
        },
        {
            label: 'Times Applied',
            value: totalApplied,
            icon: Activity,
            color: 'from-blue-500/20 to-cyan-500/20',
            iconColor: 'text-blue-400',
        },
    ];

    const getEventIcon = (type: string) => {
        if (type.includes('created')) return { icon: Sparkles, color: 'text-green-400 bg-green-500/10' };
        if (type.includes('applied')) return { icon: Zap, color: 'text-blue-400 bg-blue-500/10' };
        if (type.includes('reinforced')) return { icon: TrendingUp, color: 'text-amber-400 bg-amber-500/10' };
        if (type.includes('archived')) return { icon: Shield, color: 'text-red-400 bg-red-500/10' };
        return { icon: Activity, color: 'text-muted-foreground bg-muted' };
    };

    return (
        <div className="flex flex-col h-full bg-background">
            {/* Header */}
            <header className="px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Brain className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1">
                        <h1 className="font-semibold text-foreground">AI Insights</h1>
                        <p className="text-xs text-muted-foreground">
                            How well your AI knows you
                        </p>
                    </div>
                </div>
            </header>

            <div className="flex-1 overflow-y-auto">
                <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
                    {/* Stats Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {stats.map((stat, i) => {
                            const Icon = stat.icon;
                            return (
                                <div
                                    key={stat.label}
                                    className={cn(
                                        'relative overflow-hidden rounded-xl border border-border bg-card p-5',
                                        'hover:border-primary/30 transition-all duration-300 group'
                                    )}
                                    style={{ animationDelay: `${i * 100}ms` }}
                                >
                                    <div className={cn(
                                        'absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-100 transition-opacity duration-500',
                                        stat.color
                                    )} />
                                    <div className="relative">
                                        <div className="flex items-center justify-between mb-3">
                                            <Icon className={cn('w-5 h-5', stat.iconColor)} />
                                            <BarChart3 className="w-4 h-4 text-muted-foreground/30" />
                                        </div>
                                        <div className="text-3xl font-bold text-foreground tabular-nums">
                                            <AnimatedNumber value={stat.value} />
                                            {stat.suffix && <span className="text-lg ml-0.5">{stat.suffix}</span>}
                                        </div>
                                        <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Brain Health + Categories */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Brain Health */}
                        <div className="rounded-xl border border-border bg-card p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-6 flex items-center gap-2">
                                <Brain className="w-4 h-4 text-primary" />
                                AI Brain Health
                            </h2>
                            <div className="flex flex-col items-center gap-4">
                                <BrainHealthGauge score={brainScore} />
                                <p className="text-sm text-muted-foreground text-center max-w-xs">
                                    {brainScore >= 75
                                        ? 'Your AI has a strong understanding of your preferences!'
                                        : brainScore >= 50
                                            ? 'Good progress! Keep teaching to improve accuracy.'
                                            : brainScore >= 25
                                                ? 'Your AI is learning. Correct responses to teach it faster.'
                                                : 'Start chatting and correcting responses to train your AI.'}
                                </p>
                            </div>
                        </div>

                        {/* Category Breakdown */}
                        <div className="rounded-xl border border-border bg-card p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-6 flex items-center gap-2">
                                <BarChart3 className="w-4 h-4 text-primary" />
                                Rule Categories
                            </h2>
                            {sortedCategories.length > 0 ? (
                                <div className="space-y-4">
                                    {sortedCategories.map(([cat, count], i) => (
                                        <CategoryBar
                                            key={cat}
                                            category={cat}
                                            count={count}
                                            total={rules.length}
                                            index={i}
                                        />
                                    ))}
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center py-8 text-center">
                                    <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center mb-3">
                                        <Brain className="w-6 h-6 text-muted-foreground" />
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                        No rules learned yet. Start chatting!
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Recent Activity */}
                    <div className="rounded-xl border border-border bg-card p-6">
                        <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                            <Clock className="w-4 h-4 text-primary" />
                            Recent Activity
                        </h2>
                        {events.length > 0 ? (
                            <div className="space-y-1">
                                {events.slice(0, 8).map((event) => {
                                    const { icon: EvIcon, color } = getEventIcon(event.event_type);
                                    return (
                                        <div
                                            key={event.id}
                                            className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-accent/50 transition-colors group"
                                        >
                                            <div className={cn('w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0', color)}>
                                                <EvIcon className="w-3.5 h-3.5" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm text-foreground capitalize">
                                                    {event.event_type.replace(/_/g, ' ')}
                                                </p>
                                                {event.event_data?.rule_content ? (
                                                    <p className="text-xs text-muted-foreground truncate">
                                                        {String(event.event_data.rule_content as string)}
                                                    </p>
                                                ) : null}
                                            </div>
                                            <span className="text-xs text-muted-foreground flex-shrink-0">
                                                {formatRelativeTime(event.created_at)}
                                            </span>
                                            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/30 opacity-0 group-hover:opacity-100 transition-opacity" />
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-8 text-center">
                                <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center mb-3">
                                    <Activity className="w-6 h-6 text-muted-foreground" />
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    No activity yet. Start a conversation to see events here.
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
