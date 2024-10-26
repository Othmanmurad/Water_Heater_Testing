# Script for Shed time and duration


# Read the CSV file
file_path = '/content/drive/MyDrive/PSU/GoogleColab/GridStatus/DAMDatasets/DAM10102024.csv'
df = pd.read_csv(file_path)

# Convert the 'interval_start_utc' column to datetime
df['interval_start_utc'] = pd.to_datetime(df['interval_start_utc'])

# Shift the time 7 hours back
df['interval_start_utc'] = df['interval_start_utc'] - pd.Timedelta(hours=7)

def split_day_periods(df):
    """
    Split the dataset into morning (00:00-11:59) and afternoon/evening (12:00-23:59) periods
    """
    df = df.copy()
    df['hour'] = df['interval_start_utc'].dt.hour
    morning_df = df[df['hour'] < 12].copy()
    evening_df = df[df['hour'] >= 12].copy()
    return morning_df, evening_df

def identify_period_peaks(df, prominence_threshold=0.08, distance=4, width=1):
    """
    Modified peak detection with lower evening threshold
    """
    df = df.sort_values('interval_start_utc')
    first_hour = df['interval_start_utc'].iloc[0].hour

    # Lower threshold for evening to ensure peak detection
    if first_hour >= 12:
        prominence_threshold = 0.05  # More sensitive for evening

    price_range = df['lmp'].max() - df['lmp'].min()
    mean_price = df['lmp'].mean()
    std_price = df['lmp'].std()

    peaks, properties = find_peaks(df['lmp'],
                                 prominence=prominence_threshold * price_range,
                                 distance=distance,
                                 width=width,
                                 height=mean_price - 0.25 * std_price)

    peak_times = df['interval_start_utc'].iloc[peaks]
    peak_prices = df['lmp'].iloc[peaks]
    peak_times = peak_times.dt.floor('H')

    # Ensure evening peak detection
    if first_hour >= 12 and len(peaks) == 0:
        # Find highest price point in typical evening peak hours (17-19)
        evening_df = df[df['interval_start_utc'].dt.hour.between(17, 19)]
        if not evening_df.empty:
            max_idx = evening_df['lmp'].idxmax()
            peak_times = pd.Series([df.loc[max_idx, 'interval_start_utc']])
            peak_prices = pd.Series([df.loc[max_idx, 'lmp']])

    peak_data = sorted(zip(peak_times, peak_prices), key=lambda x: x[0])
    return peak_data

def identify_load_up_periods(df_period, peak_data, is_morning=True):
    """
    Modified load-up period identification with fixed durations
    """
    if not peak_data:
        return []

    load_up_periods = []

    for peak_time, _ in peak_data:
        if is_morning:
            # Fixed 2-hour morning load-up ending 1 hour before peak
            end_time = peak_time - pd.Timedelta(hours=2)
            start_time = end_time - pd.Timedelta(hours=2)
        else:
            # Fixed 4-hour evening load-up ending 2 hours before peak
            end_time = peak_time - pd.Timedelta(hours=2)
            start_time = end_time - pd.Timedelta(hours=4)

        load_up_periods.append((start_time, end_time, peak_time))

    return load_up_periods

def identify_shed_periods(df_period, peak_data, is_morning=True):
    """
    Modified shed period identification with flexible end time for both periods
    """
    if not peak_data:
        return []
    
    shed_periods = []
    
    for peak_time, peak_price in peak_data:
        if is_morning:
            # Morning shed starts 2 hour before peak
            start_time = peak_time - pd.Timedelta(hours=2)
        else:
            # Evening shed starts 2 hours before peak
            start_time = peak_time - pd.Timedelta(hours=2)
        
        # Get price at start of shed period
        start_price = df_period[df_period['interval_start_utc'] == start_time]['lmp'].iloc[0]
        
        # Look for price drop below start price after peak
        post_peak = df_period[df_period['interval_start_utc'] > peak_time]
        if not post_peak.empty:
            recovery_times = post_peak[post_peak['lmp'] <= start_price]
            if not recovery_times.empty:
                # End shed when price drops below start price
                end_time = df_period.loc[recovery_times.index[0], 'interval_start_utc']
            else:
                # If price doesn't drop below start price
                if is_morning:
                    # For morning, use end of morning period as maximum
                    end_time = df_period[df_period['interval_start_utc'].dt.hour < 12]['interval_start_utc'].max()
                else:
                    # For evening, use end of day
                    end_time = df_period['interval_start_utc'].max()
        else:
            # Fallback if no post-peak data
            if is_morning:
                end_time = df_period[df_period['interval_start_utc'].dt.hour < 12]['interval_start_utc'].max()
            else:
                end_time = df_period['interval_start_utc'].max()
        
        shed_periods.append((start_time, end_time, peak_time))
    
    return shed_periods

def resolve_period_overlaps(load_up_periods, shed_periods):
    """
    Simplified overlap resolution with fixed rules
    """
    if not load_up_periods or not shed_periods:
        return load_up_periods, shed_periods

    adjusted_load_up = []

    for load_start, load_end, load_peak in load_up_periods:
        valid_period = True
        for shed_start, shed_end, _ in shed_periods:
            if (load_start < shed_end) and (shed_start < load_end):
                # Any overlap with shed period invalidates load-up
                valid_period = False
                break

        if valid_period:
            adjusted_load_up.append((load_start, load_end, load_peak))

    return adjusted_load_up, shed_periods

def visualize_split_peaks(df, morning_peaks, evening_peaks, morning_loadup, evening_loadup,
                         morning_shed, evening_shed):
    """
    Create visualization of price data with all periods
    """
    plt.figure(figsize=(12, 6))

    # Plot full day price curve
    plt.plot(df['interval_start_utc'], df['lmp'], color='navy', label='LMP', linewidth=2)

    # Plot morning peaks
    for i, (peak_time, peak_price) in enumerate(morning_peaks):
        plt.axvline(x=peak_time, color='red', linestyle='--',
                   label=f'Morning Peak {i+1}', alpha=0.7)
        #plt.scatter(peak_time, peak_price, color='red', s=100, zorder=5)
       # plt.text(peak_time, peak_price + 2, f'${peak_price:.2f}\n{peak_time.strftime("%H:%M")}',
               # verticalalignment='bottom', horizontalalignment='center')

    # Plot evening peaks
    for i, (peak_time, peak_price) in enumerate(evening_peaks):
        plt.axvline(x=peak_time, color='red', linestyle='--',
                   label=f'Evening Peak {i+1}', alpha=0.7)
    #    plt.scatter(peak_time, peak_price, color='red', s=100, zorder=5)
     #   plt.text(peak_time, peak_price + 2, f'${peak_price:.2f}\n{peak_time.strftime("%H:%M")}',
      #          verticalalignment='bottom', horizontalalignment='center')

    # Plot morning load-up periods
    for start_time, end_time, _ in morning_loadup:
        plt.axvspan(start_time, end_time, color='lightblue', alpha=0.3,
                   label='Morning Load-up')

    # Plot evening load-up periods
    for start_time, end_time, _ in evening_loadup:
        plt.axvspan(start_time, end_time, color='lightblue', alpha=0.3,
                   label='Evening Load-up')

    # Plot morning shed periods
    for start_time, end_time, _ in morning_shed:
        plt.axvspan(start_time, end_time, color='lightpink', alpha=0.3,
                   label='Morning Shed')

    # Plot evening shed periods
    for start_time, end_time, _ in evening_shed:
        plt.axvspan(start_time, end_time, color='lightpink', alpha=0.3,
                   label='Evening Shed')

    # Format plot
    plt.title('Locational Marginal Price with Load-up and Shed Periods')
    plt.xlabel('Time')
    plt.ylabel('LMP ($)')

    hours = mdates.HourLocator(interval=2)
    h_fmt = mdates.DateFormatter('%H:%M')
    plt.gca().xaxis.set_major_locator(hours)
    plt.gca().xaxis.set_major_formatter(h_fmt)
    plt.xlim(df['interval_start_utc'].min(), df['interval_start_utc'].max())
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)

    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    return plt.gcf()

# Split the data into periods
morning_df, evening_df = split_day_periods(df)

# Identify peaks for each period
morning_peaks = identify_period_peaks(morning_df)
evening_peaks = identify_period_peaks(evening_df)

# Identify load-up periods
morning_loadup = identify_load_up_periods(morning_df, morning_peaks, is_morning=True)
evening_loadup = identify_load_up_periods(evening_df, evening_peaks, is_morning=False)

# Identify shed periods
morning_shed = identify_shed_periods(morning_df, morning_peaks, is_morning=True)
evening_shed = identify_shed_periods(evening_df, evening_peaks, is_morning=False)

# Resolve overlaps
morning_loadup, morning_shed = resolve_period_overlaps(morning_loadup, morning_shed)
evening_loadup, evening_shed = resolve_period_overlaps(evening_loadup, evening_shed)

# Create visualization
fig = visualize_split_peaks(df, morning_peaks, evening_peaks,
                          morning_loadup, evening_loadup,
                          morning_shed, evening_shed)
plt.show()
# Save the plot
#plt.savefig('/content/drive/MyDrive/PSU/GoogleColab/GridStatus/DAMDatasets/DAM10102024.png',dpi=300)

def create_data_for_csv(morning_loadup, morning_shed, evening_loadup, evening_shed):
    """
    Create CSV data combining morning and evening periods in one line
    """
    data = []
    row = {}
    
    # Process morning periods if they exist
    if morning_loadup and morning_shed:
        lu_start, lu_end, _ = morning_loadup[0]
        s_start, s_end, _ = morning_shed[0]
        
        row.update({
            'M_LU_time': lu_start.strftime('%H:%M'),
            'M_LU_duration': (lu_end - lu_start).total_seconds() / 3600,
            'M_S_time': s_start.strftime('%H:%M'),
            'M_S_duration': (s_end - s_start).total_seconds() / 3600
        })
    else:
        row.update({
            'M_LU_time': '',
            'M_LU_duration': '',
            'M_S_time': '',
            'M_S_duration': ''
        })
    
    # Process evening periods if they exist
    if evening_loadup and evening_shed:
        lu_start, lu_end, _ = evening_loadup[0]
        s_start, s_end, _ = evening_shed[0]
        
        row.update({
            'E_LU_time': lu_start.strftime('%H:%M'),
            'E_LU_duration': (lu_end - lu_start).total_seconds() / 3600,
            'E_S_time': s_start.strftime('%H:%M'),
            'E_S_duration': (s_end - s_start).total_seconds() / 3600
        })
    else:
        row.update({
            'E_LU_time': '',
            'E_LU_duration': '',
            'E_S_time': '',
            'E_S_duration': ''
        })
    
    data.append(row)
    return data

def save_schedule_to_csv(df, morning_loadup, morning_shed, evening_loadup, evening_shed):
    """
    Save schedule data to CSV file with one header line and one data line
    """
    # Create the data
    csv_data = create_data_for_csv(morning_loadup, morning_shed, evening_loadup, evening_shed)
    
    # Generate filename with date
    date_str = df['interval_start_utc'].iloc[0].strftime('%Y%m%d')
    csv_filename = f'Schedule_{date_str}.csv'
    csv_path = os.path.join(os.path.dirname(file_path), csv_filename)
    
    # Write to CSV
    fieldnames = ['M_LU_time', 'M_LU_duration', 'M_S_time', 'M_S_duration',
                 'E_LU_time', 'E_LU_duration', 'E_S_time', 'E_S_duration']
    
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    
    print(f"Schedule data saved as: {csv_path}")
    
    # Print summary
    print("\nSchedule Summary:")
    for row in csv_data:
        print("Morning:")
        print(f"  Load-up: {row['M_LU_time']} ({row['M_LU_duration']:.1f} hours)")
        print(f"  Shed: {row['M_S_time']} ({row['M_S_duration']:.1f} hours)")
        print("Evening:")
        print(f"  Load-up: {row['E_LU_time']} ({row['E_LU_duration']:.1f} hours)")
        print(f"  Shed: {row['E_S_time']} ({row['E_S_duration']:.1f} hours)")


# Print detailed information
print("\nMorning Peaks:")
for i, (peak_time, peak_price) in enumerate(morning_peaks, 1):
    print(f"Peak {i}:")
    print(f"  Time: {peak_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  LMP: ${peak_price:.2f}")
    print()

print("Evening Peaks:")
for i, (peak_time, peak_price) in enumerate(evening_peaks, 1):
    print(f"Peak {i}:")
    print(f"  Time: {peak_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  LMP: ${peak_price:.2f}")
    print()

print("\nMorning Load-up Periods:")
for i, (start_time, end_time, peak_time) in enumerate(morning_loadup, 1):
    print(f"Period {i}:")
    print(f"  Start: {start_time.strftime('%H:%M')}")
    print(f"  End: {end_time.strftime('%H:%M')}")
    print(f"  Duration: {(end_time - start_time).total_seconds() / 3600:.1f} hours")
    print(f"  For Peak at: {peak_time.strftime('%H:%M')}")
    print()

print("Evening Load-up Periods:")
for i, (start_time, end_time, peak_time) in enumerate(evening_loadup, 1):
    print(f"Period {i}:")
    print(f"  Start: {start_time.strftime('%H:%M')}")
    print(f"  End: {end_time.strftime('%H:%M')}")
    print(f"  Duration: {(end_time - start_time).total_seconds() / 3600:.1f} hours")
    print(f"  For Peak at: {peak_time.strftime('%H:%M')}")
    print()

print("\nMorning Shed Periods:")
for i, (start_time, end_time, peak_time) in enumerate(morning_shed, 1):
    print(f"Period {i}:")
    print(f"  Start: {start_time.strftime('%H:%M')}")
    print(f"  End: {end_time.strftime('%H:%M')}")
    print(f"  Duration: {(end_time - start_time).total_seconds() / 3600:.1f} hours")
    print(f"  For Peak at: {peak_time.strftime('%H:%M')}")
    print()

print("Evening Shed Periods:")
for i, (start_time, end_time, peak_time) in enumerate(evening_shed, 1):
    print(f"Period {i}:")
    print(f"  Start: {start_time.strftime('%H:%M')}")
    print(f"  End: {end_time.strftime('%H:%M')}")
    print(f"  Duration: {(end_time - start_time).total_seconds() / 3600:.1f} hours")
    print(f"  For Peak at: {peak_time.strftime('%H:%M')}")
    print()

save_schedule_to_csv(df, morning_loadup, morning_shed, evening_loadup, evening_shed)
