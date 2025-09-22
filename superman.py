import turtle
import math

ca = turtle.Turtle()

def func_1(x, y):
    """move the turtle to the given coordinates and set up initial configuration"""
    ca.penup()
    ca.goto(x, y)
    ca.pendown()
    ca.setheading(0)
    ca.pensize(2)
    ca.speed(10)

def circle(r, color):
    """draw a circle of the given radius and color (centered at 0,0)"""
    x_point = 0
    y_point = -r
    func_1(x_point, y_point)
    ca.pencolor(color)
    ca.fillcolor(color)
    ca.begin_fill()
    ca.circle(r)
    ca.end_fill()

def star(r, color):
    """draw a perfect solid 5-pointed star"""
    # Hitung koordinat 10 titik (5 luar & 5 dalam)
    points = []
    for i in range(10):
        angle_deg = 90 - i * 36  # tiap 36 derajat
        # titik luar (i genap), titik dalam (i ganjil)
        if i % 2 == 0:
            radius = r
        else:
            # rasio jarak titik dalam ke titik luar pada bintang = cos(72)/cos(36)
            radius = r * math.cos(math.radians(72)) / math.cos(math.radians(36))
        x = radius * math.cos(math.radians(angle_deg))
        y = radius * math.sin(math.radians(angle_deg))
        points.append((x, y))

    # Gambar poligon bintang penuh
    func_1(points[0][0], points[0][1])
    ca.pencolor(color)
    ca.fillcolor(color)
    ca.begin_fill()
    for x, y in points[1:]:
        ca.goto(x, y)
    ca.goto(points[0][0], points[0][1])  # kembali ke awal
    ca.end_fill()
    ca.hideturtle()

if __name__ == "__main__":
    circle(288, 'crimson')
    circle(234, 'snow')
    circle(174, 'crimson')
    circle(114, 'blue')
    star(114, 'white')   # bintang solid putih penuh
    turtle.done()
