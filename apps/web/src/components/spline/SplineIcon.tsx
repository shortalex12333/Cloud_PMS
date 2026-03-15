'use client';

/**
 * SplineIcon
 * Renders a Spline scene via @splinetool/runtime.
 *
 * renderSize: the pixel dimension the scene camera was designed for (i.e. the
 * natural canvas size at which the icon fills the frame). Set the inner div to
 * this size so Spline renders at correct resolution, then CSS-scale to `size`.
 *
 * When icon content doesn't fill the full canvas (Spline world-space camera is
 * fixed), use cropX/cropY/cropSize to describe the icon's bounding box within
 * the renderSize canvas. The component will translate+scale so that region
 * fills the `size × size` display box exactly.
 *
 * The outer div clips at `size × size`; nothing bleeds into layout.
 */

import { useEffect, useRef } from 'react';

interface SplineIconProps {
  scene: string;
  /** Display size in CSS px (default 32) */
  size?: number;
  /** The canvas dimension the scene was designed for — determines render resolution */
  renderSize?: number;
  /** X center of actual icon content within the renderSize canvas (px). Default: renderSize/2 */
  cropX?: number;
  /** Y center of actual icon content within the renderSize canvas (px). Default: renderSize/2 */
  cropY?: number;
  /** Width/height of the icon content bounding box within renderSize canvas (px). Default: renderSize */
  cropSize?: number;
  className?: string;
}

export default function SplineIcon({
  scene,
  size = 32,
  renderSize = 200,
  cropX,
  cropY,
  cropSize,
  className,
}: SplineIconProps) {
  const innerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !innerRef.current) return;

    let app: any;

    import('@splinetool/runtime')
      .then(({ Application }) => {
        if (!canvasRef.current) return;
        app = new Application(canvasRef.current);
        return app.load(scene);
      })
      .then(() => {
        if (!innerRef.current) return;
        // If crop props provided, translate so the crop center aligns with the
        // display box center, then scale so cropSize fills `size`.
        const cx = cropX ?? renderSize / 2;
        const cy = cropY ?? renderSize / 2;
        const cs = cropSize ?? renderSize;
        const s = size / cs;
        const tx = size / 2 - cx * s;
        const ty = size / 2 - cy * s;
        innerRef.current.style.transform = `translate(${tx}px, ${ty}px) scale(${s})`;
        innerRef.current.style.transformOrigin = '0 0';
      })
      .catch((err: unknown) => console.error('[SplineIcon] error:', err));

    return () => { app?.dispose(); };
  }, [scene, size, renderSize, cropX, cropY, cropSize]);

  return (
    <div
      className={className}
      style={{ width: size, height: size, flexShrink: 0, pointerEvents: 'none', overflow: 'hidden', position: 'relative' }}
    >
      <div
        ref={innerRef}
        style={{ width: renderSize, height: renderSize, position: 'absolute', top: 0, left: 0 }}
      >
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}
