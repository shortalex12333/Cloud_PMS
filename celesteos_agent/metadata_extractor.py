"""
Metadata extraction from file paths.
Maps NAS directory structure to doc_type and system_tag.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional


# System tag mapping from directory names
SYSTEM_TAG_MAPPING = {
    'Electrical': 'electrical',
    'HVAC': 'hvac',
    'Plumbing': 'plumbing',
    'Engines': 'propulsion',
    'Generators': 'power',
    'Generator': 'power',
    'Navigation': 'navigation',
    'Communications': 'communications',
    'Comms': 'communications',
    'Fire': 'safety',
    'Safety': 'safety',
    'Galley': 'galley',
    'Kitchen': 'galley',
    'Sanitation': 'sanitation',
    'Water': 'water',
    'Fuel': 'fuel',
    'Hydraulic': 'hydraulic',
    'Hydraulics': 'hydraulic',
    'Deck': 'deck',
    'Hull': 'hull',
    'Interior': 'interior',
    'AV': 'av',
    'Audio': 'av',
    'Video': 'av',
    'Entertainment': 'entertainment',
    'CCTV': 'security',
    'Security': 'security',
    'Stabilizers': 'stabilization',
    'Thrusters': 'propulsion',
    'Tender': 'tender',
    'Tenders': 'tender',
}

# Doc type mapping from top-level directory
DOC_TYPE_MAPPING = {
    '01_General': 'general',
    '02_Engineering': 'schematic',
    '03_Systems': 'schematic',
    '04_Manuals': 'manual',
    '05_Drawings': 'drawing',
    '06_Procedures': 'sop',
    '07_Safety': 'sop',
    '08_Maintenance': 'maintenance_log',
    '09_Logs': 'log',
    '10_Inspections': 'inspection',
    '11_Vendors': 'vendor_doc',
    '12_Warranties': 'warranty',
    '13_Certifications': 'certification',
    '14_Photos': 'photo',
    '15_Videos': 'video',
}

# Alternative naming patterns
ALT_DOC_TYPE_MAPPING = {
    'engineering': 'schematic',
    'manuals': 'manual',
    'procedures': 'sop',
    'safety': 'sop',
    'maintenance': 'maintenance_log',
    'logs': 'log',
    'inspections': 'inspection',
    'inspection': 'inspection',
    'vendors': 'vendor_doc',
    'warranties': 'warranty',
    'warranty': 'warranty',
    'certifications': 'certification',
    'certs': 'certification',
    'photos': 'photo',
    'videos': 'video',
    'drawings': 'drawing',
    'schematics': 'schematic',
}


def extract_metadata_from_path(
    file_path: Path,
    nas_root: Optional[Path] = None
) -> Dict[str, any]:
    """
    Extract metadata from file path.

    Args:
        file_path: Full path to file
        nas_root: Root of NAS mount (optional, will auto-detect)

    Returns:
        {
            'system_path': 'relative/path/from/nas',
            'directories': ['dir1', 'dir2'],
            'doc_type': 'schematic',
            'system_tag': 'electrical'
        }

    Example:
        Input: /Volumes/YachtNAS/02_Engineering/Electrical/main_panel.pdf
        Output: {
            'system_path': '02_Engineering/Electrical',
            'directories': ['02_Engineering', 'Electrical'],
            'doc_type': 'schematic',
            'system_tag': 'electrical'
        }
    """
    # Auto-detect NAS root if not provided
    if nas_root is None:
        nas_root = detect_nas_root(file_path)

    # Get relative path from NAS root
    try:
        rel_path = file_path.relative_to(nas_root)
    except ValueError:
        # File not under NAS root - use parent directory as root
        rel_path = Path(file_path.name)
        nas_root = file_path.parent

    # Extract directory parts (exclude filename)
    parts = rel_path.parts[:-1]

    if not parts:
        # File at root of NAS
        return {
            'system_path': '',
            'directories': [],
            'doc_type': 'general',
            'system_tag': 'general'
        }

    # System path (directory only, no filename)
    system_path = '/'.join(parts)
    directories = list(parts)

    # Infer doc_type from top-level directory
    top_level = parts[0]
    doc_type = DOC_TYPE_MAPPING.get(top_level)

    # Fallback: check alternative patterns
    if not doc_type:
        top_level_lower = top_level.lower()
        doc_type = ALT_DOC_TYPE_MAPPING.get(top_level_lower, 'general')

    # Infer system_tag from any matching directory
    system_tag = 'general'
    for part in parts:
        if part in SYSTEM_TAG_MAPPING:
            system_tag = SYSTEM_TAG_MAPPING[part]
            break
        # Try case-insensitive match
        for key, value in SYSTEM_TAG_MAPPING.items():
            if key.lower() in part.lower():
                system_tag = value
                break

    return {
        'system_path': system_path,
        'directories': directories,
        'doc_type': doc_type,
        'system_tag': system_tag
    }


def infer_metadata(
    file_path: Path,
    nas_root: Optional[Path] = None
) -> Tuple[str, List[str], str, str]:
    """
    Convenience function that returns tuple of metadata.

    Returns:
        (system_path, directories, doc_type, system_tag)
    """
    meta = extract_metadata_from_path(file_path, nas_root)
    return (
        meta['system_path'],
        meta['directories'],
        meta['doc_type'],
        meta['system_tag']
    )


def detect_nas_root(file_path: Path) -> Path:
    """
    Detect NAS root by looking for volume mount or known directory structure.

    Returns:
        Path to NAS root

    Raises:
        ValueError: If NAS root cannot be detected
    """
    # Check if under /Volumes/ (macOS)
    path_str = str(file_path)
    if '/Volumes/' in path_str:
        parts = file_path.parts
        try:
            volumes_idx = parts.index('Volumes')
            # Return /Volumes/{VolumeName}
            return Path('/').joinpath(*parts[:volumes_idx + 2])
        except (ValueError, IndexError):
            pass

    # Check if under numbered directory structure (01_, 02_, etc.)
    # Walk up the tree looking for a directory with multiple 01_, 02_ subdirs
    current = file_path.parent
    while current != current.parent:  # Not at root
        try:
            subdirs = [d for d in current.iterdir() if d.is_dir()]
            numbered_dirs = [d for d in subdirs if d.name[:3] in ['01_', '02_', '03_', '04_']]

            if len(numbered_dirs) >= 2:
                # Found the NAS root (has multiple numbered directories)
                return current
        except (PermissionError, OSError):
            pass

        current = current.parent

    # Fallback: use parent directory of file
    return file_path.parent


def get_content_type(file_path: Path) -> str:
    """
    Determine MIME type from file extension.

    Args:
        file_path: Path to file

    Returns:
        MIME type string
    """
    ext = file_path.suffix.lower()
    mapping = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.zip': 'application/zip',
        '.7z': 'application/x-7z-compressed',
        '.rar': 'application/x-rar-compressed',
    }
    return mapping.get(ext, 'application/octet-stream')


def is_supported_file(file_path: Path) -> bool:
    """
    Check if file type is supported for upload.

    Args:
        file_path: Path to file

    Returns:
        True if supported
    """
    supported_extensions = {
        '.pdf', '.docx', '.doc', '.xlsx', '.xls',
        '.pptx', '.ppt', '.txt', '.csv', '.png',
        '.jpg', '.jpeg', '.gif'
    }
    return file_path.suffix.lower() in supported_extensions
