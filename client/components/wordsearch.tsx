// Used to create wordsearch grids.

import React, { CSSProperties } from 'react';
import cx from 'classnames';

import { HIDDEN_CLASS, NO_COPY_CLASS } from 'components/copy';

type Cell = number | string;

export const _ = '';

interface Props {
  data: Cell[][];
  cellWidth?: number;
  cellHeight?: number;
  cellClass?: string;
  tableClass?: string;
}

const Wordsearch: React.FunctionComponent<Props> = ({
  data,
  cellWidth = 30,
  cellHeight = 30,
  cellClass = '',
  tableClass = '',
}) => (
  <table className={tableClass}>
    <tbody>
      {data.map((row, i) => (
        <tr key={i}>
          {row.map((value, j) => (
            <td className={cx('text-center font-mono', cellClass)} key={j}>
              {value}
            </td>
          ))}
        </tr>
      ))}
    </tbody>
    <style jsx>{`
      table {
        border: 1px solid var(--black);
      }
      td {
        height: ${cellHeight}px;
        width: ${cellWidth}px;
      }
    `}</style>
  </table>
);

export default Wordsearch;
