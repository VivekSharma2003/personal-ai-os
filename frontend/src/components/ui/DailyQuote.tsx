'use client';

import { useState, useEffect, useMemo } from 'react';
import { X, Quote, RefreshCw, Copy, Check, Heart } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-quote-faves';

const QUOTES = [
    { text: "The only way to do great work is to love what you do.", author: "Steve Jobs" },
    { text: "Innovation distinguishes between a leader and a follower.", author: "Steve Jobs" },
    { text: "Stay hungry, stay foolish.", author: "Steve Jobs" },
    { text: "Simplicity is the ultimate sophistication.", author: "Leonardo da Vinci" },
    { text: "The best time to plant a tree was 20 years ago. The second best time is now.", author: "Chinese Proverb" },
    { text: "Your time is limited, don't waste it living someone else's life.", author: "Steve Jobs" },
    { text: "The future belongs to those who believe in the beauty of their dreams.", author: "Eleanor Roosevelt" },
    { text: "It is during our darkest moments that we must focus to see the light.", author: "Aristotle" },
    { text: "Do what you can, with what you have, where you are.", author: "Theodore Roosevelt" },
    { text: "Believe you can and you're halfway there.", author: "Theodore Roosevelt" },
    { text: "The only impossible journey is the one you never begin.", author: "Tony Robbins" },
    { text: "Success is not final, failure is not fatal: it is the courage to continue that counts.", author: "Winston Churchill" },
    { text: "In the middle of difficulty lies opportunity.", author: "Albert Einstein" },
    { text: "What we think, we become.", author: "Buddha" },
    { text: "Act as if what you do makes a difference. It does.", author: "William James" },
    { text: "The mind is everything. What you think you become.", author: "Buddha" },
    { text: "Strive not to be a success, but rather to be of value.", author: "Albert Einstein" },
    { text: "You miss 100% of the shots you don't take.", author: "Wayne Gretzky" },
    { text: "Whether you think you can or you think you can't, you're right.", author: "Henry Ford" },
    { text: "The purpose of our lives is to be happy.", author: "Dalai Lama" },
    { text: "Life is what happens when you're busy making other plans.", author: "John Lennon" },
    { text: "Get busy living or get busy dying.", author: "Stephen King" },
    { text: "The unexamined life is not worth living.", author: "Socrates" },
    { text: "Everything you've ever wanted is on the other side of fear.", author: "George Addair" },
    { text: "We suffer more often in imagination than in reality.", author: "Seneca" },
];

const GRADIENTS = [
    'from-violet-600/20 to-purple-600/10',
    'from-blue-600/20 to-cyan-600/10',
    'from-emerald-600/20 to-teal-600/10',
    'from-rose-600/20 to-pink-600/10',
    'from-amber-600/20 to-orange-600/10',
];

export function DailyQuote() {
    const [open, setOpen] = useState(false);
    const [index, setIndex] = useState(0);
    const [copied, setCopied] = useState(false);
    const [favorites, setFavorites] = useState<number[]>([]);

    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('ai-os:open-quotes', handler);
        return () => window.removeEventListener('ai-os:open-quotes', handler);
    }, []);

    useEffect(() => {
        if (open) {
            // Pick a "daily" quote based on date
            const day = new Date().getDate() + new Date().getMonth() * 31;
            setIndex(day % QUOTES.length);
            try { setFavorites(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')); } catch {}
        }
    }, [open]);

    const quote = QUOTES[index];
    const gradient = GRADIENTS[index % GRADIENTS.length];
    const isFav = favorites.includes(index);

    const shuffle = () => {
        let next = index;
        while (next === index) next = Math.floor(Math.random() * QUOTES.length);
        setIndex(next);
        setCopied(false);
    };

    const copyQuote = () => {
        navigator.clipboard.writeText(`"${quote.text}" — ${quote.author}`);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const toggleFav = () => {
        const updated = isFav ? favorites.filter(f => f !== index) : [...favorites, index];
        setFavorites(updated);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{animation:'fadeIn 150ms ease-out'}}>
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" onClick={()=>setOpen(false)}/>
            <div className="relative max-w-md mx-auto mt-[15vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden" style={{animation:'slideUp 200ms ease-out'}}>
                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/10 flex items-center justify-center">
                            <Quote className="w-4 h-4 text-amber-400"/>
                        </div>
                        <h2 className="font-semibold text-foreground">Daily Quote</h2>
                    </div>
                    <button onClick={()=>setOpen(false)} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"><X className="w-4 h-4"/></button>
                </div>

                <div className={cn('p-8 bg-gradient-to-br', gradient)}>
                    <blockquote className="text-lg font-medium text-foreground leading-relaxed italic">
                        &ldquo;{quote.text}&rdquo;
                    </blockquote>
                    <p className="text-sm text-muted-foreground mt-4">— {quote.author}</p>
                </div>

                <div className="flex items-center justify-between px-5 py-3 border-t border-border">
                    <div className="flex items-center gap-1">
                        <button onClick={toggleFav} className={cn('p-2 rounded-lg transition-colors', isFav ? 'text-red-400' : 'text-muted-foreground hover:text-red-400')}>
                            <Heart className={cn('w-4 h-4', isFav && 'fill-current')}/>
                        </button>
                        <button onClick={copyQuote} className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
                            {copied ? <Check className="w-4 h-4 text-emerald-400"/> : <Copy className="w-4 h-4"/>}
                        </button>
                    </div>
                    <button onClick={shuffle} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
                        <RefreshCw className="w-3.5 h-3.5"/> New Quote
                    </button>
                </div>
            </div>
            <style jsx>{`@keyframes fadeIn{from{opacity:0}to{opacity:1}}@keyframes slideUp{from{opacity:0;transform:translateY(10px) scale(0.98)}to{opacity:1;transform:translateY(0) scale(1)}}`}</style>
        </div>
    );
}
