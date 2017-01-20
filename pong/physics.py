def contains(inner, outer):
    p_x, p_y = inner
    x, y, w, h = outer
    return (
        p_x >= x and
        p_x <= x + w and
        p_y >= y and
        p_y <= y + h
    )

def intersects(a_rect, b_rect):
    a_l = a_rect[0]
    a_r = a_rect[0] + a_rect[2]
    a_t = a_rect[1]
    a_b = a_rect[1] + a_rect[3]

    b_l = b_rect[0]
    b_r = b_rect[0] + b_rect[2]
    b_t = b_rect[1]
    b_b = b_rect[1] + b_rect[3]

    intersects_y = a_t < b_b or a_b > b_t
    intersects_x = a_l < b_r or a_r > b_l

    return intersects_y and intersects_x
