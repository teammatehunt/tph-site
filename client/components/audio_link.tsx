import React, { FunctionComponent, HTMLProps } from 'react';

interface Props {
  url: string;
  ref?: React.RefObject<HTMLAudioElement>;
  sourceRef?: React.RefObject<HTMLSourceElement>;
}

/**
 * NOTE: currently webpack is broken and returns an invalid url server-side for music.
 * As a workaround, this component must be dynamically imported.
 * TODO: fix this in next.config.js instead of this hacky workaround.
 */
const AudioLink: FunctionComponent<Props & HTMLProps<HTMLAudioElement>> = ({
  url,
  ref = undefined,
  ...props
}) => (
  <audio ref={ref} {...props}>
    <source src={url ? require(`assets/${url}`).default : ''} />
  </audio>
);

export default AudioLink;
