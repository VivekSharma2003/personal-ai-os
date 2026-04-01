'use client';

import { useState, useEffect, useRef } from 'react';
import { Slash, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SlashCommand {
    id: string;
    label: string;
    description: string;
    prefix: string;
}

const COMMANDS: SlashCommand[] = [
    { id: 'summarize', label: '/summarize', description: 'Summarize the following text', prefix: 'Please summarize this concisely:\n\n' },
    { id: 'translate', label: '/translate', description: 'Translate to another language', prefix: 'Translate the following to ' },
    { id: 'bullet', label: '/bullet', description: 'Convert to bullet points', prefix: 'Convert this into clear bullet points:\n\n' },
    { id: 'eli5', label: '/eli5', description: 'Explain like I\'m 5', prefix: 'Explain this in simple terms a child would understand:\n\n' },
    { id: 'code', label: '/code', description: 'Write code for this', prefix: 'Write code to implement the following:\n\n' },
    { id: 'fix', label: '/fix', description: 'Fix grammar and spelling', prefix: 'Fix the grammar, spelling, and improve clarity:\n\n' },
    { id: 'pros', label: '/pros', description: 'List pros and cons', prefix: 'List the pros and cons of:\n\n' },
    { id: 'steps', label: '/steps', description: 'Break into steps', prefix: 'Break this down into clear step-by-step instructions:\n\n' },
];

interface SlashCommandsProps {
    input: string;
    onSelect: (prefix: string) => void;
}

export function SlashCommands({ input, onSelect }: SlashCommandsProps) {
    const [visible, setVisible] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const panelRef = useRef<HTMLDivElement>(null);

    const trimmed = input.trim().toLowerCase();
    const isSlashCommand = trimmed.startsWith('/') && !trimmed.includes(' ');
    const query = isSlashCommand ? trimmed.slice(1) : '';

    const filtered = isSlashCommand
        ? COMMANDS.filter((cmd) => cmd.id.startsWith(query) || cmd.label.startsWith(trimmed))
        : [];

    useEffect(() => {
        setVisible(isSlashCommand && filtered.length > 0);
        setSelectedIndex(0);
    }, [input, isSlashCommand, filtered.length]);

    useEffect(() => {
        if (!visible) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex((prev) => Math.min(prev + 1, filtered.length - 1));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex((prev) => Math.max(prev - 1, 0));
            } else if (e.key === 'Tab' || e.key === 'Enter') {
                if (visible && filtered.length > 0) {
                    e.preventDefault();
                    onSelect(filtered[selectedIndex].prefix);
                    setVisible(false);
                }
            } else if (e.key === 'Escape') {
                setVisible(false);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [visible, filtered, selectedIndex, onSelect]);

    if (!visible || filtered.length === 0) return null;

    return (
        <div
            ref={panelRef}
            className="absolute bottom-full left-0 right-0 mb-2 bg-card border border-border rounded-xl shadow-2xl overflow-hidden z-50"
            style={{ animation: 'slashIn 150ms ease-out' }}
        >
            <div className="px-3 py-2 border-b border-border">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                    <Slash className="w-3 h-3" />
                    Quick Commands
                </p>
            </div>
            <div className="p-1 max-h-48 overflow-y-auto">
                {filtered.map((cmd, i) => (
                    <button
                        key={cmd.id}
                        onClick={() => {
                            onSelect(cmd.prefix);
                            setVisible(false);
                        }}
                        className={cn(
                            'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors',
                            i === selectedIndex ? 'bg-accent' : 'hover:bg-accent/50'
                        )}
                    >
                        <code className="text-xs font-mono text-primary font-medium">{cmd.label}</code>
                        <span className="text-xs text-muted-foreground flex-1">{cmd.description}</span>
                        {i === selectedIndex && <ArrowRight className="w-3 h-3 text-muted-foreground" />}
                    </button>
                ))}
            </div>
            <div className="px-3 py-1.5 border-t border-border">
                <p className="text-[10px] text-muted-foreground">
                    <kbd className="px-1 py-0.5 bg-muted rounded font-mono">Tab</kbd> to select ·{' '}
                    <kbd className="px-1 py-0.5 bg-muted rounded font-mono">↑↓</kbd> to navigate
                </p>
            </div>

            <style jsx>{`
                @keyframes slashIn {
                    from { opacity: 0; transform: translateY(4px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
