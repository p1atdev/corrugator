from pathlib import Path


def load_file_lines(file: str | Path) -> list[str]:
    with open(file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip() != ""]
