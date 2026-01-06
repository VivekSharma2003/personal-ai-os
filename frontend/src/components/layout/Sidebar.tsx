'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    MessageSquare,
    BookOpen,
    Clock,
    Settings,
    Sparkles,
    ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
    { href: '/', label: 'Chat', icon: MessageSquare, description: 'Talk with AI' },
    { href: '/rules', label: 'Rules', icon: BookOpen, description: 'Your preferences' },
    { href: '/timeline', label: 'Timeline', icon: Clock, description: 'Activity log' },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="w-72 h-full bg-card border-r border-border flex flex-col">
            {/* Logo */}
            <div className="p-5 border-b border-border">
                <Link href="/" className="flex items-center gap-3 group">
                    <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-smooth">
                        <Sparkles className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                        <h1 className="font-semibold text-foreground">Personal AI OS</h1>
                        <p className="text-xs text-muted-foreground">Learn & Adapt</p>
                    </div>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-3 space-y-1">
                <p className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Menu
                </p>
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-smooth group',
                                isActive
                                    ? 'bg-primary/10 text-primary'
                                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                            )}
                        >
                            <item.icon className={cn(
                                'w-5 h-5 transition-smooth',
                                isActive ? 'text-primary' : 'group-hover:text-foreground'
                            )} />
                            <div className="flex-1 min-w-0">
                                <span className="font-medium text-sm">{item.label}</span>
                                <p className={cn(
                                    'text-xs truncate transition-smooth',
                                    isActive ? 'text-primary/70' : 'text-muted-foreground'
                                )}>
                                    {item.description}
                                </p>
                            </div>
                            {isActive && (
                                <ChevronRight className="w-4 h-4 text-primary/50" />
                            )}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="p-3 border-t border-border">
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-accent/50 hover:bg-accent transition-smooth cursor-pointer">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center text-xs font-semibold text-white">
                        U
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">User</p>
                        <p className="text-xs text-muted-foreground">Free Plan</p>
                    </div>
                    <Settings className="w-4 h-4 text-muted-foreground hover:text-foreground transition-smooth" />
                </div>
            </div>
        </aside>
    );
}
