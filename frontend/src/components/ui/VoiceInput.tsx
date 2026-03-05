'use client';

import { useState, useEffect, useRef } from 'react';
import { Mic, MicOff } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VoiceInputProps {
    onTranscript: (text: string) => void;
    disabled?: boolean;
}

export function VoiceInput({ onTranscript, disabled }: VoiceInputProps) {
    const [isListening, setIsListening] = useState(false);
    const [supported, setSupported] = useState(true);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognitionRef = useRef<any>(null);

    useEffect(() => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const w = window as any;
        const SpeechRecognitionAPI = w.SpeechRecognition || w.webkitSpeechRecognition;

        if (!SpeechRecognitionAPI) {
            setSupported(false);
            return;
        }

        const recognition = new SpeechRecognitionAPI();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        recognition.onresult = (event: any) => {
            const transcript = event.results[0][0].transcript;
            onTranscript(transcript);
            setIsListening(false);
        };

        recognition.onerror = () => {
            setIsListening(false);
        };

        recognition.onend = () => {
            setIsListening(false);
        };

        recognitionRef.current = recognition;

        return () => {
            recognition.abort();
        };
    }, [onTranscript]);

    const toggleListening = () => {
        if (!recognitionRef.current) return;

        if (isListening) {
            recognitionRef.current.stop();
            setIsListening(false);
        } else {
            recognitionRef.current.start();
            setIsListening(true);
        }
    };

    if (!supported) return null;

    return (
        <button
            onClick={toggleListening}
            disabled={disabled}
            className={cn(
                'relative p-3 rounded-xl transition-all duration-200',
                isListening
                    ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20'
                    : 'bg-secondary text-muted-foreground hover:bg-accent hover:text-foreground',
                disabled && 'opacity-50 cursor-not-allowed'
            )}
            title={isListening ? 'Stop recording' : 'Voice input'}
        >
            {/* Pulsing rings when recording */}
            {isListening && (
                <>
                    <span className="absolute inset-0 rounded-xl border-2 border-red-500/30 animate-ping" />
                    <span
                        className="absolute inset-[-4px] rounded-xl border border-red-500/20"
                        style={{ animation: 'voicePulse 1.5s ease-in-out infinite' }}
                    />
                </>
            )}

            {isListening ? (
                <MicOff className="w-5 h-5 relative z-10" />
            ) : (
                <Mic className="w-5 h-5" />
            )}

            <style jsx>{`
                @keyframes voicePulse {
                    0%, 100% { transform: scale(1); opacity: 0.5; }
                    50% { transform: scale(1.08); opacity: 0; }
                }
            `}</style>
        </button>
    );
}
