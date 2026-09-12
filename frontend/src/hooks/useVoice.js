import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useVoice Hook
 * Integrates Web Speech Recognition & Speech Synthesis.
 * Allows zero-latency push-to-talk, continuous listening, "Hey ARYA" wake-word detection, and speaking with interrupt controls.
 */
export function useVoice({ onTranscriptReady, onStateChange }) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isWakeWordActive, setIsWakeWordActive] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [audioLevel, setAudioLevel] = useState(0);

  const recognitionRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis || null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const micStreamRef = useRef(null);
  const animFrameRef = useRef(null);
  const wakeWordModeRef = useRef(false);
  const silenceTimerRef = useRef(null);

  const callbacksRef = useRef({ onTranscriptReady, onStateChange });
  useEffect(() => {
    callbacksRef.current = { onTranscriptReady, onStateChange };
  });

  // Setup Web Speech Recognition
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn('SpeechRecognition API not supported in this browser.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
      callbacksRef.current.onStateChange?.(wakeWordModeRef.current ? 'idle' : 'listening');
    };

    recognition.onresult = (event) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          final += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      const currentText = (final || interim).trim();
      setTranscript(currentText);

      // Auto-submit on silence detection (if not in wake word background mode)
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (currentText && !wakeWordModeRef.current) {
        silenceTimerRef.current = setTimeout(() => {
          if (recognitionRef.current) {
            try { recognitionRef.current.stop(); } catch (e) {}
          }
          setIsListening(false);
          stopAudioAnalysis();
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
          if (callbacksRef.current.onTranscriptReady) {
             callbacksRef.current.onTranscriptReady(currentText);
          }
          setTranscript('');
        }, 1200); // 1.2 seconds of silence triggers send
      }

      // Check for voice interrupt keywords while ARYA is speaking
      const lower = currentText.toLowerCase();
      if (['stop', 'stop talking', 'be quiet', 'enough', 'halt'].includes(lower)) {
        stopSpeaking();
        return;
      }

      // Check Wake Word "Hey ARYA" or "ARYA"
      if (wakeWordModeRef.current) {
        const aryaMatch = lower.match(/(?:hey\s+)?arya\b\s*(.*)/i);
        if (aryaMatch) {
          const commandAfterWake = aryaMatch[1].trim();
          if (commandAfterWake.length > 2 && callbacksRef.current.onTranscriptReady) {
            // One-breath command: "Hey ARYA turn off the lights"
            setIsListening(false);
            stopAudioAnalysis();
            if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
            callbacksRef.current.onTranscriptReady(commandAfterWake);
            setTranscript('');
            return;
          } else if (event.results[event.results.length-1].isFinal) {
            // Two-breath command: "Hey ARYA" ... pauses ... wait for chime
            // We transition out of wakeWordMode to normal listening mode!
            try {
              const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
              const osc = audioCtx.createOscillator();
              const gainNode = audioCtx.createGain();
              osc.type = 'sine';
              osc.frequency.setValueAtTime(880, audioCtx.currentTime); // High pitch chime
              osc.frequency.exponentialRampToValueAtTime(1200, audioCtx.currentTime + 0.1);
              gainNode.gain.setValueAtTime(0, audioCtx.currentTime);
              gainNode.gain.linearRampToValueAtTime(0.3, audioCtx.currentTime + 0.05);
              gainNode.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.2);
              osc.connect(gainNode);
              gainNode.connect(audioCtx.destination);
              osc.start();
              osc.stop(audioCtx.currentTime + 0.2);
            } catch(e) {}
            
            wakeWordModeRef.current = false; // Disable background mode temporarily
            setTranscript('');
            // The continuous listener is already running, so it will just catch the next words as normal!
            return;
          }
        }
      }

      
    };

    recognition.onerror = (err) => {
      console.warn('Speech recognition error:', err.error);
      setIsListening(false);
      callbacksRef.current.onStateChange?.('idle');
      stopAudioAnalysis();
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      // Auto restart if in wake-word mode
      if (wakeWordModeRef.current) {
        setTimeout(() => {
          try { recognition.start(); } catch (e) {}
        }, 1000);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      callbacksRef.current.onStateChange?.('idle');
      stopAudioAnalysis();
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      // Auto restart if continuous wake word mode is enabled
      if (wakeWordModeRef.current) {
        setTimeout(() => {
          try { recognition.start(); } catch (e) {}
        }, 500);
      }
    };

    recognitionRef.current = recognition;

    return () => {
      try {
        recognition.abort();
      } catch (e) {}
      stopAudioAnalysis();
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    };
  }, []);

  // Audio level analysis for 3D visualizer
  const startAudioAnalysis = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const updateLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length / 255;
        setAudioLevel(avg);
        animFrameRef.current = requestAnimationFrame(updateLevel);
      };

      updateLevel();
    } catch (err) {
      console.warn('Microphone stream access not granted for visualization:', err);
    }
  };

  const stopAudioAnalysis = () => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
  };

  const toggleWakeWord = useCallback(() => {
    wakeWordModeRef.current = !wakeWordModeRef.current;
    setIsWakeWordActive(wakeWordModeRef.current);
    if (wakeWordModeRef.current) {
      startListening();
    } else {
      stopListening();
    }
  }, []);



  const startListening = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      try {
        stopSpeaking(); // Interrupt active speech when user starts talking
        setTranscript('');
        recognitionRef.current.start();
        startAudioAnalysis();
      } catch (err) {
        console.warn('Failed to start speech recognition:', err);
      }
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (err) {
        console.warn('Failed to stop speech recognition:', err);
      }
      setIsListening(false);
      stopAudioAnalysis();
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      
      // Flush any pending transcript when manually stopped
      setTranscript((currentStr) => {
        const finalStr = currentStr.trim();
        if (finalStr && !wakeWordModeRef.current && callbacksRef.current.onTranscriptReady) {
          callbacksRef.current.onTranscriptReady(finalStr);
        }
        return '';
      });
    }
  }, []);

  // Text Sanitizer for Natural Speech (Strips Markdown & Symbols)
  const sanitizeTextForSpeech = (rawText) => {
    if (!rawText) return '';
    return rawText
      .replace(/```[\s\S]*?```/g, 'Code block omitted.') // Omit raw code blocks
      .replace(/`([^`]+)`/g, '$1')                      // Replace inline code backticks
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')           // Replace markdown links with link text
      .replace(/[*#_~>]/g, ' ')                          // Remove markdown symbols
      .replace(/https?:\/\/\S+/g, 'link')               // Replace URLs with "link"
      .replace(/\s+/g, ' ')                             // Normalize whitespace
      .trim();
  };

  const speak = useCallback(
    (text) => {
      if (!synthRef.current || !text) return;

      synthRef.current.cancel(); // Stop any active speech

      const cleanText = sanitizeTextForSpeech(text);
      if (!cleanText) return;

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1.0;
      utterance.pitch = 1.02;
      utterance.volume = 1.0;

      // High-Fidelity Neural / Assistant Voice Ranking Algorithm (MALE / JARVIS OVERRIDE)
      const getBestVoice = () => {
        const voices = synthRef.current.getVoices();
        if (!voices || voices.length === 0) return null;

        // Rank 1: British Male Neural / Jarvis Style
        const jarvisVoice = voices.find(
          (v) => v.lang.startsWith('en-GB') && (v.name.includes('George') || v.name.includes('Daniel') || v.name.includes('Arthur') || v.name.includes('Male'))
        );
        if (jarvisVoice) return jarvisVoice;

        // Rank 2: American Male Neural (Guy, Ryan, Mark, David)
        const maleNeural = voices.find(
          (v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Online')) && (v.name.includes('Guy') || v.name.includes('Ryan') || v.name.includes('Davis'))
        );
        if (maleNeural) return maleNeural;

        // Rank 3: Any Male Google/Apple Voice
        const genericMale = voices.find(
          (v) => v.lang.startsWith('en') && (v.name.includes('Male') || v.name.includes('David') || v.name.includes('Mark'))
        );
        if (genericMale) return genericMale;

        // Rank 4: Any Natural Voice Fallback
        const anyNatural = voices.find(
          (v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Online'))
        );
        if (anyNatural) return anyNatural;

        // Rank 5: Any English Voice
        return voices.find((v) => v.lang.startsWith('en')) || voices[0];
      };

      const selectedVoice = getBestVoice();
      if (selectedVoice) {
        utterance.voice = selectedVoice;
      }

      utterance.onstart = () => {
        setIsSpeaking(true);
        onStateChange?.('speaking');
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        onStateChange?.('idle');
      };

      utterance.onerror = () => {
        setIsSpeaking(false);
        onStateChange?.('idle');
      };

      synthRef.current.speak(utterance);
    },
    [onStateChange]
  );

  const stopSpeaking = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
      onStateChange?.('idle');
    }
  }, [onStateChange]);

  return {
    isListening,
    isSpeaking,
    isWakeWordActive,
    transcript,
    audioLevel,
    startListening,
    stopListening,
    toggleWakeWord,
    speak,
    stopSpeaking,
  };
}

