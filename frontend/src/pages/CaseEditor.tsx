// File: src/pages/CaseEditor.tsx
// Description: A production‑ready veterinary Case Editor page with autosave, validation,
// attachments upload, and bilingual (CN/EN) labels. Uses React Hook Form + Zod + Tailwind + shadcn/ui.
// Assumes a REST API like FastAPI with routes:
//   GET    /api/cases/:id
//   POST   /api/cases         (create new)
//   PUT    /api/cases/:id     (update)
//   POST   /api/files         (multipart upload) -> returns {id,url,name,type,size}
// and a base URL in env: import.meta.env.VITE_API_BASE (e.g. "https://your-backend.example.com").

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useForm, Controller, useFieldArray } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useParams, useNavigate } from "react-router-dom";

// shadcn/ui components (make sure you've installed them in your project)
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { X, Plus, Save, Upload, Loader2, CalendarIcon } from "lucide-react";

// -----------------------------
// Schema & Types
// -----------------------------

const MedicationSchema = z.object({
  drug: z.string().min(1, "必填 | Required"),
  dose: z.string().optional().default(""),
  freq: z.string().optional().default(""),
  route: z.string().optional().default(""),
  duration: z.string().optional().default("")
});

const ProcedureSchema = z.object({
  name: z.string().min(1, "必填 | Required"),
  date: z.string().optional().default(""), // ISO date string
  notes: z.string().optional().default("")
});

const AttachmentSchema = z.object({
  id: z.string(),
  url: z.string().url(),
  name: z.string(),
  type: z.string().optional().default(""),
  size: z.number().optional().default(0)
});

const CaseSchema = z.object({
  status: z.enum(["draft", "open", "closed"]).default("draft"),
  patient: z.object({
    name: z.string().min(1, "必填 | Required"),
    species: z.enum(["canine", "feline", "other"]).default("canine"),
    breed: z.string().optional().default(""),
    sex: z.enum(["M", "F", "MN", "FN", "Unknown"]).default("Unknown"),
    ageYears: z.coerce.number().min(0).max(40).optional(),
    ageMonths: z.coerce.number().min(0).max(12).optional(),
    weightKg: z.coerce.number().min(0).max(200).optional(),
    microchip: z.string().optional().default("")
  }),
  owner: z.object({
    name: z.string().optional().default(""),
    phone: z.string().optional().default(""),
    email: z.string().email("邮箱格式不正确 | Invalid email").optional().or(z.literal(""))
  }),
  complaint: z.string().optional().default(""),
  history: z.string().optional().default(""),
  vitals: z.object({
    tempC: z.coerce.number().min(20).max(45).optional(),
    hr: z.coerce.number().min(0).max(400).optional(),
    rr: z.coerce.number().min(0).max(200).optional(),
    sbp: z.coerce.number().min(0).max(300).optional()
  }).optional().default({}),
  exam: z.string().optional().default(""),
  labs: z.string().optional().default(""),
  imaging: z.string().optional().default(""),
  diagnoses: z.array(z.string()).default([]),
  assessment: z.string().optional().default(""),
  plan: z.string().optional().default(""),
  medications: z.array(MedicationSchema).default([]),
  procedures: z.array(ProcedureSchema).default([]),
  followUpDate: z.string().optional(), // ISO date
  attachments: z.array(AttachmentSchema).default([]),
  pinned: z.boolean().default(false)
});

export type CaseForm = z.infer<typeof CaseSchema>;

// -----------------------------
// Utilities
// -----------------------------

const API_BASE = (import.meta as any).env?.VITE_API_BASE || "";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    credentials: "include",
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function uploadFile(file: File): Promise<z.infer<typeof AttachmentSchema>> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/files`, { method: "POST", body: form, credentials: "include" });
  if (!res.ok) throw new Error(`Upload failed: ${await res.text()}`);
  return res.json();
}

function useDebouncedCallback(cb: () => void, delay = 1200) {
  const timer = useRef<number | null>(null);
  return useCallback(() => {
    if (timer.current) window.clearTimeout(timer.current);
    // @ts-ignore
    timer.current = window.setTimeout(cb, delay);
  }, [cb, delay]);
}

// -----------------------------
// Small UI helpers
// -----------------------------

function Row({ label, children }: { label: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-12 gap-4 items-start">
      <Label className="col-span-12 md:col-span-2 text-sm text-muted-foreground pt-2">{label}</Label>
      <div className="col-span-12 md:col-span-10">{children}</div>
    </div>
  );
}

function Section({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <Card className="rounded-2xl shadow-sm border-muted">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-lg font-semibold">{title}</CardTitle>
        <div>{right}</div>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}

// -----------------------------
// Main Page Component
// -----------------------------

export default function CaseEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = !id || id === "new";

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [autosaveAt, setAutosaveAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<CaseForm>({
    resolver: zodResolver(CaseSchema),
    defaultValues: {
      status: "draft",
      patient: { name: "", species: "canine", breed: "", sex: "Unknown" },
      owner: { name: "", phone: "", email: "" },
      diagnoses: [],
      medications: [],
      procedures: [],
      attachments: [],
      pinned: false,
    },
    mode: "onChange",
  });

  const { control, register, handleSubmit, watch, setValue, reset, formState } = form;
  const { errors, isDirty } = formState;

  const medsFA = useFieldArray({ control, name: "medications" });
  const procsFA = useFieldArray({ control, name: "procedures" });

  // Load existing case
  useEffect(() => {
    let ignore = false;
    async function run() {
      if (isNew) return;
      setLoading(true);
      setError(null);
      try {
        const data = await api<CaseForm>(`/api/cases/${id}`);
        if (!ignore) reset(data);
      } catch (e: any) {
        if (!ignore) setError(e.message || String(e));
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    run();
    return () => {
      ignore = true;
    };
  }, [id, isNew, reset]);

  // Autosave
  const doSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      const values = CaseSchema.parse(watch());
      if (isNew) {
        const created = await api<{ id: string }>(`/api/cases`, {
          method: "POST",
          body: JSON.stringify(values),
        });
        setAutosaveAt(new Date().toLocaleString());
        navigate(`/cases/${created.id}/edit`, { replace: true });
      } else {
        await api(`/api/cases/${id}`, { method: "PUT", body: JSON.stringify(values) });
        setAutosaveAt(new Date().toLocaleString());
      }
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setSaving(false);
    }
  }, [id, isNew, navigate, watch]);

  const debouncedSave = useDebouncedCallback(() => {
    if (formState.isValid) doSave();
  }, 1500);

  useEffect(() => {
    const sub = watch(() => {
      if (!formState.isValid) return; // wait until valid
      debouncedSave();
    });
    return () => sub.unsubscribe();
  }, [watch, debouncedSave, formState.isValid]);

  // Prompt when leaving with unsaved changes
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [isDirty]);

  // Keyboard shortcut: Cmd/Ctrl+S
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        handleSubmit(() => doSave())();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleSubmit, doSave]);

  // Diagnoses chips
  const diagnoses = watch("diagnoses");
  const [diagInput, setDiagInput] = useState("");
  const addDiag = () => {
    const v = diagInput.trim();
    if (!v) return;
    setValue("diagnoses", Array.from(new Set([...(diagnoses || []), v])));
    setDiagInput("");
  };
  const removeDiag = (d: string) => setValue("diagnoses", (diagnoses || []).filter((x) => x !== d));

  const onSubmit = handleSubmit(async () => doSave());

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-2xl font-semibold leading-tight">病例编辑 / Case Editor</h1>
          <p className="text-sm text-muted-foreground">{isNew ? "新建病例 | Create new case" : `编辑病例 #${id} | Edit case`}</p>
        </div>
        <div className="flex items-center gap-2">
          {saving ? (
            <Button disabled variant="secondary" className="min-w-24"><Loader2 className="mr-2 h-4 w-4 animate-spin"/>保存中</Button>
          ) : (
            <Button onClick={onSubmit} className="min-w-24"><Save className="mr-2 h-4 w-4"/>保存 (⌘/Ctrl+S)</Button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl p-3">{error}</div>
      )}
      {autosaveAt && (
        <div className="mb-4 text-xs text-muted-foreground">已自动保存 / Autosaved: {autosaveAt}</div>
      )}

      <Tabs defaultValue="core" className="space-y-4">
        <TabsList>
          <TabsTrigger value="core">基本信息</TabsTrigger>
          <TabsTrigger value="soap">SOAP</TabsTrigger>
          <TabsTrigger value="tx">用药/处置</TabsTrigger>
          <TabsTrigger value="attachments">附件</TabsTrigger>
          <TabsTrigger value="meta">其他</TabsTrigger>
        </TabsList>

        {/* Core */}
        <TabsContent value="core" className="space-y-4">
          <Section title="患者信息 Patient">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Row label="昵称 Name">
                <Input placeholder="如：球球 / Name" {...register("patient.name")} />
                {errors.patient?.name && <p className="text-xs text-red-600 mt-1">{errors.patient.name.message}</p>}
              </Row>
              <Row label="种属 Species">
                <Controller control={control} name="patient.species" render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger><SelectValue placeholder="选择种属 / Species" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="canine">犬 Canine</SelectItem>
                      <SelectItem value="feline">猫 Feline</SelectItem>
                      <SelectItem value="other">其他 Other</SelectItem>
                    </SelectContent>
                  </Select>
                )}/>
              </Row>
              <Row label="品种 Breed"><Input {...register("patient.breed")} /></Row>
              <Row label="性别 Sex">
                <Controller control={control} name="patient.sex" render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger><SelectValue placeholder="性别" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="M">公 M</SelectItem>
                      <SelectItem value="MN">公绝育 MN</SelectItem>
                      <SelectItem value="F">母 F</SelectItem>
                      <SelectItem value="FN">母绝育 FN</SelectItem>
                      <SelectItem value="Unknown">未知 Unknown</SelectItem>
                    </SelectContent>
                  </Select>
                )}/>
              </Row>
              <Row label="年龄 Age">
                <div className="flex gap-2">
                  <Input type="number" step="1" min={0} placeholder="年 Years" className="w-28" {...register("patient.ageYears", { valueAsNumber: true })} />
                  <Input type="number" step="1" min={0} max={12} placeholder="月 Months" className="w-28" {...register("patient.ageMonths", { valueAsNumber: true })} />
                </div>
              </Row>
              <Row label="体重 Weight (kg)"><Input type="number" step="0.1" min={0} {...register("patient.weightKg", { valueAsNumber: true })} /></Row>
              <Row label="芯片 Microchip"><Input {...register("patient.microchip")} /></Row>
            </div>
          </Section>

          <Section title="主人信息 Owner">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Row label="姓名 Name"><Input {...register("owner.name")} /></Row>
              <Row label="电话 Phone"><Input {...register("owner.phone")} /></Row>
              <Row label="邮箱 Email"><Input type="email" {...register("owner.email")} />
                {errors.owner?.email && <p className="text-xs text-red-600 mt-1">{errors.owner.email.message}</p>}
              </Row>
            </div>
          </Section>

          <Section title="就诊信息 Visit">
            <Row label="主诉 Complaint"><Textarea rows={3} {...register("complaint")} /></Row>
            <Row label="现病史 History"><Textarea rows={4} {...register("history")} /></Row>
            <Row label="生命体征 Vitals">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Input type="number" step="0.1" placeholder="体温 ℃" {...register("vitals.tempC", { valueAsNumber: true })} />
                <Input type="number" placeholder="心率 HR" {...register("vitals.hr", { valueAsNumber: true })} />
                <Input type="number" placeholder="呼吸 RR" {...register("vitals.rr", { valueAsNumber: true })} />
                <Input type="number" placeholder="收缩压 SBP" {...register("vitals.sbp", { valueAsNumber: true })} />
              </div>
            </Row>
          </Section>
        </TabsContent>

        {/* SOAP */}
        <TabsContent value="soap" className="space-y-4">
          <Section title="客观检查 / Physical Exam (O)">
            <Textarea rows={5} placeholder="一般状态、皮毛、头颈、胸腔、腹腔、神经、肌骨等..." {...register("exam")} />
          </Section>

          <Section title="实验室 / Labs (O)">
            <Textarea rows={5} placeholder="CBC、生化、尿检、激素、CRP、SAA..." {...register("labs")} />
          </Section>

          <Section title="影像学 / Imaging (O)">
            <Textarea rows={4} placeholder="X-ray/US/CT/MRI 关键发现" {...register("imaging")} />
          </Section>

          <Section title="诊断 / Diagnoses (A)"
            right={<div className="flex gap-2 items-center">
              <Input value={diagInput} onChange={(e) => setDiagInput(e.target.value)} placeholder="输入并添加标签" className="w-48"/>
              <Button type="button" variant="secondary" onClick={addDiag}><Plus className="h-4 w-4 mr-1"/>添加</Button>
            </div>}
          >
            <div className="flex flex-wrap gap-2">
              {(diagnoses || []).map((d) => (
                <Badge key={d} variant="secondary" className="px-2 py-1 text-sm">
                  {d}
                  <button type="button" aria-label="remove" className="ml-2 text-muted-foreground hover:text-foreground" onClick={() => removeDiag(d)}>
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
              {!diagnoses?.length && <p className="text-sm text-muted-foreground">无诊断，先添加标签~</p>}
            </div>
          </Section>

          <Section title="评估 / Assessment (A)">
            <Textarea rows={5} placeholder="鉴别诊断、优先级、证据" {...register("assessment")} />
          </Section>

          <Section title="计划 / Plan (P)">
            <Textarea rows={5} placeholder="进一步检查、治疗计划、随访安排" {...register("plan")} />
          </Section>
        </TabsContent>

        {/* Treatment */}
        <TabsContent value="tx" className="space-y-4">
          <Section title="用药 Medications"
            right={<Button type="button" variant="secondary" onClick={() => medsFA.append({ drug: "", dose: "", freq: "", route: "", duration: "" })}><Plus className="h-4 w-4 mr-1"/>添加</Button>}
          >
            <div className="space-y-3">
              {medsFA.fields.length === 0 && <p className="text-sm text-muted-foreground">暂无用药</p>}
              {medsFA.fields.map((f, idx) => (
                <div key={f.id} className="grid grid-cols-12 gap-2 items-center">
                  <Input className="col-span-3" placeholder="药物 Drug" {...register(`medications.${idx}.drug` as const)} />
                  <Input className="col-span-2" placeholder="剂量 Dose" {...register(`medications.${idx}.dose` as const)} />
                  <Input className="col-span-2" placeholder="频次 Freq" {...register(`medications.${idx}.freq` as const)} />
                  <Input className="col-span-2" placeholder="途径 Route" {...register(`medications.${idx}.route` as const)} />
                  <Input className="col-span-2" placeholder="疗程 Duration" {...register(`medications.${idx}.duration` as const)} />
                  <Button type="button" variant="ghost" className="col-span-1" onClick={() => medsFA.remove(idx)}><X className="h-4 w-4"/></Button>
                </div>
              ))}
            </div>
          </Section>

          <Section title="处置 Procedures"
            right={<Button type="button" variant="secondary" onClick={() => procsFA.append({ name: "", date: "", notes: "" })}><Plus className="h-4 w-4 mr-1"/>添加</Button>}
          >
            <div className="space-y-3">
              {procsFA.fields.length === 0 && <p className="text-sm text-muted-foreground">暂无处置</p>}
              {procsFA.fields.map((f, idx) => (
                <div key={f.id} className="grid grid-cols-12 gap-2 items-center">
                  <Input className="col-span-4" placeholder="名称 Name" {...register(`procedures.${idx}.name` as const)} />
                  <Input className="col-span-3" type="date" placeholder="日期 Date" {...register(`procedures.${idx}.date` as const)} />
                  <Input className="col-span-4" placeholder="备注 Notes" {...register(`procedures.${idx}.notes` as const)} />
                  <Button type="button" variant="ghost" className="col-span-1" onClick={() => procsFA.remove(idx)}><X className="h-4 w-4"/></Button>
                </div>
              ))}
            </div>
          </Section>
        </TabsContent>

        {/* Attachments */}
        <TabsContent value="attachments" className="space-y-4">
          <Section title="附件 Files & Images" right={<small className="text-muted-foreground">支持图片/文档 / Images & docs</small>}>
            <div className="flex items-center gap-3">
              <input id="file" type="file" multiple className="hidden" onChange={async (e) => {
                const files = e.target.files;
                if (!files) return;
                setSaving(true);
                try {
                  const uploaded: any[] = [];
                  for (const file of Array.from(files)) {
                    const att = await uploadFile(file);
                    uploaded.push(att);
                  }
                  setValue("attachments", [ ...(watch("attachments") || []), ...uploaded ]);
                  await doSave();
                } catch (e: any) {
                  setError(e.message || String(e));
                } finally {
                  setSaving(false);
                  (e.target as HTMLInputElement).value = "";
                }
              }} />
              <Label htmlFor="file"><Button type="button" variant="secondary"><Upload className="h-4 w-4 mr-2"/>上传 Upload</Button></Label>
            </div>
            <Separator className="my-4"/>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(watch("attachments") || []).map((a, idx) => (
                <Card key={a.id} className="overflow-hidden">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm truncate" title={a.name}>{a.name}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {a.type?.startsWith("image/") ? (
                      <img src={a.url} alt={a.name} className="w-full h-40 object-cover rounded-lg"/>
                    ) : (
                      <div className="h-40 flex items-center justify-center text-sm text-muted-foreground">{a.type || "文件"}</div>
                    )}
                    <a href={a.url} target="_blank" rel="noreferrer" className="text-primary text-sm underline mt-2 inline-block">打开 / Open</a>
                  </CardContent>
                  <CardFooter className="justify-end">
                    <Button type="button" variant="ghost" onClick={() => {
                      const rest = (watch("attachments") || []).filter((_, i) => i !== idx);
                      setValue("attachments", rest);
                      debouncedSave();
                    }}><X className="h-4 w-4 mr-1"/>移除</Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          </Section>
        </TabsContent>

        {/* Meta */}
        <TabsContent value="meta" className="space-y-4">
          <Section title="病例设置">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Row label="状态 Status">
                <Controller control={control} name="status" render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger><SelectValue placeholder="选择状态" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="draft">草稿 Draft</SelectItem>
                      <SelectItem value="open">进行中 Open</SelectItem>
                      <SelectItem value="closed">已关闭 Closed</SelectItem>
                    </SelectContent>
                  </Select>
                )}/>
              </Row>
              <Row label="置顶 Pinned">
                <Controller control={control} name="pinned" render={({ field }) => (
                  <div className="flex items-center gap-2"><Switch checked={field.value} onCheckedChange={field.onChange} /><span className="text-sm text-muted-foreground">重要病例置顶</span></div>
                )}/>
              </Row>
              <Row label="随访日期 Follow-up">
                <Input type="date" {...register("followUpDate")} />
              </Row>
            </div>
          </Section>
        </TabsContent>
      </Tabs>

      <div className="h-8"/>
    </div>
  );
}

// -----------------------------
// Quick Router Wiring (Example)
// -----------------------------
// In your router config (e.g., src/main.tsx or src/App.tsx using react-router-dom):
// <Route path="/cases/new/edit" element={<CaseEditorPage/>} />
// <Route path="/cases/:id/edit" element={<CaseEditorPage/>} />
//
// Env:
// VITE_API_BASE=https://your-fastapi-backend
//
// Notes:
// - The page autosaves 1.5s after valid changes and supports Cmd/Ctrl+S manual save.
// - Adjust API paths if your backend uses a different prefix.
// - Replace shadcn/ui import paths if your project structure differs.
