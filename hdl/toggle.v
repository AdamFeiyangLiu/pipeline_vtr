module toggle(
    input logic clk,
    output logic o
);

always @(posedge clk) begin
    o <= ~o;
end

endmodule