module toggle_w_res (
    input clk,
    input res,
    output o
);

always @(posedge clk)
begin
    if (res)
    begin
        o <= 1'b0;
    end
    else
    begin
        o <= ~o;
    end
end


endmodule