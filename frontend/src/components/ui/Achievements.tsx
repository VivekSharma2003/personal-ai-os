'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Trophy, X, Lock, Star, Flame, MessageSquare, Pin, Scissors, Heart, Moon, Sun, Zap, Target, BookOpen, Award } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-achievements';
const UNLOCK_QUEUE_KEY = 'ai-os-achievement-queue';

interface Achievement {
    id: string;
    title: string;
    description: string;
    icon: React.ElementType;
    rarity: 'bronze' | 'silver' | 'gold' | 'platinum';
    check: () => boolean;
}

interface UnlockedAchievement {
    id: string;
    unlockedAt: string;
}

const RARITY_COLORS = {
    bronze: {
        bg: 'from-amber-700/20 to-orange-800/10',
        border: 'border-amber-600/40',
        text: 'text-amber-500',
        badge: 'bg-amber-500/20 text-amber-400',
        glow: 'shadow-amber-500/20',
        ring: 'ring-amber-500/30',
    },
    silver: {
        bg: 'from-slate-400/20 to-gray-500/10',
        border: 'border-slate-400/40',
        text: 'text-slate-300',
        badge: 'bg-slate-400/20 text-slate-300',
        glow: 'shadow-slate-400/20',
        ring: 'ring-slate-400/30',
    },
    gold: {
        bg: 'from-yellow-500/20 to-amber-500/10',
        border: 'border-yellow-500/40',
        text: 'text-yellow-400',
        badge: 'bg-yellow-500/20 text-yellow-400',
        glow: 'shadow-yellow-400/20',
        ring: 'ring-yellow-500/30',
    },
    platinum: {
        bg: 'from-violet-500/20 to-purple-600/10',
        border: 'border-violet-500/40',
        text: 'text-violet-400',
        badge: 'bg-violet-500/20 text-violet-400',
        glow: 'shadow-violet-400/20',
        ring: 'ring-violet-500/30',
    },
};

function getConversationCount(): number {
    try {
        const data = localStorage.getItem('ai-os-conversations');
        return data ? JSON.parse(data).length : 0;
    } catch { return 0; }
}

function getMessageCount(): number {
    try {
        const data = localStorage.getItem('ai-os-conversations');
        if (!data) return 0;
        const convos = JSON.parse(data);
        return convos.reduce((sum: number, c: any) => sum + (c.messages?.length || 0), 0);
    } catch { return 0; }
}

function getStreakCount(): number {
    try {
        const data = localStorage.getItem('ai-os-streak-data');
        return data ? JSON.parse(data).currentStreak || 0 : 0;
    } catch { return 0; }
}

function getPinCount(): number {
    try {
        const data = localStorage.getItem('ai-os-pinboard');
        return data ? JSON.parse(data).length : 0;
    } catch { return 0; }
}

function getSnippetCount(): number {
    try {
        const data = localStorage.getItem('ai-os-snippets');
        return data ? JSON.parse(data).length : 0;
    } catch { return 0; }
}

function getMoodCount(): number {
    try {
        const data = localStorage.getItem('ai-os-mood-journal');
        return data ? JSON.parse(data).length : 0;
    } catch { return 0; }
}

function getBookmarkCount(): number {
    try {
        const data = localStorage.getItem('ai-os-bookmarks');
        return data ? JSON.parse(data).length : 0;
    } catch { return 0; }
}

const ACHIEVEMENTS: Achievement[] = [
    {
        id: 'first-chat',
        title: 'Hello World',
        description: 'Start your first conversation',
        icon: MessageSquare,
        rarity: 'bronze',
        check: () => getConversationCount() >= 1,
    },
    {
        id: 'chatty',
        title: 'Chatty',
        description: 'Have 10 conversations',
        icon: MessageSquare,
        rarity: 'silver',
        check: () => getConversationCount() >= 10,
    },
    {
        id: 'conversationalist',
        title: 'Conversationalist',
        description: 'Have 50 conversations',
        icon: MessageSquare,
        rarity: 'gold',
        check: () => getConversationCount() >= 50,
    },
    {
        id: 'msg-100',
        title: 'Century',
        description: 'Send 100 messages',
        icon: Zap,
        rarity: 'silver',
        check: () => getMessageCount() >= 100,
    },
    {
        id: 'msg-500',
        title: 'Prolific',
        description: 'Send 500 messages',
        icon: Zap,
        rarity: 'gold',
        check: () => getMessageCount() >= 500,
    },
    {
        id: 'streak-3',
        title: 'Getting Started',
        description: 'Maintain a 3-day streak',
        icon: Flame,
        rarity: 'bronze',
        check: () => getStreakCount() >= 3,
    },
    {
        id: 'streak-7',
        title: 'Week Warrior',
        description: 'Maintain a 7-day streak',
        icon: Flame,
        rarity: 'silver',
        check: () => getStreakCount() >= 7,
    },
    {
        id: 'streak-30',
        title: 'Monthly Master',
        description: 'Maintain a 30-day streak',
        icon: Flame,
        rarity: 'platinum',
        check: () => getStreakCount() >= 30,
    },
    {
        id: 'first-pin',
        title: 'Pin It',
        description: 'Pin your first note',
        icon: Pin,
        rarity: 'bronze',
        check: () => getPinCount() >= 1,
    },
    {
        id: 'first-snippet',
        title: 'Code Collector',
        description: 'Save your first snippet',
        icon: Scissors,
        rarity: 'bronze',
        check: () => getSnippetCount() >= 1,
    },
    {
        id: 'mood-tracker',
        title: 'Self Aware',
        description: 'Log 5 mood entries',
        icon: Heart,
        rarity: 'silver',
        check: () => getMoodCount() >= 5,
    },
    {
        id: 'bookmark-5',
        title: 'Bookworm',
        description: 'Bookmark 5 messages',
        icon: BookOpen,
        rarity: 'silver',
        check: () => getBookmarkCount() >= 5,
    },
    {
        id: 'night-owl',
        title: 'Night Owl',
        description: 'Chat after midnight',
        icon: Moon,
        rarity: 'silver',
        check: () => {
            const hour = new Date().getHours();
            return hour >= 0 && hour < 5 && getConversationCount() > 0;
        },
    },
    {
        id: 'early-bird',
        title: 'Early Bird',
        description: 'Chat before 6 AM',
        icon: Sun,
        rarity: 'silver',
        check: () => {
            const hour = new Date().getHours();
            return hour >= 5 && hour < 7 && getConversationCount() > 0;
        },
    },
    {
        id: 'power-user',
        title: 'Power User',
        description: 'Unlock 10 achievements',
        icon: Star,
        rarity: 'platinum',
        check: () => {
            try {
                const data = localStorage.getItem(STORAGE_KEY);
                return data ? JSON.parse(data).length >= 10 : false;
            } catch { return false; }
        },
    },
];

function getUnlocked(): UnlockedAchievement[] {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch { return []; }
}

function saveUnlocked(unlocked: UnlockedAchievement[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(unlocked));
}

// Hook for checking achievements
export function useAchievements() {
    const checkAndUnlock = useCallback(() => {
        const unlocked = getUnlocked();
        const unlockedIds = new Set(unlocked.map(u => u.id));
        const newlyUnlocked: string[] = [];

        for (const achievement of ACHIEVEMENTS) {
            if (!unlockedIds.has(achievement.id) && achievement.check()) {
                unlocked.push({ id: achievement.id, unlockedAt: new Date().toISOString() });
                newlyUnlocked.push(achievement.id);
            }
        }

        if (newlyUnlocked.length > 0) {
            saveUnlocked(unlocked);
            // Queue new unlocks for toast notifications
            const queue = JSON.parse(localStorage.getItem(UNLOCK_QUEUE_KEY) || '[]');
            queue.push(...newlyUnlocked);
            localStorage.setItem(UNLOCK_QUEUE_KEY, JSON.stringify(queue));
            window.dispatchEvent(new CustomEvent('ai-os:achievement-unlocked'));
        }
    }, []);

    return { checkAndUnlock };
}

// Unlock notification toast
function UnlockToast({ achievementId, onDone }: { achievementId: string; onDone: () => void }) {
    const achievement = ACHIEVEMENTS.find(a => a.id === achievementId);
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        requestAnimationFrame(() => setVisible(true));
        const timer = setTimeout(() => {
            setVisible(false);
            setTimeout(onDone, 400);
        }, 4000);
        return () => clearTimeout(timer);
    }, [onDone]);

    if (!achievement) return null;

    const rarity = RARITY_COLORS[achievement.rarity];
    const Icon = achievement.icon;

    return (
        <div
            className={cn(
                'fixed top-6 right-6 z-[60] max-w-xs transition-all duration-500',
                visible ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 -translate-y-4 scale-95'
            )}
        >
            <div className={cn(
                'relative overflow-hidden rounded-xl border shadow-2xl bg-card p-4',
                rarity.border, rarity.glow
            )}>
                {/* Confetti particles */}
                <div className="absolute inset-0 pointer-events-none overflow-hidden">
                    {[...Array(12)].map((_, i) => (
                        <div
                            key={i}
                            className="absolute w-1.5 h-1.5 rounded-full"
                            style={{
                                left: `${10 + Math.random() * 80}%`,
                                top: `${10 + Math.random() * 80}%`,
                                background: ['#fbbf24', '#a78bfa', '#34d399', '#f472b6', '#60a5fa'][i % 5],
                                animation: `achieveParticle ${1 + Math.random() * 2}s ease-out ${Math.random() * 0.5}s infinite`,
                            }}
                        />
                    ))}
                </div>

                <div className="flex items-center gap-3 relative z-10">
                    <div className={cn(
                        'w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br',
                        rarity.bg
                    )}
                        style={{ animation: 'achieveBounce 600ms cubic-bezier(0.34,1.56,0.64,1)' }}
                    >
                        <Icon className={cn('w-6 h-6', rarity.text)} />
                    </div>
                    <div>
                        <p className="text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Achievement Unlocked!</p>
                        <p className="font-semibold text-foreground text-sm">{achievement.title}</p>
                        <p className="text-xs text-muted-foreground">{achievement.description}</p>
                    </div>
                    <span className={cn('absolute top-0 right-0 text-[9px] px-2 py-0.5 rounded-bl-lg rounded-tr-lg font-bold uppercase', rarity.badge)}>
                        {achievement.rarity}
                    </span>
                </div>
            </div>
        </div>
    );
}

// Main Achievements modal
export function Achievements() {
    const [open, setOpen] = useState(false);
    const [unlocked, setUnlocked] = useState<UnlockedAchievement[]>([]);
    const [toastQueue, setToastQueue] = useState<string[]>([]);

    // Load unlocked
    useEffect(() => {
        setUnlocked(getUnlocked());
    }, [open]);

    // Listen for unlock event
    useEffect(() => {
        const handler = () => {
            const queue: string[] = JSON.parse(localStorage.getItem(UNLOCK_QUEUE_KEY) || '[]');
            if (queue.length > 0) {
                setToastQueue(prev => [...prev, ...queue]);
                localStorage.setItem(UNLOCK_QUEUE_KEY, '[]');
            }
            setUnlocked(getUnlocked());
        };
        window.addEventListener('ai-os:achievement-unlocked', handler);
        return () => window.removeEventListener('ai-os:achievement-unlocked', handler);
    }, []);

    // Listen for open event
    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('ai-os:open-achievements', handler);
        return () => window.removeEventListener('ai-os:open-achievements', handler);
    }, []);

    const handleToastDone = useCallback(() => {
        setToastQueue(prev => prev.slice(1));
    }, []);

    const unlockedIds = useMemo(() => new Set(unlocked.map(u => u.id)), [unlocked]);
    const progress = unlocked.length;
    const total = ACHIEVEMENTS.length;

    return (
        <>
            {/* Toast notifications */}
            {toastQueue.length > 0 && (
                <UnlockToast achievementId={toastQueue[0]} onDone={handleToastDone} />
            )}

            {/* Trophy Case Modal */}
            {open && (
                <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
                    <div
                        className="absolute inset-0 bg-background/60 backdrop-blur-sm"
                        onClick={() => setOpen(false)}
                    />

                    <div
                        className="relative max-w-xl mx-auto mt-[8vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden max-h-[80vh] flex flex-col"
                        style={{ animation: 'slideUp 200ms ease-out' }}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-500/20 to-amber-500/10 flex items-center justify-center">
                                    <Trophy className="w-5 h-5 text-yellow-400" />
                                </div>
                                <div>
                                    <h2 className="font-semibold text-foreground">Trophy Case</h2>
                                    <p className="text-xs text-muted-foreground">{progress} / {total} unlocked</p>
                                </div>
                            </div>
                            <button
                                onClick={() => setOpen(false)}
                                className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Progress bar */}
                        <div className="px-5 py-3 border-b border-border/50">
                            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
                                <span>Progress</span>
                                <span>{Math.round((progress / total) * 100)}%</span>
                            </div>
                            <div className="h-2 rounded-full bg-secondary overflow-hidden">
                                <div
                                    className="h-full rounded-full bg-gradient-to-r from-yellow-500 via-amber-400 to-yellow-500 transition-all duration-700"
                                    style={{ width: `${(progress / total) * 100}%`, backgroundSize: '200% 100%', animation: 'gradient-shift 3s ease infinite' }}
                                />
                            </div>
                        </div>

                        {/* Achievements Grid */}
                        <div className="flex-1 overflow-y-auto p-4">
                            <div className="grid grid-cols-2 gap-3">
                                {ACHIEVEMENTS.map(achievement => {
                                    const isUnlocked = unlockedIds.has(achievement.id);
                                    const rarity = RARITY_COLORS[achievement.rarity];
                                    const Icon = achievement.icon;
                                    const unlockData = unlocked.find(u => u.id === achievement.id);

                                    return (
                                        <div
                                            key={achievement.id}
                                            className={cn(
                                                'relative rounded-xl border p-3.5 transition-all duration-300',
                                                isUnlocked
                                                    ? `bg-gradient-to-br ${rarity.bg} ${rarity.border} hover:shadow-lg ${rarity.glow}`
                                                    : 'bg-secondary/30 border-border/30 opacity-50 grayscale'
                                            )}
                                        >
                                            <div className="flex items-start gap-3">
                                                <div className={cn(
                                                    'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                                                    isUnlocked ? `bg-gradient-to-br ${rarity.bg}` : 'bg-muted'
                                                )}>
                                                    {isUnlocked ? (
                                                        <Icon className={cn('w-5 h-5', rarity.text)} />
                                                    ) : (
                                                        <Lock className="w-4 h-4 text-muted-foreground/50" />
                                                    )}
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <p className={cn(
                                                        'text-sm font-semibold truncate',
                                                        isUnlocked ? 'text-foreground' : 'text-muted-foreground'
                                                    )}>
                                                        {achievement.title}
                                                    </p>
                                                    <p className="text-[11px] text-muted-foreground leading-snug mt-0.5">
                                                        {achievement.description}
                                                    </p>
                                                    {unlockData && (
                                                        <p className="text-[9px] text-muted-foreground/60 mt-1">
                                                            {new Date(unlockData.unlockedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                            <span className={cn(
                                                'absolute top-2 right-2 text-[8px] px-1.5 py-0.5 rounded-md font-bold uppercase',
                                                isUnlocked ? rarity.badge : 'bg-muted text-muted-foreground/40'
                                            )}>
                                                {achievement.rarity}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>

                    <style jsx>{`
                        @keyframes fadeIn {
                            from { opacity: 0; }
                            to { opacity: 1; }
                        }
                        @keyframes slideUp {
                            from { opacity: 0; transform: translateY(10px) scale(0.98); }
                            to { opacity: 1; transform: translateY(0) scale(1); }
                        }
                    `}</style>
                </div>
            )}
        </>
    );
}
