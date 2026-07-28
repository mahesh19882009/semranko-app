function Card({
  children,
  className = '',
  padding = 'p-5',
  shadow = 'shadow-card',
  border = 'border border-slate-200',
  radius = 'rounded-3xl',
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
