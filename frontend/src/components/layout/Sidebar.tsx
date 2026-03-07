'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    MessageSquare,
    BookOpen,
    Clock,
    Sparkles,
    ChevronRight,
    ChevronLeft,
    Plus,
    Trash2,
    PanelLeftClose,
    PanelLeft,
    Command,
    Brain,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ThemeToggle } from './ThemeToggle';
import { useConversations } from '@/hooks/useConversations';

const navItems = [
    { href: '/', label: 'Chat', icon: MessageSquare, description: 'Talk with AI' },
    { href: '/insights', label: 'Insights', icon: Brain, description: 'AI brain health' },
    { href: '/rules', label: 'Rules', icon: BookOpen, description: 'Your preferences' },
    { href: '/timeline', label: 'Timeline', icon: Clock, description: 'Activity log' },
];

export function Sidebar() {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);
    const { conversations, activeId, deleteConversation, setActive } = useConversations();

    // Load collapsed state from localStorage
    useEffect(() => {
        const stored = localStorage.getItem('ai-os-sidebar-collapsed');
        if (stored === 'true') setCollapsed(true);
    }, []);

    const toggleCollapsed = () => {
        const next = !collapsed;
        setCollapsed(next);
        localStorage.setItem('ai-os-sidebar-collapsed', String(next));
    };

    const handleNewChat = () => {
        window.dispatchEvent(new CustomEvent('ai-os:new-chat'));
        setActive(null);
    };

    const handleLoadConversation = (id: string) => {
        window.dispatchEvent(new CustomEvent('ai-os:load-chat', { detail: { id } }));
    };

    return (
        <aside
            className={cn(
                'h-full bg-card border-r border-border flex flex-col transition-all duration-300 ease-out',
                collapsed ? 'w-[68px]' : 'w-72'
            )}
        >
            {/* Logo */}
            <div className="p-3 border-b border-border">
                <div className={cn('flex items-center', collapsed ? 'justify-center' : 'gap-3 px-2')}>
                    <Link href="/" className="flex items-center gap-3 group flex-shrink-0">
                        <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-smooth">
                            <Sparkles className="w-5 h-5 text-primary" />
                        </div>
                    </Link>
                    {!collapsed && (
                        <div className="flex-1 min-w-0 animate-fade-in">
                            <h1 className="font-semibold text-foreground text-sm">Personal AI OS</h1>
                            <p className="text-xs text-muted-foreground">Learn & Adapt</p>
                        </div>
                    )}
                </div>
            </div>

            {/* New Chat Button */}
            {pathname === '/' && (
                <div className={cn('px-3 pt-3', collapsed && 'flex justify-center')}>
                    <button
                        onClick={handleNewChat}
                        className={cn(
                            'flex items-center gap-2 rounded-lg transition-smooth text-sm font-medium',
                            'bg-primary/10 text-primary hover:bg-primary/20',
                            collapsed
                                ? 'w-10 h-10 justify-center'
                                : 'w-full px-3 py-2.5'
                        )}
                        title="New Chat"
                    >
                        <Plus className="w-4 h-4 flex-shrink-0" />
                        {!collapsed && <span>New Chat</span>}
                    </button>
                </div>
            )}

            {/* Navigation */}
            <nav className="p-3 space-y-1">
                {!collapsed && (
                    <p className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Menu
                    </p>
                )}
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                'flex items-center gap-3 rounded-lg transition-smooth group',
                                collapsed
                                    ? 'w-10 h-10 justify-center mx-auto'
                                    : 'px-3 py-2.5',
                                isActive
                                    ? 'bg-primary/10 text-primary'
                                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                            )}
                            title={collapsed ? item.label : undefined}
                        >
                            <item.icon
                                className={cn(
                                    'w-5 h-5 transition-smooth flex-shrink-0',
                                    isActive ? 'text-primary' : 'group-hover:text-foreground'
                                )}
                            />
                            {!collapsed && (
                                <div className="flex-1 min-w-0 animate-fade-in">
                                    <span className="font-medium text-sm">{item.label}</span>
                                    <p
                                        className={cn(
                                            'text-xs truncate transition-smooth',
                                            isActive ? 'text-primary/70' : 'text-muted-foreground'
                                        )}
                                    >
                                        {item.description}
                                    </p>
                                </div>
                            )}
                            {!collapsed && isActive && (
                                <ChevronRight className="w-4 h-4 text-primary/50" />
                            )}
                        </Link>
                    );
                })}
            </nav>

            {/* Conversation History */}
            {!collapsed && pathname === '/' && conversations.length > 0 && (
                <div className="flex-1 overflow-y-auto px-3 animate-fade-in">
                    <p className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Recent Chats
                    </p>
                    <div className="space-y-0.5">
                        {conversations.slice(0, 10).map((conv) => (
                            <div
                                key={conv.id}
                                className={cn(
                                    'group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-smooth',
                                    activeId === conv.id
                                        ? 'bg-accent text-foreground'
                                        : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                                )}
                                onClick={() => handleLoadConversation(conv.id)}
                            >
                                <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 opacity-50" />
                                <span className="flex-1 text-xs truncate">{conv.title}</span>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        deleteConversation(conv.id);
                                    }}
                                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 rounded transition-smooth"
                                    title="Delete"
                                >
                                    <Trash2 className="w-3 h-3 text-destructive" />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Spacer when no conversations or collapsed */}
            {(collapsed || pathname !== '/' || conversations.length === 0) && <div className="flex-1" />}

            {/* Footer */}
            <div className="p-3 border-t border-border space-y-2">
                {/* Cmd+K hint */}
                {!collapsed && (
                    <button
                        onClick={() => {
                            window.dispatchEvent(
                                new KeyboardEvent('keydown', { key: 'k', metaKey: true })
                            );
                        }}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-smooth"
                    >
                        <Command className="w-3.5 h-3.5" />
                        <span className="flex-1 text-left">Command Palette</span>
                        <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">⌘K</kbd>
                    </button>
                )}

                {/* Theme toggle + Collapse toggle */}
                <div className={cn('flex items-center', collapsed ? 'flex-col gap-2' : 'gap-2 px-1')}>
                    <ThemeToggle />
                    <button
                        onClick={toggleCollapsed}
                        className={cn(
                            'p-2 rounded-lg transition-smooth',
                            'hover:bg-accent text-muted-foreground hover:text-foreground'
                        )}
                        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                    >
                        {collapsed ? (
                            <PanelLeft className="w-5 h-5" />
                        ) : (
                            <PanelLeftClose className="w-5 h-5" />
                        )}
                    </button>
                    {!collapsed && (
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate text-foreground">User</p>
                            <p className="text-xs text-muted-foreground">Free Plan</p>
                        </div>
                    )}
                </div>
            </div>
        </aside>
    );
}
