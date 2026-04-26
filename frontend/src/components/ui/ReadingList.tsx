'use client';

import { useState, useEffect, useCallback } from 'react';
import { X, Plus, Trash2, ExternalLink, BookmarkPlus, Check, Circle, Link2, Tag } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-reading-list';

interface ReadingItem {
    id: string;
    title: string;
    url?: string;
    note: string;
    tags: string[];
    read: boolean;
    createdAt: string;
}

function loadItems(): ReadingItem[] {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch { return []; }
}
function saveItems(items: ReadingItem[]) { localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); }

// Extract URLs from AI content
function extractUrls(text: string): { url: string; context: string }[] {
    const urlRegex = /https?:\/\/[^\s)>\]]+/g;
    const results: { url: string; context: string }[] = [];
    let match;
    while ((match = urlRegex.exec(text)) !== null) {
        const start = Math.max(0, match.index - 50);
        const end = Math.min(text.length, match.index + match[0].length + 50);
        results.push({ url: match[0], context: text.slice(start, end).trim() });
    }
    return results;
}

export function useReadingList() {
    const addFromContent = useCallback((content: string, manualTitle?: string) => {
        const items = loadItems();
        const urls = extractUrls(content);
        let added = 0;
        for (const { url, context } of urls) {
            if (!items.some(i => i.url === url)) {
                items.push({
                    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
                    title: manualTitle || url.replace(/https?:\/\//, '').split('/')[0],
                    url,
                    note: context,
                    tags: [],
                    read: false,
                    createdAt: new Date().toISOString(),
                });
                added++;
            }
        }
        if (added > 0) saveItems(items);
        return added;
    }, []);

    return { addFromContent };
}

const TAG_COLORS: Record<string, string> = {
    'article': 'bg-blue-500/15 text-blue-400',
    'video': 'bg-red-500/15 text-red-400',
    'docs': 'bg-emerald-500/15 text-emerald-400',
    'tool': 'bg-amber-500/15 text-amber-400',
    'tutorial': 'bg-violet-500/15 text-violet-400',
    'reference': 'bg-cyan-500/15 text-cyan-400',
};
const TAG_OPTIONS = Object.keys(TAG_COLORS);

export function ReadingList() {
    const [open, setOpen] = useState(false);
    const [items, setItems] = useState<ReadingItem[]>([]);
    const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all');
    const [adding, setAdding] = useState(false);
    const [newTitle, setNewTitle] = useState('');
    const [newUrl, setNewUrl] = useState('');
    const [newNote, setNewNote] = useState('');
    const [newTags, setNewTags] = useState<string[]>([]);

    useEffect(() => {
        const handler = () => { setOpen(true); setItems(loadItems()); };
        window.addEventListener('ai-os:open-reading-list', handler);
        return () => window.removeEventListener('ai-os:open-reading-list', handler);
    }, []);

    const filtered = items.filter(i => {
        if (filter === 'unread') return !i.read;
        if (filter === 'read') return i.read;
        return true;
    });

    const toggleRead = (id: string) => {
        const updated = items.map(i => i.id === id ? { ...i, read: !i.read } : i);
        setItems(updated);
        saveItems(updated);
    };

    const deleteItem = (id: string) => {
        const updated = items.filter(i => i.id !== id);
        setItems(updated);
        saveItems(updated);
    };

    const addItem = () => {
        if (!newTitle.trim()) return;
        const item: ReadingItem = {
            id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
            title: newTitle.trim(),
            url: newUrl.trim() || undefined,
            note: newNote.trim(),
            tags: newTags,
            read: false,
            createdAt: new Date().toISOString(),
        };
        const updated = [item, ...items];
        setItems(updated);
        saveItems(updated);
        setNewTitle('');
        setNewUrl('');
        setNewNote('');
        setNewTags([]);
        setAdding(false);
    };

    const unreadCount = items.filter(i => !i.read).length;

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" onClick={() => setOpen(false)} />

            <div className="relative max-w-md mx-auto mt-[10vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                style={{ animation: 'slideUp 200ms ease-out' }}>

                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-indigo-500/10 flex items-center justify-center">
                            <BookmarkPlus className="w-4 h-4 text-blue-400" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-foreground">Reading List</h2>
                            <p className="text-[10px] text-muted-foreground">{unreadCount} unread · {items.length} total</p>
                        </div>
                    </div>
                    <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Filters */}
                <div className="flex items-center gap-1 px-5 pt-3">
                    {(['all', 'unread', 'read'] as const).map(f => (
                        <button key={f} onClick={() => setFilter(f)}
                            className={cn('px-2.5 py-1 text-xs rounded-md font-medium transition-colors capitalize',
                                filter === f ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted')}>
                            {f}
                        </button>
                    ))}
                    <button onClick={() => setAdding(true)} className="ml-auto p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                        <Plus className="w-4 h-4" />
                    </button>
                </div>

                <div className="p-5 max-h-[55vh] overflow-y-auto">
                    {adding && (
                        <div className="mb-4 p-3 rounded-xl border border-border bg-secondary/30 space-y-2.5" style={{ animation: 'slideUp 200ms ease-out' }}>
                            <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Title *"
                                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary" autoFocus />
                            <input value={newUrl} onChange={e => setNewUrl(e.target.value)} placeholder="URL (optional)"
                                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary" />
                            <input value={newNote} onChange={e => setNewNote(e.target.value)} placeholder="Note (optional)"
                                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary" />
                            <div className="flex items-center gap-1.5 flex-wrap">
                                {TAG_OPTIONS.map(t => (
                                    <button key={t} onClick={() => setNewTags(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t])}
                                        className={cn('px-2 py-0.5 rounded text-[10px] font-medium capitalize transition-all',
                                            newTags.includes(t) ? TAG_COLORS[t] + ' ring-1 ring-current/30' : 'bg-muted text-muted-foreground hover:text-foreground')}>
                                        {t}
                                    </button>
                                ))}
                            </div>
                            <div className="flex gap-2">
                                <button onClick={addItem} disabled={!newTitle.trim()} className="flex-1 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-40 transition-all">Save</button>
                                <button onClick={() => setAdding(false)} className="px-4 py-2 rounded-lg bg-secondary text-foreground text-sm hover:bg-accent transition-colors">Cancel</button>
                            </div>
                        </div>
                    )}

                    {filtered.length === 0 ? (
                        <div className="text-center py-10">
                            <BookmarkPlus className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                            <p className="text-sm text-muted-foreground">{filter === 'all' ? 'No items yet' : `No ${filter} items`}</p>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {filtered.map(item => (
                                <div key={item.id} className={cn('p-3 rounded-lg border border-border group hover:bg-accent/50 transition-colors',
                                    item.read ? 'bg-secondary/30 opacity-60' : 'bg-secondary/50')}>
                                    <div className="flex items-start gap-2.5">
                                        <button onClick={() => toggleRead(item.id)} className="mt-0.5 flex-shrink-0">
                                            {item.read
                                                ? <Check className="w-4 h-4 text-emerald-500" />
                                                : <Circle className="w-4 h-4 text-border hover:text-primary transition-colors" />
                                            }
                                        </button>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-1.5">
                                                <p className={cn('text-sm font-medium truncate', item.read ? 'text-muted-foreground line-through' : 'text-foreground')}>
                                                    {item.title}
                                                </p>
                                                {item.url && (
                                                    <a href={item.url} target="_blank" rel="noopener noreferrer" className="flex-shrink-0 text-muted-foreground/50 hover:text-primary transition-colors">
                                                        <ExternalLink className="w-3 h-3" />
                                                    </a>
                                                )}
                                            </div>
                                            {item.note && <p className="text-xs text-muted-foreground mt-0.5 truncate">{item.note}</p>}
                                            {item.tags.length > 0 && (
                                                <div className="flex items-center gap-1 mt-1.5">
                                                    {item.tags.map(t => (
                                                        <span key={t} className={cn('px-1.5 py-0.5 rounded text-[9px] font-medium capitalize', TAG_COLORS[t] || 'bg-muted text-muted-foreground')}>
                                                            {t}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <button onClick={() => deleteItem(item.id)} className="p-0.5 text-muted-foreground/30 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all">
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <style jsx>{`
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                @keyframes slideUp { from { opacity: 0; transform: translateY(10px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
            `}</style>
        </div>
    );
}
