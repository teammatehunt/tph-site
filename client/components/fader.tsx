import React, { FunctionComponent } from 'react';
import { CSSTransitionGroup } from 'react-transition-group';

interface Props {
  name: string;
  fadeInTime?: number;
  fadeOutTime?: number;
}

/** Used to fade in and out when a child component is first rendered or removed. */
const Fader: FunctionComponent<Props> = ({
  name,
  fadeInTime = 400,
  fadeOutTime = 400,
  children,
}) => (
  <CSSTransitionGroup
    transitionName={name}
    transitionEnterTimeout={fadeInTime}
    transitionLeaveTimeout={fadeOutTime}
  >
    {children}
    <style jsx>{`
      :global(.${name}-enter) {
        opacity: 0.01;
      }

      :global(.${name}-enter.${name}-enter-active) {
        opacity: 1;
        transition: opacity ${fadeInTime}ms ease-in;
      }

      :global(.${name}-leave) {
        opacity: 1;
      }

      :global(.${name}-leave.${name}-leave-active) {
        opacity: 0.01;
        transition: opacity ${fadeOutTime}ms ease-in;
      }
    `}</style>
  </CSSTransitionGroup>
);

export default Fader;
