'use client';

import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from './ThemeProvider';
import { cn } from '@/lib/utils';

export function ThemeToggle() {
    const { theme, setTheme } = useTheme();

    const cycleTheme = () => {
        const next = theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark';
        setTheme(next);
    };

    return (
        <button
            onClick={cycleTheme}
            className={cn(
                'relative p-2 rounded-lg transition-all duration-300',
                'hover:bg-accent text-muted-foreground hover:text-foreground',
                'focus:outline-none focus:ring-2 focus:ring-primary/30'
            )}
            title={`Theme: ${theme} (click to cycle)`}
        >
            <div className="relative w-5 h-5">
                <Sun
                    className={cn(
                        'absolute inset-0 w-5 h-5 transition-all duration-300',
                        theme === 'light'
                            ? 'rotate-0 scale-100 opacity-100'
                            : '-rotate-90 scale-0 opacity-0'
                    )}
                />
                <Moon
                    className={cn(
                        'absolute inset-0 w-5 h-5 transition-all duration-300',
                        theme === 'dark'
                            ? 'rotate-0 scale-100 opacity-100'
                            : 'rotate-90 scale-0 opacity-0'
                    )}
                />
                <Monitor
                    className={cn(
                        'absolute inset-0 w-5 h-5 transition-all duration-300',
                        theme === 'system'
                            ? 'rotate-0 scale-100 opacity-100'
                            : 'rotate-90 scale-0 opacity-0'
                    )}
                />
            </div>
        </button>
    );
}
