import numpy as np
import engine
from typing import Deque
from collections import deque
import time

class DynamicParticalSystem:
    def __init__(self, vao_data, indices, batch, max_particles) -> None:
        # since every paricle is the same thing we take in a batch and create some sort of origin
        # particle first
        self.batch = batch
        self.origin_id = self.batch.add_mesh(vao_data, indices)
        self.batch.meshes[self.origin_id]["visible"] = False
        
        self.origin_point = False
        self.gravity_toggle = True
        self.gravity = 9.81

        self.chunk = 2

        self.max_particles = max_particles
        self.avalible_mesh_id: Deque[str] = deque()
        for i in range(self.max_particles):
            id = self.batch.add_instance(self.origin_id)
            
            self.batch.meshes[id]["visible"] = False
            self.avalible_mesh_id.append(id)

        self.running_time = 0.0
        self.temp = 0.0

        self.alive_particles = 0

        self.intervals: float = 1
        self.creation_amount = self.chunk
        self.start = time.time()
        # [life, self.particles[index], x,y,z, vx, vy, vz, sx, sy, sz, ax, ay, az, [Quaternion] = w,x,y,z]
        self.np_particles = np.zeros((30,18), dtype=np.float64)
        
        #self.base_particle = np.array([4, int(key), 0, 0, 0, 5, 20, 2, 1, 1, 1, 0.3, 1, 2, 1, 0, 0, 0], dtype=np.float64)

    def update(self, dt, gravity=(0.0, 0.0, 0.0)) -> None:
        # reused list inside the update for each particle
        
        pos = np.empty(3, dtype=float)
        vel = np.empty(3, dtype=float)
        ang_vel = np.empty(3, dtype=float)
        quat = np.empty(4, dtype=float)
        gravity_arr = np.array(gravity, dtype=float)

        # adds the particle
        self.add_particle(dt)

        # lopps over and updates the particle
        for i in range(self.alive_particles):
            if not self.np_particles[i][0]:
                continue

            # setts the values to the arrays
            life = self.np_particles[i, 0]
            index = self.np_particles[i, 1]
            pos[:] = self.np_particles[i, 2:5]
            vel[:] = self.np_particles[i, 5:8]
            ang_vel[:] = self.np_particles[i, 11:14]
            quat[:] = self.np_particles[i, 14:18]

            # checks if the y vec has reached terminal velocity
            if vel[1] > gravity_arr[1]:
                vel += gravity_arr * dt
            pos += vel * dt
            
            # calculates the small angle for rotation
            theta = np.linalg.norm(ang_vel) * dt
            # if changes to the angle update the quaternion
            if theta > 0:
                axis = ang_vel / np.linalg.norm(ang_vel)
                quat = engine.math.rotate_quaternion(quat, theta, axis)

            # update the model data
            T = engine.math.translate(pos)
            S = engine.math.scale(self.np_particles[i, 8:11])
            R = engine.math.quat_rotation_matrix(quat)

            # Model = T * R * S (column-vector convention)
            P = T @ R @ S

            # set the model to calculated values
            key = str(int(index))
            self.batch.set_model(key, P)

            # kill the particle if it has reached either of the cases
            if life - dt <= 0.0 or pos[1] <= -50 or abs(pos[0]) > 2 or abs(pos[1]) > 20 or abs(pos[1]) > 20:
                self.batch.meshes[key]["visible"] = False
                self.avalible_mesh_id.append(key)
                life = 0.0
                self.alive_particles -= 1
            
            if life > 0.0:
                life -= dt

            # put the updated values back to the list
            self.np_particles[i, 0] = life
            self.np_particles[i, 2:5] = pos
            self.np_particles[i, 5:8] = vel
            self.np_particles[i, 11:14] = ang_vel
            self.np_particles[i, 14:18] = quat

    def update_fast(self, dt, gravity=(0.0, 0.0, 0.0)) -> None:
        self.add_particle(dt)
        
        life = self.np_particles[:, 0]
        pos = self.np_particles[:, 2:5]
        vel = self.np_particles[:, 5:8]
        scale = self.np_particles[:, 8:11]
        ang_vel = self.np_particles[:, 11:14]
        quat = self.np_particles[:, 14:18]
        grav = np.array(gravity, dtype=np.float32)

        gravety_mask = vel[:, 1] > gravity[1]
        vel[gravety_mask] += grav * dt
        pos += vel * dt

        moving = np.linalg.norm(ang_vel, axis=1) > 0

        if np.any(moving):
            active_ang = ang_vel[moving]
            theta = np.linalg.norm(active_ang, axis=1, keepdims=True) * dt

            quat[moving] = engine.math.rotate_quaternion_vectorized(quat[moving], theta, active_ang)


        T = engine.math.translate_vectorized(pos)
        S = engine.math.scale_vectorized(scale)
        R = engine.math.quat_rotation_matrix_vectorized(quat)

        model_matrices = T @ R @ S
    

        for i in range(self.alive_particles):
            #print(i)
            index_val = self.np_particles[i, 1]
            #print(index_val)
    
            # Sjekk om index er NaN før vi prøver å konvertere til int
            

            key = str(int(index_val))
            P = model_matrices[i]

            self.batch.set_model(key, P)

            if self.np_particles[i, 0] <= 0.0 or abs(self.np_particles[i, 2]) >= 20 or abs(self.np_particles[i, 4]) >= 20 or self.np_particles[i, 3] >= 40 or self.np_particles[i, 3] <= 0:
                self.batch.meshes[key]["visible"] = False
                self.avalible_mesh_id.append(key)
                life[i] = 0.0
                self.alive_particles -= 1
            
            if life[i] > 0.0:
                life[i] -= dt
        
        
        
        self.np_particles[:, 0] = life
        self.np_particles[:, 2:5] = pos
        self.np_particles[:, 5:8] = vel
        self.np_particles[:, 11:14] = ang_vel
        self.np_particles[:, 14:18] = quat

    def add_particle(self, dt) -> None:
        self.clean_up()
        if self.alive_particles + self.creation_amount >= self.max_particles:
            return
        
        self.running_time += dt

        if self.running_time <= self.intervals + self.temp:
            return
        
        self.temp += self.intervals
        
        

        if len(self.np_particles) <= self.alive_particles + self.creation_amount:
            new_chunk = np.zeros((self.chunk, 18))
            self.np_particles = np.concatenate((self.np_particles, new_chunk))

        for i in range(self.creation_amount):
            idx = self.alive_particles
            self.make_particle(idx)

    def make_particle(self, id) -> None:
        #np.array([life, int(key), x, y, z, vx, vy, vz, sx, sy, sz, ax, ay, az, qw, qx, qy, qz])
        self.alive_particles += 1

        key = self.avalible_mesh_id.popleft()
        self.batch.meshes[key]["visible"] = True

        p = self.np_particles[id]

        scale = np.random.uniform(0.3, 0.5)

        p[0] = 5
        p[1] = int(key)

        p[2:5] = 0, 0, 0

        p[5] = np.random.randint(-6,6)*2
        p[6] = np.random.randint(10,40)
        p[7] = np.random.randint(-6,6)*2
        
        p[8:11] = scale
        p[11:14] = np.random.uniform(-1, 1, 3)
        p[14:18] = 1, 0, 0, 0
        
    
    def clean_up(self) -> None:
        self.np_particles = self.np_particles[self.np_particles[:, 0] != 0.0]