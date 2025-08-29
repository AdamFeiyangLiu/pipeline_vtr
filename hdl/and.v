module and(
    input logic clk,
    input logic A,
    input logic B,
    output logic C
);

always @(posedge clk) begin
    C <= A & B;
end

endmodule