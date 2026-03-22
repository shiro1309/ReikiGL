from typing import List, Optional, Tuple
import numpy as np
import numpy.typing as npt

FaceVert = Tuple[int, Optional[int], Optional[int]]
arr: npt.NDArray[np.float32]

def parse_obj_face(line: str) -> List[List[Tuple[int, int, int]]]:
    """
    Parse a single OBJ face line:
        f 1/1/1 2/2/1 4/3/1 3/4/1
    Supports:
        - missing UVs or normals (1//1, 1/2, 1)
        - unlimited vertices (n-gons)
    Returns:
        A list of triangles. Each triangle is a list of:
        (v_idx, vt_idx, vn_idx)
    """

    parts = line.split()[1:]
    verts: List[Tuple[int, int, int]] = []

    for p in parts:
        segments = p.split("/")

        v = int(segments[0]) - 1
        vt = int(segments[1]) - 1 if len(segments) > 1 and segments[1] else -1
        vn = int(segments[2]) - 1 if len(segments) > 2 and segments[2] else -1
        verts.append((v, vt, vn))

    # Triangulate using fan method
    triangles = []
    for i in range(1, len(verts) - 1):
        triangles.extend([verts[0], verts[i], verts[i + 1]])

    return triangles

def build_indexed_mesh(triangles_list: List[Tuple[int, int, int]]) -> Tuple[np.ndarray, np.ndarray]:

    np_triangles = np.array(triangles_list, dtype='i4')

    unique_verts, indices = np.unique(np_triangles, axis=0, return_inverse=True)

    return unique_verts.astype("i4"), indices.astype("i4")

def obj(file_path: str) -> Tuple[npt.NDArray[np.float32], npt.NDArray[np.int32]]:
    raw_pos: List[List[float]] = [] # v
    raw_uv:  List[List[float]] = [] # vt
    raw_nrm: List[List[float]] = [] # vn
    all_triangles = []

    with open(file_path, "r") as f:
        for line in f:
            parts = line.split()
            if not parts: continue

            prefix = parts[0]
            if prefix == "v":
                raw_pos.append([float(parts[1]), float(parts[2]), float(parts[3])])

            elif prefix == "vn":
                raw_nrm.append([float(parts[1]), float(parts[2]), float(parts[3])])

            elif prefix == "vt":
                raw_uv.append([float(parts[1]), float(parts[2])])

            elif prefix == "f":
                all_triangles.extend(parse_obj_face(line))
    
    mesh_table, indicies = build_indexed_mesh(all_triangles)

    # making the raw data into numpy arrays for pure speed
    np_pos = np.array(raw_pos, dtype='f4')
    np_uv  = np.array(raw_uv, dtype='f4') if raw_uv else np.zeros((1, 2), dtype='f4')
    np_nrm = np.array(raw_nrm, dtype='f4') if raw_nrm else np.zeros((1, 3), dtype='f4')

    v_idxs, vt_idxs, vn_idxs = mesh_table[:, 0], mesh_table[:, 1], mesh_table[:, 2]

    final_pos = np_pos[v_idxs]
    final_uv  = np_uv[vt_idxs]
    final_nrm = np_nrm[vn_idxs]

    vao_data = np.hstack([final_pos, final_uv, final_nrm], dtype="f4")

    return vao_data, indicies