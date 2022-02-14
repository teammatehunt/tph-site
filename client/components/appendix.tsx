import React, { FC } from 'react';

interface Props {
  title?: string;
  id?: string | number;
}

export const LinkToAppendix: FC<Omit<Props, 'title'>> = ({ children, id }) => (
  <a href={`#appendix-${id}`}>{children ?? <sup>{id}</sup>}</a>
);

export const LinkToAppendixText: FC<Props> = ({ title, id }) => (
  <a href={`#appendix-${id}`}>{title ?? id}</a>
);

const Appendix: FC<Props> = ({
  title = 'Appendix',
  id = undefined,
  children,
}) => (
  <>
    <h4 id={`appendix-${id}`}>{title}</h4>
    {children}
  </>
);

export default Appendix;
