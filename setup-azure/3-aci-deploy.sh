#!/bin/bash
source ../.env.local
source .env.local

infile=deploy.template.yaml
outfile=deploy.local.yaml
cp $infile $outfile

vars="MONGO_URI CONSUMER_KEY CONSUMER_SECRET FLASK_SECRET_KEY ADMIN_ACCOUNTS \
DEPLOY_LOCATION ACR_REGISTRY_ID ACR_USERNAME ACR_PASSWORD ACI_PERS_SHARE_NAME ACI_PERS_STORAGE_ACCOUNT_NAME STORAGE_KEY \
BACKEND_URI_LOCAL BACKEND_URI_GLOBAL"

# This method severely messes up MONGO_URI for some reason
#for var in $vars; do
#    # replace the variables in the yaml file
#    #sed -i "s/\${$var}/${!var}/g" $outfile  # fails if a var (e.g. MONGO_URI) contains "/"
#    sed -i "s#\${$var}#${!var}#g" "$outfile"  # will still fail if some variable contains "#"
#done

for var in $vars; do
    # use envvar instead
    envsubst \$$var < $outfile > tmp
    mv tmp $outfile
done

#echo $(cat $outfile)

az container create --resource-group $RESOURCE_GROUP --file $outfile

#rm $outfile
