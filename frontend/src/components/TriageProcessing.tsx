import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

interface Stage {
  id: string;
  label: string;
  duration: number;
}

const stages: Stage[] = [
  { id: "intake", label: "Processing Intake", duration: 150 },
  { id: "analysis", label: "Analyzing Symptoms", duration: 200 },
  { id: "decision", label: "Generating Decision", duration: 150 },
];

interface TriageProcessingProps {
  onComplete: () => void;
}

export function TriageProcessing({ onComplete }: TriageProcessingProps) {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    if (currentStage >= stages.length) {
      onComplete();
      return;
    }

    const timer = setTimeout(() => {
      setCurrentStage((prev) => prev + 1);
    }, stages[currentStage].duration);

    return () => clearTimeout(timer);
  }, [currentStage, onComplete]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center space-y-6">
            {/* Spinner */}
            <div className="relative">
              <Loader2 className="h-16 w-16 animate-spin text-primary" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="h-12 w-12 rounded-full bg-primary/10"></div>
              </div>
            </div>

            {/* Current Stage */}
            <div className="text-center">
              <h2 className="text-xl font-bold">
                {currentStage < stages.length ? stages[currentStage].label : "Complete"}
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Please wait while we process the patient data...
              </p>
            </div>

            {/* Stage Indicators */}
            <div className="flex w-full items-center justify-center gap-2">
              {stages.map((stage, index) => (
                <div key={stage.id} className="flex items-center">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all ${
                      index < currentStage
                        ? "border-primary bg-primary text-primary-foreground"
                        : index === currentStage
                        ? "border-primary bg-primary/10 text-primary animate-pulse"
                        : "border-muted bg-muted/10 text-muted-foreground"
                    }`}
                  >
                    {index < currentStage ? (
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path d="M5 13l4 4L19 7"></path>
                      </svg>
                    ) : (
                      <span className="text-sm font-bold">{index + 1}</span>
                    )}
                  </div>
                  {index < stages.length - 1 && (
                    <div
                      className={`h-0.5 w-12 transition-all ${
                        index < currentStage ? "bg-primary" : "bg-muted"
                      }`}
                    ></div>
                  )}
                </div>
              ))}
            </div>

            {/* Stage Labels */}
            <div className="flex w-full justify-between text-xs text-muted-foreground">
              {stages.map((stage, index) => (
                <div
                  key={stage.id}
                  className={`flex-1 text-center ${
                    index === currentStage ? "font-bold text-primary" : ""
                  }`}
                >
                  {stage.label.split(" ")[0]}
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
