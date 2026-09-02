'use client';

import {
  Bot,
  Blocks,
  BookOpen,
  Box,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  CirclePlay,
  Database,
  GitBranch,
  GripVertical,
  Hand,
  LoaderCircle,
  Minus,
  MousePointer2,
  PanelRight,
  Plus,
  Rocket,
  Save,
  Settings2,
  ShieldCheck,
  Sparkles,
  Trash2,
  Undo2,
  UserRoundCheck,
  Wrench,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import Link from 'next/link';
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  executeBlueprint,
  getSession,
  releaseCheckBlueprint,
  saveBlueprint,
  type ExecutionResult,
  type ReleaseGateReport,
  type SessionIdentity,
} from '@/lib/agentblueprint-api';
import { SAMPLE_BLUEPRINT } from '@/lib/sample-blueprint';

type NodeKind =
  | 'input'
  | 'agent'
  | 'knowledge'
  | 'condition'
  | 'tool'
  | 'approval'
  | 'output';
type CanvasNode = {
  id: string;
  kind: NodeKind;
  title: string;
  description: string;
  x: number;
  y: number;
  status?: 'ready' | 'review';
};
type Edge = { from: string; to: string; label?: string };

const KIND_META: Record<
  NodeKind,
  { label: string; icon: LucideIcon; color: string; dot: string }
> = {
  input: {
    label: '开始',
    icon: CirclePlay,
    color: 'text-emerald-300',
    dot: 'bg-emerald-300',
  },
  agent: {
    label: 'AI Agent',
    icon: Bot,
    color: 'text-violet-300',
    dot: 'bg-violet-300',
  },
  knowledge: {
    label: '知识检索',
    icon: BookOpen,
    color: 'text-cyan-300',
    dot: 'bg-cyan-300',
  },
  condition: {
    label: '条件判断',
    icon: GitBranch,
    color: 'text-amber-300',
    dot: 'bg-amber-300',
  },
  tool: {
    label: '企业工具',
    icon: Wrench,
    color: 'text-blue-300',
    dot: 'bg-blue-300',
  },
  approval: {
    label: '人工审批',
    icon: UserRoundCheck,
    color: 'text-rose-300',
    dot: 'bg-rose-300',
  },
  output: {
    label: '输出',
    icon: Zap,
    color: 'text-emerald-300',
    dot: 'bg-emerald-300',
  },
};

const INITIAL_NODES: CanvasNode[] = [
  {
    id: 'start',
    kind: 'input',
    title: '用户请求',
    description: '接收订单号与退款原因',
    x: 60,
    y: 245,
  },
  {
    id: 'supervisor',
    kind: 'agent',
    title: '售后协调 Agent',
    description: '理解问题并安排处理步骤',
    x: 310,
    y: 245,
  },
  {
    id: 'rag',
    kind: 'knowledge',
    title: '退款政策 RAG',
    description: '切片 · 重排 · 上下文压缩',
    x: 570,
    y: 105,
  },
  {
    id: 'order',
    kind: 'tool',
    title: '订单核验',
    description: '读取订单与身份状态',
    x: 570,
    y: 385,
  },
  {
    id: 'rule',
    kind: 'condition',
    title: '退款规则判断',
    description: '是否满足自动退款条件',
    x: 830,
    y: 245,
  },
  {
    id: 'approval',
    kind: 'approval',
    title: '主管审批',
    description: '高风险操作需要人工确认',
    x: 1080,
    y: 385,
    status: 'review',
  },
  {
    id: 'answer',
    kind: 'output',
    title: '生成处理结果',
    description: '返回建议、依据与引用',
    x: 1080,
    y: 105,
  },
];

const INITIAL_EDGES: Edge[] = [
  { from: 'start', to: 'supervisor' },
  { from: 'supervisor', to: 'rag', label: '查政策' },
  { from: 'supervisor', to: 'order', label: '查订单' },
  { from: 'rag', to: 'rule' },
  { from: 'order', to: 'rule' },
  { from: 'rule', to: 'answer', label: '通过' },
  { from: 'rule', to: 'approval', label: '需复核' },
  { from: 'approval', to: 'answer' },
];

const PALETTE: { kind: NodeKind; title: string; description: string }[] = [
  { kind: 'agent', title: 'AI Agent', description: '理解、推理与分工' },
  { kind: 'knowledge', title: '知识检索', description: '企业 RAG 知识源' },
  { kind: 'condition', title: '条件判断', description: '规则与流程分支' },
  { kind: 'tool', title: '企业工具', description: '调用内部 API' },
  { kind: 'approval', title: '人工审批', description: '高风险操作确认' },
  { kind: 'output', title: '结果输出', description: '结构化回复用户' },
];

const NODE_WIDTH = 206;
const NODE_HEIGHT = 94;

function quoted(value: string) {
  return JSON.stringify(value.trim() || '未命名智能体');
}

function buildBlueprint(
  name: string,
  goal: string,
  role: string,
  knowledge: string,
) {
  return SAMPLE_BLUEPRINT.replace(
    'display_name: 售后退款助理',
    `display_name: ${quoted(name)}`,
  )
    .replace(
      'description: 依据售后政策为客服生成退款建议',
      `description: ${quoted(goal)}`,
    )
    .replace('    role: 售后退款助理', `    role: ${quoted(role)}`)
    .replace(
      '    goal: 基于有效政策给出可追溯的退款建议',
      `    goal: ${quoted(goal)}`,
    )
    .replace(
      '      description: 当前有效的退换货政策',
      `      description: ${quoted(knowledge)}`,
    );
}

function CanvasNodeCard({
  node,
  selected,
  panMode,
  onSelect,
  onDragStart,
}: {
  node: CanvasNode;
  selected: boolean;
  panMode: boolean;
  onSelect: () => void;
  onDragStart: (event: ReactPointerEvent<HTMLButtonElement>) => void;
}) {
  const meta = KIND_META[node.kind];
  const Icon = meta.icon;
  return (
    <button
      type="button"
      aria-label={`${node.title} 节点`}
      onClick={onSelect}
      onPointerDown={onDragStart}
      className={`absolute z-10 rounded-2xl border bg-[#151f32]/96 p-3 text-left shadow-[0_14px_35px_rgba(0,0,0,.28)] backdrop-blur ${panMode ? 'pointer-events-none' : 'cursor-grab active:cursor-grabbing'} ${
        selected
          ? 'border-cyan-300 ring-2 ring-cyan-300/15'
          : 'border-white/12 hover:border-white/25'
      }`}
      style={{
        left: node.x,
        top: node.y,
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
      }}
    >
      <span className="flex items-center justify-between">
        <span
          className={`flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.12em] ${meta.color}`}
        >
          <Icon className="size-3.5" /> {meta.label}
        </span>
        <GripVertical className="size-3.5 text-slate-600" />
      </span>
      <span className="mt-2 block truncate text-sm font-semibold text-slate-100">
        {node.title}
      </span>
      <span className="mt-1 block truncate text-[11px] text-slate-500">
        {node.description}
      </span>
      <span
        className={`absolute -right-1.5 top-[42px] size-3 rounded-full border-2 border-[#151f32] ${meta.dot}`}
      />
      <span
        className={`absolute -left-1.5 top-[42px] size-3 rounded-full border-2 border-[#151f32] ${meta.dot}`}
      />
    </button>
  );
}

export function CanvasWorkspace() {
  const [view, setView] = useState<'canvas' | 'wizard'>('canvas');
  const [canvasTool, setCanvasTool] = useState<'select' | 'pan'>('select');
  const [panning, setPanning] = useState(false);
  const [nodes, setNodes] = useState(INITIAL_NODES);
  const [edges, setEdges] = useState(INITIAL_EDGES);
  const [selectedId, setSelectedId] = useState('supervisor');
  const [zoom, setZoom] = useState(0.88);
  const [name, setName] = useState('售后退款助理');
  const [role, setRole] = useState('售后客服与订单运营团队的协作助理');
  const [goal, setGoal] = useState(
    '根据订单事实和有效政策，给出有依据、可追溯的退款处理建议',
  );
  const [knowledge, setKnowledge] = useState(
    '售后政策、退款规则、商品例外条款',
  );
  const [tools, setTools] = useState('订单系统：只读查询；退款系统：生成草稿');
  const [approval, setApproval] = useState(true);
  const [testMessage, setTestMessage] = useState(
    '订单 A1001 签收 3 天，客户想退款，需要什么材料？',
  );
  const [busy, setBusy] = useState<'save' | 'run' | 'gate' | null>(null);
  const [notice, setNotice] = useState(
    '画布修改已在当前页面生效；请点击“保存版本”持久化到企业空间。',
  );
  const [runResult, setRunResult] = useState<ExecutionResult | null>(null);
  const [gateResult, setGateResult] = useState<ReleaseGateReport | null>(null);
  const [consoleOpen, setConsoleOpen] = useState(false);
  const [identity, setIdentity] = useState<SessionIdentity | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{
    id: string;
    offsetX: number;
    offsetY: number;
  } | null>(null);
  const panRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    scrollLeft: number;
    scrollTop: number;
  } | null>(null);
  const sequenceRef = useRef(1);

  useEffect(() => {
    getSession()
      .then(setIdentity)
      .catch(() => setIdentity(null));
  }, []);

  const selected = nodes.find((node) => node.id === selectedId) ?? null;
  const blueprint = useMemo(
    () => buildBlueprint(name, goal, role, knowledge),
    [name, goal, role, knowledge],
  );

  function startDrag(
    event: ReactPointerEvent<HTMLButtonElement>,
    node: CanvasNode,
  ) {
    if (canvasTool === 'pan') return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    setSelectedId(node.id);
    dragRef.current = {
      id: node.id,
      offsetX: (event.clientX - rect.left) / zoom - node.x,
      offsetY: (event.clientY - rect.top) / zoom - node.y,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function startPan(event: ReactPointerEvent<HTMLDivElement>) {
    if (canvasTool !== 'pan' || event.button !== 0) return;
    panRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      scrollLeft: event.currentTarget.scrollLeft,
      scrollTop: event.currentTarget.scrollTop,
    };
    setPanning(true);
    event.currentTarget.setPointerCapture(event.pointerId);
    event.preventDefault();
  }

  function movePan(event: ReactPointerEvent<HTMLDivElement>) {
    const pan = panRef.current;
    if (!pan || pan.pointerId !== event.pointerId) return;
    event.currentTarget.scrollLeft =
      pan.scrollLeft - (event.clientX - pan.startX);
    event.currentTarget.scrollTop =
      pan.scrollTop - (event.clientY - pan.startY);
  }

  function endPan(event: ReactPointerEvent<HTMLDivElement>) {
    if (panRef.current?.pointerId !== event.pointerId) return;
    panRef.current = null;
    setPanning(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function moveNode(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!drag || !rect) return;
    const x = Math.max(
      16,
      Math.min(1280, (event.clientX - rect.left) / zoom - drag.offsetX),
    );
    const y = Math.max(
      16,
      Math.min(620, (event.clientY - rect.top) / zoom - drag.offsetY),
    );
    setNodes((current) =>
      current.map((node) => (node.id === drag.id ? { ...node, x, y } : node)),
    );
  }

  function addNode(kind: NodeKind, title: string, description: string) {
    const id = `${kind}-new-${sequenceRef.current++}`;
    const offset = nodes.length % 4;
    setNodes((current) => [
      ...current,
      {
        id,
        kind,
        title,
        description,
        x: 350 + offset * 90,
        y: 170 + offset * 95,
      },
    ]);
    setSelectedId(id);
    setNotice(`已添加“${title}”，可在右侧填写企业配置。`);
  }

  function updateSelected(patch: Partial<CanvasNode>) {
    setNodes((current) =>
      current.map((node) =>
        node.id === selectedId ? { ...node, ...patch } : node,
      ),
    );
  }

  function removeSelected() {
    if (!selected || selected.kind === 'input') return;
    setNodes((current) => current.filter((node) => node.id !== selected.id));
    setEdges((current) =>
      current.filter(
        (edge) => edge.from !== selected.id && edge.to !== selected.id,
      ),
    );
    setSelectedId('start');
  }

  function generateFlow() {
    setNodes(
      INITIAL_NODES.map((node) => {
        if (node.id === 'supervisor')
          return { ...node, title: name, description: goal };
        if (node.id === 'rag') return { ...node, description: knowledge };
        if (node.id === 'order') return { ...node, description: tools };
        return node;
      }).filter((node) => approval || node.id !== 'approval'),
    );
    setEdges(
      approval
        ? INITIAL_EDGES
        : INITIAL_EDGES.filter(
            (edge) => edge.from !== 'approval' && edge.to !== 'approval',
          ),
    );
    setSelectedId('supervisor');
    setView('canvas');
    setNotice('已根据业务表单生成流程，请逐个检查节点配置。');
  }

  async function perform(kind: 'save' | 'run' | 'gate') {
    setBusy(kind);
    setConsoleOpen(true);
    setNotice(
      kind === 'save'
        ? '正在保存企业版本…'
        : kind === 'run'
          ? '正在执行整条流程…'
          : '正在运行发布门禁…',
    );
    try {
      if (kind === 'save') {
        const saved = await saveBlueprint(blueprint);
        setNotice(`已保存 ${saved.display_name} · 版本 ${saved.version}`);
      } else if (kind === 'run') {
        const result = await executeBlueprint(
          blueprint,
          testMessage,
          `canvas-run-${sequenceRef.current++}`,
        );
        setRunResult(result.result);
        setNotice(
          result.result.status === 'pending_approval'
            ? '流程已暂停，正在等待人工审批。'
            : '测试运行完成。',
        );
      } else {
        const result = await releaseCheckBlueprint(blueprint);
        setGateResult(result.report);
        setNotice(
          result.report?.passed
            ? '发布门禁通过，可以进入版本发布。'
            : '门禁未通过，请先处理阻断项。',
        );
      }
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : '请求失败，请检查后端连接。',
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="flex h-screen min-h-[720px] flex-col overflow-hidden bg-[#0a1020] text-slate-100">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-white/8 bg-[#0d1526] px-4">
        <div className="flex min-w-0 items-center gap-3">
          <Link
            href="/"
            aria-label="AgentBlueprint 首页"
            className="grid size-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-cyan-300 to-violet-400 text-[#08101f]"
          >
            <Sparkles className="size-4" />
          </Link>
          <span className="hidden text-sm font-semibold sm:inline">
            AgentBlueprint
          </span>
          <span className="text-slate-700">/</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="truncate text-sm font-medium">{name}</span>
              <Badge
                variant="outline"
                className="border-white/10 text-[10px] text-slate-400"
              >
                草稿
              </Badge>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/security"
            className="hidden items-center gap-1.5 rounded-lg border border-white/8 bg-white/3 px-2.5 py-1.5 text-[11px] text-slate-400 lg:flex"
          >
            <ShieldCheck className="size-3.5 text-emerald-300" />
            {identity?.organization_id ?? '身份待验证'}
          </Link>
          <Button
            variant="ghost"
            size="sm"
            className="hidden text-slate-400 md:flex"
            onClick={() => perform('save')}
            disabled={busy !== null}
          >
            {busy === 'save' ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <Save />
            )}
            保存版本
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="border-white/10 bg-white/3"
            onClick={() => perform('gate')}
            disabled={busy !== null}
          >
            {busy === 'gate' ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <ShieldCheck />
            )}
            发布门禁
          </Button>
          <Link
            href="/evaluations"
            className="inline-flex h-8 items-center gap-2 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground"
          >
            <Rocket className="size-3.5" />
            发布
          </Link>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-[68px] shrink-0 flex-col items-center border-r border-white/8 bg-[#0d1526] py-3">
          {[
            ['/', BrainCircuit, '流程设计'],
            ['/modules', Blocks, '业务模块中心'],
            ['/blueprints', Box, '版本蓝图'],
            ['/knowledge', Database, '知识库'],
            ['/security', ShieldCheck, '企业与访问控制'],
            ['/evaluations', CheckCircle2, '评测发布'],
            ['/settings', Settings2, '环境设置'],
          ].map(([href, Icon, label], index) => (
            <Link
              key={String(label)}
              href={String(href)}
              aria-label={String(label)}
              title={String(label)}
              className={`mb-1 grid size-10 place-items-center rounded-xl ${index === 0 ? 'bg-cyan-300/12 text-cyan-300' : 'text-slate-600 hover:bg-white/5 hover:text-slate-300'}`}
            >
              <Icon className="size-4" />
            </Link>
          ))}
        </aside>

        <section className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-14 shrink-0 items-center justify-between border-b border-white/8 bg-[#0b1323] px-4">
            <div className="flex rounded-lg border border-white/8 bg-black/15 p-1">
              <button
                type="button"
                onClick={() => setView('wizard')}
                className={`rounded-md px-3 py-1.5 text-xs ${view === 'wizard' ? 'bg-white/10 text-white' : 'text-slate-500'}`}
              >
                业务向导
              </button>
              <button
                type="button"
                onClick={() => setView('canvas')}
                className={`rounded-md px-3 py-1.5 text-xs ${view === 'canvas' ? 'bg-white/10 text-white' : 'text-slate-500'}`}
              >
                高级画布
              </button>
            </div>
            <div className="hidden items-center gap-2 text-[11px] text-slate-500 md:flex">
              <ShieldCheck className="size-3.5 text-emerald-300" />
              身份隔离 <span className="text-slate-700">·</span> 工具审批{' '}
              <span className="text-slate-700">·</span> 全链路追踪
            </div>
          </div>

          {view === 'wizard' ? (
            <div className="min-h-0 flex-1 overflow-y-auto bg-grid p-5 sm:p-8">
              <div className="mx-auto max-w-3xl rounded-3xl border border-white/10 bg-[#101a2d]/95 p-6 shadow-2xl sm:p-8">
                <Badge className="bg-violet-300/10 text-violet-200">
                  企业智能体创建向导
                </Badge>
                <h1 className="mt-4 text-2xl font-semibold">
                  先说清楚业务，系统再生成流程
                </h1>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  不需要先写 YAML 或理解
                  Agent。下面这些内容是企业落地最少要讲清楚的边界。
                </p>
                <div className="mt-7 grid gap-5 sm:grid-cols-2">
                  <label
                    htmlFor="agent-name"
                    className="text-xs text-slate-400"
                  >
                    智能体名称
                    <Input
                      id="agent-name"
                      className="mt-2 border-white/10 bg-black/20"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </label>
                  <label
                    htmlFor="agent-role"
                    className="text-xs text-slate-400"
                  >
                    服务团队
                    <Input
                      id="agent-role"
                      className="mt-2 border-white/10 bg-black/20"
                      value={role}
                      onChange={(e) => setRole(e.target.value)}
                    />
                  </label>
                  <label
                    htmlFor="agent-goal"
                    className="text-xs text-slate-400 sm:col-span-2"
                  >
                    希望它完成什么
                    <Textarea
                      id="agent-goal"
                      className="mt-2 min-h-24 border-white/10 bg-black/20"
                      value={goal}
                      onChange={(e) => setGoal(e.target.value)}
                    />
                  </label>
                  <label
                    htmlFor="agent-knowledge"
                    className="text-xs text-slate-400"
                  >
                    使用哪些企业知识
                    <Textarea
                      id="agent-knowledge"
                      className="mt-2 min-h-24 border-white/10 bg-black/20"
                      value={knowledge}
                      onChange={(e) => setKnowledge(e.target.value)}
                    />
                  </label>
                  <label
                    htmlFor="agent-tools"
                    className="text-xs text-slate-400"
                  >
                    允许调用哪些系统
                    <Textarea
                      id="agent-tools"
                      className="mt-2 min-h-24 border-white/10 bg-black/20"
                      value={tools}
                      onChange={(e) => setTools(e.target.value)}
                    />
                  </label>
                </div>
                <button
                  type="button"
                  aria-label="切换高风险操作人工审批"
                  aria-pressed={approval}
                  onClick={() => setApproval(!approval)}
                  className="mt-5 flex w-full items-center justify-between rounded-xl border border-white/8 bg-black/15 p-4 text-left"
                >
                  <span>
                    <span className="block text-sm">
                      高风险操作需要人工审批
                    </span>
                    <span className="mt-1 block text-xs text-slate-500">
                      例如退款、付款、删除和对外发送
                    </span>
                  </span>
                  <span
                    className={`relative h-6 w-11 rounded-full ${approval ? 'bg-cyan-300' : 'bg-slate-700'}`}
                  >
                    <span
                      className={`absolute top-1 size-4 rounded-full bg-[#08101f] transition-all ${approval ? 'left-6' : 'left-1'}`}
                    />
                  </span>
                </button>
                <div className="mt-7 flex justify-end">
                  <Button size="lg" onClick={generateFlow}>
                    <Sparkles />
                    生成智能体流程
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex min-h-0 flex-1">
              <aside className="hidden w-56 shrink-0 overflow-y-auto border-r border-white/8 bg-[#0d1526] p-3 xl:block">
                <div className="mb-3 flex items-center justify-between px-2">
                  <span className="text-xs font-semibold">添加节点</span>
                  <Plus className="size-3.5 text-slate-500" />
                </div>
                <button
                  type="button"
                  onClick={() => setView('wizard')}
                  className="mb-4 w-full rounded-xl border border-violet-300/15 bg-violet-300/8 p-3 text-left hover:bg-violet-300/12"
                >
                  <span className="flex items-center gap-2 text-xs font-medium text-violet-200">
                    <Sparkles className="size-3.5" />
                    从业务描述生成
                  </span>
                  <span className="mt-1.5 block text-[10px] leading-4 text-slate-500">
                    填写目标、知识和工具即可
                  </span>
                </button>
                <p className="mb-2 px-2 text-[9px] font-semibold uppercase tracking-[.16em] text-slate-600">
                  基础能力
                </p>
                <div className="space-y-1.5">
                  {PALETTE.map((item) => {
                    const meta = KIND_META[item.kind];
                    const Icon = meta.icon;
                    return (
                      <button
                        key={item.kind}
                        type="button"
                        onClick={() =>
                          addNode(item.kind, item.title, item.description)
                        }
                        className="flex w-full items-center gap-3 rounded-xl border border-transparent p-2.5 text-left hover:border-white/8 hover:bg-white/4"
                      >
                        <span
                          className={`grid size-8 shrink-0 place-items-center rounded-lg bg-white/5 ${meta.color}`}
                        >
                          <Icon className="size-4" />
                        </span>
                        <span>
                          <span className="block text-xs font-medium">
                            {item.title}
                          </span>
                          <span className="mt-0.5 block text-[10px] text-slate-600">
                            {item.description}
                          </span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </aside>

              <div className="relative min-w-0 flex-1 overflow-hidden bg-[#080e1a]">
                <div className="absolute left-4 top-4 z-30 flex items-center gap-1 rounded-lg border border-white/8 bg-[#111a2b]/95 p-1 shadow-xl">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    title="选择"
                    aria-label="选择节点"
                    aria-pressed={canvasTool === 'select'}
                    onClick={() => setCanvasTool('select')}
                    className={
                      canvasTool === 'select'
                        ? 'bg-cyan-300/12 text-cyan-300'
                        : ''
                    }
                  >
                    <MousePointer2 />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    title="移动画布"
                    aria-label="使用小手移动画布"
                    aria-pressed={canvasTool === 'pan'}
                    onClick={() => setCanvasTool('pan')}
                    className={
                      canvasTool === 'pan' ? 'bg-cyan-300/12 text-cyan-300' : ''
                    }
                  >
                    <Hand />
                  </Button>
                  <span className="mx-1 h-5 w-px bg-white/8" />
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="缩小画布"
                    onClick={() => setZoom((z) => Math.max(0.55, z - 0.1))}
                  >
                    <Minus />
                  </Button>
                  <span className="w-10 text-center text-[10px] text-slate-400">
                    {Math.round(zoom * 100)}%
                  </span>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="放大画布"
                    onClick={() => setZoom((z) => Math.min(1.2, z + 0.1))}
                  >
                    <Plus />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    title="恢复布局"
                    aria-label="恢复默认布局"
                    onClick={() => {
                      setNodes(INITIAL_NODES);
                      setEdges(INITIAL_EDGES);
                      setZoom(0.88);
                      viewportRef.current?.scrollTo({ left: 0, top: 0 });
                    }}
                  >
                    <Undo2 />
                  </Button>
                </div>
                <div
                  ref={viewportRef}
                  onPointerDown={startPan}
                  onPointerMove={movePan}
                  onPointerUp={endPan}
                  onPointerCancel={endPan}
                  className={`absolute inset-0 overflow-auto ${canvasTool === 'pan' ? (panning ? 'cursor-grabbing' : 'cursor-grab') : ''}`}
                >
                  <div
                    ref={canvasRef}
                    onPointerMove={moveNode}
                    onPointerUp={() => {
                      dragRef.current = null;
                    }}
                    onPointerCancel={() => {
                      dragRef.current = null;
                    }}
                    className="bg-grid relative h-[760px] w-[1540px] select-none"
                    style={{
                      transformOrigin: 'top left',
                      transform: `scale(${zoom})`,
                    }}
                  >
                    <svg
                      className="pointer-events-none absolute inset-0 size-full overflow-visible"
                      aria-hidden="true"
                    >
                      <defs>
                        <marker
                          id="arrow"
                          markerWidth="8"
                          markerHeight="8"
                          refX="7"
                          refY="4"
                          orient="auto"
                        >
                          <path d="M0,0 L8,4 L0,8 Z" fill="#526178" />
                        </marker>
                      </defs>
                      {edges.map((edge) => {
                        const from = nodes.find(
                          (node) => node.id === edge.from,
                        );
                        const to = nodes.find((node) => node.id === edge.to);
                        if (!from || !to) return null;
                        const x1 = from.x + NODE_WIDTH;
                        const y1 = from.y + NODE_HEIGHT / 2;
                        const x2 = to.x;
                        const y2 = to.y + NODE_HEIGHT / 2;
                        const bend = Math.max(55, (x2 - x1) / 2);
                        return (
                          <g key={`${edge.from}-${edge.to}`}>
                            <path
                              d={`M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`}
                              fill="none"
                              stroke="#526178"
                              strokeWidth="1.6"
                              markerEnd="url(#arrow)"
                            />
                            {edge.label && (
                              <text
                                x={(x1 + x2) / 2}
                                y={(y1 + y2) / 2 - 8}
                                fill="#75839a"
                                fontSize="10"
                                textAnchor="middle"
                              >
                                {edge.label}
                              </text>
                            )}
                          </g>
                        );
                      })}
                    </svg>
                    {nodes.map((node) => (
                      <CanvasNodeCard
                        key={node.id}
                        node={node}
                        selected={selectedId === node.id}
                        panMode={canvasTool === 'pan'}
                        onSelect={() => setSelectedId(node.id)}
                        onDragStart={(event) => startDrag(event, node)}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <aside className="hidden w-[300px] shrink-0 overflow-y-auto border-l border-white/8 bg-[#0d1526] lg:block">
                <div className="flex h-12 items-center justify-between border-b border-white/8 px-4">
                  <span className="flex items-center gap-2 text-xs font-semibold">
                    <PanelRight className="size-3.5" />
                    节点配置
                  </span>
                  <ChevronDown className="size-3.5 text-slate-600" />
                </div>
                {selected ? (
                  <div className="space-y-5 p-4">
                    <div className="flex items-center gap-3">
                      <span
                        className={`grid size-9 place-items-center rounded-xl bg-white/5 ${KIND_META[selected.kind].color}`}
                      >
                        {(() => {
                          const Icon = KIND_META[selected.kind].icon;
                          return <Icon className="size-4" />;
                        })()}
                      </span>
                      <div>
                        <p className="text-sm font-medium">{selected.title}</p>
                        <p className="text-[10px] text-slate-600">
                          {selected.id}
                        </p>
                      </div>
                    </div>
                    <label
                      htmlFor="node-title"
                      className="block text-[11px] text-slate-500"
                    >
                      节点名称
                      <Input
                        id="node-title"
                        value={selected.title}
                        onChange={(e) =>
                          updateSelected({ title: e.target.value })
                        }
                        className="mt-2 border-white/10 bg-black/20 text-xs"
                      />
                    </label>
                    <label
                      htmlFor="node-description"
                      className="block text-[11px] text-slate-500"
                    >
                      任务说明
                      <Textarea
                        id="node-description"
                        value={selected.description}
                        onChange={(e) =>
                          updateSelected({ description: e.target.value })
                        }
                        className="mt-2 min-h-24 border-white/10 bg-black/20 text-xs"
                      />
                    </label>
                    {selected.kind === 'agent' && (
                      <>
                        <label
                          htmlFor="node-model"
                          className="block text-[11px] text-slate-500"
                        >
                          模型
                          <select
                            id="node-model"
                            className="mt-2 h-9 w-full rounded-lg border border-white/10 bg-[#0b1323] px-3 text-xs text-slate-300"
                          >
                            <option>企业默认模型</option>
                            <option>高推理模型</option>
                            <option>低成本模型</option>
                          </select>
                        </label>
                        <div className="text-[11px] text-slate-500">
                          允许转交给
                          <div>
                            <Badge
                              variant="outline"
                              className="mt-2 border-white/10 text-slate-400"
                            >
                              政策 Agent
                            </Badge>{' '}
                            <Badge
                              variant="outline"
                              className="mt-2 border-white/10 text-slate-400"
                            >
                              订单工具
                            </Badge>
                          </div>
                        </div>
                      </>
                    )}
                    {selected.kind === 'knowledge' && (
                      <div className="rounded-xl border border-cyan-300/10 bg-cyan-300/5 p-3">
                        <p className="text-xs text-cyan-200">检索策略已启用</p>
                        <p className="mt-2 text-[10px] leading-5 text-slate-500">
                          上下文增强切片 → 混合检索 → Rerank → 上下文压缩
                        </p>
                      </div>
                    )}
                    {selected.kind === 'tool' && (
                      <div className="rounded-xl border border-amber-300/10 bg-amber-300/5 p-3">
                        <p className="text-xs text-amber-200">工具权限</p>
                        <p className="mt-2 text-[10px] leading-5 text-slate-500">
                          默认只读；写操作会进入策略判断和人工审批。
                        </p>
                      </div>
                    )}
                    {selected.kind === 'approval' && (
                      <label
                        htmlFor="approval-role"
                        className="block text-[11px] text-slate-500"
                      >
                        审批角色
                        <Input
                          id="approval-role"
                          defaultValue="supervisor"
                          className="mt-2 border-white/10 bg-black/20 text-xs"
                        />
                      </label>
                    )}
                    <div className="border-t border-white/8 pt-4">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-rose-300 hover:bg-rose-300/8 hover:text-rose-200"
                        onClick={removeSelected}
                        disabled={selected.kind === 'input'}
                      >
                        <Trash2 />
                        删除节点
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="p-4 text-xs text-slate-500">请选择一个节点。</p>
                )}
              </aside>
            </div>
          )}

          <div className="shrink-0 border-t border-white/8 bg-[#0d1526]">
            <button
              type="button"
              className="flex h-10 w-full items-center justify-between px-4 text-left"
              onClick={() => setConsoleOpen(!consoleOpen)}
            >
              <span className="flex items-center gap-2 text-[11px] text-slate-400">
                <span
                  className={`size-2 rounded-full ${busy ? 'animate-pulse bg-amber-300' : 'bg-emerald-300'}`}
                />
                {notice}
              </span>
              <ChevronDown
                className={`size-3.5 text-slate-600 transition-transform ${consoleOpen ? 'rotate-180' : ''}`}
              />
            </button>
            {consoleOpen && (
              <div className="grid max-h-52 gap-4 overflow-y-auto border-t border-white/8 p-4 lg:grid-cols-[1fr_auto_1fr]">
                <div>
                  <label
                    htmlFor="test-message"
                    className="text-[10px] font-semibold uppercase tracking-[.14em] text-slate-600"
                  >
                    测试问题
                  </label>
                  <div className="mt-2 flex gap-2">
                    <Input
                      id="test-message"
                      value={testMessage}
                      onChange={(e) => setTestMessage(e.target.value)}
                      className="border-white/10 bg-black/20 text-xs"
                    />
                    <Button
                      size="sm"
                      onClick={() => perform('run')}
                      disabled={busy !== null}
                    >
                      {busy === 'run' ? (
                        <LoaderCircle className="animate-spin" />
                      ) : (
                        <CirclePlay />
                      )}
                      运行
                    </Button>
                  </div>
                </div>
                <div className="hidden w-px bg-white/8 lg:block" />
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[.14em] text-slate-600">
                    运行结果
                  </p>
                  {runResult ? (
                    <p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-300">
                      {runResult.answer ??
                        `等待 ${runResult.pending_approvals.length} 项人工审批`}
                    </p>
                  ) : gateResult ? (
                    <p
                      className={`mt-2 text-xs ${gateResult.passed ? 'text-emerald-300' : 'text-rose-300'}`}
                    >
                      门禁得分 {Math.round(gateResult.score * 100)}% ·{' '}
                      {gateResult.passed
                        ? '允许发布'
                        : `${gateResult.blockers.length} 项阻断`}
                    </p>
                  ) : (
                    <p className="mt-2 text-xs text-slate-600">
                      运行后这里会显示答案、引用、Agent 轨迹和审批状态。
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
