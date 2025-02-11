def1ch[1];

(* hubbard[d[]] is equivalent to nc[number[d[],UP], number[d[],DO]] *)
H1 = epsilon number[d[]] + U hubbard[d[]];

H = H0 + Hc + H1;

(* All operators which contain d[], except hybridization (Hc). *)
Hselfd = H1;

selfopd = ( Chop @ Expand @ komutator[Hselfd /. params, d[#1, #2]] )&;

(* Evaluate *)
Print["selfopd[CR,UP]=", selfopd[CR, UP]];
Print["selfopd[CR,DO]=", selfopd[CR, DO]];
Print["selfopd[AN,UP]=", selfopd[AN, UP]];
Print["selfopd[AN,DO]=", selfopd[AN, DO]];
