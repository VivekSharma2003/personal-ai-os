'use client';

import { useState, useEffect, useRef } from 'react';
import { BookTemplate, X, Plus, Trash2, Code, Pen, Lightbulb, Palette } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PromptTemplate {
    id: string;
    title: string;
    prompt: string;
    category: string;
    isCustom?: boolean;
}

const STORAGE_KEY = 'ai-os-prompt-templates';

const DEFAULT_TEMPLATES: PromptTemplate[] = [
    { id: 'w1', title: 'Email Draft', prompt: 'Write a professional email about ', category: 'Writing' },
    { id: 'w2', title: 'Blog Post', prompt: 'Write a blog post about ', category: 'Writing' },
    { id: 'w3', title: 'Summarize Text', prompt: 'Summarize the following text in 3 bullet points:\n\n', category: 'Writing' },
    { id: 'c1', title: 'Debug Code', prompt: 'Debug this code and explain what\'s wrong:\n\n```\n\n```', category: 'Coding' },
    { id: 'c2', title: 'Code Review', prompt: 'Review this code for bugs, performance, and best practices:\n\n```\n\n```', category: 'Coding' },
    { id: 'c3', title: 'Explain Code', prompt: 'Explain this code step by step:\n\n```\n\n```', category: 'Coding' },
    { id: 'a1', title: 'Pros & Cons', prompt: 'List the pros and cons of ', category: 'Analysis' },
    { id: 'a2', title: 'Compare Options', prompt: 'Compare these options and recommend the best one:\n\n1. \n2. \n3. ', category: 'Analysis' },
    { id: 'cr1', title: 'Story Ideas', prompt: 'Give me 5 creative story ideas about ', category: 'Creative' },
    { id: 'cr2', title: 'Brainstorm', prompt: 'Brainstorm 10 ideas for ', category: 'Creative' },
];

const CATEGORY_ICONS: Record<string, typeof Code> = {
    Writing: Pen,
    Coding: Code,
    Analysis: Lightbulb,
    Creative: Palette,
};

const CATEGORY_COLORS: Record<string, string> = {
    Writing: 'text-blue-400 bg-blue-500/10',
    Coding: 'text-emerald-400 bg-emerald-500/10',
    Analysis: 'text-amber-400 bg-amber-500/10',
    Creative: 'text-purple-400 bg-purple-500/10',
};

function getCustomTemplates(): PromptTemplate[] {
    if (typeof window === 'undefined') return [];
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    } catch {
        return [];
    }
}

function saveCustomTemplates(templates: PromptTemplate[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(templates));
}

interface PromptTemplatesProps {
    onSelect: (prompt: string) => void;
}

export function PromptTemplates({ onSelect }: PromptTemplatesProps) {
    const [open, setOpen] = useState(false);
    const [customTemplates, setCustomTemplates] = useState<PromptTemplate[]>([]);
    const [activeCategory, setActiveCategory] = useState('Writing');
    const [showAdd, setShowAdd] = useState(false);
    const [newTitle, setNewTitle] = useState('');
    const [newPrompt, setNewPrompt] = useState('');
    const panelRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setCustomTemplates(getCustomTemplates());
    }, []);

    // Close on outside click
    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        if (open) document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [open]);

    const allTemplates = [...DEFAULT_TEMPLATES, ...customTemplates];
    const categories = ['Writing', 'Coding', 'Analysis', 'Creative', ...(customTemplates.length > 0 ? ['Custom'] : [])];
    const filtered = allTemplates.filter((t) =>
        activeCategory === 'Custom' ? t.isCustom : t.category === activeCategory
    );

    const handleAdd = () => {
        if (!newTitle.trim() || !newPrompt.trim()) return;
        const newTemplate: PromptTemplate = {
            id: `custom-${Date.now()}`,
            title: newTitle.trim(),
            prompt: newPrompt.trim(),
            category: 'Custom',
            isCustom: true,
        };
        const updated = [...customTemplates, newTemplate];
        setCustomTemplates(updated);
        saveCustomTemplates(updated);
        setNewTitle('');
        setNewPrompt('');
        setShowAdd(false);
        setActiveCategory('Custom');
    };

    const handleDelete = (id: string) => {
        const updated = customTemplates.filter((t) => t.id !== id);
        setCustomTemplates(updated);
        saveCustomTemplates(updated);
    };

    return (
        <div ref={panelRef} className="relative">
            <button
                onClick={() => setOpen(!open)}
                className={cn(
                    'p-3 rounded-xl transition-all duration-200',
                    open
                        ? 'bg-primary/10 text-primary'
                        : 'bg-secondary text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
                title="Prompt Templates"
            >
                <BookTemplate className="w-5 h-5" />
            </button>

            {open && (
                <div
                    className="absolute bottom-full right-0 mb-2 w-[380px] bg-card border border-border rounded-xl shadow-2xl overflow-hidden z-50"
                    style={{ animation: 'panelSlide 200ms ease-out' }}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                        <h3 className="text-sm font-semibold text-foreground">Prompt Templates</h3>
                        <div className="flex items-center gap-1">
                            <button
                                onClick={() => setShowAdd(!showAdd)}
                                className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                                title="Add custom template"
                            >
                                <Plus className="w-3.5 h-3.5" />
                            </button>
                            <button
                                onClick={() => setOpen(false)}
                                className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                            >
                                <X className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    </div>

                    {/* Add Custom Template */}
                    {showAdd && (
                        <div className="px-4 py-3 border-b border-border bg-accent/30 space-y-2" style={{ animation: 'panelSlide 150ms ease-out' }}>
                            <input
                                value={newTitle}
                                onChange={(e) => setNewTitle(e.target.value)}
                                placeholder="Template name..."
                                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                            />
                            <textarea
                                value={newPrompt}
                                onChange={(e) => setNewPrompt(e.target.value)}
                                placeholder="Prompt text..."
                                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/30"
                                rows={2}
                            />
                            <button
                                onClick={handleAdd}
                                disabled={!newTitle.trim() || !newPrompt.trim()}
                                className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                            >
                                Save Template
                            </button>
                        </div>
                    )}

                    {/* Category Tabs */}
                    <div className="flex gap-1 px-3 py-2 border-b border-border overflow-x-auto">
                        {categories.map((cat) => (
                            <button
                                key={cat}
                                onClick={() => setActiveCategory(cat)}
                                className={cn(
                                    'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap',
                                    activeCategory === cat
                                        ? 'bg-primary/10 text-primary'
                                        : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                                )}
                            >
                                {cat}
                            </button>
                        ))}
                    </div>

                    {/* Templates List */}
                    <div className="max-h-[250px] overflow-y-auto p-2">
                        {filtered.length === 0 ? (
                            <div className="py-8 text-center">
                                <p className="text-sm text-muted-foreground">No templates in this category</p>
                            </div>
                        ) : (
                            filtered.map((template) => {
                                const IconComp = CATEGORY_ICONS[template.category] || Lightbulb;
                                const colorClass = CATEGORY_COLORS[template.category] || 'text-muted-foreground bg-muted';

                                return (
                                    <div
                                        key={template.id}
                                        className="group flex items-start gap-3 px-3 py-2.5 rounded-lg hover:bg-accent/50 cursor-pointer transition-colors"
                                        onClick={() => {
                                            onSelect(template.prompt);
                                            setOpen(false);
                                        }}
                                    >
                                        <div className={cn('w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5', colorClass)}>
                                            <IconComp className="w-3.5 h-3.5" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-foreground">{template.title}</p>
                                            <p className="text-xs text-muted-foreground truncate mt-0.5">{template.prompt}</p>
                                        </div>
                                        {template.isCustom && (
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleDelete(template.id);
                                                }}
                                                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 rounded transition-all"
                                            >
                                                <Trash2 className="w-3 h-3 text-destructive" />
                                            </button>
                                        )}
                                    </div>
                                );
                            })
                        )}
                    </div>

                    <style jsx>{`
                        @keyframes panelSlide {
                            from { opacity: 0; transform: translateY(4px) scale(0.97); }
                            to { opacity: 1; transform: translateY(0) scale(1); }
                        }
                    `}</style>
                </div>
            )}
        </div>
    );
}
