import React, { FC } from 'react';
import css from 'styled-jsx/css';

import ReactModal, { ModalProps } from 'react-modal';

/**
 * A generic modal component that's centered with an X (close button).
 * Built on top of react-modal.
 */
const Modal: FC<ModalProps> = ({ onRequestClose, children, ...props }) => {
  const { className: modalClassName, styles: modalStyles } = css.resolve`
    .abs-center {
      max-height: 80vh;
    }
  `;

  return (
    <>
      <ReactModal
        className={`abs-center ${modalClassName}`}
        onRequestClose={onRequestClose}
        {...props}
      >
        <input
          type="button"
          className="x-button"
          onClick={onRequestClose}
          value="✖"
          aria-label="Close"
        />

        {children}
        <style jsx>{`
          input.x-button {
            background: rgba(0, 0, 0, 0.2);
            border: none;
            border-radius: 50%;
            color: var(--white);
            padding: 20px;
            position: absolute;
            top: 0;
            right: 0;
            z-index: 1; /* Always show higher than content */
          }

          input.x-button:hover {
            background-color: rgba(0, 0, 0, 0.4);
            cursor: pointer;
          }
        `}</style>
      </ReactModal>
      {modalStyles}
    </>
  );
};

export default Modal;
