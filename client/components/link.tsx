import {
  cloneElement,
  FC,
  ForwardedRef,
  forwardRef,
  HTMLProps,
  ReactElement,
} from 'react';
import NextLink, { LinkProps as NextLinkProps } from 'next/link';
import { sanitizePath, useRouter } from 'utils/router';

export type LinkProps = NextLinkProps;

export const Link = forwardRef<
  HTMLAnchorElement,
  LinkProps & HTMLProps<HTMLAnchorElement>
>(
  (
    {
      href,
      replace,
      as,
      passHref,
      prefetch,
      scroll,
      shallow,
      locale,
      children,
      ...props
    },
    ref
  ) => {
    const router = useRouter();
    const sanitized = sanitizePath(router, href);
    const sanitizedAs = as ? sanitizePath(router, as) : as;
    let body;
    if (passHref) {
      body = cloneElement(children as ReactElement, { ref, ...props });
    } else {
      body = (
        <a ref={ref} {...props}>
          {children}
        </a>
      );
    }
    return (
      <NextLink
        href={sanitized}
        as={sanitizedAs}
        {...{
          replace,
          passHref,
          prefetch,
          scroll,
          shallow,
          locale,
        }}
      >
        {body}
      </NextLink>
    );
  }
);

export const LinkIfStatic = forwardRef<
  HTMLAnchorElement,
  LinkProps & HTMLProps<HTMLAnchorElement>
>(
  (
    {
      href,
      replace,
      as,
      passHref,
      prefetch,
      scroll,
      shallow,
      locale,
      children,
      ...props
    },
    ref
  ) => {
    if (
      process.env.isArchive ||
      process.env.isStatic ||
      process.env.useWorker
    ) {
      // conditional is build time constant, so conditional hook is okay
      const router = useRouter();
      const sanitized = sanitizePath(router, href);
      const sanitizedAs = as ? sanitizePath(router, as) : as;
      let body;
      if (passHref) {
        body = cloneElement(children as ReactElement, { ref, ...props });
      } else {
        body = (
          <a ref={ref} {...props}>
            {children}
          </a>
        );
      }
      // TODO: figure out types for passing the forwardRef into an embedded
      // <Link/> instead of code duplication
      return (
        <NextLink
          href={sanitized}
          as={sanitizedAs}
          {...{
            replace,
            passHref,
            prefetch,
            scroll,
            shallow,
            locale,
          }}
        >
          {body}
        </NextLink>
      );
    } else {
      return <a ref={ref} href={href} {...props} children={children} />;
    }
  }
);

export default Link;
