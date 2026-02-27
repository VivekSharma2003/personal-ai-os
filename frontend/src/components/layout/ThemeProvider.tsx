'use client';

import { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'dark' | 'light' | 'system';

interface ThemeContextType {
    theme: Theme;
    setTheme: (theme: Theme) => void;
    resolvedTheme: 'dark' | 'light';
}

const ThemeContext = createContext<ThemeContextType>({
    theme: 'dark',
    setTheme: () => { },
    resolvedTheme: 'dark',
});

export function useTheme() {
    return useContext(ThemeContext);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setTheme] = useState<Theme>('dark');
    const [resolvedTheme, setResolvedTheme] = useState<'dark' | 'light'>('dark');
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        const stored = localStorage.getItem('ai-os-theme') as Theme | null;
        if (stored) {
            setTheme(stored);
        }
    }, []);

    useEffect(() => {
        if (!mounted) return;

        const root = document.documentElement;
        let resolved: 'dark' | 'light';

        if (theme === 'system') {
            resolved = window.matchMedia('(prefers-color-scheme: dark)').matches
                ? 'dark'
                : 'light';
        } else {
            resolved = theme;
        }

        root.classList.remove('dark', 'light');
        root.classList.add(resolved);
        setResolvedTheme(resolved);
        localStorage.setItem('ai-os-theme', theme);
    }, [theme, mounted]);

    // Listen for system theme changes when in 'system' mode
    useEffect(() => {
        if (theme !== 'system') return;

        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handler = (e: MediaQueryListEvent) => {
            const root = document.documentElement;
            root.classList.remove('dark', 'light');
            root.classList.add(e.matches ? 'dark' : 'light');
            setResolvedTheme(e.matches ? 'dark' : 'light');
        };

        mediaQuery.addEventListener('change', handler);
        return () => mediaQuery.removeEventListener('change', handler);
    }, [theme]);

    // Prevent flash of wrong theme
    if (!mounted) {
        return <>{children}</>;
    }

    return (
        <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}
