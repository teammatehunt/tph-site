// Drag drop component for icon position editing.

import { useRouter } from 'utils/router';
import { clientFetch } from 'utils/fetch';
import { Rnd } from 'react-rnd';

export const DragDropPiece = ({
  slug,
  position,
  setPosition,
  imageWidth,
  setWidth,
  roundWidth,
  roundHeight,
  containerRef,
}) => {
  const router = useRouter();
  // Translate percentages into pixels.
  const left = (position[0] / 100) * roundWidth;
  const top = (position[1] / 100) * roundHeight;
  let imgWidth = (imageWidth / 100) * roundWidth;
  const pos = {
    x: left,
    y: top,
  };

  const getPosition = (e, d) => {
    if (e.clientX === 0 && e.clientY === 0) {
      // There's a weird bug where dragend doesn't publish pointer info.
      // Just ignore it if it's exactly 0,0 since it's very unlikely someone manually drags it here.
      return;
    }
    const containerRect = containerRef.current!.getBoundingClientRect();
    // We need to compute the appropriate percentages.
    // The drag view of the text may go ahead / behind the true image if the round as
    // rendered is smaller than the full-size window, but it should snap back when mouse is
    // released.
    let xPerc = (e.clientX - containerRect.left) / containerRect.width;
    let yPerc = (e.clientY - containerRect.top) / containerRect.height;
    // clip to 0 to 100%
    xPerc = 100 * Math.min(1, Math.max(xPerc, 0));
    yPerc = 100 * Math.min(1, Math.max(yPerc, 0));
    return [xPerc, yPerc];
  };

  const handleDrag = (e, d) => {
    const newPos = getPosition(e, d);
    // Ehhh this is O(n) but I guess it's okay, n is small?
    setPosition(newPos);
  };

  const handleDragStop = (e, d) => {
    // update in backend
    const pos = getPosition(e, d);
    // may be undefined from error case check.
    if (pos) {
      const formData = new FormData();
      formData.append('x', pos[0].toString());
      formData.append('y', pos[1].toString());
      clientFetch(router, `/position/${slug}`, {
        method: 'POST',
        body: formData,
      });
    }
  };

  const handleResizeStop = (e, dir, ref, delta, position) => {
    // apply delta and also update last known width.
    // we only apply this in resizeStop because the delta is defined relative to
    // when the resize was started. Unfortunately this means the icon does not re-render the
    // size until the mouse is let go.
    let widthPerc = (imgWidth + delta.width) / roundWidth;
    widthPerc = 100 * Math.min(1, Math.max(widthPerc, 0));
    setWidth(widthPerc);
    const formData = new FormData();
    formData.append('w', widthPerc.toString());
    clientFetch(router, `/position/${slug}`, {
      method: 'POST',
      body: formData,
    });
  };

  return (
    <Rnd
      position={{ x: left, y: top }}
      size={{ width: imgWidth, height: 40 }}
      minWidth={10}
      onDrag={handleDrag}
      onDragStop={handleDragStop}
      onResizeStop={handleResizeStop}
      enableResizing={{
        top: false,
        right: true,
        bottom: false,
        left: false,
        topRight: false,
        bottomRight: false,
        bottomLeft: false,
        topLeft: false,
      }}
    >
      <p className="h-12 bg-[rgba(255,0,0,0.25)]">Drag/Resize</p>
    </Rnd>
  );
};

export default DragDropPiece;
