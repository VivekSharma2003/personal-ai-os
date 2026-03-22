'use client';

import { useState, useEffect } from 'react';
import { Code2, Copy, Check, Trash2, X, Scissors } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-snippets';

interface Snippet {
    id: string;
    code: string;
    language: string;
    preview: string;
    createdAt: string;
}

function getStoredSnippets(): Snippet[] {
    if (typeof window === 'undefined') return [];
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    } catch {
        return [];
    }
}

function saveSnippets(snippets: Snippet[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(snippets));
}

// Hook for saving snippets
export function useSnippets() {
    const [snippets, setSnippets] = useState<Snippet[]>([]);

    useEffect(() => {
        setSnippets(getStoredSnippets());
    }, []);

    const saveSnippet = (code: string, language: string = 'text') => {
        const newSnippet: Snippet = {
            id: `snippet-${Date.now()}`,
            code,
            language,
            preview: code.split('\n').slice(0, 3).join('\n'),
            createdAt: new Date().toISOString(),
        };
        const updated = [newSnippet, ...snippets];
        setSnippets(updated);
        saveSnippets(updated);
    };

    const deleteSnippet = (id: string) => {
        const updated = snippets.filter((s) => s.id !== id);
        setSnippets(updated);
        saveSnippets(updated);
    };

    return { snippets, saveSnippet, deleteSnippet };
}

// Snippets library panel
export function SnippetLibrary() {
    const [open, setOpen] = useState(false);
    const { snippets, deleteSnippet } = useSnippets();
    const [copiedId, setCopiedId] = useState<string | null>(null);

    // Listen for open event
    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('ai-os:open-snippets', handler);
        return () => window.removeEventListener('ai-os:open-snippets', handler);
    }, []);

    const handleCopy = async (snippet: Snippet) => {
        await navigator.clipboard.writeText(snippet.code);
        setCopiedId(snippet.id);
        setTimeout(() => setCopiedId(null), 1500);
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div
                className="absolute inset-0 bg-background/60 backdrop-blur-sm"
                onClick={() => setOpen(false)}
            />

            <div
                className="relative max-w-lg mx-auto mt-[10vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden max-h-[70vh] flex flex-col"
                style={{ animation: 'slideUp 200ms ease-out' }}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Scissors className="w-4 h-4 text-primary" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-foreground">Saved Snippets</h2>
                            <p className="text-xs text-muted-foreground">{snippets.length} snippet{snippets.length !== 1 ? 's' : ''}</p>
                        </div>
                    </div>
                    <button
                        onClick={() => setOpen(false)}
                        className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-smooth"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Snippets */}
                <div className="flex-1 overflow-y-auto p-3">
                    {snippets.length === 0 ? (
                        <div className="py-16 text-center">
                            <Code2 className="w-10 h-10 text-muted-foreground/20 mx-auto mb-3" />
                            <p className="text-sm text-muted-foreground">No saved snippets</p>
                            <p className="text-xs text-muted-foreground/60 mt-1">
                                Click &quot;Save snippet&quot; on any code block in AI responses
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {snippets.map((snippet) => (
                                <div
                                    key={snippet.id}
                                    className="group bg-secondary/50 border border-border/50 rounded-lg overflow-hidden"
                                >
                                    <div className="flex items-center justify-between px-3 py-2 bg-secondary/80">
                                        <div className="flex items-center gap-2">
                                            <Code2 className="w-3 h-3 text-muted-foreground" />
                                            <span className="text-[10px] font-mono text-muted-foreground uppercase">
                                                {snippet.language}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <button
                                                onClick={() => handleCopy(snippet)}
                                                className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                                                title="Copy"
                                            >
                                                {copiedId === snippet.id ? (
                                                    <Check className="w-3 h-3 text-green-500" />
                                                ) : (
                                                    <Copy className="w-3 h-3" />
                                                )}
                                            </button>
                                            <button
                                                onClick={() => deleteSnippet(snippet.id)}
                                                className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                                                title="Delete"
                                            >
                                                <Trash2 className="w-3 h-3" />
                                            </button>
                                        </div>
                                    </div>
                                    <pre className="px-3 py-2 text-xs font-mono text-foreground overflow-x-auto max-h-32 leading-relaxed">
                                        <code>{snippet.preview}</code>
                                    </pre>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <style jsx>{`
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(10px) scale(0.98); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
            `}</style>
        </div>
    );
}
