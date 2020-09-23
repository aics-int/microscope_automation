'''
Created on Sep 12, 2016

@author: winfriedw
'''
import numpy
import matplotlib.pyplot as plt
import scipy.optimize
import functools

def plane(x, y, params):
    a = params[0]
    b = params[1]
    c = params[2]
    z = a*x + b*y + c
    return z

def error(params, points):
    result = 0
    for (x,y,z) in points:
        plane_z = plane(x, y, params)
        diff = abs(plane_z - z)
        result += diff**2
    return result

def cross(a, b):
    return [a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0]]

points = [(1.1,2.1,8.1),
          (3.2,4.2,8.0),
          (5.3,1.3,8.2),
          (3.4,2.4,8.3),
          (1.5,4.5,8.0)]

fun = functools.partial(error, points=points)
params0 = [0, 0, 0]
res = scipy.optimize.minimize(fun, params0)

a = res.x[0]
b = res.x[1]
c = res.x[2]

xs, ys, zs = list(zip(*points))

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

ax.scatter(xs, ys, zs)

point  = numpy.array([0.0, 0.0, c])
normal = numpy.array(cross([1, 0, a], [0, 1, b]))
d = -point.dot(normal)
xx, yy = numpy.meshgrid([-5, 10], [-5, 10])
z = (-normal[0] * xx - normal[1] * yy - d) * 1. /normal[2]
ax.plot_surface(xx, yy, z, alpha=0.2, color=[0,1,0])

ax.set_xlim(-10,10)
ax.set_ylim(-10,10)
ax.set_zlim(  0,10)

plt.show()