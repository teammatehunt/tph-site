import React, {
  FunctionComponent,
  useCallback,
  useEffect,
  useState,
} from 'react';
import dynamic from 'next/dynamic';

// Lazy-load confetti.
const ReactConfetti = dynamic(() => import('react-confetti'), {
  ssr: false,
});

/** Wrapper for Confetti component that auto-fades after 7 seconds. */
const Confetti: FunctionComponent<{
  lightMode?: boolean;
  fadeOut?: boolean;
}> = ({ lightMode = false, fadeOut = true }) => {
  const props = lightMode
    ? null
    : {
        colors: ['white'],
        drawShape: drawShape,
        initialVelocityX: 12,
        initialVelocityY: 8,
      };
  const [numPieces, setNumPieces] = useState<number>(lightMode ? 200 : 20);

  const [done, setDone] = useState<boolean>(false);

  useEffect(() => {
    if (fadeOut) {
      const timeoutId = window.setTimeout(() => void setNumPieces(0), 7000);
      return () => window.clearTimeout(timeoutId);
    }
  }, []);

  if (done) {
    return null;
  }

  function drawShape(this: any, ctx) {
    // Using this callback to set state variables is a hack but ReactConfetti
    // gives limited initialization options.
    this.angle = 0;
    this.angularSpin = 0;
    this.rotateY = 1;
    this.rotationDirection = 0;
    ctx.beginPath();

    const shadowColor = ctx.shadowColor;
    const shadowBlur = ctx.shadowBlur;
    ctx.shadowColor = 'white';
    ctx.shadowBlur = 3;
    ctx.globalAlpha = 0.75;
    ctx.arc(0, 0, this.radius / 5, 0, 2 * Math.PI);
    ctx.fill();

    const k = -10;
    const x = this.vx;
    const y = this.vy;
    const theta = Math.atan2(y, x);
    const k2 = 0.5;
    let _x = k2 * -Math.sin(theta);
    let _y = k2 * Math.cos(theta);

    ctx.moveTo(k * x, k * y);
    ctx.lineTo(_x, _y);
    _x = k2 * Math.sin(theta);
    _y = k2 * -Math.cos(theta);
    ctx.lineTo(_x, _y);
    ctx.lineTo(k * x, k * y);
    ctx.fill();
  }

  return (
    <>
      <div className={`confetti ${lightMode ? 'light' : ''}`}>
        <ReactConfetti
          numberOfPieces={numPieces}
          onConfettiComplete={() => void setDone(true)}
          {...props}
        />
      </div>
      <style jsx>{`
        .confetti {
          position: fixed;
          top: 0;
          z-index: -100;
        }
        .confetti.light {
          z-index: 100;
        }
      `}</style>
    </>
  );
};

export default Confetti;
