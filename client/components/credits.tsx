import React, { FunctionComponent, ReactNode } from 'react';

interface Props {
  bgm?: ReactNode;
  sfx?: ReactNode;
}

const Credits: FunctionComponent<Props> = ({
  bgm = undefined,
  sfx = undefined,
  children,
}) => (
  <>
    <h4>Credits</h4>
    <ul>
      {bgm && (
        <li>
          <strong>Background Music</strong>: {bgm}
        </li>
      )}
      {sfx && (
        <li>
          <strong>Sound Effects</strong>: {sfx}
        </li>
      )}
      {children}
    </ul>
  </>
);

export default Credits;
