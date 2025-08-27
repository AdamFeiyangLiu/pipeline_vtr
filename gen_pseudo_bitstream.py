import re
import sys
import copy
import traceback

# config:
array_width = 4
array_height = 4

lut_input_size = 4

channel_width = 8

net_file_path = "universal_switchbox/temp/toggle.net.post_routing"
fasm_file_path = "universal_switchbox/temp/toggle.fasm"
place_file_path = "universal_switchbox/temp/toggle.place"
route_file_path = "universal_switchbox/temp/toggle.route"

connection_box_chan_0 = 1<<0
connection_box_chan_1 = 1<<1
connection_box_chan_2 = 1<<2
connection_box_chan_3 = 1<<3
connection_box_chan_4 = 1<<4
connection_box_chan_5 = 1<<5
connection_box_chan_6 = 1<<6
connection_box_chan_7 = 1<<7
connection_box_z = 1<<8
connection_box_unknown = 0

switch_box_choose_left = 1<<0
switch_box_choose_bottom = 1<<1
switch_box_choose_right = 1<<2
switch_box_choose_top = 1<<3
switch_box_choose_clb = 1<<4
switch_box_choose_io_pad = 1 << 5
switch_box_choose_unknown = 0


# outputs

# for a lut, "None" means that we don't care what bits are in the SRAM since that LUT isn't used
# [[None, None, None, ...], [None, None, None, ...], ...]
lut_configs = [[None] * (lut_input_size**2) for _ in range((array_width - 2) * (array_height - 2))]

# goes from bottom to top
left_edge_connection_box_config = [connection_box_unknown for _ in range(array_height - 2)]
# goes from left to right
bottom_edge_connection_box_config = [connection_box_unknown for _ in range(array_width - 2)]
# goes from bottom to top
right_edge_connection_box_config = [connection_box_unknown for _ in range(array_height - 2)]
# goes from left to right
top_edge_connection_box_config = [connection_box_unknown for _ in range(array_width - 2)]

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
switch_box_configs = [[switch_box_choose_unknown for _ in range(channel_width * 2)] for _ in range((array_width - 1) * (array_height - 1))]

# the first element in the array is the left connection box for this lut, then the bottom, then the right, then the top
# row major order starting from the bottom left (e.g. connection box for bottom left lut is element 0, connection box for lut directly to the right of the bottom left lut is element 1, etc.)
connection_box_configs = [[switch_box_choose_unknown for _ in range(4)] for _ in range((array_width - 2) * (array_height - 2))]

def error(message: str):
    # ANSI code for red text
    RED = "\033[91m"
    RESET = "\033[0m"

    # Print the custom error message in red
    print(f"{RED}ERROR: {message}{RESET}", file=sys.stderr)

    # Print traceback of where this function was called
    tb = "".join(traceback.format_stack(limit=5))  # limit=5 to avoid too much noise
    print(f"{RED}Traceback (most recent call last):\n{tb}{RESET}", file=sys.stderr)
    sys.exit(1)

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

def set_switch_box_config(x, y, track, dir, conf):
    if dir == "horizontal":
        switch_box_configs[x + y*(array_width-1)][track + channel_width] = conf
    elif dir == "vertical":
        switch_box_configs[x + y*(array_width-1)][track] = conf
    else:
        error("the switch box direction isn't horizontal or vertical")

    
def get_switch_box_config(x, y, track, dir):
    if dir == "horizontal":
        return switch_box_configs[x + y*(array_width-1)][track + channel_width]
    elif dir == "vertical":
        return switch_box_configs[x + y*(array_width-1)][track]
    else:
        error("the switch box direction isn't horizontal or vertical")


def track_to_connection_box_config(track):
    return 1 << track

# note that edge is technically redundant since you can figure out the edge from the x and y coordinates, but i included it for clarity purposes
def set_edge_connection_box_config(x, y, edge, conf):
    if edge == "left":
        left_edge_connection_box_config[y - 1] = conf
    if edge == "bottom":
        bottom_edge_connection_box_config[x - 1] = conf
    if edge == "right":
        right_edge_connection_box_config[y - 1] = conf
    if edge == "top":
        top_edge_connection_box_config[x - 1] = conf

def get_edge_connection_box_config(x, y, edge):
    if edge == "left":
        return left_edge_connection_box_config[y-1]
    if edge == "bottom":
        return bottom_edge_connection_box_config[x-1]
    if edge == "right":
        return right_edge_connection_box_config[y-1]
    if edge == "top":
        return top_edge_connection_box_config[x-1]

def set_connection_box_config(lutx, luty, side, conf):
    if side == "left":
        connection_box_configs[(lutx-1)+(luty-1)*(array_width-2)][0] = conf
    if side == "bottom":
        connection_box_configs[(lutx-1)+(luty-1)*(array_width-2)][1] = conf
    if side == "right":
        connection_box_configs[(lutx-1)+(luty-1)*(array_width-2)][2] = conf
    if side == "top":
        connection_box_configs[(lutx-1)+(luty-1)*(array_width-2)][3] = conf

def get_connection_box_config(lutx, luty, side):
    if side == "left":
        return connection_box_configs[(lutx-1)+(luty-1)*(array_width-2)][0]
    if side == "bottom":
        return connection_box_configs[(lutx-1)+(luty-1)*(array_width-2)][1]
    if side == "right":
        return connection_box_configs[(lutx-1)+(luty-1)*(array_width-2)][2]
    if side == "top":
        return connection_box_configs[(lutx-1)+(luty-1)*(array_width-2)][3]

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
        # location_type is either "Class:", "Pin:", "Track:", or "Pad:"
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
        if val["type"] == "OPIN":
            # if clb output
            if val["location_type"] == "Pin:":
                x,y = parse_route_file_location(val["location"])
                nextx, nexty = parse_route_file_location(nextval["location"])
                nexttrack = int(nextval["track"])
                if nexttrack == 0 or nexttrack == 2:
                    set_switch_box_config(nextx - 1, nexty, nexttrack, "horizontal", switch_box_choose_clb)
                elif nexttrack == 1 or nexttrack == 3:
                    set_switch_box_config(nextx, nexty, nexttrack, "horizontal", switch_box_choose_clb)
            # if io pad output
            if val["location_type"] == "Pad:":
                # TODO
                pass
            index += 1
            pass
        if val["type"] == "CHANX":
            if nextval["type"] == "CHANX":
                x,y = parse_route_file_location(val["location"])
                nextx, nexty = parse_route_file_location(nextval["location"])
                nexttrack = int(nextval["track"])
                nextdir = "horizontal"
                if nextx < x:
                    set_switch_box_config(nextx, y, nexttrack, nextdir, switch_box_choose_right)
                else:
                    set_switch_box_config(nextx, y, nexttrack, nextdir, switch_box_choose_left)

            if nextval["type"] == "CHANY":
                x,y = parse_route_file_location(val["location"])
                nextx, nexty = parse_route_file_location(nextval["location"])
                nexttrack = int(nextval["track"])
                nextdir = "vertical"
                if nextx < x:
                    set_switch_box_config(nextx, y, nexttrack, nextdir, switch_box_choose_right)
                else:
                    set_switch_box_config(nextx, y, nexttrack, nextdir, switch_box_choose_left)

            if nextval["type"] == "IPIN":
                # if connected to io pad
                if nextval["location_type"] == "Pad:":
                    # TODO
                    pass
                # if connected to input pin of clb
                if nextval["location_type"] == "Pin:":
                    x,y = parse_route_file_location(val["location"])
                    nextx,nexty = parse_route_file_location(nextval["location"])
                    track = int(val["track"])
                    if nexty > y:
                        set_connection_box_config(nextx, nexty, "bottom", track_to_connection_box_config(track))
                    else:
                        set_connection_box_config(nextx, nexty, "top", track_to_connection_box_config(track))
                    pass
            index += 1
            pass
        if val["type"] == "CHANY":
            if nextval["type"] == "CHANX":
                # TODO
                pass
            if nextval["type"] == "CHANY":
                # TODO
                pass
            if nextval["type"] == "IPIN":
                # if connected to io pad
                if nextval["location_type"] == "Pad:":
                    nextx,nexty = parse_route_file_location(nextval["location"])
                    track = int(val["track"])
                    # if pad is on right edge of fpga
                    if nextx == array_width - 1:
                        set_edge_connection_box_config(nextx, nexty, "right", track_to_connection_box_config(track))
                    elif nextx == 0:
                        set_edge_connection_box_config(nextx, nexty, "left", track_to_connection_box_config(track))
                    pass
                # if connected to input pin of clb
                if nextval["location_type"] == "Pin:":
                    # TODO
                    pass
            index += 1
            pass
        if val["type"] == "IPIN":
            index += 1
            pass
        if val["type"] == "SINK":
            index += 1
            pass
        

def map_edge_connection_box_config_to_bits(x, y, edge):
    if get_edge_connection_box_config(x, y, edge) == connection_box_chan_0:
        return "000"
    if get_edge_connection_box_config(x, y, edge) == connection_box_chan_1:
        return "001"
    if get_edge_connection_box_config(x, y, edge) == connection_box_chan_2:
        return "010"
    if get_edge_connection_box_config(x, y, edge) == connection_box_chan_3:
        return "011"
    if get_edge_connection_box_config(x, y, edge) == connection_box_chan_4:
        return "100"
    if get_edge_connection_box_config(x, y, edge) == connection_box_chan_5:
        return "101"
    if get_edge_connection_box_config(x, y, edge) == connection_box_chan_6:
        return "110"
    if get_edge_connection_box_config(x, y, edge) == connection_box_chan_7:
        return "111"

def map_connection_box_config_to_bits(lutx, luty, side):
    if side == "left" or side == "bottom":
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_0:
            error(f"The {side} connection box of the LUT at ({lutx},{luty}) is connected to channel 0, which is invalid.")
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_1:
            error(f"The {side} connection box of the LUT at ({lutx},{luty}) is connected to channel 1, which is invalid.")
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_2:
            return "00"
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_3:
            return "01"
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_4:
            error(f"The {side} connection box of the LUT at ({lutx},{luty}) is connected to channel 4, which is invalid.")
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_5:
            error(f"The {side} connection box of the LUT at ({lutx},{luty}) is connected to channel 5, which is invalid.")
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_6:
            return "10"
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_7:
            return "11"

    if side == "right" or side == "top":
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_0:
            return "00"
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_1:
            return "01"
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_2:
            error(f"The {side} connection box of the LUT at ({lutx},{luty}) is connected to channel 2, which is invalid.")
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_3:
            error(f"The {side} connection box of the LUT at ({lutx},{luty}) is connected to channel 3, which is invalid.")
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_4:
            return "10"
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_5:
            return "11"
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_6:
            error(f"The {side} connection box of the LUT at ({lutx},{luty}) is connected to channel 6, which is invalid.")
        if get_connection_box_config(lutx, luty, side) == connection_box_chan_7:
            error(f"The {side} connection box of the LUT at ({lutx},{luty}) is connected to channel 7, which is invalid.")
        
def is_normal_switch_box(x, y):
    if x > 0 and x < array_width - 1 - 1 and y > 0 and y < array_height - 1 - 1:
        return True
    else:
        return False

def is_left_edge_switch_box(x, y):
    if x == 0 and y > 0 and y < array_height - 1 - 1:
        return True
    else:
        return False

def is_top_edge_switch_box(x, y):
    if x > 0 and x < array_width - 1 - 1 and y == array_height - 1 - 1:
        return True
    else:
        return False

def is_top_right_corner_switch_box(x, y):
    

def map_switch_box_config_to_bits(x, y):
    output = ""
    # case for normal switchbox
    if is_normal_switch_box(x,y):
        # iterate [0,3]
        for i in range(channel_width/2):
            # right_to_left[i]
            if get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_clb:
                if i == 0 or i == 1:
                    output.append("00")
                else:
                    print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_left:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_bottom:
                output.append("11")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_right:
                output.append("01")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_top:
                output.append("10")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_io_pad:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_unknown:
                print("DELETETHISERROR")
                output.append("ARBITRARY")

            # left_to_right[i]
            if get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_clb:
                if i == 0 or i == 1:
                    output.append("01")
                else:
                    print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_left:
                output.append("00")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_bottom:
                output.append("11")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_right:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_top:
                output.append("10")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_io_pad:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_unknown:
                print("DELETETHISERROR")
                output.append("ARBITRARY")
            
            # down_to_up[i]
            if get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_clb:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_left:
                output.append("00")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_bottom:
                output.append("11")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_right:
                output.append("01")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_top:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertial") == switch_box_choose_io_pad:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_unknown:
                print("DELETETHISERROR")
                output.append("ARBITRARY")

            # up_to_down[i]
            if get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_clb:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_left:
                output.append("00")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_bottom:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_right:
                output.append("01")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_top:
                output.append("10")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_io_pad:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_unknown:
                print("DELETETHISERROR")
                output.append("ARBITRARY")

    if is_left_edge_switch_box(x,y):
        # iterate [0,3]
        for i in range(channel_width/2):
            # right_to_left[i]
            if get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_clb:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_left:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_bottom:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_right:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_top:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_io_pad:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_unknown:
                print("EXPECTED")
                output.append("ARBITRARY")

            # left_to_right[i]
            if get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_clb:
                if i == 0 or i == 1:
                    output.append("01")
                else:
                    print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_left:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_bottom:
                output.append("11")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_right:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_top:
                output.append("10")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_io_pad:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_unknown:
                print("DELETETHISERROR")
                output.append("ARBITRARY")
            
            # down_to_up[i]
            if get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_clb:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_left:
                output.append("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_bottom:
                output.append("11")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_right:
                output.append("01")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_top:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertial") == switch_box_choose_io_pad:
                print("TODO RUDRA")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_unknown:
                print("DELETETHISERROR")
                output.append("ARBITRARY")

            # up_to_down[i]
            if get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_clb:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_left:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_bottom:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_right:
                output.append("01")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_top:
                output.append("10")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_io_pad:
                print("TODO RUDRA")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_unknown:
                print("DELETETHISERROR")
                output.append("ARBITRARY")

    if is_top_edge_switch_box(x,y):
        # iterate [0,3]
        for i in range(channel_width/2):
            # right_to_left[i]
            if get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_clb:
                if i == 0 or i == 1:
                    output.append("00")
                else:
                    print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_left:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_bottom:
                output.append("11")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_right:
                output.append("01")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_top:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_io_pad:
                print("TODO RUDRA")
            elif get_switch_box_config(x, y, 2*i+1, "horizontal") == switch_box_choose_unknown:
                print("DELETETHISERROR")
                output.append("ARBITRARY")

            # left_to_right[i]
            if get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_clb:
                if i == 0 or i == 1:
                    output.append("01")
                else:
                    print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_left:
                output.append("00")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_bottom:
                output.append("11")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_right:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_top:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_io_pad:
                print("TODO RUDRA")
            elif get_switch_box_config(x, y, 2*i, "horizontal") == switch_box_choose_unknown:
                print("DELETETHISERROR")
                output.append("ARBITRARY")
            
            # down_to_up[i]
            if get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_clb:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_left:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_bottom:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_right:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_top:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertial") == switch_box_choose_io_pad:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i, "vertical") == switch_box_choose_unknown:
                print("EXPECTED")
                output.append("ARBITRARY")

            # up_to_down[i]
            if get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_clb:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_left:
                output.append("00")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_bottom:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_right:
                output.append("01")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_top:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_io_pad:
                print("ERROR")
            elif get_switch_box_config(x, y, 2*i+1, "vertical") == switch_box_choose_unknown:
                print("DELETETHISERROR")
                output.append("ARBITRARY")

    if is_top_right_corner_switch_box(x,y):



        


def generate_bitstream_from_config_arrays():
    return


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

    print("lut configs:")
    print(lut_configs)
    print("\n\n\n\n")

    print("connection box configs:")
    print(connection_box_configs)
    print("\n\n\n\n")

    print("switch box configs:")
    print(switch_box_configs)
    print("\n\n\n\n")

    print("edge connection box configs:")
    print("left edge:")
    print(left_edge_connection_box_config)
    print("bottom edge:")
    print(bottom_edge_connection_box_config)
    print("right edge:")
    print(right_edge_connection_box_config)
    print("top edge:")
    print(top_edge_connection_box_config)
    print("\n\n\n\n")