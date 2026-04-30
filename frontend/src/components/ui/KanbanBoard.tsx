'use client';

import { useState, useEffect, useRef } from 'react';
import { X, Clock, Trash2, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-kanban';

interface KanbanCard {
    id: string;
    text: string;
    color: string;
    createdAt: string;
}

interface KanbanData {
    todo: KanbanCard[];
    doing: KanbanCard[];
    done: KanbanCard[];
}

const CARD_COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899'];
const COLUMNS: (keyof KanbanData)[] = ['todo', 'doing', 'done'];
const COL_LABELS: Record<string, { label: string; emoji: string; color: string }> = {
    todo: { label: 'To Do', emoji: '📋', color: 'text-blue-400' },
    doing: { label: 'In Progress', emoji: '🔨', color: 'text-amber-400' },
    done: { label: 'Done', emoji: '✅', color: 'text-emerald-400' },
};

function load(): KanbanData { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{"todo":[],"doing":[],"done":[]}'); } catch { return {todo:[],doing:[],done:[]}; } }
function save(d: KanbanData) { localStorage.setItem(STORAGE_KEY, JSON.stringify(d)); }

export function KanbanBoard() {
    const [open, setOpen] = useState(false);
    const [data, setData] = useState<KanbanData>({todo:[],doing:[],done:[]});
    const [addingTo, setAddingTo] = useState<keyof KanbanData | null>(null);
    const [newText, setNewText] = useState('');
    const [newColor, setNewColor] = useState(CARD_COLORS[0]);
    const [dragItem, setDragItem] = useState<{col: keyof KanbanData; id: string} | null>(null);

    useEffect(() => {
        const handler = () => { setOpen(true); setData(load()); };
        window.addEventListener('ai-os:open-kanban', handler);
        return () => window.removeEventListener('ai-os:open-kanban', handler);
    }, []);

    const addCard = (col: keyof KanbanData) => {
        if (!newText.trim()) return;
        const card: KanbanCard = { id: Date.now().toString(36), text: newText.trim(), color: newColor, createdAt: new Date().toISOString() };
        const updated = { ...data, [col]: [...data[col], card] };
        setData(updated); save(updated);
        setNewText(''); setAddingTo(null);
    };

    const deleteCard = (col: keyof KanbanData, id: string) => {
        const updated = { ...data, [col]: data[col].filter(c => c.id !== id) };
        setData(updated); save(updated);
    };

    const moveCard = (fromCol: keyof KanbanData, id: string, toCol: keyof KanbanData) => {
        const card = data[fromCol].find(c => c.id === id);
        if (!card || fromCol === toCol) return;
        const updated = {
            ...data,
            [fromCol]: data[fromCol].filter(c => c.id !== id),
            [toCol]: [...data[toCol], card],
        };
        setData(updated); save(updated);
    };

    const handleDragStart = (col: keyof KanbanData, id: string) => { setDragItem({col, id}); };
    const handleDrop = (toCol: keyof KanbanData) => {
        if (dragItem) { moveCard(dragItem.col, dragItem.id, toCol); setDragItem(null); }
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{animation:'fadeIn 150ms ease-out'}}>
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" onClick={()=>setOpen(false)}/>
            <div className="relative w-[90vw] max-w-3xl mx-auto mt-[8vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden" style={{animation:'slideUp 200ms ease-out'}}>
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500/20 to-violet-500/10 flex items-center justify-center">
                            <Clock className="w-4 h-4 text-indigo-400"/>
                        </div>
                        <h2 className="font-semibold text-foreground">Kanban Board</h2>
                    </div>
                    <button onClick={()=>setOpen(false)} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"><X className="w-4 h-4"/></button>
                </div>

                <div className="grid grid-cols-3 gap-3 p-4" style={{minHeight:'50vh'}}>
                    {COLUMNS.map(col => {
                        const info = COL_LABELS[col];
                        return (
                            <div key={col}
                                className={cn('rounded-xl p-3 bg-secondary/30 border border-border/50 flex flex-col', dragItem && dragItem.col !== col && 'ring-1 ring-primary/20')}
                                onDragOver={e => e.preventDefault()}
                                onDrop={() => handleDrop(col)}>
                                <div className="flex items-center gap-1.5 mb-3">
                                    <span>{info.emoji}</span>
                                    <span className={cn('text-xs font-semibold', info.color)}>{info.label}</span>
                                    <span className="text-[10px] text-muted-foreground/60 ml-auto">{data[col].length}</span>
                                </div>

                                <div className="flex-1 space-y-2 min-h-[100px]">
                                    {data[col].map(card => (
                                        <div key={card.id} draggable
                                            onDragStart={() => handleDragStart(col, card.id)}
                                            className="p-2.5 rounded-lg bg-card border border-border shadow-sm cursor-grab active:cursor-grabbing group hover:shadow-md transition-shadow">
                                            <div className="flex items-start gap-2">
                                                <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{backgroundColor: card.color}}/>
                                                <p className="text-xs text-foreground flex-1 leading-relaxed">{card.text}</p>
                                                <button onClick={() => deleteCard(col, card.id)} className="p-0.5 text-muted-foreground/30 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"><Trash2 className="w-3 h-3"/></button>
                                            </div>
                                            {/* Quick move buttons */}
                                            <div className="flex gap-1 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                                {COLUMNS.filter(c => c !== col).map(target => (
                                                    <button key={target} onClick={() => moveCard(col, card.id, target)}
                                                        className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground hover:text-foreground transition-colors">
                                                        → {COL_LABELS[target].label}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {addingTo === col ? (
                                    <div className="mt-2 space-y-2" style={{animation:'slideUp 150ms ease-out'}}>
                                        <textarea value={newText} onChange={e=>setNewText(e.target.value)} placeholder="Task..."
                                            className="w-full px-2.5 py-2 rounded-lg bg-background border border-border text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary resize-none" rows={2} autoFocus/>
                                        <div className="flex items-center gap-1">
                                            {CARD_COLORS.map(c => (<button key={c} onClick={()=>setNewColor(c)} className={cn('w-4 h-4 rounded-full border',newColor===c?'border-primary scale-110':'border-transparent')} style={{backgroundColor:c}}/>))}
                                        </div>
                                        <div className="flex gap-1.5">
                                            <button onClick={()=>addCard(col)} disabled={!newText.trim()} className="flex-1 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium disabled:opacity-40 transition-all">Add</button>
                                            <button onClick={()=>{setAddingTo(null);setNewText('');}} className="px-3 py-1.5 rounded-lg bg-secondary text-xs text-foreground hover:bg-accent transition-colors">Cancel</button>
                                        </div>
                                    </div>
                                ) : (
                                    <button onClick={()=>{setAddingTo(col);setNewColor(CARD_COLORS[Math.floor(Math.random()*CARD_COLORS.length)]);}}
                                        className="mt-2 w-full py-1.5 rounded-lg border border-dashed border-border text-[10px] text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all">
                                        + Add Card
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
            <style jsx>{`@keyframes fadeIn{from{opacity:0}to{opacity:1}}@keyframes slideUp{from{opacity:0;transform:translateY(10px) scale(0.98)}to{opacity:1;transform:translateY(0) scale(1)}}`}</style>
        </div>
    );
}
