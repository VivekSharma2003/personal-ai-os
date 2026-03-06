'use client';

import { useState, useEffect, useCallback } from 'react';
import { X, ChevronRight, ChevronLeft, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TourStep {
    target: string; // CSS selector
    title: string;
    description: string;
    position: 'top' | 'bottom' | 'left' | 'right';
}

const TOUR_STEPS: TourStep[] = [
    {
        target: 'aside',
        title: '📍 Navigation Sidebar',
        description: 'Navigate between Chat, Insights, Rules, and Timeline. You can collapse it for more space.',
        position: 'right',
    },
    {
        target: 'textarea[placeholder*="Message"]',
        title: '💬 Chat Input',
        description: 'Type your messages here. The AI will respond with your learned preferences applied automatically.',
        position: 'top',
    },
    {
        target: 'button[title="New Chat"]',
        title: '✨ New Chat',
        description: 'Start a fresh conversation. Your previous chats are saved in the sidebar.',
        position: 'right',
    },
    {
        target: 'a[href="/insights"]',
        title: '🧠 AI Insights',
        description: 'See how well your AI knows you — brain health score, rule stats, and category breakdowns.',
        position: 'right',
    },
    {
        target: 'a[href="/rules"]',
        title: '📖 Rules Page',
        description: 'View and manage all learned preferences. Toggle, edit, or delete rules here.',
        position: 'right',
    },
];

export function OnboardingTour() {
    const [active, setActive] = useState(false);
    const [step, setStep] = useState(0);
    const [spotlightRect, setSpotlightRect] = useState<DOMRect | null>(null);

    // Check if tour should show
    useEffect(() => {
        const completed = localStorage.getItem('ai-os-tour-completed');
        if (!completed) {
            // Delay to allow UI to render
            const timer = setTimeout(() => setActive(true), 1000);
            return () => clearTimeout(timer);
        }
    }, []);

    // Listen for manual tour start
    useEffect(() => {
        const handleStart = () => {
            setStep(0);
            setActive(true);
        };
        window.addEventListener('ai-os:start-tour', handleStart);
        return () => window.removeEventListener('ai-os:start-tour', handleStart);
    }, []);

    // Update spotlight position
    const updateSpotlight = useCallback(() => {
        if (!active) return;
        const currentStep = TOUR_STEPS[step];
        if (!currentStep) return;

        const el = document.querySelector(currentStep.target);
        if (el) {
            setSpotlightRect(el.getBoundingClientRect());
        } else {
            setSpotlightRect(null);
        }
    }, [active, step]);

    useEffect(() => {
        updateSpotlight();
        window.addEventListener('resize', updateSpotlight);
        return () => window.removeEventListener('resize', updateSpotlight);
    }, [updateSpotlight]);

    const handleNext = () => {
        if (step < TOUR_STEPS.length - 1) {
            setStep(step + 1);
        } else {
            handleComplete();
        }
    };

    const handlePrev = () => {
        if (step > 0) setStep(step - 1);
    };

    const handleComplete = () => {
        setActive(false);
        localStorage.setItem('ai-os-tour-completed', 'true');
    };

    if (!active) return null;

    const currentStep = TOUR_STEPS[step];
    const padding = 8;

    // Calculate tooltip position
    const getTooltipStyle = (): React.CSSProperties => {
        if (!spotlightRect) return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };

        const gap = 16;
        switch (currentStep.position) {
            case 'right':
                return {
                    top: spotlightRect.top + spotlightRect.height / 2,
                    left: spotlightRect.right + gap,
                    transform: 'translateY(-50%)',
                };
            case 'left':
                return {
                    top: spotlightRect.top + spotlightRect.height / 2,
                    right: window.innerWidth - spotlightRect.left + gap,
                    transform: 'translateY(-50%)',
                };
            case 'top':
                return {
                    bottom: window.innerHeight - spotlightRect.top + gap,
                    left: spotlightRect.left + spotlightRect.width / 2,
                    transform: 'translateX(-50%)',
                };
            case 'bottom':
                return {
                    top: spotlightRect.bottom + gap,
                    left: spotlightRect.left + spotlightRect.width / 2,
                    transform: 'translateX(-50%)',
                };
        }
    };

    return (
        <div className="fixed inset-0 z-[100]" style={{ animation: 'fadeIn 300ms ease-out' }}>
            {/* Overlay with spotlight cutout */}
            <svg className="absolute inset-0 w-full h-full" style={{ pointerEvents: 'none' }}>
                <defs>
                    <mask id="spotlight-mask">
                        <rect x="0" y="0" width="100%" height="100%" fill="white" />
                        {spotlightRect && (
                            <rect
                                x={spotlightRect.left - padding}
                                y={spotlightRect.top - padding}
                                width={spotlightRect.width + padding * 2}
                                height={spotlightRect.height + padding * 2}
                                rx="12"
                                fill="black"
                            />
                        )}
                    </mask>
                </defs>
                <rect
                    x="0" y="0" width="100%" height="100%"
                    fill="rgba(0,0,0,0.6)"
                    mask="url(#spotlight-mask)"
                    style={{ pointerEvents: 'auto' }}
                    onClick={handleComplete}
                />
            </svg>

            {/* Pulsing border around target */}
            {spotlightRect && (
                <div
                    className="absolute border-2 border-primary rounded-xl pointer-events-none"
                    style={{
                        top: spotlightRect.top - padding,
                        left: spotlightRect.left - padding,
                        width: spotlightRect.width + padding * 2,
                        height: spotlightRect.height + padding * 2,
                        animation: 'tourPulse 2s ease-in-out infinite',
                    }}
                />
            )}

            {/* Tooltip */}
            <div
                className="absolute z-10 w-72 bg-card border border-border rounded-xl shadow-2xl p-4"
                style={{
                    ...getTooltipStyle(),
                    animation: 'slideUp 200ms ease-out',
                }}
            >
                <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-primary" />
                    <h3 className="font-semibold text-foreground text-sm">{currentStep.title}</h3>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                    {currentStep.description}
                </p>

                {/* Progress dots */}
                <div className="flex items-center justify-between">
                    <div className="flex gap-1.5">
                        {TOUR_STEPS.map((_, i) => (
                            <div
                                key={i}
                                className={cn(
                                    'w-1.5 h-1.5 rounded-full transition-all duration-300',
                                    i === step ? 'bg-primary w-4' : i < step ? 'bg-primary/50' : 'bg-muted-foreground/30'
                                )}
                            />
                        ))}
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleComplete}
                            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                        >
                            Skip
                        </button>
                        {step > 0 && (
                            <button
                                onClick={handlePrev}
                                className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                            >
                                <ChevronLeft className="w-3.5 h-3.5" />
                            </button>
                        )}
                        <button
                            onClick={handleNext}
                            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
                        >
                            {step === TOUR_STEPS.length - 1 ? 'Done!' : 'Next'}
                            {step < TOUR_STEPS.length - 1 && <ChevronRight className="w-3 h-3" />}
                        </button>
                    </div>
                </div>
            </div>

            <style jsx>{`
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes tourPulse {
                    0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
                    50% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
                }
            `}</style>
        </div>
    );
}
