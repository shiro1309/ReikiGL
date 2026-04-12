from typing import List, Optional, Tuple, Dict, TypedDict, NotRequired, cast
import json
import numpy as np
import numpy.typing as npt
import os

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

def obj_l(file_path: str) -> Tuple[List[float], List[int]]:
    raw_pos: List[List[float]] = [] 
    raw_uv:  List[List[float]] = [] 
    raw_nrm: List[List[float]] = [] 
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
    
    mesh_table, indices = build_indexed_mesh(all_triangles)

    # Convert to numpy for indexing speed
    np_pos = np.array(raw_pos, dtype='f4')
    np_uv  = np.array(raw_uv, dtype='f4') if raw_uv else np.zeros((len(np_pos), 2), dtype='f4')
    np_nrm = np.array(raw_nrm, dtype='f4') if raw_nrm else np.zeros((len(np_pos), 3), dtype='f4')

    v_idxs, vt_idxs, vn_idxs = mesh_table[:, 0], mesh_table[:, 1], mesh_table[:, 2]

    # Map the data
    final_pos = np_pos[v_idxs]
    final_uv  = np_uv[vt_idxs]
    final_nrm = np_nrm[vn_idxs]

    # 1. Create the (N, 8) packed array [Pos(3), UV(2), Norm(3)]
    packed_data = np.hstack([final_pos, final_uv, final_nrm]).astype('f4')

    # 2. Flatten to list to match create_icosphere_fast output
    final_vertices = packed_data.ravel().tolist()
    
    # 3. Ensure indices is a flat list of unsigned ints
    final_indices = np.array(indices, dtype='u4').ravel().tolist()

    return final_vertices, final_indices




def load_mtl_color(file_path: str) -> List[float]:
    """Helper to find and parse the diffuse color (Kd) from a .mtl file."""
    mtl_path = os.path.splitext(file_path)[0] + ".mtl"
    default_white = [1.0, 1.0, 1.0, 1.0] # RGBA
    
    if not os.path.exists(mtl_path):
        return default_white

    try:
        with open(mtl_path, "r") as f:
            for line in f:
                parts = line.split()
                if not parts: continue
                # Kd is the diffuse color in MTL files
                if parts[0] == "Kd":
                    r, g, b = float(parts[1]), float(parts[2]), float(parts[3])
                    return [r, g, b, 1.0] # Return with full alpha
    except Exception:
        pass
        
    return default_white

def obj_c(file_path: str) -> Tuple[List[float], List[int]]:
    raw_pos: List[List[float]] = [] 
    raw_uv:  List[List[float]] = [] 
    raw_nrm: List[List[float]] = [] 
    all_triangles = []

    # Get the color once from the .mtl or default to white
    diffuse_color = load_mtl_color(file_path)

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
                # Assuming parse_obj_face is defined elsewhere in your scope
                all_triangles.extend(parse_obj_face(line))
    
    mesh_table, indices = build_indexed_mesh(all_triangles)

    # Convert to numpy
    np_pos = np.array(raw_pos, dtype='f4')
    np_uv  = np.array(raw_uv, dtype='f4') if raw_uv else np.zeros((len(np_pos), 2), dtype='f4')
    np_nrm = np.array(raw_nrm, dtype='f4') if raw_nrm else np.zeros((len(np_pos), 3), dtype='f4')

    v_idxs, vt_idxs, vn_idxs = mesh_table[:, 0], mesh_table[:, 1], mesh_table[:, 2]

    # Map the data
    final_pos = np_pos[v_idxs]
    final_uv  = np_uv[vt_idxs]
    final_nrm = np_nrm[vn_idxs]

    # 1. Create the Color array (N vertices x 4 channels)
    # We broadcast the single diffuse_color across all vertex rows
    num_vertices = len(final_pos)
    final_col = np.tile(np.array(diffuse_color, dtype='f4'), (num_vertices, 1))

    # 2. Create the (N, 12) packed array [Pos(3), UV(2), Norm(3), Color(4)]
    packed_data = np.hstack([final_pos, final_uv, final_nrm, final_col]).astype('f4')

    # 3. Flatten
    final_vertices = packed_data.ravel().tolist()
    final_indices = np.array(indices, dtype='u4').ravel().tolist()

    return final_vertices, final_indices


class RawMaterial(TypedDict):
    name: str

    Ns: NotRequired[float]
    Ka: NotRequired[list[float]]
    Kd: NotRequired[list[float]]
    Ks: NotRequired[list[float]]
    Ke: NotRequired[list[float]]

    Ni: NotRequired[float]
    d: NotRequired[float]
    illum: NotRequired[int]

class Material(TypedDict):
    name: str

    specular_exponent: NotRequired[float]

    ambient_color: NotRequired[tuple[float, float, float]]
    diffuse_color: NotRequired[tuple[float, float, float]]
    specular_color: NotRequired[tuple[float, float, float]]
    emissive_color: NotRequired[tuple[float, float, float]]

    optical_density: NotRequired[float]
    alpha: NotRequired[float]
    illumination_model: NotRequired[int]

def to_vec3(values: list[float]) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"Expected 3 values, got {len(values)}")
    return (values[0], values[1], values[2])

def convert_material(raw: RawMaterial) -> Material:
    material: Material = {
        "name": raw["name"],
    }

    if "Ns" in raw: material["specular_exponent"] = raw["Ns"]

    if "Ka" in raw: material["ambient_color"] = to_vec3(raw["Ka"])
    if "Kd" in raw: material["diffuse_color"] = to_vec3(raw["Kd"])
    if "Ks" in raw: material["specular_color"] = to_vec3(raw["Ks"])
    if "Ke" in raw: material["emissive_color"] = to_vec3(raw["Ke"])

    if "Ni" in raw: material["optical_density"] = raw["Ni"]
    if "d" in raw: material["alpha"] = raw["d"]
    if "illum" in raw: material["illumination_model"] = raw["illum"]

    return material

def convert_materials(rawMaterials: Dict[str, RawMaterial]) -> Dict[str, Material]:
    new_materials: Dict[str, Material] = {}
    for name, data in rawMaterials.items():
        new_materials[name] = convert_material(data)
    
    return new_materials

def material_to_rgba(mat: Material | None):
    if not mat:
        return (1.0, 1.0, 1.0, 1.0)

    r, g, b = mat.get("diffuse_color", (1.0, 1.0, 1.0))
    a = mat.get("alpha", 1.0)

    return (r, g, b, a)

# will just load in the material and send it back to the main function to be used and not applied
def load_mtl_materials(path: str) -> Optional[Dict[str, Material]]:
    mtl_path = os.path.splitext(path)[0] + ".mtl"
    if not os.path.exists(mtl_path):
        return None
    
    current_material: RawMaterial | None = None
    materials: Dict[str, RawMaterial] = {}
    
    try:
        with open(mtl_path, "r") as file:
            for line in file:
                parts = line.split()
                if not parts: continue

                prefix = parts[0]
                match prefix:
                    case "newmtl":
                        name = parts[1]
                        current_material = {"name": name}
                        materials[name] = current_material

                    case "Kd" if current_material:
                        current_material["Kd"] = list(map(float, parts[1:]))

                    case "Ks" if current_material:
                        current_material["Ks"] = list(map(float, parts[1:]))

                    case "Ke" if current_material:
                        current_material["Ke"] = list(map(float, parts[1:]))

                    case "Ni" if current_material:
                        current_material["Ni"] = float(parts[1])

                    case "d" if current_material:
                        current_material["d"] = float(parts[1])

                    case "illum" if current_material:
                        current_material["illum"] = int(parts[1])

        return convert_materials(materials)

    except Exception:
        return None

def parse_obj_face_color(line: str, color: Tuple[float, float, float, float]) -> Tuple[List[List[Tuple[int, int, int]]], List[Tuple[float, float, float, float]]]:
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
    colors = []
    for i in range(1, len(verts) - 1):
        triangles.extend([verts[0], verts[i], verts[i + 1]])
        colors.extend([color, color, color])

    return triangles, colors

def parse_obj_face_colorid(line: str, color: int) -> List[List[Tuple[int, int, int, int]]]:
    parts = line.split()[1:]
    verts: List[Tuple[int, int, int, int]] = []

    for p in parts:
        segments = p.split("/")

        v = int(segments[0]) - 1
        vt = int(segments[1]) - 1 if len(segments) > 1 and segments[1] else -1
        vn = int(segments[2]) - 1 if len(segments) > 2 and segments[2] else -1
        verts.append((v, vt, vn, color))

    # Triangulate using fan method
    triangles = []
    for i in range(1, len(verts) - 1):
        triangles.extend([verts[0], verts[i], verts[i + 1]])

    return triangles

def obj_color(path: str) -> Tuple[List, List]:
    raw_pos:    List[List[float]] = [] 
    raw_uv:     List[List[float]] = [] 
    raw_nrm:    List[List[float]] = [] 
    
    all_color = []
    all_triangles = []
    current_material = None
    colors = []
    material_to_id: dict = {}
    active_id = 0

    materials : Optional[Dict[str, Material]] = load_mtl_materials(path)
    if materials:
        n = 0
        for name, data in materials.items():
            colors.append(material_to_rgba(data))

            material_to_id[name] = n

            n += 1
        
    else:
        colors.append((1.0, 1.0, 1.0, 1.0))
    print(colors, material_to_id)
            

    with open(path, "r") as f:
        for line in f:
            parts = line.split()
            if not parts: 
                continue

            prefix = parts[0]

            # --- vertices ---
            if prefix == "v":
                raw_pos.append([float(parts[1]), float(parts[2]), float(parts[3])])

            elif prefix == "vn":
                raw_nrm.append([float(parts[1]), float(parts[2]), float(parts[3])])

            elif prefix == "vt":
                raw_uv.append([float(parts[1]), float(parts[2])])
            
            # --- material switch ---
            elif prefix == "usemtl":
                if materials:
                    current_material = materials.get(parts[1])
                else:
                    current_material = None
            
            elif prefix == "f":
                if current_material:
                    name = current_material["name"]
                    active_id = material_to_id[name]
                    all_triangles.extend(parse_obj_face_colorid(line, active_id))
                else:
                    all_triangles.extend(parse_obj_face_colorid(line, active_id))
    
    mesh_table, indices = build_indexed_mesh(all_triangles)

    np_pos = np.array(raw_pos, dtype='f4')
    np_uv  = np.array(raw_uv, dtype='f4') if raw_uv else np.zeros((1, 2), dtype='f4')
    np_nrm = np.array(raw_nrm, dtype='f4') if raw_nrm else np.zeros((1, 3), dtype='f4')
    np_colors = np.array(colors, dtype="f4")

    v_idxs, vt_idxs, vn_idxs, c_idxs = mesh_table[:, 0], mesh_table[:, 1], mesh_table[:, 2], mesh_table[:, 3]

    final_pos = np_pos[v_idxs]
    final_uv  = np_uv[vt_idxs]
    final_nrm = np_nrm[vn_idxs]
    final_col = np_colors[c_idxs]

    packed_data = np.hstack([final_pos, final_uv, final_nrm, final_col], dtype="f4")

    # 2. Flatten to list to match create_icosphere_fast output
    final_vertices = packed_data.ravel().tolist()
    
    # 3. Ensure indices is a flat list of unsigned ints
    final_indices = np.array(indices, dtype='u4').ravel().tolist()

    return final_vertices, final_indices



            
