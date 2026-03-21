'use client';

import { cn } from '@/lib/utils';

const SUGGESTION_SETS = [
    ['Tell me more about this', 'Give a concrete example', 'Simplify the explanation'],
    ['What are the alternatives?', 'Why is this important?', 'How do I implement this?'],
    ['Can you elaborate?', 'What are the trade-offs?', 'Show me the code'],
    ['Summarize the key points', 'What should I watch out for?', 'Compare with other approaches'],
    ['Break this down step by step', 'What\'s the best practice?', 'Give me a real-world scenario'],
];

interface SmartSuggestionsProps {
    onSelect: (prompt: string) => void;
    visible: boolean;
    lastMessageContent?: string;
}

export function SmartSuggestions({ onSelect, visible }: SmartSuggestionsProps) {
    if (!visible) return null;

    // Pick a pseudo-random set based on timestamp
    const setIndex = Math.floor(Date.now() / 10000) % SUGGESTION_SETS.length;
    const suggestions = SUGGESTION_SETS[setIndex];

    return (
        <div className="flex flex-wrap gap-2 mt-3 ml-12" style={{ animation: 'suggestionsIn 400ms ease-out' }}>
            {suggestions.map((suggestion, i) => (
                <button
                    key={suggestion}
                    onClick={() => onSelect(suggestion)}
                    className={cn(
                        'px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200',
                        'bg-primary/5 border border-primary/15 text-primary/80',
                        'hover:bg-primary/10 hover:border-primary/30 hover:text-primary',
                        'hover:scale-105 active:scale-95'
                    )}
                    style={{
                        animation: `suggestionsIn 400ms ease-out ${i * 100}ms both`,
                    }}
                >
                    {suggestion}
                </button>
            ))}

            <style jsx>{`
                @keyframes suggestionsIn {
                    from { opacity: 0; transform: translateY(6px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
