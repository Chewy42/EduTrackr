from pathlib import Path

from app.scrapers import scrape_chapman_coursicle


def test_output_path_uses_single_backend_segment() -> None:
    path = scrape_chapman_coursicle.get_output_path()
    assert path.name.startswith("chapman_coursicle_")
    assert path.suffix == ".csv"
    backend_segments = [part for part in path.parts if part == "backend"]
    assert len(backend_segments) == 1
    assert "backend" in path.parts
    assert "data" in path.parts
