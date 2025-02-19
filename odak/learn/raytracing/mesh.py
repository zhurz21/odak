import torch
from ..tools.transformation import rotate_points
from .boundary import reflect, intersect_w_triangle


class planar_mesh():
    def __init__(
                 self,
                 size = [1., 1.],
                 number_of_meshes = [10, 10],
                 angles = torch.tensor([0., 0., 0.]),
                 offset = torch.tensor([0., 0., 0.]),
                 device = torch.device('cpu')
                ):
        """
        Definition to generate a plane with meshes.


        Parameters
        -----------
        number_of_meshes  : torch.tensor
                            Number of squares over plane.
                            There are two triangles at each square.
        size              : list
                            Size of the plane.
        angles            : torch.tensor
                            Rotation angles in degrees.
        offset            : torch.tensor
                            Offset along XYZ axes.
                            Expected dimension is [1 x 3] or offset for each triangle [m x 3].
                            m here refers to `2 * number_of_meshes[0]` times  `number_of_meshes[1]`.
        device            : torch.device
                            Computational resource to be used (e.g., cpu, cuda).
        """
        self.device = device
        self.angles = angles.to(self.device)
        self.offset = offset.to(self.device)
        self.size = torch.tensor(size, device = self.device)
        self.number_of_meshes = torch.tensor(number_of_meshes, device = self.device)
        self.init_heights()


    def init_heights(self):
        """
        Internal function to initialize a height map.
        """
        self.heights = torch.zeros(
                                   (self.number_of_meshes[0], self.number_of_meshes[1], 1),
                                   requires_grad = True,
                                   device = self.device
                                  )
        x = torch.linspace(-self.size[0] / 2., self.size[0] / 2., self.number_of_meshes[0], device = self.device) 
        y = torch.linspace(-self.size[1] / 2., self.size[1] / 2., self.number_of_meshes[1], device = self.device)
        X, Y = torch.meshgrid(x, y, indexing = 'ij')
        self.X = X.unsqueeze(-1)
        self.Y = Y.unsqueeze(-1)


    def get_squares(self):
        """
        Internal function to initiate squares over a plane.

        Returns
        -------
        squares     : torch.tensor
                      Squares over a plane.
                      Expected size is [m x n x 3].
        """
        squares = torch.cat((
                             self.X,
                             self.Y,
                             self.heights
                            ), dim = -1)
        return squares


    def get_triangles(self):
        """
        Internal function to get triangles.
        """ 
        squares = self.get_squares()
        triangles = torch.zeros(2, self.number_of_meshes[0], self.number_of_meshes[1], 3, 3, device = self.device)
        for i in range(0, self.number_of_meshes[0] - 1):
            for j in range(0, self.number_of_meshes[1] - 1):
                first_triangle = torch.cat((
                                            squares[i + 1, j].unsqueeze(0),
                                            squares[i, j + 1].unsqueeze(0),
                                            squares[i + 1, j + 1].unsqueeze(0)
                                           ), dim = 0)
                second_triangle = torch.cat((
                                             squares[i, j].unsqueeze(0),
                                             squares[i + 1, j].unsqueeze(0),
                                             squares[i, j + 1].unsqueeze(0)
                                            ), dim = 0)
                triangles[0, i, j], _, _, _ = rotate_points(first_triangle, angles = self.angles)
                triangles[1, i, j], _, _, _ = rotate_points(second_triangle, angles = self.angles)
        triangles = triangles.view(-1, 3, 3) + self.offset
        return triangles 


    def mirror(self, rays):
        """
        Function to bounce light rays off the meshes.
 
        Parameters
        ----------
        rays        : torch.tensor
                      Rays to be bounced.
                      Expected size is [2 x 3], [1 x 2 x 3] or [m x 2 x 3].
 
        Returns
        -------
        
        """
        if len(rays.shape) == 2:
            rays = rays.unsqueeze(0)
        triangles = self.get_triangles()
        reflected_rays = torch.empty((0, 2, 3), device = self.device)
        reflected_normals = torch.empty((0, 2, 3), device = self.device)
        for triangle in triangles:
            _, _, intersecting_rays, intersecting_normals, check = intersect_w_triangle(
                                                                                        rays,
                                                                                        triangle
                                                                                       ) 
            triangle_reflected_rays = reflect(intersecting_rays, intersecting_normals)
            if triangle_reflected_rays.shape[0] > 0:
                reflected_rays = torch.cat((
                                            reflected_rays,
                                            triangle_reflected_rays
                                          ))
                reflected_normals = torch.cat((
                                               reflected_normals,
                                               intersecting_normals
                                              ))
        return reflected_rays, reflected_normals
