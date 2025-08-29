HDL ?= hdl/toggle.v
ARCH ?= arch/2x2.xml
ROUTE_CHAN_WIDTH ?= 8



run:
	python3 scripts/taco_flow.py --verilog_file $(HDL) --arch_file $(ARCH) --route_chan_width $(ROUTE_CHAN_WIDTH)

clean:
	rm -rf temp/