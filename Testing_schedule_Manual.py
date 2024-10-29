# This script analyzes the dataset
# The user should enter the "Load-up" and "Shed"
# starting time and duration
# The output of the scrip is a data graph with
# shedding the "Load-up" and "Shed" periods


import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Read the CSV file
file_path = '/content/drive/MyDrive/PSU/GoogleColab/GridStatus/DAMDatasets/DAM10032024.csv'
df = pd.read_csv(file_path)

# Convert the 'interval_start_utc' column to datetime
df['interval_start_utc'] = pd.to_datetime(df['interval_start_utc'])

# Shift the time 7 hours back
df['interval_start_utc'] = df['interval_start_utc'] - pd.Timedelta(hours=7)

def identify_peak_periods(df, prominence_threshold=0.05, distance=1, width=1):
    df = df.sort_values('interval_start_utc')
    peaks, properties = find_peaks(df['lmp'], prominence=prominence_threshold*df['lmp'].max(),
                                   distance=distance, width=width)
    peak_times = df['interval_start_utc'].iloc[peaks]
    peak_prices = df['lmp'].iloc[peaks]
    peak_times = peak_times.dt.floor('H')
    peak_data = sorted(zip(peak_times, peak_prices), key=lambda x: x[0])
    return peak_data

def manual_load_up_times(df, peak_data):
    load_up_times = []
    for peak_time, peak_price in peak_data:
        print(f"\nPeak at {peak_time.strftime('%Y-%m-%d %H:%M')} (LMP: ${peak_price:.2f})")
        hours_before = int(input("Hours before peak to start load-up: "))
        duration = int(input("Duration of load-up (hours): "))

        load_up_start = peak_time - pd.Timedelta(hours=hours_before)
        load_up_end = load_up_start + pd.Timedelta(hours=duration)

        load_up_times.append((load_up_start, load_up_end, peak_time))
    return load_up_times

def manual_shed_periods(df, peak_data, load_up_times):
    shed_periods = []
    for (load_up_start, load_up_end, peak_time), (peak_time, peak_price) in zip(load_up_times, peak_data):
        print(f"\nPeak at {peak_time.strftime('%Y-%m-%d %H:%M')} (LMP: ${peak_price:.2f})")
        print(f"Load-up ends at {load_up_end.strftime('%Y-%m-%d %H:%M')}")
        hours_after_loadup = float(input("Hours after load-up to start shed: "))
        duration = float(input("Duration of shed (hours): "))

        shed_start = load_up_end + pd.Timedelta(hours=hours_after_loadup)
        shed_end = shed_start + pd.Timedelta(hours=duration)

        shed_periods.append((shed_start, shed_end, peak_time))
    return shed_periods

def manual_recovery_load_up_time(shed_periods):
    recovery_times = []
    include_recovery = input("\nDo you want to include recovery load-up? (yes/no): ").lower() == 'yes'

    if include_recovery:
        for shed_start, shed_end, peak_time in shed_periods:
            print(f"\nShed period ends at {shed_end.strftime('%Y-%m-%d %H:%M')}")
            hours_after_shed = float(input("Hours after shed to start recovery: "))
            duration = float(input("Duration of recovery (hours): "))

            recovery_start = shed_end + pd.Timedelta(hours=hours_after_shed)
            recovery_end = recovery_start + pd.Timedelta(hours=duration)

            recovery_times.append((recovery_start, recovery_end, peak_time))

    return recovery_times, include_recovery

# Identify peaks
peak_data = identify_peak_periods(df)

# Manual input for load-up times
load_up_times = manual_load_up_times(df, peak_data)

# Manual input for shed periods
shed_periods = manual_shed_periods(df, peak_data, load_up_times)

# Manual input for recovery load-up times
recovery_times, include_recovery = manual_recovery_load_up_time(shed_periods)

# Visualization
plt.figure(figsize=(12, 6))
plt.plot(df['interval_start_utc'], df['lmp'], color='navy', label='LMP')

for i, (peak_time, peak_price) in enumerate(peak_data):
    plt.axvline(x=peak_time, color=f'C{i+1}', linestyle='--', label=f'Peak {i+1}')
    #plt.text(peak_time, peak_price, f'${peak_price:.2f}',
     #        verticalalignment='bottom', horizontalalignment='center')

for i, (start, end, peak) in enumerate(load_up_times):
    plt.axvspan(start, end, color='green', alpha=0.3, label=f'Load-up {i+1}')

for i, (start, end, peak) in enumerate(shed_periods):
    #plt.axvspan(start, end, color='red', alpha=0.3, hatch='\\', label=f'Shed {i+1}')
    plt.axvspan(start, end, color='red', alpha=0.3, label=f'Shed {i+1}')


if include_recovery:
    for i, (start, end, peak) in enumerate(recovery_times):
        plt.axvspan(start, end, color='blue', alpha=0.3, label=f'Recovery {i+1}')

#plt.title('Locational Marginal Price - CAISO with Peaks, Load-up, Shed, and Recovery Periods')
plt.title('Locational Marginal Price - CAISO - Plan E')

plt.xlabel('Time')
plt.ylabel('LMP ($)')

hours = mdates.HourLocator(interval=1)
h_fmt = mdates.DateFormatter('%H:%M')
plt.gca().xaxis.set_major_locator(hours)
plt.gca().xaxis.set_major_formatter(h_fmt)
plt.xlim(df['interval_start_utc'].min(), df['interval_start_utc'].max())
plt.gca().xaxis.set_minor_locator(mdates.HourLocator())
plt.xticks(rotation=0)
plt.grid(True, linestyle='--', alpha=0.7)

legend_elements = [plt.Line2D([0], [0], color='navy', label='LMP')]
legend_elements.extend([plt.Line2D([0], [0], color=f'C{i+1}', linestyle='--', label=f'Peak {i+1}') for i in range(len(peak_data))])
legend_elements.extend([plt.Rectangle((0, 0), 1, 1, fc='green', alpha=0.3, label=f'Load-up {i+1}') for i in range(len(load_up_times))])
#legend_elements.extend([plt.Rectangle((0, 0), 1, 1, fc='red', alpha=0.3, hatch='\\', label=f'Shed {i+1}') for i in range(len(shed_periods))])
legend_elements.extend([plt.Rectangle((0, 0), 1, 1, fc='red', alpha=0.3, label=f'Shed {i+1}') for i in range(len(shed_periods))])

if include_recovery:
    #legend_elements.extend([plt.Rectangle((0, 0), 1, 1, fc='blue', alpha=0.3, label=f'Load-up 2 {i+1}') for i in range(len(recovery_times))])
    legend_elements.extend([plt.Rectangle((0, 0), 1, 1, fc='blue', alpha=0.3, label=f'Load-up 2') for i in range(len(recovery_times))])


plt.legend(handles=legend_elements)
plt.tight_layout()
plt.savefig('/content/drive/MyDrive/PSU/GoogleColab/GridStatus/Plan_E.png',dpi=300)
plt.show()

# Print information
print("\nIdentified Peaks:")
for i, (peak_time, peak_price) in enumerate(peak_data):
    print(f"Peak {i+1}:")
    print(f"  Time: {peak_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  LMP: ${peak_price:.2f}")
    print()

print("Load-up Periods:")
for i, (start, end, peak) in enumerate(load_up_times):
    print(f"Load-up {i+1}:")
    print(f"  Start: {start.strftime('%Y-%m-%d %H:%M')}")
    print(f"  End: {end.strftime('%Y-%m-%d %H:%M')}")
    print(f"  For Peak at: {peak.strftime('%Y-%m-%d %H:%M')}")
    print()

print("Shed Periods:")
for i, (start, end, peak) in enumerate(shed_periods):
    print(f"Shed {i+1}:")
    print(f"  Start: {start.strftime('%Y-%m-%d %H:%M')}")
    print(f"  End: {end.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Duration: {(end - start).total_seconds() / 3600:.2f} hours")
    print(f"  For Peak at: {peak.strftime('%Y-%m-%d %H:%M')}")
    print()

if include_recovery:
    print("Recovery Load-up Times:")
    for i, (start, end, peak_time) in enumerate(recovery_times):
        print(f"Recovery {i+1}:")
        print(f"  Start: {start.strftime('%Y-%m-%d %H:%M')}")
        print(f"  End: {end.strftime('%Y-%m-%d %H:%M')}")
        print(f"  For Peak at: {peak_time.strftime('%Y-%m-%d %H:%M')}")
        print()


# Function to create a list of dictionaries with the required information
def create_data_for_csv(load_up_times, shed_periods, recovery_times, include_recovery):
    data = []
    for i, ((lu_start, lu_end, _), (s_start, s_end, _)) in enumerate(zip(load_up_times, shed_periods)):
        row = {
            'LU_time': lu_start.strftime('%H:%M'),
            'LU_duration': (lu_end - lu_start).total_seconds() / 3600,
            'S_time': s_start.strftime('%H:%M'),
            'S_duration': (s_end - s_start).total_seconds() / 3600,
            'RLU_time': '',
            'RLU_duration': ''
        }
        if include_recovery and i < len(recovery_times):
            rlu_start, rlu_end, _ = recovery_times[i]
            row['RLU_time'] = rlu_start.strftime('%H:%M')
            row['RLU_duration'] = (rlu_end - rlu_start).total_seconds() / 3600
        data.append(row)
    return data

# After all the calculations and user inputs...

# Create the data for the CSV
csv_data = create_data_for_csv(load_up_times, shed_periods, recovery_times, include_recovery)

# Define the output CSV file path
#csv_filename = os.path.splitext(os.path.basename(file_path))[0] + '_schedule.csv'
csv_filename = 'Testing_schedule.csv'

csv_path = os.path.join(os.path.dirname(file_path), csv_filename)

# Write the data to the CSV file
with open(csv_path, 'w', newline='') as csvfile:
    fieldnames = ['LU_time', 'LU_duration', 'S_time', 'S_duration', 'RLU_time', 'RLU_duration']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for row in csv_data:
        writer.writerow(row)

print(f"Schedule data saved as: {csv_path}")
