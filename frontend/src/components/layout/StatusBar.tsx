'use client';

import { useState, useEffect } from 'react';
import { Wifi, WifiOff, Sparkles, Clock } from 'lucide-react';
import { api } from '@/lib/api';
import { cn, formatRelativeTime } from '@/lib/utils';

export function StatusBar() {
    const [online, setOnline] = useState<boolean | null>(null);
    const [activeRules, setActiveRules] = useState(0);
    const [lastSync, setLastSync] = useState<string | null>(null);

    useEffect(() => {
        async function checkHealth() {
            try {
                const res = await fetch('/health');
                setOnline(res.ok);
                setLastSync(new Date().toISOString());
            } catch {
                setOnline(false);
            }
        }

        async function loadRules() {
            try {
                const res = await api.getRules('active');
                setActiveRules(res.active);
            } catch {
                // API not running
            }
        }

        checkHealth();
        loadRules();

        const healthInterval = setInterval(checkHealth, 15000);
        const rulesInterval = setInterval(loadRules, 30000);

        return () => {
            clearInterval(healthInterval);
            clearInterval(rulesInterval);
        };
    }, []);

    return (
        <div className="h-7 bg-card/80 backdrop-blur-sm border-t border-border flex items-center px-4 gap-4 text-[11px] text-muted-foreground select-none flex-shrink-0">
            {/* Connection status */}
            <div className="flex items-center gap-1.5">
                {online === null ? (
                    <>
                        <div className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-pulse" />
                        <span>Checking...</span>
                    </>
                ) : online ? (
                    <>
                        <div className="relative">
                            <div className="w-2 h-2 rounded-full bg-emerald-500" />
                            <div className="absolute inset-0 w-2 h-2 rounded-full bg-emerald-500 animate-ping opacity-40" />
                        </div>
                        <span className="text-emerald-500/80">Connected</span>
                    </>
                ) : (
                    <>
                        <div className="w-2 h-2 rounded-full bg-red-500" />
                        <span className="text-red-400/80">Offline</span>
                    </>
                )}
            </div>

            <div className="w-px h-3 bg-border" />

            {/* Active rules */}
            <div className="flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 text-primary/50" />
                <span>{activeRules} active rule{activeRules !== 1 ? 's' : ''}</span>
            </div>

            <div className="flex-1" />

            {/* Last sync */}
            {lastSync && (
                <div className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3 text-muted-foreground/50" />
                    <span>Synced {formatRelativeTime(lastSync)}</span>
                </div>
            )}
        </div>
    );
}
