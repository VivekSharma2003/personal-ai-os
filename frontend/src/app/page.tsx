'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { api, ChatResponse, FeedbackResponse } from '@/lib/api';
import { cn, generateId } from '@/lib/utils';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    rulesApplied?: number;
    interactionId?: string;
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [correctionMode, setCorrectionMode] = useState<string | null>(null);
    const [correctionText, setCorrectionText] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const { toast } = useToast();
    const conversationId = useRef(generateId());

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            id: generateId(),
            role: 'user',
            content: input.trim(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response: ChatResponse = await api.chat(
                userMessage.content,
                conversationId.current
            );

            const assistantMessage: Message = {
                id: generateId(),
                role: 'assistant',
                content: response.response,
                rulesApplied: response.rules_applied,
                interactionId: response.interaction_id,
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to get response. Please try again.',
                variant: 'destructive',
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleCorrection = async (interactionId: string) => {
        if (!correctionText.trim()) return;

        try {
            const response: FeedbackResponse = await api.feedback(
                interactionId,
                correctionText.trim()
            );

            if (response.status === 'rule_created' || response.status === 'rule_reinforced') {
                toast({
                    title: '✓ Preference Learned',
                    description: response.message,
                    variant: 'success',
                });
            } else {
                toast({
                    title: 'Feedback Received',
                    description: response.message,
                });
            }
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to submit feedback.',
                variant: 'destructive',
            });
        }

        setCorrectionMode(null);
        setCorrectionText('');
    };

    return (
        <div className="flex flex-col h-full bg-background">
            {/* Header */}
            <header className="px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                        <MessageSquare className="w-4 h-4 text-primary" />
                    </div>
                    <div>
                        <h1 className="font-semibold text-foreground">Chat</h1>
                        <p className="text-xs text-muted-foreground">
                            Your preferences are applied automatically
                        </p>
                    </div>
                </div>
            </header>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto">
                <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-[60vh] text-center">
                            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mb-5">
                                <Sparkles className="w-7 h-7 text-primary" />
                            </div>
                            <h2 className="text-xl font-semibold text-foreground mb-2">Start a conversation</h2>
                            <p className="text-muted-foreground max-w-sm text-sm leading-relaxed">
                                I learn from your corrections. Tell me what you prefer, and I'll remember for next time.
                            </p>
                            <div className="mt-8 flex flex-wrap justify-center gap-2">
                                {['Explain something', 'Write for me', 'Help me think'].map((suggestion) => (
                                    <button
                                        key={suggestion}
                                        onClick={() => setInput(suggestion + '...')}
                                        className="px-4 py-2 rounded-full border border-border bg-card text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-smooth"
                                    >
                                        {suggestion}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {messages.map((message) => (
                        <div
                            key={message.id}
                            className={cn(
                                'flex gap-4 animate-fade-in',
                                message.role === 'user' ? 'justify-end' : 'justify-start'
                            )}
                        >
                            {message.role === 'assistant' && (
                                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                                    <Sparkles className="w-4 h-4 text-primary" />
                                </div>
                            )}

                            <div
                                className={cn(
                                    'max-w-[75%] rounded-2xl px-4 py-3',
                                    message.role === 'user'
                                        ? 'bg-primary text-primary-foreground'
                                        : 'bg-secondary text-secondary-foreground'
                                )}
                            >
                                <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{message.content}</p>

                                {message.role === 'assistant' && (
                                    <div className="mt-3 pt-3 border-t border-border/30 flex items-center justify-between text-xs">
                                        {message.rulesApplied && message.rulesApplied > 0 ? (
                                            <span className="text-primary/80 flex items-center gap-1">
                                                <Sparkles className="w-3 h-3" />
                                                {message.rulesApplied} preference{message.rulesApplied > 1 ? 's' : ''} applied
                                            </span>
                                        ) : (
                                            <span className="text-muted-foreground">No preferences applied</span>
                                        )}
                                        <button
                                            onClick={() => setCorrectionMode(message.id)}
                                            className="text-muted-foreground hover:text-foreground transition-smooth"
                                        >
                                            Teach me
                                        </button>
                                    </div>
                                )}

                                {correctionMode === message.id && (
                                    <div className="mt-3 pt-3 border-t border-border/30 space-y-3">
                                        <textarea
                                            value={correctionText}
                                            onChange={(e) => setCorrectionText(e.target.value)}
                                            placeholder="What should I do differently?"
                                            className="w-full p-3 rounded-xl bg-background/80 border border-border text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 placeholder:text-muted-foreground"
                                            rows={2}
                                            autoFocus
                                        />
                                        <div className="flex gap-2">
                                            <Button
                                                size="sm"
                                                onClick={() => handleCorrection(message.interactionId!)}
                                                className="rounded-lg"
                                            >
                                                Save preference
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => {
                                                    setCorrectionMode(null);
                                                    setCorrectionText('');
                                                }}
                                                className="rounded-lg"
                                            >
                                                Cancel
                                            </Button>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {message.role === 'user' && (
                                <div className="w-8 h-8 rounded-lg bg-foreground/10 flex items-center justify-center flex-shrink-0 mt-1">
                                    <span className="text-xs font-medium text-foreground">U</span>
                                </div>
                            )}
                        </div>
                    ))}

                    {isLoading && (
                        <div className="flex gap-4 animate-fade-in">
                            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center mt-1">
                                <Sparkles className="w-4 h-4 text-primary" />
                            </div>
                            <div className="bg-secondary rounded-2xl px-4 py-3">
                                <div className="flex gap-1.5">
                                    <div className="typing-dot" />
                                    <div className="typing-dot" />
                                    <div className="typing-dot" />
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input */}
            <div className="border-t border-border bg-card/50 backdrop-blur-sm">
                <div className="max-w-3xl mx-auto px-4 py-4">
                    <div className="flex gap-3 items-end">
                        <div className="flex-1 relative">
                            <textarea
                                value={input}
                                onChange={(e) => {
                                    setInput(e.target.value);
                                    e.target.style.height = 'auto';
                                    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                placeholder="Message Personal AI OS..."
                                className="w-full px-4 py-3 rounded-xl bg-secondary border border-border resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-smooth min-h-[48px] max-h-[120px] text-[15px]"
                                disabled={isLoading}
                                rows={1}
                            />
                        </div>
                        <Button
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading}
                            size="lg"
                            className="rounded-xl h-12 w-12 p-0"
                        >
                            {isLoading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <Send className="w-5 h-5" />
                            )}
                        </Button>
                    </div>
                    <p className="text-center text-xs text-muted-foreground mt-3">
                        Tip: Correct me to teach preferences. They'll be applied automatically.
                    </p>
                </div>
            </div>
        </div>
    );
}
