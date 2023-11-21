import React, { Fragment, useRef } from 'react';
import { Link, LinkProps } from 'components/link';
import { Menu, Transition } from '@headlessui/react';
import { ChevronDownIcon } from '@heroicons/react/solid';
import { useRouter } from 'utils/router';
import cx from 'classnames';

interface NavbarLinkProps extends Omit<LinkProps, 'href'> {
  href?: string; // optional
  linkText: string;
  truncate?: boolean;
  floatRight?: boolean;
}

interface Props extends NavbarLinkProps {
  // List of lists for grouping
  dropdownItems?: (NavbarLinkProps & { href: string })[][];
}

/** A link in the top navbar. */
const NavbarLink: React.FC<Props> = ({
  linkText,
  truncate,
  floatRight,
  href,
  as,
  dropdownItems = [],
}) => {
  const router = useRouter();
  const rstrip = (path: string | undefined) =>
    path ? path.replace(/\/$/, '') : path;
  const isSelected =
    rstrip(href) === rstrip(router.pathname) &&
    (!as || rstrip(as.toString()) === rstrip(router.asPath));

  const linkComponent =
    dropdownItems.length > 0 ? (
      <Menu as="div" className="py-2 relative">
        <Menu.Button className="navlink inline-flex items-center border-none font-bold">
          <span>{linkText}</span>
          <ChevronDownIcon className="w-5 h-5" aria-hidden="true" />
        </Menu.Button>
        {dropdownItems.length > 0 && (
          <Transition
            as={Fragment}
            enter="transition ease-out duration-150"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Menu.Items className="menu mt-2 left-0 origin-top-left p-4 space-y-2 flex flex-col">
              {dropdownItems.map((list, i) => (
                <Fragment key={i}>
                  {list.map((item, j) => (
                    <Menu.Item key={j}>
                      <Link
                        className="inner navlink"
                        href={item.href}
                        title={item.linkText}
                      >
                        {item.linkText}
                      </Link>
                    </Menu.Item>
                  ))}
                  {i < dropdownItems.length - 1 && <hr className="mx-2" />}
                </Fragment>
              ))}
            </Menu.Items>
          </Transition>
        )}
      </Menu>
    ) : (
      <span className="py-2 inline-flex items-center border-none font-bold">
        {linkText}
      </span>
    );

  return (
    <li className={cx('px-auto link', { truncate })}>
      {isSelected || !href ? (
        linkComponent
      ) : (
        <Link href={href} title={linkText}>
          {linkComponent}
        </Link>
      )}

      <style jsx>{`
        li {
          list-style: none;
          height: 100%;
          margin-left: ${floatRight ? 'auto' : '8px'};
          margin-right: 8px;
          overflow: visible;
        }

        :global(.navlink) {
          color: var(--link);
        }

        :global(.navlink):hover {
          text-decoration: underline;
          text-underline-offset: 4px;
        }

        a:global(.inner):not(:hover) {
          text-decoration: none !important;
        }

        .truncate,
        .inner {
          min-width: 120px;
        }

        :global(.menu) {
          position: absolute;
          background: var(--navbar);
          min-width: 200px;
        }

        :global(.menu hr) {
          border-color: var(--link);
        }

        @media (max-width: 800px) {
          :global(.menu) {
            background: none;
            position: initial;
          }

          li {
            margin-block: 6px;
            margin-left: 0;
            min-width: 50vw;
          }

          :global(.collapsed) li {
            display: ${isSelected ? 'list-item' : 'none'};
          }
        }
      `}</style>
    </li>
  );
};

export default NavbarLink;
