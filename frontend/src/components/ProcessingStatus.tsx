'use client';

import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic,
  Languages,
  Brain,
  Database,
  Sparkles,
  Check,
  Loader2
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

export type ProcessingStep =
  | 'transcribing'
  | 'translating_input'
  | 'understanding'
  | 'planning'
  | 'executing'
  | 'translating_output'
  | 'complete';

interface ProcessingStatusProps {
  isProcessing: boolean;
  isVoiceInput?: boolean;
  hasTamilInput?: boolean;
  variant?: 'voice' | 'chat';
  className?: string;
}

const STEPS_CONFIG: Record<ProcessingStep, {
  icon: React.ElementType;
  label: string;
  sublabel: string;
  duration: number; // ms before moving to next step
}> = {
  transcribing: {
    icon: Mic,
    label: 'Transcribing',
    sublabel: 'Converting speech to text...',
    duration: 800
  },
  translating_input: {
    icon: Languages,
    label: 'Translating',
    sublabel: 'Tamil to English...',
    duration: 1200
  },
  understanding: {
    icon: Brain,
    label: 'Understanding',
    sublabel: 'Analyzing your question...',
    duration: 600
  },
  planning: {
    icon: Sparkles,
    label: 'Planning',
    sublabel: 'Creating query strategy...',
    duration: 800
  },
  executing: {
    icon: Database,
    label: 'Executing',
    sublabel: 'Running database query...',
    duration: 1000
  },
  translating_output: {
    icon: Languages,
    label: 'Translating',
    sublabel: 'English to Tamil...',
    duration: 1000
  },
  complete: {
    icon: Check,
    label: 'Complete',
    sublabel: 'Done!',
    duration: 0
  }
};

export function ProcessingStatus({
  isProcessing,
  isVoiceInput = false,
  hasTamilInput = false,
  variant = 'chat',
  className
}: ProcessingStatusProps) {
  const [currentStep, setCurrentStep] = useState<ProcessingStep>('understanding');
  const [completedSteps, setCompletedSteps] = useState<ProcessingStep[]>([]);

  // Determine which steps to show based on input type
  const getSteps = (): ProcessingStep[] => {
    const steps: ProcessingStep[] = [];

    if (isVoiceInput) {
      steps.push('transcribing');
    }

    if (hasTamilInput) {
      steps.push('translating_input');
    }

    steps.push('understanding', 'planning', 'executing');

    if (hasTamilInput) {
      steps.push('translating_output');
    }

    return steps;
  };

  const steps = getSteps();

  // Progress through steps automatically
  useEffect(() => {
    if (!isProcessing) {
      setCurrentStep('understanding');
      setCompletedSteps([]);
      return;
    }

    let stepIndex = 0;
    setCurrentStep(steps[0]);
    setCompletedSteps([]);

    const progressToNextStep = () => {
      if (stepIndex < steps.length - 1) {
        setCompletedSteps(prev => [...prev, steps[stepIndex]]);
        stepIndex++;
        setCurrentStep(steps[stepIndex]);

        const nextDuration = STEPS_CONFIG[steps[stepIndex]].duration;
        if (nextDuration > 0) {
          setTimeout(progressToNextStep, nextDuration);
        }
      }
    };

    const initialDuration = STEPS_CONFIG[steps[0]].duration;
    const timer = setTimeout(progressToNextStep, initialDuration);

    return () => clearTimeout(timer);
  }, [isProcessing, isVoiceInput, hasTamilInput]);

  if (!isProcessing) return null;

  // Voice mode variant - centered, larger
  if (variant === 'voice') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className={cn("w-full max-w-md mx-auto", className)}
      >
        <div className="bg-zinc-900/80 backdrop-blur-xl border border-zinc-800 rounded-2xl p-6 shadow-2xl">
          {/* Current Step - Large */}
          <div className="flex items-center gap-4 mb-6">
            <motion.div
              animate={{
                scale: [1, 1.1, 1],
                rotate: [0, 5, -5, 0]
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
              className="w-14 h-14 rounded-xl bg-violet-500/20 flex items-center justify-center"
            >
              {(() => {
                const StepIcon = STEPS_CONFIG[currentStep].icon;
                return <StepIcon className="w-7 h-7 text-violet-400" />;
              })()}
            </motion.div>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-white">
                {STEPS_CONFIG[currentStep].label}
              </h3>
              <p className="text-sm text-zinc-400">
                {STEPS_CONFIG[currentStep].sublabel}
              </p>
            </div>
            <Loader2 className="w-5 h-5 text-violet-400 animate-spin" />
          </div>

          {/* Progress Steps */}
          <div className="flex items-center gap-2">
            {steps.map((step, index) => {
              const isCompleted = completedSteps.includes(step);
              const isCurrent = currentStep === step;

              return (
                <motion.div
                  key={step}
                  className="flex-1 h-1.5 rounded-full overflow-hidden bg-zinc-800"
                >
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: isCompleted ? '100%' : isCurrent ? '50%' : '0%'
                    }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                    className={cn(
                      "h-full rounded-full",
                      isCompleted ? "bg-green-500" : "bg-violet-500"
                    )}
                  />
                </motion.div>
              );
            })}
          </div>

          {/* Step Labels */}
          <div className="flex items-center justify-between mt-3">
            {steps.map((step, index) => {
              const isCompleted = completedSteps.includes(step);
              const isCurrent = currentStep === step;
              const StepIcon = STEPS_CONFIG[step].icon;

              return (
                <motion.div
                  key={step}
                  className="flex flex-col items-center gap-1"
                  animate={{
                    opacity: isCurrent ? 1 : isCompleted ? 0.7 : 0.4
                  }}
                >
                  <div className={cn(
                    "w-6 h-6 rounded-full flex items-center justify-center transition-colors",
                    isCompleted ? "bg-green-500/20" : isCurrent ? "bg-violet-500/20" : "bg-zinc-800"
                  )}>
                    {isCompleted ? (
                      <Check className="w-3 h-3 text-green-400" />
                    ) : (
                      <StepIcon className={cn(
                        "w-3 h-3",
                        isCurrent ? "text-violet-400" : "text-zinc-500"
                      )} />
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </motion.div>
    );
  }

  // Chat mode variant - compact, inline
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.95 }}
      className={cn("flex justify-start w-full", className)}
    >
      <div className="max-w-[85%] md:max-w-[75%]">
        {/* Avatar */}
        <div className="flex items-center gap-3 mb-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center text-[10px] font-black text-white">
            T
          </div>
          <span className="text-xs font-semibold text-zinc-400">Thara is thinking...</span>
        </div>

        {/* Processing Card */}
        <div className="bg-card/80 backdrop-blur-xl border border-border rounded-2xl rounded-tl-md p-4 shadow-lg">
          {/* Current Step */}
          <div className="flex items-center gap-3 mb-4">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              className="w-10 h-10 rounded-xl bg-violet-500/15 flex items-center justify-center"
            >
              {(() => {
                const StepIcon = STEPS_CONFIG[currentStep].icon;
                return <StepIcon className="w-5 h-5 text-violet-400" />;
              })()}
            </motion.div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-foreground">
                {STEPS_CONFIG[currentStep].label}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {STEPS_CONFIG[currentStep].sublabel}
              </p>
            </div>
          </div>

          {/* Mini Progress */}
          <div className="flex items-center gap-1.5">
            {steps.map((step, index) => {
              const isCompleted = completedSteps.includes(step);
              const isCurrent = currentStep === step;
              const StepIcon = STEPS_CONFIG[step].icon;

              return (
                <motion.div
                  key={step}
                  className={cn(
                    "flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium transition-all",
                    isCompleted
                      ? "bg-green-500/15 text-green-400"
                      : isCurrent
                        ? "bg-violet-500/15 text-violet-400"
                        : "bg-muted/50 text-muted-foreground"
                  )}
                  animate={isCurrent ? { scale: [1, 1.05, 1] } : {}}
                  transition={{ duration: 1, repeat: Infinity }}
                >
                  {isCompleted ? (
                    <Check className="w-3 h-3" />
                  ) : isCurrent ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    >
                      <Loader2 className="w-3 h-3" />
                    </motion.div>
                  ) : (
                    <StepIcon className="w-3 h-3" />
                  )}
                  <span className="hidden sm:inline">{STEPS_CONFIG[step].label}</span>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
