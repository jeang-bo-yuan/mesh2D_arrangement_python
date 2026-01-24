import arrangement2D.config as cfg
cfg.DEBUG = True
cfg.DEBUG_PLOT = True

from arrangement2D.arrangement2D import arrangement2D_polygons
from shapely import Polygon

arrangement2D_polygons([
    Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
    Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)])
])

arrangement2D_polygons([
    Polygon([(0, 0), (4, 0), (4, 4), (0, 4)]),
    Polygon([(1, 1), (2, 1), (2, 2), (1, 2)])
])
