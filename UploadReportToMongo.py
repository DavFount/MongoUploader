# Author: Davidalen Fountain
# Version: 2.0
# Email: davfount@gmail.com
# Description: Takes a CSV file and uploads to Mongo DB. 


import csv
import time
import re
import json
import tkinter as tk
from os import path
from datetime import datetime
from tkinter import filedialog, END
from pymongo import MongoClient
from pymongo.errors import BulkWriteError


with open('config.json') as config_file:
    config = json.load(config_file)

#############################
# isTestPatient(PatientName)
# This function checks the columns with patient names and comapres it to an 
# array of invalid or test patient names.
# Inputs: PatientName is the name of the patient from the CSV file.
# returns boolean if the patient name is invalid or not
def isTestPatient(PatientName):
    for name in config["invalid_patient"]:
        if name in PatientName:
            return True
    return False

#############################
# FileSelect(event)
# This function handles the selection of a file via the GUI
# Inputs: Event Object
# no return value
def FileSelect(event=None):
    filename = filedialog.askopenfilename(
        initialdir="/", title="Select file", filetypes=(("CSV files", "*.csv"), ))
    entryText.set(filename)

def DatabaseMenu_SelectionEvent(e):
    collection_select = tk.OptionMenu(
        root, choices_variable, *config["collections"][dbchoices_variable.get()])
    collection_select.grid(row=2, column=0, pady=5)

#############################
# ImportToMongo()
# This function reads the CSV file line by line. Performs any required type conversions. And lastly uploads the config to a Mongo Database.
# Inputs: None
# No return value
def ImportToMongo():
    filepath = entryText.get()
    collection = choices_variable.get()
    database_name = dbchoices_variable.get()

    # Return error if file is lft blank or set to an invalid file.
    if not path.exists(filepath) or not 'csv' in filepath:
        error_text.set('Error:Invalid or Non-Existant File.')
        return

    # Return error if Collection is invalid
    if collection == 'Select a collection':
        error_text.set('Error: A collection is required.')
        return

    if database_name == 'Select a database':
        error_text.set('Error: A database is required.')

    client = MongoClient(config["connection_uri"])
    database = client[database_name]

    # Empty list to queue patients for upload
    FileContent = []

    # Clear Errors
    error_text.set('')

    with open(filepath) as csvFile:
        dbCollection = database[collection]
        csvReader = csv.DictReader(csvFile)
        error = ''
        # Loop through the file line by line
        for row in csvReader:
            # Check for invalid patients
            for key, value in row.items():
                if key in config["pt_name_columns"]:
                    if isTestPatient(value):
                        continue
            
            # Only works when needed.
            try:
                patient = dbCollection.find_one({"MRN": row["MRN"], "CURR_ADDRESS_1": row["CURR_ADDRESS_1"]})
                if patient:
                    continue
            except:
                pass

            # Convert data types to correct data Types
            if collection in config["conversion_sets"].keys():
                for conversion_set in config["conversion_sets"][collection]:
                    if not conversion_set["name"] in row.keys():
                        continue

                    if conversion_set["value"]:
                        row[conversion_set["name"]] = conversion_set["value"]
                    else:
                        try:
                            if conversion_set["type"] == "string":
                                row[conversion_set["name"]] = row[conversion_set["name"]].strip()
                            elif conversion_set["type"] == "float":
                                row[conversion_set["name"]] = float(row[conversion_set["name"]].replace(",", ""))
                            elif conversion_set["type"] == "integer":
                                row[conversion_set["name"]] = int(row[conversion_set["name"]])
                            elif conversion_set["type"] == "date":
                                row[conversion_set["name"]] = datetime.strptime(row[conversion_set["name"]], config["date_format"])
                            else:
                                print(f'Type not found: {conversion_set["type"]}')
                        except ValueError as ve:
                            print('Error: ', ve)
                
            
            FileContent.append(row)

        
        if error:
            last_run_text.set(error)
            return

        # Try to insert data into MongoDB and print any errors.
        try:
            dbCollection.insert_many(FileContent)
        except BulkWriteError as exc:
            print(exc.details)

        last_run_text.set(f'Upload Finished {entryText.get()}')
        entryText.set('')
        

root = tk.Tk()
root.title("Upload files to MongoDB")
root.minsize(410, 175)

entryText = tk.StringVar()
file_path = tk.Entry(root, textvariable=entryText, width=50)
file_path.grid(row=0, columnspan=2, column=0, pady=5, padx=5)

select_button = tk.Button(root, text='Select File', command=FileSelect)
select_button.grid(row=0, column=2, pady=5, padx=5)

dbchoices_variable = tk.StringVar()
dbchoices_variable.set('Select a database')

db_select = tk.OptionMenu(
    root, dbchoices_variable, *config["databases"], command = DatabaseMenu_SelectionEvent)
db_select.grid(row=1, column=0, pady=5)


choices_variable = tk.StringVar()
choices_variable.set('Select a collection')

upload_button_text = tk.StringVar()
upload_button = tk.Button(root, text='Upload File',
                          command=ImportToMongo)
upload_button.grid(row=1, column=1, pady=5, padx=5)

quit_button = tk.Button(root, text='Close', command=root.quit)
quit_button.grid(row=1, column=2, pady=5)

error_text = tk.StringVar()
error = tk.Label(root, textvariable=error_text)
error.config(fg='red')
error.grid(row=3, columnspan=3, pady=5, padx=2)

last_run_text = tk.StringVar()
last_run = tk.Label(root, textvariable=last_run_text)
last_run.grid(row=4, columnspan=3, pady=5, padx=2)
root.mainloop()
