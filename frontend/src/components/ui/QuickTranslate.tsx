'use client';

import { useState, useEffect, useRef } from 'react';
import { Globe, ChevronDown, X, Languages } from 'lucide-react';
import { cn } from '@/lib/utils';

const LANG_STORAGE_KEY = 'ai-os-translate-lang';

interface Language {
    code: string;
    name: string;
    flag: string;
    greeting: string;
}

const LANGUAGES: Language[] = [
    { code: 'es', name: 'Spanish', flag: '🇪🇸', greeting: 'Hola' },
    { code: 'fr', name: 'French', flag: '🇫🇷', greeting: 'Bonjour' },
    { code: 'de', name: 'German', flag: '🇩🇪', greeting: 'Hallo' },
    { code: 'hi', name: 'Hindi', flag: '🇮🇳', greeting: 'नमस्ते' },
    { code: 'ja', name: 'Japanese', flag: '🇯🇵', greeting: 'こんにちは' },
    { code: 'ko', name: 'Korean', flag: '🇰🇷', greeting: '안녕하세요' },
    { code: 'pt', name: 'Portuguese', flag: '🇧🇷', greeting: 'Olá' },
    { code: 'zh', name: 'Chinese', flag: '🇨🇳', greeting: '你好' },
];

// Simple local word-swapping translation for demo purposes
const TRANSLATION_MAPS: Record<string, Record<string, string>> = {
    es: {
        'hello': 'hola', 'hi': 'hola', 'the': 'el', 'is': 'es', 'are': 'son',
        'yes': 'sí', 'no': 'no', 'and': 'y', 'or': 'o', 'thank': 'gracias',
        'you': 'tú', 'good': 'bueno', 'bad': 'malo', 'what': 'qué', 'how': 'cómo',
        'please': 'por favor', 'here': 'aquí', 'there': 'allí', 'this': 'esto', 'that': 'eso',
        'code': 'código', 'function': 'función', 'data': 'datos', 'help': 'ayuda',
        'world': 'mundo', 'time': 'tiempo', 'day': 'día', 'night': 'noche',
        'with': 'con', 'for': 'para', 'from': 'de', 'to': 'a',
        'can': 'puedo', 'will': 'será', 'have': 'tener', 'do': 'hacer',
    },
    fr: {
        'hello': 'bonjour', 'hi': 'salut', 'the': 'le', 'is': 'est', 'are': 'sont',
        'yes': 'oui', 'no': 'non', 'and': 'et', 'or': 'ou', 'thank': 'merci',
        'you': 'vous', 'good': 'bon', 'bad': 'mauvais', 'what': 'quoi', 'how': 'comment',
        'please': 's\'il vous plaît', 'here': 'ici', 'there': 'là', 'this': 'ceci', 'that': 'cela',
        'code': 'code', 'function': 'fonction', 'data': 'données', 'help': 'aide',
        'world': 'monde', 'time': 'temps', 'day': 'jour', 'night': 'nuit',
        'with': 'avec', 'for': 'pour', 'from': 'de', 'to': 'à',
        'can': 'peux', 'will': 'sera', 'have': 'avoir', 'do': 'faire',
    },
    de: {
        'hello': 'hallo', 'hi': 'hallo', 'the': 'der', 'is': 'ist', 'are': 'sind',
        'yes': 'ja', 'no': 'nein', 'and': 'und', 'or': 'oder', 'thank': 'danke',
        'you': 'du', 'good': 'gut', 'bad': 'schlecht', 'what': 'was', 'how': 'wie',
        'please': 'bitte', 'here': 'hier', 'there': 'dort', 'this': 'dies', 'that': 'das',
        'code': 'Code', 'function': 'Funktion', 'data': 'Daten', 'help': 'Hilfe',
        'world': 'Welt', 'time': 'Zeit', 'day': 'Tag', 'night': 'Nacht',
        'with': 'mit', 'for': 'für', 'from': 'von', 'to': 'zu',
        'can': 'kann', 'will': 'wird', 'have': 'haben', 'do': 'tun',
    },
    hi: {
        'hello': 'नमस्ते', 'hi': 'नमस्ते', 'the': 'यह', 'is': 'है', 'are': 'हैं',
        'yes': 'हाँ', 'no': 'नहीं', 'and': 'और', 'or': 'या', 'thank': 'धन्यवाद',
        'you': 'आप', 'good': 'अच्छा', 'bad': 'बुरा', 'what': 'क्या', 'how': 'कैसे',
        'please': 'कृपया', 'here': 'यहाँ', 'there': 'वहाँ', 'this': 'यह', 'that': 'वह',
        'code': 'कोड', 'function': 'फ़ंक्शन', 'data': 'डेटा', 'help': 'मदद',
        'world': 'दुनिया', 'time': 'समय', 'day': 'दिन', 'night': 'रात',
        'with': 'के साथ', 'for': 'के लिए', 'from': 'से', 'to': 'को',
    },
    ja: {
        'hello': 'こんにちは', 'hi': 'こんにちは', 'the': 'その', 'is': 'です', 'are': 'です',
        'yes': 'はい', 'no': 'いいえ', 'and': 'と', 'or': 'または', 'thank': 'ありがとう',
        'you': 'あなた', 'good': '良い', 'bad': '悪い', 'what': '何', 'how': 'どう',
        'please': 'お願いします', 'code': 'コード', 'function': '関数', 'data': 'データ', 'help': '助け',
        'world': '世界', 'time': '時間', 'day': '日', 'night': '夜',
    },
    ko: {
        'hello': '안녕하세요', 'hi': '안녕', 'the': '그', 'is': '입니다', 'are': '있습니다',
        'yes': '예', 'no': '아니요', 'and': '그리고', 'or': '또는', 'thank': '감사합니다',
        'you': '당신', 'good': '좋은', 'bad': '나쁜', 'what': '무엇', 'how': '어떻게',
        'please': '제발', 'code': '코드', 'function': '함수', 'data': '데이터', 'help': '도움',
        'world': '세계', 'time': '시간', 'day': '날', 'night': '밤',
    },
    pt: {
        'hello': 'olá', 'hi': 'oi', 'the': 'o', 'is': 'é', 'are': 'são',
        'yes': 'sim', 'no': 'não', 'and': 'e', 'or': 'ou', 'thank': 'obrigado',
        'you': 'você', 'good': 'bom', 'bad': 'mau', 'what': 'o quê', 'how': 'como',
        'please': 'por favor', 'code': 'código', 'function': 'função', 'data': 'dados', 'help': 'ajuda',
        'world': 'mundo', 'time': 'tempo', 'day': 'dia', 'night': 'noite',
        'with': 'com', 'for': 'para', 'from': 'de', 'to': 'para',
    },
    zh: {
        'hello': '你好', 'hi': '嗨', 'the': '这', 'is': '是', 'are': '是',
        'yes': '是的', 'no': '不', 'and': '和', 'or': '或', 'thank': '谢谢',
        'you': '你', 'good': '好', 'bad': '坏', 'what': '什么', 'how': '怎么',
        'please': '请', 'code': '代码', 'function': '函数', 'data': '数据', 'help': '帮助',
        'world': '世界', 'time': '时间', 'day': '天', 'night': '夜',
    },
};

function translateText(text: string, langCode: string): string {
    const map = TRANSLATION_MAPS[langCode];
    if (!map) return text;

    // Replace words while preserving structure, markdown, and code blocks
    const lines = text.split('\n');
    return lines.map(line => {
        // Skip code block lines
        if (line.trim().startsWith('```') || line.trim().startsWith('`')) return line;

        return line.replace(/\b([a-zA-Z]+)\b/g, (match) => {
            const lower = match.toLowerCase();
            const translated = map[lower];
            if (!translated) return match;
            // Preserve original capitalization
            if (match[0] === match[0].toUpperCase()) {
                return translated.charAt(0).toUpperCase() + translated.slice(1);
            }
            return translated;
        });
    }).join('\n');
}

export function TranslateButton({ content }: { content: string }) {
    const [showDropdown, setShowDropdown] = useState(false);
    const [translated, setTranslated] = useState<string | null>(null);
    const [selectedLang, setSelectedLang] = useState<Language | null>(null);
    const [isTranslating, setIsTranslating] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Load preferred language
    useEffect(() => {
        const saved = localStorage.getItem(LANG_STORAGE_KEY);
        if (saved) {
            const lang = LANGUAGES.find(l => l.code === saved);
            if (lang) setSelectedLang(lang);
        }
    }, []);

    // Close dropdown on outside click
    useEffect(() => {
        if (!showDropdown) return;
        const handler = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [showDropdown]);

    const handleTranslate = (lang: Language) => {
        setSelectedLang(lang);
        setShowDropdown(false);
        setIsTranslating(true);
        localStorage.setItem(LANG_STORAGE_KEY, lang.code);

        // Simulate translation delay for UX
        setTimeout(() => {
            const result = translateText(content, lang.code);
            setTranslated(result);
            setIsTranslating(false);
        }, 300);
    };

    const handleClear = () => {
        setTranslated(null);
        setSelectedLang(null);
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => {
                    if (translated) {
                        handleClear();
                    } else {
                        setShowDropdown(!showDropdown);
                    }
                }}
                className={cn(
                    'p-1.5 rounded-md text-muted-foreground transition-smooth',
                    translated
                        ? 'bg-primary/10 text-primary hover:bg-primary/20'
                        : 'hover:bg-muted hover:text-foreground'
                )}
                title={translated ? 'Clear translation' : 'Translate'}
            >
                {translated ? (
                    <Languages className="w-3.5 h-3.5" />
                ) : (
                    <Globe className="w-3.5 h-3.5" />
                )}
            </button>

            {/* Language picker dropdown */}
            {showDropdown && (
                <div
                    className="absolute bottom-full right-0 mb-2 w-48 bg-card border border-border rounded-xl shadow-2xl overflow-hidden z-50"
                    style={{ animation: 'slideUp 150ms ease-out' }}
                >
                    <div className="px-3 py-2 border-b border-border">
                        <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Translate to</p>
                    </div>
                    <div className="max-h-52 overflow-y-auto p-1">
                        {LANGUAGES.map(lang => (
                            <button
                                key={lang.code}
                                onClick={() => handleTranslate(lang)}
                                className={cn(
                                    'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-sm transition-colors',
                                    selectedLang?.code === lang.code
                                        ? 'bg-primary/10 text-foreground'
                                        : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                                )}
                            >
                                <span className="text-base">{lang.flag}</span>
                                <span className="flex-1 font-medium">{lang.name}</span>
                                <span className="text-[10px] text-muted-foreground/60">{lang.greeting}</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Translated result - shows below the message */}
            {(translated || isTranslating) && (
                <div
                    className="absolute top-full left-0 right-0 mt-2 -ml-24 w-72 z-40"
                    style={{ animation: 'slideUp 200ms ease-out' }}
                >
                    <div className="bg-card/95 backdrop-blur-md border border-primary/20 rounded-xl p-3 shadow-xl">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-1.5">
                                <span className="text-sm">{selectedLang?.flag}</span>
                                <span className="text-[10px] font-medium text-primary uppercase tracking-wider">
                                    {selectedLang?.name}
                                </span>
                            </div>
                            <button
                                onClick={handleClear}
                                className="p-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                            >
                                <X className="w-3 h-3" />
                            </button>
                        </div>
                        {isTranslating ? (
                            <div className="flex items-center gap-2 py-2">
                                <div className="flex gap-1">
                                    <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                                <span className="text-xs text-muted-foreground">Translating...</span>
                            </div>
                        ) : (
                            <p className="text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap max-h-32 overflow-y-auto">
                                {translated && translated.length > 200 ? translated.slice(0, 200) + '...' : translated}
                            </p>
                        )}
                    </div>
                </div>
            )}

            <style jsx>{`
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(4px) scale(0.98); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
            `}</style>
        </div>
    );
}
