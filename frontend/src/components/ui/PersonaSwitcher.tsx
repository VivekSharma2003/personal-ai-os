'use client';

import { useState, useEffect, useRef } from 'react';
import { ChevronDown, Sparkles, Code2, Zap, Heart, Briefcase } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-persona';

export interface Persona {
    id: string;
    label: string;
    description: string;
    icon: typeof Sparkles;
    color: string;
    systemPrompt: string;
}

export const PERSONAS: Persona[] = [
    {
        id: 'default',
        label: 'Balanced',
        description: 'Clear and helpful responses',
        icon: Sparkles,
        color: 'text-emerald-400 bg-emerald-500/10',
        systemPrompt: '',
    },
    {
        id: 'creative',
        label: 'Creative',
        description: 'Imaginative and expressive',
        icon: Heart,
        color: 'text-pink-400 bg-pink-500/10',
        systemPrompt: 'Be creative, use vivid language, metaphors, and an engaging tone.',
    },
    {
        id: 'technical',
        label: 'Technical',
        description: 'Precise and detailed',
        icon: Code2,
        color: 'text-blue-400 bg-blue-500/10',
        systemPrompt: 'Be technical and precise. Use exact terminology, include code examples when relevant, and be thorough.',
    },
    {
        id: 'concise',
        label: 'Concise',
        description: 'Brief and to the point',
        icon: Zap,
        color: 'text-amber-400 bg-amber-500/10',
        systemPrompt: 'Be extremely concise. Use short sentences, bullet points, and minimal filler words.',
    },
    {
        id: 'professional',
        label: 'Professional',
        description: 'Formal and business-like',
        icon: Briefcase,
        color: 'text-violet-400 bg-violet-500/10',
        systemPrompt: 'Use a professional, business-appropriate tone. Be structured and formal.',
    },
];

function getStoredPersona(): string {
    if (typeof window === 'undefined') return 'default';
    return localStorage.getItem(STORAGE_KEY) || 'default';
}

export function usePersona() {
    const [personaId, setPersonaId] = useState('default');

    useEffect(() => {
        setPersonaId(getStoredPersona());
    }, []);

    const setPersona = (id: string) => {
        setPersonaId(id);
        localStorage.setItem(STORAGE_KEY, id);
    };

    const activePersona = PERSONAS.find((p) => p.id === personaId) || PERSONAS[0];

    return { personaId, setPersona, activePersona };
}

export function PersonaSwitcher() {
    const [open, setOpen] = useState(false);
    const { activePersona, setPersona } = usePersona();
    const dropdownRef = useRef<HTMLDivElement>(null);
    const Icon = activePersona.icon;

    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        if (open) document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [open]);

    return (
        <div ref={dropdownRef} className="relative">
            <button
                onClick={() => setOpen(!open)}
                className={cn(
                    'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-smooth',
                    'text-muted-foreground hover:text-foreground hover:bg-accent',
                    open && 'bg-accent text-foreground'
                )}
                title="Switch AI persona"
            >
                <div className={cn('w-4 h-4 rounded flex items-center justify-center', activePersona.color)}>
                    <Icon className="w-2.5 h-2.5" />
                </div>
                <span className="hidden sm:inline">{activePersona.label}</span>
                <ChevronDown className={cn('w-3 h-3 transition-transform', open && 'rotate-180')} />
            </button>

            {open && (
                <div
                    className="absolute right-0 top-full mt-1 w-56 bg-card border border-border rounded-xl shadow-xl overflow-hidden z-50"
                    style={{ animation: 'personaIn 150ms ease-out' }}
                >
                    <div className="p-1">
                        {PERSONAS.map((persona) => {
                            const PIcon = persona.icon;
                            return (
                                <button
                                    key={persona.id}
                                    onClick={() => {
                                        setPersona(persona.id);
                                        setOpen(false);
                                    }}
                                    className={cn(
                                        'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors text-left',
                                        'hover:bg-accent',
                                        activePersona.id === persona.id && 'bg-accent'
                                    )}
                                >
                                    <div className={cn('w-7 h-7 rounded-md flex items-center justify-center', persona.color)}>
                                        <PIcon className="w-3.5 h-3.5" />
                                    </div>
                                    <div>
                                        <p className="font-medium text-foreground text-xs">{persona.label}</p>
                                        <p className="text-[10px] text-muted-foreground">{persona.description}</p>
                                    </div>
                                </button>
                            );
                        })}
                    </div>

                    <style jsx>{`
                        @keyframes personaIn {
                            from { opacity: 0; transform: translateY(-4px) scale(0.97); }
                            to { opacity: 1; transform: translateY(0) scale(1); }
                        }
                    `}</style>
                </div>
            )}
        </div>
    );
}
