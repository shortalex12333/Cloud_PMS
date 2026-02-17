---
wave: 2
depends_on: [FE-01-01]
files_modified:
  - apps/web/src/components/lens/WorkOrderLens.tsx
  - apps/web/src/components/media/MediaRenderer.tsx
  - apps/web/src/components/media/DocumentCard.tsx
autonomous: true
requirements: [WO-03]
---

# Plan FE-01-04: File Rendering (Media + Documents)

## Objective

Implement file rendering in Work Order lens: media renders inline (images, videos), documents render as preview cards that open Document lens.

## Tasks

<task id="1">
Create `MediaRenderer.tsx`:

```tsx
interface MediaRendererProps {
  file: {
    id: string;
    url: string;         // Signed URL
    filename: string;
    mime_type: string;
    size_bytes: number;
  };
  maxHeight?: number;    // Default 240px
}
```

Behavior:
- Images (.png, .jpg, .jpeg, .gif, .heic, .webp): `<img>` with object-fit: cover
- Videos (.mp4, .mov, .webm): `<video>` with controls, poster frame
- Click opens lightbox (full-screen overlay)
- Loading skeleton while fetching
- Error state if URL fails
</task>

<task id="2">
Create `DocumentCard.tsx`:

```tsx
interface DocumentCardProps {
  file: {
    id: string;
    url: string;
    filename: string;
    mime_type: string;
    size_bytes: number;
  };
  onClick: () => void;   // Opens Document lens
}
```

Visual spec:
- Card with surface-primary background
- Left: Document icon (📄 for PDF, 📝 for DOCX, etc.)
- Middle: filename (truncated), file size formatted
- Right: chevron or open icon
- Hover: surface-hover background
- Click: Navigate to Document lens with file ID
</task>

<task id="3">
Create utility to determine file type:

```tsx
function getFileCategory(mimeType: string): 'image' | 'video' | 'document' {
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.startsWith('video/')) return 'video';
  return 'document';
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
```
</task>

<task id="4">
Update AttachmentsSection to use new renderers:

```tsx
{attachments.map(file => {
  const category = getFileCategory(file.mime_type);

  if (category === 'image' || category === 'video') {
    return <MediaRenderer key={file.id} file={file} maxHeight={240} />;
  }

  return (
    <DocumentCard
      key={file.id}
      file={file}
      onClick={() => openDocumentLens(file.id)}
    />
  );
})}
```
</task>

<task id="5">
Ensure signed URLs are used:

```tsx
// Files should already have signed URLs from backend
// If not, fetch signed URL before rendering
const { data: signedUrl } = useQuery({
  queryKey: ['signed-url', file.id],
  queryFn: () => api.get(`/files/${file.id}/signed-url`),
  enabled: !file.url.includes('token='),
});
```

Verify:
- No raw storage paths exposed
- URLs include authentication token
- URLs expire after reasonable time (1 hour)
</task>

<task id="6">
Test file rendering:

1. Upload test image → verify inline render
2. Upload test PDF → verify card render
3. Click PDF card → verify Document lens opens
4. Test expired URL handling
</task>

## Verification

```bash
# Components exist
ls apps/web/src/components/media/

# Build passes
cd apps/web && npm run build

# No raw storage paths
grep -rn "storage.googleapis\|supabase.co/storage" apps/web/src/components/ | grep -v "// " | wc -l
# Should be 0
```

## must_haves

- [ ] MediaRenderer handles images and videos
- [ ] DocumentCard shows filename, size, icon
- [ ] File type detection works correctly
- [ ] Signed URLs used (no raw paths)
- [ ] Click document → Document lens opens
- [ ] Build passes
