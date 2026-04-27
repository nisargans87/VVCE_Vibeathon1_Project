import React from 'react';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'primary', delay = 0 }) {
  const colorMap = {
    primary: 'bg-primary/10 text-primary',
    safe: 'bg-safe/10 text-safe',
    warning: 'bg-warning/10 text-warning',
    danger: 'bg-danger/10 text-danger',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
    >
      <Card className="p-5 sm:p-6 hover:shadow-lg transition-shadow duration-300 border-0 shadow-sm">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground font-medium">{title}</p>
            <p className="text-2xl sm:text-3xl font-heading font-bold text-foreground">{value}</p>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
          <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center", colorMap[color])}>
            <Icon className="w-6 h-6" />
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
