from typing import List

def hexfile(file: str) -> List:
    rgb_list = []
    alp = "abcdef0123456789"
    hex_color_list = []
    temp_hex = ''

    # open file
    try:
        with open(file, 'r') as f:
            raw_data = f.read()

    # sets the hex data into a list
        for leter in raw_data:
            if leter in alp:
                temp_hex += leter
            else:
                if len(temp_hex) > 0:
                    hex_color_list.append(temp_hex)
                temp_hex = ''

        # convert from hex to rgb
        for color in hex_color_list:
            r_hex = color[0:2]
            g_hex = color[2:4]
            b_hex = color[4:6]

            r = int(r_hex, 16)
            g = int(g_hex, 16)
            b = int(b_hex, 16)
            a = int(255)

            col = (r, g, b, a)
            rgb_list.append(col)    
        
        return rgb_list
    
    # failed or could not find file
    except:
        col_1 = (251, 245, 239, 255)
        col_2 = (242, 211, 171, 255)
        col_3 = (198, 159, 165, 255)
        col_4 = (139, 109, 156, 255)
        col_5 = (73, 77, 126, 255)
        col_6 = (39, 39, 68, 255)
        return [col_1, col_2, col_3, col_4, col_5, col_6]