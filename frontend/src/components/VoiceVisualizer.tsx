'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState, useRef } from 'react';

interface VoiceVisualizerProps {
  isRecording: boolean;
  isSpeaking: boolean;
}

export function VoiceVisualizer({ isRecording, isSpeaking }: VoiceVisualizerProps) {
  const [audioLevels, setAudioLevels] = useState<number[]>(Array(32).fill(0.1));
  const animationRef = useRef<number>();

  useEffect(() => {
    const animate = () => {
      if (isRecording || isSpeaking) {
        setAudioLevels(prev => prev.map(() => 
          Math.random() * 0.8 + 0.2
        ));
      } else {
        setAudioLevels(prev => prev.map((v) => 
          Math.max(0.1, v * 0.95)
        ));
      }
      animationRef.current = requestAnimationFrame(animate);
    };
    
    animationRef.current = requestAnimationFrame(animate);
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [isRecording, isSpeaking]);

  const isActive = isRecording || isSpeaking;

  return (
    <div className="relative w-60 h-60 flex items-center justify-center">
      {/* Outer Glow Rings */}
      <motion.div
        animate={{
          scale: isActive ? [1, 1.15, 1] : 1,
          opacity: isActive ? [0.1, 0.25, 0.1] : 0.05,
        }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="absolute w-56 h-56 rounded-full border border-violet-500/20"
      />
      <motion.div
        animate={{
          scale: isActive ? [1, 1.25, 1] : 1,
          opacity: isActive ? [0.05, 0.15, 0.05] : 0.03,
        }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
        className="absolute w-60 h-60 rounded-full border border-violet-500/10"
      />

      {/* Ambient Glow */}
      <motion.div
        animate={{
          scale: isRecording ? [1, 1.3, 1] : isSpeaking ? [1, 1.2, 1] : 1,
          opacity: isRecording ? 0.4 : isSpeaking ? 0.25 : 0.1,
        }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        className="absolute w-40 h-40 rounded-full bg-gradient-to-br from-violet-500/30 via-purple-500/20 to-fuchsia-500/10 blur-3xl"
      />

      {/* Circular Audio Bars */}
      <div className="absolute w-44 h-44 rounded-full">
        {audioLevels.map((level, i) => {
          const angle = (i / audioLevels.length) * 360;
          const barHeight = isActive ? 20 + level * 40 : 8;
          return (
            <motion.div
              key={i}
              className="absolute left-1/2 bottom-1/2 origin-bottom"
              style={{
                transform: `rotate(${angle}deg) translateX(-50%)`,
                width: '3px',
              }}
              animate={{ height: barHeight }}
              transition={{ duration: 0.1, ease: "easeOut" }}
            >
              <div
                className={`w-full h-full rounded-full transition-colors duration-300 ${
                  isRecording
                    ? 'bg-gradient-to-t from-violet-500 to-purple-400'
                    : isSpeaking
                      ? 'bg-gradient-to-t from-purple-500 to-fuchsia-400'
                      : 'bg-zinc-700'
                }`}
                style={{
                  boxShadow: isActive ? `0 0 ${10 + level * 15}px ${isRecording ? 'rgba(139, 92, 246, 0.5)' : 'rgba(168, 85, 247, 0.5)'}` : 'none'
                }}
              />
            </motion.div>
          );
        })}
      </div>

      {/* Inner Orb */}
      <motion.div
        animate={{
          scale: isRecording ? [1, 1.08, 1] : isSpeaking ? [1, 1.05, 1] : 1,
        }}
        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        className="relative z-10 w-24 h-24 rounded-full overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, rgba(24, 24, 27, 0.9), rgba(9, 9, 11, 0.95))',
          boxShadow: isActive
            ? `inset 0 0 30px rgba(139, 92, 246, 0.15), 0 0 60px ${isRecording ? 'rgba(139, 92, 246, 0.3)' : 'rgba(168, 85, 247, 0.3)'}`
            : 'inset 0 0 20px rgba(0,0,0,0.5), 0 10px 40px rgba(0,0,0,0.5)'
        }}
      >
        {/* Glass Reflection */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-transparent" />
        
        {/* Inner Glow Ring */}
        <motion.div
          animate={{ opacity: isActive ? [0.3, 0.6, 0.3] : 0.1 }}
          transition={{ duration: 2, repeat: Infinity }}
          className="absolute inset-2 rounded-full border border-violet-500/30"
        />

        {/* Center Icon Area */}
        <div className="absolute inset-0 flex items-center justify-center">
          <AnimatePresence mode="wait">
            {isRecording ? (
              <motion.div
                key="recording"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                className="flex flex-col items-center gap-2"
              >
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                  className="w-4 h-4 rounded-full bg-violet-500 shadow-[0_0_20px_rgba(139,92,246,0.8)]"
                />
                <span className="text-[9px] font-bold text-violet-400 uppercase tracking-[0.3em]">Live</span>
              </motion.div>
            ) : isSpeaking ? (
              <motion.div
                key="speaking"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                className="flex gap-1"
              >
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    animate={{ height: [8, 20, 8] }}
                    transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.15 }}
                    className="w-1 bg-purple-400 rounded-full"
                  />
                ))}
              </motion.div>
            ) : (
              <motion.div
                key="idle"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                className="w-3 h-3 rounded-full bg-zinc-600"
              />
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Floating Particles */}
      <AnimatePresence>
        {isActive && (
          <>
            {[...Array(6)].map((_, i) => (
              <motion.div
                key={`particle-${i}`}
                initial={{ opacity: 0, scale: 0 }}
                animate={{
                  opacity: [0, 0.8, 0],
                  scale: [0, 1, 0.5],
                  x: [0, (Math.random() - 0.5) * 200],
                  y: [0, (Math.random() - 0.5) * 200],
                }}
                exit={{ opacity: 0, scale: 0 }}
                transition={{
                  duration: 2 + Math.random() * 2,
                  repeat: Infinity,
                  delay: i * 0.3,
                }}
                className={`absolute w-1.5 h-1.5 rounded-full ${
                  isRecording ? 'bg-violet-400' : 'bg-purple-400'
                }`}
                style={{
                  boxShadow: `0 0 10px ${isRecording ? 'rgba(139, 92, 246, 0.8)' : 'rgba(168, 85, 247, 0.8)'}`
                }}
              />
            ))}
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
