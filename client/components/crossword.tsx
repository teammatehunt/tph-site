import React from 'react';
import CSS from 'csstype';
import cx from 'classnames';

type Cell = number | string | '!' | '';

export const _ = '';
export const X: Cell = '!'; // black
export const Y: Cell = '~'; // cyan
export const Z: Cell = ' '; // lightgray
export enum Colors {
  C1 = 'red',
  C2 = 'orange',
  C3 = 'yellow',
  C4 = 'palegreen',
  C5 = 'cyan',
  C6 = 'plum',
  C7 = 'black',
  C8 = 'CornflowerBlue',
  C9 = 'lightgray',
  C10 = 'indianred',
  C11 = 'Plum',
}
export enum Borders {
  L = 'border-left',
  T = 'border-top',
  TL = 'border-topleft',
}

interface Props {
  data: Cell[][];
  fill?: (Cell | React.ReactNode)[][];
  shading?: (Colors | '')[][];
  borders?: (Borders | '')[][];
  appendCols?: Cell[]; // Additional columns to prepend to the end without borders.
  emptycells?: boolean;
  cellWidth?: number;
  cellHeight?: number;
  cellClass?: string;
  tableClass?: string;
  // If true and a cell contains a `/`, will split clue going across/down.
  rebus?: boolean;
  gridColor?: string;
  optimizeForPrint?: boolean;
}

const Crossword: React.FunctionComponent<Props> = ({
  data,
  fill = null,
  shading = null,
  borders = null, // Most likely used with barred=true
  appendCols = [],
  emptycells = false,
  cellWidth = 30,
  cellHeight = 30,
  cellClass = '',
  tableClass = '',
  rebus = false,
  gridColor = 'black',
  optimizeForPrint = true,
}) => (
  <>
    <table
      className={cx(tableClass, 'text-center', 'crossword', {
        barred: !!borders,
      })}
      cellSpacing={0}
    >
      <tbody>
        {data.map((row, i) => (
          <tr key={`row-${i}`}>
            {row.map((cell, j) => {
              const value = fill ? fill[i][j] : '';
              const classes: string[] = [];
              const styles: CSS.Properties = {};
              if (cell === X) {
                if (emptycells) {
                  classes.push('empty');
                } else {
                  classes.push('filled');
                }
              } else {
                const barred = !!borders;
                const solidBorder = `${barred ? 3 : 1}px solid ${gridColor}`;

                if (!barred) {
                  styles.border = solidBorder;
                } else {
                  // Manually specify borders based on edge or value.
                  styles.border = '1px solid lightgrey';

                  const borderValue = borders?.[i][j];
                  if (
                    borderValue === Borders.T ||
                    borderValue === Borders.TL ||
                    i === 0
                  ) {
                    styles.borderTop = solidBorder;
                  }
                  if (
                    borderValue === Borders.L ||
                    borderValue === Borders.TL ||
                    j === 0
                  ) {
                    styles.borderLeft = solidBorder;
                  }
                  if (i === data.length - 1) {
                    styles.borderBottom = solidBorder;
                  }
                  if (j === row.length - 1) {
                    styles.borderRight = solidBorder;
                  }
                }
              }
              if (typeof cell == 'string') {
                if (cell.includes(Z)) {
                  styles.backgroundColor = 'lightgray';
                }
                if (cell.includes(Y)) {
                  styles.backgroundColor = 'cyan';
                }
              }
              if (shading?.[i][j]) {
                styles.backgroundColor = shading[i][j];
              }
              const number =
                typeof cell === 'string'
                  ? parseInt(
                      cell.replace(new RegExp('[' + X + Y + Z + ']', 'g'), ''),
                      10
                    )
                  : cell;

              // Split by '/' for rebuses
              const isRebusCell =
                rebus && typeof value === 'string' && value.length > 1;
              const [across, down] = isRebusCell
                ? value.split('/')
                : [value, null];
              const isWide =
                isRebusCell && (across as string).length > (down?.length ?? 0);

              return (
                <td
                  key={`cell-${i}-${j}`}
                  className={cx(cellClass, classes.join(' '))}
                  style={styles}
                  data-skip-inline-borders
                >
                  {!Number.isNaN(number) && (
                    <div className="clue">{number}</div>
                  )}
                  <div
                    className={cx('value', {
                      rebus: isRebusCell,
                      wide: isWide,
                    })}
                  >
                    {across}
                  </div>
                  {down && <div className="value rebus">{down}</div>}
                </td>
              );
            })}
            {appendCols[i] && (
              <td className="append text-left">{appendCols[i]}</td>
            )}
          </tr>
        ))}
      </tbody>
    </table>

    <style jsx>{`
      table.crossword {
        border-collapse: collapse;
        margin-left: auto;
        margin-right: auto;
        border: 2px solid ${gridColor};
      }

      td:not(.filled) {
        background-color: #fff;
      }

      td.filled {
        background-color: ${gridColor};
        border: 1px solid ${gridColor};
      }

      td.append {
        padding-left: 40px;
      }

      td > .clue {
        position: absolute;
        width: min-content;
        height: 33%;
        text-align: left;
        color: black;
        top: 0;
        left: 0;
        transform: scale(0.67);
        transform-origin: top left;
      }
      td > .value {
        color: black;
        position: absolute;
        width: 100%;
        height: 67%;
        top: 33%;
        left: 0;
      }

      td > .rebus {
        font-size: 9px;
        line-height: 10px;
        left: 30%;
      }
      td > .rebus:first-child {
        top: 33%;
      }
      td > .rebus.wide {
        top: 50%;
        left: 0;
      }
      td > .rebus:last-child {
        top: 28%;
        transform: translateY(-50%);
        writing-mode: vertical-lr;
        font-size: 8px;
        text-orientation: upright;
        letter-spacing: -8px;
      }
      td > .rebus.wide + .rebus {
        left: 33%;
      }

      @media print {
        td {
          /* Ensure that filled cells are black even when printed */
          print-color-adjust: exact;
          -webkit-print-color-adjust: exact;
        }
      }
    `}</style>
    <style jsx>{`
      td {
        /* firefox is dumb af */
        background-clip: padding-box;
        height: ${cellHeight}px;
        width: ${cellWidth}px;
        position: relative;
      }

      @media print {
        td.filled {
          /* Use diagonal lines of black to save ink */
          background-image: ${optimizeForPrint
            ? `linear-gradient(135deg, ${gridColor} 10%, #fff 10%, #fff 50%, ${gridColor} 50%, ${gridColor} 60%, #fff 60%, #fff 100%)`
            : 'none'};
          background-size: 7.07px 7.07px;
        }
      }
    `}</style>
  </>
);

export default Crossword;
