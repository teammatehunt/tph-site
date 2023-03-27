import React, { Fragment } from 'react';
import cx from 'classnames';

import { RoundData } from 'components/puzzles_map';
import { LinkIfStatic } from 'components/link';
import PuzzleImage, { PuzzleData } from 'components/puzzle_image';
import ShadowImage from 'components/shadow_image';

interface Props {
  bg?: string;
  ratio?: number;
  rounds: RoundData[];
}

interface RoundImageProps {
  url: string;
  name: string;
  position?: [number, number];
  iconSrc: string;
  imageWidth: number;
  zIndex?: number;
}

const RoundImage: React.FC<RoundImageProps> = ({
  url,
  name,
  position,
  iconSrc,
  imageWidth,
  zIndex = 0,
}) => {
  const posLeft = position?.[0] ?? 0;
  const posTop = position?.[1] ?? 0;
  return (
    <div
      className="absolute round-img z-1"
      style={{
        left: `${posLeft}%`,
        top: `${posTop}%`,
        width: `${imageWidth || 15}%`,
        zIndex,
      }}
    >
      <LinkIfStatic href={url}>
        <ShadowImage alt={name} src={iconSrc} />
      </LinkIfStatic>
    </div>
  );
};

const RoundMap: React.FC<Props> = ({ bg = '', ratio = 0.8, rounds }) => {
  return (
    <div className={cx('mx-auto', { 'bg-map': !!bg })}>
      {rounds.map((round) => (
        <Fragment key={round.slug}>
          {round.wordmark && (
            <RoundImage
              url={round.url}
              name={round.name}
              iconSrc={round.wordmark}
              position={
                round.position
                  ? [round.position.x, round.position.y]
                  : undefined
              }
              imageWidth={round.position?.width ?? 15}
            />
          )}
          {round.foreground && (
            <img className="fg" alt="" src={round.foreground} />
          )}
        </Fragment>
      ))}

      <style jsx>{`
        :global(body),
        :global(#__next) {
          background: #fff;
        }
        .bg-map {
          background: url(${bg}) 0 / cover;
          overflow: hidden;
          position: relative;
          height: ${100 / ratio}vw;
          width: calc(100vw - 16px);
          max-width: max(1200px, 90vh);
          max-height: max(${1200 / ratio}px, ${90 / ratio}vh);
        }
        .fg {
          position: relative;
          pointer-events: none;
        }
      `}</style>
    </div>
  );
};

export default RoundMap;
