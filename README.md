# Marco-Polo
Beginning of an Algo Trading Bot

## What you need for now
Modify [Config File app/config.py ](app/config.py) to reflect the number of processors you have.  If you
do not know then set it low.  Default is to 8 which is my dev box. 

When ever you modify anything you will have to rebuild the docker image and run it again to update. 

## Docker instructions:
Be sure to be in this directory and run the two commands:   

```docker build -t marko-polo```   

```docker run -v $(pwd)/app/output:/app/output marko-polo```

## Output folders
For now the output will be generated in app/output

##  More to come later.