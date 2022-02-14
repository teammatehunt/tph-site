import React, {
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import Link, { LinkProps } from 'next/link';
import { useRouter } from 'next/router';
import { Menu } from 'react-feather';
import cx from 'classnames';

import HuntInfoContext from 'components/context';
import LoginForm from 'components/login';
import RegisterForm from 'components/register';

/** FIXME: Customize themes here and include them below. */
const DarkTheme = () => (
  <style global jsx>{`
    :root {
      --theme-translucent: rgba(0, 0, 0, 0.8);
    }

    body {
      background: linear-gradient(to bottom, var(--dark), transparent);
    }
    h1 {
      text-shadow: 4px 4px 0px rgba(222, 197, 125, 0.25);
    }
  `}</style>
);

const LightTheme = () => (
  <style global jsx>{`
    body {
      background-image: linear-gradient(
        0.25turn,
        var(--background-transparent),
        var(--background),
        var(--background-transparent)
      );
      background-size: 100%, 400px;
      background-repeat: no-repeat, repeat;
    }
  `}</style>
);

interface NavbarLinkProps extends LinkProps {
  linkText: string;
  truncate?: boolean;
  floatRight?: boolean;
  smallCaps?: boolean;
}

/** A link in the top navbar. */
const NavbarLink: FunctionComponent<NavbarLinkProps> = ({
  linkText,
  truncate,
  floatRight,
  smallCaps = true,
  ...props
}) => {
  const router = useRouter();
  const isSelected =
    props.href === router.pathname && (!props.as || props.as === router.asPath);

  return (
    <li
      className={cx({
        'small-caps': smallCaps,
        selected: isSelected,
        truncate,
      })}
    >
      {isSelected || !props.href ? (
        <div className="link">
          <strong>{linkText}</strong>
        </div>
      ) : (
        <Link {...props}>
          <a title={linkText}>
            <div className="link">
              <strong>{linkText}</strong>
            </div>
          </a>
        </Link>
      )}
      <style jsx>{`
        li {
          list-style: none;
          margin-left: ${floatRight ? 'auto' : '8px'};
          margin-right: 8px;
          padding-left: 4px;
          padding-right: 4px;
        }

        li.selected {
          color: var(--primary);
          text-decoration: underline;
          text-underline-offset: 4px;
        }

        div.link {
          /* padding on top for links in <NavbarLink/> so the clickable area
           * spans to the top, but we use additional margin for the <hr/> */
          padding-top: 12px;
        }

        a {
          color: var(--primary);
        }

        a:not(:hover) {
          text-decoration: none;
        }

        .truncate {
          min-width: 120px;
        }

        @media (max-width: 800px) {
          div.link {
            padding-top: 0;
          }

          li {
            margin-block: 6px;
            margin-left: 0;
          }

          :global(.collapsed) li {
            display: ${isSelected ? 'list-item' : 'none'};
          }
        }
      `}</style>
    </li>
  );
};

/**
 * The layout component, rendered on every page. Controls the rendering of the
 * navbar as well as global page styling (e.g. color schemes).
 */
const Layout: React.FC = ({ children }) => {
  const router = useRouter();
  const { huntInfo, userInfo } = useContext(HuntInfoContext);
  const [isNavbarCollapsed, setNavbarCollapsed] = useState<boolean>(true);
  const loggedIn = !!userInfo?.teamInfo;
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

  const themeStyle = useMemo(() => {
    // FIXME: set up theme variants here.
    const theme = 'light';
    switch (theme) {
      default:
        return <LightTheme />;
    }
  }, []);

  const prehunt = huntInfo.secondsToStartTime > 0;

  return (
    <>
      <div className="nav-container">
        <nav
          className={cx({ scrolled: isScrolled, collapsed: isNavbarCollapsed })}
        >
          <button
            className="collapse-menu"
            aria-expanded={!isNavbarCollapsed}
            onClick={() =>
              setNavbarCollapsed((_isNavbarCollapsed) => !_isNavbarCollapsed)
            }
          >
            <Menu />
          </button>

          <div className="nav-list">
            <ul>
              <NavbarLink href="/" linkText={prehunt ? 'Home' : 'Puzzles'} />
              <NavbarLink href="/story" linkText="Story" />
              <NavbarLink href="/leaderboard" linkText="Teams" />
              <NavbarLink href="/rules" linkText="Rules" />
              <NavbarLink href="/faq" linkText="FAQ" />
              {prehunt ? null : (
                <NavbarLink href="/puzzles" linkText="List of Puzzles" />
              )}
              {(userInfo?.errata?.length ?? 0) > 0 && (
                <NavbarLink href="/updates" linkText="Errata" />
              )}
              <NavbarLink href="/wrapup" linkText="Wrap-up" />
              {/* FIXME: Link to archive if you have one. */}
              {/*<NavbarLink href="/FIXME" linkText="Archive" />*/}
              {/* TODO: only show after hunt starts */}
              {/*<NavbarLink href="/puzzles" linkText="Puzzles" />*/}
              {userInfo?.unlocks?.map((unlock) => (
                <NavbarLink
                  key={unlock.url}
                  href={unlock.url}
                  linkText={unlock.pageName}
                />
              ))}

              <hr />
              {userInfo?.teamInfo && (
                <>
                  <NavbarLink
                    href={`/team/${userInfo.teamInfo.slug}`}
                    linkText={userInfo.teamInfo.name}
                    floatRight
                    truncate
                    smallCaps={false}
                  />
                  {userInfo.isImpersonate && (
                    <a href="/impersonate/stop" title="Stop impersonating">
                      (🕵️)
                    </a>
                  )}
                </>
              )}
              {loggedIn ? (
                <NavbarLink href="/logout" linkText="Logout" />
              ) : (
                <>
                  <NavbarLink href="/login" linkText="Login" floatRight />
                  <NavbarLink href="/register" linkText="Sign up" />
                </>
              )}
            </ul>
          </div>
        </nav>
      </div>
      <div>{children}</div>

      <style jsx>{`
        .nav-container {
          pointer-events: none; /* gradient should not be clickable */
          position: sticky;
          top: 0;
          left: 0;
          right: 0;
          z-index: 1000; /* Show above other content */
        }

        nav {
          background: var(--navbar);
          pointer-events: initial;
          user-select: none;
        }

        .collapse-menu {
          display: none;
        }

        hr {
          border-color: var(--secondary);
          color: var(--secondary);
          border-bottom: none;
          height: 1px;
          margin: 24px 24px 12px 24px;
          flex-grow: 1;
        }

        ul {
          display: inline-flex;
          margin: 0 16px;
          padding: 0;
          width: calc(100% - 32px);
        }

        :global(#__next) {
          min-height: calc(100vh - 16px);
        }

        /* Responsive navbar for small devices. */
        @media (max-width: 800px) {
          nav-container {
            position: fixed;
          }

          nav {
            display: flex;
            align-items: flex-start;
            justify-content: flex-start;
            background-color: transparent;
          }

          hr {
            margin: 12px;
          }

          ul {
            position: absolute;
            padding-inline: 6px;
            background-color: var(--theme-translucent);
            border: 1px solid var(--primary);
            border-radius: 4px;
            color: var(--primary);
            flex-direction: column;
            width: min-content;
            max-width: calc(100% - 48px); /* Allow room for collapse icon. */
          }

          .collapsed .nav-list {
            display: none;
          }

          .collapse-menu {
            border: none;
            background-color: var(--navbar);
            color: var(--primary);
            display: inline-block;
            margin-left: 12px;
            line-height: 0;
            padding: 6px;
          }
        }
      `}</style>

      {themeStyle}
    </>
  );
};

export default Layout;
