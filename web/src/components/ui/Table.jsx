function Table({ children, className = '', ...props }) {
  return (
    <div className={`overflow-x-auto ${className}`} {...props}>
      <table className="min-w-full text-left text-sm">{children}</table>
    </div>
  );
}

function TableHeader({ children, className = '', sticky = true, ...props }) {
  const classes = [
    'bg-slate-50 text-xs uppercase tracking-wider text-slate-500',
    sticky ? 'sticky top-0' : '',
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

function TableRow({ children, className = '', hover = true, ...props }) {
  const classes = [
    'border-b border-slate-100',
    hover && 'hover:bg-slate-50 transition',
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

function TableCell({ children, className = '', ...props }) {
  return (
    <td className={`px-5 py-4 ${className}`} {...props}>
      {children}
    </td>
  );
}

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
