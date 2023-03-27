import React from 'react';
import * as PIXI from 'pixi.js-legacy';
import { PixiComponent, useApp } from '@inlet/react-pixi/legacy';
import { Viewport as PixiViewport } from 'pixi-viewport';

export interface ViewportProps {
  width: number;
  height: number;
  worldWidth?: number;
  worldHeight?: number;
  initialPos?: number;
  onMoved?: (left: number, top: number, type: string) => void;
  onDrag?: (start: boolean) => void;
  pause?: boolean;
  children?: React.ReactNode;
}

export interface PixiComponentViewportProps extends ViewportProps {
  app: PIXI.Application;
}

const PixiComponentViewport = PixiComponent('Viewport', {
  create: ({
    width,
    height,
    worldWidth,
    worldHeight,
    initialPos,
    onMoved,
    onDrag,
    app,
  }: PixiComponentViewportProps) => {
    const viewport = new PixiViewport({
      screenWidth: width,
      screenHeight: height,
      worldWidth: worldWidth ?? width,
      worldHeight: worldHeight ?? height,
      ticker: app.ticker,
      interaction: app.renderer.plugins.interaction,
    });
    if (initialPos) {
      viewport.left = Math.max(0, Math.min(initialPos, viewport.worldWidth));
    }
    viewport.drag().decelerate().clamp({ direction: 'all' }).mouseEdges({
      left: 20,
      right: 20,
      speed: 12,
    });
    if (onMoved) {
      viewport.on('moved', ({ viewport, type }) => {
        onMoved(viewport.left, viewport.top, type);
      });
    }
    if (onDrag) {
      viewport.on('drag-start', () => onDrag(true));
      viewport.on('drag-end', () => onDrag(false));
    }

    return viewport;
  },

  applyProps: (instance, oldProps, newProps) => {
    if (
      newProps.width !== oldProps.width ||
      newProps.height !== oldProps.height ||
      newProps.worldWidth !== oldProps.worldWidth ||
      newProps.worldHeight !== oldProps.worldHeight
    ) {
      instance.resize(
        newProps.width,
        newProps.height,
        newProps.worldWidth,
        newProps.worldHeight
      );
    }
    const pause = newProps.pause ?? false;
    if (pause !== oldProps.pause) {
      instance.pause = pause;
    }
  },
});

const Viewport = (props: ViewportProps) => {
  const app = useApp();
  return <PixiComponentViewport app={app} {...props} />;
};

export default Viewport;
