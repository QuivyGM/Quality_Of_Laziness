#!/usr/bin/env python3
"""
Music File Renamer (with Auto-Sanitization)
============================================
Renames music files based on metadata with configurable format.
Automatically sanitizes invalid characters.

Files are copied to OUTPUT_PATH - originals are never modified.
"""

# =============================================================================
# CONFIGURATION - Edit these values
# =============================================================================

TARGET_PATH = r"C:\Users\path"  # Source folder
OUTPUT_PATH = r"C:\Users\path"  # Output folder
DRY_RUN = False              # True = preview only, False = actually copy/rename

# -----------------------------------------------------------------------------
# FILENAME FORMAT CONFIGURATION
# -----------------------------------------------------------------------------
# Available placeholders: {artist}, {album}, {track}, {title}
# {track} will be zero-padded to 2 digits (e.g., "01", "12")

FILENAME_FORMAT = "{title} _ {artist}"
FILENAME_FORMAT_NO_TRACK = "{title} _ {artist}"

# =============================================================================
# CHARACTER REPLACEMENT RULES
# =============================================================================
# Applied in order - more specific patterns first

REPLACEMENTS = [
    (":", "-"),      # Colon to dash
    ("|", "-"),      # Pipe to dash
    ("/", "-"),      # Slash to dash
    ("?", ""),       # Question mark removed
    (""", "'"),      # Curly quote to apostrophe
    (""", "'"),      # Curly quote to apostrophe
    ("\"", "'"),     # Straight quote to apostrophe
    ("<", "("),      # Angle bracket to parenthesis
    (">", ")"),      # Angle bracket to parenthesis
    ("*", ""),       # Asterisk removed
    ("\\", "-"),     # Backslash to dash
]

# =============================================================================

import os
import sys
import shutil
import re
from pathlib import Path

try:
    from mutagen import File as MutagenFile
    from mutagen.easyid3 import EasyID3
    from mutagen.mp4 import MP4
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
except ImportError:
    print("ERROR: mutagen library not found.")
    print("Install with: pip install mutagen --break-system-packages")
    sys.exit(1)


# Android/Windows invalid filename characters
INVALID_CHARS = r'[<>:"/\\|?*]'
INVALID_CHARS_PATTERN = re.compile(INVALID_CHARS)

# Supported audio extensions
SUPPORTED_EXTENSIONS = {'.m4a', '.mp3', '.flac', '.ogg', '.opus', '.wma', '.aac', '.wav', '.aiff'}


class RenameResult:
    """Holds the result of a rename operation"""
    def __init__(self, original_path, new_name=None, success=True, reason=None,
                 was_sanitized=False, sanitize_details=None):
        self.original_path = original_path
        self.new_name = new_name
        self.success = success
        self.reason = reason
        self.was_sanitized = was_sanitized
        self.sanitize_details = sanitize_details or {}  # {field: (original, sanitized)}


def get_metadata(filepath):
    """
    Extract metadata from audio file.
    Returns dict with: artist, album, track_number, title
    """
    try:
        audio = MutagenFile(filepath, easy=True)
        if audio is None:
            return None
        
        metadata = {
            'artist': None,
            'album': None,
            'track_number': None,
            'title': None
        }
        
        # Handle MP4/M4A files differently
        if filepath.lower().endswith('.m4a') or filepath.lower().endswith('.mp4'):
            audio = MP4(filepath)
            metadata['artist'] = audio.tags.get('\xa9ART', [None])[0]
            metadata['album'] = audio.tags.get('\xa9alb', [None])[0]
            metadata['title'] = audio.tags.get('\xa9nam', [None])[0]
            track_info = audio.tags.get('trkn', [(None, None)])[0]
            if track_info and track_info[0]:
                metadata['track_number'] = str(track_info[0])
        else:
            # For other formats using easy tags
            metadata['artist'] = audio.get('artist', [None])[0]
            metadata['album'] = audio.get('album', [None])[0]
            metadata['title'] = audio.get('title', [None])[0]
            track = audio.get('tracknumber', [None])[0]
            if track:
                # Handle "1/12" format
                metadata['track_number'] = track.split('/')[0]
        
        return metadata
        
    except Exception as e:
        return None


def has_invalid_chars(text):
    """Check if text contains characters invalid for filenames"""
    if text is None:
        return False
    return bool(INVALID_CHARS_PATTERN.search(text))


def sanitize(text):
    """
    Sanitize text by applying replacement rules.
    Returns (sanitized_text, was_changed)
    """
    if text is None:
        return None, False
    
    original = text
    result = text
    
    # Apply replacements in order
    for old, new in REPLACEMENTS:
        result = result.replace(old, new)
    
    # Clean up any remaining invalid chars (fallback)
    result = INVALID_CHARS_PATTERN.sub('', result)
    
    # Clean up multiple spaces/dashes
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'-{2,}', '-', result)
    result = re.sub(r'\s*-\s*-\s*', ' - ', result)
    
    # Strip leading/trailing whitespace, dots, dashes
    result = result.strip(' .-')
    
    return result, result != original


def generate_new_filename(metadata, extension):
    """
    Generate new filename from metadata using configured format.
    """
    artist = metadata['artist']
    album = metadata['album']
    title = metadata['title']
    track = metadata['track_number']
    
    # Zero-pad track number
    if track:
        try:
            track_padded = f"{int(track):02d}"
        except (ValueError, TypeError):
            track_padded = track
    else:
        track_padded = None
    
    # Choose format based on whether track exists
    if track_padded and '{track}' in FILENAME_FORMAT:
        fmt = FILENAME_FORMAT
    else:
        fmt = FILENAME_FORMAT_NO_TRACK
    
    # Build filename from format
    new_name = fmt.format(
        artist=artist or '',
        album=album or '',
        track=track_padded or '',
        title=title or ''
    )
    
    return f"{new_name}{extension}"


def get_required_fields():
    """Determine which metadata fields are required based on format strings"""
    required = set()
    
    for fmt in [FILENAME_FORMAT, FILENAME_FORMAT_NO_TRACK]:
        if '{artist}' in fmt:
            required.add('artist')
        if '{album}' in fmt:
            required.add('album')
        if '{title}' in fmt:
            required.add('title')
    
    return required


def process_file(filepath):
    """
    Process a single file and determine if it can be renamed.
    Returns a RenameResult object.
    """
    path = Path(filepath)
    extension = path.suffix.lower()
    
    # Check if supported format
    if extension not in SUPPORTED_EXTENSIONS:
        return RenameResult(filepath, success=False, reason="Unsupported format")
    
    # Get metadata
    metadata = get_metadata(filepath)
    
    if metadata is None:
        return RenameResult(filepath, success=False, reason="Could not read metadata")
    
    # Check for missing required fields
    required_fields = get_required_fields()
    missing_fields = []
    
    for field in required_fields:
        if not metadata.get(field):
            missing_fields.append(field)
    
    if missing_fields:
        return RenameResult(
            filepath, 
            success=False, 
            reason=f"Missing metadata: {', '.join(missing_fields)}"
        )
    
    # Sanitize metadata fields
    sanitized_metadata = {}
    sanitize_details = {}
    was_sanitized = False
    
    for field in ['artist', 'album', 'title']:
        original = metadata.get(field)
        if original:
            sanitized, changed = sanitize(original)
            sanitized_metadata[field] = sanitized
            if changed:
                was_sanitized = True
                sanitize_details[field] = (original, sanitized)
        else:
            sanitized_metadata[field] = original
    
    sanitized_metadata['track_number'] = metadata['track_number']
    
    # Generate new filename with sanitized metadata
    new_name = generate_new_filename(sanitized_metadata, extension)
    
    return RenameResult(
        filepath, 
        new_name=new_name, 
        success=True,
        was_sanitized=was_sanitized,
        sanitize_details=sanitize_details
    )


def scan_directory(directory):
    """
    Scan directory for audio files and process each one.
    Returns tuple of (successful_results, failed_results)
    """
    successful = []
    failed = []
    
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"ERROR: Directory '{directory}' does not exist")
        sys.exit(1)
    
    if not dir_path.is_dir():
        print(f"ERROR: '{directory}' is not a directory")
        sys.exit(1)
    
    # Find all audio files
    audio_files = []
    for ext in SUPPORTED_EXTENSIONS:
        audio_files.extend(dir_path.rglob(f"*{ext}"))
        audio_files.extend(dir_path.rglob(f"*{ext.upper()}"))
    
    # Remove duplicates (from case variations)
    audio_files = list(set(audio_files))
    audio_files.sort()
    
    print(f"\nFound {len(audio_files)} audio file(s) in '{directory}'\n")
    
    for filepath in audio_files:
        result = process_file(str(filepath))
        if result.success:
            successful.append(result)
        else:
            failed.append(result)
    
    return successful, failed


def print_dry_run_report(successful, failed, source_dir, output_dir):
    """Print a detailed report of what would happen"""
    
    # Separate sanitized from clean
    sanitized = [r for r in successful if r.was_sanitized]
    clean = [r for r in successful if not r.was_sanitized]
    
    print("=" * 70)
    print("DRY RUN REPORT")
    print("=" * 70)
    print(f"  Source:  {source_dir}")
    print(f"  Output:  {output_dir}")
    print(f"  Failed:  {Path(output_dir) / '_failed'}")
    print(f"  Format:  {FILENAME_FORMAT}")
    
    if clean:
        print(f"\n✓ CLEAN FILES ({len(clean)}):")
        print("-" * 70)
        # Show first 10
        for result in clean[:10]:
            old_name = Path(result.original_path).name
            print(f"  {old_name}")
            print(f"    → {result.new_name}")
        if len(clean) > 10:
            print(f"  ... and {len(clean) - 10} more clean files")
    
    if sanitized:
        print(f"\n⚠ SANITIZED FILES ({len(sanitized)}):")
        print("-" * 70)
        for result in sanitized:
            old_name = Path(result.original_path).name
            print(f"  {old_name}")
            for field, (orig, sani) in result.sanitize_details.items():
                print(f"    {field}: \"{orig}\"")
                print(f"         → \"{sani}\"")
            print(f"    → {result.new_name}")
            print()
    
    if failed:
        print(f"\n✗ FAILED FILES ({len(failed)}):")
        print("-" * 70)
        for result in failed:
            old_name = Path(result.original_path).name
            print(f"  {old_name}")
            print(f"    Reason: {result.reason}")
            print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Clean:     {len(clean)}")
    print(f"  Sanitized: {len(sanitized)}")
    print(f"  Failed:    {len(failed)}")
    print(f"  Total:     {len(successful)} success, {len(failed)} failed")
    
    print(f"\nTo execute, set DRY_RUN = False and run again.")
    print()


def execute_copy_rename(successful, failed, output_dir):
    """Copy files to output directory with new names"""
    
    output_path = Path(output_dir)
    failed_path = output_path / "_failed"
    
    copied_count = 0
    sanitized_count = 0
    failed_count = 0
    errors = []
    
    # Create output directories
    if not output_path.exists():
        output_path.mkdir(parents=True)
        print(f"Created output directory: {output_path}")
    
    if failed and not failed_path.exists():
        failed_path.mkdir(parents=True)
        print(f"Created failed directory: {failed_path}")
    
    # Copy and rename successful files
    print("\nCopying and renaming files...")
    for result in successful:
        src_path = Path(result.original_path)
        dest_path = output_path / result.new_name
        
        try:
            # Handle name collision
            if dest_path.exists():
                base = dest_path.stem
                ext = dest_path.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = output_path / f"{base} ({counter}){ext}"
                    counter += 1
                print(f"  ⚠ Collision: {result.new_name} → {dest_path.name}")
            
            shutil.copy2(str(src_path), str(dest_path))
            copied_count += 1
            
            if result.was_sanitized:
                sanitized_count += 1
                print(f"  ⚠ {src_path.name} → {dest_path.name}")
            else:
                print(f"  ✓ {src_path.name} → {dest_path.name}")
                
        except Exception as e:
            errors.append(f"Failed to copy {src_path.name}: {str(e)}")
    
    # Copy failed files
    if failed:
        print("\nCopying failed files to _failed/...")
        for result in failed:
            src_path = Path(result.original_path)
            dest_path = failed_path / src_path.name
            
            try:
                if dest_path.exists():
                    base = dest_path.stem
                    ext = dest_path.suffix
                    counter = 1
                    while dest_path.exists():
                        dest_path = failed_path / f"{base} ({counter}){ext}"
                        counter += 1
                
                shutil.copy2(str(src_path), str(dest_path))
                failed_count += 1
                print(f"  → {src_path.name} ({result.reason})")
            except Exception as e:
                errors.append(f"Failed to copy {src_path.name}: {str(e)}")
    
    # Summary
    print("\n" + "=" * 70)
    print("EXECUTION COMPLETE")
    print("=" * 70)
    print(f"  Copied & renamed: {copied_count}")
    print(f"    - Clean:        {copied_count - sanitized_count}")
    print(f"    - Sanitized:    {sanitized_count}")
    print(f"  Copied to failed: {failed_count}")
    print(f"\n  Original files were NOT modified.")
    
    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for error in errors:
            print(f"    - {error}")
    
    print()


def main():
    source_dir = Path(TARGET_PATH)
    output_dir = Path(OUTPUT_PATH)
    dry_run = DRY_RUN
    
    # Resolve relative paths
    if not source_dir.is_absolute():
        source_dir = Path.cwd() / source_dir
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    
    print(f"\nMusic File Renamer (Auto-Sanitize)")
    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")
    print(f"Mode:   {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"Format: {FILENAME_FORMAT}")
    
    # Scan and process
    successful, failed = scan_directory(source_dir)
    
    if not successful and not failed:
        print("\nNo audio files found.")
        return
    
    if dry_run:
        print_dry_run_report(successful, failed, source_dir, output_dir)
    else:
        execute_copy_rename(successful, failed, output_dir)


if __name__ == '__main__':
    main()
