# Marco-Polo
Beginning of an Algo Trading Bot

## What you need for now
Modify [Config File app/config.py ](app/config.py) to reflect the number of processors you have.  If you
do not know then set it low.  Default is to 8 which is my dev box. 

When ever you modify anything you will have to rebuild the docker image and run it again to update. 

## Docker instructions:
 
**Build Container**   
```docker build -t marko-polo```   

**Run container Linux / OSx**   
```docker run -v $(pwd)/app/output:/app/output marko-polo```

**Run container Windows Powershell**   
```docker run -v ${PWD}\app\output:/app/output marko-polo```


## Output folders
For now the output will be generated in app/output


