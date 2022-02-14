import React, { CSSProperties } from 'react';

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
}

interface Props {
  data: Cell[][];
  fill?: Cell[][];
  shading?: (Colors | '')[][];
  appendCols?: Cell[]; // Additional columns to prepend to the end without borders.
  emptycells?: boolean;
}

const Crossword: React.FunctionComponent<Props> = ({
  data,
  fill = null,
  shading = null,
  appendCols = [],
  emptycells = false,
}) => (
  <>
    <table cellSpacing={0}>
      <tbody>
        {data.map((row, i) => (
          <tr key={`row-${i}`}>
            {row.map((cell, j) => {
              const value = fill ? fill[i][j] : '';
              const classes: string[] = [];
              const styles: CSSProperties = {};
              if (cell === X) {
                if (emptycells) {
                  classes.push('empty');
                } else {
                  styles.backgroundColor = '#000';
                  styles.border = '1px solid black';
                }
              } else {
                styles.border = '1px solid black';
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
                  ? cell.replace(new RegExp('[' + X + Y + Z + ']', 'g'), '')
                  : cell;
              return (
                <td
                  key={`cell-${i}-${j}`}
                  className={classes.join(' ')}
                  style={styles}
                >
                  <div className="number" style={{ textAlign: 'left' }}>
                    {number}
                  </div>
                  <div className="value">{value}</div>
                </td>
              );
            })}
            {appendCols[i] && <td className="append">{appendCols[i]}</td>}
          </tr>
        ))}
      </tbody>
    </table>

    <style jsx>{`
      table {
        border-collapse: collapse;
        text-align: center;
      }

      td {
        /* firefox is dumb af */
        background-clip: padding-box;
        height: 30px;
        width: 30px;
        position: relative;
      }

      td.append {
        padding-left: 40px;
        text-align: left;
      }

      td > .number {
        position: absolute;
        width: min-content;
        height: 33%;
        text-align: left;
        /* font-size: x-small; */
        top: 0;
        left: 0;
        transform: scale(0.67);
        transform-origin: top left;
      }
      td > .value {
        position: absolute;
        width: 100%;
        height: 67%;
        top: 33%;
        left: 0;
      }
    `}</style>
  </>
);

export default Crossword;
