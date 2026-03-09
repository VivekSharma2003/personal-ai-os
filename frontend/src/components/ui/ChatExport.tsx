'use client';

import { useState, useRef, useEffect } from 'react';
import { Download, Copy, Check, ChevronDown, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ExportMessage {
    role: 'user' | 'assistant';
    content: string;
}

interface ChatExportProps {
    messages: ExportMessage[];
    conversationTitle?: string;
}

function messagesToMarkdown(messages: ExportMessage[], title?: string): string {
    const lines: string[] = [];
    lines.push(`# ${title || 'Conversation'}`);
    lines.push(`> Exported from Personal AI OS on ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}`);
    lines.push('');
    lines.push('---');
    lines.push('');

    messages.forEach((msg) => {
        if (msg.role === 'user') {
            lines.push(`### 🧑 You`);
        } else {
            lines.push(`### ✨ AI`);
        }
        lines.push('');
        lines.push(msg.content);
        lines.push('');
    });

    return lines.join('\n');
}

export function ChatExport({ messages, conversationTitle }: ChatExportProps) {
    const [open, setOpen] = useState(false);
    const [copied, setCopied] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close on outside click
    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        if (open) document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [open]);

    const handleCopyMarkdown = async () => {
        const md = messagesToMarkdown(messages, conversationTitle);
        await navigator.clipboard.writeText(md);
        setCopied(true);
        setTimeout(() => { setCopied(false); setOpen(false); }, 1500);
    };

    const handleDownloadMarkdown = () => {
        const md = messagesToMarkdown(messages, conversationTitle);
        const blob = new Blob([md], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${(conversationTitle || 'conversation').replace(/[^a-z0-9]/gi, '_').toLowerCase()}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        setOpen(false);
    };

    if (messages.length === 0) return null;

    return (
        <div ref={dropdownRef} className="relative">
            <button
                onClick={() => setOpen(!open)}
                className={cn(
                    'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-smooth',
                    'text-muted-foreground hover:text-foreground hover:bg-accent',
                    open && 'bg-accent text-foreground'
                )}
                title="Export conversation"
            >
                <Download className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Export</span>
                <ChevronDown className={cn('w-3 h-3 transition-transform', open && 'rotate-180')} />
            </button>

            {open && (
                <div
                    className="absolute right-0 top-full mt-1 w-52 bg-card border border-border rounded-xl shadow-xl overflow-hidden z-50"
                    style={{ animation: 'dropdownIn 150ms ease-out' }}
                >
                    <div className="p-1">
                        <button
                            onClick={handleCopyMarkdown}
                            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm hover:bg-accent transition-colors text-left"
                        >
                            {copied ? (
                                <Check className="w-4 h-4 text-green-500" />
                            ) : (
                                <Copy className="w-4 h-4 text-muted-foreground" />
                            )}
                            <div>
                                <p className="font-medium text-foreground">
                                    {copied ? 'Copied!' : 'Copy as Markdown'}
                                </p>
                                <p className="text-xs text-muted-foreground">To clipboard</p>
                            </div>
                        </button>
                        <button
                            onClick={handleDownloadMarkdown}
                            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm hover:bg-accent transition-colors text-left"
                        >
                            <FileText className="w-4 h-4 text-muted-foreground" />
                            <div>
                                <p className="font-medium text-foreground">Download .md</p>
                                <p className="text-xs text-muted-foreground">Save as file</p>
                            </div>
                        </button>
                    </div>

                    <style jsx>{`
                        @keyframes dropdownIn {
                            from { opacity: 0; transform: translateY(-4px) scale(0.97); }
                            to { opacity: 1; transform: translateY(0) scale(1); }
                        }
                    `}</style>
                </div>
            )}
        </div>
    );
}
