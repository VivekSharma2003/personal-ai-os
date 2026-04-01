'use client';

import { useState } from 'react';
import { FileText, Copy, Check, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

interface ConversationSummaryProps {
    messages: Message[];
}

export function ConversationSummary({ messages }: ConversationSummaryProps) {
    const [open, setOpen] = useState(false);
    const [copied, setCopied] = useState(false);

    const generateSummary = () => {
        if (messages.length === 0) return '';

        const userMsgs = messages.filter((m) => m.role === 'user');
        const aiMsgs = messages.filter((m) => m.role === 'assistant');

        const topics = userMsgs.map((m) => {
            const text = m.content.trim();
            return text.length > 80 ? text.slice(0, 80) + '...' : text;
        });

        const lines: string[] = [];
        lines.push(`## Conversation Summary`);
        lines.push(`**${messages.length} messages** (${userMsgs.length} from you, ${aiMsgs.length} from AI)\n`);

        lines.push('### Topics Discussed');
        topics.forEach((t, i) => {
            lines.push(`${i + 1}. ${t}`);
        });

        if (aiMsgs.length > 0) {
            lines.push('\n### Key Points');
            aiMsgs.slice(0, 5).forEach((m) => {
                const firstSentence = m.content.split(/[.!?\n]/).filter(Boolean)[0] || '';
                if (firstSentence.trim()) {
                    lines.push(`- ${firstSentence.trim().slice(0, 120)}${firstSentence.length > 120 ? '...' : ''}`);
                }
            });
        }

        return lines.join('\n');
    };

    const summary = generateSummary();

    const handleCopy = async () => {
        await navigator.clipboard.writeText(summary);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    if (messages.length === 0) return null;

    return (
        <>
            <button
                onClick={() => setOpen(true)}
                className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-smooth"
                title="Conversation Summary"
            >
                <FileText className="w-4 h-4" />
            </button>

            {open && (
                <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
                    <div
                        className="absolute inset-0 bg-background/60 backdrop-blur-sm"
                        onClick={() => setOpen(false)}
                    />
                    <div
                        className="relative max-w-md mx-auto mt-[12vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                        style={{ animation: 'slideUp 200ms ease-out' }}
                    >
                        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
                            <div className="flex items-center gap-2">
                                <FileText className="w-4 h-4 text-primary" />
                                <h3 className="text-sm font-semibold text-foreground">Summary</h3>
                            </div>
                            <div className="flex items-center gap-1">
                                <button
                                    onClick={handleCopy}
                                    className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-smooth"
                                    title="Copy summary"
                                >
                                    {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                                </button>
                                <button
                                    onClick={() => setOpen(false)}
                                    className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-smooth"
                                >
                                    <X className="w-3.5 h-3.5" />
                                </button>
                            </div>
                        </div>
                        <div className="p-5 max-h-[50vh] overflow-y-auto">
                            <pre className="text-sm text-foreground whitespace-pre-wrap leading-relaxed font-sans">
                                {summary}
                            </pre>
                        </div>
                    </div>

                    <style jsx>{`
                        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                        @keyframes slideUp { from { opacity: 0; transform: translateY(10px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
                    `}</style>
                </div>
            )}
        </>
    );
}
