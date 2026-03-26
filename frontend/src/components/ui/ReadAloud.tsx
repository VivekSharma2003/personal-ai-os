'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Volume2, VolumeX, Square } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ReadAloudProps {
    content: string;
}

export function ReadAloud({ content }: ReadAloudProps) {
    const [playing, setPlaying] = useState(false);
    const [supported, setSupported] = useState(true);
    const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

    useEffect(() => {
        setSupported(typeof window !== 'undefined' && 'speechSynthesis' in window);
        return () => {
            window.speechSynthesis?.cancel();
        };
    }, []);

    const handleToggle = useCallback(() => {
        if (!supported) return;

        if (playing) {
            window.speechSynthesis.cancel();
            setPlaying(false);
            return;
        }

        // Strip markdown formatting for cleaner speech
        const cleanText = content
            .replace(/```[\s\S]*?```/g, 'code block omitted')
            .replace(/`([^`]+)`/g, '$1')
            .replace(/\*\*([^*]+)\*\*/g, '$1')
            .replace(/\*([^*]+)\*/g, '$1')
            .replace(/#{1,6}\s/g, '')
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
            .replace(/[>\-*]/g, '');

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onend = () => setPlaying(false);
        utterance.onerror = () => setPlaying(false);

        utteranceRef.current = utterance;
        window.speechSynthesis.speak(utterance);
        setPlaying(true);
    }, [content, playing, supported]);

    if (!supported) return null;

    return (
        <button
            onClick={handleToggle}
            className={cn(
                'p-1.5 rounded-md transition-smooth',
                playing
                    ? 'text-primary hover:bg-primary/10'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            )}
            title={playing ? 'Stop reading' : 'Read aloud'}
        >
            {playing ? (
                <div className="relative">
                    <Volume2 className="w-3.5 h-3.5" />
                    <span
                        className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-primary rounded-full"
                        style={{ animation: 'pulse 1.5s ease-in-out infinite' }}
                    />
                </div>
            ) : (
                <Volume2 className="w-3.5 h-3.5" />
            )}

            <style jsx>{`
                @keyframes pulse {
                    0%, 100% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.5; transform: scale(1.3); }
                }
            `}</style>
        </button>
    );
}
