import React, { FC, HTMLProps, useCallback, useEffect, useState } from 'react';
import cx from 'classnames';
import parse from 'html-react-parser';
import Typist from 'react-typist';

import Fader from 'components/fader';

export interface Sprite {
  name: string;
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
  showNameRight?: boolean;
}

/**
 * A component used to render textboxes as seen in visual novels and games.
 * Supports text, sprite (e.g. character art), and options for text speed and
 * fast forwarding.
 */
const MessageBox: FC<Props & HTMLProps<HTMLDivElement>> = ({
  text,
  sprite,
  avgTypingDelay = 30,
  className = '',
  centered = false,
  canFastForward = true,
  showNameRight = false,
  onTypingDone,
  children,
  ...props
}) => {
  const [typingDone, setTypingDone] = useState<boolean>(false);
  const [fastForward, setFastForward] = useState<boolean>(false);

  useEffect(() => {
    setFastForward(false);
    setTypingDone(false);
  }, [text]);

  const onClick = useCallback(() => {
    if (typingDone) {
      onTypingDone?.();
    } else if (canFastForward) {
      setFastForward(true);
      setTypingDone(true);
    }
  }, [text, canFastForward, typingDone, onTypingDone]);

  return (
    <>
      <Fader name="sprite-fade">
        {sprite?.src && (
          <img
            className={cx('abs-center', 'sprite', className)}
            src={sprite.src}
            alt={sprite.name}
          />
        )}
      </Fader>
      <div
        className={cx('abs-center', 'container', className, {
          center: centered,
          clickable: !!onClick,
        })}
        onClick={onClick}
      >
        {sprite && sprite.name && (
          <h3 className={cx({ right: showNameRight })}>{sprite.name}</h3>
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
              {parse(text)}
            </Typist>
          ) : (
            <React.Fragment key={text}>
              {parse(text)}
              <Typist cursor={{ show: false }} {...props} />
            </React.Fragment>
          )}
        </div>
      </div>
      {children}
      <style jsx>{`
        .container {
          background: var(--white);
          color: var(--black);
          font-size: min(3vw, 20px);
          padding: 1.4vh 1vw;
          height: 20%;
          left: 50%;
          width: 90%;
          user-select: none;
          z-index: 100;
        }

        .container:not(.center) {
          border: 2px solid darkred;
          top: 85%;
        }

        .container.center {
          text-align: middle;
          z-index: 10;
        }

        .clickable {
          pointer-events: auto;
        }
        .clickable:hover {
          cursor: pointer;
        }

        h3 {
          background: white;
          border: none;
          color: #0b264a;
          top: -58px;
          left: 20px;
          font-size: min(3vw, 20px);
          min-width: 80px;
          padding: 6px 20px 2px;
          position: absolute;
          text-align: center;
        }

        h3.right {
          left: calc(100% - 100px);
        }

        img {
          max-height: 80%;
        }

        .sprite {
          top: 25%;
          z-index: 10;
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
        className={cx('options abs-center flex-center-vert', {
          hasImage: messages[0]?.sprite?.src,
        })}
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
          flex-direction: column;
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
