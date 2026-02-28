'use client';

import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
    const renderMarkdown = (text: string) => {
        const lines = text.split('\n');
        const elements: JSX.Element[] = [];
        let i = 0;
        let key = 0;

        while (i < lines.length) {
            const line = lines[i];

            // Fenced code blocks
            if (line.trimStart().startsWith('```')) {
                const lang = line.trimStart().slice(3).trim();
                const codeLines: string[] = [];
                i++;
                while (i < lines.length && !lines[i].trimStart().startsWith('```')) {
                    codeLines.push(lines[i]);
                    i++;
                }
                i++; // skip closing ```
                elements.push(
                    <div key={key++} className="my-3 rounded-lg overflow-hidden border border-border/50">
                        {lang && (
                            <div className="px-3 py-1.5 bg-muted/80 text-xs text-muted-foreground font-mono border-b border-border/50">
                                {lang}
                            </div>
                        )}
                        <pre className="p-3 bg-muted/40 overflow-x-auto">
                            <code className="text-sm font-mono text-foreground/90 leading-relaxed">
                                {codeLines.join('\n')}
                            </code>
                        </pre>
                    </div>
                );
                continue;
            }

            // Empty lines
            if (line.trim() === '') {
                elements.push(<div key={key++} className="h-2" />);
                i++;
                continue;
            }

            // Headings
            const headingMatch = line.match(/^(#{1,6})\s+(.+)/);
            if (headingMatch) {
                const level = headingMatch[1].length;
                const text = headingMatch[2];
                const sizes: Record<number, string> = {
                    1: 'text-xl font-bold',
                    2: 'text-lg font-semibold',
                    3: 'text-base font-semibold',
                    4: 'text-sm font-semibold',
                    5: 'text-sm font-medium',
                    6: 'text-xs font-medium',
                };
                elements.push(
                    <div key={key++} className={cn(sizes[level] || sizes[3], 'mt-3 mb-1')}>
                        {renderInline(text)}
                    </div>
                );
                i++;
                continue;
            }

            // Blockquote
            if (line.trimStart().startsWith('> ')) {
                const quoteLines: string[] = [];
                while (i < lines.length && lines[i].trimStart().startsWith('> ')) {
                    quoteLines.push(lines[i].replace(/^>\s?/, ''));
                    i++;
                }
                elements.push(
                    <blockquote key={key++} className="my-2 pl-3 border-l-2 border-primary/40 text-muted-foreground italic">
                        {quoteLines.map((ql, qi) => (
                            <p key={qi}>{renderInline(ql)}</p>
                        ))}
                    </blockquote>
                );
                continue;
            }

            // Unordered list
            if (line.match(/^\s*[-*+]\s/)) {
                const listItems: string[] = [];
                while (i < lines.length && lines[i].match(/^\s*[-*+]\s/)) {
                    listItems.push(lines[i].replace(/^\s*[-*+]\s/, ''));
                    i++;
                }
                elements.push(
                    <ul key={key++} className="my-2 ml-4 space-y-1">
                        {listItems.map((item, li) => (
                            <li key={li} className="flex items-start gap-2">
                                <span className="text-primary mt-1.5 text-xs">●</span>
                                <span>{renderInline(item)}</span>
                            </li>
                        ))}
                    </ul>
                );
                continue;
            }

            // Ordered list
            if (line.match(/^\s*\d+\.\s/)) {
                const listItems: string[] = [];
                while (i < lines.length && lines[i].match(/^\s*\d+\.\s/)) {
                    listItems.push(lines[i].replace(/^\s*\d+\.\s/, ''));
                    i++;
                }
                elements.push(
                    <ol key={key++} className="my-2 ml-4 space-y-1">
                        {listItems.map((item, li) => (
                            <li key={li} className="flex items-start gap-2">
                                <span className="text-primary/70 font-medium text-sm min-w-[1.2rem]">{li + 1}.</span>
                                <span>{renderInline(item)}</span>
                            </li>
                        ))}
                    </ol>
                );
                continue;
            }

            // Horizontal rule
            if (line.match(/^-{3,}$/) || line.match(/^\*{3,}$/) || line.match(/^_{3,}$/)) {
                elements.push(<hr key={key++} className="my-3 border-border/50" />);
                i++;
                continue;
            }

            // Normal paragraph
            elements.push(
                <p key={key++} className="my-1 leading-relaxed">
                    {renderInline(line)}
                </p>
            );
            i++;
        }

        return elements;
    };

    const renderInline = (text: string): (string | JSX.Element)[] => {
        const parts: (string | JSX.Element)[] = [];
        let remaining = text;
        let inlineKey = 0;

        while (remaining.length > 0) {
            // Inline code
            const codeMatch = remaining.match(/^(.*?)`([^`]+)`/);
            if (codeMatch) {
                if (codeMatch[1]) parts.push(codeMatch[1]);
                parts.push(
                    <code
                        key={`ic-${inlineKey++}`}
                        className="px-1.5 py-0.5 rounded bg-muted text-primary/90 text-[0.85em] font-mono"
                    >
                        {codeMatch[2]}
                    </code>
                );
                remaining = remaining.slice(codeMatch[0].length);
                continue;
            }

            // Bold
            const boldMatch = remaining.match(/^(.*?)\*\*(.+?)\*\*/);
            if (boldMatch) {
                if (boldMatch[1]) parts.push(boldMatch[1]);
                parts.push(
                    <strong key={`b-${inlineKey++}`} className="font-semibold">
                        {boldMatch[2]}
                    </strong>
                );
                remaining = remaining.slice(boldMatch[0].length);
                continue;
            }

            // Italic
            const italicMatch = remaining.match(/^(.*?)\*(.+?)\*/);
            if (italicMatch) {
                if (italicMatch[1]) parts.push(italicMatch[1]);
                parts.push(
                    <em key={`i-${inlineKey++}`} className="italic text-foreground/80">
                        {italicMatch[2]}
                    </em>
                );
                remaining = remaining.slice(italicMatch[0].length);
                continue;
            }

            // Links
            const linkMatch = remaining.match(/^(.*?)\[([^\]]+)\]\(([^)]+)\)/);
            if (linkMatch) {
                if (linkMatch[1]) parts.push(linkMatch[1]);
                parts.push(
                    <a
                        key={`a-${inlineKey++}`}
                        href={linkMatch[3]}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline underline-offset-2"
                    >
                        {linkMatch[2]}
                    </a>
                );
                remaining = remaining.slice(linkMatch[0].length);
                continue;
            }

            // No more special tokens, push the rest
            parts.push(remaining);
            break;
        }

        return parts;
    };

    return (
        <div className={cn('text-[15px]', className)}>
            {renderMarkdown(content)}
        </div>
    );
}
