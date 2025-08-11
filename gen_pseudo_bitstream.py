import re

# config:
array_width = 4
array_height = 4

lut_input_size = 4

channel_width = 8

net_file_path = "rudra_testing_0/temp/toggle.net.post_routing"
fasm_file_path = "rudra_testing_0/temp/toggle.fasm"
place_file_path = "rudra_testing_0/temp/toggle.place"
route_file_path = "rudra_testing_0/temp/toggle.route"



connection_box_chan_0 = 0
connection_box_chan_0 = 1
connection_box_chan_0 = 2
connection_box_chan_0 = 3
connection_box_chan_0 = 4
connection_box_chan_0 = 5
connection_box_chan_0 = 6
connection_box_chan_0 = 7
connection_box_z = 1000
connection_box_unknown = None

switch_box_choose_left = 0
switch_box_choose_bottom = 1
switch_box_choose_right = 2
switch_box_choose_top = 3
switch_box_choose_clb = 4
switch_box_choose_unknown = None


# outputs

# for a lut, "None" means that we don't care what bits are in the SRAM since that LUT isn't used
# [[None, None, None, ...], [None, None, None, ...], ...]
lut_configs = [([None] * (lut_input_size**2))] * (array_width - 2) * (array_height - 2)


left_edge_connection_box_config = [connection_box_unknown]  * (array_height - 2)
bottom_edge_connection_box_config = [connection_box_unknown] * (array_width - 2)
right_edge_connection_box_config = [connection_box_unknown] * (array_height - 2)
top_edge_connection_box_config = [connection_box_unknown] * (array_width - 2)

# # goes from track 0 to track channel_width
# bottom_left_corner_switch_box_config = [switch_box_choose_unknown] * channel_width
# bottom_right_corner_switch_box_config = [switch_box_choose_unknown] * channel_width
# top_right_corner_switch_box_config = [switch_box_choose_unknown] * channel_width
# top_left_corner_switch_box_config = [switch_box_choose_unknown] * channel_width

# # goes channel_width vertical wires then channel_width/2 horizontal wires
# left_edge_switch_box_configs = [[switch_box_choose_unknown] * (int)((channel_width + channel_width/2))] * (array_height - 3)
# # goes channel_width/2 vertical wires then channel_width horizontal wires
# bottom_edge_switch_box_configs = [[switch_box_choose_unknown] * (int)((channel_width + channel_width/2))] * (array_width - 3)
# # goes channel_width vertical wires then channel_width/2 horizontal wires
# right_edge_switch_box_configs = [[switch_box_choose_unknown] * (int)((channel_width + channel_width/2))] * (array_height - 3)
# # goes channel_width/2 vertical wires then channel_width horizontal wires
# top_edge_switch_box_configs = [[switch_box_choose_unknown] * (int)((channel_width + channel_width/2))] * (array_width - 3)

# goes channel_width vertical wires then channel_width horizontal wires
switch_box_configs = [[switch_box_choose_unknown] * (channel_width + channel_width)] * (array_width - 1) * (array_height - 1)

# the first element in the array is the left connection box for this lut, then the bottom, then the right, then the top
# row major order starting from the bottom left (e.g. connection box for bottom left lut is element 0, connection box for lut directly to the right of the bottom left lut is element 1, etc.)
connection_box_configs = [([None] * (4))] * (array_width - 2) * (array_height - 2)

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


def parse_route_file_location(route_file_location):
    parts = route_file_location.strip("()").split(",")

    # Convert to integers
    x, y, z = map(int, parts)
    return (x,y)    

def set_switch_box_config(x, y, conf):
    switch_box_configs[x + y*(array_width-1)] = conf


def process_route_file():
    route_file = open(route_file_path, "r")
    while(route_file.readline()):
            # Look ahead to the next line without losing position
            pos = route_file.tell()
            next_line = route_file.readline()
            route_file.seek(pos) 
            if next_line.startswith("Node"):
                break
    

    l = []
    for line in route_file:
        if line.strip() == '':
            break
        parts = line.split()
        # type can be either "SOURCE", "OPIN", "CHANX", "CHANY", "IPIN", or "SINK"
        # location is a coordinate type e.g. (1, 1, 0)
        # location_type is either "Class", "Pin", or "Track"
        # track is the track number if and only if the location_type is "Track"
        l.append({
            "type": parts[2],
            "location": parts[3],
            "location_type": parts[4],
            "track": parts[5],
        })
    

    index = 0
    while (index < len(l)):
        val = l[index]
        if (index < len(l) - 1):
            nextval = l[index + 1]
        if (index > 0):
            prevval = l[index - 1]
        if val["type"] == "SOURCE":
            index += 1
            pass
        # if we see an OPIN, then we need to look at the next node to set the switch box config appropriately
        if val["type"] == "OPIN":
            x,y = parse_route_file_location(val["location"])
            nextx, nexty = parse_route_file_location(nextval["location"])
            assert(nextval["location_type"] == "Track")
            nexttrack = int(nextval["track"])
            if nexttrack == 0 or nexttrack == 2:
                set_switch_box_config(nextx - 1, nexty, switch_box_choose_clb)
            elif nexttrack == 1 or nexttrack == 3:
                set_switch_box_config(nextx, nexty, switch_box_choose_clb)
            index += 1
            pass
        if val["type"] == "CHANX":
            index += 1
            pass
        if val["type"] == "CHANY":
            index += 1
            pass
        if val["type"] == "IPIN":
            index += 1
            pass
        if val["type"] == "SINK":
            index += 1
            pass


        print(val)
        



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

    process_route_file()


    # print(lut_configs)

    # print(all_blocks)
