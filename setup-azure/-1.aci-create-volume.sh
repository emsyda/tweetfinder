#!/bin/bash
source .env.local

# Change these four parameters as needed
ACI_PERS_RESOURCE_GROUP=$ACI_PERS_RESOURCE_GROUP
ACI_PERS_STORAGE_ACCOUNT_NAME_RANDOM=$ACI_PERS_STORAGE_ACCOUNT_NAME_RANDOM
ACI_PERS_LOCATION=$ACI_PERS_LOCATION
ACI_PERS_SHARE_NAME=$ACI_PERS_SHARE_NAME

# Create the storage account with the parameters
az storage account create \
    --resource-group $ACI_PERS_RESOURCE_GROUP \
    --name $ACI_PERS_STORAGE_ACCOUNT_NAME_RANDOM \
    --location $ACI_PERS_LOCATION \
    --sku Standard_LRS

# Create the file share
az storage share create \
  --name $ACI_PERS_SHARE_NAME \
  --account-name $ACI_PERS_STORAGE_ACCOUNT_NAME_RANDOM
