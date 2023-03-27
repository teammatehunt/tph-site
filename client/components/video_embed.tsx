import { FC } from 'react';

import { HIDDEN_CLASS } from 'components/copy';

// Statically check that the given ratio is between 1-16.
type AspectRatioNum =
  | 1
  | 2
  | 3
  | 4
  | 5
  | 6
  | 7
  | 8
  | 9
  | 10
  | 11
  | 12
  | 13
  | 14
  | 15
  | 16;

interface Props {
  src: string;
  linkSrc?: string; // For linking in copy to clipboard
  aspectRatio?: [AspectRatioNum, AspectRatioNum]; // w, h
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
  aspectRatio = [16, 9],
}) => (
  <div
    className={`flex items-center justify-center aspect-w-${aspectRatio[0]} aspect-h-${aspectRatio[1]}`}
  >
    <span className={HIDDEN_CLASS}>{`=HYPERLINK("${
      linkSrc ?? src
    }", "Link to video")`}</span>

    <iframe
      allowFullScreen
      className="h-full w-full"
      src={src}
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    />
  </div>
);

export default VideoEmbed;
