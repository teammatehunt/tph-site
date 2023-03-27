import React, { useState } from 'react';
import Link from 'components/link';
import parse from 'html-react-parser';

import LazyLoadImage from 'components/lazy_load_image';

export interface Story {
  slug: string;
  text: string;
  imageUrl?: string;
  puzzleUrl?: string;
  url?: string;
  act?: number;
}

interface Props extends Story {
  scrollPosition?: number;
  visibleByDefault?: boolean;
  shallow?: boolean;
}

const StoryCard: React.FC<Props> = ({
  slug,
  text,
  imageUrl,
  puzzleUrl,
  url,
  visibleByDefault = true,
  shallow = false,
  ...props
}) => {
  const [interactionOpen, setInteractionOpen] = useState(false);

  const storycardImg = imageUrl ? (
    <LazyLoadImage
      className="w-full"
      alt=""
      src={imageUrl}
      visibleByDefault={visibleByDefault}
      {...props}
    />
  ) : null;

  return (
    <div className="story">
      <div className="story-anchor" id={slug} />
      {url ? (
        <>
          <Link href={url} shallow={shallow}>
            <a>{storycardImg}</a>
          </Link>
          <p className="px-8 py-5">{parse(text)}</p>
        </>
      ) : (
        <>
          {storycardImg}
          <p className="px-8 py-5">{parse(text)}</p>
        </>
      )}

      <style jsx>{`
        .story {
          position: relative;
          margin: 0 auto;
          width: 100%;
        }

        .story-anchor {
          position: absolute;
          top: calc(-48px - 5vh);
        }

        .story :global(img) {
          width: 100%;
        }

        .story :global(.placeholder) {
          background: var(--muted);
        }

        :global(.lazy-load-image-background) {
          width: 100%;
        }
      `}</style>
    </div>
  );
};

export default StoryCard;
