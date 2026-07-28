/**
 * Typography Component
 * 
 * A comprehensive typography system with heading and text variants.
 * Provides consistent text styling throughout the application.
 */
const headingStyles = {
  h1: 'text-3xl font-bold text-slate-900 tracking-tight',
  h2: 'text-2xl font-bold text-slate-900 tracking-tight',
  h3: 'text-xl font-semibold text-slate-900',
  h4: 'text-lg font-semibold text-slate-900',
  h5: 'text-base font-semibold text-slate-900',
  h6: 'text-sm font-semibold text-slate-900 uppercase tracking-wider',
};

const textStyles = {
  body: 'text-sm text-slate-700',
  bodySmall: 'text-xs text-slate-600',
  muted: 'text-sm text-slate-500',
  mutedSmall: 'text-xs text-slate-400',
  link: 'text-sm font-medium text-brand-600 hover:text-brand-700',
  error: 'text-sm text-danger',
  success: 'text-sm text-success',
  warning: 'text-sm text-warning',
};

/**
 * Base Typography component
 * @param {React.ElementType} as - HTML element to render
 * @param {React.ReactNode} children - Text content
 * @param {string} className - Additional CSS classes
 */
function Typography({ as, children, className = '', ...props }) {
  const Component = as || 'p';
  const styles = as?.startsWith('h') ? headingStyles[as] : textStyles.body;

  return (
    <Component className={`${styles || ''} ${className}`} {...props}>
      {children}
    </Component>
  );
}

Typography.H1 = ({ children, className, ...props }) => (
  <h1 className={`${headingStyles.h1} ${className || ''}`} {...props}>{children}</h1>
);
Typography.H2 = ({ children, className, ...props }) => (
  <h2 className={`${headingStyles.h2} ${className || ''}`} {...props}>{children}</h2>
);
Typography.H3 = ({ children, className, ...props }) => (
  <h3 className={`${headingStyles.h3} ${className || ''}`} {...props}>{children}</h3>
);
Typography.H4 = ({ children, className, ...props }) => (
  <h4 className={`${headingStyles.h4} ${className || ''}`} {...props}>{children}</h4>
);
Typography.H5 = ({ children, className, ...props }) => (
  <h5 className={`${headingStyles.h5} ${className || ''}`} {...props}>{children}</h5>
);
Typography.H6 = ({ children, className, ...props }) => (
  <h6 className={`${headingStyles.h6} ${className || ''}`} {...props}>{children}</h6>
);
Typography.Body = ({ children, className, ...props }) => (
  <p className={`${textStyles.body} ${className || ''}`} {...props}>{children}</p>
);
Typography.BodySmall = ({ children, className, ...props }) => (
  <p className={`${textStyles.bodySmall} ${className || ''}`} {...props}>{children}</p>
);
Typography.Muted = ({ children, className, ...props }) => (
  <p className={`${textStyles.muted} ${className || ''}`} {...props}>{children}</p>
);
Typography.MutedSmall = ({ children, className, ...props }) => (
  <p className={`${textStyles.mutedSmall} ${className || ''}`} {...props}>{children}</p>
);
Typography.Link = ({ children, className, ...props }) => (
  <a className={`${textStyles.link} ${className || ''}`} {...props}>{children}</a>
);
Typography.Error = ({ children, className, ...props }) => (
  <p className={`${textStyles.error} ${className || ''}`} {...props}>{children}</p>
);
Typography.Success = ({ children, className, ...props }) => (
  <p className={`${textStyles.success} ${className || ''}`} {...props}>{children}</p>
);
Typography.Warning = ({ children, className, ...props }) => (
  <p className={`${textStyles.warning} ${className || ''}`} {...props}>{children}</p>
);

export default Typography;
