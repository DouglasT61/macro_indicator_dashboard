import { useEffect } from 'react';

interface AboutAppModalProps {
  content: string;
  open: boolean;
  onClose: () => void;
}

export function AboutAppModal({ content, open, onClose }: AboutAppModalProps) {
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
    <div className="about-app-modal" onClick={onClose} role="presentation">
      <section
        aria-label="About this app"
        className="about-app-modal__panel"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="about-app-modal__header">
          <div>
            <p className="eyebrow">About This App</p>
            <h2>User Guide</h2>
          </div>
          <button className="button-secondary" onClick={onClose} type="button">
            Close
          </button>
        </div>
        <pre className="about-app-modal__content">{content}</pre>
      </section>
    </div>
  );
}
