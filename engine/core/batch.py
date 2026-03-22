import numpy as np
import moderngl as mgl
from typing import Tuple, cast


import struct

class Batch3D:
    def __init__(self, ctx: mgl.Context, program: mgl.Program,
                 fmt: str, attrs: Tuple[str, ...]) -> None:

        self.ctx = ctx
        self.program = program
        self.fmt = fmt
        self.attrs = attrs

        self.vertex_data = []
        self.index_data = []
        self.meshes = {}   # stores: first_index, count, model_matrix
        self.meshes2 = {}
        self.uniqe_counter = 0
        self.max_meshes = 12000

        # compute float stride
        #self.stride = sum(int(x[0]) for x in fmt.split() if 'x' not in x)


    def add_mesh(self, vao_data, indices) -> str:
        """
        vao_data: flat interleaved vertex list (float32) (vx, vy, vz, uvx, uvy, nx, ny, xz)
        indices: integer list
        """

        start_vertex = len(self.vertex_data)
        shifted = [i + start_vertex for i in indices]

        # record mesh info
        self.meshes[str(self.uniqe_counter)] = {
            "first_index": len(self.index_data),
            "count": len(indices),
            "model": np.eye(4, dtype="f4"),  # default transform
            "visible": True,
            "wireframe": False,
        }
        self.uniqe_counter += 1

        # append vertex/index data
        self.vertex_data.extend(vao_data)
        self.index_data.extend(shifted)

        return str(self.uniqe_counter - 1)
    
    def add_instance(self, original_mesh_id: str) -> str:
        
        original = self.meshes[original_mesh_id]
    
        # Lag en kopi av verdiene som definerer geometrien
        mesh_info = {
            "first_index": original["first_index"],
            "count": original["count"],
            "model": np.eye(4, dtype="f4"),
            "visible": True,
            "wireframe": False,
        }

        #self.meshes.append(mesh_info)
        self.meshes[str(self.uniqe_counter)] = mesh_info
        self.uniqe_counter += 1
        return str(self.uniqe_counter - 1)
    
    def remove_instance(self, original_mesh_id) -> None:
        self.meshes.pop(original_mesh_id)


    def set_model(self, mesh_id: str, model_matrix: np.ndarray):
        #self.meshes[mesh_id]["model"] = model_matrix
        self.meshes[mesh_id]["model"] = model_matrix

    def hide_mesh(self, mesh_id: int):
        self.meshes[mesh_id]["visible"] = False

    def remove_mesh(self):
        pass

    def remove_meshes(self):
        pass


    def build(self) -> None:
        self.vbo = self.ctx.buffer(np.array(self.vertex_data, dtype="f4").tobytes())
        self.ibo = self.ctx.buffer(np.array(self.index_data, dtype="i4").tobytes())

        mesh_colors = np.array([
            [1.0, 0.0, 0.0, 1.0], 
            [0.0, 0.0, 1.0, 1.0],
            [0.7, 0.7, 0.8, 1.0]
        ], dtype=np.float32)

        # 2. Lag buffer og bind til binding=1 (eksempel for ModernGL)
        color_ssbo = self.ctx.buffer(mesh_colors.tobytes())
        color_ssbo.bind_to_storage_buffer(1)

        
        self.mesh_id_data = np.arange(self.max_meshes, dtype='i4')
        self.mesh_id_buffer = self.ctx.buffer(self.mesh_id_data.tobytes())

        # single VAO for everything
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, self.fmt, *self.attrs),
             (self.mesh_id_buffer, '1i /i', 'in_mesh_id')],
            self.ibo,
            index_element_size=4
        )

        self.matrix_buffer = self.ctx.buffer(reserve=len(self.meshes) * 64)
        self.matrix_buffer.bind_to_storage_buffer(0)

        # Each command is 5 unsigned ints (20 bytes)
        self.indirect_buffer = self.ctx.buffer(reserve=len(self.meshes) * 20)

    
    def draw(self, camera) -> None:
        P = camera.get_projection_matrix()  # 4×4
        V = camera.get_view_matrix()      # 4×4

        VP = P @ V

        if "u_view_projection" in self.program:
            vp_data = cast(mgl.Uniform, self.program["u_view_projection"])
            vp_data.write(VP.T.astype('f4').tobytes())

        for name, data in self.meshes.items():
            if not data["visible"]:
                continue

            m_data = data["model"].astype('f4').T.tobytes()
            self.matrix_buffer.write(m_data, offset=0)
            
            if data["wireframe"]:
                self.ctx.wireframe = True
                self.ctx.disable(mgl.CULL_FACE)
            else:
                self.ctx.wireframe = False
                self.ctx.enable(mgl.CULL_FACE)

            self.vao.render(
                mode=self.ctx.TRIANGLES,
                vertices=data["count"],
                first=data["first_index"],
            )
            self.ctx.enable(mgl.CULL_FACE)
        
        self.ctx.wireframe = False
        self.ctx.enable(mgl.CULL_FACE)
        self.ctx.finish() 


    def draw_fast(self, camera) -> None:
        solid_comands = []

        wire_comands = []
        matrix = []
        active_meshes = 0

        # --- partition meshes

        for name, data in self.meshes.items():
            if not data["visible"]:
                continue
            
            # the actual model data per mesh
            m_data = data["model"].T.astype("f4").tobytes()
            
            cmd = struct.pack('5i', 
                data["count"], 
                1, 
                data["first_index"],
                0, 
                active_meshes
            )
            
            # the model data gets added to its coresponding area wirefram or solid
            # the cmd data is the "comands" or the info the shader goes from
            if data["wireframe"]:
                matrix.append(m_data)
                wire_comands.append(cmd)
            else:
                matrix.append(m_data)
                solid_comands.append(cmd)

            active_meshes += 1

        if active_meshes == 0:
            return
        
        all_matrices = b''.join(matrix)
        self.matrix_buffer.write(all_matrices)

        vp = camera.get_projection_matrix() @ camera.get_view_matrix()
        vp_data = cast(mgl.Uniform, self.program["u_view_projection"])
        vp_data.write(vp.T.astype('f4').tobytes())
        
        if solid_comands:
            self.ctx.wireframe = False
            self.ctx.enable(mgl.CULL_FACE)

            tmp_indirect = self.ctx.buffer(b''.join(solid_comands))
            self.vao.render_indirect(tmp_indirect, count=len(solid_comands))
        
        if wire_comands:
            self.ctx.wireframe = True
            self.ctx.disable(mgl.CULL_FACE)

            tmp_indirect = self.ctx.buffer(b''.join(wire_comands))
            self.vao.render_indirect(tmp_indirect, count=len(wire_comands))
            