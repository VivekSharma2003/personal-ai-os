'use client';

import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';

const SUGGESTION_PREFIXES: Record<string, string[]> = {
    'explain': ['explain how this works', 'explain the difference between', 'explain in simple terms'],
    'how': ['how do I implement', 'how does this work', 'how can I improve'],
    'what': ['what is the best way to', 'what are the pros and cons', 'what does this mean'],
    'tell': ['tell me more about', 'tell me the difference between', 'tell me how to'],
    'can': ['can you give me an example', 'can you explain this differently', 'can you help me with'],
    'write': ['write a function that', 'write a summary of', 'write a test for'],
    'give': ['give me an example of', 'give me 5 ideas for', 'give me a step by step guide'],
    'help': ['help me understand', 'help me debug this', 'help me write'],
    'show': ['show me an example', 'show me how to', 'show me the code for'],
    'create': ['create a plan for', 'create a list of', 'create a template for'],
};

interface AutoCompleteProps {
    input: string;
    onAccept: (suggestion: string) => void;
}

export function AutoComplete({ input, onAccept }: AutoCompleteProps) {
    const [suggestion, setSuggestion] = useState('');

    const getSuggestion = useCallback((text: string): string => {
        if (!text || text.length < 2) return '';

        const lower = text.toLowerCase().trim();
        const words = lower.split(/\s+/);
        const firstWord = words[0];

        // Check if any prefix group matches
        const prefixGroup = SUGGESTION_PREFIXES[firstWord];
        if (prefixGroup) {
            // Find a suggestion that starts with what the user typed
            const match = prefixGroup.find(
                (s) => s.startsWith(lower) && s !== lower
            );
            if (match) {
                return match.slice(text.trim().length);
            }
        }

        // Partial first word match
        for (const [key, suggestions] of Object.entries(SUGGESTION_PREFIXES)) {
            if (key.startsWith(lower) && key !== lower) {
                return key.slice(lower.length) + ' ' + suggestions[0].slice(key.length);
            }
        }

        return '';
    }, []);

    useEffect(() => {
        setSuggestion(getSuggestion(input));
    }, [input, getSuggestion]);

    // Listen for Tab key
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Tab' && suggestion && input) {
                e.preventDefault();
                onAccept(input.trim() + suggestion);
                setSuggestion('');
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [suggestion, input, onAccept]);

    if (!suggestion || !input) return null;

    return (
        <div className="absolute inset-0 pointer-events-none flex items-start">
            <div className="w-full px-4 py-3 text-[15px]">
                <span className="invisible">{input}</span>
                <span className="text-muted-foreground/30">{suggestion}</span>
            </div>
        </div>
    );
}
