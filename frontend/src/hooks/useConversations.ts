'use client';

import { useState, useEffect, useCallback } from 'react';

interface Conversation {
    id: string;
    title: string;
    preview: string;
    messageCount: number;
    createdAt: string;
    updatedAt: string;
}

interface StoredMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    rulesApplied?: number;
    interactionId?: string;
}

interface ConversationData {
    meta: Conversation;
    messages: StoredMessage[];
}

const STORAGE_KEY = 'ai-os-conversations';
const ACTIVE_KEY = 'ai-os-active-conversation';

function getStoredConversations(): Record<string, ConversationData> {
    if (typeof window === 'undefined') return {};
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : {};
    } catch {
        return {};
    }
}

function saveConversationsToStorage(conversations: Record<string, ConversationData>) {
    if (typeof window === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}

export function useConversations() {
    const [conversations, setConversations] = useState<Record<string, ConversationData>>({});
    const [activeId, setActiveId] = useState<string | null>(null);
    const [loaded, setLoaded] = useState(false);

    // Load from localStorage on mount
    useEffect(() => {
        const stored = getStoredConversations();
        setConversations(stored);
        const active = localStorage.getItem(ACTIVE_KEY);
        if (active && stored[active]) {
            setActiveId(active);
        }
        setLoaded(true);
    }, []);

    const saveConversation = useCallback(
        (id: string, messages: StoredMessage[]) => {
            if (messages.length === 0) return;

            const firstUserMsg = messages.find((m) => m.role === 'user');
            const title = firstUserMsg
                ? firstUserMsg.content.slice(0, 50) + (firstUserMsg.content.length > 50 ? '...' : '')
                : 'New Conversation';

            const lastMsg = messages[messages.length - 1];
            const preview =
                lastMsg.content.slice(0, 80) + (lastMsg.content.length > 80 ? '...' : '');

            const now = new Date().toISOString();

            setConversations((prev) => {
                const updated = {
                    ...prev,
                    [id]: {
                        meta: {
                            id,
                            title,
                            preview,
                            messageCount: messages.length,
                            createdAt: prev[id]?.meta?.createdAt || now,
                            updatedAt: now,
                        },
                        messages,
                    },
                };
                saveConversationsToStorage(updated);
                return updated;
            });
        },
        []
    );

    const loadConversation = useCallback(
        (id: string): StoredMessage[] | null => {
            const conv = conversations[id];
            if (!conv) return null;
            setActiveId(id);
            localStorage.setItem(ACTIVE_KEY, id);
            return conv.messages;
        },
        [conversations]
    );

    const deleteConversation = useCallback((id: string) => {
        setConversations((prev) => {
            const updated = { ...prev };
            delete updated[id];
            saveConversationsToStorage(updated);
            return updated;
        });
        if (activeId === id) {
            setActiveId(null);
            localStorage.removeItem(ACTIVE_KEY);
        }
    }, [activeId]);

    const listConversations = useCallback((): Conversation[] => {
        return Object.values(conversations)
            .map((c) => c.meta)
            .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
    }, [conversations]);

    const setActive = useCallback((id: string | null) => {
        setActiveId(id);
        if (id) {
            localStorage.setItem(ACTIVE_KEY, id);
        } else {
            localStorage.removeItem(ACTIVE_KEY);
        }
    }, []);

    return {
        conversations: listConversations(),
        activeId,
        loaded,
        saveConversation,
        loadConversation,
        deleteConversation,
        setActive,
    };
}
