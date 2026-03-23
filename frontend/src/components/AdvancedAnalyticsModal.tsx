import { useEffect, type ReactNode } from 'react';

interface AdvancedAnalyticsModalProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}

export function AdvancedAnalyticsModal({ open, onClose, children }: AdvancedAnalyticsModalProps) {
  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    document.body.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="advanced-drawer" onClick={onClose} role="presentation">
      <aside
        aria-label="Advanced analytics"
        className="advanced-drawer__panel"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="advanced-drawer__header">
          <div>
            <p className="eyebrow">Advanced Analytics</p>
            <h2>Models, Calibration, and Historical Analogs</h2>
          </div>
          <button className="button-secondary" onClick={onClose} type="button">
            Close
          </button>
        </div>
        <div className="advanced-drawer__content">{children}</div>
      </aside>
    </div>
  );
}
