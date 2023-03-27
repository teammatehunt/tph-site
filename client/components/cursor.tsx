import React, { DragEvent, FC, HTMLProps, useMemo, useState } from 'react';
import { DragHandlers, HTMLMotionProps, motion } from 'framer-motion';

import cursor from 'assets/museum/cursor.png';

export type Position = { x: number; y: number };

interface AnimatedObjectProps {
  pos: Position;
  drag?: boolean;
  zIndex?: number;
  onDrag?: (e: DragEvent<HTMLDivElement>) => void;
  onDragStart?: (e: DragEvent<HTMLDivElement>) => void;
  onDragEnd?: (e: DragEvent<HTMLDivElement>) => void;
  dropShadowColor?: string;
}

// framer-motion's type system is broken. Redefine these types ourselves.
type MotionProps = Omit<
  HTMLMotionProps<'div'>,
  'onDrag' | 'onDragStart' | 'onDragEnd' | 'onAnimationStart'
>;

/** Spring-animated cursor. See https://liveblocks.io/blog/how-to-animate-multiplayer-cursors */
export const AnimatedObject: FC<AnimatedObjectProps & MotionProps> = ({
  pos,
  zIndex = 50,
  drag = false,
  onDrag,
  onDragStart,
  onDragEnd,
  dropShadowColor = 'transparent',
  animate = true,
  children,
  ...props
}) => {
  return (
    <motion.div
      style={{
        position: 'absolute',
        top: '0',
        left: '0',
        zIndex,
      }}
      initial={pos}
      animate={{
        ...pos,
        filter: `drop-shadow(0 0 0.25rem ${dropShadowColor})`,
      }}
      transition={
        animate
          ? { type: 'spring', damping: 30, mass: 0.8, stiffness: 350 }
          : { duration: 0 }
      }
      onDrag={onDrag as DragHandlers['onDrag']}
      onDragStart={onDragStart as DragHandlers['onDragStart']}
      onDragEnd={onDragEnd as DragHandlers['onDragEnd']}
      {...props}
    >
      {children}
    </motion.div>
  );
};

/** Returns a number from 0 - 360 for use as a random hue-rotation. */
const hashUuid = (uuid: string) => {
  return uuid.split('').reduce((a, b) => a + b.charCodeAt(0), 0) % 360;
};

export const Cursor: FC<Position & { uuid: string }> = ({ uuid, x, y }) => {
  const hueRotate = useMemo(() => hashUuid(uuid), [uuid]);
  return (
    <AnimatedObject pos={{ x, y }} zIndex={50}>
      <img alt="" src={cursor} />
      <style jsx>{`
        img {
          pointer-events: none;
          user-select: none;
          opacity: 0.5;
        }
      `}</style>
      <style jsx>{`
        img {
          filter: hue-rotate(${hueRotate}deg);
        }
      `}</style>
    </AnimatedObject>
  );
};
