HDL ?= hdl/toggle_w_res.v
ARCH ?= arch/Arch_2x2.xml
ROUTE_CHAN_WIDTH ?= 8

hdl_name = $(shell basename $(HDL) .v)

run:
	python3 scripts/taco_flow.py --verilog_file $(HDL) --arch_file $(ARCH) --route_chan_width $(ROUTE_CHAN_WIDTH)
	python3 scripts/gen_pseudo_bitstream.py --fasm_file temp/$(hdl_name).fasm --place_file temp/$(hdl_name).place --route_file temp/$(hdl_name).route 
clean:
	rm -rf temp/
	rm -rf bitstreams/