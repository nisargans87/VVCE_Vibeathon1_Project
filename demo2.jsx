import React from 'react';
import { Card } from '@/components/ui/card';
import { useLanguage } from '@/lib/LanguageContext';
import { ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react';
import { motion } from 'framer-motion';

export default function RiskGauge({ score = 25 }) {
  const { t } = useLanguage();

  const getLevel = () => {
    if (score <= 33) return { label: t('low'), color: 'text-safe', bg: 'bg-safe', icon: ShieldCheck };
    if (score <= 66) return { label: t('medium'), color: 'text-warning', bg: 'bg-warning', icon: ShieldAlert };
    return { label: t('high'), color: 'text-danger', bg: 'bg-danger', icon: ShieldX };
  };

  const level = getLevel();
  const Icon = level.icon;

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.3 }}>
      <Card className="p-6 border-0 shadow-sm">
        <h3 className="font-heading font-semibold text-foreground mb-4">{t('riskScore')}</h3>
        <div className="flex items-center gap-6">
          <div className="relative w-24 h-24">
            <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="42" fill="none" stroke="hsl(var(--muted))" strokeWidth="8" />
              <circle
                cx="50" cy="50" r="42"
                fill="none"
                stroke={score <= 33 ? 'hsl(var(--safe))' : score <= 66 ? 'hsl(var(--warning))' : 'hsl(var(--danger))'}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${score * 2.64} 264`}
                className="transition-all duration-1000"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xl font-bold font-heading">{score}</span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Icon className={`w-6 h-6 ${level.color}`} />
              <span className={`text-lg font-semibold ${level.color}`}>{level.label}</span>
            </div>
            <p className="text-sm text-muted-foreground">
              {score <= 33
                ? 'Your account is well protected'
                : score <= 66
                ? 'Some activities need attention'
                : 'Immediate action required'}
            </p>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
