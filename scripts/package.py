"""Package tracked source and compiled UI without secrets, caches or Git internals."""
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    dist = ROOT / 'frontend/dist'
    if not (dist / 'index.html').exists():
        raise SystemExit('Build frontend first: npm --prefix frontend run build')
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    files = {ROOT / p for p in tracked if p}
    files.update(p for p in dist.rglob('*') if p.is_file())
    output = ROOT / 'artifacts/find-my-bug.zip'
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(files):
            relative = file.relative_to(ROOT)
            if not file.is_file() or file.is_symlink():
                continue
            if any(part in {'.git', 'node_modules', '__pycache__', '.venv', 'artifacts', 'test-results'}
                   or part.startswith('.env') for part in relative.parts):
                continue
            archive.write(file, Path('find-my-bug') / relative)
    print(f'{output} ({output.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
