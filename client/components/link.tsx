import { FC, HTMLProps } from 'react';
import Link from 'next/link';

interface LinkProps {
  href: string;
  replace?: boolean;
}

const LinkIfStatic: FC<HTMLProps<HTMLAnchorElement> & LinkProps> = ({
  children,
  href,
  replace,
  ...props
}) => {
  if (process.env.isStatic || process.env.useWorker) {
    return (
      <Link href={href} replace={replace}>
        <a {...props}>{children}</a>
      </Link>
    );
  } else {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  }
};

export default LinkIfStatic;
