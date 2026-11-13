module network_mode_decode(
 input wire [3:0] control,
 output wire [1:0] branch_enable,
 output wire mode_request,
 output wire network_request
);
 assign branch_enable=control[1:0];
 assign mode_request=control[2];
 assign network_request=control[3];
endmodule
