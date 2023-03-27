import React, { FunctionComponent, useContext } from 'react';
import cx from 'classnames';

import ShineImage from 'components/shine_image';
import HuntInfoContext from 'components/context';
import { LinkIfStatic } from 'components/link';

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
  ne?: number; // Used for nesting in the puzzle list
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

export const PuzzleImageTitle: FunctionComponent<{
  puzzleData: PuzzleData;
}> = ({ puzzleData }) => (
  <h4
    className={cx('puzzle-image-title p-2 min-w-fit', {
      'font-bold': puzzleData.isMeta,
    })}
  >
    {puzzleData?.name}

    <style jsx>{`
      h4 {
        font-size: max(14px, min(18px, 2vw)) !important;
        line-height: max(14px, min(18px, 2vw)) !important;
        background: white;
        border-radius: 8px;
        margin: 0 auto;
        max-width: 360px;
        min-width: 100px;
      }

      :global(.darkmode) h4 {
        color: rgba(255, 255, 255, 0.8);
      }

      @media (max-width: 800px) {
        h4 {
          min-width: fit-content;
        }
      }
    `}</style>
  </h4>
);

export const PuzzleImageAnswer = ({ puzzleData }) => (
  <>
    <h5
      className={cx('answer rounded-md font-mono bg-white', {
        underline: !puzzleData.answer,
      })}
    >
      {puzzleData?.answer || <>&nbsp;</>}
    </h5>
    <style jsx>{`
      h5 {
        color: var(--primary);
        font-size: 14px;
        background: white;
        border-radius: 8px;
        margin: 0 auto;
        padding: 0 8px;
        width: fit-content;
        min-width: 100px;
      }
      h5:not(.overlay) {
        margin-top: 4px;
      }
      h5.overlay {
        border-radius: 8px;
        color: #fff !important;
        font-size: calc(max(12px, min(22px, 1.3vw)));
        padding: 0 20px;
        text-shadow: 2px 2px 8px #000;
      }
      @media (max-width: 800px) {
        h5 {
          min-width: 10ch;
        }
      }
    `}</style>
  </>
);

const PuzzleImage: FunctionComponent<{
  puzzleData: PuzzleData;
  showSolved?: boolean;
  position?: [number, number];
  textPosition?: [number | string, number | string];
  iconSrc?: string;
  imageWidth?: number;
  zIndex?: number;
  showAnswer?: boolean;
  showTitle?: boolean;
  textOverlay?: boolean;
  interactable?: boolean;
}> = ({
  puzzleData,
  showSolved = false,
  position = undefined,
  textPosition = undefined,
  iconSrc = undefined,
  imageWidth = 100,
  zIndex = undefined,
  showAnswer = true,
  showTitle = true,
  textOverlay = false,
  interactable = true,
}) => {
  const { userInfo, huntInfo } = useContext(HuntInfoContext);
  const loggedIn = !!userInfo?.teamInfo;
  const huntIsOver = huntInfo && new Date() > new Date(huntInfo.endTime);
  const posLeft = position?.[0];
  const posTop = position?.[1];

  const InnerImage = () => (
    <>
      <ShineImage
        src={iconSrc ?? getIcon(puzzleData, loggedIn, huntIsOver, showSolved)}
        interactable={interactable}
      >
        {puzzleData && (
          <div
            className={cx({
              'puzzle-image-label overlay abs-center': textOverlay,
            })}
            style={
              textPosition
                ? {
                    transform: `translate(${textPosition[0]}%, ${textPosition[1]}%`,
                  }
                : {}
            }
          >
            {showTitle && <PuzzleImageTitle puzzleData={puzzleData} />}
            {showAnswer && puzzleData?.answer != undefined && (
              <PuzzleImageAnswer puzzleData={puzzleData} />
            )}
          </div>
        )}
      </ShineImage>
    </>
  );

  return (
    <div
      className={cx('wrapper inline-block text-center rounded-lg p-4', {
        overlay: textOverlay,
      })}
      style={
        posLeft !== undefined
          ? {
              left: `${posLeft}%`,
              top: `${posTop}%`,
              width: `${imageWidth || 15}%`,
              zIndex: zIndex ?? 0,
            }
          : {}
      }
    >
      {interactable ? (
        <LinkIfStatic href={`/puzzles/${puzzleData.slug}`}>
          <InnerImage />
        </LinkIfStatic>
      ) : (
        <InnerImage />
      )}

      <style jsx>{`
        div {
          position: absolute;
          transform: translate(-50%, -0%);
        }

        .wrapper :global(a) {
          position: relative;
        }

        .wrapper :global(a:visited),
        .wrapper :global(a:active),
        .wrapper :global(a:hover),
        .wrapper :global(a:link) {
          text-decoration: none !important;
        }
      `}</style>
    </div>
  );
};

export default PuzzleImage;
