1- Testing_schedule.py
This script analyzes the day ahead market data and **AUTOMATICALLY** schedules the **_"Load-up"_** and **_"Shed"_** times and durations.
Also, it creates a testing schedule and stores it in Testing_schedule.csv

2- Testing_schedule_Manual.py 
This script analyzes the day ahead market data and prompts the user to enter the **_"Load-up"_** and **_"Shed"_** times and durations **MANUALLY**.
Also, it creates a testing schedule and stores it in Testing_schedule.csv


3- WH_testing.py
This script is used to run tests using the testing schedule file Testing_schedule.csv
Note: It works only with data that has only one peak

4- DrawController_FM.py
This script is used to run scheduled water draw. The water draws schedule file contains of two comma separated variables, the header line could be any two variables (e.g. Var1,Var2. or Time,Values).
The name of the file could be any .csv file but has to be updated in the DrawController_FM.py file.
