import React, { FC } from 'react';
import cx from 'classnames';
import css from 'styled-jsx/css';

import ReactModal, { ModalProps } from 'react-modal';

interface Props {
  darkMode?: boolean;
  blurBackground?: boolean;
  fullscreen?: boolean;
  XButton?: () => React.ReactNode;
}

/**
 * A generic modal component that's centered with an X (close button).
 * Built on top of react-modal.
 */
const Modal: FC<Props & ModalProps> = ({
  onRequestClose,
  darkMode = false,
  blurBackground = false,
  fullscreen = false,
  children,
  XButton,
  className,
  ...props
}) => {
  const { className: modalClassName, styles: modalStyles } = css.resolve`
    .fullscreen {
      max-height: 80vh;
    }

    :global(.ReactModal__Overlay) {
      background-color: ${blurBackground
        ? 'rgba(0,0,0,0.6)'
        : darkMode
        ? 'rgba(0,0,0,0.75)'
        : 'rgba(255,255,255,0.75)'} !important;
      backdrop-filter: ${blurBackground ? 'blur(8px)' : 'none'};
      z-index: 1000; /* Show over navbar */
    }
  `;

  return (
    <>
      <ReactModal
        className={cx('abs-center', modalClassName, className, {
          fullscreen,
          darkmode: darkMode,
        })}
        onRequestClose={onRequestClose}
        {...props}
      >
        <button
          onClick={onRequestClose}
          className={cx('x-button print:hidden', {
            default: !XButton,
          })}
          aria-label="Close"
        >
          {XButton ? <XButton /> : '✖'}
        </button>
        {children}
        <style jsx>{`
          .x-button {
            border: none;
            color: var(--white);
            position: absolute;
            top: 32px;
            right: 32px;
            width: 48px;
            height: 48px;
            z-index: 100; /* Always show higher than content */
          }

          .x-button.default {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 50%;
            top: 0;
            right: 0;
            padding: 12px 20px;
          }

          .x-button.default:hover {
            background-color: rgba(0, 0, 0, 0.4);
          }

          :global(.darkmode .x-button.default) {
            background: rgba(255, 255, 255, 0.2);
          }
          :global(.darkmode .x-button.default):hover {
            background-color: rgba(255, 255, 255, 0.4);
          }
        `}</style>
      </ReactModal>
      {modalStyles}
    </>
  );
};

export default Modal;
