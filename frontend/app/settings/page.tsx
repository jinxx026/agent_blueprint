'use client';

import { useEffect, useState } from 'react';
import {
  Check,
  KeyRound,
  RotateCcw,
  Server,
  Settings2,
  ShieldCheck,
  UserRound,
} from 'lucide-react';

import { StudioShell } from '@/components/studio-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DEFAULT_API_BASE,
  getAccessToken,
  getApiBase,
  getSession,
  setAccessToken,
  type SessionIdentity,
} from '@/lib/agentblueprint-api';

export default function SettingsPage() {
  const [api, setApi] = useState(DEFAULT_API_BASE);
  const [token, setToken] = useState('');
  const [identity, setIdentity] = useState<SessionIdentity | null>(null);
  const [checking, setChecking] = useState(false);
  const [notice, setNotice] = useState(
    '设置只保存在当前设备。企业身份由后端验证，不能在前端手动指定。',
  );

  async function verify() {
    setChecking(true);
    try {
      const session = await getSession();
      setIdentity(session);
      setNotice(`连接成功：已验证 ${session.organization_id} 企业空间。`);
    } catch (error) {
      setIdentity(null);
      setNotice(
        error instanceof Error
          ? `连接未验证：${error.message}`
          : '连接未验证，请检查后端地址和访问令牌。',
      );
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    queueMicrotask(() => {
      setApi(getApiBase());
      setToken(getAccessToken());
      void verify();
    });
  }, []);

  async function save() {
    localStorage.setItem('agentblueprint:api-base', api.replace(/\/$/, ''));
    localStorage.removeItem('agentblueprint:tenant-id');
    setAccessToken(token);
    await verify();
  }

  async function reset() {
    localStorage.removeItem('agentblueprint:api-base');
    localStorage.removeItem('agentblueprint:tenant-id');
    setAccessToken('');
    setApi(DEFAULT_API_BASE);
    setToken('');
    await verify();
  }

  return (
    <StudioShell
      active="settings"
      title="环境与身份设置"
      description="连接企业后端，并确认当前设备代表的真实用户与组织。"
      actions={
        <>
          <Button
            variant="outline"
            onClick={reset}
            className="border-white/10 bg-white/3"
          >
            <RotateCcw />
            恢复默认
          </Button>
          <Button
            onClick={save}
            disabled={checking}
            className="bg-cyan-300 text-slate-950 hover:bg-cyan-200"
          >
            <Check />
            {checking ? '正在验证' : '保存并验证'}
          </Button>
        </>
      }
    >
      <div
        className={`mb-4 rounded-xl border px-4 py-3 text-xs ${identity ? 'border-emerald-300/15 bg-emerald-300/5 text-emerald-100/80' : 'border-white/8 bg-white/3 text-slate-400'}`}
      >
        {notice}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-white/8 bg-panel p-5">
          <div className="mb-5 flex items-center gap-2">
            <Server className="size-4 text-cyan-300" />
            <h2 className="text-sm font-medium">API 与访问凭证</h2>
          </div>
          <label
            htmlFor="api-base"
            className="mb-4 block text-xs text-slate-500"
          >
            后端 API 地址
            <Input
              id="api-base"
              value={api}
              onChange={(event) => setApi(event.target.value)}
              className="mt-2 h-10 border-white/10 bg-slate-950/60 font-mono"
            />
          </label>
          <label
            htmlFor="access-token"
            className="block text-xs text-slate-500"
          >
            Bearer Token（JWT / OIDC 环境）
            <div className="relative mt-2">
              <KeyRound className="absolute left-3 top-3 size-4 text-slate-700" />
              <Input
                id="access-token"
                type="password"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                placeholder="本地开发模式可留空"
                autoComplete="off"
                className="h-10 border-white/10 bg-slate-950/60 pl-9 font-mono"
              />
            </div>
          </label>
          <p className="mt-4 text-[11px] leading-5 text-slate-600">
            线上版本必须使用 HTTPS 后端。令牌仅存于当前浏览器，不会写入
            Blueprint，也不会作为模型上下文发送。
          </p>
        </section>

        <section className="rounded-2xl border border-white/8 bg-panel p-5">
          <div className="mb-5 flex items-center gap-2">
            <ShieldCheck className="size-4 text-violet-300" />
            <h2 className="text-sm font-medium">已验证企业身份</h2>
          </div>
          <div className="space-y-3">
            <IdentityLine
              icon={Server}
              label="企业组织"
              value={identity?.organization_id ?? '等待后端验证'}
            />
            <IdentityLine
              icon={UserRound}
              label="当前用户"
              value={identity?.display_name ?? identity?.user_id ?? '—'}
            />
            <IdentityLine
              icon={KeyRound}
              label="角色权限"
              value={identity?.roles.join('、') || '—'}
            />
          </div>
          <div className="mt-5 rounded-xl border border-cyan-300/10 bg-cyan-300/5 p-3 text-xs leading-5 text-cyan-100/65">
            企业编号和角色来自已签名身份与后端 Membership，前端没有修改入口。
          </div>
        </section>

        <section className="rounded-2xl border border-white/8 bg-panel p-5 lg:col-span-2">
          <div className="mb-5 flex items-center gap-2">
            <Settings2 className="size-4 text-violet-300" />
            <h2 className="text-sm font-medium">运行适配器</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <SettingLine label="流程编排" value="LangGraph" />
            <SettingLine label="Agent 抽象" value="LangChain" />
            <SettingLine label="RAG" value="Hybrid + Rerank" />
            <SettingLine label="身份" value="JWT / OIDC" />
            <SettingLine label="持久化" value="SQLite（开发）" />
          </div>
          <div className="mt-5 rounded-xl border border-amber-300/15 bg-amber-300/5 p-3 text-xs leading-5 text-amber-100/70">
            模型密钥、数据库密码和连接器凭证必须配置在后端 Secret Manager
            中，不能从这个页面传给模型。
          </div>
        </section>
      </div>
    </StudioShell>
  );
}

function IdentityLine({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Server;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-white/3 px-3 py-3 text-xs">
      <Icon className="size-4 shrink-0 text-slate-600" />
      <span className="text-slate-500">{label}</span>
      <span className="ml-auto max-w-[60%] truncate font-mono text-slate-200">
        {value}
      </span>
    </div>
  );
}

function SettingLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-white/3 px-3 py-2.5 text-xs">
      <span className="text-slate-500">{label}</span>
      <Badge className="bg-emerald-300/10 text-emerald-300">{value}</Badge>
    </div>
  );
}
