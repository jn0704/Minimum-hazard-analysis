# Minimum-hazard-analysis

The minimum hazard analysis (MHA) calculates evacuation routes that minimize exposure to building collapse zones between populations and shelters.The model calculates paths that minimize the length of roads traveled that overlap with building collapse zones, rather than consider the overall evacuation distances. 

* Step 1: Identify the path that minimizes road hazards from population node i to shelter node j, where P_i > 0 and C_j > 0
* Step 2: If C_j ≥ P_i, assign P_i to the path. Next, C_j = C_j - P_i and P_i = 0
* Step 3: If C_j < P_i, assign P_i - C_j to the path. Next, C_j = 0 and P_i = P_i - C_j
* Step 4: If the sum of populations or shelter capacities is zero, end the process. If not, we return to step 1
