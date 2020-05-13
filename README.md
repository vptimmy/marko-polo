# Marco-Polo
This is the beginning of an Algo trading bot.  This was a [COVID-19](https://en.wikipedia.org/wiki/Coronavirus_disease_2019)
inspired project to keep my mind busy and sane.  

A friend asked for assistance getting this [project](https://towardsdatascience.com/build-a-commission-free-algo-trading-bot-by-machine-learning-quarterly-earnings-reports-full-b414e5d759e8) 
up and running.  After all the usual hoops of debugging and getting the software configured I decided to attempt to streamline
the business logic and process.  This project includes a [Dockerfile](https://docker.com) so you do not have to
configure Python nor install any dependencies / requirements.

**THIS PROJECT IS INCOMPLETE!**   
Currently it will download all the 10-Q reports and create a financial.json file.  I still need to implement
creating the differences between the 10-Q reports and uploading the data to Google AI.


## Environmental Variables
You can set and control your own environmental variables by creating a `.env` file at the app directory. 
Environmental variables you can currently set:
```
LOGGING_LEVEL=INFO         # Can also be set to DEBUG, ERROR, WARNING.  Defaults to INFO
SEC_ANALYZE_SINCE_FY=2020  # Where do you want to start your analyze?  The further back the longer it takes
SEC_ANALYZE_QUARTER=QTR2   # This would just anyalze QTR2 in 2020.
```

## Docker instructions:
If you don't know much about Python then I recommend you to use [Docker](https://docker.com) to run
this program.  Docker will remove all the pain points of getting Python installed on your machine and setting
up your computer to run this application.  It will take ~ 10 minutes to download and install Docker compared
to hours of setting up and learning Python.

[Docker](https://docker.com) by default only gives you 2 cpus and limited memory.  This program does a lot of data processing, so the 
more cores / cpus / memory you give it the faster it will complete.

Go to your Docker Settings and modify your resources to allocate more.


**Build Container**   
```docker build -t marko-polo .```   

**Run container Linux / OSx**   
```docker run -v $(pwd)/app/output:/app/output marko-polo```

**Run container Windows Powershell**   
```docker run -v ${PWD}\app\output:/app/output marko-polo```

## Running locally with Python
Unless you know Python rather well I recommend you use the Docker above.  If you comfortable with Python
and know how to troubleshoot and install dependencies the you can follow the steps below to run locally.
  
First install Python 3.6+ (I use f-strings in the code)

### Running with Python Linux/OSx instructions
1) `pip3 install -r requirements.txt`
2) `python3 app/main.py`

### Running with Python Windows instructions
1) `pip3 install -r requirements.txt` *requires you to know where pip3 is on windows*
2) `python3 app\main.py`

## Output folders
As of now the log files stored in app/output.  Be sure to use the `-v` above to volume mount that folder.


