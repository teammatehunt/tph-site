import React, { FunctionComponent, useContext } from 'react';
import cx from 'classnames';

import ShineImage from 'components/shine_image';
import HuntInfoContext from 'components/context';
import LinkIfStatic from 'components/link';

export interface PuzzleData {
  name: string;
  slug: string;
  iconURLs: { [name: string]: string };
  isMeta: boolean;
  position: [number, number];
  mainRoundPosition?: [number, number];
  iconSize: number;
  textPosition: [number, number];
  round: string;
  url?: string;
  answer?: string; // Only present if team has solved the puzzle
}

const getIcon = (
  puzzleData: PuzzleData,
  loggedIn: boolean,
  huntIsOver: boolean,
  showSolved: boolean
) => {
  if (huntIsOver && !loggedIn) {
    if (puzzleData.iconURLs.solved && showSolved) {
      return puzzleData.iconURLs.solved;
    } else {
      return puzzleData.iconURLs.unsolved;
    }
  }
  // Otherwise, follow default behavior.
  // We expect that the solved key only exists in the data if puzzle is solved.
  if (puzzleData.iconURLs.solved) {
    return puzzleData.iconURLs.solved;
  } else {
    return puzzleData.iconURLs.unsolved;
  }
};

const getShineIcon = (
  puzzleData: PuzzleData,
  loggedIn: boolean,
  huntIsOver: boolean,
  showSolved: boolean
) => {
  if (huntIsOver && !loggedIn) {
    return showSolved
      ? puzzleData.iconURLs.solvedShine
      : puzzleData.iconURLs.unsolvedShine;
  } else {
    // We expect that the solved key only exists in the data if puzzle is solved.
    return puzzleData.iconURLs.solvedShine ?? puzzleData.iconURLs.unsolvedShine;
  }
};

const PuzzleImage: FunctionComponent<{
  puzzleData: PuzzleData;
  showSolved?: boolean;
  position?: [number, number];
  mainRoundPosition?: [number, number];
  textPosition?: [number | string, number | string];
  height?: number | string;
  iconSrc?: string;
  imageHeight?: number | string;
  zIndex?: number;
  showAnswer?: boolean;
  textOverlay?: boolean;
}> = ({
  puzzleData,
  showSolved = false,
  position = undefined,
  mainRoundPosition = undefined,
  textPosition = undefined,
  height = undefined,
  iconSrc = undefined,
  imageHeight = '100%',
  zIndex = undefined,
  showAnswer = true,
  textOverlay = false,
}) => {
  const { userInfo, huntInfo } = useContext(HuntInfoContext);
  const loggedIn = !!userInfo?.teamInfo;
  const huntIsOver = huntInfo && new Date() > new Date(huntInfo.endTime);
  const posLeft = mainRoundPosition ? mainRoundPosition[0] : position?.[0];
  const posTop = mainRoundPosition ? mainRoundPosition[1] : position?.[1];
  return (
    <div
      className={cx('container', { overlay: textOverlay })}
      style={
        posLeft
          ? {
              left: posLeft,
              top: posTop,
              height: height,
              zIndex: zIndex ?? 0,
            }
          : {}
      }
    >
      <LinkIfStatic href={`/puzzles/${puzzleData.slug}`}>
        {puzzleData.iconURLs.bgIcon &&
          (loggedIn || (huntIsOver && showSolved)) && (
            <img
              className="bg"
              style={{ left: -35 }}
              src={puzzleData.iconURLs.bgIcon}
              height={(imageHeight as number) * 0.65}
            />
          )}
        <ShineImage
          src={iconSrc ?? getIcon(puzzleData, loggedIn, huntIsOver, showSolved)}
          height={imageHeight}
        >
          {puzzleData && (
            <h4
              className={textOverlay ? 'overlay abs-center name' : 'name'}
              style={
                textPosition
                  ? {
                      left: textPosition[0],
                      top: textPosition[1],
                    }
                  : {}
              }
            >
              {puzzleData.name}
            </h4>
          )}
        </ShineImage>
      </LinkIfStatic>
      {showAnswer && puzzleData?.answer && (
        <h5 className={cx('monospace', { overlay: textOverlay })}>
          {puzzleData.answer}
        </h5>
      )}

      <style jsx>{`
        div {
          display: inline-block;
          text-align: center;
        }

        div {
          position: absolute;
          transform: translate(-50%, -0%);
        }

        .name {
          max-width: 250px;
        }

        h4 {
          font-family: var(--title-font);
          font-size: 20px;
          font-weight: normal;
          max-width: 250px;
          line-height: 1.2;
          letter-spacing: 0.1em;
          text-transform: lowercase;
        }

        :global(.darkmode) h4 {
          color: rgba(255, 255, 255, 0.8);
        }

        h5 {
          color: var(--secondary);
          font-size: 14px;
        }

        h4,
        h5 {
          margin: 0 auto;
        }

        h5:not(.overlay) {
          margin-top: 4px;
        }

        h4.overlay,
        h5.overlay {
          border-radius: 8px;
          color: #fff !important;
          font-size: calc(max(12px, min(22px, 1.3vw)));
          padding: 0 20px;
          text-shadow: 2px 2px 8px #000;
        }

        h5.overlay {
          color: #000 !important;
          font-size: 1vw;
          text-shadow: 2px 2px 8px #fff;
        }

        .container :global(a) {
          position: relative;
        }

        .container :global(a:visited),
        .container :global(a:active),
        .container :global(a:hover),
        .container :global(a:link) {
          text-decoration: none !important;
        }

        .bg {
          position: absolute;
          top: 0;
          left: 0;
          transform: translateX(-50%);
        }

        @media (max-width: 800px) {
          h4,
          h5 {
            min-width: 15ch;
          }
        }
      `}</style>
    </div>
  );
};

export default PuzzleImage;
