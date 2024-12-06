# Calculates Tournament Performance Rating (TPR) and Estimated Performance Rating (EPR) in cases of perfect or zero scores
import math

def calculate_win_probability(A, B):
    return 1 / (1 + 10 ** ((B - A) / 400))

def calculate_cpr(m, n, B):

    if m < 0 or m > n:
        raise ValueError("Score m must be between 0 and n.")
    if n <= 0:
        raise ValueError("Number of games n must be positive.")

    return B - ((n+1)/n) * 400 * math.log10((n + 0.5 - m) / (m + 0.5))

def calculate_TPR(m, n, B):
    if m == 0:
        return calculate_cpr(m, n, B)
    elif m == n:
        return calculate_cpr(m, n, B)
    return B - 400 * math.log10((n - m) / m)
