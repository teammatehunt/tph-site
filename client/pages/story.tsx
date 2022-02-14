import React, { useCallback, useContext, useEffect, useMemo } from 'react';
import parse from 'html-react-parser';
import {
  LazyLoadImage,
  trackWindowScroll,
} from 'react-lazy-load-image-component';

import HuntInfoContext from 'components/context';
import Section from 'components/section';
import Title from 'components/title';
import StoryNotifications, {
  notifsKey,
  getUrl,
  addSeenNotifs,
  getCurrentStorycards,
} from 'components/story_notifications';
import { Story } from 'components/context';
import { useLocalStorage } from 'utils/storage';
import LinkIfStatic from 'components/link';

interface Props {
  story_cards: Story[];
}

const StoryPage = ({ scrollPosition }) => {
  const { huntInfo, userInfo } = useContext(HuntInfoContext);
  const notifs = useLocalStorage<string[]>(notifsKey, []);
  const hasFinished = userInfo?.teamInfo?.stage === 'finished';

  const currentStorycards = useMemo(
    () => getCurrentStorycards(huntInfo.storyUnlocks, false),
    [huntInfo.storyUnlocks]
  );

  // If they're looking at Story they don't need to see the notification anymore.
  // Only advance this for logged in users - after hunt close, logged out
  // users can be further ahead than new teams, which can cause problems.
  useEffect(() => {
    if (currentStorycards && !!userInfo?.teamInfo) {
      if (typeof window !== 'undefined') {
        addSeenNotifs(notifs, currentStorycards);
      }
    }
  }, [currentStorycards]);

  const scrollToBottom = useCallback(() => {
    document
      .querySelector(`#${currentStorycards[currentStorycards.length - 1].slug}`)
      ?.scrollIntoView({ behavior: 'smooth' });
  }, [currentStorycards]);

  return (
    <>
      <Title title="Story" subline="Drama! Intrigue! Funnel Cake!" />
      <StoryNotifications onlyFinished />

      <Section center>
        {currentStorycards.length >= 2 && (
          <button onClick={scrollToBottom}>Jump to Most Recent</button>
        )}

        {currentStorycards.map((story, i) => {
          const storycard = getUrl(story) ? (
            // Lazy load all but the first image.
            // TODO(ivan): Replace placeholder rectangle with image or css animation or svg src
            // https://css-tricks.com/preventing-content-reflow-from-lazy-loaded-images/
            <LazyLoadImage
              alt={story.text}
              src={getUrl(story)}
              visibleByDefault={
                i === 0 ||
                (typeof window !== 'undefined' &&
                  window.location.hash &&
                  story.slug === window.location.hash)
              }
              effect="blur"
              placeholder={<div className="placeholder" />}
              scrollPosition={scrollPosition}
            />
          ) : (
            <p>{parse(story.text)}</p>
          );
          let href: string | null = null;
          if (hasFinished && i === currentStorycards.length - 1) {
            href = '/victory';
          } else if (story.puzzleSlug) {
            href = `/puzzles/${story.puzzleSlug}`;
          }
          return (
            <div className="story" key={story.slug}>
              <div className="story-anchor" id={story.slug} />
              {href ? (
                <LinkIfStatic href={href}>
                  <a>{storycard}</a>
                </LinkIfStatic>
              ) : (
                <>{storycard}</>
              )}
            </div>
          );
        })}
        {hasFinished ? (
          <p>
            <i>
              <LinkIfStatic href="/victory">
                <a className="big">finis</a>
              </LinkIfStatic>
            </i>
          </p>
        ) : null}
      </Section>
      <style jsx>{`
        :global(section) {
          max-width: 800px;
        }

        .story {
          position: relative;
          margin: 0 auto;
          width: 100%;
        }

        .story-anchor {
          position: absolute;
          top: calc(-48px - 5vh);
        }

        p {
          padding: 20px 30px;
        }

        .story :global(img) {
          width: 100%;
        }

        a.big {
          font-size: 24px;
        }

        .story :global(.placeholder) {
          background: var(--muted);
          height: 250px;
          width: 100%;
        }

        :global(.lazy-load-image-background) {
          width: 100%;
        }

        :global(html) {
          scroll-behavior: smooth;
        }
      `}</style>
    </>
  );
};

export default trackWindowScroll(StoryPage);
