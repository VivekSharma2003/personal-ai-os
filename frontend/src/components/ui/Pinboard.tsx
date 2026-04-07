'use client';

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Pin, X, Trash2, GripVertical, Palette, Plus, Minimize2, Maximize2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PinnedNote {
    id: string;
    content: string;
    color: string;
    x: number;
    y: number;
    width: number;
    createdAt: number;
    source?: 'chat' | 'manual';
}

const STORAGE_KEY = 'ai-os-pinboard';
const NOTE_COLORS = [
    { name: 'Yellow', value: 'from-yellow-500/20 to-amber-500/10', border: 'border-yellow-500/30', dot: 'bg-yellow-400' },
    { name: 'Blue', value: 'from-blue-500/20 to-sky-500/10', border: 'border-blue-500/30', dot: 'bg-blue-400' },
    { name: 'Green', value: 'from-emerald-500/20 to-green-500/10', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
    { name: 'Purple', value: 'from-violet-500/20 to-purple-500/10', border: 'border-violet-500/30', dot: 'bg-violet-400' },
    { name: 'Pink', value: 'from-pink-500/20 to-rose-500/10', border: 'border-pink-500/30', dot: 'bg-pink-400' },
    { name: 'Orange', value: 'from-orange-500/20 to-amber-500/10', border: 'border-orange-500/30', dot: 'bg-orange-400' },
];

function loadNotes(): PinnedNote[] {
    if (typeof window === 'undefined') return [];
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch {
        return [];
    }
}

function saveNotes(notes: PinnedNote[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
}

function generateId(): string {
    return Math.random().toString(36).substring(2, 12);
}

// Hook to allow external pin-from-chat
export function usePinboard() {
    const pinMessage = useCallback((content: string) => {
        const notes = loadNotes();
        const note: PinnedNote = {
            id: generateId(),
            content,
            color: NOTE_COLORS[Math.floor(Math.random() * NOTE_COLORS.length)].value,
            x: 80 + Math.random() * 300,
            y: 80 + Math.random() * 200,
            width: 240,
            createdAt: Date.now(),
            source: 'chat',
        };
        notes.push(note);
        saveNotes(notes);
        window.dispatchEvent(new CustomEvent('ai-os:pinboard-updated'));
    }, []);

    return { pinMessage };
}

function NoteCard({
    note,
    onDelete,
    onMove,
    onColorChange,
}: {
    note: PinnedNote;
    onDelete: (id: string) => void;
    onMove: (id: string, x: number, y: number) => void;
    onColorChange: (id: string, color: string) => void;
}) {
    const [dragging, setDragging] = useState(false);
    const [showColors, setShowColors] = useState(false);
    const dragOffset = useRef({ x: 0, y: 0 });

    const colorObj = NOTE_COLORS.find(c => c.value === note.color) || NOTE_COLORS[0];

    const handleMouseDown = (e: React.MouseEvent) => {
        e.preventDefault();
        setDragging(true);
        dragOffset.current = {
            x: e.clientX - note.x,
            y: e.clientY - note.y,
        };
    };

    useEffect(() => {
        if (!dragging) return;

        const handleMouseMove = (e: MouseEvent) => {
            onMove(note.id, e.clientX - dragOffset.current.x, e.clientY - dragOffset.current.y);
        };

        const handleMouseUp = () => setDragging(false);

        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('mouseup', handleMouseUp);
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [dragging, note.id, onMove]);

    return (
        <div
            className={cn(
                'absolute rounded-xl border shadow-lg overflow-hidden group transition-shadow',
                `bg-gradient-to-br ${note.color} ${colorObj.border}`,
                dragging ? 'shadow-2xl scale-[1.03] cursor-grabbing z-50' : 'hover:shadow-xl cursor-grab'
            )}
            style={{
                left: note.x,
                top: note.y,
                width: note.width,
                animation: 'noteDropIn 300ms cubic-bezier(0.34,1.56,0.64,1)',
            }}
        >
            {/* Drag handle */}
            <div
                className="flex items-center justify-between px-3 py-1.5 border-b border-white/10"
                onMouseDown={handleMouseDown}
            >
                <GripVertical className="w-3.5 h-3.5 text-foreground/30" />
                <div className="flex items-center gap-1">
                    {note.source === 'chat' && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-primary/20 text-primary font-medium">chat</span>
                    )}
                    <button
                        onClick={() => setShowColors(!showColors)}
                        className="p-1 rounded hover:bg-white/10 text-foreground/40 hover:text-foreground/70 transition-colors"
                    >
                        <Palette className="w-3 h-3" />
                    </button>
                    <button
                        onClick={() => onDelete(note.id)}
                        className="p-1 rounded hover:bg-red-500/20 text-foreground/40 hover:text-red-400 transition-colors"
                    >
                        <Trash2 className="w-3 h-3" />
                    </button>
                </div>
            </div>

            {/* Color picker */}
            {showColors && (
                <div className="flex gap-1.5 px-3 py-2 border-b border-white/10" style={{ animation: 'noteSlide 150ms ease-out' }}>
                    {NOTE_COLORS.map(c => (
                        <button
                            key={c.name}
                            onClick={() => {
                                onColorChange(note.id, c.value);
                                setShowColors(false);
                            }}
                            className={cn('w-5 h-5 rounded-full transition-transform hover:scale-110', c.dot, note.color === c.value && 'ring-2 ring-white/50 scale-110')}
                            title={c.name}
                        />
                    ))}
                </div>
            )}

            {/* Content */}
            <div className="px-3 py-2.5 max-h-40 overflow-y-auto">
                <p className="text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap break-words">
                    {note.content.length > 300 ? note.content.slice(0, 300) + '...' : note.content}
                </p>
            </div>

            {/* Timestamp */}
            <div className="px-3 py-1.5 text-[9px] text-foreground/30">
                {new Date(note.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </div>
        </div>
    );
}

export function Pinboard() {
    const [open, setOpen] = useState(false);
    const [notes, setNotes] = useState<PinnedNote[]>([]);
    const [newNoteText, setNewNoteText] = useState('');

    useEffect(() => {
        setNotes(loadNotes());
    }, []);

    // Listen for updates from external pin actions
    useEffect(() => {
        const handleUpdate = () => setNotes(loadNotes());
        window.addEventListener('ai-os:pinboard-updated', handleUpdate);
        return () => window.removeEventListener('ai-os:pinboard-updated', handleUpdate);
    }, []);

    // Keyboard shortcut ⌘B
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
                e.preventDefault();
                setOpen(prev => !prev);
            }
        };
        const handleCustom = () => setOpen(true);
        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('ai-os:open-pinboard', handleCustom);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('ai-os:open-pinboard', handleCustom);
        };
    }, []);

    const handleDelete = useCallback((id: string) => {
        setNotes(prev => {
            const updated = prev.filter(n => n.id !== id);
            saveNotes(updated);
            return updated;
        });
    }, []);

    const handleMove = useCallback((id: string, x: number, y: number) => {
        setNotes(prev => {
            const updated = prev.map(n => (n.id === id ? { ...n, x, y } : n));
            saveNotes(updated);
            return updated;
        });
    }, []);

    const handleColorChange = useCallback((id: string, color: string) => {
        setNotes(prev => {
            const updated = prev.map(n => (n.id === id ? { ...n, color } : n));
            saveNotes(updated);
            return updated;
        });
    }, []);

    const handleAddNote = useCallback(() => {
        if (!newNoteText.trim()) return;
        const note: PinnedNote = {
            id: generateId(),
            content: newNoteText.trim(),
            color: NOTE_COLORS[Math.floor(Math.random() * NOTE_COLORS.length)].value,
            x: 100 + Math.random() * 400,
            y: 100 + Math.random() * 200,
            width: 240,
            createdAt: Date.now(),
            source: 'manual',
        };
        setNotes(prev => {
            const updated = [...prev, note];
            saveNotes(updated);
            return updated;
        });
        setNewNoteText('');
    }, [newNoteText]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50">
            <div
                className="absolute inset-0 bg-background/80 backdrop-blur-md animate-fade-in"
                onClick={() => setOpen(false)}
            />

            {/* Toolbar */}
            <div className="relative z-10 flex items-center justify-between px-6 py-3 border-b border-border bg-card/90 backdrop-blur-sm" style={{ animation: 'noteSlide 200ms ease-out' }}>
                <div className="flex items-center gap-3">
                    <Pin className="w-5 h-5 text-primary" />
                    <h2 className="font-semibold text-foreground text-sm">Pinboard</h2>
                    <span className="text-xs text-muted-foreground">
                        {notes.length} note{notes.length !== 1 ? 's' : ''}
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            value={newNoteText}
                            onChange={e => setNewNoteText(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleAddNote()}
                            placeholder="Quick note..."
                            className="px-3 py-1.5 rounded-lg bg-secondary border border-border text-xs w-48 focus:outline-none focus:ring-2 focus:ring-primary/30 placeholder:text-muted-foreground"
                        />
                        <button
                            onClick={handleAddNote}
                            disabled={!newNoteText.trim()}
                            className="p-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                        >
                            <Plus className="w-4 h-4" />
                        </button>
                    </div>
                    <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground">
                        <X className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Canvas */}
            <div className="relative z-10 w-full h-[calc(100vh-52px)] overflow-auto">
                {notes.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center" style={{ animation: 'noteDropIn 400ms ease-out' }}>
                        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                            <Pin className="w-8 h-8 text-primary/50" />
                        </div>
                        <h3 className="text-lg font-semibold text-foreground mb-1">No pinned notes yet</h3>
                        <p className="text-sm text-muted-foreground max-w-xs">
                            Pin messages from your chats or add quick notes using the field above.
                        </p>
                        <p className="text-xs text-muted-foreground mt-4">
                            <kbd className="px-1.5 py-0.5 bg-muted rounded font-mono text-[10px]">⌘B</kbd> to toggle
                        </p>
                    </div>
                ) : (
                    notes.map(note => (
                        <NoteCard
                            key={note.id}
                            note={note}
                            onDelete={handleDelete}
                            onMove={handleMove}
                            onColorChange={handleColorChange}
                        />
                    ))
                )}
            </div>

            <style jsx>{`
                @keyframes noteDropIn {
                    from { opacity: 0; transform: translateY(-15px) scale(0.9); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
                @keyframes noteSlide {
                    from { opacity: 0; transform: translateY(-8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
