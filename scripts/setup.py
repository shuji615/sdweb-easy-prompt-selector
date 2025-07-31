from pathlib import Path
import os

def write_filename_list():
    """Generate tmp/easyPromptSelector.txt listing all YAML tag files for Easy Prompt Selector JS side.
    The file is written at the WebUI root path (same directory where webui.py resides) inside a `tmp` folder.
    Each line contains a POSIX-style relative path from the WebUI root so that the front-end can fetch it
    using the `file=` URL convention.
    """
    try:
        # Determine the WebUI root directory (two levels up from this file: scripts/ -> extension root -> webui root)
        extension_root = Path(__file__).resolve().parent.parent
        webui_root = extension_root.parent.parent  # stable-diffusion-webui root

        tags_dir = extension_root / 'tags'
        if not tags_dir.exists():
            print(f"[EasyPromptSelector] Tags directory not found: {tags_dir}")
            return

        tmp_dir = webui_root / 'tmp'
        tmp_dir.mkdir(parents=True, exist_ok=True)
        output_file = tmp_dir / 'easyPromptSelector.txt'

        # Collect YAML file paths relative to the webui root so JS can fetch with file=<path>
        yaml_paths = [p.relative_to(webui_root).as_posix() for p in tags_dir.rglob('*.yml')]

        # Write list
        output_file.write_text('\n'.join(yaml_paths), encoding='utf-8')
        print(f"[EasyPromptSelector] Wrote {len(yaml_paths)} tag file paths to {output_file}")
    except Exception as e:
        print(f"[EasyPromptSelector] Failed to write filename list: {e}")
