'use client';

import { useEffect, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Database,
  Fingerprint,
  KeyRound,
  LockKeyhole,
  RefreshCw,
  Server,
  ShieldCheck,
  UserRound,
  UsersRound,
  type LucideIcon,
} from 'lucide-react';

import { StudioShell } from '@/components/studio-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getSession, type SessionIdentity } from '@/lib/agentblueprint-api';

const roleNames: Record<string, string> = {
  organization_admin: '企业管理员',
  ai_developer: 'AI 开发者',
  business_owner: '业务负责人',
  customer_service: '客服人员',
  supervisor: '审批主管',
  auditor: '审计人员',
};

export default function SecurityPage() {
  const [identity, setIdentity] = useState<SessionIdentity | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  function refresh() {
    setLoading(true);
    setError('');
    getSession()
      .then(setIdentity)
      .catch((e) => setError(e instanceof Error ? e.message : '身份验证失败'))
      .finally(() => setLoading(false));
  }
  useEffect(() => {
    queueMicrotask(refresh);
  }, []);
  return (
    <StudioShell
      active="security"
      title="企业与访问控制"
      description="确认当前身份、安全边界和阶段 A 的落地状态。"
      actions={
        <Button
          variant="outline"
          onClick={refresh}
          disabled={loading}
          className="border-white/10 bg-white/3"
        >
          <RefreshCw className={loading ? 'animate-spin' : ''} />
          重新验证
        </Button>
      }
    >
      {error && (
        <div className="mb-5 rounded-xl border border-rose-300/15 bg-rose-300/5 p-4 text-sm text-rose-200">
          {error}。请到环境设置检查后端地址或访问令牌。
        </div>
      )}
      <div className="grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
        <section className="overflow-hidden rounded-2xl border border-white/8 bg-panel">
          <div className="border-b border-white/8 p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-xl bg-cyan-300/10 text-cyan-300">
                  <Fingerprint className="size-5" />
                </span>
                <div>
                  <h2 className="text-sm font-medium">当前验证身份</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    来自后端 RequestContext，不读取前端租户输入
                  </p>
                </div>
              </div>
              <Badge
                className={
                  identity
                    ? 'bg-emerald-300/10 text-emerald-300'
                    : 'bg-slate-300/10 text-slate-400'
                }
              >
                {identity ? '已验证' : '等待连接'}
              </Badge>
            </div>
          </div>
          <div className="grid gap-px bg-white/8 sm:grid-cols-2">
            <IdentityItem
              icon={Server}
              label="企业组织"
              value={identity?.organization_id ?? '—'}
            />
            <IdentityItem
              icon={UserRound}
              label="用户身份"
              value={identity?.display_name ?? identity?.user_id ?? '—'}
            />
            <IdentityItem
              icon={KeyRound}
              label="用户标识"
              value={identity?.user_id ?? '—'}
            />
            <IdentityItem
              icon={LockKeyhole}
              label="身份来源"
              value={identity ? 'JWT / Membership' : '—'}
            />
          </div>
          <div className="p-5">
            <p className="text-[10px] font-semibold uppercase tracking-[.14em] text-slate-600">
              已授予角色
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {identity?.roles.length ? (
                identity.roles.map((role) => (
                  <Badge
                    key={role}
                    variant="outline"
                    className="border-cyan-300/15 bg-cyan-300/5 text-cyan-200"
                  >
                    {roleNames[role] ?? role}
                  </Badge>
                ))
              ) : (
                <span className="text-xs text-slate-600">尚未取得角色</span>
              )}
            </div>
          </div>
        </section>
        <section className="rounded-2xl border border-white/8 bg-panel p-5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-violet-300" />
            <h2 className="text-sm font-medium">身份信任链</h2>
          </div>
          <div className="mt-5 space-y-2">
            {[
              '验证 Bearer Token 签名和有效期',
              '读取签名中的组织与用户',
              '查询平台 Membership',
              '采用数据库中的角色',
              '生成不可变 RequestContext',
            ].map((item, index) => (
              <div
                key={item}
                className="flex items-center gap-3 rounded-xl bg-white/3 px-3 py-3"
              >
                <span className="grid size-6 shrink-0 place-items-center rounded-full bg-emerald-300/10 text-[10px] text-emerald-300">
                  {index + 1}
                </span>
                <span className="text-xs text-slate-300">{item}</span>
                {index < 4 && (
                  <ArrowRight className="ml-auto size-3 text-slate-700" />
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
      <section className="mt-5 rounded-2xl border border-white/8 bg-panel p-5">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-sm font-medium">阶段 A 安全底座</h2>
            <p className="mt-1 text-xs text-slate-500">
              网站只展示已经真实实现的能力，未完成项不会标记为可用于生产。
            </p>
          </div>
          <Badge
            variant="outline"
            className="border-amber-300/20 text-amber-200"
          >
            进行中
          </Badge>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <StageCard
            icon={Fingerprint}
            title="A1 身份与租户"
            status="完成"
            done
            items="JWT / OIDC、Membership、服务端租户"
          />
          <StageCard
            icon={Database}
            title="A2 生产数据库"
            status="下一步"
            items="PostgreSQL、迁移、行级安全"
          />
          <StageCard
            icon={Server}
            title="A3 运行持久化"
            status="待实施"
            items="Checkpointer、审批恢复、运行事件"
          />
          <StageCard
            icon={UsersRound}
            title="A4 成员管理"
            status="待实施"
            items="邀请、分配角色、停用和登录页面"
          />
        </div>
      </section>
    </StudioShell>
  );
}

function IdentityItem({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-panel p-5">
      <Icon className="size-4 text-slate-600" />
      <p className="mt-3 text-[10px] uppercase tracking-[.12em] text-slate-600">
        {label}
      </p>
      <p className="mt-1 truncate font-mono text-xs text-slate-200">{value}</p>
    </div>
  );
}
function StageCard({
  icon: Icon,
  title,
  status,
  items,
  done = false,
}: {
  icon: LucideIcon;
  title: string;
  status: string;
  items: string;
  done?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-4 ${done ? 'border-emerald-300/15 bg-emerald-300/5' : 'border-white/8 bg-black/10'}`}
    >
      <div className="flex items-center justify-between">
        <Icon
          className={`size-4 ${done ? 'text-emerald-300' : 'text-slate-600'}`}
        />
        {done && <CheckCircle2 className="size-4 text-emerald-300" />}
      </div>
      <p className="mt-4 text-sm font-medium">{title}</p>
      <p
        className={`mt-1 text-xs ${done ? 'text-emerald-300' : 'text-slate-500'}`}
      >
        {status}
      </p>
      <p className="mt-3 text-[11px] leading-5 text-slate-600">{items}</p>
    </div>
  );
}
