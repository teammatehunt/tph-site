import React, { FC, Fragment, HTMLProps, useState } from 'react';
import cx from 'classnames';

import { HIDDEN_CLASS, NO_COPY_CLASS, Monospace } from 'components/copy';

type Slot = number | string;

interface Props {
  data: Slot[];
  fill?: string;
  hlClassName?: string;
  tableClassName?: string;
  copyAsOneLine?: boolean;
}

const EnumBlanks: FC<Props> = ({
  data,
  fill = null,
  hlClassName = '',
  tableClassName = '',
  copyAsOneLine = false,
}) => {
  return (
    <>
      <table className={cx(tableClassName, { [NO_COPY_CLASS]: copyAsOneLine })}>
        <tbody>
          <tr>
            {data.map((v, j) => (
              <td
                key={j}
                style={{
                  paddingTop: '10px',
                  paddingBottom: '0',
                  paddingLeft: '0',
                  paddingRight: '0',
                  border: 'none',
                  textAlign: 'center',
                  width: '1.5ex',
                  minWidth: '1.5ex',
                }}
              >
                <Monospace>
                  {v == '_' || typeof v === 'number' ? (
                    fill && fill[j] ? (
                      <span className="underline">{fill[j]}</span>
                    ) : (
                      <span className="text-xl">_</span>
                    )
                  ) : v == '*' ? (
                    fill && fill[j] ? (
                      <span className={hlClassName}>
                        <span className="underline">{fill[j]}</span>
                      </span>
                    ) : (
                      <span>
                        <span
                          className={cx(NO_COPY_CLASS, hlClassName, 'text-xl')}
                        >
                          _
                        </span>
                        <span className={HIDDEN_CLASS}>*</span>
                      </span>
                    )
                  ) : (
                    v
                  )}
                </Monospace>
              </td>
            ))}
          </tr>
          <tr>
            {data.map((v, j) => (
              <td
                key={j}
                style={{
                  fontSize: '0.7rem',
                  paddingTop: '0',
                  paddingBottom: '0',
                  paddingLeft: '0',
                  paddingRight: '0',
                  border: 'none',
                  textAlign: 'center',
                  verticalAlign: 'top',
                  lineHeight: '0.3rem',
                }}
              >
                {typeof v === 'number' ? v : ''}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
      {copyAsOneLine ? (
        <div className={HIDDEN_CLASS}>
          {data.map((v, j) => (
            <Monospace>
              {fill && fill[j] ? fill[j] : v}
              <span>&nbsp;</span>
            </Monospace>
          ))}
        </div>
      ) : null}
    </>
  );
};

export default EnumBlanks;
