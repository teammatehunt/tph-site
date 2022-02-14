import { FC } from 'react';

import AspectRatio from 'components/aspect_ratio';
import { HIDDEN_CLASS } from 'components/copy';

interface Props {
  src: string;
  linkSrc?: string; // For linking in copy to clipboard
  aspectRatio?: number;
}

/**
 * Generates an embedded iframe for videos. The src should be the embeddable url
 * from YouTube. You can also define a custom aspect ratio that will be
 * respected for the video.
 *
 * When rendered in a container that is included in Copy-to-Clipboard, it will
 * generate a hyperlink "Link to video".
 */
const VideoEmbed: FC<Props> = ({
  src,
  linkSrc = undefined,
  aspectRatio = undefined,
}) => (
  <AspectRatio className="flex-center-vert" ratio={aspectRatio}>
    <span className={HIDDEN_CLASS}>{`=HYPERLINK("${
      linkSrc ?? src
    }", "Link to video")`}</span>

    <iframe
      allowFullScreen
      src={src}
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    />

    <style jsx>{`
      iframe {
        height: 100%;
        width: 100%;
      }
    `}</style>
  </AspectRatio>
);

export default VideoEmbed;
