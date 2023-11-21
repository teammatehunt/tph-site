import React, {
  FunctionComponent,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import dynamic from 'next/dynamic';

import AutoResizer from 'components/autoresizer';
import Custom404 from 'pages/404';
import HuntInfoContext from 'components/context';
import PostHuntSettings from 'components/post_hunt_settings';
import PuzzleImage, { PuzzleData } from 'components/puzzle_image';
import { RoundData as PuzzleRoundData } from 'components/puzzle';
import Section from 'components/section';
import { serverFetch } from 'utils/fetch';

const DragDropPiece = dynamic(() => import('components/drag_drop_ui'), {
  ssr: false,
});

export const updateArray = (index, setState) => (newVal) => {
  setState((vals) => vals.map((item, i) => (i !== index ? item : newVal)));
};

const DEFAULT_WIDTH = 1000;
const DEFAULT_HEIGHT = 640;

export interface RoundData extends PuzzleRoundData {
  wordmark: string;
  roundart?: string; // background behind puzzle icons
  footer?: string;
  foreground?: string;
  position?: { x: number; y: number; width?: number };
  textOverlay?: boolean;
}

export interface RoundProps {
  // Map from round name to list of puzzles.
  puzzles: Record<string, PuzzleData[]>;
  rounds: Record<string, RoundData>;
}

export interface Props {
  // Map from round name to list of puzzles.
  puzzles: Record<string, PuzzleData[]>;
  roundData: RoundData;
}

const Wordmark: FunctionComponent<{
  imageUrl: string;
  zIndex?: number;
}> = ({ imageUrl, zIndex = undefined }) => (
  <div className="wordmark absolute top-[12%] flex justify-center w-full pt-2">
    <img className="mark max-w-[40%]" src={imageUrl} />
  </div>
);

export const RoundHeader: FunctionComponent<{
  roundData: RoundData;
}> = ({ roundData }) => (
  <header key={roundData.slug} className="relative -mt-8">
    {roundData.header && (
      <img className="w-full -z-10" src={roundData.header} alt="" />
    )}
    {roundData.wordmark && <Wordmark imageUrl={roundData.wordmark} />}
  </header>
);

export const RoundFooter: FunctionComponent<{
  roundData: RoundData;
}> = ({ roundData }) => (
  <img
    className="absolute inset-x-0 bottom-0 w-full -z-10"
    src={roundData.footer}
  />
);

export const PuzzleImages: FunctionComponent<{
  puzzles: PuzzleData[];
  roundData: RoundData;
  showSolved?: boolean;
}> = ({ puzzles, roundData, showSolved }) => {
  const { huntInfo, userInfo } = useContext(HuntInfoContext);
  const showDragDrop = userInfo?.superuser && huntInfo.secondsToStartTime > 0;

  const positions = useMemo(
    () =>
      puzzles.map((puzzle) => {
        return puzzle.mainRoundPosition ?? puzzle.position ?? [0, 0];
      }),
    [puzzles]
  );
  const widths = useMemo(
    () => puzzles.map((puzzle) => puzzle.iconSize),
    [puzzles]
  );
  const [posStates, setPosStates] = useState(positions);
  const [widthStates, setWidthStates] = useState(widths);

  useEffect(() => {
    setPosStates(positions);
    setWidthStates(widths);
  }, [positions, widths]);

  return (
    <>
      <AutoResizer className="select-none">
        {(width, height, ref) => (
          <>
            {roundData.roundart && (
              <img
                key={roundData.slug}
                alt=""
                className="w-full"
                src={roundData.roundart}
              />
            )}
            {puzzles.map((puzzle, i) => (
              <PuzzleImage
                key={puzzle.slug}
                puzzleData={puzzle}
                showSolved={showSolved}
                imageWidth={widthStates[i]}
                position={posStates[i]}
                textPosition={puzzle.textPosition}
                textOverlay={roundData.textOverlay}
              />
            ))}
            {showDragDrop &&
              puzzles.map((puzzle, i) => (
                <DragDropPiece
                  key={puzzle.slug}
                  slug={puzzle.slug}
                  position={posStates[i]}
                  setPosition={updateArray(i, setPosStates)}
                  imageWidth={widthStates[i]}
                  setWidth={updateArray(i, setWidthStates)}
                  roundWidth={width}
                  roundHeight={height}
                  containerRef={ref}
                />
              ))}
          </>
        )}
      </AutoResizer>
      {roundData.footer && <RoundFooter roundData={roundData} />}
    </>
  );
};

const PuzzlesMap = ({ puzzles, roundData }: Props) => {
  const [showSolved, setShowSolved] = useState<boolean>(false);
  const allPuzzles = Object.values(puzzles ?? {}).flat();

  return (
    <>
      {allPuzzles.length ? (
        <>
          <RoundHeader roundData={roundData} />
          <Section className="puzzles-map pt-0 min-h-[50vh]">
            <PostHuntSettings
              showSolved={showSolved}
              setShowSolved={setShowSolved}
            />
            <PuzzleImages
              roundData={roundData}
              puzzles={allPuzzles}
              showSolved={showSolved}
            />
          </Section>
        </>
      ) : (
        <Custom404 />
      )}

      <style global jsx>{`
        /* Override the background style. */
        #__next {
          background-image: ${roundData.background
            ? `url(${roundData.background}) !important`
            : `inherit`};
        }
      `}</style>
    </>
  );
};

interface RoundServerResponse extends RoundProps {
  redirect?: string;
}

export default PuzzlesMap;
export const getPuzzlesMapProps =
  (slug?: string, redirect = false) =>
  async (context) => {
    const url = slug ? `/rounds/${slug}` : '/puzzles';
    const props = await serverFetch<RoundServerResponse>(context, url);

    if (props.redirect) {
      return {
        redirect: {
          destination: props.redirect,
          permanent: false,
        },
      };
    }

    const act = (slug && props.rounds?.[slug]?.act) || 1;
    const newProps = {
      ...props,
      roundSlug: slug,
    };
    if (act) {
      newProps[act] = act;
    }

    return { props: newProps };
  };
