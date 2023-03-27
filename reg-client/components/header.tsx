import React from 'react';
import { useRouter } from 'next/router';
import cx from 'classnames';
import Link from 'next/link';

import { useScrollPosition } from 'utils/useScrollPosition';
import imgLogoLight from 'assets/public/museum_logo_light.png';
import imgLogoDark from 'assets/public/museum_logo_dark.png';

interface LinkProps {
  href: string;
  text: string;
}
const HeaderLink: React.FC<LinkProps> = ({ href, text }) => {
  const router = useRouter();
  const isSelected = href === router.pathname;

  return (
    <Link href={href}>
      <a
        className={cx(
          'text-sm sm:text-base hover:underline',
          isSelected ? 'underline' : 'no-underline'
        )}
      >
        {text}
      </a>
    </Link>
  );
};

const Header = ({ isHomepage }: { isHomepage?: boolean }) => {
  const scrollPosition = useScrollPosition();
  const useTransparentStyle = isHomepage && scrollPosition < 100;
  const headerClassNamePrefix =
    'fixed top-0 h-24 w-full flex items-center z-[100] bg-white transition-colors duration-500';

  return (
    <>
      <header
        className={cx(headerClassNamePrefix, {
          'bg-white text-black drop-shadow-lg': !useTransparentStyle,
          'bg-transparent text-white': useTransparentStyle,
        })}
      >
        <nav className="flex justify-between w-full lg:w-[90vw] lg:mx-auto px-6 items-center">
          <div className="max-w-[120px] mr-4 transition-opacity">
            <Link href="/">
              <a>
                <img
                  className="w-24 sm:w-32"
                  src={useTransparentStyle ? imgLogoDark : imgLogoLight}
                  alt="Museum of Interesting Things"
                />
              </a>
            </Link>
          </div>
          <div>
            <div className="flex space-x-4 lg:space-x-8 text-right">
              <HeaderLink href="/faq" text="Plan your visit" />
              <HeaderLink href="/register" text="Reserve tickets" />
            </div>
          </div>
        </nav>
      </header>
      {/* Since the header is fixed, this allows subsequent elements to appear below the header instead of getting occluded by it */}
      {!isHomepage && <div className="w-full h-24"></div>}
    </>
  );
};

export default Header;
