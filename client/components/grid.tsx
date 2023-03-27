// Used to create grids, such as crosswords. Can also be used as blanks to fill in.

import React, { CSSProperties } from 'react';
import cx from 'classnames';

import { HIDDEN_CLASS, NO_COPY_CLASS } from 'components/copy';
import { Colors } from 'components/crossword';

type Cell = number | string;

export const _ = '';

interface Props {
  data: Cell[][];
  lightBorder?: boolean;
  dashed?: boolean;
  shading?: (Colors | '')[][];
  noBorder?: boolean[][];
  className?: string;
}

const Grid: React.FunctionComponent<Props> = ({
  data,
  lightBorder = false,
  dashed = false,
  shading = null,
  noBorder = null,
  className,
}) => (
  <>
    <div className={cx(NO_COPY_CLASS, className, { dashed })}>
      <table cellSpacing={0} className={lightBorder ? 'light' : ''}>
        <tbody>
          {data.map((row, i) => (
            <tr key={`row-${i}`}>
              {row.map((cell, j) => {
                const styles: CSSProperties = {};
                if (shading?.[i][j]) {
                  styles.backgroundColor = shading[i][j];
                }
                if (noBorder?.[i][j]) {
                  styles.border = 'none';
                }
                return (
                  <td key={`cell-${i}-${j}`} style={styles}>
                    {cell}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    <div className={HIDDEN_CLASS}>
      <table>
        <tbody>
          {data.map((row, i) => (
            <tr key={`row-${i}`}>
              {row.map((cell, j) => {
                const styles: CSSProperties = {};
                if (shading?.[i][j]) {
                  styles.backgroundColor = shading[i][j];
                }
                /* The logic around noBorder here assumes 1-row wide clues where
                   noBorder is never true for two adjacent cells. This is done to
                   reuse code between the crossword and fillable-square use cases. */
                if (i === 0 && !noBorder?.[i][j])
                  styles.borderTop = '1px solid black';
                if (i === data.length - 1 && !noBorder?.[i][j])
                  styles.borderBottom = '1px solid black';
                if (j === 0 || noBorder?.[i][j])
                  styles.borderLeft = '1px solid black';
                if (j === row.length - 1 || noBorder?.[i][j])
                  styles.borderRight = '1px solid black';
                return (
                  <td key={`cell-${i}-${j}`} style={styles}>
                    {cell}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    <style jsx>{`
      .${NO_COPY_CLASS} table {
        border-collapse: collapse;
        text-align: center;
      }

      .${NO_COPY_CLASS} td {
        background-clip: padding-box;
        border: 1px solid black;
        height: 30px;
        width: 30px;
        position: relative;
      }

      .${NO_COPY_CLASS}.dashed td {
        border-style: dashed;
      }

      .${NO_COPY_CLASS} .light td {
        border-color: lightgray;
      }

      .${NO_COPY_CLASS} td.black {
        background: black;
      }
    `}</style>
  </>
);

export default Grid;
