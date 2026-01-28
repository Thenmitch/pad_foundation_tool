# --------------------------------------------------
"""def solve_pad(
    G,
    Q,
    Sur_G,
    Sur_Q,
    q_allow,
    target_utilisation,
    min_width,
    min_depth,
    rounding,
    include_self_weight,
):

    best_solution = None
    best_utilisation = 0.0
    best_volume = None

    # Base loads (excluding pad & surcharge)
    N_ck_initial = gamma_G * G + gamma_Q * Q
    q_target = target_utilisation * q_allow

    t = min_depth
    while t <= DEPTH_SEARCH_LIMIT:

        min_width_45 = 2.0 * t

        A_req = N_ck_initial / q_target
        B = max(math.sqrt(A_req), min_width, min_width_45)

        while True:

            N_ck_sur_G = Sur_G * B**2
            N_ck_sur_Q = Sur_Q * B**2

            W_pad = B**2 * t * GAMMA_CONC if include_self_weight else 0.0

            N_ck = (
                gamma_G * (G + W_pad + N_ck_sur_G)
                + gamma_Q * (Q + N_ck_sur_Q)
            )

            q_ed = N_ck / B**2
            util = q_ed / q_allow

            if util > target_utilisation:
                B += B_REFINE_STEP
            else:
                break

        volume = B**2 * t

        if (
            util > best_utilisation
            or (
                abs(util - best_utilisation) < 1e-6
                and (best_volume is None or volume < best_volume)
            )
        ):
            best_utilisation = util
            best_volume = volume

            best_solution = {
                "B_opt": B,
                "t": t,
                "N_ck_initial": N_ck_initial,
                "q_target": q_target,
            }

        t += DEPTH_STEP

    return best_solution"""