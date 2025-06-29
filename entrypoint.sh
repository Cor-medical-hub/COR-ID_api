#!/bin/bash

# read secrets

#if [[ $CORID_ENV == "prod" ]]; then
#  . ./corid_env.production
#fi
#if [[ $CORID_ENV == "dev" ]]; then
#  . ./corid_env.development
#fi
#
#[[ ! -d $SCAN_DIR ]] &&  mkdir $SCAN_DIR
#chmod -R 0777 $SCAN_DIR
#mount -t cifs "$SCAN_UNC/$SCAN_UNC_DIR" $SCAN_DIR -o ro,user=$SCAN_USER,password=$SCAN_PASSWORD



/usr/local/bin/alembic upgrade head

/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --log-config log_config.yaml
