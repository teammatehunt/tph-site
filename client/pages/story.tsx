import React, { useContext } from 'react';
import { trackWindowScroll } from 'react-lazy-load-image-component';
import { ArrowRightIcon } from '@heroicons/react/outline';

import HuntInfoContext from 'components/context';
import Section from 'components/section';
import StoryCard from 'components/storycard';
import { serverFetch } from 'utils/fetch';

export interface Story {
  slug: string;
  text: string;
  title?: string;
  imageUrl?: string;
  puzzleSlug?: string;
}

interface Props {
  story?: Story[];
  scrollPosition?: number;
}

const StoryPage: React.FC<Props> = ({ story = [], scrollPosition }) => {
  const { huntInfo } = useContext(HuntInfoContext);

  return (
    <>
      <Section title="Story">
        {/* Lazy load all but the first image. */}
        {story.map((story, i) => (
          <Section
            key={story.slug}
            heading={story.title ? `...${story.title}` : undefined}
          >
            <StoryCard
              {...story}
              scrollPosition={scrollPosition}
              visibleByDefault={
                i === 0 ||
                (typeof window !== 'undefined' &&
                  !!window.location.hash &&
                  story.slug === window.location.hash)
              }
            />
          </Section>
        ))}
      </Section>

      <style global jsx>{`
        section {
          max-width: 900px;
        }

        html {
          scroll-behavior: smooth;
        }
      `}</style>
    </>
  );
};

export default trackWindowScroll(StoryPage);

export const getServerSideProps = async (context) => {
  const props = await serverFetch(context, '/story');
  return { props };
};
