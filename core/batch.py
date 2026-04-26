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


class AdvancedBatch:
    def __init__(self, ctx: mgl.Context, program: mgl.Program, fmt: str, attrs: Tuple[str, ...]) -> None:
        """
        Manages high-speed rendering of multiple meshes using Indirect Drawing.
        
        Args:
            ctx: The ModernGL context.
            program: The shader program.
            max_meshes: Maximum objects allowed in the batch.
            max_vertices: Maximum total vertices allowed in the VBO.

            '3f 2x4 3f 4f'
            'in_pos', 'in_uv', 'in_norm', 'in_color'
        """
        self.ctx = ctx
        self.program = program
        self.max_meshes = 10000
        self.max_vertices = 500000
        
        # 1. CPU Shadow Copies
        # Format: x, y, z, u, v, nx, ny, nz, r, g, b, a (12 floats)
        self.vertex_data = [] 
        self.index_data = []
        self.meshes = {} # Stores offsets and metadata
        
        # Metadata for the VAO
        self.fmt = fmt
        self.attrs = attrs
        self.stride = 12 * 4 # 12 floats * 4 bytes = 48 bytes
        
    def add_mesh(self, vertices, indices, color=[1.0, 1.0, 1.0, 1.0]) -> int:
        """
        Adds a mesh to the batch lists. Handles both single-color and per-vertex modes.
        
        If 'color' is provided as a list [R, G, B, A], it will be appended to 
        every vertex (Normal Mode).
        If 'color' is None, it assumes vertices are already 12-floats long (Advanced Mode).
        
        Args:
            vertices (list): Flat list of vertex floats (8 or 12 per vertex).
            indices (list): List of indices for the EBO.
            color (list, optional): [r, g, b, a] to apply to the whole mesh.
            
        Returns:
            int: The unique mesh_id for this instance.
        """
        mesh_id = len(self.meshes)
        
        # Safety check for 12-float stride
        if len(vertices) % 12 != 0:
            raise ValueError(f"Vertex data length {len(vertices)} must be multiple of 12.")

        start_vertex = len(self.vertex_data) // 12
        start_index = len(self.index_data)
        
        # Add indices with the correct offset
        shifted_indices = [i + start_vertex for i in indices]
        
        self.vertex_data.extend(vertices)
        self.index_data.extend(shifted_indices)
        
        self.meshes[mesh_id] = {
            'start_vertex': start_vertex,
            'vertex_count': len(vertices) // 12,
            'start_index': start_index,
            'index_count': len(indices),
            'color': color,
        }
        return mesh_id

    def build(self) -> None:
        """
        Finalizes the batch and ships the data to the GPU. 
        Calculates indirect commands and sets up the VAO.
        """
        # Convert lists to NumPy for the initial upload
        v_np = np.array(self.vertex_data, dtype='f4')
        i_np = np.array(self.index_data, dtype='i4')

        # 1. Vertex Buffer (VBO) - Pre-allocate space
        self.vbo = self.ctx.buffer(reserve=self.max_vertices * self.stride)
        self.vbo.write(v_np.tobytes())

        # 2. Index Buffer (IBO)
        self.ibo = self.ctx.buffer(i_np.tobytes())

        # 3. Mesh ID Buffer (for gl_InstanceID mapping)
        mesh_ids = np.arange(self.max_meshes, dtype='i4')
        self.mesh_id_buffer = self.ctx.buffer(mesh_ids.tobytes())

        # 4. Matrix SSBO (Binding 0)
        self.matrix_buffer = self.ctx.buffer(reserve=self.max_meshes * 64)
        self.matrix_buffer.bind_to_storage_buffer(0)

        # 5. VAO Setup
        # Note the '1i /i' which means 1 integer, updated per instance
        self.vao = self.ctx.vertex_array(
            self.program,
            [
                (self.vbo, self.fmt, *self.attrs),
                (self.mesh_id_buffer, '1i /i', 'in_mesh_id')
            ],
            self.ibo
        )

        # 6. Indirect Buffer
        self.indirect_buffer = self.ctx.buffer(reserve=self.max_meshes * 20)
        self._update_indirect()

    def _update_indirect(self) -> None:
        """Generates the byte commands for the GPU Indirect Draw call."""
        commands = []
        for m_id, m in self.meshes.items():
            commands.extend([
                m['index_count'], # count
                1,                # instanceCount
                m['start_index'], # firstIndex
                0,                # baseVertex
                m_id              # baseInstance (becomes in_mesh_id)
            ])
        self.indirect_buffer.write(np.array(commands, dtype='u4').tobytes())

    def update_color(self, mesh_id, r, g, b, a=1.0) -> None:
        """Targeted update of colors in the VBO."""
        m = self.meshes[mesh_id]
        new_color = np.array([r, g, b, a], dtype='f4')
        
        # We need to update every vertex in this specific mesh
        # We'll build a small buffer of just the color data to blast onto the GPU
        start_v = m['start_vertex']
        count_v = m['vertex_count']
        
        # Optimization: Update the CPU shadow so it's ready for future redraws
        # (Though for speed, you might just do the GPU write)
        for i in range(count_v):
            # Calculate the exact byte offset for the COLOR part of the vertex
            # Offset = (VertexIndex * 12 floats + 8 floats offset) * 4 bytes
            offset = (start_v + i) * self.stride + (8 * 4)
            self.vbo.write(new_color.tobytes(), offset=offset)
    
    def update_mesh_color_fast(self, mesh_id, r, g, b, a=1.0) -> None:
        """
        Updates the color for an entire mesh in one single GPU operation.
        """
        if mesh_id not in self.meshes:
            return
        
        mesh = self.meshes[mesh_id]
        start_v = mesh['start_vertex']
        count_v = mesh['vertex_count']

        # 1. Grab the chunk of data from our CPU shadow list
        # Every mesh starts at start_v * 12 floats
        start_idx = start_v * 12
        end_idx = (start_v + count_v) * 12

        # Create a view of this specific mesh's data
        # Note: If you want this to be EXTREMELY fast, keep self.vertex_data 
        # as a NumPy array permanently instead of a list.
        mesh_chunk = np.array(self.vertex_data[start_idx:end_idx], dtype='f4')

        # 2. Reshape to (-1, 12) so we can talk to the columns
        # We want columns 8, 9, 10, 11 (the RGBA part)
        reshaped_view = mesh_chunk.reshape(-1, 12)
        reshaped_view[:, 8:12] = [r, g, b, a]

        # 3. Update the CPU shadow so the change is persistent
        self.vertex_data[start_idx:end_idx] = mesh_chunk.flatten().tolist()

        # 3. One single write call for the whole mesh block
        byte_offset = start_v * self.stride
        self.vbo.write(mesh_chunk.tobytes(), offset=byte_offset)

    def update_matrix(self, mesh_id, matrix_np) -> None:
        """Updates the 4x4 matrix for a specific mesh."""
        # Matrix is 64 bytes (16 floats)
        offset = mesh_id * 64
        self.matrix_buffer.write(matrix_np.tobytes(), offset=offset)

    def draw_fast(self, camera: BaseCamera) -> None:
        active_meshes = len(self.meshes)
        if active_meshes == 0:
            return

        if 'u_is_batched' in self.program:
            self.program['u_is_batched'] = True
        
        camera.apply_to_shader(self.program, "view", "projection")
        
        self.vao.render_indirect(self.indirect_buffer, count=active_meshes)


class SimpleInstancedBatch:
    def __init__(self, ctx, program, vertices, indices):
        self.ctx = ctx
        self.program = program
        
        # 1. Create Buffers for the SINGLE mesh
        self.vbo = self.ctx.buffer(np.array(vertices, dtype='f4'))
        self.ibo = self.ctx.buffer(np.array(indices, dtype='i4'))
        
        # 2. Setup VAO (standard 330, no layouts needed if names match)
        # Format '3f 3f 4f' matches pos, norm, color
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f 3f 4f', 'in_pos', 'in_norm', 'in_color')],
            self.ibo
        )
        
        self.instance_matrices = []

    def clear_instances(self):
        self.instance_matrices = []

    def add_instance(self, matrix_np):
        self.instance_matrices.append(matrix_np)

    def draw(self, camera):
        if not self.instance_matrices:
            return
            
        camera.apply_to_shader(self.program, "view", "projection")
        
        # We can only draw in batches of 250 due to the shader array limit
        for i in range(0, len(self.instance_matrices), 250):
            chunk = self.instance_matrices[i:i + 250]
            
            # Flatten the matrices into one long list of floats
            flat_data = np.array(chunk, dtype='f4').flatten()
            
            # Upload the matrices to the uniform array
            self.program['u_models'].write(flat_data.tobytes())
            
            # Draw the mesh 'len(chunk)' times
            self.vao.render(instances=len(chunk))


class GameObject:
    def __init__(self, ctx, program, vertices, indices) -> None:
        self.ctx = ctx
        self.program = program
        
        # 1. Create Buffers for this specific mesh
        
        self.vbo = self.ctx.buffer(np.array(vertices, dtype='f4'))
        self.ibo = self.ctx.buffer(np.array(indices, dtype='i4'))
        
        # 2. Setup VAO
        # Ensure 'in_pos', 'in_norm', 'in_color' match the shader
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f 2x4 3f 4f', 'in_pos', 'in_norm', 'in_color')],
            self.ibo
        )
        
        # Transform properties
        self.matrix = np.eye(4, dtype='f4')

    def render(self, camera) -> None:
        # Standard camera matrices
        camera.apply_to_shader(self.program, "view", "projection")

        # Object transform
        self.program['u_model'].write(self.matrix.tobytes())

        # Lighting uniforms
        # Adjust these values to change the look of the scene

        if 'u_camera_pos' in self.program:
            # Assuming your camera object has a 'position' attribute
            self.program['u_camera_pos'].value = camera.position

        if 'u_diffuseColor' in self.program:
            self.program['u_diffuseColor'].value = (1.0, 1.0, 1.0)

        # Draw call
        self.vao.render(mgl.TRIANGLES)

    def release(self):
        """Cleanup GPU resources for this object."""
        self.vbo.release()
        self.ibo.release()
        self.vao.release()

    def update_matrix(self, matrix) -> None:
        self.matrix = matrix