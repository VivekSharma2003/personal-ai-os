'use client';

import { useState, useEffect, useCallback } from 'react';
import { X, Plus, Trash2, RotateCcw, ChevronLeft, ChevronRight, Sparkles, BookOpen, Shuffle } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-flashcards';

interface Flashcard {
    id: string;
    front: string;
    back: string;
    deck: string;
    createdAt: string;
    lastReviewed?: string;
    reviewCount: number;
    confidence: number; // 0-3 (again, hard, good, easy)
}

function loadCards(): Flashcard[] {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch { return []; }
}

function saveCards(cards: Flashcard[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cards));
}

// Extract flashcards from AI text content
function autoExtract(text: string): { front: string; back: string }[] {
    const cards: { front: string; back: string }[] = [];

    // Pattern 1: "**Term**: Definition"
    const boldPattern = /\*\*(.+?)\*\*[:\-–]\s*(.+?)(?:\n|$)/g;
    let match;
    while ((match = boldPattern.exec(text)) !== null) {
        if (match[1].length < 100 && match[2].length < 300) {
            cards.push({ front: match[1].trim(), back: match[2].trim() });
        }
    }

    // Pattern 2: Numbered list items with colons "1. Term: Definition"
    const listPattern = /\d+\.\s+(.+?)[:\-–]\s+(.+?)(?:\n|$)/g;
    while ((match = listPattern.exec(text)) !== null) {
        const front = match[1].replace(/\*\*/g, '').trim();
        const back = match[2].trim();
        if (front.length < 100 && back.length < 300 && !cards.some(c => c.front === front)) {
            cards.push({ front, back });
        }
    }

    return cards.slice(0, 10); // Cap at 10
}

export function useFlashcardExtractor() {
    const addFromContent = useCallback((content: string) => {
        const extracted = autoExtract(content);
        if (extracted.length === 0) return 0;

        const cards = loadCards();
        let added = 0;
        for (const { front, back } of extracted) {
            if (!cards.some(c => c.front === front)) {
                cards.push({
                    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
                    front,
                    back,
                    deck: 'Auto-Extracted',
                    createdAt: new Date().toISOString(),
                    reviewCount: 0,
                    confidence: 0,
                });
                added++;
            }
        }
        if (added > 0) saveCards(cards);
        return added;
    }, []);

    return { addFromContent };
}

export function Flashcards() {
    const [open, setOpen] = useState(false);
    const [cards, setCards] = useState<Flashcard[]>([]);
    const [view, setView] = useState<'browse' | 'study' | 'add'>('browse');
    const [currentIdx, setCurrentIdx] = useState(0);
    const [flipped, setFlipped] = useState(false);
    const [newFront, setNewFront] = useState('');
    const [newBack, setNewBack] = useState('');
    const [newDeck, setNewDeck] = useState('General');

    useEffect(() => {
        const handler = () => { setOpen(true); setCards(loadCards()); };
        window.addEventListener('ai-os:open-flashcards', handler);
        return () => window.removeEventListener('ai-os:open-flashcards', handler);
    }, []);

    const studyCards = cards.length > 0
        ? [...cards].sort((a, b) => a.confidence - b.confidence)
        : [];

    const handleAdd = () => {
        if (!newFront.trim() || !newBack.trim()) return;
        const card: Flashcard = {
            id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
            front: newFront.trim(),
            back: newBack.trim(),
            deck: newDeck || 'General',
            createdAt: new Date().toISOString(),
            reviewCount: 0,
            confidence: 0,
        };
        const updated = [...cards, card];
        setCards(updated);
        saveCards(updated);
        setNewFront('');
        setNewBack('');
    };

    const handleDelete = (id: string) => {
        const updated = cards.filter(c => c.id !== id);
        setCards(updated);
        saveCards(updated);
        if (currentIdx >= updated.length) setCurrentIdx(Math.max(0, updated.length - 1));
    };

    const handleRate = (confidence: number) => {
        const updated = cards.map(c =>
            c.id === studyCards[currentIdx]?.id
                ? { ...c, confidence, reviewCount: c.reviewCount + 1, lastReviewed: new Date().toISOString() }
                : c
        );
        setCards(updated);
        saveCards(updated);
        setFlipped(false);

        if (currentIdx < studyCards.length - 1) {
            setCurrentIdx(currentIdx + 1);
        } else {
            setView('browse');
            setCurrentIdx(0);
        }
    };

    const handleShuffle = () => {
        setCurrentIdx(0);
        setFlipped(false);
    };

    const decks = Array.from(new Set(cards.map(c => c.deck)));

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" onClick={() => setOpen(false)} />

            <div
                className="relative max-w-lg mx-auto mt-[10vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                style={{ animation: 'slideUp 200ms ease-out' }}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500/20 to-purple-500/10 flex items-center justify-center">
                            <BookOpen className="w-4 h-4 text-violet-400" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-foreground">Flashcards</h2>
                            <p className="text-[10px] text-muted-foreground">{cards.length} cards in {decks.length || 1} deck{decks.length !== 1 ? 's' : ''}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-1">
                        {['browse', 'study', 'add'].map(v => (
                            <button
                                key={v}
                                onClick={() => { setView(v as any); setCurrentIdx(0); setFlipped(false); }}
                                className={cn(
                                    'px-2.5 py-1 text-xs rounded-md font-medium transition-colors capitalize',
                                    view === v ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                                )}
                            >
                                {v}
                            </button>
                        ))}
                        <button onClick={() => setOpen(false)} className="p-1.5 ml-1 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-5 max-h-[60vh] overflow-y-auto">
                    {view === 'browse' && (
                        cards.length === 0 ? (
                            <div className="text-center py-10">
                                <BookOpen className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                                <p className="text-sm text-muted-foreground">No flashcards yet</p>
                                <p className="text-xs text-muted-foreground/60 mt-1">Add cards manually or auto-extract from AI responses</p>
                                <button onClick={() => setView('add')} className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors">
                                    <Plus className="w-3.5 h-3.5 inline mr-1.5" />Create Card
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {cards.map(card => (
                                    <div key={card.id} className="flex items-start gap-3 p-3 rounded-lg bg-secondary/50 border border-border group hover:bg-accent/50 transition-colors">
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-foreground truncate">{card.front}</p>
                                            <p className="text-xs text-muted-foreground truncate mt-0.5">{card.back}</p>
                                            <div className="flex items-center gap-2 mt-1.5">
                                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium">{card.deck}</span>
                                                <span className="text-[10px] text-muted-foreground/60">Reviewed {card.reviewCount}×</span>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => handleDelete(card.id)}
                                            className="p-1 rounded text-muted-foreground/40 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                                        >
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                ))}
                                {cards.length >= 2 && (
                                    <button
                                        onClick={() => { setView('study'); handleShuffle(); }}
                                        className="w-full mt-3 px-4 py-2.5 rounded-lg bg-gradient-to-r from-violet-500 to-purple-600 text-white text-sm font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                                    >
                                        <Sparkles className="w-4 h-4" /> Study Now
                                    </button>
                                )}
                            </div>
                        )
                    )}

                    {view === 'study' && studyCards.length > 0 && (
                        <div className="flex flex-col items-center">
                            <p className="text-xs text-muted-foreground mb-4">Card {currentIdx + 1} of {studyCards.length}</p>

                            {/* Card with flip */}
                            <div
                                className="relative w-full h-48 cursor-pointer"
                                onClick={() => setFlipped(!flipped)}
                                style={{ perspective: '1000px' }}
                            >
                                <div
                                    className="absolute inset-0 transition-transform duration-500"
                                    style={{
                                        transformStyle: 'preserve-3d',
                                        transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
                                    }}
                                >
                                    {/* Front */}
                                    <div
                                        className="absolute inset-0 rounded-xl bg-gradient-to-br from-violet-500/10 to-purple-500/5 border border-violet-500/20 flex flex-col items-center justify-center p-6"
                                        style={{ backfaceVisibility: 'hidden' }}
                                    >
                                        <p className="text-lg font-semibold text-foreground text-center">{studyCards[currentIdx]?.front}</p>
                                        <p className="text-[10px] text-muted-foreground/50 mt-4">Tap to reveal</p>
                                    </div>

                                    {/* Back */}
                                    <div
                                        className="absolute inset-0 rounded-xl bg-gradient-to-br from-emerald-500/10 to-teal-500/5 border border-emerald-500/20 flex flex-col items-center justify-center p-6"
                                        style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
                                    >
                                        <p className="text-sm text-foreground text-center leading-relaxed">{studyCards[currentIdx]?.back}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Rating buttons */}
                            {flipped && (
                                <div className="flex items-center gap-2 mt-5" style={{ animation: 'slideUp 200ms ease-out' }}>
                                    <p className="text-xs text-muted-foreground mr-2">How well did you know it?</p>
                                    {[
                                        { label: 'Again', value: 0, color: 'bg-red-500/80' },
                                        { label: 'Hard', value: 1, color: 'bg-orange-500/80' },
                                        { label: 'Good', value: 2, color: 'bg-blue-500/80' },
                                        { label: 'Easy', value: 3, color: 'bg-emerald-500/80' },
                                    ].map(r => (
                                        <button
                                            key={r.label}
                                            onClick={() => handleRate(r.value)}
                                            className={cn('px-3 py-1.5 rounded-lg text-white text-xs font-medium hover:opacity-80 transition-opacity', r.color)}
                                        >
                                            {r.label}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* Nav */}
                            <div className="flex items-center gap-3 mt-4">
                                <button
                                    disabled={currentIdx <= 0}
                                    onClick={() => { setCurrentIdx(currentIdx - 1); setFlipped(false); }}
                                    className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground disabled:opacity-30 transition-colors"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => { setCurrentIdx(0); setFlipped(false); }}
                                    className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground transition-colors"
                                    title="Restart"
                                >
                                    <RotateCcw className="w-4 h-4" />
                                </button>
                                <button
                                    disabled={currentIdx >= studyCards.length - 1}
                                    onClick={() => { setCurrentIdx(currentIdx + 1); setFlipped(false); }}
                                    className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground disabled:opacity-30 transition-colors"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    )}

                    {view === 'add' && (
                        <div className="space-y-3">
                            <div>
                                <label className="text-xs font-medium text-muted-foreground mb-1 block">Front (Question)</label>
                                <input
                                    value={newFront}
                                    onChange={e => setNewFront(e.target.value)}
                                    placeholder="e.g. What is photosynthesis?"
                                    className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-medium text-muted-foreground mb-1 block">Back (Answer)</label>
                                <textarea
                                    value={newBack}
                                    onChange={e => setNewBack(e.target.value)}
                                    placeholder="e.g. The process by which plants convert light into energy..."
                                    rows={3}
                                    className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-medium text-muted-foreground mb-1 block">Deck</label>
                                <input
                                    value={newDeck}
                                    onChange={e => setNewDeck(e.target.value)}
                                    placeholder="General"
                                    className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
                                />
                            </div>
                            <button
                                onClick={handleAdd}
                                disabled={!newFront.trim() || !newBack.trim()}
                                className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-40 transition-all flex items-center justify-center gap-2"
                            >
                                <Plus className="w-4 h-4" /> Add Card
                            </button>
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
