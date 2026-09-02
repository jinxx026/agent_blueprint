'use client';

import { useEffect, useState } from 'react';
import {
  CheckCircle2,
  LoaderCircle,
  Play,
  Rocket,
  ShieldX,
} from 'lucide-react';

import { StudioShell } from '@/components/studio-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  type BlueprintRecord,
  type EvaluationRecord,
  evaluateStoredBlueprint,
  listBlueprints,
  listEvaluations,
  publishBlueprint,
} from '@/lib/agentblueprint-api';

export default function EvaluationsPage() {
  const [blueprints, setBlueprints] = useState<BlueprintRecord[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [runs, setRuns] = useState<EvaluationRecord[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(
    '先选择一个已保存蓝图，再运行回归评测。',
  );
  useEffect(() => {
    listBlueprints()
      .then((items) => {
        setBlueprints(items);
        if (items[0]) {
          setSelected(items[0].id);
          void listEvaluations(items[0].id).then(setRuns);
        }
      })
      .catch((e) => setNotice(String(e)));
  }, []);
  async function choose(id: string) {
    setSelected(id);
    setRuns(await listEvaluations(id));
  }
  async function evaluate() {
    if (!selected) return;
    setBusy(true);
    try {
      const result = await evaluateStoredBlueprint(selected);
      setRuns(await listEvaluations(selected));
      setNotice(
        result.passed
          ? `评测通过：${Math.round(result.score * 100)} 分，可以发布。`
          : '评测失败，发布被阻断。',
      );
    } catch (e) {
      setNotice(e instanceof Error ? e.message : '评测失败');
    } finally {
      setBusy(false);
    }
  }
  async function publish() {
    if (!selected) return;
    setBusy(true);
    try {
      const result = await publishBlueprint(selected, 'production');
      setNotice(`版本 ${result.blueprint_version} 已发布到 production。`);
      setBlueprints(await listBlueprints());
    } catch (e) {
      setNotice(e instanceof Error ? e.message : '发布失败');
    } finally {
      setBusy(false);
    }
  }
  const latest = runs[0];
  return (
    <StudioShell
      active="evaluations"
      title="评测与发布"
      description="运行固定验收集，只有达到分数和安全要求的版本才能进入生产。"
      actions={
        <>
          <Button
            onClick={evaluate}
            disabled={busy || !selected}
            variant="outline"
            className="border-emerald-300/20 bg-emerald-300/5 text-emerald-300"
          >
            {busy ? <LoaderCircle className="animate-spin" /> : <Play />}
            运行评测
          </Button>
          <Button
            onClick={publish}
            disabled={busy || !latest?.passed}
            className="bg-cyan-300 text-slate-950 hover:bg-cyan-200"
          >
            <Rocket />
            发布生产
          </Button>
        </>
      }
    >
      <div className="mb-4 rounded-xl border border-white/8 bg-white/3 px-4 py-3 text-xs text-slate-400">
        {notice}
      </div>
      <div className="grid gap-4 xl:grid-cols-[.65fr_1.35fr]">
        <section className="rounded-2xl border border-white/8 bg-panel p-4">
          <h2 className="mb-3 text-sm font-medium">选择蓝图</h2>
          <div className="space-y-2">
            {blueprints.map((item) => (
              <button
                key={item.id}
                onClick={() => choose(item.id)}
                className={`w-full rounded-xl border p-3 text-left ${selected === item.id ? 'border-cyan-300/30 bg-cyan-300/5' : 'border-white/8 bg-white/3'}`}
              >
                <div className="flex justify-between">
                  <span className="text-sm">{item.display_name}</span>
                  <Badge className="bg-white/5 text-slate-400">
                    {item.stage}
                  </Badge>
                </div>
                <p className="mt-1 font-mono text-[10px] text-slate-600">
                  v{item.version}
                </p>
              </button>
            ))}
            {blueprints.length === 0 && (
              <p className="rounded-xl border border-dashed border-white/10 p-6 text-center text-xs text-slate-600">
                请先到蓝图库保存一个蓝图
              </p>
            )}
          </div>
        </section>
        <section className="rounded-2xl border border-white/8 bg-panel p-4">
          {!latest ? (
            <div className="grid min-h-[460px] place-items-center text-center">
              <div>
                <CheckCircle2 className="mx-auto mb-3 size-9 text-slate-700" />
                <p className="text-sm text-slate-500">还没有评测记录</p>
              </div>
            </div>
          ) : (
            <div>
              <div
                className={`mb-4 rounded-xl border p-5 ${latest.passed ? 'border-emerald-300/20 bg-emerald-300/5' : 'border-rose-300/20 bg-rose-300/5'}`}
              >
                <div className="flex items-end justify-between">
                  <div className="flex items-center gap-3">
                    {latest.passed ? (
                      <CheckCircle2 className="size-7 text-emerald-300" />
                    ) : (
                      <ShieldX className="size-7 text-rose-300" />
                    )}
                    <div>
                      <p className="text-lg font-semibold">
                        {latest.passed ? '发布门禁通过' : '发布门禁阻断'}
                      </p>
                      <p className="text-xs text-slate-500">
                        Blueprint v{latest.blueprint_version}
                      </p>
                    </div>
                  </div>
                  <p className="font-mono text-4xl font-semibold">
                    {Math.round(latest.score * 100)}
                    <span className="text-sm text-slate-500">%</span>
                  </p>
                </div>
              </div>
              <div className="space-y-3">
                {latest.report.cases.map((item) => (
                  <article
                    key={item.case_id}
                    className="rounded-xl border border-white/8 bg-white/3 p-4"
                  >
                    <div className="flex justify-between">
                      <div>
                        <p className="text-sm font-medium">
                          {item.description}
                        </p>
                        <p className="mt-1 font-mono text-[9px] text-slate-600">
                          {item.case_id}
                        </p>
                      </div>
                      <Badge
                        className={
                          item.passed
                            ? 'bg-emerald-300/10 text-emerald-300'
                            : 'bg-rose-300/10 text-rose-300'
                        }
                      >
                        {item.passed ? 'PASS' : 'FAIL'}
                      </Badge>
                    </div>
                    <div className="mt-3 grid gap-1 sm:grid-cols-5">
                      {item.checks.map((check) => (
                        <div
                          key={check.check}
                          className="rounded-lg bg-slate-950/50 px-2 py-2 text-center"
                        >
                          <p className="truncate text-[9px] text-slate-500">
                            {check.check}
                          </p>
                          <p
                            className={`mt-1 text-[10px] ${check.passed ? 'text-emerald-300' : 'text-rose-300'}`}
                          >
                            {check.passed ? '通过' : '失败'}
                          </p>
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </StudioShell>
  );
}
