'use client';

import { useEffect, useState, type ReactNode } from 'react';
import {
  Activity,
  Blocks,
  Bot,
  CheckCircle2,
  Database,
  Settings2,
  ShieldCheck,
  Sparkles,
  UserRound,
} from 'lucide-react';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  getApiBase,
  getSession,
  type SessionIdentity,
} from '@/lib/agentblueprint-api';

const nav = [
  ['workspace', '工作台', Activity, '/'],
  ['modules', '业务模块中心', Blocks, '/modules'],
  ['blueprints', '智能体蓝图', Bot, '/blueprints'],
  ['knowledge', '企业知识库', Database, '/knowledge'],
  ['security', '企业与访问控制', ShieldCheck, '/security'],
  ['evaluations', '评测与发布', CheckCircle2, '/evaluations'],
] as const;

export function StudioShell({
  active,
  title,
  description,
  actions,
  children,
}: {
  active: string;
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [hosted, setHosted] = useState(false);
  const [identity, setIdentity] = useState<SessionIdentity | null>(null);
  useEffect(() => {
    const api = getApiBase();
    const isHosted =
      window.location.protocol === 'https:' && api.startsWith('http://');
    if (isHosted) {
      queueMicrotask(() => {
        setHosted(true);
        setConnected(false);
      });
      return;
    }
    let alive = true;
    const check = () =>
      fetch(`${api}/health`, { cache: 'no-store' })
        .then((r) => {
          if (alive) setConnected(r.ok);
          if (r.ok)
            getSession()
              .then((value) => alive && setIdentity(value))
              .catch(() => alive && setIdentity(null));
        })
        .catch(() => alive && setConnected(false));
    void check();
    const timer = window.setInterval(check, 5000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);
  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="flex h-16 items-center justify-between border-b border-white/8 px-5 lg:px-7">
        <Link href="/" className="flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-300">
            <Sparkles className="size-4" />
          </span>
          <span>
            <span className="block text-sm font-semibold">AgentBlueprint</span>
            <span className="block text-[10px] uppercase tracking-[.18em] text-slate-500">
              Enterprise AI Studio
            </span>
          </span>
        </Link>
        <div className="flex items-center gap-2">
          {identity && (
            <Link
              href="/security"
              className="hidden items-center gap-2 rounded-lg border border-white/8 bg-white/3 px-3 py-1.5 text-xs text-slate-300 sm:flex"
            >
              <UserRound className="size-3.5 text-cyan-300" />
              <span>{identity.display_name ?? identity.user_id}</span>
              <span className="text-slate-600">·</span>
              <span className="font-mono text-slate-500">
                {identity.organization_id}
              </span>
            </Link>
          )}
          <Badge
            className={
              connected
                ? 'bg-emerald-300/10 text-emerald-300'
                : hosted
                  ? 'bg-amber-300/10 text-amber-200'
                  : 'bg-rose-300/10 text-rose-300'
            }
          >
            {connected
              ? '身份已验证'
              : hosted
                ? '线上后端待部署'
                : connected === null
                  ? '检测后端'
                  : '后端未启动'}
          </Badge>
          <Link href="/settings">
            <Button variant="outline" className="border-white/10 bg-white/3">
              <Settings2 />
              环境设置
            </Button>
          </Link>
        </div>
      </header>
      <div className="grid min-h-[calc(100vh-64px)] lg:grid-cols-[236px_minmax(0,1fr)]">
        <aside className="hidden border-r border-white/8 p-4 lg:flex lg:flex-col">
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[.16em] text-slate-600">
            Enterprise Studio
          </p>
          <nav className="space-y-1">
            {nav.map(([id, label, Icon, href]) => (
              <Link
                key={id}
                href={href}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm ${active === id ? 'bg-white/8 text-white' : 'text-slate-500 hover:bg-white/5 hover:text-slate-200'}`}
              >
                <Icon className="size-4" />
                {label}
              </Link>
            ))}
          </nav>
          <div className="mt-auto rounded-xl border border-white/8 bg-white/3 p-3">
            <p className="text-xs text-slate-500">当前安全边界</p>
            <p className="mt-1 truncate font-mono text-xs text-cyan-300">
              {identity?.organization_id ?? '等待身份验证'}
            </p>
            <p className="mt-3 text-[11px] leading-5 text-slate-500">
              组织和角色由服务端签名身份与 Membership 决定，不能由前端修改。
            </p>
          </div>
        </aside>
        <section className="min-w-0 p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-[1400px]">
            <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                  {title}
                </h1>
                <p className="mt-2 text-sm text-slate-500">{description}</p>
              </div>
              {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
            </div>
            {children}
          </div>
        </section>
      </div>
    </main>
  );
}
