/**
 * This file is preserved as a simplified snapshot of how we created the Puzzle Factory
 * in MH 2023, but it's very likely overkill for most puzzlehunts.
 * Feel free to remove and uninstall the pixi.js and react-pixi dependencies.
 */
import React, {
  FC,
  HTMLProps,
  memo,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  Container,
  Stage,
  Sprite,
  Text,
  useTick,
} from '@inlet/react-pixi/legacy';
import { utils as PixiUtils, Ticker, TextStyle } from 'pixi.js-legacy';
import cx from 'classnames';
import dynamic from 'next/dynamic';

import ANIMATIONS from './animations';
import { MessageBoxContext } from 'components/context';
import useGPUTier, { WEBGL_SUPPORTED } from 'utils/gpu';
import useScreenSize from 'utils/useScreenSize';
import { useLocalStorage } from 'utils/storage';
import { useTexture } from './hooks';

PixiUtils.skipHello();

const Viewport = dynamic(() => import('components/game/viewport'), {
  ssr: false,
});

export interface GameObject {
  slug: string;
  type: string;
  parallax: number;
  imageUrl?: string;
  closeupUrl?: string;
  closeupText?: string;
  alt?: string;
  subtitle?: string;
  height?: number;
  ratio?: number;
  /* Position is defined in terms of percentages of world width / ratio, world height.
   * For example [100, 50] in a world with ratio 2 will take up half width, half height. */
  position: [number, number, number];
  anchor?: [number, number];
  textOffset?: [number, number];
  animation?: string;
  dimensions?: [number, number];
  clickable?: boolean;
  background?: string;
  onClick?: (
    slug: string,
    url?: string,
    text?: string,
    closeupUrl?: string
  ) => void;
  onHover?: (slug?: string) => void;
  cursor?: string;
  visible?: boolean;
  url?: string;
}

export interface GameLayer {
  objs: GameObject[];
  parallax: number;
  interactive: boolean;
}

interface SceneProps {
  name: string;
  layers: GameLayer[];
  initialPos: number;
  minX: number;
  maxX: number;
  onClick?: (scene: string, slug: string, url?: string) => void;
  paused?: boolean;
}

const PUZZLE_TEXT_STYLE = new TextStyle({
  fill: 'white',
  align: 'center',
  fontFamily: 'Cairo', // CSS vars don't seem to work so hard-code
  fontSize: 20,
  dropShadow: true,
  dropShadowAlpha: 0.2,
});

const ANSWER_TEXT_STYLE = new TextStyle({
  fill: 'white',
  align: 'center',
  fontFamily: 'DM Mono', // CSS vars don't seem to work so hard-code
  fontSize: 20,
  dropShadow: true,
  dropShadowAlpha: 0.2,
});

const ANCHOR_CENTER = { x: 0.5, y: 0 };

const getCursor = (cursor: string) => {
  switch (cursor) {
    case 'pointer':
      return 'pointer';
    case 'up':
      return 'n-resize';
    case 'down':
      return 's-resize';
    default:
      return 'auto';
  }
};
/**
 * A generic "canvas" used to render (clickable) objects, animations, and text.
 * Powered by react-pixi and PixiJS which uses WebGL or canvas under the hood.
 * Used to render data passed from the server in the schema of GameObjects.
 * Examples of projects made from this include Remember to Hydrate and Puzzle Factory
 */
const Scene: FC<SceneProps & Omit<HTMLProps<HTMLDivElement>, 'onClick'>> = ({
  name,
  layers,
  minX,
  maxX,
  initialPos,
  onClick,
  className = undefined,
  paused = false,
  ...props
}) => {
  const { setSprite: setMessageBoxSprite, setText: setMessageBoxText } =
    useContext(MessageBoxContext);
  const { width: screenWidth, height: screenHeight } = useScreenSize();
  const isViewportMoving = useRef<boolean>(false);
  const worldHeight = screenHeight;
  const worldWidth = worldHeight * ((maxX - minX) / 100);

  // disable rendering if window is inactive to spare the gpu
  const [isWindowHidden, setWindowHidden] = useState<boolean>(false);
  const toggleHide = () => {
    if (typeof window !== 'undefined') {
      setWindowHidden(document.hidden);
    }
  };
  useEffect(() => {
    if (typeof window !== 'undefined') {
      document.addEventListener('visibilitychange', toggleHide);
      return () => {
        document.removeEventListener('visibilitychange', toggleHide);
      };
    }
  }, []);

  // Used to compute parallax
  const initialLeft =
    ((initialPos - minX) / (maxX - minX)) * worldWidth - screenWidth / 2 ?? 0;
  const [stageX, setStageX] = useState(initialLeft);
  const [cursor, setCursor] = useState<string | undefined>();

  const [hoveredSlug, setHoveredSlug] = useState<string | undefined>();

  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (loaded) {
      return;
    }
    const timeoutId = window.setTimeout(() => void setLoaded(true), 1000);
    return () => window.clearTimeout(timeoutId);
  }, []);

  const onMoved = useCallback((newX: number, _: number, type: string) => {
    setStageX((lastX) => {
      if (type === 'mouse-edges') {
        setCursor(lastX < newX ? 'right' : 'left');
      } else {
        setCursor(undefined);
      }
      return newX;
    });
  }, []);
  const onDrag = useCallback((start: boolean) => {
    isViewportMoving.current = start;
  }, []);

  // Cache onClick to avoid multiple rerenders.
  const onClickGameObject = useCallback(
    (slug, url?: string, text?: string, closeupUrl?: string) => {
      if (isViewportMoving.current) {
        // Don't process click events if dragging viewport.
        return;
      }
      if (text) {
        setMessageBoxText(text);
        setMessageBoxSprite({ src: closeupUrl });
      } else {
        setMessageBoxText('');
        setMessageBoxSprite(undefined);
        onClick?.(name, slug, url);
      }
    },
    [name, onClick, setMessageBoxText]
  );
  const onHoverGameObject = useCallback(
    (slug) => void setHoveredSlug(slug),
    []
  );

  const gpuTier = useGPUTier();
  useEffect(() => {
    // Run once on initialization
    Ticker.shared.maxFPS = gpuTier < 2 ? 30 : 60;
  }, [gpuTier]);

  const { get: gpuEnabled } = useLocalStorage<boolean>('gpu', true);

  const pixiOptions = useMemo(
    () => ({
      sharedTicker: true, // share to synchronize animations
      // Use canvas fallback if webGL isn't supported, GPU cannot handle 30fps, or forced via settings
      forceCanvas: !WEBGL_SUPPORTED || gpuTier < 2 || !gpuEnabled(),
    }),
    [gpuTier]
  );
  if (WEBGL_SUPPORTED && gpuTier === -1) {
    return <>Loading...</>;
  }

  return (
    <Stage
      className={cx(className, cursor ? `cursor-${cursor}` : undefined)}
      width={screenWidth}
      height={screenHeight}
      options={pixiOptions}
      raf={!loaded || (!paused && !isWindowHidden)}
    >
      <Viewport
        width={screenWidth}
        height={screenHeight}
        worldWidth={worldWidth}
        worldHeight={worldHeight}
        onMoved={onMoved}
        onDrag={onDrag}
        pause={paused}
        initialPos={initialLeft}
      >
        {layers.map(({ objs, parallax, interactive }, i) => (
          <Container
            key={i}
            x={(1 - parallax) * stageX}
            interactiveChildren={interactive}
          >
            {objs.map((obj) => (
              <GameComponent
                key={obj.slug}
                worldWidth={worldWidth}
                worldHeight={worldHeight}
                worldMinX={minX}
                worldMaxX={maxX}
                onClick={onClickGameObject}
                onHover={onHoverGameObject}
                {...obj}
              />
            ))}
          </Container>
        ))}

        {/* Add layer of text above all other layers */}
        <Container interactiveChildren={false}>
          {layers.map(({ objs }) =>
            objs.map((obj) => (
              <GameText
                key={obj.slug}
                worldWidth={worldWidth}
                worldHeight={worldHeight}
                worldMinX={minX}
                worldMaxX={maxX}
                {...obj}
                visible={hoveredSlug === obj.slug}
              />
            ))
          )}
        </Container>
      </Viewport>
    </Stage>
  );
};

interface WorldDimensions {
  worldWidth: number;
  worldHeight: number;
  worldMinX: number;
  worldMaxX: number;
}

const GameComponent: FC<GameObject & WorldDimensions> = ({
  worldWidth,
  worldHeight,
  worldMinX,
  worldMaxX,
  slug,
  type,
  url,
  imageUrl,
  closeupUrl,
  closeupText,
  alt,
  position,
  animation,
  anchor,
  height = 100,
  clickable,
  onClick,
  onHover,
  cursor = 'pointer',
  ratio = 1,
}) => {
  const [isHover, setHover] = useState(false);
  const onClickSprite = useCallback(() => {
    onClick?.(slug, url, closeupText, closeupUrl);
  }, [slug, url, onClick, closeupUrl, closeupText, closeupUrl]);
  const onMouseOver = useCallback(() => {
    setHover(true);
    onHover?.(slug);
  }, [slug, onHover]);
  const onMouseOut = useCallback(() => {
    setHover(false);
    onHover?.(undefined);
  }, [slug, onHover]);

  const texture = useTexture(imageUrl);

  const [animationProps, setAnimationProps] = useState({
    x: 0,
    y: 0,
    z: 0,
    rotation: 0,
    scale: 1,
    alpha: 1,
  });

  const animationTimer = useRef<number>(0);

  useTick((delta) => {
    animationTimer.current += delta;
    const animateFn = animation ? ANIMATIONS[animation] : undefined;
    if (animateFn) {
      setAnimationProps((animationProps) => ({
        ...animationProps,
        ...animateFn(animationTimer.current, animationProps),
      }));
    }
  });

  if (!texture) {
    return null;
  }
  return (
    <Sprite
      rotation={animationProps.rotation}
      x={
        ((position[0] + animationProps.x - worldMinX) /
          (worldMaxX - worldMinX)) *
        worldWidth
      }
      y={(position[1] + animationProps.y) * (worldHeight / 100)}
      anchor={
        /* Backgrounds are anchored at the top-left, while objects are anchored top-middle. */
        ['puzzle', 'round'].includes(type) ? ANCHOR_CENTER : anchor
      }
      zIndex={position[2] + animationProps.z}
      alpha={animationProps.alpha}
      accessible={!!alt}
      accessibleHint={alt}
      interactive={clickable}
      width={(height / 100) * worldHeight * ratio * animationProps.scale}
      height={(height / 100) * worldHeight * animationProps.scale}
      texture={texture}
      mouseover={onMouseOver}
      mouseout={onMouseOut}
      pointerup={clickable ? onClickSprite : undefined}
      tint={isHover ? 0xeeeeee : 0xffffff}
      cursor={getCursor(cursor)}
    />
  );
};

const GameText: FC<GameObject & WorldDimensions> = ({
  worldWidth,
  worldHeight,
  worldMinX,
  worldMaxX,
  type,
  url,
  imageUrl,
  alt,
  subtitle,
  position,
  textOffset = [0, 0],
  height = 100,
  visible = true,
}) => (
  <>
    {(type === 'puzzle' || type === 'round') && (
      <Text
        text={alt}
        x={
          ((position[0] + textOffset[0] - worldMinX) /
            (worldMaxX - worldMinX)) *
          worldWidth
        }
        y={((position[1] + textOffset[1] + height) / 100) * worldHeight}
        anchor={{ x: 0.5, y: 0 }}
        visible={visible}
        style={PUZZLE_TEXT_STYLE}
      />
    )}
    {subtitle && (
      <Text
        text={subtitle}
        x={
          ((position[0] + textOffset[0] - worldMinX) /
            (worldMaxX - worldMinX)) *
          worldWidth
        }
        y={((position[1] + textOffset[1] + height) / 100) * worldHeight + 28}
        anchor={{ x: 0.5, y: 0 }}
        visible={visible}
        style={ANSWER_TEXT_STYLE}
      />
    )}
  </>
);

export default Scene;
