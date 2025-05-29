import os
import numpy as np
import argparse

from dem_evaluator import load_and_align_dem, compute_rmse

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Evaluate DEM against ground truth.")
    parser.add_argument("--my_dem_path", type=str, default="my_dem.tif", help="Path to the generated DEM file.")
    parser.add_argument("--gt_dem_path", type=str, default="gt_dem.tif", help="Path to the ground truth DEM file.")
    args = parser.parse_args()

    aligned_pred, aligned_gt = load_and_align_dem(args.my_dem_path, args.gt_dem_path)
    rmse = compute_rmse(aligned_pred, aligned_gt)
    print(f"RMSE between generated DEM and ground truth DEM: {rmse:.4f}")