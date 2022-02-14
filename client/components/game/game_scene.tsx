import React, { FC } from 'react';
import cx from 'classnames';

import AspectRatio from 'components/aspect_ratio';

export interface GameObject {
  slug: string;
  imageUrl: string;
  alt?: string;
  position: [number, number, number];
  animation?: string;
  dimensions?: [number, number];
  filter?: string;
  clickable?: boolean;
  background?: string;
}

export interface GameScene {
  name?: string;
  bgColor?: string;
  objs: GameObject[];
}

export const EMPTY_SCENE: GameScene = {
  objs: [],
};

interface SceneProps {
  scene: GameScene;
  onClick?: (scene: string, slug: string) => void;
  className?: string;
  ratio?: number;
}

/**
 * A generic "canvas" used to render (clickable) objects and text.
 * Used to render data passed from the server in the schema of GameObjects.
 * Examples of projects made from this include Remember to Hydrate, Mystery Manor.
 */
const Scene: FC<SceneProps> = ({
  scene,
  onClick,
  children,
  ratio = 75,
  className = undefined,
}) => {
  return (
    <AspectRatio
      ratio={ratio}
      className={className}
      style={{
        background: scene.bgColor,
      }}
    >
      {scene.objs.map(
        (
          {
            slug,
            imageUrl,
            alt,
            position,
            animation,
            dimensions,
            filter,
            clickable,
            background,
          },
          i
        ) => {
          const Component = imageUrl ? 'img' : 'div';
          return (
            <Component
              className={cx('obj', {
                clickable,
                [`animate-${animation}`]: !!animation,
              })}
              onClick={
                clickable && onClick
                  ? () => onClick(scene.name || '', slug)
                  : undefined
              }
              key={`${slug}-${i}`}
              src={imageUrl}
              alt={alt}
              style={{
                left: `${position[0]}%`,
                top: `${position[1]}%`,
                zIndex: position[2],
                width: dimensions ? `${dimensions[0]}%` : undefined,
                height: dimensions ? `${dimensions[1]}%` : undefined,
                background,
                filter,
              }}
            />
          );
        }
      )}

      {children}

      <style jsx>{`
        :global(.wrapper) {
          position: relative;
          margin: 0 auto;
          overflow: hidden;
        }

        .obj {
          position: absolute;
          height: 100%;
          width: 100%;
          /* Not selectable or draggable */
          user-drag: none;
          user-select: none;
        }

        .clickable:hover {
          cursor: pointer;
          filter: saturate(0.5);
        }
      `}</style>
    </AspectRatio>
  );
};

export default Scene;
