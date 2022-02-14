import React, { FunctionComponent, HTMLProps } from 'react';

interface Props {
  url: string;
}

/**
 * NOTE: currently webpack is broken and returns an invalid url server-side.
 * As a workaround, this component must be dynamically imported.
 * TODO: fix this in next.config.js instead of this hacky workaround.
 */
const PdfViewer: FunctionComponent<Props & HTMLProps<HTMLIFrameElement>> = ({
  url,
  ...props
}) => <iframe src={require(`assets/${url}`).default} {...props} />;

export default PdfViewer;
