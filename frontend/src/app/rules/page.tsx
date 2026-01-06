'use client';

import { useState, useEffect } from 'react';
import {
    Search,
    Filter,
    ToggleLeft,
    ToggleRight,
    Pencil,
    Trash2,
    Check,
    X,
    Info
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { api, Rule } from '@/lib/api';
import {
    cn,
    formatRelativeTime,
    getConfidenceColor,
    getConfidenceBgColor,
    getCategoryIcon,
    getCategoryColor
} from '@/lib/utils';

const categories = ['all', 'style', 'tone', 'formatting', 'logic', 'safety'];
const statuses = ['all', 'active', 'disabled', 'archived'];

export default function RulesPage() {
    const [rules, setRules] = useState<Rule[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('all');
    const [statusFilter, setStatusFilter] = useState('all');
    const [editingRule, setEditingRule] = useState<string | null>(null);
    const [editContent, setEditContent] = useState('');
    const [stats, setStats] = useState({ total: 0, active: 0, archived: 0, disabled: 0 });
    const { toast } = useToast();

    useEffect(() => {
        fetchRules();
    }, [categoryFilter, statusFilter]);

    const fetchRules = async () => {
        try {
            const response = await api.getRules(
                statusFilter === 'all' ? undefined : statusFilter,
                categoryFilter === 'all' ? undefined : categoryFilter
            );
            setRules(response.rules);
            setStats({
                total: response.total,
                active: response.active,
                archived: response.archived,
                disabled: response.disabled,
            });
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to fetch rules',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const handleToggle = async (ruleId: string) => {
        try {
            const updated = await api.toggleRule(ruleId);
            setRules(rules.map(r => r.id === ruleId ? updated : r));
            toast({
                title: 'Rule Updated',
                description: `Rule is now ${updated.status}`,
                variant: 'success',
            });
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to toggle rule',
                variant: 'destructive',
            });
        }
    };

    const handleDelete = async (ruleId: string) => {
        if (!confirm('Are you sure you want to delete this rule?')) return;

        try {
            await api.deleteRule(ruleId);
            setRules(rules.filter(r => r.id !== ruleId));
            toast({
                title: 'Rule Deleted',
                description: 'The rule has been permanently deleted',
            });
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to delete rule',
                variant: 'destructive',
            });
        }
    };

    const handleEdit = async (ruleId: string) => {
        if (!editContent.trim()) return;

        try {
            const updated = await api.updateRule(ruleId, { content: editContent });
            setRules(rules.map(r => r.id === ruleId ? updated : r));
            setEditingRule(null);
            setEditContent('');
            toast({
                title: 'Rule Updated',
                description: 'The rule content has been updated',
                variant: 'success',
            });
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to update rule',
                variant: 'destructive',
            });
        }
    };

    const filteredRules = rules.filter(rule =>
        rule.content.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <header className="px-6 py-4 border-b border-border glass">
                <h1 className="text-xl font-semibold">Your Rules</h1>
                <p className="text-sm text-muted-foreground">
                    Manage your learned preferences and behaviors
                </p>
            </header>

            {/* Stats */}
            <div className="px-6 py-4 grid grid-cols-4 gap-4 border-b border-border">
                {[
                    { label: 'Total', value: stats.total, color: 'text-foreground' },
                    { label: 'Active', value: stats.active, color: 'text-green-500' },
                    { label: 'Disabled', value: stats.disabled, color: 'text-yellow-500' },
                    { label: 'Archived', value: stats.archived, color: 'text-muted-foreground' },
                ].map(stat => (
                    <div key={stat.label} className="bg-muted/50 rounded-lg p-3">
                        <p className={cn('text-2xl font-bold', stat.color)}>{stat.value}</p>
                        <p className="text-xs text-muted-foreground">{stat.label}</p>
                    </div>
                ))}
            </div>

            {/* Filters */}
            <div className="px-6 py-4 flex flex-wrap gap-4 border-b border-border">
                <div className="flex-1 min-w-[200px] relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        placeholder="Search rules..."
                        className="w-full pl-10 pr-4 py-2 rounded-lg bg-muted border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                </div>

                <div className="flex gap-2">
                    {categories.map(cat => (
                        <button
                            key={cat}
                            onClick={() => setCategoryFilter(cat)}
                            className={cn(
                                'px-3 py-2 rounded-lg text-sm transition-smooth capitalize',
                                categoryFilter === cat
                                    ? 'bg-primary text-primary-foreground'
                                    : 'bg-muted hover:bg-muted/80'
                            )}
                        >
                            {cat === 'all' ? 'All' : `${getCategoryIcon(cat)} ${cat}`}
                        </button>
                    ))}
                </div>

                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="px-3 py-2 rounded-lg bg-muted border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                >
                    {statuses.map(status => (
                        <option key={status} value={status}>
                            {status.charAt(0).toUpperCase() + status.slice(1)}
                        </option>
                    ))}
                </select>
            </div>

            {/* Rules List */}
            <div className="flex-1 overflow-y-auto p-6">
                {loading ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="animate-pulse text-muted-foreground">Loading rules...</div>
                    </div>
                ) : filteredRules.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                        <Info className="w-12 h-12 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium mb-2">No rules found</h3>
                        <p className="text-muted-foreground max-w-md">
                            {rules.length === 0
                                ? "You haven't learned any rules yet. Start chatting and correct the AI to teach it your preferences."
                                : "No rules match your current filters."}
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {filteredRules.map(rule => (
                            <div
                                key={rule.id}
                                className={cn(
                                    'bg-card rounded-xl border p-4 transition-smooth hover:border-primary/30',
                                    rule.status === 'disabled' && 'opacity-60',
                                    rule.status === 'archived' && 'opacity-40'
                                )}
                            >
                                <div className="flex items-start gap-4">
                                    {/* Confidence Indicator */}
                                    <div className="flex flex-col items-center gap-1">
                                        <div
                                            className={cn(
                                                'w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold',
                                                getConfidenceBgColor(rule.confidence)
                                            )}
                                        >
                                            {Math.round(rule.confidence * 100)}
                                        </div>
                                        <span className="text-xs text-muted-foreground">conf.</span>
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        {editingRule === rule.id ? (
                                            <div className="space-y-2">
                                                <textarea
                                                    value={editContent}
                                                    onChange={(e) => setEditContent(e.target.value)}
                                                    className="w-full p-2 rounded-lg bg-muted border border-border resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                                                    rows={2}
                                                />
                                                <div className="flex gap-2">
                                                    <Button size="sm" onClick={() => handleEdit(rule.id)}>
                                                        <Check className="w-4 h-4 mr-1" /> Save
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => {
                                                            setEditingRule(null);
                                                            setEditContent('');
                                                        }}
                                                    >
                                                        <X className="w-4 h-4 mr-1" /> Cancel
                                                    </Button>
                                                </div>
                                            </div>
                                        ) : (
                                            <>
                                                <p className="font-medium mb-2">{rule.content}</p>
                                                <div className="flex flex-wrap items-center gap-2 text-xs">
                                                    <span className={cn('px-2 py-1 rounded-full border', getCategoryColor(rule.category))}>
                                                        {getCategoryIcon(rule.category)} {rule.category}
                                                    </span>
                                                    <span className="text-muted-foreground">
                                                        Applied {rule.times_applied}x
                                                    </span>
                                                    <span className="text-muted-foreground">
                                                        Reinforced {rule.times_reinforced}x
                                                    </span>
                                                    {rule.created_at && (
                                                        <span className="text-muted-foreground">
                                                            Created {formatRelativeTime(rule.created_at)}
                                                        </span>
                                                    )}
                                                </div>
                                                {rule.original_correction && (
                                                    <p className="mt-2 text-sm text-muted-foreground italic">
                                                        Original: "{rule.original_correction}"
                                                    </p>
                                                )}
                                            </>
                                        )}
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => handleToggle(rule.id)}
                                            className="p-2 rounded-lg hover:bg-muted transition-smooth"
                                            title={rule.status === 'active' ? 'Disable' : 'Enable'}
                                        >
                                            {rule.status === 'active' ? (
                                                <ToggleRight className="w-5 h-5 text-green-500" />
                                            ) : (
                                                <ToggleLeft className="w-5 h-5 text-muted-foreground" />
                                            )}
                                        </button>
                                        <button
                                            onClick={() => {
                                                setEditingRule(rule.id);
                                                setEditContent(rule.content);
                                            }}
                                            className="p-2 rounded-lg hover:bg-muted transition-smooth"
                                            title="Edit"
                                        >
                                            <Pencil className="w-4 h-4 text-muted-foreground" />
                                        </button>
                                        <button
                                            onClick={() => handleDelete(rule.id)}
                                            className="p-2 rounded-lg hover:bg-muted transition-smooth"
                                            title="Delete"
                                        >
                                            <Trash2 className="w-4 h-4 text-red-500" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
