import numpy as np
import moderngl as mgl
from typing import Tuple, cast
from .camera import BaseCamera

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

        self.color_buffer = self.ctx.buffer(reserve=self.max_meshes * 16)
        self.color_buffer.bind_to_storage_buffer(1)


        # compute float stride
        #self.stride = sum(int(x[0]) for x in fmt.split() if 'x' not in x)


    def add_mesh(self, vao_data, indices) -> str:
        """
        vao_data: flat interleaved vertex list (float32) (vx, vy, vz, uvx, uvy, nx, ny, xz)
        indices: integer list
        """

        start_vertex = len(self.vertex_data) // 8
        shifted = [i + start_vertex for i in indices]

        # record mesh info
        self.meshes[str(self.uniqe_counter)] = {
            "first_index": len(self.index_data),
            "count": len(indices),
            "model": np.eye(4, dtype="f4"),  # default transform
            "visible": True,
            "wireframe": False,
            "color" : np.array([255,255,255,255], np.float32)
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
            "color" : np.array([255,255,255,255], np.float32)
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

    def debug_color_buffer(self) -> None:
        # 1. Read the entire buffer from the GPU
        # Each color is 16 bytes (vec4)
        raw_data = self.color_buffer.read()

        # 2. Convert raw bytes into a NumPy array of floats
        # We expect (number_of_meshes, 4)
        gpu_colors = np.frombuffer(raw_data, dtype='f4').reshape(-1, 4)

        print("--- GPU COLOR BUFFER DEBUG ---")
        for i in range(self.uniqe_counter):
            print(f"Mesh ID {i}: {gpu_colors[i]}")
        print("-------------------------------")

    def set_mesh_color(self, mesh_id: str, color: np.ndarray):
        # mesh_id is a string in your code, convert to int for indexing
        self.meshes[mesh_id]["color"] = color


    def build(self) -> None:
        self.vbo = self.ctx.buffer(np.array(self.vertex_data, dtype="f4").tobytes())
        self.ibo = self.ctx.buffer(np.array(self.index_data, dtype="i4").tobytes())
        
        self.mesh_id_data = np.arange(self.max_meshes, dtype='i4')
        self.mesh_id_buffer = self.ctx.buffer(self.mesh_id_data.tobytes())

        self.matrix_buffer = self.ctx.buffer(reserve=len(self.meshes) * 64)
        self.matrix_buffer.bind_to_storage_buffer(0)

        # single VAO for everything
        self.vao = self.ctx.vertex_array(
            self.program,
            [
                (self.vbo, self.fmt, *self.attrs),
                (self.mesh_id_buffer, '1i /i', 'in_mesh_id')
            ],
            self.ibo,
            index_element_size=4
        )

        

        # Each command is 5 unsigned ints (20 bytes)
        self.indirect_buffer = self.ctx.buffer(reserve=len(self.meshes) * 20)

    
    def draw(self, camera: BaseCamera) -> None:
        camera.apply_to_shader(self.program, "view", "projection")
        self.program['u_is_batched'] = True # Ensure shader uses SSBO logic

        for name, data in self.meshes.items():
            if not data["visible"]:
                continue

            mesh_id = int(name) # Convert key '0', '1' to int

            # 1. Write Matrix to the correct slot
            m_data = data["model"].astype('f4').T.tobytes()
            self.matrix_buffer.write(m_data, offset=mesh_id * 64)

            # 2. Write Color to the correct slot (Debug: Force White if missing)
            # Assuming you store color in data["color"] or similar
            color_data = np.array(data.get("color", [1,1,1,1]), dtype='f4').tobytes()
            self.color_buffer.write(color_data, offset=mesh_id * 16)

            # 3. Handle Wireframe
            self.ctx.wireframe = data.get("wireframe", False)

            # 4. Render
            # Since you are using an IBO, 'first' is the index offset.
            self.vao.render(
                mode=mgl.TRIANGLES,
                vertices=data["count"],
                first=data["first_index"]
            )

        self.ctx.wireframe = False


    def draw_fast(self, camera: BaseCamera) -> None:
        solid_comands = []

        wire_comands = []
        matrix = []
        active_meshes = 0

        if 'u_is_batched' in self.program:
        # For bools, you can use direct assignment or .value
            self.program['u_is_batched'] = True
        
        self.matrix_buffer.bind_to_storage_buffer(0)
        self.color_buffer.bind_to_storage_buffer(1)

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

        all_colors = []
        for name, data in self.meshes.items():
            # 1. Convert to numpy array
            c = data["color"] / 255.0
            
            # 2. CRITICAL: If the tuple is (R, G, B), we MUST add the A (1.0)
            # If we don't, the next color in the buffer will be shifted by 4 bytes!
            if c.size == 3:
                c = np.concatenate([c, [1.0]], axis=0).astype('f4')
                
            all_colors.append(c.tobytes())
        
        # Join and write
        self.color_buffer.write(b''.join(all_colors))

        #vp = camera.get_projection_matrix() @ camera.get_view_matrix()
        #vp_data = cast(mgl.Uniform, self.program["u_view_projection"])
        #vp_data.write(vp.T.astype('f4').tobytes())
        camera.apply_to_shader(self.program, "view", "projection")
        
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



import numpy as np
import moderngl as mgl
import struct
from typing import Tuple, cast

class NBatch3D:
    def __init__(self, ctx: mgl.Context, program: mgl.Program, 
                 fmt: str, attrs: Tuple[str, ...], max_meshes: int = 10000) -> None:
        self.ctx = ctx
        self.program = program
        self.fmt = fmt
        self.attrs = attrs
        self.max_meshes = max_meshes
        
        self.vertex_data = []
        self.index_data = []
        self.meshes = {}  # Stores: first_index, count, model_matrix, visible, etc.
        self.unique_counter = 0

        # Pre-allocate SSBOs for performance
        # 16 floats per matrix (64 bytes) * max_meshes
        self.matrix_buffer = self.ctx.buffer(reserve=self.max_meshes * 64)
        # 4 floats per color (16 bytes) * max_meshes
        self.color_buffer = self.ctx.buffer(reserve=self.max_meshes * 16)
        
        self.matrix_buffer.bind_to_storage_buffer(0)
        self.color_buffer.bind_to_storage_buffer(1)

    def add_mesh(self, vao_data, indices) -> str:
        """Adds geometry and returns a unique mesh_id."""
        mesh_id = str(self.unique_counter)
        start_vertex = len(self.vertex_data) // (sum(int(x[0]) for x in self.fmt.split() if 'f' in x))
        
        # Shift indices based on current vertex count
        shifted_indices = [i + start_vertex for i in indices]

        self.meshes[mesh_id] = {
            "first_index": len(self.index_data),
            "count": len(indices),
            "model": np.eye(4, dtype="f4"),
            "visible": True,
            "wireframe": False,
        }

        self.vertex_data.extend(vao_data)
        self.index_data.extend(shifted_indices)
        
        self.unique_counter += 1
        return mesh_id

    def set_model(self, mesh_id: str, model_matrix: np.ndarray):
        """Update the matrix in the dictionary and the GPU buffer."""
        idx = int(mesh_id)
        self.meshes[mesh_id]["model"] = model_matrix
        # Write directly to the specific slot in the SSBO
        # ModernGL/OpenGL expects Column-Major (.T)
        data = model_matrix.T.astype('f4').tobytes()
        self.matrix_buffer.write(data, offset=idx * 64)

    def set_mesh_color(self, mesh_id: str, color: np.ndarray):
        """Update the color in the GPU buffer (0.0 - 1.0 floats)."""
        idx = int(mesh_id)
        # RGBA = 16 bytes
        self.color_buffer.write(color.astype('f4').tobytes(), offset=idx * 16)

    def build(self) -> None:
        """Finalize the vertex/index buffers and create the VAO."""
        self.vbo = self.ctx.buffer(np.array(self.vertex_data, dtype="f4").tobytes())
        self.ibo = self.ctx.buffer(np.array(self.index_data, dtype="i4").tobytes())

        # We add 'in_mesh_id' as a per-vertex attribute (manually handled or via divisor)
        # However, for indirect drawing, we usually use gl_DrawID or a custom ID buffer.
        # Let's create a buffer that assigns each vertex its mesh ID.
        
        # Simplified: We use an ID buffer to tell each vertex which mesh it belongs to
        # (This is necessary if your shader uses colors[in_mesh_id])
        ids = []
        for mesh_id, data in self.meshes.items():
            # Roughly estimate vertex count for this mesh
            v_count = data["count"] # This is index count, adjust as needed
            ids.extend([int(mesh_id)] * v_count) 
            
        self.id_buffer = self.ctx.buffer(np.array(ids, dtype='i4').tobytes())

        self.vao = self.ctx.vertex_array(
            self.program,
            [
                (self.vbo, self.fmt, *self.attrs),
                (self.id_buffer, '1i', 'in_mesh_id')
            ],
            self.ibo
        )

    def draw_fast(self, camera: BaseCamera) -> None:
        """The optimized indirect draw call."""
        # 1. Update Camera Uniform
        vp = camera.get_projection_matrix() @ camera.get_view_matrix()
        if "u_view_projection" in self.program:
            view_projection_data = cast(mgl.Uniform, self.program["u_view_projection"])
            view_projection_data.write(vp.T.astype('f4').tobytes())

        solid_commands = []
        wire_commands = []

        for mesh_id, data in self.meshes.items():
            if not data["visible"]:
                continue
            
            # Indirect Command: count, instanceCount, firstIndex, baseVertex, baseInstance
            cmd = struct.pack('5I', 
                data["count"], 
                1, 
                data["first_index"], 
                0, 
                int(mesh_id) # baseInstance can be used as gl_InstanceID
            )
            
            if data["wireframe"]:
                wire_commands.append(cmd)
            else:
                solid_commands.append(cmd)

        # 2. Render Solids
        if solid_commands:
            self.ctx.wireframe = False
            ind_buf = self.ctx.buffer(b''.join(solid_commands))
            self.vao.render_indirect(ind_buf, count=len(solid_commands))
            ind_buf.release()

        # 3. Render Wireframes
        if wire_commands:
            self.ctx.wireframe = True
            ind_buf = self.ctx.buffer(b''.join(wire_commands))
            self.vao.render_indirect(ind_buf, count=len(wire_commands))
            ind_buf.release()
