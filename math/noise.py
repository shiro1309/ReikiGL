import numpy as np
import numpy.typing as npt

def fade(t: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    return 6*t**5 - 15*t**4 + 10*t**3

def lerp(t: npt.NDArray[np.float64], a: npt.NDArray[np.float64], b: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    return a + t * (b - a)

def vectorized_perlin_3d(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64], z: npt.NDArray[np.float64], gradients: np.ndarray):
    X, Y, Z = np.floor(x).astype(int), np.floor(y).astype(int), np.floor(z).astype(int)
    xf, yf, zf = x - X, y - Y, z - Z
    
    repeat = gradients.shape[0]
    X0, Y0, Z0 = X % repeat, Y % repeat, Z % repeat
    X1, Y1, Z1 = (X0 + 1) % repeat, (Y0 + 1) % repeat, (Z0 + 1) % repeat

    def get_grad(ix: int, iy: int, iz: int) -> float: return gradients[ix, iy, iz]

    # Dot products for 8 corners
    """ n000 = np.sum(np.stack([xf,   yf,   zf],   axis=-1) * get_grad(X0, Y0, Z0), axis=-1)
    n100 = np.sum(np.stack([xf-1, yf,   zf],   axis=-1) * get_grad(X1, Y0, Z0), axis=-1)
    n010 = np.sum(np.stack([xf,   yf-1, zf],   axis=-1) * get_grad(X0, Y1, Z0), axis=-1)
    n110 = np.sum(np.stack([xf-1, yf-1, zf],   axis=-1) * get_grad(X1, Y1, Z0), axis=-1)
    n001 = np.sum(np.stack([xf,   yf,   zf-1], axis=-1) * get_grad(X0, Y0, Z1), axis=-1)
    n101 = np.sum(np.stack([xf-1, yf,   zf-1], axis=-1) * get_grad(X1, Y0, Z1), axis=-1)
    n011 = np.sum(np.stack([xf,   yf-1, zf-1], axis=-1) * get_grad(X0, Y1, Z1), axis=-1)
    n111 = np.sum(np.stack([xf-1, yf-1, zf-1], axis=-1) * get_grad(X1, Y1, Z1), axis=-1) """
    
    # Dot products for 8 corners (other way)
    x0f, x1f = xf, xf - 1
    y0f, y1f = yf, yf - 1
    z0f, z1f = zf, zf - 1
    
    n000 = np.sum(np.stack([x0f, y0f, z0f], axis=-1) * gradients[X0, Y0, Z0], axis=-1)
    n100 = np.sum(np.stack([x1f, y0f, z0f], axis=-1) * gradients[X1, Y0, Z0], axis=-1)
    n010 = np.sum(np.stack([x0f, y1f, z0f], axis=-1) * gradients[X0, Y1, Z0], axis=-1)
    n110 = np.sum(np.stack([x1f, y1f, z0f], axis=-1) * gradients[X1, Y1, Z0], axis=-1)

    n001 = np.sum(np.stack([x0f, y0f, z1f], axis=-1) * gradients[X0, Y0, Z1], axis=-1)
    n101 = np.sum(np.stack([x1f, y0f, z1f], axis=-1) * gradients[X1, Y0, Z1], axis=-1)
    n011 = np.sum(np.stack([x0f, y1f, z1f], axis=-1) * gradients[X0, Y1, Z1], axis=-1)
    n111 = np.sum(np.stack([x1f, y1f, z1f], axis=-1) * gradients[X1, Y1, Z1], axis=-1)



    u, v, w = fade(xf), fade(yf), fade(zf)
    return lerp(w, lerp(v, lerp(u, n000, n100), lerp(u, n010, n110)),
                   lerp(v, lerp(u, n001, n101), lerp(u, n011, n111)))


def vectorized_fractal_3d(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64], z: npt.NDArray[np.float64], gradients: np.ndarray, octaves: int=4, persistence: float=0.5, lacunarity: float=2.0):
    """
    Stacks multiple layers of noise using NumPy vectorization.
    """
    total = np.zeros_like(x)
    freq = 1.0
    amp = 1.0
    max_amp = 0
    
    for _ in range(octaves):
        # Sample the core 3D noise at current frequency
        # We multiply coordinates by freq to "zoom out" for detail
        total += np.abs(vectorized_perlin_3d(x * freq, y * freq, z * freq, gradients)) * amp
        max_amp += amp
        amp *= persistence
        freq *= lacunarity
        
    return total / max_amp