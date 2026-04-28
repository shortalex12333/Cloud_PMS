// apps/web/src/components/lens/sections/__tests__/LensImageViewer.test.tsx

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import * as React from 'react';
import { LensImageViewer, type LensImage } from '../LensImageViewer';

afterEach(() => {
  cleanup();
});

function img(over: Partial<LensImage> = {}): LensImage {
  return {
    id: over.id ?? 'att-1',
    url: over.url ?? 'https://cdn.example/full/att-1.jpg',
    thumbnail_url: over.thumbnail_url,
    description: over.description ?? null,
    uploaded_by_name: over.uploaded_by_name ?? 'Alex K.',
    uploaded_at: over.uploaded_at ?? '2026-04-24T10:00:00Z',
    category: over.category ?? 'photo',
    filename: over.filename ?? 'inspection.jpg',
  };
}

describe('LensImageViewer', () => {
  it('renders empty-state message + upload button when images=[]', () => {
    const onUpload = vi.fn();
    render(
      <LensImageViewer
        images={[]}
        canUpload
        onUpload={onUpload}
        emptyMessage="Nothing here yet"
      />,
    );
    expect(screen.getByTestId('lens-image-viewer-empty').textContent).toBe(
      'Nothing here yet',
    );
    fireEvent.click(screen.getByRole('button', { name: /Upload Image/ }));
    expect(onUpload).toHaveBeenCalledTimes(1);
  });

  it('renders every image as a list item with uploader + comment', () => {
    render(
      <LensImageViewer
        images={[
          img({ id: '1', description: 'Panel open, wires visible' }),
          img({ id: '2', description: 'Filter replaced' }),
        ]}
      />,
    );
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0].textContent).toContain('Panel open, wires visible');
    expect(items[0].textContent).toContain('Alex K.');
    expect(items[1].textContent).toContain('Filter replaced');
  });

  it('falls back to "No comment" when description is missing', () => {
    render(<LensImageViewer images={[img({ description: null })]} />);
    expect(screen.getByText('No comment')).toBeDefined();
  });

  it('hides Edit button when no onEditComment provided (read-only mode)', () => {
    render(<LensImageViewer images={[img({ description: 'x' })]} />);
    expect(screen.queryByRole('button', { name: /Edit/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /\+ Comment/ })).toBeNull();
  });

  it('Edit button renders "+ Comment" label on images without description', () => {
    const onEditComment = vi.fn();
    render(
      <LensImageViewer
        images={[img({ description: null })]}
        onEditComment={onEditComment}
      />,
    );
    const edit = screen.getByRole('button', { name: /\+ Comment/ });
    expect(edit).toBeDefined();
  });

  it('opens lightbox on image click, shows Next/Prev nav only when multiple', () => {
    const imgs = [img({ id: '1' }), img({ id: '2' }), img({ id: '3' })];
    render(<LensImageViewer images={imgs} />);
    // No dialog yet
    expect(screen.queryByRole('dialog')).toBeNull();
    // Open first image
    fireEvent.click(screen.getAllByRole('button', { name: /Open inspection\.jpg/ })[0]);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeDefined();
    // Nav arrows present when > 1 image
    expect(screen.getByRole('button', { name: 'Previous image' })).toBeDefined();
    expect(screen.getByRole('button', { name: 'Next image' })).toBeDefined();
  });

  it('lightbox hides nav arrows for single-image gallery', () => {
    render(<LensImageViewer images={[img({ id: 'solo' })]} />);
    fireEvent.click(screen.getAllByRole('button', { name: /Open/ })[0]);
    expect(screen.getByRole('dialog')).toBeDefined();
    expect(screen.queryByRole('button', { name: 'Previous image' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Next image' })).toBeNull();
  });

  it('ArrowRight advances the lightbox to the next image', () => {
    const imgs = [
      img({ id: '1', description: 'first' }),
      img({ id: '2', description: 'second' }),
    ];
    render(<LensImageViewer images={imgs} />);
    fireEvent.click(screen.getAllByRole('button', { name: /Open/ })[0]);
    // first image visible in dialog
    expect(screen.getByRole('dialog').textContent).toContain('first');
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getByRole('dialog').textContent).toContain('second');
  });

  it('Escape closes the lightbox', () => {
    render(<LensImageViewer images={[img()]} />);
    fireEvent.click(screen.getAllByRole('button', { name: /Open/ })[0]);
    expect(screen.getByRole('dialog')).toBeDefined();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('clicking the overlay backdrop closes the lightbox', () => {
    render(<LensImageViewer images={[img()]} />);
    fireEvent.click(screen.getAllByRole('button', { name: /Open/ })[0]);
    const dialog = screen.getByRole('dialog');
    fireEvent.click(dialog);
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('fires onEditComment with new text when user edits via prompt', async () => {
    const onEditComment = vi.fn();
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('new caption');
    render(
      <LensImageViewer
        images={[img({ id: 'att-9', description: 'old' })]}
        onEditComment={onEditComment}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    expect(onEditComment).toHaveBeenCalledWith('att-9', 'new caption');
    promptSpy.mockRestore();
  });

  it('ignores edit when the prompt is cancelled (returns null)', async () => {
    const onEditComment = vi.fn();
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue(null);
    render(
      <LensImageViewer
        images={[img({ description: 'old' })]}
        onEditComment={onEditComment}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    expect(onEditComment).not.toHaveBeenCalled();
    promptSpy.mockRestore();
  });

  it('uses thumbnail_url when present, falls back to url', () => {
    const { container } = render(
      <LensImageViewer
        images={[
          img({ id: 'a', thumbnail_url: 'https://cdn/thumb/a.jpg', url: 'https://cdn/full/a.jpg' }),
          img({ id: 'b', thumbnail_url: undefined, url: 'https://cdn/full/b.jpg' }),
        ]}
      />,
    );
    const imgs = container.querySelectorAll('img');
    expect(imgs[0].getAttribute('src')).toBe('https://cdn/thumb/a.jpg');
    expect(imgs[1].getAttribute('src')).toBe('https://cdn/full/b.jpg');
  });
});
