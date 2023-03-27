// type checking is disabled because after static conversion, teamInfo is always
// null, which forces the type to never, which makes the rest of the code fail.
import React, {
  FunctionComponent,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import Head from 'next/head';

import HuntInfoContext from 'components/context';
import Confetti from 'components/confetti';
import Section from 'components/section';

interface Props {
  teamInfo?: {
    name: string;
    profile_pic?: string;
    profile_pic_approved: boolean;
  };
}

const Victory: FunctionComponent<Props> = () => {
  const { userInfo } = useContext(HuntInfoContext);
  const teamInfo = userInfo?.teamInfo;

  const w = 950;
  const h = 820;
  const [width, setWidth] = useState(w);
  const ref = useRef<HTMLDivElement>(null);
  const scale = width / w;

  useEffect(() => {
    const onResize = () => {
      if (ref.current) {
        setWidth(ref.current.offsetWidth);
      }
    };
    onResize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
    };
  }, []);

  return (
    <>
      <Head>
        <title>Congratulations!</title>
      </Head>

      <Section center>
        <Confetti fadeOut={false} />
        <div className="container" ref={ref}>
          <img className="finale" src={undefined /* FIXME */} />
        </div>
        <p>You’ve completed Matt and Emma's FIXME!</p>
        <p>
          Thank you, <b>{teamInfo?.name ?? ''}</b>, for bringing Matt and Emma
          home.
        </p>
        <p>
          Before you go, we would love to{' '}
          <a href="FIXME" target="_blank">
            hear your feedback on the hunt
          </a>
          !
        </p>
      </Section>

      <style jsx>{`
        p {
          font-size: 18px;
        }

        .container {
          position: relative;
          max-width: 100%;
          width: max-content;
          height: min-content;
          margin-left: auto;
          margin-right: auto;
        }

        .finale {
          width: 500px;
          margin: 20vh 0 10vh;
          max-width: 100%;
        }

        @media (max-width: 800px) {
          .container {
            width: 90vw;
          }
        }
      `}</style>
    </>
  );
};

export default Victory;
