from src.domain.models import BoundingBox


def test_bounding_box_dimensions_and_center():
    bbox = BoundingBox(page=1, x0=100.0, y0=200.0, x1=300.0, y1=400.0)
    assert bbox.width == 200.0
    assert bbox.height == 200.0
    assert bbox.center == (200.0, 300.0)


def test_bounding_box_distance_same_page():
    bbox1 = BoundingBox(page=1, x0=0.0, y0=0.0, x1=10.0, y1=10.0)  # center (5, 5)
    bbox2 = BoundingBox(page=1, x0=30.0, y0=40.0, x1=40.0, y1=50.0)  # center (35, 45)

    # dx = 30, dy = 40 -> distance = 50.0
    dist = bbox1.distance_to(bbox2)
    assert round(dist, 1) == 50.0


def test_bounding_box_distance_different_pages():
    bbox1 = BoundingBox(page=1, x0=0.0, y0=0.0, x1=10.0, y1=10.0)
    bbox2 = BoundingBox(page=2, x0=0.0, y0=0.0, x1=10.0, y1=10.0)
    assert bbox1.distance_to(bbox2) == float("inf")
