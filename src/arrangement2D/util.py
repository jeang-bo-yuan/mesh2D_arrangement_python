import shapely

def triangulate(polygons: list[shapely.Polygon]) -> list[shapely.Polygon]:
    return shapely.get_parts(
        shapely.constrained_delaunay_triangles(
            shapely.MultiPolygon(polygons)
        )
    ).tolist()
