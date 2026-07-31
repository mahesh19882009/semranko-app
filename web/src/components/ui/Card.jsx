/**
 * Card Component
 * 
 * A flexible card container with customizable padding, shadow, border, and radius.
 * 
 * @param {React.ReactNode} children - Card content
 * @param {string} padding - Padding classes: 'p-5' | 'p-6' | 'p-8' | 'p-0'
 * @param {string} shadow - Shadow classes: 'shadow-card' | 'shadow-sm' | 'shadow-md' | 'shadow-lg' | 'shadow-elevated' | 'shadow-none'
 * @param {string} border - Border classes: 'border border-slate-200' | 'border-0'
 * @param {string} radius - Border radius: 'rounded-3xl' | 'rounded-2xl' | 'rounded-xl' | 'rounded-lg'
 * @param {string} className - Additional CSS classes
 * @param {React.ElementType} as - HTML element to render
 */
function Card({
  children,
  className = '',
  padding = 'p-5',
  shadow = 'shadow-card',
  border = 'border border-slate-200',
  radius = 'rounded-xs',
  as: Component = 'div',
  ...props
}) {
  const classes = [
    'bg-white',
    radius,
    border,
    shadow,
    padding,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Component className={classes} {...props}>
      {children}
    </Component>
  );
}

/**
 * CardHeader Component
 * 
 * Header section of a card with optional bottom border.
 * 
 * @param {React.ReactNode} children - Header content
 * @param {string} border - Border classes: 'border-b border-slate-200' | 'border-0'
 * @param {string} padding - Padding classes
 * @param {string} className - Additional CSS classes
 * @param {React.ElementType} as - HTML element to render
 */
function CardHeader({
  children,
  className = '',
  border = 'border-b border-slate-200',
  padding = 'px-5 py-5',
  as: Component = 'div',
  ...props
}) {
  const classes = [
    border,
    padding,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Component className={classes} {...props}>
      {children}
    </Component>
  );
}

/**
 * CardBody Component
 * 
 * Main content section of a card.
 * 
 * @param {React.ReactNode} children - Body content
 * @param {string} padding - Padding classes
 * @param {string} className - Additional CSS classes
 * @param {React.ElementType} as - HTML element to render
 */
function CardBody({
  children,
  className = '',
  padding = 'p-5',
  as: Component = 'div',
  ...props
}) {
  const classes = [
    padding,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Component className={classes} {...props}>
      {children}
    </Component>
  );
}

/**
 * CardFooter Component
 * 
 * Footer section of a card with optional top border.
 * 
 * @param {React.ReactNode} children - Footer content
 * @param {string} border - Border classes: 'border-t border-slate-200' | 'border-0'
 * @param {string} padding - Padding classes
 * @param {string} className - Additional CSS classes
 * @param {React.ElementType} as - HTML element to render
 */
function CardFooter({
  children,
  className = '',
  border = 'border-t border-slate-200',
  padding = 'px-5 py-4',
  as: Component = 'div',
  ...props
}) {
  const classes = [
    border,
    padding,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Component className={classes} {...props}>
      {children}
    </Component>
  );
}

Card.Header = CardHeader;
Card.Body = CardBody;
Card.Footer = CardFooter;

export default Card;
