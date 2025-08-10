import re

# config:
array_width = 4
array_height = 4

lut_input_size = 4

net_file_path = "rudra_testing_0/temp/toggle.net.post_routing"
fasm_file_path = "rudra_testing_0/temp/toggle.fasm"
place_file_path = "rudra_testing_0/temp/toggle.place"
route_file_path = "rudra_testing_0/temp/toggle.route"


# outputs

# [[None, None, None, ...], [None, None, None, ...], ...]
lut_configs = [([None] * (lut_input_size**2))] * (array_width - 2) * (array_height - 2)



def place_file_to_list_of_dicts():
    place_file = open(place_file_path, "r")
    # read until we get to the actual "data" part of the place file
    while (place_file.readline().startswith("#--") == False):
        pass

    # for each remaining line now, create a dictionary and append to a list
    l = []
    for line in place_file:
        parts = line.split()
        l.append({
            "block_name": parts[0],
            "x": int(parts[1]),
            "y": int(parts[2]),
            "subblk": int(parts[3]),
            "layer": int(parts[4]),
            "block_number": parts[5]
        })

    return l

# x and y coordinates of the LUT relative to the bottom-leftmost lut
# for instance, the bottom-leftmost lut is (0,0), then (0,1) is right next to it
# config is a list that will be applied to the config
def set_lut_config(x, y, config):
    lut_configs[x + y*(array_width - 2)] = config

# the bits are on the 0-indexed line (lut_num * 2) + 1 with current fasm ouput
# for example the bits for lut 2 are on the 6th line of the file (so 0-indexed line number 5)
def fasm_file_get_lut_bits_as_list(lut_num):
    fasm_file = open(fasm_file_path, "r")
    # read the first (lut_num)
    for i in range((lut_num * 2) + 1):
        fasm_file.readline()
    line = fasm_file.readline()
    match = re.search(r"=16'b([01]+)", line)
    if match:
        return list(match.group(1))
    return []


if __name__ == "__main__":
    # this list of dictionaries includes each block (including io blocks)
    all_blocks = place_file_to_list_of_dicts()
    
    # let's first determine the bits in each lut
    # to do this, figure out which blocks in the route file are clb blocks and which are not
    # for example, if array_width=4 and array_height=4, then the clb blocks are the ones whose (1<=x<=2) and (1<=y<=2) since the perimeter consists of io blocks
    # see figure 66 here: https://docs.verilogtorouting.org/en/latest/vpr/file_formats/#placement-file-format-place
    clb_blocks = [block for block in all_blocks if (0 < block["x"] < (array_width - 1)) and (0 < block["y"] < (array_height - 1))]
    for index, item in enumerate(clb_blocks):
        config = fasm_file_get_lut_bits_as_list(index)
        # subtract 1 from x and y coordinates due to io on bottom and left
        set_lut_config(item["x"]-1, item["y"]-1, config)

    print(lut_configs)

