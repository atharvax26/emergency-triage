import { useState, useCallback, useRef, useEffect } from "react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SpeechRecognitionAPI: any =
  typeof window !== "undefined"
    ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    : null;

interface UseSpeechRecognitionOptions {
  onResult: (transcript: string) => void;
  continuous?: boolean;
  lang?: string;
}

interface SpeechRecognitionResult {
  isListening: boolean;
  isSupported: boolean;
  toggle: () => void;
  stop: () => void;
}

export function useSpeechRecognition({
  onResult,
  continuous = true,
  lang = "en-US",
}: UseSpeechRecognitionOptions): SpeechRecognitionResult {
  const [isListening, setIsListening] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  const isSupported = !!SpeechRecognitionAPI;

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const toggle = useCallback(() => {
    if (!SpeechRecognitionAPI) return;

    if (isListening) {
      stop();
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = continuous;
    recognition.interimResults = false;
    recognition.lang = lang;

    recognition.onresult = (event: any) => {
      const last = event.results[event.results.length - 1];
      if (last.isFinal) {
        onResult(last[0].transcript);
      }
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [SpeechRecognitionAPI, isListening, continuous, lang, onResult, stop]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  return { isListening, isSupported, toggle, stop };
}
