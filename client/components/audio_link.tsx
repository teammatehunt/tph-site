import React, { FunctionComponent, HTMLProps } from 'react';
import { HIDDEN_CLASS } from 'components/copy';

interface Props {
  src: string;
  ref?: React.RefObject<HTMLAudioElement>;
  sourceRef?: React.RefObject<HTMLSourceElement>;
}

const AudioLink: FunctionComponent<Props & HTMLProps<HTMLAudioElement>> = ({
  src,
  ref = undefined,
  ...props
}) => (
  <>
    <audio ref={ref} controls {...props}>
      <source src={src} />
    </audio>
    <div className={HIDDEN_CLASS}>
      <a href={src}>[Audio link]</a>
    </div>
  </>
);

export default AudioLink;
