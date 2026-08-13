'use client'
import { useEffect, useRef } from 'react';

export default function TurnstileWidget({ action, onToken }) {
  const container = useRef(null);
  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

  useEffect(() => {
    if (!siteKey) {
      onToken?.(null);
      return undefined;
    }
    let widgetId;
    const render = () => {
      if (!container.current || !window.turnstile) return;
      widgetId = window.turnstile.render(container.current, {
        sitekey: siteKey,
        action,
        callback: (token) => onToken?.(token),
        'expired-callback': () => onToken?.(null),
        'error-callback': () => onToken?.(null),
      });
    };
    const existing = document.querySelector('script[data-rankcare-turnstile]');
    if (existing) {
      if (window.turnstile) render(); else existing.addEventListener('load', render, { once: true });
    } else {
      const script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.defer = true;
      script.dataset.rankcareTurnstile = 'true';
      script.addEventListener('load', render, { once: true });
      document.head.appendChild(script);
    }
    return () => {
      if (widgetId !== undefined && window.turnstile) window.turnstile.remove(widgetId);
    };
  }, [action, onToken, siteKey]);

  if (!siteKey) return null;
  return <div ref={container} aria-label="Security verification" />;
}
