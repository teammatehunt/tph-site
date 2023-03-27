import React, { FC, HTMLProps, useCallback, useRef } from 'react';
import TextareaAutosize from 'react-textarea-autosize';

/**
 * Renders a multiline textarea for answer submissions.
 */
const MultilineTextarea: FC<HTMLProps<HTMLInputElement>> = ({
  className,
  children,
  name,
  id,
  disabled,
  type,
}) => {
  return (
    <TextareaAutosize
      className={className}
      name={name}
      id={id}
      disabled={disabled}
    >
      {children}
    </TextareaAutosize>
  );
};

export default MultilineTextarea;
