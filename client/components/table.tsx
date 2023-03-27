import React, { FC, useEffect, useRef } from 'react';
import cx from 'classnames';
import Script from 'next/script';

interface TableProps {
  isFull?: boolean;
  isFixed?: boolean;
  noBorder?: boolean;
  noOverflow?: boolean;
  isSortable?: boolean;
}

const Table: FC<TableProps & React.HTMLProps<HTMLTableElement>> = ({
  isFull,
  isFixed,
  noBorder,
  noOverflow,
  isSortable,
  className = undefined,
  ...props
}) => {
  const ref = useRef<HTMLTableElement>(null);
  useEffect(() => {
    if (!isSortable || typeof window === 'undefined') {
      return;
    }

    async function delayedSort() {
      // directly call the makeSortable function once it's all rendered.
      /* @ts-ignore */
      while (!window.sorttable) {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
      /* @ts-ignore */
      window.sorttable.makeSortable(ref.current);
    }
    delayedSort();
  }, [isSortable]);

  return (
    <>
      <Script src={process.env.basePath + '/sorttable.js'} />

      <div
        className={cx(className, {
          'overflow-x-auto': !noOverflow,
          'min-w-full': isFull,
          'max-w-full': !isFull,
        })}
      >
        <table
          ref={ref}
          className={cx(className, {
            bordered: !noBorder,
            'w-full table-fixed': isFixed,
            'm-auto': !isFull,
          })}
          {...props}
        />
      </div>

      <style global jsx>{`
        .darkmode table.bordered th,
        .darkmode table.bordered td {
          border-color: var(--white);
        }

        @media print {
          .darkmode table.bordered th,
          .darkmode table.bordered td {
            border-color: var(--black);
          }
        }
      `}</style>
    </>
  );
};

export const FullTable = (props) => <Table isFull {...props} />;

export default Table;
