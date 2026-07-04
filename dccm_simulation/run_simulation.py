import os
import numpy as np
import matplotlib.pyplot as plt
from simulation import run_deadline_factor_experiment, run_task_count_experiment

# Styling settings to match standard scientific publications (MATLAB style)
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['text.color'] = 'black'
plt.rcParams['axes.labelcolor'] = 'black'
plt.rcParams['xtick.color'] = 'black'
plt.rcParams['ytick.color'] = 'black'

# Color schemes from the paper
COLORS_FIG2 = {
    "DCCM": "#1a2672",     # Dark Navy Blue
    "BDAS": "#00a2e8",     # Cyan / Light Blue
    "HEFT": "#8ebe6c",     # Soft Green
    "BDHEFT": "#fff200"    # Bright Yellow
}

COLORS_FIG3 = {
    "DCCM": "#0072bd",     # MATLAB Default Blue
    "BDAS": "#d95319",     # MATLAB Default Orange
    "HEFT": "#edb120",     # MATLAB Default Yellow
    "BDHEFT": "#7e2f8e"    # MATLAB Default Purple
}

def apply_matlab_style(ax):
    """
    Applies standard MATLAB-style axis spines and ticks.
    """
    ax.spines['top'].set_visible(True)
    ax.spines['right'].set_visible(True)
    ax.spines['left'].set_visible(True)
    ax.spines['bottom'].set_visible(True)
    ax.spines['top'].set_color('black')
    ax.spines['right'].set_color('black')
    ax.spines['left'].set_color('black')
    ax.spines['bottom'].set_color('black')
    ax.spines['top'].set_linewidth(0.8)
    ax.spines['right'].set_linewidth(0.8)
    ax.spines['left'].set_linewidth(0.8)
    ax.spines['bottom'].set_linewidth(0.8)
    
    # Tick marks pointing inward on all sides
    ax.tick_params(direction='in', top=True, right=True, left=True, bottom=True, labelsize=10)
    ax.grid(False) # No grid lines, matching the paper

def create_success_rate_plots(all_results, save_path):
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    
    workflows = ["Montage", "Ligo", "Cybershake", "Epigenomics"]
    df_values = [4, 8, 12, 16]
    labels = ["(a) Montage", "(b) Ligo", "(c) Cybershake", "(d) Epigenomics"]
    
    for idx, name in enumerate(workflows):
        ax = axes[idx // 2, idx % 2]
        res = all_results[name]
        
        x = np.arange(len(df_values))
        width = 0.18
        
        # Plotting bars matching paper colors
        ax.bar(x - 1.5*width, res["DCCM"]["sr"], width, label="DCCM", color=COLORS_FIG2["DCCM"], edgecolor='black', linewidth=0.5)
        ax.bar(x - 0.5*width, res["BDAS"]["sr"], width, label="BDAS", color=COLORS_FIG2["BDAS"], edgecolor='black', linewidth=0.5)
        ax.bar(x + 0.5*width, res["HEFT"]["sr"], width, label="HEFT", color=COLORS_FIG2["HEFT"], edgecolor='black', linewidth=0.5)
        ax.bar(x + 1.5*width, res["BDHEFT"]["sr"], width, label="BDHEFT", color=COLORS_FIG2["BDHEFT"], edgecolor='black', linewidth=0.5)
        
        ax.set_ylabel("Success Rate (%)", fontsize=11)
        ax.set_xlabel(f"Deadline Factor (DF)\n\n{labels[idx]}", fontsize=11, labelpad=8)
        ax.set_xticks(x)
        ax.set_xticklabels([str(df) for df in df_values])
        ax.set_ylim(0, 115) # room for legend
        ax.set_yticks([0, 20, 40, 60, 80, 100])
        
        apply_matlab_style(ax)
        
        # Centered legend inside each plot at the top
        ax.legend(loc="upper center", ncol=4, frameon=True, edgecolor='black', facecolor='white', fontsize=8.5, columnspacing=1.0, handletextpad=0.4)
            
    plt.tight_layout()
    # Add figure caption at the bottom
    plt.figtext(0.5, 0.02, "FIGURE 2. Performance comparison of success rate for Montage, Ligo, Cybershake and Epigenomics.", 
                ha='center', fontsize=12, fontweight='bold', family='sans-serif')
    
    # Adjust spacing to fit the figure text
    plt.subplots_adjust(bottom=0.12)
    plt.savefig(os.path.join(save_path, "success_rate_comparison.png"), dpi=300)
    plt.close()
    print("Saved success_rate_comparison.png")

def create_cost_ratio_plots(all_results, save_path):
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    
    workflows = ["Montage", "Ligo", "Cybershake", "Epigenomics"]
    df_values = [4, 8, 12, 16]
    labels = ["(a) Montage", "(b) Ligo", "(c) Cybershake", "(d) Epigenomics"]
    
    # Different Y limits per paper charts
    y_limits = {
        "Montage": 3.2,
        "Ligo": 4.2,
        "Cybershake": 2.7,
        "Epigenomics": 5.2
    }
    
    for idx, name in enumerate(workflows):
        ax = axes[idx // 2, idx % 2]
        res = all_results[name]
        
        x = np.arange(len(df_values))
        width = 0.18
        
        # Plotting bars matching Figure 3 Matlab colors
        ax.bar(x - 1.5*width, res["DCCM"]["cost"], width, label="DCCM", color=COLORS_FIG3["DCCM"], edgecolor='black', linewidth=0.5)
        ax.bar(x - 0.5*width, res["BDAS"]["cost"], width, label="BDAS", color=COLORS_FIG3["BDAS"], edgecolor='black', linewidth=0.5)
        ax.bar(x + 0.5*width, res["HEFT"]["cost"], width, label="HEFT", color=COLORS_FIG3["HEFT"], edgecolor='black', linewidth=0.5)
        ax.bar(x + 1.5*width, res["BDHEFT"]["cost"], width, label="BDHEFT", color=COLORS_FIG3["BDHEFT"], edgecolor='black', linewidth=0.5)
        
        ax.set_ylabel("Cost Ratio", fontsize=11)
        ax.set_xlabel(f"Deadline Factor (DF)\n\n{labels[idx]}", fontsize=11, labelpad=8)
        ax.set_xticks(x)
        ax.set_xticklabels([str(df) for df in df_values])
        ax.set_ylim(0, y_limits[name])
        
        apply_matlab_style(ax)
        
        # Centered legend inside each plot at the top
        ax.legend(loc="upper center", ncol=4, frameon=True, edgecolor='black', facecolor='white', fontsize=8.5, columnspacing=1.0, handletextpad=0.4)
            
    plt.tight_layout()
    plt.figtext(0.5, 0.02, "FIGURE 3. Performance comparison of cost ratio for Montage, Ligo, Cybershake and Epigenomics.", 
                ha='center', fontsize=12, fontweight='bold', family='sans-serif')
    
    plt.subplots_adjust(bottom=0.12)
    plt.savefig(os.path.join(save_path, "cost_ratio_comparison.png"), dpi=300)
    plt.close()
    print("Saved cost_ratio_comparison.png")

def create_mean_load_plots(all_load_results, save_path):
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    
    workflows = ["Montage", "Ligo", "Cybershake", "Epigenomics"]
    task_counts = [30, 60, 90, 120, 150]
    labels = ["(a)", "(b)", "(c)", "(d)"]
    
    # Different Y limits per Figure 4 load charts
    y_limits = {
        "Montage": 0.62,
        "Ligo": 0.72,
        "Cybershake": 0.92,
        "Epigenomics": 0.92
    }
    
    for idx, name in enumerate(workflows):
        ax = axes[idx // 2, idx % 2]
        res = all_load_results[name]
        
        x = np.arange(len(task_counts))
        width = 0.3
        
        # Fig 4 uses Matlab default blue and orange
        ax.bar(x - 0.5*width, res["DCCM"], width, label="DCCM", color=COLORS_FIG3["DCCM"], edgecolor='black', linewidth=0.5)
        ax.bar(x + 0.5*width, res["BDAS"], width, label="BDAS", color=COLORS_FIG3["BDAS"], edgecolor='black', linewidth=0.5)
        
        ax.set_ylabel("Mean Load", fontsize=11)
        ax.set_xlabel(f"Number of Tasks\n\n{labels[idx]}", fontsize=11, labelpad=8)
        ax.set_xticks(x)
        ax.set_xticklabels([str(tc) for tc in task_counts])
        ax.set_ylim(0, y_limits[name])
        
        apply_matlab_style(ax)
        
        ax.legend(loc="upper left", frameon=True, edgecolor='black', facecolor='white', fontsize=9)
            
    plt.tight_layout()
    plt.figtext(0.5, 0.02, "FIGURE 4. Performance Comparison of Mean Load.", 
                ha='center', fontsize=12, fontweight='bold', family='sans-serif')
    
    plt.subplots_adjust(bottom=0.12)
    plt.savefig(os.path.join(save_path, "mean_load_comparison.png"), dpi=300)
    plt.close()
    print("Saved mean_load_comparison.png")

if __name__ == "__main__":
    plot_dir = "dccm_simulation/plots"
    os.makedirs(plot_dir, exist_ok=True)
    
    workflows = ["Montage", "Ligo", "Cybershake", "Epigenomics"]
    
    # 1. Run Deadline Factor Experiment
    df_results = {}
    for wf in workflows:
        df_results[wf] = run_deadline_factor_experiment(wf, df_values=[4, 8, 12, 16], num_runs=1)
        
    create_success_rate_plots(df_results, plot_dir)
    create_cost_ratio_plots(df_results, plot_dir)
    
    # 2. Run Task Count Experiment
    load_results = {}
    for wf in workflows:
        load_results[wf] = run_task_count_experiment(wf, task_counts=[30, 60, 90, 120, 150], num_runs=1)
        
    create_mean_load_plots(load_results, plot_dir)
    
    print("\nSimulation complete! All plots are saved in 'dccm_simulation/plots/'.")
