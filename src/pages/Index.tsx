import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getMockTriageResult, type PatientIntake } from "@/lib/mock-data";

const Index = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState<PatientIntake>({
    name: "",
    age: "",
    gender: "",
    chiefComplaint: "",
    symptoms: "",
  });
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState<string[]>([]);

  const update = (field: keyof PatientIntake, value: string) =>
    setForm((f) => ({ ...f, [field]: value }));

  const canSubmit = form.name && form.age && form.gender && form.chiefComplaint && form.symptoms;

  const handleSubmit = () => {
    if (!canSubmit) return;
    const result = getMockTriageResult(form);
    navigate("/dashboard", { state: { result } });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const newFiles = Array.from(e.dataTransfer.files).map((f) => f.name);
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).map((f) => f.name);
      setFiles((prev) => [...prev, ...newFiles]);
    }
  };

  return (
    <main className="container max-w-2xl py-8">
      <h1 className="mb-8 text-3xl font-bold">Patient Intake</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Patient Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Name & Age row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name" className="text-base">Full Name</Label>
              <Input id="name" placeholder="Patient name" className="h-12 text-base" value={form.name} onChange={(e) => update("name", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="age" className="text-base">Age</Label>
              <Input id="age" type="number" placeholder="Age" className="h-12 text-base" value={form.age} onChange={(e) => update("age", e.target.value)} />
            </div>
          </div>

          {/* Gender */}
          <div className="space-y-2">
            <Label className="text-base">Gender</Label>
            <Select value={form.gender} onValueChange={(v) => update("gender", v)}>
              <SelectTrigger className="h-12 text-base">
                <SelectValue placeholder="Select gender" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="male">Male</SelectItem>
                <SelectItem value="female">Female</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Chief Complaint */}
          <div className="space-y-2">
            <Label htmlFor="complaint" className="text-base">Chief Complaint</Label>
            <Input id="complaint" placeholder="e.g. Chest pain, difficulty breathing" className="h-12 text-base" value={form.chiefComplaint} onChange={(e) => update("chiefComplaint", e.target.value)} />
          </div>

          {/* Symptoms with Mic */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="symptoms" className="text-base">Symptoms</Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="icon" className="h-10 w-10" type="button">
                    <Mic className="h-5 w-5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Voice input — Coming soon</TooltipContent>
              </Tooltip>
            </div>
            <Textarea
              id="symptoms"
              placeholder="Describe all symptoms in detail..."
              className="min-h-[120px] text-base"
              value={form.symptoms}
              onChange={(e) => update("symptoms", e.target.value)}
            />
          </div>

          {/* File Upload */}
          <div className="space-y-2">
            <Label className="text-base">Attach Files (optional)</Label>
            <label
              className={`flex min-h-[100px] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 transition-colors ${
                dragOver ? "border-primary bg-accent" : "border-border hover:border-primary/50"
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <Upload className="h-8 w-8 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                Drag & drop patient history or protocol PDFs, or click to browse
              </span>
              <input type="file" className="hidden" multiple accept=".pdf,.doc,.docx" onChange={handleFileInput} />
            </label>
            {files.length > 0 && (
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                {files.map((f, i) => (
                  <li key={i}>📎 {f}</li>
                ))}
              </ul>
            )}
          </div>

          {/* Submit */}
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="h-14 w-full text-lg font-bold"
            size="lg"
          >
            Analyze Patient
          </Button>
        </CardContent>
      </Card>
    </main>
  );
};

export default Index;
