import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useLanguage } from '@/lib/LanguageContext';
import { base44 } from '@/api/base44Client';
import {
  LayoutDashboard, Shield, BookOpen, AlertTriangle,
  Landmark, Lock, FileWarning, Users, Menu, X,
  ChevronRight, LogOut
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const navItems = [
  { key: 'dashboard', path: '/', icon: LayoutDashboard },
  { key: 'fraudDetection', path: '/fraud-detection', icon: Shield },
  { key: 'financialLiteracy', path: '/financial-literacy', icon: BookOpen },
  { key: 'fraudAwareness', path: '/fraud-awareness', icon: AlertTriangle },
  { key: 'bankingRules', path: '/banking-rules', icon: Landmark },
  { key: 'security', path: '/security', icon: Lock },
  { key: 'grievance', path: '/grievance', icon: FileWarning },
  { key: 'guardians', path: '/guardians', icon: Users },
];

export default function Sidebar() {
  const { t } = useLanguage();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    base44.auth.logout();
  };

  const NavContent = () => (
    <div className="flex flex-col h-full">
      <div className="p-6 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-sidebar-primary flex items-center justify-center">
            <Shield className="w-5 h-5 text-sidebar-primary-foreground" />
          </div>
          <div>
            <h1 className="font-heading text-lg font-bold text-sidebar-primary-foreground">SafePay</h1>
            <p className="text-xs text-sidebar-foreground/60">Secure · Simple · Smart</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;
          return (
            <Link
              key={item.key}
              to={item.path}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-lg shadow-sidebar-primary/20"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              )}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <span className="truncate">{t(item.key)}</span>
              {isActive && <ChevronRight className="w-4 h-4 ml-auto" />}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-sidebar-border">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent"
          onClick={handleLogout}
        >
          <LogOut className="w-5 h-5" />
          {t('logout')}
        </Button>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile toggle */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-4 left-4 z-50 lg:hidden bg-card shadow-lg"
        onClick={() => setMobileOpen(!mobileOpen)}
      >
        {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </Button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-40 w-72 bg-sidebar transition-transform duration-300 lg:translate-x-0",
        mobileOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <NavContent />
      </aside>
    </>
  );
}
