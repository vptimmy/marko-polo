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
NUMBER_OF_POOLS=8          # This is the number of CPU's / cores. Processes the data faster.
LOGGING_LEVEL=INFO         # Can also be set to DEBUG, ERROR, WARNING.  Defaults to INFO
SEC_ANALYZE_SINCE_FY=2020  # Where do you want to start your analyze?  The further back the longer it takes
SEC_ANALYZE_QUARTER=QTR2   # This would just anyalze QTR2 in 2020.
```

## Docker instructions:
**Build Container**   
```docker build -t marko-polo .```   

**Run container Linux / OSx**   
```docker run -v $(pwd)/app/output:/app/output marko-polo```

**Run container Windows Powershell**   
```docker run -v ${PWD}\app\output:/app/output marko-polo```

## Output folders
As of now the log files are located in app/output.  Be sure to use the `-v` above to volume mount that folder.


