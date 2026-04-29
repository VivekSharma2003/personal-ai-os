'use client';

import { useState, useEffect, useRef } from 'react';
import { X, Pencil, Eraser, Download, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';

const COLORS = ['#ffffff','#ef4444','#f59e0b','#10b981','#3b82f6','#8b5cf6','#ec4899','#06b6d4'];
const SIZES = [2, 4, 8, 14];
type Tool = 'pen' | 'eraser';

export function Whiteboard() {
    const [open, setOpen] = useState(false);
    const [tool, setTool] = useState<Tool>('pen');
    const [color, setColor] = useState('#ffffff');
    const [size, setSize] = useState(4);
    const [drawing, setDrawing] = useState(false);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const ctxRef = useRef<CanvasRenderingContext2D | null>(null);
    const lastPos = useRef<{x:number;y:number}|null>(null);

    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('ai-os:open-whiteboard', handler);
        return () => window.removeEventListener('ai-os:open-whiteboard', handler);
    }, []);

    useEffect(() => {
        if (!open || !canvasRef.current) return;
        const canvas = canvasRef.current;
        const container = canvas.parentElement;
        if (!container) return;
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctxRef.current = ctx;
    }, [open]);

    const getPos = (e: React.MouseEvent | React.TouchEvent) => {
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return {x:0,y:0};
        if ('touches' in e) return {x: e.touches[0].clientX - rect.left, y: e.touches[0].clientY - rect.top};
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    };

    const startDraw = (e: React.MouseEvent | React.TouchEvent) => { setDrawing(true); lastPos.current = getPos(e); };
    const draw = (e: React.MouseEvent | React.TouchEvent) => {
        if (!drawing || !ctxRef.current || !lastPos.current) return;
        const ctx = ctxRef.current; const pos = getPos(e);
        ctx.beginPath(); ctx.moveTo(lastPos.current.x, lastPos.current.y); ctx.lineTo(pos.x, pos.y);
        ctx.strokeStyle = tool === 'eraser' ? '#1a1a2e' : color;
        ctx.lineWidth = tool === 'eraser' ? size * 4 : size;
        ctx.stroke(); lastPos.current = pos;
    };
    const stopDraw = () => { setDrawing(false); lastPos.current = null; };

    const clearCanvas = () => { const c = canvasRef.current; const ctx = ctxRef.current; if(c&&ctx){ctx.fillStyle='#1a1a2e';ctx.fillRect(0,0,c.width,c.height);} };
    const downloadCanvas = () => { const c = canvasRef.current; if(!c) return; const a=document.createElement('a'); a.download=`whiteboard-${Date.now()}.png`; a.href=c.toDataURL(); a.click(); };

    if (!open) return null;
    return (
        <div className="fixed inset-0 z-50" style={{animation:'fadeIn 150ms ease-out'}}>
            <div className="absolute inset-0 bg-background/80 backdrop-blur-md" />
            <div className="relative w-[90vw] max-w-3xl mx-auto mt-[5vh] bg-card border border-border rounded-xl shadow-2xl overflow-hidden" style={{animation:'slideUp 200ms ease-out'}}>
                <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                    <div className="flex items-center gap-2">
                        <button onClick={()=>setTool('pen')} className={cn('p-2 rounded-lg transition-colors',tool==='pen'?'bg-primary text-primary-foreground':'text-muted-foreground hover:bg-muted')}><Pencil className="w-4 h-4"/></button>
                        <button onClick={()=>setTool('eraser')} className={cn('p-2 rounded-lg transition-colors',tool==='eraser'?'bg-primary text-primary-foreground':'text-muted-foreground hover:bg-muted')}><Eraser className="w-4 h-4"/></button>
                        <div className="w-px h-6 bg-border mx-1"/>
                        {COLORS.map(c=>(<button key={c} onClick={()=>{setColor(c);setTool('pen');}} className={cn('w-5 h-5 rounded-full border-2 transition-transform',color===c&&tool==='pen'?'scale-125 border-primary':'border-transparent hover:scale-110')} style={{backgroundColor:c}}/>))}
                        <div className="w-px h-6 bg-border mx-1"/>
                        {SIZES.map(s=>(<button key={s} onClick={()=>setSize(s)} className={cn('p-1.5 rounded-lg transition-colors',size===s?'bg-muted':'hover:bg-muted')}><div className="rounded-full bg-foreground" style={{width:s+2,height:s+2}}/></button>))}
                    </div>
                    <div className="flex items-center gap-1">
                        <button onClick={clearCanvas} className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors" title="Clear"><RotateCcw className="w-4 h-4"/></button>
                        <button onClick={downloadCanvas} className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors" title="Download"><Download className="w-4 h-4"/></button>
                        <button onClick={()=>setOpen(false)} className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"><X className="w-4 h-4"/></button>
                    </div>
                </div>
                <div className="relative" style={{height:'65vh'}}>
                    <canvas ref={canvasRef} className={cn('w-full h-full',tool==='eraser'?'cursor-cell':'cursor-crosshair')}
                        onMouseDown={startDraw} onMouseMove={draw} onMouseUp={stopDraw} onMouseLeave={stopDraw}
                        onTouchStart={startDraw} onTouchMove={draw} onTouchEnd={stopDraw}/>
                </div>
            </div>
            <style jsx>{`@keyframes fadeIn{from{opacity:0}to{opacity:1}}@keyframes slideUp{from{opacity:0;transform:translateY(10px) scale(0.98)}to{opacity:1;transform:translateY(0) scale(1)}}`}</style>
        </div>
    );
}
