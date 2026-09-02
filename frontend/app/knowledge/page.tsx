'use client';

import { useEffect, useState } from 'react';
import { Database, LoaderCircle, Plus, Search } from 'lucide-react';

import { StudioShell } from '@/components/studio-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  addKnowledgeDocument,
  type KnowledgeRecord,
  listKnowledgeDocuments,
} from '@/lib/agentblueprint-api';

export default function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeRecord[]>([]);
  const [title, setTitle] = useState('售后退款政策');
  const [source, setSource] = useState('after_sales_policy');
  const [roles, setRoles] = useState('customer_service, supervisor');
  const [content, setContent] = useState(
    '普通商品签收七天内可以申请退款。退款需要订单号和购买凭证。',
  );
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(
    '录入文本后会在运行时经过上下文增强切片、混合召回、rerank 和压缩。',
  );
  const refresh = () =>
    listKnowledgeDocuments()
      .then(setItems)
      .catch((e) => setNotice(String(e)));
  useEffect(() => {
    void refresh();
  }, []);
  async function add() {
    setBusy(true);
    try {
      await addKnowledgeDocument({
        source_id: source,
        title,
        content,
        allowed_roles: roles
          .split(',')
          .map((x) => x.trim())
          .filter(Boolean),
        citation_base: `kb://${source}`,
      });
      await refresh();
      setNotice('知识文档已保存，可以用于评测和 RAG。');
    } catch (e) {
      setNotice(e instanceof Error ? e.message : '保存失败');
    } finally {
      setBusy(false);
    }
  }
  return (
    <StudioShell
      active="knowledge"
      title="企业知识库"
      description="管理带租户、角色权限、版本和引用地址的知识文档。"
      actions={
        <Button
          onClick={add}
          disabled={busy}
          className="bg-violet-300 text-slate-950 hover:bg-violet-200"
        >
          {busy ? <LoaderCircle className="animate-spin" /> : <Plus />}
          保存并索引
        </Button>
      }
    >
      <div className="mb-4 rounded-xl border border-white/8 bg-white/3 px-4 py-3 text-xs text-slate-400">
        {notice}
      </div>
      <div className="grid gap-4 xl:grid-cols-[.75fr_1.25fr]">
        <section className="rounded-2xl border border-white/8 bg-panel p-4">
          <h2 className="mb-4 text-sm font-medium">新增知识文档</h2>
          <label
            htmlFor="knowledge-title"
            className="mb-3 block text-xs text-slate-500"
          >
            标题
            <Input
              id="knowledge-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-2 border-white/10 bg-slate-950/60"
            />
          </label>
          <label
            htmlFor="knowledge-source"
            className="mb-3 block text-xs text-slate-500"
          >
            知识源 ID
            <Input
              id="knowledge-source"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="mt-2 border-white/10 bg-slate-950/60 font-mono"
            />
          </label>
          <label
            htmlFor="knowledge-roles"
            className="mb-3 block text-xs text-slate-500"
          >
            允许角色
            <Input
              id="knowledge-roles"
              value={roles}
              onChange={(e) => setRoles(e.target.value)}
              className="mt-2 border-white/10 bg-slate-950/60"
            />
          </label>
          <label
            htmlFor="knowledge-content"
            className="block text-xs text-slate-500"
          >
            正文
            <Textarea
              id="knowledge-content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="mt-2 min-h-72 border-white/10 bg-slate-950/60 text-sm leading-6"
            />
          </label>
        </section>
        <section className="rounded-2xl border border-white/8 bg-panel p-4">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="size-4 text-violet-300" />
              <h2 className="text-sm font-medium">已索引文档</h2>
            </div>
            <Badge className="bg-violet-300/10 text-violet-300">
              {items.length} documents
            </Badge>
          </div>
          {items.length === 0 ? (
            <div className="grid min-h-96 place-items-center rounded-xl border border-dashed border-white/10 text-center">
              <div>
                <Search className="mx-auto mb-3 size-8 text-slate-700" />
                <p className="text-sm text-slate-500">暂无知识文档</p>
              </div>
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {items.map((item) => (
                <article
                  key={item.id}
                  className="rounded-xl border border-white/8 bg-white/3 p-4"
                >
                  <div className="flex justify-between">
                    <h3 className="text-sm font-medium">{item.title}</h3>
                    <Badge variant="outline" className="border-white/10">
                      v{item.version}
                    </Badge>
                  </div>
                  <p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-500">
                    {item.content}
                  </p>
                  <p className="mt-3 font-mono text-[9px] text-violet-300">
                    {item.citation_base}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-1">
                    {item.allowed_roles.map((role) => (
                      <Badge
                        key={role}
                        className="bg-white/5 text-[9px] text-slate-400"
                      >
                        {role}
                      </Badge>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </StudioShell>
  );
}
