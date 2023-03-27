import React, { FunctionComponent } from 'react';
import cx from 'classnames';
import { Transition } from '@headlessui/react';

interface Props {
  name: string;
  show: boolean;
  fadeInTime?: number;
  fadeOutTime?: number;
}

/** Used to fade in and out when a child component is first rendered or removed. */
const Fader: FunctionComponent<Props> = ({
  name,
  show,
  fadeInTime = 300,
  fadeOutTime = 300,
  children,
}) => (
  <Transition
    appear
    show={show}
    enter={cx(name, 'transition-opacity ease-in fade-in')}
    enterFrom="opacity-0"
    enterTo="opacity-100"
    leave={cx(name, 'transition-opacity ease-in fade-out')}
    leaveFrom="opacity-100"
    leaveTo="opacity-0"
  >
    {children}
    <style global jsx>{`
      .${name}.fade-in {
        transition-duration: ${fadeInTime}ms;
      }

      .${name}.fade-out {
        transition-duration: ${fadeOutTime}ms;
      }
    `}</style>
  </Transition>
);

export default Fader;
