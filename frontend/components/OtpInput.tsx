import React, { useRef } from 'react';

interface OtpInputProps {
  value: string;
  onChange: (value: string) => void;
  length?: number;
  disabled?: boolean;
}

const OtpInput: React.FC<OtpInputProps> = ({ value, onChange, length = 6, disabled = false }) => {
  const inputRefs = useRef<Array<HTMLInputElement | null>>([]);
  const digits = Array.from({ length }, (_, index) => value[index] || '');

  const focusInput = (index: number) => {
    inputRefs.current[index]?.focus();
    inputRefs.current[index]?.select();
  };

  const handleDigitChange = (index: number, rawValue: string) => {
    const cleaned = rawValue.replace(/\D/g, '');
    const nextDigits = [...digits];

    if (!cleaned) {
      nextDigits[index] = '';
      onChange(nextDigits.join(''));
      return;
    }

    if (cleaned.length > 1) {
      const chars = cleaned.slice(0, length - index).split('');
      chars.forEach((char, offset) => {
        nextDigits[index + offset] = char;
      });
      onChange(nextDigits.join(''));
      const focusIndex = Math.min(index + chars.length, length - 1);
      focusInput(focusIndex);
      return;
    }

    nextDigits[index] = cleaned;
    onChange(nextDigits.join(''));
    if (index < length - 1) {
      focusInput(index + 1);
    }
  };

  const handleKeyDown = (index: number, event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Backspace' && !digits[index] && index > 0) {
      const nextDigits = [...digits];
      nextDigits[index - 1] = '';
      onChange(nextDigits.join(''));
      focusInput(index - 1);
      event.preventDefault();
    }

    if (event.key === 'ArrowLeft' && index > 0) {
      focusInput(index - 1);
      event.preventDefault();
    }

    if (event.key === 'ArrowRight' && index < length - 1) {
      focusInput(index + 1);
      event.preventDefault();
    }
  };

  const handlePaste = (event: React.ClipboardEvent<HTMLDivElement>) => {
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
    if (!pasted) {
      return;
    }

    onChange(pasted);
    const focusIndex = Math.min(pasted.length, length - 1);
    focusInput(focusIndex);
    event.preventDefault();
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 sm:gap-3" onPaste={handlePaste}>
        {digits.map((digit, index) => (
          <input
            key={index}
            ref={(element) => {
              inputRefs.current[index] = element;
            }}
            type="text"
            inputMode="numeric"
            autoComplete={index === 0 ? 'one-time-code' : 'off'}
            maxLength={length}
            value={digit}
            disabled={disabled}
            onChange={(event) => handleDigitChange(index, event.target.value)}
            onKeyDown={(event) => handleKeyDown(index, event)}
            className="h-14 w-12 rounded-2xl border border-slate-200 bg-white text-center text-2xl font-black tracking-[0.2em] text-slate-950 shadow-sm outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-50 sm:h-16 sm:w-14"
          />
        ))}
      </div>
      <p className="text-sm text-slate-500">Paste is supported. Only numeric digits are accepted.</p>
    </div>
  );
};

export default OtpInput;
