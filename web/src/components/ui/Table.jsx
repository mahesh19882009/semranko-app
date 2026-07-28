/**
 * Table Component
 * 
 * A flexible table component with sticky headers, hover states, and scrollable body.
 * Composed of sub-components for flexible composition.
 * 
 * @param {React.ReactNode} children - Table content
 * @param {string} className - Additional CSS classes
 */
function Table({ children, className = '', ...props }) {
  return (
    <div className={`overflow-x-auto ${className}`} {...props}>
      <table className="min-w-full text-left text-sm">{children}</table>
    </div>
  );
}

/**
 * TableHeader Component
 * 
 * Table header with optional sticky positioning.
 * 
 * @param {React.ReactNode} children - Header content
 * @param {boolean} sticky - Whether header should stick to top when scrolling
 * @param {string} className - Additional CSS classes
 */
function TableHeader({ children, className = '', sticky = true, ...props }) {
  const classes = [
    'bg-slate-50 text-xs uppercase tracking-wider text-slate-500',
    sticky ? 'sticky top-0 z-10' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <thead className={classes} {...props}>
      {children}
    </thead>
  );
}

/**
 * TableBody Component
 * 
 * Table body with optional scrollable content.
 * 
 * @param {React.ReactNode} children - Body content
 * @param {string} maxHeight - Maximum height for scrollable body (e.g., '320px')
 * @param {string} className - Additional CSS classes
 */
function TableBody({ children, className = '', maxHeight, ...props }) {
  const bodyClasses = [
    maxHeight ? `max-h-[${maxHeight}]` : '',
    maxHeight ? 'overflow-y-auto block' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  if (maxHeight) {
    return (
      <tbody className={bodyClasses} {...props}>
        {children}
      </tbody>
    );
  }

  return <tbody {...props}>{children}</tbody>;
}

/**
 * TableRow Component
 * 
 * Table row with optional hover effect.
 * 
 * @param {React.ReactNode} children - Row content
 * @param {boolean} hover - Whether row should have hover effect
 * @param {string} className - Additional CSS classes
 */
function TableRow({ children, className = '', hover = true, ...props }) {
  const classes = [
    'border-b border-slate-100',
    hover && 'hover:bg-slate-50 transition-colors',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <tr className={classes} {...props}>
      {children}
    </tr>
  );
}

/**
 * TableCell Component
 * 
 * Standard table cell.
 * 
 * @param {React.ReactNode} children - Cell content
 * @param {string} className - Additional CSS classes
 */
function TableCell({ children, className = '', ...props }) {
  return (
    <td className={`px-5 py-4 ${className}`} {...props}>
      {children}
    </td>
  );
}

/**
 * TableHeaderCell Component
 * 
 * Table header cell.
 * 
 * @param {React.ReactNode} children - Cell content
 * @param {string} className - Additional CSS classes
 */
function TableHeaderCell({ children, className = '', ...props }) {
  return (
    <th className={`px-5 py-4 font-medium ${className}`} {...props}>
      {children}
    </th>
  );
}

Table.Header = TableHeader;
Table.Body = TableBody;
Table.Row = TableRow;
Table.Cell = TableCell;
Table.HeaderCell = TableHeaderCell;

export default Table;
