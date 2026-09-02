'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  Blocks,
  BookOpen,
  Bot,
  Check,
  Database,
  FileSearch,
  Filter,
  LoaderCircle,
  PackageCheck,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
  Unplug,
  Wrench,
} from 'lucide-react';

import { StudioShell } from '@/components/studio-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  installBusinessModule,
  listBusinessModules,
  uninstallBusinessModule,
  type BusinessModule,
  type RagProfile,
} from '@/lib/agentblueprint-api';

const DEFAULT_RAG: RagProfile = {
  strategy: 'hybrid',
  chunk_strategy: 'contextual',
  chunk_size: 800,
  chunk_overlap: 120,
  candidate_count: 20,
  top_k: 5,
  rerank: true,
  compression: true,
  return_citations: true,
  source_ids: [],
};

const FALLBACK_MODULES: BusinessModule[] = [
  [
    'customer-service',
    '智能客服与售后',
    '客户服务',
    '回答政策问题、查询订单，并将退款等高风险动作交给人工审批。',
    3,
    'medium',
    ['产品手册', '售后政策', '历史工单'],
    ['CRM', '工单系统', '订单系统'],
  ],
  [
    'contract-review',
    '合同审查助手',
    '法务合规',
    '识别风险条款、比对标准模板，并输出带原文引用的审查意见。',
    4,
    'high',
    ['合同模板', '法务规则', '历史意见'],
    ['合同系统', '文档库'],
  ],
  [
    'hr-policy',
    '员工制度助手',
    '人力资源',
    '基于员工身份解释制度、福利和办事流程，隔离敏感人事数据。',
    2,
    'medium',
    ['员工手册', '福利制度', '办事指南'],
    ['HRIS', '企业门户'],
  ],
  [
    'sales-copilot',
    '销售方案助手',
    '销售增长',
    '结合客户资料和产品能力生成拜访准备、方案草稿与跟进建议。',
    3,
    'medium',
    ['产品资料', '客户画像', '成功案例'],
    ['CRM', '邮件', '报价系统'],
  ],
  [
    'finance-audit',
    '费用审核助手',
    '财务运营',
    '依据公司制度核验报销材料，标出异常并保留完整审计证据。',
    3,
    'high',
    ['财务制度', '费用标准', '审计案例'],
    ['ERP', '报销系统', '发票平台'],
  ],
  [
    'operations-sop',
    '运营 SOP 助手',
    '运营管理',
    '将分散流程沉淀为可执行指引，遇到例外情况自动升级负责人。',
    2,
    'low',
    ['SOP', '岗位手册', '异常案例'],
    ['知识库', '任务系统'],
  ],
].map(
  ([
    key,
    name,
    category,
    description,
    agentCount,
    risk,
    knowledge,
    connectors,
  ]) => ({
    key: String(key),
    name: String(name),
    category: String(category),
    description: String(description),
    agent_count: Number(agentCount),
    risk_level: risk as BusinessModule['risk_level'],
    knowledge_types: knowledge as string[],
    connectors: connectors as string[],
    installed: false,
    installation_id: null,
    rag: null,
    updated_at: null,
  }),
);

const riskText = { low: '低风险', medium: '中风险', high: '高风险' };
const categories = [
  '全部',
  ...new Set(FALLBACK_MODULES.map((item) => item.category)),
];

export default function ModulesPage() {
  const [modules, setModules] = useState(FALLBACK_MODULES);
  const [selectedKey, setSelectedKey] = useState(FALLBACK_MODULES[0].key);
  const [category, setCategory] = useState('全部');
  const [rag, setRag] = useState<RagProfile>(DEFAULT_RAG);
  const [sourceText, setSourceText] = useState('');
  const [busy, setBusy] = useState<'load' | 'save' | 'remove' | null>('load');
  const [connected, setConnected] = useState(false);
  const [notice, setNotice] = useState('正在读取企业已经启用的模块…');

  const selected =
    modules.find((item) => item.key === selectedKey) ?? modules[0];
  const visible = useMemo(
    () =>
      modules.filter(
        (item) => category === '全部' || item.category === category,
      ),
    [modules, category],
  );
  const installedCount = modules.filter((item) => item.installed).length;

  async function refresh() {
    setBusy('load');
    try {
      const result = await listBusinessModules();
      setModules(result);
      setConnected(true);
      setNotice('模块目录已与企业空间同步。选择模块后可配置独立 RAG。');
      const current = result.find((item) => item.key === selectedKey);
      if (current?.rag) {
        setRag({ ...current.rag, source_ids: [...current.rag.source_ids] });
        setSourceText(current.rag.source_ids.join(', '));
      }
    } catch {
      setConnected(false);
      setNotice(
        '当前展示产品目录预览；连接企业后端后即可保存安装和 RAG 配置。',
      );
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => {
    let active = true;
    void listBusinessModules()
      .then((result) => {
        if (!active) return;
        setModules(result);
        setConnected(true);
        setNotice('模块目录已与企业空间同步。选择模块后可配置独立 RAG。');
        const current = result.find(
          (item) => item.key === FALLBACK_MODULES[0].key,
        );
        if (current?.rag) {
          setRag({ ...current.rag, source_ids: [...current.rag.source_ids] });
          setSourceText(current.rag.source_ids.join(', '));
        }
      })
      .catch(() => {
        if (!active) return;
        setConnected(false);
        setNotice(
          '当前展示产品目录预览；连接企业后端后即可保存安装和 RAG 配置。',
        );
      })
      .finally(() => {
        if (active) setBusy(null);
      });
    return () => {
      active = false;
    };
  }, []);

  function applyModule(module: BusinessModule) {
    setSelectedKey(module.key);
    const profile = module.rag ?? DEFAULT_RAG;
    setRag({ ...profile, source_ids: [...profile.source_ids] });
    setSourceText(profile.source_ids.join(', '));
  }

  async function save() {
    if (!selected) return;
    setBusy('save');
    try {
      const saved = await installBusinessModule(selected.key, {
        ...rag,
        source_ids: sourceText
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
      });
      setModules((current) =>
        current.map((item) => (item.key === saved.key ? saved : item)),
      );
      applyModule(saved);
      setConnected(true);
      setNotice(`${saved.name} 已启用，独立 RAG 策略已保存。`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : '模块保存失败');
    } finally {
      setBusy(null);
    }
  }

  async function uninstall() {
    if (!selected?.installed) return;
    setBusy('remove');
    try {
      await uninstallBusinessModule(selected.key);
      setModules((current) =>
        current.map((item) =>
          item.key === selected.key
            ? {
                ...item,
                installed: false,
                installation_id: null,
                rag: null,
                updated_at: null,
              }
            : item,
        ),
      );
      setRag(DEFAULT_RAG);
      setSourceText('');
      setNotice(`${selected.name} 已从企业空间停用，平台模板仍然保留。`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : '模块停用失败');
    } finally {
      setBusy(null);
    }
  }

  return (
    <StudioShell
      active="modules"
      title="业务模块中心"
      description="企业选择需要的 AI 能力，并为每个模块配置独立知识、检索和安全策略。"
      actions={
        <Button
          variant="outline"
          onClick={refresh}
          disabled={busy !== null}
          className="border-white/10 bg-white/3"
        >
          <RefreshCw className={busy === 'load' ? 'animate-spin' : ''} />
          同步企业配置
        </Button>
      }
    >
      <div
        className={`mb-5 flex items-center gap-3 rounded-xl border px-4 py-3 text-xs ${connected ? 'border-emerald-300/15 bg-emerald-300/5 text-emerald-100/75' : 'border-amber-300/15 bg-amber-300/5 text-amber-100/70'}`}
      >
        {connected ? (
          <PackageCheck className="size-4 text-emerald-300" />
        ) : (
          <Unplug className="size-4 text-amber-300" />
        )}
        {notice}
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <Metric
          icon={Blocks}
          label="可选业务模块"
          value={String(modules.length)}
          tone="cyan"
        />
        <Metric
          icon={PackageCheck}
          label="企业已启用"
          value={String(installedCount)}
          tone="emerald"
        />
        <Metric
          icon={Database}
          label="独立 RAG 配置"
          value={String(installedCount)}
          tone="violet"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_420px]">
        <section className="rounded-2xl border border-white/8 bg-panel p-4">
          <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h2 className="text-sm font-medium">模块目录</h2>
              <p className="mt-1 text-[11px] text-slate-600">
                一个企业可以组合多个模块，不需要从零搭建每套 Agent。
              </p>
            </div>
            <div className="flex flex-wrap gap-1">
              <Filter className="mr-1 mt-2 size-3.5 text-slate-600" />
              {categories.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setCategory(item)}
                  className={`rounded-lg px-2.5 py-1.5 text-[10px] ${category === item ? 'bg-cyan-300/10 text-cyan-300' : 'text-slate-500 hover:bg-white/5'}`}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {visible.map((module) => (
              <ModuleCard
                key={module.key}
                module={module}
                selected={module.key === selectedKey}
                onSelect={() => applyModule(module)}
              />
            ))}
          </div>
        </section>

        <aside className="rounded-2xl border border-white/8 bg-panel p-5 xl:sticky xl:top-5 xl:self-start">
          <div className="flex items-start justify-between gap-3">
            <div>
              <Badge className="bg-violet-300/10 text-violet-200">
                模块专属配置
              </Badge>
              <h2 className="mt-3 text-lg font-semibold">{selected?.name}</h2>
              <p className="mt-1 text-xs text-slate-500">
                每个模块独立保存，互不影响。
              </p>
            </div>
            {selected?.installed && (
              <Badge className="bg-emerald-300/10 text-emerald-300">
                <Check className="size-3" />
                已启用
              </Badge>
            )}
          </div>

          <div className="mt-5 grid grid-cols-2 gap-3">
            <SelectField
              label="召回策略"
              value={rag.strategy}
              onChange={(value) =>
                setRag((current) => ({
                  ...current,
                  strategy: value as RagProfile['strategy'],
                }))
              }
              options={[
                ['hybrid', '混合召回'],
                ['semantic', '语义召回'],
                ['keyword', '关键词召回'],
              ]}
            />
            <SelectField
              label="切片方式"
              value={rag.chunk_strategy}
              onChange={(value) =>
                setRag((current) => ({
                  ...current,
                  chunk_strategy: value as RagProfile['chunk_strategy'],
                }))
              }
              options={[
                ['contextual', '上下文增强'],
                ['structure', '按文档结构'],
                ['fixed', '固定长度'],
              ]}
            />
            <NumberField
              label="切片长度"
              value={rag.chunk_size}
              onChange={(value) =>
                setRag((current) => ({ ...current, chunk_size: value }))
              }
            />
            <NumberField
              label="切片重叠"
              value={rag.chunk_overlap}
              onChange={(value) =>
                setRag((current) => ({ ...current, chunk_overlap: value }))
              }
            />
            <NumberField
              label="初次召回数"
              value={rag.candidate_count}
              onChange={(value) =>
                setRag((current) => ({ ...current, candidate_count: value }))
              }
            />
            <NumberField
              label="最终上下文数"
              value={rag.top_k}
              onChange={(value) =>
                setRag((current) => ({ ...current, top_k: value }))
              }
            />
          </div>

          <label
            htmlFor="rag-sources"
            className="mt-4 block text-[10px] font-semibold uppercase tracking-[.12em] text-slate-600"
          >
            绑定知识源 ID
          </label>
          <Input
            id="rag-sources"
            value={sourceText}
            onChange={(event) => setSourceText(event.target.value)}
            placeholder="contracts, legal-rules"
            className="mt-2 border-white/10 bg-slate-950/60 font-mono text-xs"
          />

          <div className="mt-4 space-y-2">
            <ToggleLine
              icon={FileSearch}
              label="Rerank 二次排序"
              active={rag.rerank}
              onClick={() =>
                setRag((current) => ({ ...current, rerank: !current.rerank }))
              }
            />
            <ToggleLine
              icon={Sparkles}
              label="上下文压缩"
              active={rag.compression}
              onClick={() =>
                setRag((current) => ({
                  ...current,
                  compression: !current.compression,
                }))
              }
            />
            <ToggleLine
              icon={ShieldCheck}
              label="强制返回引用"
              active={rag.return_citations}
              onClick={() =>
                setRag((current) => ({
                  ...current,
                  return_citations: !current.return_citations,
                }))
              }
            />
          </div>

          <div className="mt-5 rounded-xl border border-white/8 bg-black/15 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[.12em] text-slate-600">
              实际检索链路
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[10px] text-slate-400">
              <span>上下文切片</span>
              <ArrowRight className="size-3 text-slate-700" />
              <span>{rag.candidate_count} 条召回</span>
              <ArrowRight className="size-3 text-slate-700" />
              <span>Rerank</span>
              <ArrowRight className="size-3 text-slate-700" />
              <span>{rag.top_k} 条压缩上下文</span>
            </div>
          </div>

          <div className="mt-5 flex gap-2">
            <Button
              onClick={save}
              disabled={busy !== null}
              className="flex-1 bg-cyan-300 text-slate-950 hover:bg-cyan-200"
            >
              {busy === 'save' ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <Save />
              )}
              {selected?.installed ? '更新配置' : '启用模块'}
            </Button>
            {selected?.installed && (
              <Button
                variant="outline"
                size="icon"
                onClick={uninstall}
                disabled={busy !== null}
                aria-label="停用模块"
                className="border-rose-300/15 text-rose-300 hover:bg-rose-300/5"
              >
                <Trash2 />
              </Button>
            )}
          </div>
        </aside>
      </div>
    </StudioShell>
  );
}

function ModuleCard({
  module,
  selected,
  onSelect,
}: {
  module: BusinessModule;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`rounded-2xl border p-4 text-left transition ${selected ? 'border-cyan-300/35 bg-cyan-300/5' : 'border-white/8 bg-white/3 hover:border-white/18 hover:bg-white/5'}`}
    >
      <div className="flex items-start justify-between gap-3">
        <span
          className={`grid size-9 place-items-center rounded-xl ${selected ? 'bg-cyan-300/12 text-cyan-300' : 'bg-white/5 text-slate-500'}`}
        >
          <Bot className="size-4" />
        </span>
        <div className="flex gap-1.5">
          {module.installed && (
            <Badge className="bg-emerald-300/10 text-[9px] text-emerald-300">
              已启用
            </Badge>
          )}
          <Badge
            variant="outline"
            className={`text-[9px] ${module.risk_level === 'high' ? 'border-rose-300/15 text-rose-300' : 'border-white/10 text-slate-500'}`}
          >
            {riskText[module.risk_level]}
          </Badge>
        </div>
      </div>
      <p className="mt-4 text-sm font-semibold">{module.name}</p>
      <p className="mt-1 text-[10px] text-cyan-300/70">
        {module.category} · {module.agent_count} 个 Agent
      </p>
      <p className="mt-3 min-h-10 text-[11px] leading-5 text-slate-500">
        {module.description}
      </p>
      <div className="mt-3 flex items-center gap-2 border-t border-white/6 pt-3 text-[10px] text-slate-600">
        <BookOpen className="size-3" />
        {module.knowledge_types.join(' · ')}
      </div>
      <div className="mt-2 flex items-center gap-2 text-[10px] text-slate-600">
        <Wrench className="size-3" />
        {module.connectors.join(' · ')}
      </div>
    </button>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Blocks;
  label: string;
  value: string;
  tone: 'cyan' | 'emerald' | 'violet';
}) {
  const colors = {
    cyan: 'text-cyan-300 bg-cyan-300/10',
    emerald: 'text-emerald-300 bg-emerald-300/10',
    violet: 'text-violet-300 bg-violet-300/10',
  };
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/8 bg-panel p-4">
      <span
        className={`grid size-9 place-items-center rounded-xl ${colors[tone]}`}
      >
        <Icon className="size-4" />
      </span>
      <div>
        <p className="text-xl font-semibold">{value}</p>
        <p className="text-[10px] text-slate-600">{label}</p>
      </div>
    </div>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[][];
}) {
  return (
    <label className="text-[10px] text-slate-600">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1.5 h-9 w-full rounded-lg border border-white/10 bg-slate-950/70 px-2 text-xs text-slate-300 outline-none focus:border-cyan-300/40"
      >
        {options.map(([key, text]) => (
          <option key={key} value={key}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-[10px] text-slate-600">
      {label}
      <Input
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-1.5 h-9 border-white/10 bg-slate-950/70 text-xs"
      />
    </label>
  );
}

function ToggleLine({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: typeof FileSearch;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className="flex w-full items-center gap-3 rounded-xl bg-white/3 px-3 py-2.5 text-xs"
    >
      <Icon
        className={active ? 'size-4 text-violet-300' : 'size-4 text-slate-700'}
      />
      <span className="text-slate-400">{label}</span>
      <span
        className={`ml-auto flex h-5 w-9 items-center rounded-full p-0.5 transition ${active ? 'bg-cyan-300/70' : 'bg-slate-800'}`}
      >
        <span
          className={`size-4 rounded-full bg-white transition-transform ${active ? 'translate-x-4' : ''}`}
        />
      </span>
    </button>
  );
}
