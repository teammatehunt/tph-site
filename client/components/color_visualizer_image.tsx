// Used to display a hex color viewer

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import cx from 'classnames';

import { NO_COPY_CLASS } from 'components/copy';
import InfoIcon from 'components/info_icon';

// https://drafts.csswg.org/css-color/#hsl-to-rgb
function hslToRgb(hue, sat, light) {
  hue = hue % 360;

  if (hue < 0) {
    hue += 360;
  }

  sat /= 100;
  light /= 100;

  function f(n) {
    let k = (n + hue / 30) % 12;
    let a = sat * Math.min(light, 1 - light);
    return light - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
  }

  return [f(0), f(8), f(4)];
}

// https://drafts.csswg.org/css-color/#rgb-to-hsl
function rgbToHsl(red, green, blue) {
  let max = Math.max(red, green, blue);
  let min = Math.min(red, green, blue);
  let [hue, sat, light] = [NaN, 0, (min + max) / 2];
  let d = max - min;

  if (d !== 0) {
    sat =
      light === 0 || light === 1
        ? 0
        : (max - light) / Math.min(light, 1 - light);

    switch (max) {
      case red:
        hue = (green - blue) / d + (green < blue ? 6 : 0);
        break;
      case green:
        hue = (blue - red) / d + 2;
        break;
      case blue:
        hue = (red - green) / d + 4;
    }

    hue = hue * 60;
  }

  return [hue, sat * 100, light * 100];
}

// https://drafts.csswg.org/css-color/#hwb-to-rgb
function hwbToRgb(hue, white, black) {
  white /= 100;
  black /= 100;
  if (white + black >= 1) {
    let gray = white / (white + black);
    return [gray, gray, gray];
  }
  let rgb = hslToRgb(hue, 100, 50);
  for (let i = 0; i < 3; i++) {
    rgb[i] *= 1 - white - black;
    rgb[i] += white;
  }
  return rgb;
}

// https://drafts.csswg.org/css-color/#rgb-to-hwb
function rgbToHwb(red, green, blue) {
  var hsl = rgbToHsl(red, green, blue);
  var white = Math.min(red, green, blue);
  var black = 1 - Math.max(red, green, blue);
  return [hsl[0], white * 100, black * 100];
}

interface ColorVisualizerProps {
  color: string | number[];
}

export const ColorVisualizer: React.FC<ColorVisualizerProps> = ({ color }) => {
  const [width, setWidth] = useState(100);
  const ref = useRef<HTMLDivElement>(null);
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
  let rgb: number[] | null = null;
  if (typeof color === 'string') {
    const suffix = color.startsWith('#') ? color.substr(1) : color;
    const isValid = Boolean(
      suffix.match(/^[0-9a-f]+$/i) && [3, 6].includes(suffix.length)
    );
    if (isValid) {
      rgb = [];
      for (let i = 0; i < 3; ++i) {
        const len = suffix.length / 3;
        rgb.push(parseInt(suffix.substr(i * len, len), 16) / 255);
      }
    }
  } else {
    if (color.length >= 3) rgb = color.map((v) => v / 255);
  }
  const n = 64;
  const conicGradient = Array.from(
    Array(n + 1),
    (_, i) => `hwb(${360 * (1 - i / n)} 0% 0%)`
  ).join(',\n');

  let [h, w, b] = rgbToHwb(rgb?.[0], rgb?.[1], rgb?.[2]);
  if (Number.isNaN(h)) h = 0;

  const barWidth = 10;
  const y = (1 / 2 + (((w - b) / 100) * Math.sqrt(3)) / 4) * 100;
  const x = (1 / 4 + ((1 - w / 100 - b / 100) * 3) / 4) * 100;

  const textSize = 10;

  return (
    <div className="color-visualizer" ref={ref}>
      <div className="scaled">
        <div className="labels">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <defs>
              <path
                id="circular"
                d={`M 50 ${textSize / 2} A ${50 - textSize / 2} ${
                  50 - textSize / 2
                } 0 0 1 50 ${100 - textSize / 2}`}
              />
            </defs>
            {['red', 'yellow', 'green', 'cyan', 'blue', 'magenta'].map(
              (color, i) => (
                <text
                  key={color}
                  className={`text ${color}`}
                  transform={`rotate(${-60 * i} 50 50)`}
                >
                  <textPath href="#circular" startOffset="50%">
                    {color}
                  </textPath>
                </text>
              )
            )}
          </svg>
        </div>
        <div className="diagram">
          <div className="wheel" />
          {(rgb || null) && (
            <div className="rotated">
              <div className="bar" />
              <div className="triangle-scaled">
                <div className="triangle" />
                <div className="marker" />
              </div>
            </div>
          )}
        </div>
      </div>
      <style jsx>{`
        .color-visualizer {
          position: relative;
          padding-bottom: 100%;
        }
        .scaled {
          position: absolute;
          height: 100px;
          width: 100px;
          transform: scale(calc(${width} / 100));
          transform-origin: top left;
        }
        .scaled > * {
          position: absolute;
        }
        .diagram {
          height: 100px;
          width: 100px;
          transform: scale(${1 - (2 * textSize) / 100});
        }
        .diagram > * {
          position: absolute;
        }
        .labels {
          height: 100px;
          width: 100px;
        }
        .text {
          text-anchor: middle;
          dominant-baseline: middle;
          font-size: 10px;
          stroke-width: 0.2px;
          stroke: rgba(0, 0, 0, 0.5);
          paint-order: stroke;
        }
        .red {
          fill: hwb(0 0% 0%);
        }
        .yellow {
          fill: hwb(60 0% 0%);
        }
        .green {
          fill: hwb(120 0% 0%);
        }
        .cyan {
          fill: hwb(180 0% 0%);
        }
        .blue {
          fill: hwb(240 0% 0%);
        }
        .magenta {
          fill: hwb(300 0% 0%);
        }
        .wheel {
          height: 100px;
          width: 100px;
          background: conic-gradient(from 0.25turn, ${conicGradient});
          clip-path: path(
            evenodd,
            '${`
            M 50,0
            A 50,50 0 1,1 50,100
            A 50,50 0 1,1 50,0
            V ${barWidth} A ${50 - barWidth},${50 - barWidth} 0 1,1 50,${
              100 - barWidth
            }
            A ${50 - barWidth},${50 - barWidth} 0 1,1 50,${barWidth}
            Z`
              .trim()
              .replaceAll(/\s+/g, ' ')}'
          );
        }
        .rotated {
          height: 100%;
          width: 100%;
          transform: rotate(${-h}deg);
        }
        .triangle-scaled {
          height: 100%;
          width: 100%;
          transform: scale(${1 - (2 * barWidth) / 100});
        }
        .triangle {
          position: absolute;
          height: 100px;
          width: 100px;
          background: linear-gradient(
              to right,
              transparent 25%,
              hwb(${h} 0% 0%)
            ),
            conic-gradient(
              from 0.25turn at 100% 50%,
              white 0deg 150deg,
              black 210deg 360deg
            );
          clip-path: polygon(
            100% 50%,
            25% ${50 + 25 * Math.sqrt(3)}%,
            25% ${50 - 25 * Math.sqrt(3)}%
          );
        }
        .bar {
          position: absolute;
          height: 1px;
          width: ${barWidth}px;
          top: 50%;
          right: 0;
          background-color: white;
          transform: translateY(-50%);
        }
        .marker {
          position: absolute;
          height: 5px;
          width: 5px;
          top: ${y}px;
          left: ${x}px;
          border-radius: 50%;
          border: 1px solid white;
          transform: translate(-50%);
        }
      `}</style>
    </div>
  );
};

// TODO: standardize styling
export const ColorVisualizerImageHelp = (props) => (
  <InfoIcon className={NO_COPY_CLASS} {...props}>
    You can click on this image to visualize colors. The visualization tool is
    not part of a puzzle.
  </InfoIcon>
);

interface ColorVisualizerImageProps
  extends React.ImgHTMLAttributes<HTMLImageElement> {
  center?: boolean;
  hideIcon?: boolean;
}

const ColorVisualizerImage: React.FC<ColorVisualizerImageProps> = ({
  src,
  center = false,
  hideIcon = false,
  ...props
}) => {
  // popup properties
  const [popupPosition, setPopupPosition] = useState<number[] | null>(null);
  const closePopup = useCallback(() => {
    setPopupPosition(null);
  }, [setPopupPosition]);
  const closePopupEscape = useCallback(
    (e) => {
      if (e.key === 'Escape') closePopup();
    },
    [closePopup]
  );

  const [color, setColor] = useState<number[]>([]);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const onLoad = useCallback(() => {
    const img = imgRef.current;
    const canvas = canvasRef.current;
    if (img && canvas) {
      const ctx = canvas.getContext('2d', {
        willReadFrequently: true,
      });
      if (ctx) {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      }
    }
  }, []);
  useEffect(() => {
    if (imgRef.current?.complete) onLoad();
  }, []);
  const onClick = useCallback(
    (e: React.MouseEvent<HTMLImageElement>) => {
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      const img = imgRef.current;
      if (canvas && ctx && img) {
        const rect = img.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const offsetY = e.clientY - rect.top;
        const x = Math.round(offsetX * (canvas.width / rect.width));
        const y = Math.round(offsetY * (canvas.height / rect.height));
        const rgba = ctx.getImageData(x, y, 1, 1).data;
        const color = [rgba[0], rgba[1], rgba[2]];
        const alpha = rgba[3];
        if (alpha) {
          setColor(color);
          const offset = 10;
          setPopupPosition([offsetX + offset, offsetY + offset]);
        }
      }
    },
    [setColor, setPopupPosition]
  );

  return (
    <>
      {!hideIcon && <ColorVisualizerImageHelp center={center} />}
      <div className="component" onKeyDown={closePopupEscape} tabIndex={-1}>
        <div className="popup" role="dialog" aria-label="Color visualizer">
          <input
            type="button"
            className="x-button"
            onClick={closePopup}
            value="✖"
            aria-label="Close"
          />
          <ColorVisualizer color={color} />
        </div>
        <img
          ref={imgRef}
          src={src}
          crossOrigin="anonymous"
          onLoad={onLoad}
          onClick={onClick}
          {...props}
        />
        <canvas ref={canvasRef} />
      </div>
      <style jsx>{`
        img {
          cursor: crosshair;
        }
        canvas {
          display: none;
        }
        input.x-button {
          background: rgba(0, 0, 0, 0.2);
          border: none;
          border-radius: 50%;
          color: var(--white);
          width: 40px;
          height: 40px;
          position: absolute;
          top: 0;
          right: 0;
          z-index: 1; /* Always show higher than content */
        }
        input.x-button:hover {
          background-color: rgba(0, 0, 0, 0.4);
          cursor: pointer;
        }
        .component {
          position: relative;
          outline: none;
        }
        .popup {
          position: absolute;
          visibility: ${popupPosition === null ? 'hidden' : 'visible'};
          left: ${popupPosition?.[0] ?? 0}px;
          top: ${popupPosition?.[1] ?? 0}px;
          width: 200px;
          height: 200px;
          padding: 10px;
          border-radius: 20px;
          background-color: dimgray;
          opacity: 0.9;
          z-index: 1;
        }
      `}</style>
    </>
  );
};
export default ColorVisualizerImage;
