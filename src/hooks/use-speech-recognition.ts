import { useState, useCallback, useRef, useEffect } from "react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SpeechRecognitionAPI: any =
  typeof window !== "undefined"
    ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    : null;

interface UseSpeechRecognitionOptions {
  onResult: (transcript: string) => void;
  onInterimResult?: (transcript: string) => void;
  continuous?: boolean;
  lang?: string;
}

interface SpeechRecognitionResult {
  isListening: boolean;
  isSupported: boolean;
  interimTranscript: string;
  toggle: () => void;
  stop: () => void;
}

export function useSpeechRecognition({
  onResult,
  onInterimResult,
  continuous = true,
  lang = "en-US",
}: UseSpeechRecognitionOptions): SpeechRecognitionResult {
  const [isListening, setIsListening] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  const isSupported = !!SpeechRecognitionAPI;

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
    setInterimTranscript("");
  }, []);

  const toggle = useCallback(() => {
    if (!SpeechRecognitionAPI) {
      console.error('Speech Recognition API not supported');
      return;
    }

    if (isListening) {
      stop();
      return;
    }

    try {
      const recognition = new SpeechRecognitionAPI();
      recognition.continuous = continuous;
      recognition.interimResults = true;
      recognition.lang = lang;

      recognition.onstart = () => {
        console.log('Speech recognition started');
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        console.log('Speech recognition result:', event);
        let interimText = "";
        let finalText = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          console.log(`Result ${i}: ${transcript}, isFinal: ${event.results[i].isFinal}`);
          
          if (event.results[i].isFinal) {
            finalText += transcript;
          } else {
            interimText += transcript;
          }
        }

        if (interimText) {
          console.log('Interim text:', interimText);
          setInterimTranscript(interimText);
          if (onInterimResult) {
            onInterimResult(interimText);
          }
        }

        if (finalText.trim()) {
          console.log('Final text:', finalText);
          setInterimTranscript("");
          onResult(finalText.trim());
        }
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error, event);
        setIsListening(false);
        setInterimTranscript("");
      };

      recognition.onend = () => {
        console.log('Speech recognition ended');
        setIsListening(false);
        setInterimTranscript("");
      };

      recognitionRef.current = recognition;
      console.log('Starting speech recognition...');
      recognition.start();
    } catch (error) {
      console.error('Failed to start speech recognition:', error);
      setIsListening(false);
    }
  }, [isListening, continuous, lang, onResult, onInterimResult, stop]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  return { isListening, isSupported, interimTranscript, toggle, stop };
}
