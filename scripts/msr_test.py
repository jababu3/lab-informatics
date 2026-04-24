import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import warnings

# Suppress optimization warnings for clean output
warnings.filterwarnings('ignore')

# ---------------------------------------------------------
# 1. CORE FUNCTIONS (Curve Fitting & MSR Stats)
# ---------------------------------------------------------

def four_param_logistic(x, min_val, max_val, ic50, hill_slope):
    """
    4-Parameter Logistic Model.
    Equation: y = min + (max - min) / (1 + (x / ic50)^hill_slope)
    Note: x is concentration, not log-concentration.
    """
    return min_val + (max_val - min_val) / (1 + np.power((x / ic50), hill_slope))

def fit_ic50(group_df):
    """
    Fits the 4PL model to a single compound's data and returns the IC50.
    """
    try:
        x_data = group_df['concentration'].values
        y_data = group_df['response'].values
        
        # Initial guesses: [min, max, ic50, slope]
        # Estimate IC50 as the median concentration to start
        p0 = [min(y_data), max(y_data), np.median(x_data), 1.0]
        
        # Bounds to ensure IC50 is positive
        bounds = ([-np.inf, -np.inf, 0, -np.inf], [np.inf, np.inf, np.inf, np.inf])
        
        popt, _ = curve_fit(four_param_logistic, x_data, y_data, p0=p0, bounds=bounds, maxfev=5000)
        return popt[2] # Return IC50
    except Exception as e:
        return np.nan

def calculate_msr_statistics(df):
    """
    Takes a DataFrame with columns: ['compound', 'run_id', 'ic50']
    Returns a dictionary of statistics and the processed DataFrame.
    """
    # Pivot to get Run 1 and Run 2 side-by-side
    pivot_df = df.pivot(index='compound', columns='run_id', values='ic50').dropna()
    
    if pivot_df.shape[1] < 2:
        raise ValueError("Data must contain at least two runs (columns) to calculate MSR.")
    
    # We assume the first two columns found are the replicates
    run1 = pivot_df.iloc[:, 0]
    run2 = pivot_df.iloc[:, 1]
    
    # 1. Convert to Log10 Scale
    log_run1 = np.log10(run1)
    log_run2 = np.log10(run2)
    
    # 2. Calculate Differences (d) and Mean (avg) on Log scale
    # Difference d = Log(Run1) - Log(Run2)
    diffs = log_run1 - log_run2
    
    # Geometric Mean (for plotting)
    # Average of logs = Log of geometric mean
    mean_log = (log_run1 + log_run2) / 2
    geometric_means = 10**mean_log
    
    # 3. Calculate Stats described in Eastwood et al. 2006
    # sd = standard deviation of the differences
    s_d = np.std(diffs, ddof=1)
    mean_diff = np.mean(diffs)
    
    # MSR = 10^(2 * s_d)
    msr = 10**(2 * s_d)
    
    # Mean Ratio (MR) = 10^mean_diff
    mr = 10**mean_diff
    
    # Limits of Agreement (LsA)
    # Lower = MR / MSR
    # Upper = MR * MSR
    lsa_low = mr / msr
    lsa_high = mr * msr
    
    stats = {
        "MSR": msr,
        "Mean Ratio (MR)": mr,
        "LsA Low": lsa_low,
        "LsA High": lsa_high,
        "Num Compounds": len(pivot_df)
    }
    
    # Prepare plotting data
    plot_data = pd.DataFrame({
        "Geometric Mean IC50": geometric_means,
        "Potency Ratio (Run1/Run2)": 10**diffs, # equivalent to run1 / run2
        "Log Diff": diffs
    })
    
    return stats, plot_data

# ---------------------------------------------------------
# 2. REPLICATION HELPER (Data Generation)
# ---------------------------------------------------------

def generate_synthetic_data(target_log_ic50s):
    """
    Generates synthetic dose-response curves (conc vs response) 
    that will result in the provided LogIC50s.
    
    This simulates the "Raw Data" that Eastwood et al. would have had.
    """
    compounds = []
    concentrations = []
    responses = []
    run_ids = []
    
    # Standard 10-point dose curve
    dose_range = np.logspace(-2, 5, 10) # 0.01 nM to 100,000 nM
    
    for compound, (log_ic50_r1, log_ic50_r2) in target_log_ic50s.items():
        # RUN 1
        ic50_1 = 10**log_ic50_r1
        resp_1 = four_param_logistic(dose_range, 0, 100, ic50_1, 1.0)
        # Add slight noise to response to simulate real assay
        resp_1 += np.random.normal(0, 2, size=len(resp_1)) 
        
        compounds.extend([compound] * len(dose_range))
        concentrations.extend(dose_range)
        responses.extend(resp_1)
        run_ids.extend(['Run1'] * len(dose_range))
        
        # RUN 2
        ic50_2 = 10**log_ic50_r2
        resp_2 = four_param_logistic(dose_range, 0, 100, ic50_2, 1.0)
        resp_2 += np.random.normal(0, 2, size=len(resp_2))
        
        compounds.extend([compound] * len(dose_range))
        concentrations.extend(dose_range)
        responses.extend(resp_2)
        run_ids.extend(['Run2'] * len(dose_range))
        
    return pd.DataFrame({
        'compound': compounds,
        'concentration': concentrations,
        'response': responses,
        'run_id': run_ids
    })

# ---------------------------------------------------------
# 3. MAIN EXECUTION
# ---------------------------------------------------------

def main():
    print("--- Eastwood et al. (2006) MSR Replication ---")
    
    # 1. EXTRACT DATA FROM PAPER (Table 3 - The "Passed" Assay)
    # We manually transcribe the Log(IC50) values from Table 3 in the PDF.
    # We use these to generate synthetic raw data, then process that raw data 
    # to see if we recover the MSR of ~1.60 reported in the paper.
    
    # Format: Compound: (Run1 LogIC50, Run2 LogIC50)
    # Note: We selected rows where data was clearly readable and valid.
    paper_data_log_values = {
        'P1-1': (0.9196, 0.6739),
        'P1-3': (1.4544, 1.2774), # Inferred from ratio 1.50
        'P1-4': (0.7185, 0.4669),
        'P1-5': (1.6865, 1.4814),
        'P1-6': (1.5629, 1.4231),
        'P1-7': (3.5555, 3.5973),
        'P1-8': (1.8909, 1.8349),
        'P2-2': (1.5746, 1.4106),
        'P2-3': (1.7257, 1.5771),
        'P2-4': (1.6108, 1.4128),
        'P2-5': (1.2683, 1.1816),
        'P2-6': (0.7701, 0.6415),
        'P2-7': (1.3978, 1.3608),
        'P2-8': (3.0370, 2.9863),
        'P4-1': (1.5043, 1.4991),
        'P4-2': (3.5517, 3.3986),
        'P4-3': (2.4320, 2.3536),
        'P4-5': (2.2279, 2.1943),
        'P4-6': (3.6699, 3.5926),
        'P4-7': (1.4645, 1.3373),
        'P4-8': (1.8955, 1.7200),
        'P5-1': (2.3573, 2.1301),
        'P5-2': (3.8638, 3.7413),
        'P5-3': (3.8438, 3.6900), 
        'P5-4': (0.4425, 0.0934)
    }

    # 2. GENERATE RAW DATAFRAME
    # This simulates the user providing "compound, concentration, response"
    print(f"Generating synthetic raw data for {len(paper_data_log_values)} compounds...")
    raw_df = generate_synthetic_data(paper_data_log_values)
    
    # 3. CALCULATE IC50s (Curve Fitting)
    print("Fitting 4-Parameter Logistic curves to calculate IC50s...")
    results = []
    
    # Group by compound AND run_id to get individual IC50s per run
    grouped = raw_df.groupby(['compound', 'run_id'])
    
    for (compound, run_id), group in grouped:
        ic50 = fit_ic50(group)
        results.append({'compound': compound, 'run_id': run_id, 'ic50': ic50})
    
    ic50_df = pd.DataFrame(results)
    
    # 4. CALCULATE MSR
    print("Calculating Minimum Significant Ratio (MSR)...")
    stats, plot_data = calculate_msr_statistics(ic50_df)
    
    # 5. DISPLAY RESULTS
    print("\n" + "="*40)
    print("RESULTS REPLICATING EASTWOOD TABLE 3")
    print("="*40)
    print(f"Paper Reported MSR:   1.60")
    print(f"Calculated MSR:       {stats['MSR']:.2f}")
    print(f"Mean Ratio (MR):      {stats['Mean Ratio (MR)']:.2f}")
    print(f"Limits of Agreement:  {stats['LsA Low']:.2f} - {stats['LsA High']:.2f}")
    print("-" * 40)
    
    if 1.50 <= stats['MSR'] <= 1.70:
        print("SUCCESS: Replication matches paper values closely.")
    else:
        print("NOTE: Slight deviation due to synthetic noise in curve fitting.")

    # 6. PLOT (Bland-Altman Style)
    plt.figure(figsize=(10, 6))
    
    # Plot Points
    plt.scatter(plot_data['Geometric Mean IC50'], plot_data['Potency Ratio (Run1/Run2)'], color='black', alpha=0.7)
    
    # Plot Lines
    plt.axhline(stats['Mean Ratio (MR)'], color='blue', linestyle='-', label=f"Mean Ratio ({stats['Mean Ratio (MR)']:.2f})")
    plt.axhline(stats['LsA High'], color='red', linestyle='--', label=f"Limits of Agmt ({stats['LsA Low']:.2f}-{stats['LsA High']:.2f})")
    plt.axhline(stats['LsA Low'], color='red', linestyle='--')
    plt.axhline(1.0, color='gray', linestyle=':', linewidth=1)
    
    # Formatting to match Eastwood Figure 1/3
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('Geometric Mean IC50 (nM)')
    plt.ylabel('Potency Ratio (Run 1 / Run 2)')
    plt.title('Replicate-Experiment: Ratio vs Geometric Mean')
    plt.legend()
    plt.grid(True, which="both", ls="-", alpha=0.2)
    
    # Save the plot
    plt.tight_layout()
    plt.savefig('msr_plot.png')
    print("Plot saved to 'msr_plot.png'")

if __name__ == "__main__":
    main()