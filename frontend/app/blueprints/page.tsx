'use client';

import { useEffect, useState } from 'react';
import { FileCode2, History, LoaderCircle, Save } from 'lucide-react';

import { StudioShell } from '@/components/studio-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  type BlueprintRecord,
  type BlueprintVersion,
  listBlueprints,
  listBlueprintVersions,
  saveBlueprint,
} from '@/lib/agentblueprint-api';
import { SAMPLE_BLUEPRINT } from '@/lib/sample-blueprint';

export default function BlueprintsPage() {
  const [content, setContent] = useState(SAMPLE_BLUEPRINT);
  const [items, setItems] = useState<BlueprintRecord[]>([]);
  const [versions, setVersions] = useState<BlueprintVersion[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(
    '可以保存示例蓝图，系统会自动校验并建立版本。',
  );
  const refresh = () =>
    listBlueprints()
      .then(setItems)
      .catch((e) => setNotice(String(e)));
  useEffect(() => {
    void refresh();
  }, []);
  async function save() {
    setBusy(true);
    try {
      const saved = await saveBlueprint(content);
      setSelected(saved.id);
      setVersions(await listBlueprintVersions(saved.id));
      await refresh();
      setNotice(`已保存 ${saved.display_name} v${saved.version}`);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : '保存失败');
    } finally {
      setBusy(false);
    }
  }
  async function choose(item: BlueprintRecord) {
    setSelected(item.id);
    setContent(item.content);
    setVersions(await listBlueprintVersions(item.id));
    setNotice(`已载入 ${item.display_name}`);
  }
  return (
    <StudioShell
      active="blueprints"
      title="智能体蓝图库"
      description="保存经过校验的业务蓝图，并保留不可变版本记录。"
      actions={
        <Button
          onClick={save}
          disabled={busy}
          className="bg-cyan-300 text-slate-950 hover:bg-cyan-200"
        >
          {busy ? <LoaderCircle className="animate-spin" /> : <Save />}
          保存当前版本
        </Button>
      }
    >
      <div className="mb-4 rounded-xl border border-white/8 bg-white/3 px-4 py-3 text-xs text-slate-400">
        {notice}
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.2fr_.8fr]">
        <section className="overflow-hidden rounded-2xl border border-white/8 bg-panel">
          <div className="flex h-12 items-center gap-2 border-b border-white/8 px-4">
            <FileCode2 className="size-4 text-cyan-300" />
            <h2 className="text-sm font-medium">YAML 编辑器</h2>
          </div>
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            spellCheck={false}
            className="min-h-[650px] resize-none rounded-none border-0 bg-transparent p-4 font-mono text-[11px] leading-5 focus-visible:ring-0"
          />
        </section>
        <div className="space-y-4">
          <section className="rounded-2xl border border-white/8 bg-panel p-4">
            <h2 className="mb-3 text-sm font-medium">已保存蓝图</h2>
            <div className="space-y-2">
              {items.length === 0 ? (
                <Empty text="还没有保存的蓝图" />
              ) : (
                items.map((item) => (
                  <button
                    onClick={() => choose(item)}
                    key={item.id}
                    className={`w-full rounded-xl border p-3 text-left ${selected === item.id ? 'border-cyan-300/30 bg-cyan-300/5' : 'border-white/8 bg-white/3 hover:bg-white/5'}`}
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{item.display_name}</p>
                      <Badge className="bg-white/5 text-slate-400">
                        {item.stage}
                      </Badge>
                    </div>
                    <p className="mt-1 font-mono text-[10px] text-slate-500">
                      {item.name} · v{item.version}
                    </p>
                  </button>
                ))
              )}
            </div>
          </section>
          <section className="rounded-2xl border border-white/8 bg-panel p-4">
            <div className="mb-3 flex items-center gap-2">
              <History className="size-4 text-violet-300" />
              <h2 className="text-sm font-medium">版本历史</h2>
            </div>
            {versions.length === 0 ? (
              <Empty text="选择蓝图后查看版本" />
            ) : (
              <div className="space-y-2">
                {versions.map((v) => (
                  <div key={v.id} className="rounded-lg bg-white/3 p-3">
                    <div className="flex justify-between text-xs">
                      <span>v{v.version}</span>
                      <span className="text-slate-500">{v.stage}</span>
                    </div>
                    <p className="mt-2 truncate font-mono text-[9px] text-slate-600">
                      SHA {v.content_hash}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </StudioShell>
  );
}
function Empty({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-dashed border-white/10 p-6 text-center text-xs text-slate-600">
      {text}
    </div>
  );
}
