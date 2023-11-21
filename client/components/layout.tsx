import React, { useContext, useEffect, useRef, useState } from 'react';
import { MenuIcon } from '@heroicons/react/outline';
import { useRouter } from 'utils/router';
import cx from 'classnames';
import dynamic from 'next/dynamic';

import HuntInfoContext from 'components/context';
import MuseumTheme from 'components/themes/museum';
import NavbarLink from 'components/navbar';
import VolumeSlider from 'components/volume_slider';
import ResetLocalDatabaseButton from 'components/reset_local_database_button';

interface Props {
  children?: React.ReactNode;
}

/**
 * The layout component, rendered on every page. Controls the rendering of the
 * navbar as well as global page styling (e.g. color schemes).
 */
const Layout: React.FC<Props> = ({ children }) => {
  const router = useRouter();
  const { huntInfo, userInfo, round } = useContext(HuntInfoContext);
  const [isNavbarCollapsed, setNavbarCollapsed] = useState<boolean>(true);
  const teamInfo = userInfo?.teamInfo;
  const [isScrolled, setScrolled] = useState<boolean>(false);

  const basePath = router.asPath.split('#')[0]; // grab the path before hash

  useEffect(() => {
    const onScroll = () => void setScrolled(window.scrollY > 0);
    document.addEventListener('scroll', onScroll);

    return function cleanup() {
      document.removeEventListener('scroll', onScroll);
    };
  }, []);

  const handleRouteChange = (url: string) => {
    setNavbarCollapsed(true);
  };

  useEffect(() => {
    router.events.on('hashChangeComplete', handleRouteChange);
    router.events.on('routeChangeComplete', handleRouteChange);
    return () => {
      router.events.off('hashChangeComplete', handleRouteChange);
      router.events.off('routeChangeComplete', handleRouteChange);
    };
  }, [router.events]);

  // Customize styles based on round.
  const themeStyle = <MuseumTheme roundSlug={round.slug} />;

  const prehunt = huntInfo.secondsToStartTime > 0;
  let loginUrl = '/login';
  if (!['/login', ''].includes(router.pathname.replace(/\/$/, ''))) {
    loginUrl += `?next=${encodeURIComponent(router.asPath)}`;
  }

  return (
    <>
      {/* gradient should not be clickable */}
      <div className="nav-container pointer-events-none fixed top-0">
        <nav
          className={cx('select-none print:hidden', {
            scrolled: isScrolled,
            collapsed: isNavbarCollapsed,
          })}
        >
          <button
            className="border-none md:hidden collapse-menu mt-2 print:hidden"
            aria-expanded={!isNavbarCollapsed}
            onClick={() => setNavbarCollapsed((collapsed) => !collapsed)}
          >
            <MenuIcon className="h-6 w-6" />
          </button>

          <div className="nav-list">
            <ul className="inline-flex">
              <NavbarLink href="/" linkText="Home" />
              {!(prehunt && !userInfo?.superuser) && teamInfo?.rounds && (
                <NavbarLink
                  linkText="Rounds"
                  dropdownItems={
                    teamInfo?.rounds?.map((act) =>
                      act.map((roundData) => ({
                        href: roundData.url,
                        linkText: roundData.name,
                      }))
                    ) ?? []
                  }
                />
              )}
              <NavbarLink
                linkText="Hunt"
                dropdownItems={[
                  ...(prehunt && !userInfo?.superuser
                    ? []
                    : [[{ href: '/puzzles', linkText: 'List of Puzzles' }]]),
                  [
                    { href: '/story', linkText: 'Story' },
                    { href: '/about', linkText: 'About' },
                    { href: '/events', linkText: 'Events' },
                    { href: '/sponsors', linkText: 'Sponsors' },
                    {
                      href: '/health_and_safety',
                      linkText: 'Health & Safety',
                    },
                    // FIXME: Enable as needed
                    /*{
                      href:
                        router.nextRouter.basePath + '/spoilr/progress/solves',
                      linkText: 'Hunt Stats',
                    },
                    { href: '/credits', linkText: 'Credits' },
                   */
                  ],
                ]}
              />
              {userInfo?.unlocks?.map((unlock) => (
                <NavbarLink
                  key={unlock.url}
                  href={unlock.url}
                  linkText={unlock.pageName}
                />
              ))}

              {!!teamInfo ? (
                <>
                  {!process.env.isArchive && (
                    <NavbarLink
                      linkText={teamInfo.name}
                      truncate
                      dropdownItems={[
                        [{ href: '/logout', linkText: 'Logout' }],
                      ]}
                    />
                  )}
                </>
              ) : (
                <NavbarLink href={loginUrl} linkText="Login" />
              )}

              {process.env.useWorker && <ResetLocalDatabaseButton />}

              <div className="grow" />
              <VolumeSlider />
            </ul>
          </div>
        </nav>
      </div>
      {children}

      <style jsx>{`
        .nav-container {
          left: 0;
          right: 0;
          z-index: 1000; /* Show above other content */
        }

        nav {
          background: var(--navbar);
          pointer-events: initial;
        }

        ul {
          margin: 0 16px;
          width: calc(100% - 32px);
        }

        :global(#__next) {
          min-height: calc(100vh - 16px);
        }

        /* Responsive navbar: show on small devices */
        @media (max-width: 800px) {
          .nav-container {
            position: fixed;
          }

          nav {
            background-color: transparent;
          }

          nav :global(.menu) {
            position: initial;
          }

          ul {
            position: absolute;
            padding-inline: 6px;
            background-color: var(--theme-translucent);
            border: 1px solid var(--on-primary);
            color: var(--link);
            flex-direction: column;
            width: min-content;
          }

          nav :global(li) {
            margin-left: 8px;
          }

          .nav-list {
            margin-top: 50px;
          }

          .collapsed .nav-list {
            display: none;
          }

          .collapse-menu {
            background-color: var(--navbar);
            color: var(--link);
            padding: 8px 16px !important;
            position: absolute;
            margin-left: 16px;
            top: 0;
            line-height: 0;
          }
        }
      `}</style>

      {themeStyle}
    </>
  );
};

export default Layout;
