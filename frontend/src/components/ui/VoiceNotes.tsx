'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Mic, Square, Download, Trash2, Play, Pause } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'ai-os-voice-notes';

interface VoiceNote {
    id: string;
    title: string;
    duration: number; // seconds
    audioUrl: string; // blob URL (not persisted, re-created from base64)
    audioBase64: string;
    createdAt: string;
}

function loadNotes(): VoiceNote[] {
    try {
        const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        return raw.map((n: any) => ({
            ...n,
            audioUrl: n.audioBase64 ? URL.createObjectURL(base64ToBlob(n.audioBase64, 'audio/webm')) : '',
        }));
    } catch { return []; }
}

function saveNotes(notes: VoiceNote[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(
        notes.map(n => ({ ...n, audioUrl: undefined }))
    ));
}

function base64ToBlob(base64: string, mime: string): Blob {
    const byteChars = atob(base64);
    const byteArrays: Uint8Array[] = [];
    for (let offset = 0; offset < byteChars.length; offset += 512) {
        const slice = byteChars.slice(offset, offset + 512);
        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) byteNumbers[i] = slice.charCodeAt(i);
        byteArrays.push(new Uint8Array(byteNumbers));
    }
    return new Blob(byteArrays, { type: mime });
}

function blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const dataUrl = reader.result as string;
            resolve(dataUrl.split(',')[1]);
        };
        reader.readAsDataURL(blob);
    });
}

function formatDuration(s: number): string {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
}

export function VoiceNotes() {
    const [open, setOpen] = useState(false);
    const [notes, setNotes] = useState<VoiceNote[]>([]);
    const [recording, setRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const [playingId, setPlayingId] = useState<string | null>(null);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        const handler = () => { setOpen(true); setNotes(loadNotes()); };
        window.addEventListener('ai-os:open-voice-notes', handler);
        return () => window.removeEventListener('ai-os:open-voice-notes', handler);
    }, []);

    const startRecording = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mr = new MediaRecorder(stream);
            chunksRef.current = [];
            mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            mr.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
                const base64 = await blobToBase64(blob);
                const url = URL.createObjectURL(blob);
                const note: VoiceNote = {
                    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
                    title: `Note ${notes.length + 1}`,
                    duration: recordingTime,
                    audioUrl: url,
                    audioBase64: base64,
                    createdAt: new Date().toISOString(),
                };
                const updated = [note, ...notes];
                setNotes(updated);
                saveNotes(updated);
            };
            mr.start();
            mediaRecorderRef.current = mr;
            setRecording(true);
            setRecordingTime(0);
            timerRef.current = setInterval(() => setRecordingTime(t => t + 1), 1000);
        } catch {
            // Microphone denied
        }
    }, [notes, recordingTime]);

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && recording) {
            mediaRecorderRef.current.stop();
            setRecording(false);
            if (timerRef.current) clearInterval(timerRef.current);
        }
    }, [recording]);

    const togglePlay = (note: VoiceNote) => {
        if (playingId === note.id) {
            audioRef.current?.pause();
            setPlayingId(null);
        } else {
            if (audioRef.current) audioRef.current.pause();
            const audio = new Audio(note.audioUrl);
            audio.onended = () => setPlayingId(null);
            audio.play();
            audioRef.current = audio;
            setPlayingId(note.id);
        }
    };

    const deleteNote = (id: string) => {
        if (playingId === id) { audioRef.current?.pause(); setPlayingId(null); }
        const updated = notes.filter(n => n.id !== id);
        setNotes(updated);
        saveNotes(updated);
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50" style={{ animation: 'fadeIn 150ms ease-out' }}>
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" onClick={() => { if (!recording) setOpen(false); }} />
            <div className="relative max-w-sm mx-auto mt-[12vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                style={{ animation: 'slideUp 200ms ease-out' }}>

                <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-rose-500/20 to-pink-500/10 flex items-center justify-center">
                            <Mic className="w-4 h-4 text-rose-400" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-foreground">Voice Notes</h2>
                            <p className="text-[10px] text-muted-foreground">{notes.length} note{notes.length !== 1 ? 's' : ''} saved</p>
                        </div>
                    </div>
                    <button onClick={() => { if (!recording) setOpen(false); }} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="p-5 max-h-[60vh] overflow-y-auto">
                    {/* Record button */}
                    <div className="flex flex-col items-center mb-5">
                        {recording ? (
                            <>
                                <div className="relative">
                                    <div className="absolute inset-0 rounded-full bg-red-500/20 animate-ping" />
                                    <button onClick={stopRecording}
                                        className="relative w-16 h-16 rounded-full bg-red-500 text-white flex items-center justify-center shadow-lg hover:bg-red-600 transition-colors">
                                        <Square className="w-5 h-5" />
                                    </button>
                                </div>
                                <p className="text-sm font-bold text-red-400 tabular-nums mt-3">{formatDuration(recordingTime)}</p>
                                <p className="text-[10px] text-muted-foreground">Recording... tap to stop</p>
                            </>
                        ) : (
                            <button onClick={startRecording}
                                className="w-14 h-14 rounded-full bg-gradient-to-br from-rose-500 to-pink-600 text-white flex items-center justify-center shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 transition-all">
                                <Mic className="w-5 h-5" />
                            </button>
                        )}
                    </div>

                    {/* Notes list */}
                    {notes.length === 0 ? (
                        <p className="text-center text-xs text-muted-foreground/60 py-4">Tap the mic to record your first note</p>
                    ) : (
                        <div className="space-y-2">
                            {notes.map(note => (
                                <div key={note.id} className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50 border border-border group hover:bg-accent/50 transition-colors">
                                    <button onClick={() => togglePlay(note)}
                                        className={cn('w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-colors',
                                            playingId === note.id ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground')}>
                                        {playingId === note.id ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
                                    </button>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-foreground">{note.title}</p>
                                        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                                            <span>{formatDuration(note.duration)}</span>
                                            <span>·</span>
                                            <span>{new Date(note.createdAt).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                    <button onClick={() => deleteNote(note.id)}
                                        className="p-1 text-muted-foreground/30 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all">
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
            <style jsx>{`
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                @keyframes slideUp { from { opacity: 0; transform: translateY(10px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
            `}</style>
        </div>
    );
}
