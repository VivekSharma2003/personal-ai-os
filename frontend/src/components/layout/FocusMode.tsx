'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface FocusModeContextType {
    focusMode: boolean;
    toggleFocusMode: () => void;
}

const FocusModeContext = createContext<FocusModeContextType>({
    focusMode: false,
    toggleFocusMode: () => { },
});

export function useFocusMode() {
    return useContext(FocusModeContext);
}

export function FocusModeProvider({ children }: { children: ReactNode }) {
    const [focusMode, setFocusMode] = useState(false);

    const toggleFocusMode = () => setFocusMode((prev) => !prev);

    // Keyboard shortcut: Cmd+.
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === '.') {
                e.preventDefault();
                toggleFocusMode();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    // Listen for custom event from command palette
    useEffect(() => {
        const handler = () => toggleFocusMode();
        window.addEventListener('ai-os:toggle-focus', handler);
        return () => window.removeEventListener('ai-os:toggle-focus', handler);
    }, []);

    return (
        <FocusModeContext.Provider value={{ focusMode, toggleFocusMode }}>
            {children}
        </FocusModeContext.Provider>
    );
}
