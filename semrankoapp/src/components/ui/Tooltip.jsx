'use client'
import Tippy from '@tippyjs/react';

/** Consistent wrapper around the already-installed tooltip implementation. */
function Tooltip({ content, children, placement = 'top', disabled = false }) {
  if (!content || disabled) return children;
  return (
    <Tippy content={content} placement={placement} appendTo="parent" interactive={false}>
      <span className="inline-flex">{children}</span>
    </Tippy>
  );
}

export default Tooltip;
