from shapely.geometry import LineString, Point, Polygon
import shapely.ops
from shapely.plotting import *
import shapely

import time

from joblib import Parallel, delayed
import math

from .config import *
if ARRANGEMENT_DEBUG:
    import matplotlib.pyplot as plt
    import time

#region Utility #####################################################################################################################
def sorted_tuple(t0, t1):
    if t0 <= t1:
        return (t0, t1)
    else:
        return (t1, t0)
    

#endregion

#region 找交點 #########################################################################################################################
def find_intersections(edges: list[RAW_EDGE_TYPE], pairs: list[tuple[int, int]]) -> list[tuple[int, int, RAW_POINT_TYPE]]:
    """
    輸入一堆線的端點（edges）和要比較的兩條線的 index（pairs），回傳 [(i, j, (x, y)), ...] 代表 edges[i] 和 edges[j] 相交於 (x, y)
    """
    from shapely import LineString

    result = []
    for (i, j) in pairs:
        inter = LineString(edges[i]).intersection(LineString(edges[j]))

        if isinstance(inter, Point) or isinstance(inter, LineString):
            # 有兩種可能：相交一點，交於一線
            for co in inter.coords:
                result.append((i, j, co))

    return result
    
def find_line_points_parallel(edges: list[RAW_EDGE_TYPE], chunk_size: int = 10000) -> tuple[list[RAW_POINT_TYPE], list[list[int]]]:
    """
    求出每條線段和其他線段的交點，line_points[i] = [起點, 終點 (, 分割點 ...)]
    
    :return: (vertices, line_points)
    :rtype: tuple[list[RAW_POINT_TYPE], list[list[int]]]
    """
    lines = [LineString(e) for e in edges]
    # 建立空間索引
    tree = shapely.STRtree(lines)

    if ARRANGEMENT_DEBUG:
        start = time.perf_counter()
    #############################################################################################################
    # 第一步: 對於每條直線，去和其他可能相交的線求出交點並記錄
    #############################################################################################################
    pairs = tree.query(lines) # pairs[0, i] 和 pairs[1, i] 為相交的兩線
    unique_pairs: list[tuple[int, int]] = [(pairs[0, i], pairs[1, i])       # 取出那一欄的兩個 index
                                            for i in range(pairs.shape[1])  # 對於每一欄
                                            if pairs[0, i] < pairs[1, i]]   # (a, b) 為一對則 (b, a) 也是，留一個就好
    
    if len(unique_pairs) > 3 * chunk_size:
        # 將 unique_pairs 拆成數個 chunk，每個 chunk 平行處理
        intersections : list[list[tuple[int, int, RAW_POINT_TYPE]]] = Parallel(-1)(
            delayed(find_intersections)(edges, unique_pairs[i * chunk_size : i * chunk_size + chunk_size])
                for i in range(math.ceil(len(unique_pairs) / chunk_size))
        )
    else:
        intersections : list[list[tuple[int, int, RAW_POINT_TYPE]]] = [find_intersections(edges, unique_pairs)]

    if ARRANGEMENT_DEBUG:
        end = time.perf_counter()
        print(f"#Unique Edge Pairs: {len(unique_pairs)}")
        print(f"Find Intersections: {end - start}")

    #############################################################################################################
    # 第二步: 將所有求出的交點記在 line_points
    #############################################################################################################
    # 每個線由哪些點組成
    #   line_points[i] = [起點index, 終點index(, 分割點...)]
    line_points : list[list[int]] = [[] for _ in range(len(edges))]
    # 所有頂點的座標
    vertices : list[tuple[float, float]] = []
    # 從頂點座標查 index
    vertex_index_lookup : dict[tuple[int, int], int] = dict()
    
    def getVertIndex(p: tuple[float, float]) -> int:
        if p in vertex_index_lookup.keys():
            return vertex_index_lookup[p]
        else:
            vertices.append(p) # 插入頂點
            vertex_index_lookup[p] = len(vertices) - 1 # 記錄 index
            return len(vertices) - 1

    # 加入 起點 / 終點
    for i in range(len(edges)):
        line_points[i].append(getVertIndex(edges[i][0])) # 起點 / 終點
        line_points[i].append(getVertIndex(edges[i][1]))

    # 加入其他交點
    for subResult in intersections:
        for i, j, co in subResult:
            Index = getVertIndex(co)
            line_points[i].append(Index)
            line_points[j].append(Index)

    return vertices, line_points
#endregion

#region ArrangeMent 的兩大步驟 ##################################################################################
def split_edges(edges: list[RAW_EDGE_TYPE]) -> list[RAW_EDGE_TYPE]:
    """
    輸入一堆線，將這些線在彼此相交處分割，回傳分割後的線
    """
    # 先找每個線的交點
    vertices, line_points = find_line_points_parallel(edges)

    result_edges : set[RAW_POINT_TYPE]= set()

    if ARRANGEMENT_DEBUG:
        start_perf = time.perf_counter()

    # 對於每個線條進行分割
    for i in range(len(edges)):
        start, end = line_points[i][:2]
        split_points = list(set(line_points[i]) - {start, end})

        if len(split_points) == 0:
            result_edges.add(sorted_tuple(start, end))
            continue

        # 基於方法 4: https://gis.stackexchange.com/a/203068/339861
        start_co, end_co = vertices[start], vertices[end]
        line = LineString([start_co, end_co])

        # 將所有分割點投影到線段上，按分割點距離起點的距離進行排列
        split_dist = [line.project(Point(vertices[vertex_index])) for vertex_index in split_points]
        split_points, split_dist = zip(*sorted(zip(split_points, split_dist), key=lambda x: x[1]))

        # 加入 (起點, 分割點0)、（起點, 分割點-1）
        result_edges.add(sorted_tuple(start, split_points[0]))
        result_edges.add(sorted_tuple(split_points[-1], end))

        for splitI in range(1, len(split_points)):
            result_edges.add(sorted_tuple(split_points[splitI - 1], split_points[splitI]))

    if ARRANGEMENT_DEBUG:
        print(f"#Vertices = {len(vertices)}")
        print(f"#Edges (after split) = {len(result_edges)}")
        end_perf = time.perf_counter()
        print(f"Split Edges: {end_perf - start_perf}")

        if ARRANGEMENT_DEBUG_PLOT:
            from shapely import MultiLineString
            plot_line(MultiLineString([(vertices[i], vertices[j]) for (i, j) in result_edges]))
            plt.title("Line works")
            plt.show()

    return [(vertices[i], vertices[j]) for (i, j) in result_edges]

def polygonize_edges(edges: list[RAW_EDGE_TYPE]) -> list[Polygon]:
    """
    將這些邊連成數個 Polygon
    """
    if ARRANGEMENT_DEBUG:
        start = time.perf_counter()

    lines = [LineString(e) for e in edges]
    polygons = shapely.get_parts(shapely.ops.polygonize(lines)).tolist()

    # triangles = []
    # for P in polygons:
    #     triangles += shapely.get_parts(shapely.constrained_delaunay_triangles(P)).tolist()

    if ARRANGEMENT_DEBUG:
        end = time.perf_counter()
        print(f"Polygonize and Delaunay: {end - start}")
        print(f"#Result Polygons: {len(polygons)}")

        if ARRANGEMENT_DEBUG_PLOT:
            for tri in polygons:
                plot_polygon(tri, add_points=False)
            plt.title("Arrangement")
            plt.show()

    return polygons
#endregion

#region Arrangement
def arrangement2D(raw_edges: list[RAW_EDGE_TYPE]) -> list[Polygon]:
    """
    輸入一堆 Polygon 的邊，將 Polygon 圍出的範圍做細分，每一個細分出的區塊彼此不重疊
    """
    if ARRANGEMENT_DEBUG:
        print("\n\n== arrangement 2D ==")
    
    # Step1. 分割 Edge Soup
    raw_edges = split_edges(raw_edges)
    # Step2. 把 Edgs Soup 轉回 Polygon 再對每個 Polygon 三角化
    polygons = polygonize_edges(raw_edges)

    return polygons

def arrangement2D_polygons(polygons: list[Polygon]) -> list[Polygon]:
    edges = []

    for poly in polygons:
        for i in range(1, len(poly.exterior.coords)):
            edges.append((poly.exterior.coords[i - 1], poly.exterior.coords[i]))

    return arrangement2D(edges)

#endregion
