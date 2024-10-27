import subprocess
import time
import os
import signal
import csv
from datetime import datetime, timedelta

def start_commodity():
    global process
    process = subprocess.Popen(['./sample2'], stdin=subprocess.PIPE)
    time.sleep(5)
    send_command('o\n')  # Initial outside communication

def send_command(command):
    process.stdin.write(command.encode())
    process.stdin.flush()
    time.sleep(1)

def update_csv(input_file, output_file, last_line):
    with open(input_file, 'r') as input_csv, open(output_file, 'a') as output_csv:
        reader = csv.reader((row.replace('\0','') for row in input_csv), delimiter=',')
        writer = csv.writer(output_csv)
        for i, row in enumerate(reader):
            if i > last_line:
                writer.writerow(row)
                last_line = i
    return last_line

def end_service():
    os.kill(process.pid, signal.SIGINT)
    process.wait()
    time.sleep(5)

def get_schedule():
    schedule = []
    try:
        with open('Testing_schedule.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header row
            for row in reader:
                current_date = datetime.now().date()
                
                # Morning periods (first set of LU and S)
                if row[0] and row[1]:  # LU_time and LU_duration for morning
                    lu_time = datetime.combine(current_date, 
                                            datetime.strptime(row[0], '%H:%M').time())
                    schedule.append({
                        'command': 'l',
                        'start': lu_time,
                        'duration': float(row[1]) * 60,
                        'period': 'Morning Load-up'
                    })
                
                if row[2] and row[3]:  # S_time and S_duration for morning
                    s_time = datetime.combine(current_date, 
                                           datetime.strptime(row[2], '%H:%M').time())
                    schedule.append({
                        'command': 's',
                        'start': s_time,
                        'duration': float(row[3]) * 60,
                        'period': 'Morning Shed'
                    })
                
                # Evening periods (second set of LU and S)
                if row[4] and row[5]:  # LU_time and LU_duration for evening
                    lu_time = datetime.combine(current_date, 
                                            datetime.strptime(row[4], '%H:%M').time())
                    schedule.append({
                        'command': 'l',
                        'start': lu_time,
                        'duration': float(row[5]) * 60,
                        'period': 'Evening Load-up'
                    })
                
                if row[6] and row[7]:  # S_time and S_duration for evening
                    s_time = datetime.combine(current_date, 
                                           datetime.strptime(row[6], '%H:%M').time())
                    schedule.append({
                        'command': 's',
                        'start': s_time,
                        'duration': float(row[7]) * 60,
                        'period': 'Evening Shed'
                    })
        
        schedule.sort(key=lambda x: x['start'])
        
        # Handle day rollover
        for i in range(1, len(schedule)):
            if schedule[i]['start'] < schedule[i-1]['start']:
                schedule[i]['start'] += timedelta(days=1)
        
        # Print schedule for verification
        print("\nLoaded Schedule:")
        for event in schedule:
            print(f"{event['period']}: {event['start'].strftime('%H:%M')} "
                  f"for {event['duration']/60:.1f} hours")
        
        return schedule
        
    except FileNotFoundError:
        print("Error: 'Testing_schedule.csv' not found in the current directory.")
        return []
    except Exception as e:
        print(f"Error reading schedule: {e}")
        return []

def main():
    test_duration = int(input("How long should the test run? (hours): "))
    
    start_choice = input("Start immediately? (y/n): ").lower()
    if start_choice != 'y':
        start_time = input("Enter start time (HH:MM): ")
        hour, minute = map(int, start_time.split(':'))
        start_datetime = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        if start_datetime <= datetime.now():
            start_datetime += timedelta(days=1)
        wait_time = (start_datetime - datetime.now()).total_seconds()
        print(f"Waiting for {wait_time/3600:.2f} hours to start...")
        time.sleep(wait_time)

    print("Starting commodity service...")
    start_commodity()

    schedule = get_schedule()
    if not schedule:
        print("No valid schedule found. Exiting.")
        end_service()
        return

    last_event_time = max(item['start'] + timedelta(minutes=item['duration']) for item in schedule)
    end_time = max(datetime.now() + timedelta(hours=test_duration), last_event_time)

    last_line = 0
    last_command = None

    print("Beginning test execution...")
    while datetime.now() < end_time:
        current_time = datetime.now()
        
        # Find active command
        active_command = None
        for item in schedule:
            end_time_event = item['start'] + timedelta(minutes=item['duration'])
            if item['start'] <= current_time < end_time_event:
                active_command = item
                if last_command != item['command']:
                    send_command(f"{item['command']}\n")
                    print(f"Sent command: {item['command']} ({item['period']})")
                    last_command = item['command']
                break
        
        if not active_command:
            if last_command != 'e':
                send_command("e\n")  # Baseline if no other command is active
                print("Sent command: Baseline")
                last_command = 'e'

        send_command("o\n")
        print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("Sent outside communication command")

        last_line = update_csv('log.csv', 'output.csv', last_line)

        next_interval = current_time + timedelta(minutes=10)
        sleep_time = (next_interval - datetime.now()).total_seconds()
        if sleep_time > 0:
            print(f"Sleeping for {sleep_time/60:.2f} minutes...")
            time.sleep(sleep_time)

    end_service()
    print("Test completed.")
