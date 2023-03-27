import React, { FunctionComponent, Fragment } from 'react';

interface Props {
  caption?: string | string[];
  clickForFullSize?: boolean;
}

/** Generic component for an image with a caption. */
const CaptionImage: FunctionComponent<
  Props & React.ImgHTMLAttributes<HTMLImageElement>
> = ({
  caption,
  id,
  src,
  clickForFullSize = false,
  alt,
  children,
  ...props
}) => {
  const Wrapper = clickForFullSize ? 'a' : 'div';

  const fullCaption = Array.isArray(caption) ? caption.join(' ') : caption;
  const captionArray = Array.isArray(caption) ? caption : [caption];

  return (
    <>
      <Wrapper
        className="text-center"
        href={clickForFullSize ? src : undefined}
        target={clickForFullSize ? '_blank' : ''}
        rel={clickForFullSize ? 'noopener noreferrer' : ''}
        role="figure"
        aria-labelledby={`caption-${id}`}
      >
        {children ?? (
          <img
            src={src}
            className="block mx-auto"
            alt={alt ?? fullCaption ?? ''}
            {...props}
          />
        )}
      </Wrapper>
      {caption && (
        <p className="text-center caption" id={`caption-${id}`}>
          <strong>
            {captionArray.map((line, i) => (
              <Fragment key={line}>
                {line}
                {i < caption.length - 1 && <br />}
              </Fragment>
            ))}
          </strong>
        </p>
      )}
      <style jsx>{`
        img {
          max-width: 80%;
        }

        .caption {
          margin: 8px 0 20px;
        }
      `}</style>
    </>
  );
};

interface CaptionImagesProps extends Props {
  srcs: string[];
  alts?: string[];
  maxHeight?: string;
}

export const CaptionImages: FunctionComponent<CaptionImagesProps> = ({
  srcs,
  alts,
  caption,
  maxHeight = '18vh',
  ...props
}) => (
  <CaptionImage caption={caption} {...props}>
    <div className="flex items-center justify-center">
      {srcs.map((imageSrc, i) => (
        <img
          src={imageSrc}
          key={imageSrc}
          alt={alts?.[i] ?? (Array.isArray(caption) ? caption[i] : caption)}
        />
      ))}
    </div>

    <style jsx>{`
      @media (max-width: 800px) {
        div {
          overflow-x: auto;
        }

        img {
          max-width: 25%;
          height: 8vh;
        }
      }

      img {
        object-fit: cover;
      }

      img:not(:first-child) {
        margin-left: 8px;
      }

      img {
        height: ${maxHeight};
      }
    `}</style>
  </CaptionImage>
);

export default CaptionImage;
