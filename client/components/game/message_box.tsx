import React, { FC, HTMLProps, useCallback, useEffect, useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/outline';
import cx from 'classnames';
import parse from 'html-react-parser';
import Typist from 'react-typist';

import Fader from 'components/fader';

export interface Sprite {
  name?: string;
  src?: string;
}

interface Option {
  slug: string;
  text: string;
}

interface Props {
  text: string;
  sprite?: Sprite;
  centered?: boolean;
  avgTypingDelay?: number;
  onTypingDone?: () => void;
  canFastForward?: boolean;
  canCollapse?: boolean;
  showNameRight?: boolean;
  wrapperClassName?: string;
}

/**
 * A component used to render textboxes as seen in visual novels and games.
 * Supports text, sprite (e.g. character art), and options for text speed and
 * fast forwarding.
 */
export const MessageBox: FC<Props & HTMLProps<HTMLDivElement>> = ({
  text,
  sprite,
  avgTypingDelay = 5,
  className = '',
  wrapperClassName = '',
  centered = false,
  canCollapse = false,
  canFastForward = true,
  showNameRight = false,
  onTypingDone,
  children,
  ...props
}) => {
  const [typingDone, setTypingDone] = useState<boolean>(false);
  const [fastForward, setFastForward] = useState<boolean>(false);
  const [isCollapsed, setCollapsed] = useState<boolean>(false);

  useEffect(() => {
    setFastForward(false);
    setTypingDone(false);
    setCollapsed(false);
  }, [text]);

  const onClick = useCallback(() => {
    if (typingDone) {
      onTypingDone?.();
      if (canCollapse) {
        setCollapsed((collapsed) => !collapsed);
      }
    } else if (canFastForward) {
      setFastForward(true);
      setTypingDone(true);
    }
  }, [canFastForward, typingDone, onTypingDone]);

  return (
    <>
      <div
        onClick={onClick}
        className={cx('overlay absolute inset-0 z-20', {
          hidden: canCollapse || !text,
        })}
      />
      <div className={wrapperClassName}>
        <Fader show={!!text && !isCollapsed} name="sprite-fade">
          {sprite?.src && (
            <img
              className={cx('abs-center sprite', className)}
              src={sprite.src}
              alt={sprite.name ?? ''}
            />
          )}
        </Fader>
        <div
          className={cx('abs-center wrapper', {
            'text-center': centered,
            collapsed: isCollapsed,
            hidden: !text,
          })}
        >
          <div
            className={cx('message-box bg-blur dark', className, {
              'pointer-events-auto cursor-pointer': !!onClick,
            })}
            onClick={onClick}
          >
            {sprite && sprite.name && (
              <h3
                className={cx('bg-blur dark', { 'float-right': showNameRight })}
              >
                {sprite.name}
              </h3>
            )}
            {canCollapse && (
              <h3 className="collapse-icon bg-blur dark">
                {isCollapsed ? <ChevronUpIcon /> : <ChevronDownIcon />}
              </h3>
            )}
            <div className={cx('text', className)}>
              {avgTypingDelay > 0 && !fastForward ? (
                <Typist
                  avgTypingDelay={avgTypingDelay}
                  delayGenerator={
                    avgTypingDelay < 1 ? () => avgTypingDelay : undefined
                  }
                  key={text}
                  cursor={{
                    show: false,
                  }}
                  onTypingDone={() => void setTypingDone(true)}
                  {...props}
                >
                  {centered && <Typist.Delay ms={2000} />}
                  {typeof text === 'string' ? parse(text) : text}
                </Typist>
              ) : (
                <React.Fragment key={text}>
                  {typeof text === 'string' ? parse(text) : text}
                  <Typist cursor={{ show: false }} {...props} />
                </React.Fragment>
              )}
            </div>
          </div>
        </div>
        {children}
      </div>

      <style jsx>{`
        .overlay {
          background-color: rgba(0, 0, 0, 0.2);
        }
        .wrapper {
          left: 50%;
          max-width: 900px;
          width: 90%;
          z-index: 10;
        }
        .wrapper:not(.text-center) {
          top: calc(100vh - 60px); /* 24px padding on bottom */
          z-index: 100;
        }
        .message-box {
          padding: 1.4vh 1vw;
          font-size: min(3vw, 20px);
          user-select: none;
          height: 88px;
          width: 100%;
        }
        .wrapper:not(.text-center) .message-box {
          border: 1px solid var(--primary);
          transition: transform 250ms ease-in-out;
        }
        .wrapper:not(.text-center).collapsed .message-box {
          transform: translateY(104px); /* 60px offset + half of height */
        }

        :global(.darkmode) .message-box,
        :global(.darkmode) h3 {
          border-color: var(--white);
        }

        h3 {
          border: 1px solid var(--primary);
          border-bottom: none;
          top: min(-1vw, -44px);
          left: 0px;
          font-size: min(2.5vw, 16px) !important;
          min-width: 40px;
          padding: 8px 12px;
          position: absolute;
          text-align: center;
        }

        h3.collapse-icon :global(svg) {
          width: 28px;
          height: 28px;
        }

        h3.right {
          left: calc(100% - 100px);
        }

        img {
          max-height: 80%;
        }

        .sprite {
          top: 50%;
          left: 50%;
          height: 50%;
        }
      `}</style>
    </>
  );
};

export interface Message {
  slug: string;
  text: string;
  options?: Option[];
  sprite?: Sprite;
}

interface ListProps extends Omit<Props, 'text' | 'sprite'> {
  messages: Message[];
  onClickOption: (slug: string) => void;
}

/**
 * This component renders a sequence of message boxes (e.g. a dialogue stream).
 * Passing in options (multiple choice buttons) will render with the last
 * dialogue box.
 */
const MessageBoxList: FC<ListProps & HTMLProps<HTMLDivElement>> = ({
  messages,
  onClickOption,
  onTypingDone,
  ...props
}) => {
  const [index, setIndex] = useState<number>(0);

  useEffect(() => {
    setIndex(0);
  }, [messages]);

  const onMessageDone = useCallback(() => {
    if (index < messages.length - 1) {
      setIndex(index + 1);
    } else {
      onTypingDone?.();
    }
  }, [messages, index, onTypingDone]);

  return (
    <>
      <div
        className={cx(
          'options abs-center flex flex-col items-center justify-center',
          {
            hasImage: messages[0]?.sprite?.src,
          }
        )}
      >
        {messages[index].options?.map((option, i) => (
          <button
            key={`option-${i}`}
            className="option"
            onClick={() => onClickOption(option.slug)}
          >
            {option.text}
          </button>
        ))}
      </div>

      <MessageBox
        onTypingDone={
          // Don't allow closing the window if there are choices.
          messages[index].options?.length ? undefined : onMessageDone
        }
        text={messages[index].text}
        sprite={messages[index].sprite}
        {...props}
      />

      <style jsx>{`
        .options {
          margin: 0 auto;
          pointer-events: auto;
          top: 40%;
          width: 80%;
          z-index: 100;
        }

        .option {
          color: var(--black);
          border: 2px solid darkred;
          font-size: min(3vw, 18px);
          padding: 4px 0;
          margin-bottom: 20px;
          min-width: 80%;
        }

        .options.hasImage {
          top: 65%;
        }
      `}</style>
    </>
  );
};

export default MessageBoxList;
