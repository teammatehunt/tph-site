import React, {
  FunctionComponent,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import dynamic from 'next/dynamic';

import Custom404 from 'pages/404';
import Section from 'components/section';
import PuzzleImage, { PuzzleData } from 'components/puzzle_image';
import HuntInfoContext from 'components/context';
import { serverFetch } from 'utils/fetch';
//import map from 'assets/public/map.jpg';
import PostHuntSettings from 'components/post_hunt_settings';

const StoryNotifications = dynamic(
  () => import('components/story_notifications'),
  { ssr: false }
);

export interface Props {
  // Map from round name to list of puzzles.
  puzzles: Record<string, PuzzleData[]>;
}

const Logo: FunctionComponent<{
  position?: [number, number];
  width?: number | string;
  zIndex?: number;
}> = ({ position = undefined, width = undefined, zIndex = undefined }) => (
  <div
    style={
      position
        ? {
            left: position[0],
            top: position[1],
            width: width,
            zIndex: zIndex ?? 0,
          }
        : {}
    }
  >
    <img src="/logo.png" />
    <style jsx>{`
      div {
        display: inline-block;
        text-align: center;
        position: absolute;
        transform: translate(-50%, -50%);
      }

      img {
        width: ${width}px;
      }
    `}</style>
  </div>
);

export const PuzzleImages: FunctionComponent<{
  puzzles: PuzzleData[];
  showSolved?: boolean;
}> = ({ puzzles, showSolved }) => {
  const { userInfo } = useContext(HuntInfoContext);

  const w = 950;
  const h = 820;
  const [width, setWidth] = useState(w);
  const ref = useRef<HTMLDivElement>(null);
  const scale = width / w;

  useEffect(() => {
    const onResize = () => {
      if (ref.current) {
        setWidth(ref.current.offsetWidth);
      }
    };
    onResize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
    };
  }, []);

  // FIXME
  return (
    <>
      <div className="container" ref={ref}>
        {/* FIXME: the canvas will resize based on the dimensions fo the background image */}
        {/*<img className="bg" src={map} />*/}

        <div className="canvas">
          {puzzles.map((puzzle) => (
            <PuzzleImage
              key={puzzle.slug}
              puzzleData={puzzle}
              showSolved={showSolved}
              imageHeight={puzzle.iconSize}
              position={[puzzle.position[0] ?? 0, puzzle.position[1] ?? 0]}
              mainRoundPosition={puzzle.mainRoundPosition}
            />
          ))}
          <Logo position={[180, 111]} width={250} />
        </div>
      </div>

      <style jsx>{`
        .bg {
          user-select: none;
          width: ${w}px;
          max-width: 100%;
        }

        .container {
          position: relative;
          max-width: 100%;
          width: max-content;
          height: min-content;
          margin-left: auto;
          margin-right: auto;
        }

        .canvas {
          position: absolute;
          top: 0;
          left: 0;
          width: ${w}px;
          height: ${h}px;
          user-select: none;
          transform: scale(${scale});
          transform-origin: top left;
        }
      `}</style>
    </>
  );
};

const PuzzlesMap = ({ puzzles }: Props) => {
  const { userInfo, huntInfo } = useContext(HuntInfoContext);
  const toggle = huntInfo.toggle;
  const [showSolved, setShowSolved] = useState<boolean>(false);
  const allPuzzles = Object.values(puzzles ?? {}).flat();

  return (
    <div>
      <StoryNotifications />

      <Section className="nopadding">
        <PostHuntSettings
          showSolved={showSolved}
          setShowSolved={setShowSolved}
        />
        {allPuzzles.length ? (
          <PuzzleImages puzzles={allPuzzles} showSolved={showSolved} />
        ) : (
          <Custom404 />
        )}
      </Section>

      <style global jsx>{`
        section.nopadding {
          padding-top: 0;
        }
      `}</style>
    </div>
  );
};

export default PuzzlesMap;
export const getPuzzlesMapProps = async (context) => {
  let props: Props;
  if (process.env.isStatic) {
    try {
      props = require('assets/json_responses/puzzles.json');
    } catch {
      props = {} as Props;
    }
  } else {
    props = await serverFetch<Props>(context, '/puzzles');
  }
  return {
    props,
  };
};
